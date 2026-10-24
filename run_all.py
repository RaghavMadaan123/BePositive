"""
GlucoTwin - end-to-end pipeline.

    python run_all.py            # generate data -> calibrate twins -> train -> evaluate -> export dashboard

Takes ~2-3 minutes on a laptop CPU. Outputs land in data/, outputs/ and dashboard/data.js
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

import generate_data
import twin_engine
import features
import train_evaluate
import export_dashboard


def main():
    t0 = time.time()
    print("[1/5] Generating synthetic EHR + wearable cohort ...")
    generate_data.run()
    print("[2/5] Initialising and calibrating one digital twin per patient ...")
    ehr, arr, times, meals = twin_engine.load()
    fitted, cal_report = twin_engine.calibrate(ehr, arr)
    cal_report.to_csv(os.path.join(twin_engine.ROOT, "outputs", "twin_calibration.csv"), index=False)
    print("[3/5] Synchronising twins with live streams and forecasting 2 h ahead ...")
    twin = twin_engine.run_twin(ehr, arr, fitted, save_states_at={export_dashboard.WHATIF_K})
    print("[4/5] Fusing features, training and evaluating the spike predictor ...")
    df = features.build(ehr, arr, times, twin, fitted)
    metrics, models, te = train_evaluate.run(df, ehr, arr["cgm_mgdl"])
    print("[5/5] Exporting doctor dashboard data ...")
    export_dashboard.run(ehr, arr, times, twin, fitted, df, models, metrics, cal_report)
    print(f"Done in {time.time() - t0:.0f}s. Open dashboard/index.html in a browser.")


if __name__ == "__main__":
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs"), exist_ok=True)
    main()
