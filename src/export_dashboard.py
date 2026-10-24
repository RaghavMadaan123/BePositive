"""
export_dashboard.py
-------------------
Packages everything the clinician dashboard needs into dashboard/data.js
(a plain JS file, so dashboard/index.html opens straight from disk with no server).

For a set of held-out patients:
  * last 72 h of CGM, twin glucose, HR, HRV, steps, sleep stages, meal events
  * GlucoTwin risk every 15 min + alerts
  * local explanation of the latest alert (which data stream drove it)
  * twin parameters (EHR prior vs calibrated) and patient summary
  * pre-computed what-if scenarios from the twin state at 18:30 on day 13
"""
from __future__ import annotations

import itertools
import json
import os
import shutil

import numpy as np
import pandas as pd

from features import FEATURE_GROUPS, SPIKE
from physiology import simulate
from twin_engine import STEP, ROOT

WHATIF_DAY = 12
WHATIF_K = WHATIF_DAY * 288 + 222 - 1        # sample whose timestamp is 18:30 on the day
WINDOW_DAYS = 3
DASH = os.path.join(ROOT, "dashboard")
N_SHOW = 8


def _np(o):
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    raise TypeError(type(o))


def _round(a, nd=1):
    return [None if (v is None or (isinstance(v, float) and np.isnan(v))) else round(float(v), nd) for v in a]


def plan_from_habits(prof_i, typical_i, start_hour, hours=24):
    """Habitual next-24h plan for one patient from the twin's learned meal profile."""
    T = hours * 60
    carbs = np.zeros(T)
    meals = []
    windows = {"dinner": (19.0, 23.5, 1.15), "breakfast": (6.0, 11.0, 0.75), "lunch": (12.0, 15.5, 1.1)}
    for name, (lo, hi, scale) in windows.items():
        slots = np.arange(int(lo * 4), int(hi * 4))
        s = slots[np.argmax(prof_i[slots])]
        h = s / 4
        rel = (h - start_hour) % 24
        m0 = int(rel * 60)
        c = float(np.clip(typical_i * scale, 25, 140))
        carbs[m0:m0 + 15] += c / 15
        meals.append(dict(name=name, minute=m0, carbs=round(c)))
    return carbs, sorted(meals, key=lambda m: m["minute"])


