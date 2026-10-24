"""
physiology.py
-------------
Mechanistic glucose-insulin core of the GlucoTwin digital twin.

The model is an extended Bergman minimal model (Bergman 1979; Toffolo 1980)
with a two-compartment gut absorption model for meals (Dalla Man 2007, simplified)
and an exercise-driven insulin-independent uptake term (Roy & Parker 2007, simplified).

State per patient (all vectorised over patients / candidate parameter sets):
    G   plasma glucose                         [mg/dL]
    X   remote insulin action                  [1/min]
    I   plasma insulin above zero              [uU/mL]
    Q1  gut compartment 1 (stomach)            [mg]
    Q2  gut compartment 2 (intestine)          [mg]
    E   exercise effect (decays after activity)[1/min]

Equations (t in minutes):
    dG/dt  = -(SG + X + E) * G + SG * Gb + Ra / (V * BW) + EGPstress
    dX/dt  = -p2 * X + p2 * SI * (I - Ib)
    dI/dt  = -n * (I - Ib) + gamma * max(G - h, 0)
    dQ1/dt = -kabs * Q1 + carb_input_mg
    dQ2/dt =  kabs * (Q1 - Q2)
    Ra     =  f * kabs * Q2
    dE/dt  = -E / tau_ex + k_ex * activity

Everything is plain numpy so the same code is used for
(a) generating the synthetic cohort, (b) calibrating each patient's twin,
(c) the real-time state observer and (d) what-if simulation.
"""
from __future__ import annotations

import numpy as np

DT = 1.0  # integration step, minutes

# Population constants
P2 = 0.04          # 1/min, insulin action dynamics
N_CLEAR = 0.13      # 1/min, insulin clearance
H_THRESH = 90.0     # mg/dL, secretion threshold
V_G = 1.7           # dL/kg, glucose distribution volume
F_BIO = 0.9         # carb bioavailability
TAU_EX = 45.0       # min, persistence of exercise effect
IB = 10.0           # uU/mL basal insulin


def simulate(params: dict, carbs_g: np.ndarray, activity: np.ndarray,
             stress: np.ndarray | None = None, state0: dict | None = None,
             record_every: int = 1, return_state: bool = False):
    """Integrate the model.

    params  : dict of arrays shaped (P,) - SI, SG, Gb, gamma, kabs, BW, k_ex
    carbs_g : (T, P) grams of carbohydrate ingested in each minute
    activity: (T, P) activity intensity 0..1 (1 ~ brisk walking)
    stress  : (T, P) optional endogenous glucose production boost, mg/dL/min
    state0  : optional initial state dict of (P,) arrays
    Returns G recorded every `record_every` minutes, shape (T//record_every, P)
    """
    T, P = carbs_g.shape
    SI, SG, Gb = params["SI"], params["SG"], params["Gb"]
    gamma, kabs, BW, k_ex = params["gamma"], params["kabs"], params["BW"], params["k_ex"]

    if state0 is None:
        G = Gb.astype(float).copy()
        X = np.zeros(P); I = np.full(P, IB)
        Q1 = np.zeros(P); Q2 = np.zeros(P); E = np.zeros(P)
    else:
        G, X, I = state0["G"].copy(), state0["X"].copy(), state0["I"].copy()
        Q1, Q2, E = state0["Q1"].copy(), state0["Q2"].copy(), state0["E"].copy()

    out = np.empty((T // record_every, P))
    vol = V_G * BW
    for t in range(T):
        Ra = F_BIO * kabs * Q2                       # mg/min
        dG = -(SG + X + E) * G + SG * Gb + Ra / vol
        if stress is not None:
            dG = dG + stress[t]
        dX = -P2 * X + P2 * SI * (I - IB)
        dI = -N_CLEAR * (I - IB) + gamma * np.maximum(G - H_THRESH, 0.0)
        dQ1 = -kabs * Q1 + carbs_g[t] * 1000.0
        dQ2 = kabs * (Q1 - Q2)
        dE = -E / TAU_EX + k_ex * activity[t]

        G = np.maximum(G + DT * dG, 30.0)
        X = X + DT * dX
        I = np.maximum(I + DT * dI, 0.0)
        Q1 = Q1 + DT * dQ1
        Q2 = Q2 + DT * dQ2
        E = E + DT * dE
        if (t + 1) % record_every == 0:
            out[(t + 1) // record_every - 1] = G

    if return_state:
        return out, dict(G=G, X=X, I=I, Q1=Q1, Q2=Q2, E=E)
    return out


def step_state(state: dict, params: dict, carbs_g: np.ndarray, activity: np.ndarray,
               stress: np.ndarray | None, minutes: int) -> dict:
    """Advance a state dict by `minutes` with constant per-minute inputs (P,) arrays.
    Used by the real-time observer (5-min CGM cadence)."""
    T = minutes
    P = state["G"].shape[0]
    c = np.zeros((T, P)); c[0] = carbs_g
    a = np.tile(activity, (T, 1))
    s = None if stress is None else np.tile(stress, (T, 1))
    _, st = simulate(params, c, a, s, state0=state, record_every=T, return_state=True)
    return st
