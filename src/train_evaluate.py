"""
train_evaluate.py
-----------------
Trains the 2-hour glucose-spike predictor and evaluates it on patients the
model has never seen (patient-level hold-out = "new patient onboarded to the
clinic"). Runs an ablation that shows what each data stream - and the digital
twin itself - adds.

Models
  M0  Rule baseline     : CGM > 140 and rising > 1 mg/dL/min
  M1  CGM only          : gradient-boosted trees on CGM history
  M2  + wearables       : + HR, HRV, steps, sleep, context
  M3  + EHR             : + static clinical record   (= plain data fusion)
  M4  GlucoTwin (full)  : + digital-twin forecasts & personalised parameters
"""
from __future__ import annotations

import json
import os
import pickle

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score, roc_curve, precision_recall_curve
from sklearn.model_selection import train_test_split

from features import FEATURE_GROUPS, H, R

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "outputs")
FIG = os.path.join(OUT, "figures")


def feature_sets():
    g = FEATURE_GROUPS
    m1 = g["CGM history"]
    m2 = m1 + g["Wearables (HR, HRV, steps, sleep)"] + g["Context & meal log"]
    m3 = m2 + g["EHR (static)"]
    m4 = m3 + g["Digital twin"]
    return {"M1 CGM only": m1, "M2 + wearables & context": m2, "M3 + EHR (data fusion)": m3, "M4 GlucoTwin (full)": m4}


def make_model(seed=0):
    return HistGradientBoostingClassifier(max_iter=400, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=80,
                                          l2_regularization=1.0, early_stopping=True, validation_fraction=0.12,
                                          random_state=seed)


def event_metrics(df: pd.DataFrame, prob: np.ndarray, thr: float, cgm: np.ndarray):
    """Clinical view: per spike EPISODE (CGM crossing 180 mg/dL from below), was the patient
    alerted in the 2 h beforehand, how early, and how many false alarms per patient-day?"""
    d = df[["patient_idx", "k", "label"]].copy()
    d["alert"] = prob >= thr
    caught, leads, n_events, false_alerts, days = 0, [], 0, 0, 0.0
    for pid, g in d.groupby("patient_idx"):
        g = g.sort_values("k")
        kmin, kmax = g.k.min(), g.k.max()
        days += (kmax - kmin) / 288
        c = cgm[:, pid]
        ks = np.arange(kmin + H, kmax + 1)
        onsets = ks[(c[ks] > 180) & (c[ks - 1] <= 180)]
        # merge crossings within 30 min of a previous one (sensor noise) into one episode
        keep, last = [], -10 ** 9
        for o in onsets:
            if o - last > 6:
                keep.append(o)
            last = o
        al = g[g.alert].k.values
        for o in keep:
            n_events += 1
            w = al[(al < o) & (al >= o - H)]
            if len(w):
                caught += 1
                leads.append((o - w.min()) * 5)
        fa = g[g.alert & (g.label == 0)].k.values
        last = -10 ** 9
        for kk in fa:
            if kk - last >= H:
                false_alerts += 1
                last = kk
    return dict(events=n_events, event_sensitivity=caught / max(n_events, 1),
                median_lead_min=float(np.median(leads)) if leads else 0.0,
                false_alerts_per_patient_day=false_alerts / max(days, 1e-9))


