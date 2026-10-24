"""
twin_engine.py
--------------
The Digital Twin itself: one calibrated, continuously synchronised virtual
patient per real patient.

Lifecycle of a twin
    1. INITIALISE  - prior physiology from the EHR (fasting glucose, HOMA-IR,
                     diagnosis, medication, TCF7L2/KCNQ1 genotype)
    2. CALIBRATE   - personalise insulin sensitivity (SI) and beta-cell
                     responsiveness (gamma) on the first 3 days ("onboarding")
                     of CGM + meal log + step data
    3. SYNCHRONISE - every 5 minutes a state observer pulls the virtual
                     patient towards the latest CGM reading and detects
                     unlogged meals from the glucose trajectory
    4. FORECAST    - every 15 minutes the twin is run 2 h into the future under
                     (a) "no further meal" and (b) "habitual behaviour" scenarios
    5. WHAT-IF     - clinicians run counterfactual scenarios (smaller dinner,
                     post-meal walk, better sleep, missed metformin)
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from physiology import simulate, V_G, F_BIO

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

CAL_DAYS = 3
STEP = 5                  # CGM cadence (min)
PRED_EVERY = 15           # prediction cadence (min)
HORIZON = 120             # forecast horizon (min)
K_OBS = 0.35              # observer gain on glucose
POP_KEX = 1.6e-4
PRIOR_W = 150.0
SI_GRID = np.array([0.35, 0.5, 0.7, 0.85, 1.0, 1.2, 1.45, 1.8, 2.3, 3.0])
GAMMA_GRID = np.array([0.5, 0.75, 1.0, 1.4, 2.0])


# --------------------------------------------------------------------------- data
def load():
    ehr = pd.read_csv(os.path.join(DATA, "ehr_patients.csv"))
    ts = pd.read_csv(os.path.join(DATA, "wearable_timeseries.csv.gz"), parse_dates=["timestamp"])
    meals = pd.read_csv(os.path.join(DATA, "meal_log.csv"), parse_dates=["time"])
    ids = ehr.patient_id.tolist()
    ts = ts.sort_values(["patient_id", "timestamp"])
    times = np.sort(ts.timestamp.unique())
    n, T = len(ids), len(times)
    arr = {}
    for col in ["cgm_mgdl", "heart_rate_bpm", "hrv_rmssd_ms", "steps", "sleep_stage"]:
        arr[col] = ts.pivot(index="timestamp", columns="patient_id", values=col)[ids].values.astype(float)
    t0 = pd.Timestamp(times[0]) - pd.Timedelta(minutes=STEP)
    # logged carbs on the 5-min grid
    logged = np.zeros((T, n))
    pidx = {p: i for i, p in enumerate(ids)}
    for _, r in meals.iterrows():
        k = int((r.time - t0) / pd.Timedelta(minutes=STEP))
        if 0 <= k < T:
            logged[k, pidx[r.patient_id]] += r.carbs_g_estimated
    arr["logged_carbs"] = logged
    arr["activity"] = np.clip(arr["steps"] / (110 * STEP), 0, 1.2)
    return ehr, arr, pd.to_datetime(times), meals


# --------------------------------------------------------------------------- 1. prior
def ehr_prior(ehr: pd.DataFrame) -> dict:
    """Population knowledge -> prior twin parameters. Uses ONLY EHR fields."""
    fpg = ehr.fasting_glucose_mgdl.values
    homa = fpg * ehr.fasting_insulin_uU.values / 405.0
    SI = 15e-4 * (1.0 / np.clip(homa, 0.3, 20)) ** 0.9 * np.exp(-0.03 * (ehr.bmi.values - 23))
    grp = ehr.cohort_group.values
    gamma = np.where(grp == "T2D", 0.045, np.where(grp == "Prediabetes", 0.078, 0.12))
    gamma = gamma * (1 - 0.12 * ehr.gene_TCF7L2_rs7903146.values) * (1 - 0.06 * ehr.gene_KCNQ1_rs2237892.values)
    gamma = gamma * np.where(ehr.med_sulfonylurea.values == 1, 1.45, 1) * np.where(ehr.med_dpp4i.values == 1, 1.15, 1)
    SG = np.where(grp == "T2D", 0.0105, 0.0135)
    return dict(SI=SI, gamma=gamma, SG=SG, Gb=fpg.astype(float), kabs=np.full(len(ehr), 0.023),
                BW=ehr.weight_kg.values.astype(float), k_ex=np.full(len(ehr), POP_KEX))


def to_minutes(x5: np.ndarray, spread_carbs=False) -> np.ndarray:
    """5-min grid -> 1-min grid."""
    if spread_carbs:  # carbs logged at a 5-min slot are eaten over 15 min
        T, n = x5.shape
        out = np.zeros((T * STEP, n))
        for k in np.nonzero(x5.any(1))[0]:
            out[k * STEP: k * STEP + 15] += x5[k] / 15.0
        return out[: T * STEP]
    return np.repeat(x5, STEP, axis=0)


# --------------------------------------------------------------------------- 2. calibrate
def calibrate(ehr, arr, verbose=True) -> tuple[dict, pd.DataFrame]:
    prior = ehr_prior(ehr)
    n = len(ehr)
    n_cal = CAL_DAYS * 288
    cgm = arr["cgm_mgdl"][:n_cal]
    # data-driven basal glucose: median of CGM between 04:00 and 06:00 on onboarding nights
    hours = (np.arange(n_cal) * STEP / 60) % 24
    night = (hours >= 4) & (hours < 6)
    Gb = np.median(cgm[night], axis=0)
    carbs_m = to_minutes(arr["logged_carbs"][:n_cal], spread_carbs=True)
    act_m = to_minutes(arr["activity"][:n_cal])

    cand = [(a, b) for a in SI_GRID for b in GAMMA_GRID]
    C = len(cand)
    rep = lambda v: np.repeat(v, C)
    par = {k: rep(prior[k]) for k in prior}
    par["Gb"] = rep(Gb)
    par["SI"] = par["SI"] * np.tile([c[0] for c in cand], n)
    par["gamma"] = par["gamma"] * np.tile([c[1] for c in cand], n)
    G = simulate(par, np.repeat(carbs_m, C, axis=1), np.repeat(act_m, C, axis=1), record_every=STEP)
    G = G.reshape(n_cal, n, C)
    resid = G - cgm[:, :, None]
    # Huber loss: robust to glucose rises from meals the patient forgot to log
    d = 25.0
    hub = np.where(np.abs(resid) < d, 0.5 * resid ** 2, d * (np.abs(resid) - 0.5 * d))
    loss = hub[60:].mean(0)                        # skip first 5 h burn-in
    # MAP estimate: Gaussian prior on log-multipliers keeps the twin close to the EHR prior
    # unless the patient's own data clearly disagree (SI and gamma are partly confounded)
    logm = np.array([np.log(c[0]) ** 2 + np.log(c[1]) ** 2 for c in cand])
    loss = loss + PRIOR_W * logm[None, :]
    best = loss.argmin(1)
    fitted = dict(prior)
    fitted["Gb"] = Gb
    fitted["SI"] = prior["SI"] * np.array([cand[b][0] for b in best])
    fitted["gamma"] = prior["gamma"] * np.array([cand[b][1] for b in best])
    best_G = G[:, np.arange(n), best]
    rmse = np.sqrt(((best_G - cgm)[60:] ** 2).mean(0))
    prior_rmse = np.sqrt(((G[:, :, cand.index((1.0, 1.0))] - cgm)[60:] ** 2).mean(0))
    report = pd.DataFrame(dict(patient_id=ehr.patient_id, SI_prior=prior["SI"], SI_twin=fitted["SI"],
                               gamma_prior=prior["gamma"], gamma_twin=fitted["gamma"], Gb_twin=Gb,
                               rmse_prior=prior_rmse, rmse_calibrated=rmse))
    if verbose:
        print(f"calibration RMSE (open-loop, 3 days): prior {prior_rmse.mean():.1f} -> twin {rmse.mean():.1f} mg/dL")
    return fitted, report


# --------------------------------------------------------------------------- 3+4. synchronise + forecast
def habit_profile(arr, cal_slots: int) -> tuple[np.ndarray, np.ndarray]:
    """Per patient: probability of a meal starting in each 15-min slot of the day and typical carbs,
    learned from onboarding days (logged meals + CGM-detected rises)."""
    cgm = arr["cgm_mgdl"][:cal_slots]
    slope = np.vstack([np.zeros((3, cgm.shape[1])), cgm[3:] - cgm[:-3]]) / 15.0
    onset = (slope > 1.2) & (np.roll(slope, 3, axis=0) <= 1.2)
    logged = arr["logged_carbs"][:cal_slots] > 0
    raw = onset | logged
    # de-duplicate: one meal event per 45-min window (logged entry and its CGM rise are the same meal)
    ev = np.zeros_like(raw, dtype=float)
    for i in range(raw.shape[1]):
        last = -10 ** 6
        for k in np.nonzero(raw[:, i])[0]:
            if k - last > 9:
                ev[k, i] = 1.0
                last = k
    slot = (np.arange(cal_slots) * STEP // 15) % 96
    prof = np.zeros((96, cgm.shape[1]))
    for s in range(96):
        prof[s] = ev[slot == s].sum(0)
    # smooth +-45 min (kernel sums to 1) -> expected meal starts per 15-min slot per day
    k = np.array([0.25, 0.5, 0.75, 1, 0.75, 0.5, 0.25]); k = k / k.sum()
    prof = np.array([np.convolve(np.r_[prof[-3:, i], prof[:, i], prof[:3, i]], k, "valid") for i in range(prof.shape[1])]).T
    prof = np.clip(prof / CAL_DAYS, 0, 1)
    lc = arr["logged_carbs"][:cal_slots]
    typical = np.where((lc > 0).sum(0) > 0, lc.sum(0) / np.maximum((lc > 0).sum(0), 1), 60.0)
    return prof, typical


def run_twin(ehr, arr, fitted, verbose=True, save_states_at=()) -> dict:
    """Synchronise every twin with its patient over the whole monitoring period and
    produce 2-hour forecasts every 15 minutes. Fully vectorised across patients."""
    n = len(ehr)
    T = arr["cgm_mgdl"].shape[0]
    cal = CAL_DAYS * 288
    prof, typical = habit_profile(arr, cal)
    par = fitted
    vol = V_G * par["BW"]
    cgm = arr["cgm_mgdl"]
    state = dict(G=cgm[0].copy(), X=np.zeros(n), I=np.full(n, 10.0), Q1=np.zeros(n), Q2=np.zeros(n), E=np.zeros(n))
    twin_G = np.full((T, n), np.nan)
    detected = np.zeros((T, n))
    n_pred = T // (PRED_EVERY // STEP)
    fc_nomeal = np.full((n_pred, n), np.nan)
    fc_habit = np.full((n_pred, n), np.nan)
    fc_curve_mean = np.full((n_pred, n), np.nan)
    last_meal_k = np.full(n, -999)
    saved = {}
    for k in range(T):
        # 3a. inputs for the next 5 minutes
        carbs = arr["logged_carbs"][k].copy()
        last_meal_k = np.where(carbs > 0, k, last_meal_k)
        # 3b. unlogged-meal detector: sustained rise with no logged meal in last 45 min
        if k >= 3:
            slope = (cgm[k] - cgm[k - 3]) / 15.0
            resid = cgm[k] - state["G"]
            unl = (slope > 1.3) & (resid > 12) & (k - last_meal_k > 9)
            if unl.any():
                est = np.clip(resid * vol / (F_BIO * 1000) * 2.5, 15, 70)   # g carbs implied by the miss
                carbs = carbs + np.where(unl, est, 0)
                detected[k] = np.where(unl, est, 0)
                last_meal_k = np.where(unl, k, last_meal_k)
        c_m = np.zeros((STEP, n)); c_m[0] = carbs / 3; c_m[1] = carbs / 3; c_m[2] = carbs / 3
        a_m = np.tile(arr["activity"][k], (STEP, 1))
        _, state = simulate(par, c_m, a_m, state0=state, record_every=STEP, return_state=True)
        # 3c. observer correction toward measured CGM
        state["G"] = state["G"] + K_OBS * (cgm[k] - state["G"])
        twin_G[k] = state["G"]
        if k in save_states_at:
            saved[k] = {kk: v.copy() for kk, v in state.items()}
        # 4. forecast
        if k % (PRED_EVERY // STEP) == 0 and k >= cal - 1:
            j = k // (PRED_EVERY // STEP)
            act_now = np.tile(arr["activity"][max(0, k - 2):k + 1].mean(0), (HORIZON, 1)) * 0.5
            g0 = simulate(par, np.zeros((HORIZON, n)), act_now, state0=state, record_every=5)
            fc_nomeal[j] = g0.max(0)
            # habitual-meal scenario: expected carbs from the habit profile over the next 2 h
            slot_now = ((k + 1) * STEP // 15) % 96
            slots = (slot_now + np.arange(1, 7)) % 96
            p_meal = prof[slots]                                 # (6, n)
            exp_carbs = np.zeros((HORIZON, n))
            p_meal = p_meal * np.minimum(1.0, 1.0 / np.maximum(p_meal.sum(0), 1e-9))   # at most one meal in 2 h
            for s in range(6):
                exp_carbs[s * 15: s * 15 + 15] += (p_meal[s] * typical) / 15.0
            g1 = simulate(par, exp_carbs, act_now, state0=state, record_every=5)
            fc_habit[j] = g1.max(0)
            fc_curve_mean[j] = g1.mean(0)
    if verbose:
        err = (twin_G[cal:] - cgm[cal:])
        print(f"twin synchronisation residual (post-observer) MAE {np.nanmean(np.abs(err)):.1f} mg/dL; "
              f"unlogged meals detected: {(detected > 0).sum()}")
    return dict(twin_G=twin_G, detected=detected, fc_nomeal=fc_nomeal, fc_habit=fc_habit,
                fc_mean=fc_curve_mean, habit_prof=prof, typical_carbs=typical, states=saved)


# --------------------------------------------------------------------------- 5. what-if
def what_if(par_i: dict, state_i: dict, carbs_plan: np.ndarray, activity_plan: np.ndarray,
            si_mult: float = 1.0, gb_shift: float = 0.0) -> np.ndarray:
    """Counterfactual simulation for ONE patient. carbs_plan/activity_plan are 1-min arrays."""
    p = {k: np.atleast_1d(np.asarray(v, dtype=float)) for k, v in par_i.items()}
    p["SI"] = p["SI"] * si_mult
    p["Gb"] = p["Gb"] + gb_shift
    s = {k: np.atleast_1d(np.asarray(v, dtype=float)) for k, v in state_i.items()}
    return simulate(p, carbs_plan[:, None], activity_plan[:, None], state0=s, record_every=5)[:, 0]
