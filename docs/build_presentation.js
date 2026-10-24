const pptxgen = require("pptxgenjs");
// applyTheme comes from the pptx skill used to build this deck; optional
let applyTheme = async () => {}; try { ({ applyTheme } = require("./apply_theme.js")); } catch (e) {}
const DOCS = __dirname + "/";

const OUT = DOCS + "GlucoTwin_Presentation.pptx";

const THEME = {
  name: "GlucoTwin", headFontFace: "Calibri", bodyFontFace: "Calibri",
  colors: { dk1: "14212B", lt1: "FFFFFF", dk2: "0B3C49", lt2: "EEF3F5",
    accent1: "0E7C86", accent2: "7A5AF8", accent3: "D64933", accent4: "E8A33D", accent5: "2E9E6A", accent6: "5D6B78",
    hlink: "0E7C86", folHlink: "7A5AF8" },
};
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "GlucoTwin - Digital Twin Challenge 2026";
pres.author = "Team GlucoTwin, IIM Kozhikode";
const C = pres.SchemeColor;
const W = 10, H = 5.625;

// ---------- layouts ----------
pres.defineSlideMaster({ title: "DARK", background: { color: THEME.colors.dk2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 1.55, w: 8.8, h: 1.3, fontSize: 40, bold: true, color: C.background1, valign: "top", align: "left" }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.6, y: 2.95, w: 8.2, h: 1.0, fontSize: 18, color: "CFE6EA", valign: "top" }, text: "" } },
  ] });
pres.defineSlideMaster({ title: "CONTENT", background: { color: THEME.colors.lt1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.28, w: 9.0, h: 0.7, fontSize: 28, bold: true, color: C.text1, valign: "middle", align: "left" }, text: "" } },
    { text: { text: "GlucoTwin · Digital Twin Challenge 2026", options: { x: 0.5, y: 5.22, w: 5, h: 0.28, fontSize: 9, color: "8A97A3" } } },
  ],
  slideNumber: { x: 9.1, y: 5.22, w: 0.4, h: 0.28, fontSize: 9, color: "8A97A3", align: "right" } });

function slide(master, section) { return pres.addSlide({ masterName: master, sectionTitle: section }); }
function txt(s, t, o) { s.addText(t, Object.assign({ isTextBox: true, fontSize: 14, color: C.text1, margin: 0, valign: "top" }, o)); }
function card(s, x, y, w, h, fill, name) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { color: fill }, objectName: name });
}
function badge(s, x, y, label, fill) {
  s.addShape(pres.shapes.OVAL, { x, y, w: 0.42, h: 0.42, fill: { color: fill }, line: { color: fill } });
  s.addText(label, { isTextBox: true, x, y, w: 0.42, h: 0.42, fontSize: 13, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0 });
}
function stat(s, x, y, w, big, label, color) {
  txt(s, big, { x, y, w, h: 0.75, fontSize: 40, bold: true, color });
  txt(s, label, { x, y: y + 0.78, w, h: 0.6, fontSize: 12, color: "5D6B78" });
}

// ================= 1. Title =================
pres.addSection({ title: "Opening" });
let s = slide("DARK", "Opening");
s.addText("GlucoTwin", { placeholder: "title" });
s.addText("A personal digital twin that sees a Type 2 Diabetes glucose spike two hours before it happens", { placeholder: "body" });
txt(s, "Be Positive · IIM Kozhikode\nDigital Twin Challenge 2026 · Happiest Health · Reimagining & Reforming Healthcare in India Summit", { x: 0.6, y: 4.35, w: 8.5, h: 0.7, fontSize: 12, color: "9FC3CA" });
s.addShape(pres.shapes.OVAL, { x: 8.05, y: 0.45, w: 1.4, h: 1.4, fill: { color: THEME.colors.accent2 }, line: { color: THEME.colors.accent2 } });
s.addText("GT", { isTextBox: true, x: 8.05, y: 0.45, w: 1.4, h: 1.4, fontSize: 34, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0 });
s.addNotes(`Hello, and thank you to the Happiest Health jury for this opportunity. We are [team name] from IIM Kozhikode, and our project is GlucoTwin.

In one sentence: GlucoTwin is a personal digital twin for people living with Type 2 Diabetes. It fuses a patient's electronic health record with the live stream from their wearables and continuous glucose monitor, keeps a virtual copy of that patient's glucose physiology running in sync, and uses it to warn the patient and their doctor about a glucose spike roughly an hour and a half before it happens, while there is still time to do something about it.

Over the next twenty minutes we will cover the problem and why India specifically needs proactive diabetes care, how we chose a narrow but high-value adverse event, the two data streams and how we handled the data-privacy sandbox rules, the architecture of the twin, the results on patients the model had never seen, and then a live walkthrough of the doctor dashboard, including the what-if simulator. We will close with limitations, governance, and how this could be piloted inside Happiest Health's clinic network.

Everything you will see runs from a single public GitHub repository with one command, python run_all.py, on synthetic data only.`);