def run(df: pd.DataFrame, ehr: pd.DataFrame, cgm: np.ndarray):
    os.makedirs(FIG, exist_ok=True)
    data = df[(df.eligible == 1) & (df.label >= 0)].reset_index(drop=True)
    pats = ehr.patient_id.values
    tr_p, te_p = train_test_split(pats, test_size=0.3, random_state=7, stratify=ehr.cohort_group.values)
    tr = data[data.patient_id.isin(tr_p)].reset_index(drop=True)
    te = data[data.patient_id.isin(te_p)].reset_index(drop=True)
    print(f"samples train {len(tr):,} ({len(tr_p)} pts)  test {len(te):,} ({len(te_p)} pts)  "
          f"spike prevalence {data.label.mean():.3f}")

    results, models, probs = {}, {}, {}
    # M0 rule baseline
    rule = ((te.cgm_now > 140) & (te.slope_15 > 1.0)).astype(float).values
    results["M0 Rule (CGM>140 & rising)"] = dict(
        auroc=roc_auc_score(te.label, rule), auprc=average_precision_score(te.label, rule),
        brier=brier_score_loss(te.label, rule), **event_metrics(te, rule, 0.5, cgm))
    probs["M0 Rule (CGM>140 & rising)"] = rule

    for name, cols in feature_sets().items():
        m = make_model()
        m.fit(tr[cols], tr.label)
        p = m.predict_proba(te[cols])[:, 1]
        # operating threshold chosen on TRAINING data: 80% sample-level sensitivity
        ptr = m.predict_proba(tr[cols])[:, 1]
        fpr, tpr, th = roc_curve(tr.label, ptr)
        thr = float(th[np.argmax(tpr >= 0.80)])
        results[name] = dict(auroc=roc_auc_score(te.label, p), auprc=average_precision_score(te.label, p),
                             brier=brier_score_loss(te.label, p), threshold=thr, **event_metrics(te, p, thr, cgm))
        models[name] = (m, cols, thr)
        probs[name] = p
        print(f"{name:28s} AUROC {results[name]['auroc']:.3f}  AUPRC {results[name]['auprc']:.3f}  "
              f"event-sens {results[name]['event_sensitivity']:.2f}  lead {results[name]['median_lead_min']:.0f} min  "
              f"FA/pt-day {results[name]['false_alerts_per_patient_day']:.2f}")

    full_name = "M4 GlucoTwin (full)"
    m, cols, thr = models[full_name]

    # subgroup performance
    te_g = te.merge(ehr[["patient_id", "cohort_group"]], on="patient_id")
    sub = {}
    for g, idx in te_g.groupby("cohort_group").groups.items():
        y = te_g.loc[idx, "label"]
        if y.nunique() > 1:
            sub[g] = dict(n=int(len(idx)), auroc=float(roc_auc_score(y, probs[full_name][idx])),
                          prevalence=float(y.mean()))
    # group permutation importance on test set
    rng = np.random.default_rng(0)
    base = roc_auc_score(te.label, m.predict_proba(te[cols])[:, 1])
    gimp = {}
    for g, gcols in FEATURE_GROUPS.items():
        drops = []
        for rep in range(3):
            X = te[cols].copy()
            perm = rng.permutation(len(X))
            X[gcols] = X[gcols].values[perm]
            drops.append(base - roc_auc_score(te.label, m.predict_proba(X)[:, 1]))
        gimp[g] = float(np.mean(drops))
    # top single features
    fimp = {}
    for c in cols:
        X = te[cols].copy()
        X[c] = X[c].values[rng.permutation(len(X))]
        fimp[c] = base - roc_auc_score(te.label, m.predict_proba(X)[:, 1])
    top_feats = dict(sorted(fimp.items(), key=lambda kv: -kv[1])[:15])

    metrics = dict(task="Predict CGM > 180 mg/dL within the next 120 min (onset), 15-min cadence",
                   n_patients=int(len(pats)), n_train_patients=int(len(tr_p)), n_test_patients=int(len(te_p)),
                   n_train_samples=int(len(tr)), n_test_samples=int(len(te)), prevalence=float(data.label.mean()),
                   models=results, subgroups_full_model=sub, group_importance_auroc_drop=gimp,
                   top_features_auroc_drop=top_feats, test_patients=list(map(str, te_p)))
    with open(os.path.join(OUT, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2, default=float)
    with open(os.path.join(OUT, "glucotwin_model.pkl"), "wb") as f:
        pickle.dump(dict(model=m, features=cols, threshold=thr, train_medians=tr[cols].median().to_dict()), f)
    te_out = te[["patient_id", "timestamp", "k", "cgm_now", "future_max", "label"]].copy()
    te_out["risk"] = probs[full_name]
    te_out["alert"] = te_out.risk >= thr
    te_out.to_csv(os.path.join(OUT, "test_predictions.csv.gz"), index=False, compression="gzip")

    make_figures(te, probs, results, gimp)
    return metrics, models, te


def make_figures(te, probs, results, gimp):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    colors = {"M0 Rule (CGM>140 & rising)": "#9AA0A6", "M1 CGM only": "#7FB3D5", "M2 + wearables & context": "#5499C7",
              "M3 + EHR (data fusion)": "#2471A3", "M4 GlucoTwin (full)": "#E4572E"}
    fig, ax = plt.subplots(1, 2, figsize=(12, 5))
    for name, p in probs.items():
        if name.startswith("M0"):
            continue
        fpr, tpr, _ = roc_curve(te.label, p)
        ax[0].plot(fpr, tpr, color=colors[name], lw=2.6 if "M4" in name else 1.6, label=f"{name} ({results[name]['auroc']:.3f})")
        pr, rc, _ = precision_recall_curve(te.label, p)
        ax[1].plot(rc, pr, color=colors[name], lw=2.6 if "M4" in name else 1.6, label=f"{name} ({results[name]['auprc']:.3f})")
    ax[0].plot([0, 1], [0, 1], ls="--", c="#ccc")
    ax[0].set(xlabel="False positive rate", ylabel="True positive rate", title="ROC - held-out patients")
    ax[1].axhline(te.label.mean(), ls="--", c="#ccc")
    ax[1].set(xlabel="Recall", ylabel="Precision", title="Precision-Recall - held-out patients")
    ax[0].legend(fontsize=9, loc="lower right"); ax[1].legend(fontsize=9, loc="upper right")
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "roc_pr_ablation.png"), dpi=170); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 5))
    pt, pp = calibration_curve(te.label, probs["M4 GlucoTwin (full)"], n_bins=10, strategy="quantile")
    ax.plot([0, 1], [0, 1], ls="--", c="#ccc"); ax.plot(pp, pt, "o-", c="#E4572E", lw=2)
    ax.set(xlabel="Predicted spike probability", ylabel="Observed frequency", title="Calibration - GlucoTwin")
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "calibration.png"), dpi=170); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.5, 4))
    items = sorted(gimp.items(), key=lambda kv: kv[1])
    ax.barh([k for k, _ in items], [v for _, v in items], color=["#E4572E" if "twin" in k.lower() else "#2471A3" for k, _ in items])
    ax.set(xlabel="Drop in AUROC when stream is shuffled", title="What each data stream contributes")
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "stream_importance.png"), dpi=170); plt.close(fig)
