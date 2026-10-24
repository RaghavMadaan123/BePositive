"""Quick sanity checks: python tests/test_smoke.py (run after run_all.py)."""
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from physiology import simulate  # noqa: E402


def test_meal_raises_glucose_and_walk_lowers_peak():
    T = 360
    par = dict(SI=np.array([4.8e-4]), SG=np.array([0.0105]), Gb=np.array([115.0]), gamma=np.array([0.045]),
               kabs=np.array([0.023]), BW=np.array([70.0]), k_ex=np.array([1.6e-4]))
    carbs = np.zeros((T, 1)); carbs[30:45] = 75 / 15
    still = simulate(par, carbs, np.zeros((T, 1)))[:, 0]
    act = np.zeros((T, 1)); act[60:90] = 0.9
    walk = simulate(par, carbs, act)[:, 0]
    assert still.max() > 180, "75 g meal should spike a T2D twin"
    assert walk.max() < still.max(), "post-meal walk should lower the peak"
    assert abs(still[-1] - 115) < 25, "glucose should return toward basal"


def test_outputs_exist_and_twin_beats_fusion():
    m = json.load(open(os.path.join(ROOT, "outputs", "metrics.json")))
    full, fusion = m["models"]["M4 GlucoTwin (full)"], m["models"]["M3 + EHR (data fusion)"]
    assert full["auroc"] > 0.85
    assert full["auroc"] >= fusion["auroc"]
    assert os.path.exists(os.path.join(ROOT, "dashboard", "data.js"))
    assert os.path.exists(os.path.join(ROOT, "data", "ehr_patients.csv"))


if __name__ == "__main__":
    test_meal_raises_glucose_and_walk_lowers_peak()
    test_outputs_exist_and_twin_beats_fusion()
    print("all smoke tests passed")