// ================= 2. Problem =================
pres.addSection({ title: "Problem" });
s = slide("CONTENT", "Problem");
s.addText("India's diabetes care is still reactive", { placeholder: "title" });
stat(s, 0.5, 1.2, 2.8, "101 M", "Indians living with diabetes (ICMR-INDIAB, Lancet D&E 2023)", THEME.colors.accent3);
stat(s, 3.55, 1.2, 2.8, "136 M", "more with prediabetes, the pipeline of tomorrow's patients", THEME.colors.accent1);
stat(s, 6.6, 1.2, 2.9, "~3 / yr", "typical HbA1c checks: a 90-day average that hides daily spikes", THEME.colors.accent2);
card(s, 0.5, 3.0, 9.0, 1.95, THEME.colors.lt2, "problem-card");
txt(s, [
  { text: "The gap: ", options: { bold: true } },
  { text: "post-meal glucose spikes drive vascular damage and HbA1c, but they happen between clinic visits. CGMs and smartwatches now generate the data, yet they only show what already happened; the patient learns about a spike after it peaks.", options: {} },
], { x: 0.75, y: 3.18, w: 8.5, h: 0.95, fontSize: 14 });
txt(s, [
  { text: "What a clinician needs: ", options: { bold: true, color: THEME.colors.accent1 } },
  { text: "a warning early enough to act (portion, walk, medication), personalised to this patient's physiology, explained in plain terms, and with few false alarms.", options: {} },
], { x: 0.75, y: 4.1, w: 8.5, h: 0.75, fontSize: 14 });
s.addNotes(`Let us start with the problem. According to the ICMR-INDIAB study published in The Lancet Diabetes and Endocrinology in 2023, India has around 101 million people living with diabetes and another 136 million with prediabetes. That second number matters: it is the pipeline of tomorrow's patients, and it is where prevention has the highest return.

Yet the way we manage diabetes is largely reactive. A typical patient gets an HbA1c test a few times a year. HbA1c is a 90-day average. It is a valuable number, but it hides exactly the thing that does damage day to day: the sharp glucose spikes after meals, especially the carbohydrate-heavy meals and late dinners that are common in Indian diets.

Continuous glucose monitors and smartwatches have changed the data situation. A patient can now have a glucose reading every five minutes, plus heart rate, heart rate variability, sleep and steps. But these devices are rear-view mirrors. They tell you that you spiked, after you have spiked.

What a clinician actually needs is different. They need a warning early enough to act, whether that is a smaller portion, a walk after the meal, or a medication check. It has to be personalised, because two patients eating the same thali respond very differently. It has to be explainable, so the doctor trusts it. And it must not cry wolf, because alert fatigue kills adoption. Those four requirements, early, personal, explainable and low false alarms, shaped every design decision you will see.`);

// ================= 3. Why a twin =================
s = slide("CONTENT", "Problem");
s.addText("Why a digital twin, not just another ML model", { placeholder: "title" });
const cols = [
  { h: "Pure ML", c: THEME.colors.accent6, b: "Learns correlations from data. Strong with lots of data, but a black box, cannot answer \"what if she walks after dinner?\" and degrades for unusual patients." },
  { h: "Pure physiology", c: THEME.colors.accent6, b: "Equations of glucose and insulin. Explainable and can simulate interventions, but generic parameters fit real patients poorly and ignore context such as sleep and stress." },
  { h: "GlucoTwin = hybrid", c: THEME.colors.accent2, b: "A physiological model personalised to each patient and kept in sync with live data, whose forecasts feed an ML risk layer. Accurate, explainable, and able to run counterfactuals." },
];
cols.forEach((k, i) => {
  const x = 0.5 + i * 3.05;
  card(s, x, 1.2, 2.85, 3.0, i === 2 ? "F2EFFF" : THEME.colors.lt2, "col-" + i);
  badge(s, x + 0.25, 1.42, String(i + 1), k.c);
  txt(s, k.h, { x: x + 0.8, y: 1.45, w: 1.95, h: 0.4, fontSize: 17, bold: true, color: i === 2 ? THEME.colors.accent2 : C.text1 });
  txt(s, k.b, { x: x + 0.25, y: 2.05, w: 2.4, h: 2.0, fontSize: 13 });
});
txt(s, [{ text: "Design principle: ", options: { bold: true } }, { text: "the twin is the patient's virtual copy; the ML layer is the alarm that listens to it.", options: { italic: true } }],
  { x: 0.5, y: 4.45, w: 9.0, h: 0.5, fontSize: 14, color: THEME.colors.dk2 });
s.addNotes(`Why a digital twin and not simply another machine-learning model? There are two traditional ways to forecast glucose.

The first is pure machine learning: feed lots of CGM history into a model and let it learn the patterns. This works well when you have abundant data, but it is a black box. More importantly, it cannot answer causal questions. If a doctor asks, what happens if this patient walks for fifteen minutes after dinner, a pure ML model has no way to answer, because it has never been told how exercise acts on glucose.

The second is pure physiology: the differential equations that describe how glucose is absorbed from the gut, how insulin is secreted, and how insulin drives glucose into tissue. These models are explainable and they can simulate interventions. But with textbook parameters they fit real individuals poorly, and they know nothing about context such as a bad night's sleep or a stressful day.

GlucoTwin is a hybrid, and this is the core idea of the project. We take a physiological model, personalise its parameters to each patient using their EHR and their first three days of data, and keep it synchronised with every new CGM reading. That synchronised virtual patient produces forecasts and personalised parameters, and those become inputs to a machine-learning risk layer that also sees the raw wearable and EHR data.

A simple way to remember it: the twin is the patient's virtual copy, and the ML layer is the alarm that listens to it. You will see in the results that adding the twin improves accuracy and cuts false alarms compared with plain data fusion.`);

