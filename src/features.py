"""
features.py
-----------
Fuses the two data streams + the twin's own forecasts into one feature vector
per patient every 15 minutes, and builds the adverse-event label.

ADVERSE EVENT: post-prandial / stress glucose SPIKE = CGM rises above
180 mg/dL (ADA / International Consensus on Time-in-Range upper limit)
at any time in the next 120 minutes, while the patient is currently
<= 180 mg/dL (i.e. we predict the onset, not an ongoing excursion).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from twin_engine import CAL_DAYS, PRED_EVERY, STEP, HORIZON

SPIKE = 180.0
R = PRED_EVERY // STEP          # 3 CGM samples per prediction step
H = HORIZON // STEP             # 24 CGM samples in the horizon

FEATURE_GROUPS = {
    "CGM history": ["cgm_now", "slope_15", "slope_30", "slope_60", "accel", "mean_2h", "sd_2h", "max_2h", "min_2h",
                    "mean_24h", "tir_24h", "hrs_since_high"],
    "Wearables (HR, HRV, steps, sleep)": ["hr_now", "hr_delta", "hrv_30", "hrv_rel", "steps_30", "steps_120",
                                         "sleep_hrs_last_night", "deep_frac_last_night", "rem_frac_last_night",
                                         "night_hrv", "awake_now"],
    "Context & meal log": ["hour_sin", "hour_cos", "weekend", "logged_carbs_2h", "mins_since_logged_meal"],
    "EHR (static)": ["age", "bmi", "waist_cm", "hba1c_pct", "fasting_glucose_mgdl", "fasting_insulin_uU", "homa_ir",
                     "t2d_duration_yrs", "is_t2d", "is_prediabetes", "med_metformin", "med_sulfonylurea", "med_dpp4i",
                     "med_basal_insulin", "gene_TCF7L2_rs7903146", "gene_KCNQ1_rs2237892", "gene_FTO_rs9939609",
                     "egfr", "tg_mgdl", "hdl_mgdl", "sbp", "family_history_t2d"],
    "Digital twin": ["twin_fc_nomeal_max", "twin_fc_habit_max", "twin_fc_habit_mean", "twin_meal_prob_2h",
                     "twin_SI", "twin_gamma", "twin_unlogged_carbs_2h", "twin_residual"],
}


def _roll(x, w, fn):
    return getattr(pd.DataFrame(x).rolling(w, min_periods=1), fn)().values


def build(ehr, arr, times, twin, fitted) -> pd.DataFrame:
    cgm = arr["cgm_mgdl"]
    T, n = cgm.shape
    hr, hrv, steps, stage = arr["heart_rate_bpm"], arr["hrv_rmssd_ms"], arr["steps"], arr["sleep_stage"]
    asleep = stage > 0
    hours = (times.hour + times.minute / 60).values

    # rolling helpers (5-min grid)
    mean_2h, sd_2h = _roll(cgm, 24, "mean"), _roll(cgm, 24, "std")
    max_2h, min_2h = _roll(cgm, 24, "max"), _roll(cgm, 24, "min")
    mean_24h = _roll(cgm, 288, "mean")
    tir_24h = _roll(((cgm >= 70) & (cgm <= 180)).astype(float), 288, "mean")
    hr_30, hr_2h = _roll(hr, 6, "mean"), _roll(hr, 24, "mean")
    hrv_30 = _roll(hrv, 6, "mean")
    steps_30, steps_120 = _roll(steps, 6, "sum"), _roll(steps, 24, "sum")
    logged_2h = _roll(arr["logged_carbs"], 24, "sum")
    unlog_2h = _roll(twin["detected"], 24, "sum")
    resid = _roll(cgm - twin["twin_G"], 6, "mean")
    hrv_base = np.nanmedian(np.where(~asleep[: CAL_DAYS * 288], hrv[: CAL_DAYS * 288], np.nan), axis=0)

    # hours since last CGM>180 and minutes since last logged meal
    hs_high = np.zeros((T, n)); ms_meal = np.zeros((T, n))
    last_h = np.full(n, -10 ** 6); last_m = np.full(n, -10 ** 6)
    for k in range(T):
        last_h = np.where(cgm[k] > SPIKE, k, last_h)
        last_m = np.where(arr["logged_carbs"][k] > 0, k, last_m)
        hs_high[k] = np.minimum((k - last_h) * STEP / 60, 48)
        ms_meal[k] = np.minimum((k - last_m) * STEP, 1440)

    # last night's sleep summary (night ending on the current day, 20:00-11:00 window)
    day_idx = np.arange(T) // 288
    night_stats = {}
    for d in range(T // 288):
        lo, hi = max(0, d * 288 - 48), d * 288 + 132   # 20:00 prev day -> 11:00
        st = stage[lo:hi]
        sl = st > 0
        tot = sl.sum(0) * STEP / 60
        deep = (st == 2).sum(0) / np.maximum(sl.sum(0), 1)
        rem = (st == 3).sum(0) / np.maximum(sl.sum(0), 1)
        nh = np.nanmean(np.where(sl, hrv[lo:hi], np.nan), axis=0)
        night_stats[d] = (tot, deep, rem, nh)

    e = ehr.copy()
    e["homa_ir"] = e.fasting_glucose_mgdl * e.fasting_insulin_uU / 405
    e["is_t2d"] = (e.cohort_group == "T2D").astype(int)
    e["is_prediabetes"] = (e.cohort_group == "Prediabetes").astype(int)
    static_cols = FEATURE_GROUPS["EHR (static)"]
    static = e[static_cols].values

    rows = []
    start = CAL_DAYS * 288           # aligned with run_twin forecasts (k % R == 0)
    for k in range(start, T, R):
        j = k // R
        d = day_idx[k]
        tot, deep, rem, nh = night_stats[d]
        has_future = k + H < T
        future_max = cgm[k + 1: k + 1 + H].max(0) if has_future else np.full(n, np.nan)
        f = dict(
            patient_idx=np.arange(n), k=np.full(n, k), day=np.full(n, d),
            cgm_now=cgm[k], slope_15=(cgm[k] - cgm[k - 3]) / 15, slope_30=(cgm[k] - cgm[k - 6]) / 30,
            slope_60=(cgm[k] - cgm[k - 12]) / 60,
            accel=((cgm[k] - cgm[k - 3]) - (cgm[k - 3] - cgm[k - 6])) / 15,
            mean_2h=mean_2h[k], sd_2h=sd_2h[k], max_2h=max_2h[k], min_2h=min_2h[k], mean_24h=mean_24h[k],
            tir_24h=tir_24h[k], hrs_since_high=hs_high[k],
            hr_now=hr_30[k], hr_delta=hr_30[k] - hr_2h[k], hrv_30=hrv_30[k], hrv_rel=hrv_30[k] / hrv_base,
            steps_30=steps_30[k], steps_120=steps_120[k], sleep_hrs_last_night=tot, deep_frac_last_night=deep,
            rem_frac_last_night=rem, night_hrv=nh, awake_now=(~asleep[k]).astype(int),
            hour_sin=np.full(n, np.sin(2 * np.pi * hours[k] / 24)), hour_cos=np.full(n, np.cos(2 * np.pi * hours[k] / 24)),
            weekend=np.full(n, int(times[k].weekday() >= 5)), logged_carbs_2h=logged_2h[k], mins_since_logged_meal=ms_meal[k],
            twin_fc_nomeal_max=twin["fc_nomeal"][j], twin_fc_habit_max=twin["fc_habit"][j],
            twin_fc_habit_mean=twin["fc_mean"][j],
            twin_meal_prob_2h=twin["habit_prof"][((k + 1) * STEP // 15 + np.arange(1, 9)) % 96].sum(0),
            twin_SI=fitted["SI"] * 1e4, twin_gamma=fitted["gamma"], twin_unlogged_carbs_2h=unlog_2h[k],
            twin_residual=resid[k],
            future_max=future_max,
            label=((future_max > SPIKE) & (cgm[k] <= SPIKE)).astype(int) if has_future else np.full(n, -1),
            eligible=(cgm[k] <= SPIKE).astype(int),
        )
        df = pd.DataFrame(f)
        df[static_cols] = static
        rows.append(df)
    out = pd.concat(rows, ignore_index=True)
    out["patient_id"] = ehr.patient_id.values[out.patient_idx]
    out["timestamp"] = times[out.k.values]
    return out
