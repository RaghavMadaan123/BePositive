"""
generate_data.py
----------------
Creates the synthetic, privacy-safe dataset used by GlucoTwin (DPDP Act / HIPAA
sandbox rule: no real patient data is used anywhere).

Two streams are produced, exactly as the challenge requires:

1. STATIC / HISTORICAL (Synthea-style EHR)       -> data/ehr_patients.csv
   demographics, diagnoses (ICD-10), labs (LOINC), medications, genetic markers
   + a FHIR R4 bundle per patient                 -> data/fhir/<id>.json

2. DYNAMIC / REAL-TIME (wearable + CGM, 5-min)   -> data/wearable_timeseries.csv.gz
   CGM glucose, heart rate, HRV (RMSSD), step count, sleep stage
   + the patient's own (incomplete, noisy) meal log -> data/meal_log.csv

The cohort is modelled on the Indian T2D population: "thin-fat" Asian-Indian
phenotype (high insulin resistance at lower BMI), carbohydrate-heavy meals,
late dinners, TCF7L2 risk-allele frequencies reported for South Asians.

The hidden physiology (true meals, true insulin sensitivity, ...) is saved to
data/ground_truth/ only for transparency; the predictive pipeline never reads it.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from physiology import simulate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

N_PATIENTS = 100
N_DAYS = 14
START = datetime(2026, 9, 1, 0, 0)
FIRST_NAMES_M = ["Arjun", "Rohan", "Vikram", "Suresh", "Anil", "Rahul", "Karthik", "Imran", "Deepak", "Manoj",
                 "Prakash", "Ravi", "Sanjay", "Harish", "Naveen", "Gaurav", "Faisal", "Ajay", "Mohan", "Vivek"]
FIRST_NAMES_F = ["Priya", "Anjali", "Kavya", "Meera", "Sunita", "Lakshmi", "Neha", "Fatima", "Pooja", "Divya",
                 "Asha", "Rekha", "Shalini", "Nandini", "Geeta", "Swati", "Ayesha", "Radha", "Uma", "Sneha"]
CITIES = ["Bengaluru", "Mumbai", "Chennai", "Hyderabad", "Delhi", "Kolkata", "Pune", "Kochi", "Ahmedabad", "Lucknow"]


def lognorm(rng, mean, sd_log, size=None):
    return mean * np.exp(rng.normal(0, sd_log, size) - sd_log ** 2 / 2)


def make_cohort(rng: np.random.Generator) -> pd.DataFrame:
    n = N_PATIENTS
    group = rng.choice(["T2D", "Prediabetes", "At-risk"], size=n, p=[0.6, 0.25, 0.15])
    sex = rng.choice(["M", "F"], size=n)
    age = np.where(group == "T2D", rng.normal(52, 10, n),
                   np.where(group == "Prediabetes", rng.normal(45, 10, n), rng.normal(38, 9, n)))
    age = np.clip(age, 28, 76).round().astype(int)
    bmi = np.clip(np.where(group == "T2D", rng.normal(26.8, 3.6, n), rng.normal(25.2, 3.4, n)), 19, 40).round(1)
    height = np.where(sex == "M", rng.normal(169, 6, n), rng.normal(156, 5.5, n))
    weight = (bmi * (height / 100) ** 2).round(1)
    waist = (bmi * np.where(sex == "M", 3.45, 3.35) + rng.normal(4, 4, n)).round(0)

    # Genetic markers (allele counts). South-Asian risk-allele frequencies (approx.).
    tcf7l2 = rng.binomial(2, 0.30, n)      # rs7903146 T allele  -> beta-cell secretion
    kcnq1 = rng.binomial(2, 0.40, n)       # rs2237892 C allele  -> beta-cell secretion
    fto = rng.binomial(2, 0.30, n)         # rs9939609 A allele  -> adiposity
    family_hx = rng.random(n) < np.where(group == "T2D", 0.65, 0.45)

    duration = np.where(group == "T2D", np.clip(rng.gamma(2.2, 3.0, n), 0.5, 25), 0).round(1)

    # Medications
    metformin = (group == "T2D") & (rng.random(n) < 0.82)
    sulfonylurea = (group == "T2D") & (rng.random(n) < 0.30)
    dpp4 = (group == "T2D") & (rng.random(n) < 0.22)
    basal_insulin = (group == "T2D") & (duration > 8) & (rng.random(n) < 0.35)
    statin = rng.random(n) < np.where(group == "T2D", 0.55, 0.15)
    hypertension = rng.random(n) < np.where(group == "T2D", 0.48, 0.25)
    acei = hypertension & (rng.random(n) < 0.7)

    # ---- latent physiology (hidden) ----
    si_base = np.where(group == "T2D", 4.8, np.where(group == "Prediabetes", 9.0, 15.0)) * 1e-4
    SI = lognorm(rng, si_base, 0.30) * np.exp(-0.045 * (bmi - 23)) * np.exp(-0.004 * (age - 45))
    SI *= np.exp(-0.01 * (waist - 90).clip(0))
    g_base = np.where(group == "T2D", 0.045, np.where(group == "Prediabetes", 0.078, 0.120))
    gamma = lognorm(rng, g_base, 0.25) * (1 - 0.12 * tcf7l2) * (1 - 0.06 * kcnq1) * np.exp(-0.02 * duration)
    gamma *= np.where(sulfonylurea, 1.45, 1.0) * np.where(dpp4, 1.15, 1.0)
    SG = lognorm(rng, np.where(group == "T2D", 0.0105, 0.0135), 0.15)
    Gb = np.where(group == "T2D", rng.normal(128, 12, n) + 1.2 * duration,
                  np.where(group == "Prediabetes", rng.normal(104, 6, n), rng.normal(90, 5, n)))
    Gb = Gb - np.where(metformin, 13, 0) - np.where(basal_insulin, 16, 0)
    kabs = rng.uniform(0.016, 0.030, n)
    k_ex = lognorm(rng, 1.6e-4, 0.25)

    # labs derived from physiology later (HbA1c, FPG) + independent labs
    ldl = np.clip(rng.normal(118, 30, n) - np.where(statin, 30, 0), 45, 220).round(0)
    hdl = np.clip(rng.normal(np.where(sex == "M", 40, 47), 8, n), 22, 80).round(0)
    tg = np.clip(lognorm(rng, np.where(group == "T2D", 175, 140), 0.35), 60, 500).round(0)
    egfr = np.clip(rng.normal(98 - 0.6 * (age - 40) - 0.7 * duration, 12, n), 25, 125).round(0)
    sbp = np.clip(rng.normal(np.where(hypertension, 142, 124), 12, n) - np.where(acei, 8, 0), 98, 185).round(0)
    dbp = np.clip(sbp * 0.62 + rng.normal(0, 6, n), 60, 110).round(0)

    names = [(rng.choice(FIRST_NAMES_M) if s == "M" else rng.choice(FIRST_NAMES_F)) for s in sex]
    ids = [f"GT-{1001 + i}" for i in range(n)]

    df = pd.DataFrame(dict(
        patient_id=ids, display_name=[f"{nm} (synthetic)" for nm in names], sex=sex, age=age,
        city=rng.choice(CITIES, n), cohort_group=group, height_cm=height.round(1), weight_kg=weight,
        bmi=bmi, waist_cm=waist, t2d_duration_yrs=duration, family_history_t2d=family_hx.astype(int),
        hypertension=hypertension.astype(int), dyslipidemia=(statin | (ldl > 130)).astype(int),
        nafld=(rng.random(n) < np.where(bmi > 27, 0.45, 0.2)).astype(int),
        med_metformin=metformin.astype(int), med_sulfonylurea=sulfonylurea.astype(int),
        med_dpp4i=dpp4.astype(int), med_basal_insulin=basal_insulin.astype(int),
        med_statin=statin.astype(int), med_acei=acei.astype(int),
        gene_TCF7L2_rs7903146=tcf7l2, gene_KCNQ1_rs2237892=kcnq1, gene_FTO_rs9939609=fto,
        ldl_mgdl=ldl, hdl_mgdl=hdl, tg_mgdl=tg, egfr=egfr, sbp=sbp, dbp=dbp,
    ))
    latent = pd.DataFrame(dict(patient_id=ids, SI=SI, SG=SG, Gb=Gb, gamma=gamma, kabs=kabs, BW=weight, k_ex=k_ex))
    return df, latent


def make_behaviour(rng, cohort: pd.DataFrame):
    """Per-patient habits -> minute-level carbs, activity, sleep, stress."""
    n = len(cohort)
    T = N_DAYS * 1440
    carbs = np.zeros((T, n))
    activity = np.zeros((T, n))
    stress = np.zeros((T, n))
    asleep = np.zeros((T, n), dtype=bool)
    stage = np.zeros((T, n), dtype=np.int8)       # 0 wake 1 light 2 deep 3 REM
    meals, logs = [], []
    si_mult = np.ones((N_DAYS, n))
    stress_day = np.zeros((N_DAYS, n), dtype=bool)
    sleep_summary = []

    habit = dict(
        bf=rng.normal(8.4, 0.7, n), lu=rng.normal(13.6, 0.6, n), sn=rng.normal(17.2, 0.5, n), di=rng.normal(21.0, 0.7, n),
        p_snack=rng.uniform(0.3, 0.9, n), carb_mult=lognorm(rng, 1.0, 0.22, n), p_log=rng.uniform(0.35, 0.9, n),
        p_mwalk=rng.uniform(0.05, 0.7, n), p_pdwalk=rng.uniform(0.0, 0.6, n), bed=rng.normal(23.4, 0.7, n),
        sleep_h=np.clip(rng.normal(6.6, 0.8, n), 4.8, 8.5), p_poor=rng.uniform(0.08, 0.35, n), p_stress=rng.uniform(0.05, 0.3, n),
        bg_steps=rng.uniform(3, 9, n),
    )
    mean_carbs = dict(bf=52, lu=82, sn=28, di=76)

    for d in range(N_DAYS):
        weekend = (START + timedelta(days=d)).weekday() >= 5
        # ---- sleep of the night that ENDS on day d morning (starts d-1 evening) ----
        for p in range(n):
            poor = rng.random() < habit["p_poor"][p]
            dur = habit["sleep_h"][p] + rng.normal(0, 0.6) - (1.3 if poor else 0) + (0.6 if weekend else 0)
            dur = float(np.clip(dur, 3.5, 9.5))
            bed = habit["bed"][p] + rng.normal(0, 0.5) + (0.6 if weekend else 0)
            start = int((d * 24 + bed - 24) * 60)
            end = start + int(dur * 60)
            deep_scale = 0.55 if poor else 1.0
            mins = 0
            deep_min = 0
            for t in range(max(start, 0), min(end, T)):
                rel = t - start
                cyc = (rel % 90) / 90
                frac_night = rel / max(end - start, 1)
                if rel < 12 or rng.random() < 0.015:
                    s = 0
                elif cyc < 0.45:
                    s = 1
                elif cyc < 0.75 and rng.random() < deep_scale * (1.2 - frac_night):
                    s = 2
                elif cyc >= 0.75 and rng.random() < 0.4 + 0.6 * frac_night:
                    s = 3
                else:
                    s = 1
                asleep[t, p] = True
                stage[t, p] = s
                mins += 1
                deep_min += s == 2
            deep_frac = deep_min / max(mins, 1)
            # poor / short sleep -> reduced insulin sensitivity next day (Spiegel 1999, Donga 2010)
            si_mult[d, p] = float(np.clip(1 - 0.09 * max(0, 7 - dur) - (0.12 if deep_frac < 0.12 else 0), 0.6, 1.05))
            sd = rng.random() < habit["p_stress"][p]
            stress_day[d, p] = sd
            if sd:
                stress[d * 1440 + 9 * 60: d * 1440 + 19 * 60, p] += rng.uniform(0.06, 0.13)
            sleep_summary.append(dict(patient_id=cohort.patient_id[p], day=d, sleep_hours=round(dur, 2),
                                      deep_fraction=round(deep_frac, 3)))

        # ---- meals ----
        for p in range(n):
            for key in ["bf", "lu", "sn", "di"]:
                if key == "sn" and rng.random() > habit["p_snack"][p]:
                    continue
                if key == "bf" and rng.random() < 0.06:
                    continue
                hour = habit[key][p] + rng.normal(0, 0.45) + (0.7 if weekend and key in ("bf", "di") else 0)
                tmin = int(d * 1440 + hour * 60)
                if not (0 <= tmin < T):
                    continue
                c = mean_carbs[key] * habit["carb_mult"][p] * lognorm(rng, 1.0, 0.25)
                if rng.random() < 0.07:   # festive / restaurant meal
                    c *= 1.6
                if weekend:
                    c *= 1.12
                c = float(np.clip(c, 8, 220))
                dur_eat = 15
                carbs[tmin:tmin + dur_eat, p] += c / dur_eat
                meals.append(dict(patient_id=cohort.patient_id[p], time=START + timedelta(minutes=tmin), meal=key, carbs_g=round(c, 1)))
                if rng.random() < habit["p_log"][p]:
                    logs.append(dict(patient_id=cohort.patient_id[p], time=START + timedelta(minutes=tmin + int(rng.integers(0, 10))),
                                     meal=key, carbs_g_estimated=round(c * lognorm(rng, 1.0, 0.3), 0)))
                # post-meal walk
                if key == "di" and rng.random() < habit["p_pdwalk"][p]:
                    w0 = tmin + int(rng.integers(15, 40))
                    activity[w0:w0 + int(rng.integers(15, 35)), p] = rng.uniform(0.7, 1.0)
            if rng.random() < habit["p_mwalk"][p]:
                w0 = int(d * 1440 + rng.normal(6.6, 0.4) * 60)
                L = int(rng.integers(20, 50))
                activity[w0:w0 + L, p] = rng.uniform(0.8, 1.1)
    return dict(carbs=carbs, activity=activity, stress=stress, asleep=asleep, stage=stage, si_mult=si_mult,
                stress_day=stress_day, meals=pd.DataFrame(meals), logs=pd.DataFrame(logs),
                sleep=pd.DataFrame(sleep_summary), habit=habit)


def run():
    rng = np.random.default_rng(2026)
    os.makedirs(os.path.join(DATA, "ground_truth"), exist_ok=True)
    os.makedirs(os.path.join(DATA, "fhir"), exist_ok=True)

    cohort, latent = make_cohort(rng)
    beh = make_behaviour(rng, cohort)
    n, T = len(cohort), N_DAYS * 1440

    # background wake activity (ambulation) adds a little to activity intensity
    wake = ~beh["asleep"]
    bg = (rng.random((T, n)) < 0.12) * rng.uniform(0.15, 0.45, (T, n)) * wake
    act = np.maximum(beh["activity"], bg)

    # ---- simulate true glucose day by day (insulin sensitivity varies with sleep) ----
    par = {k: latent[k].values.astype(float) for k in ["SI", "SG", "Gb", "gamma", "kabs", "BW", "k_ex"]}
    G_true = np.empty((T, n))
    state = None
    # warm-up day using day-0 inputs
    _, state = simulate(par, beh["carbs"][:1440], act[:1440], beh["stress"][:1440], return_state=True)
    for d in range(N_DAYS):
        p_d = dict(par); p_d["SI"] = par["SI"] * beh["si_mult"][d]
        sl = slice(d * 1440, (d + 1) * 1440)
        G_true[sl], state = simulate(p_d, beh["carbs"][sl], act[sl], beh["stress"][sl], state0=state, return_state=True)

    # ---- CGM: interstitial lag (~8 min) + sensor noise, sampled every 5 min ----
    lag = 8
    G_isf = np.vstack([np.repeat(G_true[:1], lag, 0), G_true[:-lag]])
    idx5 = np.arange(4, T, 5)
    cgm = G_isf[idx5] + rng.normal(0, 1, (len(idx5), n)) * (3 + 0.03 * G_isf[idx5])
    cgm = np.clip(cgm, 40, 400).round(0)

    # ---- wearables at 5-min cadence ----
    act5 = act.reshape(-1, 5, n).mean(1)
    asleep5 = beh["asleep"].reshape(-1, 5, n).mean(1) > 0.5
    stage5 = beh["stage"][idx5]
    stress5 = beh["stress"][idx5] > 0
    group = cohort.cohort_group.values
    rhr = rng.normal(70, 6, n) + np.where(group == "T2D", 5, 0) + 0.25 * (cohort.bmi.values - 25)
    base_hrv = np.clip(rng.normal(42, 9, n) - 0.35 * (cohort.age.values - 40) - np.where(group == "T2D", 6, 0), 12, 80)
    day5 = np.repeat(np.arange(N_DAYS), 288)
    simult5 = beh["si_mult"][day5]
    carbs5 = beh["carbs"].reshape(-1, 5, n).sum(1)
    postmeal = pd.DataFrame(carbs5).rolling(12, min_periods=1).sum().values > 10

    hr = rhr + 42 * act5 - 9 * asleep5 + 3.5 * postmeal + 7 * stress5 + rng.normal(0, 2.5, act5.shape)
    hr += (1 - simult5) * 20 * (~asleep5)
    hrv = base_hrv * (1 + 0.22 * asleep5 - 0.45 * np.clip(act5, 0, 1) - 0.22 * stress5 - 0.6 * (1 - simult5)) \
        * lognorm(rng, 1.0, 0.12, act5.shape)
    steps = np.where(asleep5, 0, rng.poisson(np.clip(act5 * 110 * 5 + cohort.bmi.values * 0, 0, None)))

    ts = [START + timedelta(minutes=int(m + 1)) for m in idx5]
    long = pd.DataFrame({
        "patient_id": np.tile(cohort.patient_id.values, len(idx5)),
        "timestamp": np.repeat(np.array(ts, dtype="datetime64[m]"), n),
        "cgm_mgdl": cgm.ravel(),
        "heart_rate_bpm": hr.round(0).ravel(),
        "hrv_rmssd_ms": hrv.round(1).ravel(),
        "steps": steps.ravel().astype(int),
        "sleep_stage": np.where(asleep5, stage5, 0).ravel().astype(int),
    }).sort_values(["patient_id", "timestamp"])
    long.to_csv(os.path.join(DATA, "wearable_timeseries.csv.gz"), index=False, compression="gzip")

    # ---- EHR labs derived from physiology (consistent HbA1c / fasting glucose) ----
    mean_g = G_true.mean(0)
    cohort["hba1c_pct"] = np.clip((mean_g + 46.7) / 28.7 + rng.normal(0, 0.25, n), 4.6, 13.5).round(1)
    fasting = G_true[[d * 1440 + 7 * 60 for d in range(N_DAYS)]].mean(0)
    cohort["fasting_glucose_mgdl"] = (fasting + rng.normal(0, 6, n)).round(0)
    # HOMA-IR-like proxy available in many Indian lab panels
    cohort["fasting_insulin_uU"] = np.clip(10 * (1e-3 / latent.SI.values) ** 0.5 + rng.normal(0, 2, n), 2, 40).round(1)
    cohort["last_visit_date"] = (START - pd.to_timedelta(rng.integers(5, 80, n), unit="D")).strftime("%Y-%m-%d")
    cohort.to_csv(os.path.join(DATA, "ehr_patients.csv"), index=False)

    beh["logs"].sort_values(["patient_id", "time"]).to_csv(os.path.join(DATA, "meal_log.csv"), index=False)

    # ground truth (never used by the predictor)
    latent.to_csv(os.path.join(DATA, "ground_truth", "latent_physiology.csv"), index=False)
    beh["meals"].to_csv(os.path.join(DATA, "ground_truth", "true_meals.csv"), index=False)
    beh["sleep"].to_csv(os.path.join(DATA, "ground_truth", "sleep_nightly.csv"), index=False)

    write_fhir(cohort)
    print(f"cohort: {n} patients x {N_DAYS} days | CGM rows: {len(long):,}")
    print(cohort.cohort_group.value_counts().to_dict())
    print("mean CGM by group:", long.merge(cohort[["patient_id", "cohort_group"]]).groupby("cohort_group").cgm_mgdl.mean().round(1).to_dict())
    print("share CGM>180:", round((long.cgm_mgdl > 180).mean(), 3))
    return cohort


def write_fhir(cohort: pd.DataFrame):
    """Minimal FHIR R4 bundle per patient so the EHR stream is interoperable (ABDM / HL7 ready)."""
    loinc = {"hba1c_pct": ("4548-4", "Hemoglobin A1c/Hemoglobin.total in Blood", "%"),
             "fasting_glucose_mgdl": ("1558-6", "Fasting glucose [Mass/volume] in Serum or Plasma", "mg/dL"),
             "bmi": ("39156-5", "Body mass index", "kg/m2"),
             "ldl_mgdl": ("13457-7", "LDL cholesterol (calculated)", "mg/dL"),
             "egfr": ("33914-3", "eGFR", "mL/min/1.73m2"),
             "sbp": ("8480-6", "Systolic blood pressure", "mm[Hg]")}
    icd = {"T2D": ("E11.9", "Type 2 diabetes mellitus without complications"),
           "Prediabetes": ("R73.03", "Prediabetes")}
    for _, r in cohort.iterrows():
        entries = [{"resource": {"resourceType": "Patient", "id": r.patient_id, "gender": "male" if r.sex == "M" else "female",
                                 "birthDate": str(2026 - int(r.age)), "address": [{"city": r.city, "country": "IN"}],
                                 "meta": {"tag": [{"code": "SYNTHETIC"}]}}}]
        if r.cohort_group in icd:
            c, d = icd[r.cohort_group]
            entries.append({"resource": {"resourceType": "Condition", "subject": {"reference": f"Patient/{r.patient_id}"},
                                         "code": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10", "code": c, "display": d}]}}})
        if r.hypertension:
            entries.append({"resource": {"resourceType": "Condition", "subject": {"reference": f"Patient/{r.patient_id}"},
                                         "code": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10", "code": "I10", "display": "Essential hypertension"}]}}})
        for col, (code, disp, unit) in loinc.items():
            entries.append({"resource": {"resourceType": "Observation", "status": "final", "subject": {"reference": f"Patient/{r.patient_id}"},
                                         "code": {"coding": [{"system": "http://loinc.org", "code": code, "display": disp}]},
                                         "valueQuantity": {"value": float(r[col]), "unit": unit}, "effectiveDateTime": r.last_visit_date}})
        for med in ["metformin", "sulfonylurea", "dpp4i", "basal_insulin", "statin", "acei"]:
            if r[f"med_{med}"]:
                entries.append({"resource": {"resourceType": "MedicationStatement", "status": "active",
                                             "subject": {"reference": f"Patient/{r.patient_id}"},
                                             "medicationCodeableConcept": {"text": med.replace("_", " ")}}})
        bundle = {"resourceType": "Bundle", "type": "collection", "entry": entries}
        with open(os.path.join(DATA, "fhir", f"{r.patient_id}.json"), "w") as f:
            json.dump(bundle, f, indent=1)


if __name__ == "__main__":
    run()