// ================= 4. Use case =================
s = slide("CONTENT", "Problem");
s.addText("Scope: one condition, one adverse event, one decision", { placeholder: "title" });
card(s, 0.5, 1.2, 4.3, 3.75, THEME.colors.lt2, "usecase");
txt(s, "Use case", { x: 0.75, y: 1.38, w: 3.8, h: 0.35, fontSize: 13, bold: true, color: THEME.colors.accent1 });
txt(s, [
  { text: "Condition: Type 2 Diabetes and prediabetes", options: { bullet: true, breakLine: true } },
  { text: "Patient: adult with a CGM + smartwatch, managed in an outpatient / clinic model", options: { bullet: true, breakLine: true } },
  { text: "User: treating doctor or diabetes educator; nudges reach the patient", options: { bullet: true, breakLine: true } },
  { text: "Decision supported: intervene before the meal or right after it", options: { bullet: true } },
], { x: 0.75, y: 1.8, w: 3.85, h: 2.9, fontSize: 14, paraSpaceAfter: 8 });
card(s, 5.1, 1.2, 4.4, 3.75, "FCEDEA", "event");
txt(s, "Adverse event predicted", { x: 5.35, y: 1.38, w: 4.0, h: 0.35, fontSize: 13, bold: true, color: THEME.colors.accent3 });
txt(s, "CGM glucose > 180 mg/dL\nwithin the next 120 minutes", { x: 5.35, y: 1.8, w: 4.0, h: 0.9, fontSize: 20, bold: true, color: C.text1 });
txt(s, [
  { text: "180 mg/dL = upper limit of the international time-in-range consensus", options: { bullet: true, breakLine: true } },
  { text: "Predicted only while the patient is still ≤ 180, so every alert is a genuine early warning", options: { bullet: true, breakLine: true } },
  { text: "Risk refreshed every 15 minutes", options: { bullet: true } },
], { x: 5.35, y: 2.8, w: 3.95, h: 2.0, fontSize: 13, paraSpaceAfter: 6 });
s.addNotes(`The challenge brief rightly says a whole-body twin is out of scope, and asks teams to pick one condition and one localised outcome. We chose Type 2 Diabetes and prediabetes, because of the scale we just saw and because the CGM signal makes outcomes measurable.

Our persona is an adult with a CGM and a smartwatch who is managed in an outpatient or clinic model, which maps directly onto Happiest Health's away-from-the-hospital clinic approach. The primary user is the treating doctor or a diabetes educator, and the nudges reach the patient through their app.

The adverse event is precise. We predict that CGM glucose will cross 180 milligrams per decilitre at any point in the next 120 minutes. 180 is the upper bound of the internationally agreed time-in-range target. Two details make this honest. First, we only make a prediction while the patient is still at or below 180, so we are predicting the onset of a spike, not detecting one that has already started. That rules out the trivial trick of flagging people who are already high. Second, the risk is refreshed every fifteen minutes, so it behaves like a live early-warning score.

This is exactly the example in the challenge brief, predicting a glucose spike two hours in advance, and we took it seriously as a clinical product rather than only a modelling exercise.`);

// ================= 5. Data =================
pres.addSection({ title: "Solution" });
s = slide("CONTENT", "Solution");
s.addText("Two data streams, fully synthetic and privacy-safe", { placeholder: "title" });
card(s, 0.5, 1.15, 4.4, 2.75, "E9F6F7", "ehr");
badge(s, 0.72, 1.33, "E", THEME.colors.accent1);
txt(s, "Static / historical: EHR", { x: 1.27, y: 1.4, w: 3.5, h: 0.35, fontSize: 16, bold: true, color: THEME.colors.accent1 });
txt(s, [
  { text: "Demographics, BMI, waist, BP", options: { bullet: true, breakLine: true } },
  { text: "ICD-10 diagnoses (E11.9, R73.03, I10)", options: { bullet: true, breakLine: true } },
  { text: "LOINC labs: HbA1c, fasting glucose & insulin, lipids, eGFR", options: { bullet: true, breakLine: true } },
  { text: "Medications: metformin, SU, DPP-4i, insulin", options: { bullet: true, breakLine: true } },
  { text: "Genetic markers: TCF7L2, KCNQ1, FTO", options: { bullet: true } },
], { x: 0.75, y: 1.9, w: 4.0, h: 1.95, fontSize: 13, paraSpaceAfter: 3 });
card(s, 5.1, 1.15, 4.4, 2.75, "EAF2FB", "wear");
badge(s, 5.32, 1.33, "W", "3B82C4");
txt(s, "Dynamic / real-time: wearables", { x: 5.87, y: 1.4, w: 3.5, h: 0.35, fontSize: 16, bold: true, color: "3B82C4" });
txt(s, [
  { text: "CGM glucose every 5 min", options: { bullet: true, breakLine: true } },
  { text: "Heart rate and HRV (RMSSD)", options: { bullet: true, breakLine: true } },
  { text: "Step count", options: { bullet: true, breakLine: true } },
  { text: "Sleep stages: wake / light / deep / REM", options: { bullet: true, breakLine: true } },
  { text: "Patient's own meal log: incomplete & noisy", options: { bullet: true } },
], { x: 5.35, y: 1.9, w: 4.0, h: 1.95, fontSize: 13, paraSpaceAfter: 3 });
stat(s, 0.5, 4.05, 2.2, "100", "synthetic patients", THEME.colors.dk2);
stat(s, 2.75, 4.05, 2.2, "14 days", "per patient, 5-min data", THEME.colors.dk2);
stat(s, 5.0, 4.05, 2.2, "403 k", "CGM + wearable rows", THEME.colors.dk2);
stat(s, 7.25, 4.05, 2.3, "0", "real patient records", THEME.colors.accent3);
s.addNotes(`Now the data. The challenge requires a fusion of two streams, and the sandbox rules require anonymised, open-source or synthetic data because of the DPDP Act and HIPAA. We built our own Synthea-style generator, and we want to explain why that is a strength rather than a shortcut.

The static stream is the EHR: demographics, BMI, waist and blood pressure; diagnoses coded in ICD-10; lab results coded in LOINC, including HbA1c, fasting glucose, fasting insulin, lipids and kidney function; medications; and genetic markers. We included TCF7L2, KCNQ1 and FTO risk alleles at frequencies reported for South Asian populations, because TCF7L2 in particular affects insulin secretion. Every patient is also exported as an HL7 FHIR R4 bundle, so the pipeline is interoperable and ABDM-ready.

The dynamic stream mimics a CGM and a smartwatch: glucose every five minutes, heart rate, HRV, steps, and sleep stages. We also added the patient's own meal log, deliberately incomplete and noisy, because in real life patients forget to log meals and misjudge carbs.

The key design choice is that the data is generated by physiology, not by random noise. Each synthetic patient has hidden physiology, such as insulin sensitivity and beta-cell function, derived from their profile. The cohort reflects the thin-fat Asian Indian phenotype, carbohydrate-heavy meals, late dinners, and the fact that a short or poor night's sleep reduces insulin sensitivity the next day. The EHR is consistent with the glucose traces: HbA1c is computed from each patient's simulated glucose.

In total: 100 patients, 14 days each, over 400,000 rows of five-minute data, and zero real patient records. Because we control the ground truth, we can also verify whether the twin recovers each patient's true physiology, which you cannot do with real data. The generator can be swapped for MIMIC-IV, Synthea output, or the OhioT1DM CGM dataset through the same loader.`);