def run(ehr, arr, times, twin, fitted, df, models, metrics, cal_report):
    os.makedirs(DASH, exist_ok=True)
    figs_src = os.path.join(ROOT, "outputs", "figures")
    figs_dst = os.path.join(DASH, "figures")
    os.makedirs(figs_dst, exist_ok=True)
    for f in os.listdir(figs_src):
        shutil.copy(os.path.join(figs_src, f), figs_dst)

    m, cols, thr = models["M4 GlucoTwin (full)"]
    df = df.copy()
    df["risk"] = m.predict_proba(df[cols])[:, 1]
    df.loc[df.eligible == 0, "risk"] = np.nan   # already above 180 -> "in excursion", not a prediction
    train_med = df[cols].median()

    test_ids = metrics["test_patients"]
    T = arr["cgm_mgdl"].shape[0]
    k0 = T - WINDOW_DAYS * 288
    pid_index = {p: i for i, p in enumerate(ehr.patient_id)}

    # pick a varied set of held-out patients: highest-risk T2D first, then prediabetes, at-risk
    summ = []
    for p in test_ids:
        i = pid_index[p]
        c = arr["cgm_mgdl"][k0:, i]
        recent = df[(df.patient_idx == i) & (df.k >= T - 288)]
        summ.append(dict(p=p, i=i, grp=ehr.cohort_group[i], tir=float(((c >= 70) & (c <= 180)).mean()),
                         alerts=int((recent.risk >= thr).sum())))
    summ = pd.DataFrame(summ)
    chosen = []
    for grp, k in [("T2D", 4), ("Prediabetes", 2), ("At-risk", 2)]:
        chosen += summ[summ.grp == grp].sort_values("tir").p.tolist()[:k]
    chosen = chosen[:N_SHOW]

    patients = []
    for p in chosen:
        i = pid_index[p]
        e = ehr.iloc[i]
        sl = slice(k0, T)
        pdf = df[(df.patient_idx == i) & (df.k >= k0)].sort_values("k")
        risk_series = pdf[["k", "risk"]].values
        # latest alert explanation (or latest prediction if none)
        al = pdf[pdf.risk >= thr]
        row = al.iloc[-1] if len(al) else pdf.dropna(subset=["risk"]).iloc[-1]
        logit = lambda q: float(np.log(np.clip(q, 1e-6, 1 - 1e-6) / (1 - np.clip(q, 1e-6, 1 - 1e-6))))
        xrow = row[cols].to_frame().T.astype(float)
        base_p = float(m.predict_proba(xrow)[:, 1][0])
        contrib = {}
        for g, gcols in FEATURE_GROUPS.items():
            x = xrow.copy()
            x[gcols] = train_med[gcols].values
            # contribution in log-odds: how much this stream moves the alert vs a "typical" patient
            contrib[g] = round(logit(base_p) - logit(float(m.predict_proba(x)[:, 1][0])), 2)
        explain = dict(time=str(times[int(row.k)])[:16], risk=round(base_p, 3), contributions=contrib,
                       facts=dict(cgm_now=float(row.cgm_now), slope_15=round(float(row.slope_15), 2),
                                  twin_fc_habit_max=round(float(row.twin_fc_habit_max), 0),
                                  twin_fc_nomeal_max=round(float(row.twin_fc_nomeal_max), 0),
                                  twin_meal_prob_2h=round(float(row.twin_meal_prob_2h), 2),
                                  sleep_hrs_last_night=round(float(row.sleep_hrs_last_night), 1),
                                  hrv_rel=round(float(row.hrv_rel), 2), steps_120=int(row.steps_120)))

        # meals in window
        logged = np.nonzero(arr["logged_carbs"][sl, i])[0]
        detected = np.nonzero(twin["detected"][sl, i])[0]

        # ---- what-if from the synchronised twin state at 18:30 on the anchor day ----
        whatif = None
        if WHATIF_K in twin["states"]:
            st = {kk: v[i] for kk, v in twin["states"][WHATIF_K].items()}
            par_i = {kk: v[i] for kk, v in fitted.items()}
            start_hour = 18.5
            carbs0, meals0 = plan_from_habits(twin["habit_prof"][:, i], twin["typical_carbs"][i], start_hour)
            dinner = [mm for mm in meals0 if mm["name"] == "dinner"][0]
            scen = {}
            on_met = bool(e.med_metformin)
            for cut, walk, sleep, met in itertools.product([0, 25, 50], [0, 15, 30], ["normal", "short"],
                                                           ["taken", "missed"] if on_met else ["taken"]):
                c = carbs0.copy()
                d0 = dinner["minute"]
                c[d0:d0 + 15] *= (1 - cut / 100)
                a = np.zeros_like(c)
                if walk:
                    a[d0 + 20: d0 + 20 + walk] = 0.9
                gb = 13.0 if met == "missed" else 0.0
                # short sleep tonight lowers insulin sensitivity from next morning (07:00)
                split = int(((7 - start_hour) % 24) * 60)
                pr = {kk: np.atleast_1d(np.asarray(v, float)) for kk, v in par_i.items()}
                pr["Gb"] = pr["Gb"] + gb
                s = {kk: np.atleast_1d(np.asarray(v, float)) for kk, v in st.items()}
                g1, s_mid = simulate(pr, c[:split, None], a[:split, None], state0=s, record_every=5, return_state=True)
                p2 = dict(pr); p2["SI"] = pr["SI"] * (0.8 if sleep == "short" else 1.0)
                g2 = simulate(p2, c[split:, None], a[split:, None], state0=s_mid, record_every=5)
                g = np.r_[g1[:, 0], g2[:, 0]]
                key = f"{cut}|{walk}|{sleep}|{met}"
                dwin = g[d0 // 5: d0 // 5 + 48]
                scen[key] = dict(g=_round(g, 0), peak=round(float(g.max())), dinner_peak=round(float(dwin.max())),
                                 dinner_mins_above=int((dwin > SPIKE).sum() * 5),
                                 mins_above=int((g > SPIKE).sum() * 5), tir=round(float(((g >= 70) & (g <= 180)).mean()), 3))
            whatif = dict(start=str(times[WHATIF_K])[:16], meals=meals0, on_metformin=on_met, scenarios=scen)

        cal = cal_report.iloc[i]
        cg = arr["cgm_mgdl"][sl, i]
        patients.append(dict(
            id=p, name=e.display_name, sex=e.sex, age=int(e.age), city=e.city, group=e.cohort_group,
            ehr=dict(bmi=float(e.bmi), waist=float(e.waist_cm), hba1c=float(e.hba1c_pct), fpg=float(e.fasting_glucose_mgdl),
                     fasting_insulin=float(e.fasting_insulin_uU), duration=float(e.t2d_duration_yrs),
                     egfr=float(e.egfr), ldl=float(e.ldl_mgdl), tg=float(e.tg_mgdl), bp=f"{int(e.sbp)}/{int(e.dbp)}",
                     family_history=bool(e.family_history_t2d), hypertension=bool(e.hypertension),
                     nafld=bool(e.nafld), dyslipidemia=bool(e.dyslipidemia),
                     meds=[mname for mname, col in [("Metformin", "med_metformin"), ("Sulfonylurea", "med_sulfonylurea"),
                                                    ("DPP-4 inhibitor", "med_dpp4i"), ("Basal insulin", "med_basal_insulin"),
                                                    ("Statin", "med_statin"), ("ACE inhibitor", "med_acei")] if e[col]],
                     genes=dict(TCF7L2=int(e.gene_TCF7L2_rs7903146), KCNQ1=int(e.gene_KCNQ1_rs2237892), FTO=int(e.gene_FTO_rs9939609)),
                     last_visit=e.last_visit_date),
            twin=dict(SI_prior=round(cal.SI_prior * 1e4, 2), SI=round(cal.SI_twin * 1e4, 2), gamma_prior=round(cal.gamma_prior, 4),
                      gamma=round(cal.gamma_twin, 4), Gb=round(cal.Gb_twin, 0), rmse_prior=round(cal.rmse_prior, 1),
                      rmse_cal=round(cal.rmse_calibrated, 1)),
            stats=dict(tir=round(float(((cg >= 70) & (cg <= 180)).mean()), 3), mean=round(float(cg.mean()), 0),
                       gmi=round(3.31 + 0.02392 * float(cg.mean()), 1), cv=round(float(cg.std() / cg.mean()), 3),
                       spikes=int(((cg[1:] > SPIKE) & (cg[:-1] <= SPIKE)).sum())),
            series=dict(cgm=_round(cg, 0), twin=_round(twin["twin_G"][sl, i], 0), hr=_round(arr["heart_rate_bpm"][sl, i], 0),
                        hrv=_round(arr["hrv_rmssd_ms"][sl, i], 1), steps=[int(v) for v in arr["steps"][sl, i]],
                        sleep=[int(v) for v in arr["sleep_stage"][sl, i]],
                        risk=[[int(k - k0), None if np.isnan(r) else round(float(r), 3)] for k, r in risk_series]),
            meals=dict(logged=[[int(k), round(float(arr["logged_carbs"][k0 + k, i]))] for k in logged],
                       detected=[[int(k), round(float(twin["detected"][k0 + k, i]))] for k in detected]),
            explain=explain, whatif=whatif,
        ))

    mm = metrics["models"]
    payload = dict(
        generated="GlucoTwin PoC - synthetic data only",
        t0=str(times[k0])[:16], step_min=STEP, threshold=round(thr, 3), spike=SPIKE,
        model=dict(task=metrics["task"], n_patients=metrics["n_patients"], n_test=metrics["n_test_patients"],
                   prevalence=round(metrics["prevalence"], 3),
                   table=[dict(name=k, auroc=round(v["auroc"], 3), auprc=round(v["auprc"], 3),
                               sens=round(v["event_sensitivity"], 3), lead=v["median_lead_min"],
                               fa=round(v["false_alerts_per_patient_day"], 2)) for k, v in mm.items()],
                   streams=metrics["group_importance_auroc_drop"]),
        patients=patients,
    )
    with open(os.path.join(DASH, "data.js"), "w") as f:
        f.write("window.GT_DATA = ")
        json.dump(payload, f, separators=(",", ":"), default=_np)
        f.write(";\n")
    print(f"dashboard data: {len(patients)} patients -> dashboard/data.js "
          f"({os.path.getsize(os.path.join(DASH, 'data.js')) / 1e6:.1f} MB)")