// ================= 6. Architecture =================
s = slide("CONTENT", "Solution");
s.addText("Architecture", { placeholder: "title" });
s.addImage({ path: DOCS + "architecture.png", x: 0.9, y: 1.0, w: 8.2, h: 4.11, objectName: "architecture" });
s.addNotes(`Here is the full architecture, and it reads left to right.

On the left are the data streams: the EHR, the wearables and CGM, and the patient app's meal log, coming in through an ingestion layer with a FHIR R4 adapter, five-minute resampling and data-quality checks.

In the middle is the digital twin engine, with one virtual patient per real patient. At its heart is the mechanistic core, an extended Bergman minimal model. The equations at the top describe glucose, remote insulin action, plasma insulin, a two-compartment gut absorbing carbohydrates, and an exercise term that increases glucose uptake. Around that core sit five steps: initialise from the EHR, calibrate on three onboarding days, synchronise every five minutes, forecast every fifteen minutes, and the what-if simulator. Below is the hybrid machine-learning risk layer, gradient-boosted trees that take 58 fused features, including the twin's forecasts and personalised parameters, and output the probability of a spike in the next two hours.

On the right is the clinician and patient layer: the doctor dashboard, alerts and nudges, outcome tracking, and governance.

The loop at the bottom is the point of a digital twin. Every new sample synchronises the twin, the twin re-forecasts, and the risk updates. It is a living model, not a one-off prediction. The footer shows the headline held-out results, which we will unpack in a moment.`);

// ================= 7. Twin lifecycle =================
s = slide("CONTENT", "Solution");
s.addText("How each twin is born and kept alive", { placeholder: "title" });
const steps = [
  ["Initialise", "EHR sets prior physiology: insulin sensitivity from HOMA-IR & BMI; β-cell response from diagnosis, genotype, drugs; basal glucose from FPG"],
  ["Calibrate", "First 3 days: MAP search over insulin sensitivity and β-cell response against CGM, robust to unlogged meals"],
  ["Synchronise", "Every 5 min a state observer pulls the virtual glucose onto the CGM and detects meals the patient forgot to log"],
  ["Forecast", "Every 15 min the twin runs 2 h ahead: \"no further meal\" and \"habitual routine\" from its learned meal-time profile"],
  ["What-if", "Doctor tests interventions on the live state: smaller dinner, walk, short sleep, missed metformin"],
];
steps.forEach((st, i) => {
  const x = 0.5 + i * 1.84;
  card(s, x, 1.25, 1.7, 3.05, i === 4 ? "F2EFFF" : THEME.colors.lt2, "step-" + i);
  badge(s, x + 0.18, 1.42, String(i + 1), THEME.colors.accent2);
  txt(s, st[0], { x: x + 0.18, y: 1.95, w: 1.4, h: 0.35, fontSize: 15, bold: true, color: THEME.colors.accent2 });
  txt(s, st[1], { x: x + 0.18, y: 2.35, w: 1.38, h: 1.9, fontSize: 11.5 });
  if (i < 4) txt(s, "›", { x: x + 1.7, y: 2.5, w: 0.14, h: 0.4, fontSize: 20, bold: true, color: "8A97A3", align: "center" });
});
txt(s, [{ text: "Sleep enters the physiology: ", options: { bold: true } }, { text: "short or poor sleep lowers next-day insulin sensitivity; walking adds insulin-independent glucose uptake; stress raises hepatic glucose output.", options: {} }],
  { x: 0.5, y: 4.5, w: 9.0, h: 0.55, fontSize: 13, color: THEME.colors.dk2 });
s.addNotes(`Let us zoom into the twin's lifecycle, because this is what makes it a twin rather than a forecast.

Step one, initialise. The moment a patient is onboarded, the EHR gives us a prior. Insulin sensitivity is estimated from HOMA-IR, which uses fasting glucose and fasting insulin, adjusted for BMI. Beta-cell responsiveness is set from the diagnosis, the TCF7L2 and KCNQ1 genotype, and medications such as sulfonylureas and DPP-4 inhibitors that boost secretion. Basal glucose comes from fasting plasma glucose.

Step two, calibrate. During the first three days we search over insulin sensitivity and beta-cell response to find the values that best reproduce that patient's CGM, given their logged meals and steps. Two technical points: we use a robust Huber loss, so meals the patient forgot to log do not distort the fit, and we use a maximum-a-posteriori approach that keeps the twin close to the EHR prior unless the patient's own data clearly disagree. This matters because those two parameters are partly confounded.

Step three, synchronise. Every five minutes a state observer nudges the virtual glucose towards the measured CGM. If glucose rises sharply with no logged meal, the twin infers an unlogged meal and injects the implied carbohydrate into its gut compartment, so its internal state stays physiologically plausible.

Step four, forecast. Every fifteen minutes the twin is run two hours into the future under two scenarios: no further food, and the patient's habitual routine, using a meal-time profile the twin learned during onboarding.

Step five, what-if. A doctor can take the live state and test interventions.

Finally, context enters through physiology, not just as features: poor sleep lowers next-day insulin sensitivity, walking adds insulin-independent uptake, and stress raises glucose output from the liver.`);

// ================= 8. Twin fidelity =================
s = slide("CONTENT", "Solution");
s.addText("The twin learns each patient's physiology", { placeholder: "title" });
stat(s, 0.5, 1.2, 2.9, "−30%", "error in recovered insulin sensitivity vs EHR-only prior (log-scale, against hidden ground truth)", THEME.colors.accent2);
stat(s, 3.55, 1.2, 2.9, "51 → 46", "mg/dL open-loop RMSE over 3 days after calibration (no data assimilation)", THEME.colors.accent1);
stat(s, 6.6, 1.2, 2.9, "6.8", "mg/dL mean absolute error once synchronised to live CGM every 5 min", THEME.colors.accent5);
s.addImage({ path: DOCS + "shot_glucose_risk.png", x: 0.5, y: 2.85, w: 5.4, h: 1.86, objectName: "twin-trace" });
txt(s, [
  { text: "Purple dashed line = twin glucose tracking the patient's CGM (black).", options: { breakLine: true } },
  { text: "Hollow purple circles = meals the patient never logged, detected by the twin from the glucose trajectory.", options: { breakLine: true } },
  { text: "Red area = live spike risk; it rises before each excursion.", options: {} },
], { x: 6.15, y: 2.9, w: 3.35, h: 1.9, fontSize: 12.5, paraSpaceAfter: 6 });
s.addNotes(`Does the twin actually learn each patient? This is where synthetic data with hidden ground truth is powerful, because we can check.

First number: compared with the EHR-only prior, calibration reduces the error in the recovered insulin sensitivity by about 30 percent on a log scale, measured against each patient's hidden true value. So three days of CGM, steps and an imperfect meal log really do tell the twin something the medical record alone cannot.

Second: in pure open-loop simulation over three days, meaning the twin is given only the logged meals and steps and is never corrected, the error falls from about 51 to about 46 milligrams per decilitre. Open-loop error stays relatively high for an honest reason: patients forget to log a good share of their meals, and a model cannot simulate a meal it was never told about.

That is exactly why the third number matters. Once the twin is synchronised with the live CGM every five minutes, its mean absolute error drops to 6.8 milligrams per decilitre, which is comparable to the measurement noise of a consumer CGM.

The screenshot shows this for one patient. The black line is the CGM. The purple dashed line is the twin, tracking it closely. The hollow purple circles are meals the patient never logged, detected by the twin from the shape of the glucose curve. And the red shading is the live spike risk, which you can see rising before each excursion above the dashed 180 line.`);

// ================= 9. ML + ablation =================
pres.addSection({ title: "Results" });
s = slide("CONTENT", "Results");
s.addText("Every stream adds signal; the twin adds the most", { placeholder: "title" });
s.addChart(pres.charts.BAR, [{ name: "AUROC", labels: ["CGM only", "+ wearables & context", "+ EHR (fusion)", "GlucoTwin (full)"], values: [0.752, 0.931, 0.927, 0.942] }], {
  x: 0.5, y: 1.1, w: 5.0, h: 3.8, barDir: "bar", chartColors: ["7FB3D5", "5499C7", "2471A3", "D64933"], varyColors: true,
  valAxisMinVal: 0.5, valAxisMaxVal: 1.0, valAxisLabelFormatCode: "0.00", showValue: true, dataLabelFormatCode: "0.000", dataLabelPosition: "outEnd",
  dataLabelFontSize: 11, dataLabelColor: "14212B", catAxisLabelFontSize: 11, valAxisLabelFontSize: 10, catAxisLabelColor: "5D6B78", valAxisLabelColor: "5D6B78",
  valGridLine: { color: "E2E7EC", size: 0.5 }, catGridLine: { style: "none" }, showLegend: false, showTitle: true, title: "AUROC on 30 unseen patients",
  titleFontSize: 12, titleColor: "14212B", catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", dataLabelFontFace: "+mn-lt", titleFontFace: "+mn-lt",
});
card(s, 5.8, 1.15, 3.7, 3.75, THEME.colors.lt2, "ml-card");
txt(s, "Risk model", { x: 6.05, y: 1.32, w: 3.2, h: 0.35, fontSize: 15, bold: true, color: THEME.colors.accent3 });
txt(s, [
  { text: "Gradient-boosted trees (scikit-learn), 58 features in 5 streams", options: { bullet: true, breakLine: true } },
  { text: "Patient-level split: 70 train / 30 test patients, never mixed", options: { bullet: true, breakLine: true } },
  { text: "56 k training, 23 k test samples; 31% spike prevalence", options: { bullet: true, breakLine: true } },
  { text: "Twin features: 2-h forecast peaks, meal probability, personalised SI & γ, unlogged carbs, residual", options: { bullet: true } },
], { x: 6.05, y: 1.75, w: 3.25, h: 3.05, fontSize: 12.5, paraSpaceAfter: 6 });
s.addNotes(`On to results. The risk layer is a gradient-boosted tree model from scikit-learn with 58 features grouped into five streams: CGM history, wearables, context and meal log, the static EHR, and the digital twin.

Evaluation is deliberately strict. We split by patient: 70 patients for training and 30 for testing, and no patient appears in both. This mimics the real situation of a new patient being onboarded to a clinic. Around 56,000 samples are used for training and 23,000 for testing, with spikes occurring in about 31 percent of eligible windows.

The chart is an ablation, where we add one stream at a time. With CGM history alone the AUROC is 0.75: past glucose on its own is a weak predictor of a spike two hours out, because the spike is caused by a meal that has not happened yet. Adding wearables and context, things like time of day, steps, sleep and the meal log, jumps it to 0.93. Adding the static EHR does not help further in ranking terms, which is a useful finding: the EHR is far more valuable for initialising the twin than as raw model inputs. Adding the digital twin's features gives the best model, 0.942.

The twin features are the two-hour forecast peaks under the two scenarios, the probability a habitual meal is coming, the personalised insulin sensitivity and beta-cell response, carbohydrates from unlogged meals the twin detected, and how far the twin currently sits from the CGM.`);

// ================= 10. Clinical results =================
s = slide("CONTENT", "Results");
s.addText("Clinically: earlier warnings, far fewer false alarms", { placeholder: "title" });
stat(s, 0.5, 1.15, 2.15, "0.942", "AUROC on unseen patients (AUPRC 0.888)", THEME.colors.accent3);
stat(s, 2.8, 1.15, 2.15, "77%", "of spike episodes flagged before onset", THEME.colors.accent1);
stat(s, 5.1, 1.15, 2.15, "85 min", "median warning before the spike", THEME.colors.accent2);
stat(s, 7.4, 1.15, 2.15, "4.6×", "fewer false alerts than CGM-only (0.79 vs 3.61 per patient-day)", THEME.colors.accent5);
s.addTable([
  [{ text: "Model", options: { bold: true, color: "5D6B78" } }, { text: "AUROC", options: { bold: true, color: "5D6B78" } }, { text: "Episodes caught", options: { bold: true, color: "5D6B78" } }, { text: "Median lead", options: { bold: true, color: "5D6B78" } }, { text: "False alerts / pt-day", options: { bold: true, color: "5D6B78" } }],
  ["Rule: CGM > 140 and rising", "0.546", "54%", "10 min", "0.40"],
  ["CGM-only ML", "0.752", "87%", "90 min", "3.61"],
  ["+ wearables, context, EHR", "0.927", "78%", "75 min", "0.83"],
  [{ text: "GlucoTwin (full)", options: { bold: true } }, { text: "0.942", options: { bold: true } }, { text: "77%", options: { bold: true } }, { text: "85 min", options: { bold: true } }, { text: "0.79", options: { bold: true } }],
], { x: 0.5, y: 2.75, w: 9.0, colW: [3.0, 1.2, 1.6, 1.4, 1.8], fontSize: 12, color: "14212B", border: { type: "solid", pt: 0.5, color: "E2E7EC" }, rowH: 0.36, fill: { color: "FFFFFF" } });
txt(s, "Alert threshold fixed on training patients only (80% sample sensitivity). Calibrated probabilities; consistent across T2D (AUROC 0.94), prediabetes (0.94) and at-risk (0.93).",
  { x: 0.5, y: 4.65, w: 9.0, h: 0.45, fontSize: 11, color: "5D6B78" });
s.addNotes(`AUROC is a modelling metric. A doctor cares about something else: if I switch this on, how many spikes do I hear about in time, and how often am I bothered for nothing? So we also evaluated at the level of spike episodes.

We fixed the alert threshold on the training patients only, at 80 percent sensitivity, and then measured on the 30 unseen patients.

GlucoTwin flags 77 percent of spike episodes before they begin, with a median warning of 85 minutes. That is enough time to change a portion size, take a walk, or check medication. It does that with 0.79 false alerts per patient per day, under one a day.

Compare that with the alternatives in the table. A simple rule, glucose above 140 and rising, catches only about half the spikes and gives a ten-minute warning, which is useless clinically. A CGM-only model catches more episodes but fires 3.6 false alerts a day, which in practice means patients turn the alerts off. GlucoTwin delivers roughly the same coverage with 4.6 times fewer false alarms than CGM-only, and it improves on plain data fusion too: higher AUROC, a longer warning, and fewer false alerts.

Two more checks. The probabilities are well calibrated, as you can see in the calibration curve in the repository, so a 70 percent risk really means about a 70 percent chance. And performance is consistent across subgroups: AUROC about 0.94 for Type 2 diabetes, 0.94 for prediabetes and 0.93 for the at-risk group, so the model is not only working for the sickest patients.`);

// ================= 11. Dashboard =================
pres.addSection({ title: "Demo" });
s = slide("CONTENT", "Demo");
s.addText("The doctor's view of the virtual patient", { placeholder: "title" });
s.addImage({ path: DOCS + "dashboard_patient_view.png", x: 0.5, y: 1.0, w: 2.87, h: 4.14, objectName: "dashboard-full" });
const feats = [
  ["1", "Patient list ranked by live spike risk", THEME.colors.accent3],
  ["2", "72-h timeline: CGM, twin glucose, meals (logged & detected), risk", THEME.colors.accent1],
  ["3", "\"Why this alert\": contribution of each data stream + plain-language reasons & suggested action", THEME.colors.accent2],
  ["4", "Twin physiology: EHR prior vs personalised parameters", THEME.colors.accent2],
  ["5", "What-if simulator, then HR / HRV, steps and sleep", THEME.colors.accent5],
];
feats.forEach((f, i) => {
  badge(s, 3.75, 1.15 + i * 0.78, f[0], f[2]);
  txt(s, f[1], { x: 4.35, y: 1.17 + i * 0.78, w: 5.1, h: 0.62, fontSize: 14, valign: "middle" });
});
s.addNotes(`Let us move to the dashboard, which is the conceptual UI the challenge asks for, except that ours is fully working. It is a single HTML file in the repository: open dashboard slash index.html in any browser, no server needed. [If recording: switch to the browser now and demonstrate as you speak.]

On the left is the patient list, ranked by live spike risk for the next two hours, so a doctor or diabetes educator managing hundreds of patients sees who needs attention right now.

Selecting a patient opens the virtual patient. At the top is the clinical summary from the EHR: diagnosis, HbA1c, labs, medications and genetic markers, next to live KPIs: spike risk, 72-hour time in range, the glucose management indicator, number of spikes, and glycaemic variability.

The main chart shows the last 72 hours: CGM in black, the twin in purple, logged meals as orange dots, unlogged meals the twin detected as hollow circles, and the red risk area. You can see the risk rise ahead of each excursion.

Below that is the explanation panel. For the latest alert it shows how much each data stream pushed the risk up or down relative to a typical patient, and then explains it in plain language: current glucose, the twin's forecast peak under the patient's habitual routine, whether a meal is habitually due, and whether last night's sleep or HRV is a factor, ending with a suggested action. Next to it is the twin's physiology, showing how calibration moved this patient's insulin sensitivity and beta-cell response away from what the EHR suggested.`);

// ================= 12. What-if =================
s = slide("CONTENT", "Demo");
s.addText("What-if: test the intervention on the twin first", { placeholder: "title" });
s.addImage({ path: DOCS + "shot_whatif.png", x: 0.5, y: 1.05, w: 5.9, h: 3.03, objectName: "whatif" });
stat(s, 6.7, 1.1, 2.8, "−89 mg/dL", "post-dinner peak when tonight's dinner carbs are halved (309 → 220)", THEME.colors.accent5);
stat(s, 6.7, 2.55, 2.8, "−65 min", "time above 180 after dinner, for the same change", THEME.colors.accent1);
txt(s, "Also simulated: 15/30-min post-dinner walk, a short night's sleep (lower next-day insulin sensitivity), and a missed metformin dose.",
  { x: 0.5, y: 4.3, w: 9.0, h: 0.6, fontSize: 13, color: THEME.colors.dk2 });
s.addNotes(`This is the feature that only a digital twin can offer: the what-if simulator.

It starts from the twin's live, synchronised state, here at 6:30 in the evening, and simulates the next 24 hours. The grey dashed line is the patient's habitual plan, built from the meal times and portion sizes the twin learned. The doctor can then change four things: tonight's dinner carbohydrate, a walk after dinner of fifteen or thirty minutes, whether tonight's sleep is normal or short, and, for patients on metformin, whether the evening dose is taken or missed.

In this example, halving the dinner carbohydrate brings the post-dinner peak down from 309 to 220 milligrams per decilitre, 89 lower, and cuts the time above 180 after dinner by 65 minutes, which raises 24-hour time in range by five points. A walk after dinner lowers the peak by about another 15 to 20 milligrams per decilitre. Selecting a short night's sleep shows the next day's breakfast and lunch spikes getting worse, because sleep loss reduces insulin sensitivity. A missed metformin dose shifts the whole curve upwards.

Why does this matter clinically? It turns generic advice, eat less rice and walk more, into a personal, quantified conversation: for you, halving tonight's rice avoids about an hour above target. That is far more motivating for a patient, and it lets a doctor compare options before changing a prescription. All curves are generated by the patient's calibrated twin, so they reflect that patient's own physiology.`);

// ================= 13. Impact =================
pres.addSection({ title: "Impact" });
s = slide("CONTENT", "Impact");
s.addText("From proof of concept to a Happiest Health pilot", { placeholder: "title" });
const phases = [
  ["0–3 months", "Retrospective validation", "Re-run on de-identified CGM + EHR data (OhioT1DM, MIMIC-IV, partner clinic) under DPDP consent; recalibrate population priors for Indian cohorts"],
  ["3–9 months", "Clinic pilot", "100–200 consenting patients in Happiest Health clinics; dashboard for doctors and educators; app nudges; measure time-in-range and alert fatigue"],
  ["9–18 months", "Scale & regulate", "ABDM / FHIR integration, more conditions on the same twin core (hypertension, CVD risk); CDSCO SaMD pathway"],
];
phases.forEach((p, i) => {
  const x = 0.5 + i * 3.05;
  card(s, x, 1.2, 2.85, 2.65, THEME.colors.lt2, "phase-" + i);
  txt(s, p[0], { x: x + 0.22, y: 1.35, w: 2.4, h: 0.3, fontSize: 12, bold: true, color: THEME.colors.accent1 });
  txt(s, p[1], { x: x + 0.22, y: 1.68, w: 2.4, h: 0.4, fontSize: 16, bold: true });
  txt(s, p[2], { x: x + 0.22, y: 2.15, w: 2.42, h: 1.65, fontSize: 13 });
});
card(s, 0.5, 4.05, 9.0, 0.95, "EAF7F0", "value");
txt(s, [{ text: "Value: ", options: { bold: true, color: THEME.colors.accent5 } },
  { text: "each 10-point gain in time-in-range is linked to lower risk of complications; spikes are prevented between visits, care teams prioritise by risk, and patients get personal, quantified advice.", options: {} }],
  { x: 0.75, y: 4.17, w: 8.5, h: 0.75, fontSize: 13 });
s.addNotes(`How does this become real? We see three phases, designed around Happiest Health's clinic model.

Phase one, the first three months: retrospective validation. The whole pipeline is built so the synthetic generator can be swapped for real, de-identified data, for example the public OhioT1DM CGM dataset, MIMIC-IV, or de-identified data from a partner clinic collected with consent under the DPDP Act. We would recalibrate the population priors specifically for Indian cohorts.

Phase two, months three to nine: a clinic pilot with 100 to 200 consenting patients who already use a CGM. Doctors and diabetes educators use the dashboard, patients receive nudges in the app, and we measure what actually matters: change in time in range, number of spikes, and alert fatigue, meaning how often alerts are acted on versus dismissed.

Phase three: scale and regulation. Integrate with ABDM using the FHIR resources we already export, and extend the same twin core to related conditions such as hypertension and cardiovascular risk. For clinical deployment, a tool like this would be software as a medical device, so we would follow the CDSCO pathway.

On value: time in range is now an accepted clinical outcome, and studies link higher time in range with fewer complications. GlucoTwin aims to prevent spikes between visits, help care teams prioritise their attention by risk, and give patients advice that is personal and quantified.`);

// ================= 14. Limits =================
s = slide("CONTENT", "Impact");
s.addText("Limitations and responsible AI", { placeholder: "title" });
card(s, 0.5, 1.2, 4.4, 3.75, "FCEDEA", "limits");
txt(s, "Honest limitations", { x: 0.75, y: 1.38, w: 3.9, h: 0.35, fontSize: 15, bold: true, color: THEME.colors.accent3 });
txt(s, [
  { text: "Synthetic data: results show the method works, not clinical accuracy", options: { bullet: true, breakLine: true } },
  { text: "Minimal model simplifies physiology (no glucagon, no meal composition beyond carbs)", options: { bullet: true, breakLine: true } },
  { text: "Meal timing habits are a strong signal; irregular eaters will be harder", options: { bullet: true, breakLine: true } },
  { text: "Needs real-world validation before any clinical use", options: { bullet: true } },
], { x: 0.75, y: 1.82, w: 3.95, h: 3.0, fontSize: 14, paraSpaceAfter: 10 });
card(s, 5.1, 1.2, 4.4, 3.75, "EAF7F0", "safeguards");
txt(s, "Safeguards built in", { x: 5.35, y: 1.38, w: 3.9, h: 0.35, fontSize: 15, bold: true, color: THEME.colors.accent5 });
txt(s, [
  { text: "Privacy by design: no real data; DPDP consent & purpose limitation for pilots", options: { bullet: true, breakLine: true } },
  { text: "Human in the loop: decision support for clinicians, never autonomous dosing", options: { bullet: true, breakLine: true } },
  { text: "Explainable alerts and a physiological model doctors can inspect", options: { bullet: true, breakLine: true } },
  { text: "Subgroup checks, calibration, open-source code (MIT)", options: { bullet: true } },
], { x: 5.35, y: 1.82, w: 3.95, h: 3.0, fontSize: 14, paraSpaceAfter: 10 });
s.addNotes(`We want to be transparent about limitations, because in healthcare that builds trust.

First and most important: all results are on synthetic data. They show that the method works and that each component adds value, but they are not a claim of clinical accuracy. Real patients are messier, and the numbers will move.

Second, the minimal model is a simplification. It does not model glucagon, and it treats meals as carbohydrate only, without fat, protein or fibre slowing absorption. These are natural extensions, for example moving to the UVA/Padova model.

Third, a big part of the signal comes from habitual meal timing. That is realistic, since most people eat at fairly regular times, but patients with irregular schedules, such as shift workers, will be harder to predict, and we would want to measure that specifically in a pilot.

On the right are the safeguards we built in. Privacy by design: no real data was used, and any pilot would follow DPDP consent and purpose limitation. Human in the loop: GlucoTwin is decision support for clinicians and nudges for patients; it never doses insulin autonomously. Explainability: every alert comes with its reasons, and the physiological model is inspectable. And we check calibration and subgroup performance, and release all the code under the MIT license so it can be audited and improved.`);

// ================= 15. Close =================
pres.addSection({ title: "Close" });
s = slide("DARK", "Close");
s.addText("Proactive care, one twin at a time", { placeholder: "title" });
s.addText("EHR + wearables → calibrated, synchronised virtual patient → 85-min warning with 4.6× fewer false alarms → personal what-if advice", { placeholder: "body" });
txt(s, "Run it: python run_all.py → open dashboard/index.html\nThank you · Be Positive · IIM Kozhikode", { x: 0.6, y: 4.3, w: 8.5, h: 0.7, fontSize: 13, color: "9FC3CA" });
s.addNotes(`To summarise. GlucoTwin fuses a patient's EHR with their wearable and CGM stream into a calibrated, continuously synchronised virtual patient. That twin powers an early-warning system that flags most glucose spikes about 85 minutes before they happen, with less than one false alarm per patient per day, 4.6 times fewer than a CGM-only approach. And because it is a twin and not just a classifier, a doctor can test interventions on it first and give patients personal, quantified advice.

Everything is reproducible. Clone the repository, run python run_all.py, and in about a minute it regenerates the synthetic cohort, calibrates the hundred twins, trains and evaluates the model, and exports the dashboard. The README walks through every component.

We believe this is a practical foundation for proactive, personalised diabetes care in India, and a natural fit for Happiest Health's clinic network. Thank you very much for your time; we look forward to your questions.`);

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("written", OUT);
})();
