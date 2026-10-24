# GlucoTwin - 20-minute video script

Record this as a narrated PowerPoint (Slide Show > Record) or a screen recording, then upload as an **unlisted YouTube video** and paste the link into the README.
At a natural 140-160 words per minute the full script runs about 22-26 minutes, comfortably above the 20-minute minimum. On slides 11-12, switch to the browser and demonstrate the live dashboard (`dashboard/index.html`) while speaking.
Total: 3624 words.


## Slide 1 - GlucoTwin (title)  (~1.5 min)

Hello, and thank you to the Happiest Health jury for this opportunity. We are [team name] from IIM Kozhikode, and our project is GlucoTwin.

In one sentence: GlucoTwin is a personal digital twin for people living with Type 2 Diabetes. It fuses a patient's electronic health record with the live stream from their wearables and continuous glucose monitor, keeps a virtual copy of that patient's glucose physiology running in sync, and uses it to warn the patient and their doctor about a glucose spike roughly an hour and a half before it happens, while there is still time to do something about it.

Over the next twenty minutes we will cover the problem and why India specifically needs proactive diabetes care, how we chose a narrow but high-value adverse event, the two data streams and how we handled the data-privacy sandbox rules, the architecture of the twin, the results on patients the model had never seen, and then a live walkthrough of the doctor dashboard, including the what-if simulator. We will close with limitations, governance, and how this could be piloted inside Happiest Health's clinic network.

Everything you will see runs from a single public GitHub repository with one command, python run_all.py, on synthetic data only.

## Slide 2 - India's diabetes care is still reactive  (~1.8 min)

Let us start with the problem. According to the ICMR-INDIAB study published in The Lancet Diabetes and Endocrinology in 2023, India has around 101 million people living with diabetes and another 136 million with prediabetes. That second number matters: it is the pipeline of tomorrow's patients, and it is where prevention has the highest return.

Yet the way we manage diabetes is largely reactive. A typical patient gets an HbA1c test a few times a year. HbA1c is a 90-day average. It is a valuable number, but it hides exactly the thing that does damage day to day: the sharp glucose spikes after meals, especially the carbohydrate-heavy meals and late dinners that are common in Indian diets.

Continuous glucose monitors and smartwatches have changed the data situation. A patient can now have a glucose reading every five minutes, plus heart rate, heart rate variability, sleep and steps. But these devices are rear-view mirrors. They tell you that you spiked, after you have spiked.

What a clinician actually needs is different. They need a warning early enough to act, whether that is a smaller portion, a walk after the meal, or a medication check. It has to be personalised, because two patients eating the same thali respond very differently. It has to be explainable, so the doctor trusts it. And it must not cry wolf, because alert fatigue kills adoption. Those four requirements, early, personal, explainable and low false alarms, shaped every design decision you will see.

## Slide 3 - Why a digital twin, not just another ML model  (~1.9 min)

Why a digital twin and not simply another machine-learning model? There are two traditional ways to forecast glucose.

The first is pure machine learning: feed lots of CGM history into a model and let it learn the patterns. This works well when you have abundant data, but it is a black box. More importantly, it cannot answer causal questions. If a doctor asks, what happens if this patient walks for fifteen minutes after dinner, a pure ML model has no way to answer, because it has never been told how exercise acts on glucose.

The second is pure physiology: the differential equations that describe how glucose is absorbed from the gut, how insulin is secreted, and how insulin drives glucose into tissue. These models are explainable and they can simulate interventions. But with textbook parameters they fit real individuals poorly, and they know nothing about context such as a bad night's sleep or a stressful day.

GlucoTwin is a hybrid, and this is the core idea of the project. We take a physiological model, personalise its parameters to each patient using their EHR and their first three days of data, and keep it synchronised with every new CGM reading. That synchronised virtual patient produces forecasts and personalised parameters, and those become inputs to a machine-learning risk layer that also sees the raw wearable and EHR data.

A simple way to remember it: the twin is the patient's virtual copy, and the ML layer is the alarm that listens to it. You will see in the results that adding the twin improves accuracy and cuts false alarms compared with plain data fusion.

## Slide 4 - Scope: one condition, one adverse event, one decision  (~1.6 min)

The challenge brief rightly says a whole-body twin is out of scope, and asks teams to pick one condition and one localised outcome. We chose Type 2 Diabetes and prediabetes, because of the scale we just saw and because the CGM signal makes outcomes measurable.

Our persona is an adult with a CGM and a smartwatch who is managed in an outpatient or clinic model, which maps directly onto Happiest Health's away-from-the-hospital clinic approach. The primary user is the treating doctor or a diabetes educator, and the nudges reach the patient through their app.

The adverse event is precise. We predict that CGM glucose will cross 180 milligrams per decilitre at any point in the next 120 minutes. 180 is the upper bound of the internationally agreed time-in-range target. Two details make this honest. First, we only make a prediction while the patient is still at or below 180, so we are predicting the onset of a spike, not detecting one that has already started. That rules out the trivial trick of flagging people who are already high. Second, the risk is refreshed every fifteen minutes, so it behaves like a live early-warning score.

This is exactly the example in the challenge brief, predicting a glucose spike two hours in advance, and we took it seriously as a clinical product rather than only a modelling exercise.

## Slide 5 - Two data streams, fully synthetic and privacy-safe  (~2.2 min)

Now the data. The challenge requires a fusion of two streams, and the sandbox rules require anonymised, open-source or synthetic data because of the DPDP Act and HIPAA. We built our own Synthea-style generator, and we want to explain why that is a strength rather than a shortcut.

The static stream is the EHR: demographics, BMI, waist and blood pressure; diagnoses coded in ICD-10; lab results coded in LOINC, including HbA1c, fasting glucose, fasting insulin, lipids and kidney function; medications; and genetic markers. We included TCF7L2, KCNQ1 and FTO risk alleles at frequencies reported for South Asian populations, because TCF7L2 in particular affects insulin secretion. Every patient is also exported as an HL7 FHIR R4 bundle, so the pipeline is interoperable and ABDM-ready.

The dynamic stream mimics a CGM and a smartwatch: glucose every five minutes, heart rate, HRV, steps, and sleep stages. We also added the patient's own meal log, deliberately incomplete and noisy, because in real life patients forget to log meals and misjudge carbs.

The key design choice is that the data is generated by physiology, not by random noise. Each synthetic patient has hidden physiology, such as insulin sensitivity and beta-cell function, derived from their profile. The cohort reflects the thin-fat Asian Indian phenotype, carbohydrate-heavy meals, late dinners, and the fact that a short or poor night's sleep reduces insulin sensitivity the next day. The EHR is consistent with the glucose traces: HbA1c is computed from each patient's simulated glucose.

In total: 100 patients, 14 days each, over 400,000 rows of five-minute data, and zero real patient records. Because we control the ground truth, we can also verify whether the twin recovers each patient's true physiology, which you cannot do with real data. The generator can be swapped for MIMIC-IV, Synthea output, or the OhioT1DM CGM dataset through the same loader.

## Slide 6 - Architecture  (~1.6 min)

Here is the full architecture, and it reads left to right.

On the left are the data streams: the EHR, the wearables and CGM, and the patient app's meal log, coming in through an ingestion layer with a FHIR R4 adapter, five-minute resampling and data-quality checks.

In the middle is the digital twin engine, with one virtual patient per real patient. At its heart is the mechanistic core, an extended Bergman minimal model. The equations at the top describe glucose, remote insulin action, plasma insulin, a two-compartment gut absorbing carbohydrates, and an exercise term that increases glucose uptake. Around that core sit five steps: initialise from the EHR, calibrate on three onboarding days, synchronise every five minutes, forecast every fifteen minutes, and the what-if simulator. Below is the hybrid machine-learning risk layer, gradient-boosted trees that take 58 fused features, including the twin's forecasts and personalised parameters, and output the probability of a spike in the next two hours.

On the right is the clinician and patient layer: the doctor dashboard, alerts and nudges, outcome tracking, and governance.

The loop at the bottom is the point of a digital twin. Every new sample synchronises the twin, the twin re-forecasts, and the risk updates. It is a living model, not a one-off prediction. The footer shows the headline held-out results, which we will unpack in a moment.

## Slide 7 - How each twin is born and kept alive  (~2.0 min)

Let us zoom into the twin's lifecycle, because this is what makes it a twin rather than a forecast.

Step one, initialise. The moment a patient is onboarded, the EHR gives us a prior. Insulin sensitivity is estimated from HOMA-IR, which uses fasting glucose and fasting insulin, adjusted for BMI. Beta-cell responsiveness is set from the diagnosis, the TCF7L2 and KCNQ1 genotype, and medications such as sulfonylureas and DPP-4 inhibitors that boost secretion. Basal glucose comes from fasting plasma glucose.

Step two, calibrate. During the first three days we search over insulin sensitivity and beta-cell response to find the values that best reproduce that patient's CGM, given their logged meals and steps. Two technical points: we use a robust Huber loss, so meals the patient forgot to log do not distort the fit, and we use a maximum-a-posteriori approach that keeps the twin close to the EHR prior unless the patient's own data clearly disagree. This matters because those two parameters are partly confounded.

Step three, synchronise. Every five minutes a state observer nudges the virtual glucose towards the measured CGM. If glucose rises sharply with no logged meal, the twin infers an unlogged meal and injects the implied carbohydrate into its gut compartment, so its internal state stays physiologically plausible.

Step four, forecast. Every fifteen minutes the twin is run two hours into the future under two scenarios: no further food, and the patient's habitual routine, using a meal-time profile the twin learned during onboarding.

Step five, what-if. A doctor can take the live state and test interventions.

Finally, context enters through physiology, not just as features: poor sleep lowers next-day insulin sensitivity, walking adds insulin-independent uptake, and stress raises glucose output from the liver.

## Slide 8 - The twin learns each patient's physiology  (~1.8 min)

Does the twin actually learn each patient? This is where synthetic data with hidden ground truth is powerful, because we can check.

First number: compared with the EHR-only prior, calibration reduces the error in the recovered insulin sensitivity by about 30 percent on a log scale, measured against each patient's hidden true value. So three days of CGM, steps and an imperfect meal log really do tell the twin something the medical record alone cannot.

Second: in pure open-loop simulation over three days, meaning the twin is given only the logged meals and steps and is never corrected, the error falls from about 51 to about 46 milligrams per decilitre. Open-loop error stays relatively high for an honest reason: patients forget to log a good share of their meals, and a model cannot simulate a meal it was never told about.

That is exactly why the third number matters. Once the twin is synchronised with the live CGM every five minutes, its mean absolute error drops to 6.8 milligrams per decilitre, which is comparable to the measurement noise of a consumer CGM.

The screenshot shows this for one patient. The black line is the CGM. The purple dashed line is the twin, tracking it closely. The hollow purple circles are meals the patient never logged, detected by the twin from the shape of the glucose curve. And the red shading is the live spike risk, which you can see rising before each excursion above the dashed 180 line.

## Slide 9 - Every stream adds signal; the twin adds the most  (~1.7 min)

On to results. The risk layer is a gradient-boosted tree model from scikit-learn with 58 features grouped into five streams: CGM history, wearables, context and meal log, the static EHR, and the digital twin.

Evaluation is deliberately strict. We split by patient: 70 patients for training and 30 for testing, and no patient appears in both. This mimics the real situation of a new patient being onboarded to a clinic. Around 56,000 samples are used for training and 23,000 for testing, with spikes occurring in about 31 percent of eligible windows.

The chart is an ablation, where we add one stream at a time. With CGM history alone the AUROC is 0.75: past glucose on its own is a weak predictor of a spike two hours out, because the spike is caused by a meal that has not happened yet. Adding wearables and context, things like time of day, steps, sleep and the meal log, jumps it to 0.93. Adding the static EHR does not help further in ranking terms, which is a useful finding: the EHR is far more valuable for initialising the twin than as raw model inputs. Adding the digital twin's features gives the best model, 0.942.

The twin features are the two-hour forecast peaks under the two scenarios, the probability a habitual meal is coming, the personalised insulin sensitivity and beta-cell response, carbohydrates from unlogged meals the twin detected, and how far the twin currently sits from the CGM.

## Slide 10 - Clinically: earlier warnings, far fewer false alarms  (~1.9 min)

AUROC is a modelling metric. A doctor cares about something else: if I switch this on, how many spikes do I hear about in time, and how often am I bothered for nothing? So we also evaluated at the level of spike episodes.

We fixed the alert threshold on the training patients only, at 80 percent sensitivity, and then measured on the 30 unseen patients.

GlucoTwin flags 77 percent of spike episodes before they begin, with a median warning of 85 minutes. That is enough time to change a portion size, take a walk, or check medication. It does that with 0.79 false alerts per patient per day, under one a day.

Compare that with the alternatives in the table. A simple rule, glucose above 140 and rising, catches only about half the spikes and gives a ten-minute warning, which is useless clinically. A CGM-only model catches more episodes but fires 3.6 false alerts a day, which in practice means patients turn the alerts off. GlucoTwin delivers roughly the same coverage with 4.6 times fewer false alarms than CGM-only, and it improves on plain data fusion too: higher AUROC, a longer warning, and fewer false alerts.

Two more checks. The probabilities are well calibrated, as you can see in the calibration curve in the repository, so a 70 percent risk really means about a 70 percent chance. And performance is consistent across subgroups: AUROC about 0.94 for Type 2 diabetes, 0.94 for prediabetes and 0.93 for the at-risk group, so the model is not only working for the sickest patients.

## Slide 11 - The doctor's view of the virtual patient  (~1.9 min)

Let us move to the dashboard, which is the conceptual UI the challenge asks for, except that ours is fully working. It is a single HTML file in the repository: open dashboard slash index.html in any browser, no server needed. [If recording: switch to the browser now and demonstrate as you speak.]

On the left is the patient list, ranked by live spike risk for the next two hours, so a doctor or diabetes educator managing hundreds of patients sees who needs attention right now.

Selecting a patient opens the virtual patient. At the top is the clinical summary from the EHR: diagnosis, HbA1c, labs, medications and genetic markers, next to live KPIs: spike risk, 72-hour time in range, the glucose management indicator, number of spikes, and glycaemic variability.

The main chart shows the last 72 hours: CGM in black, the twin in purple, logged meals as orange dots, unlogged meals the twin detected as hollow circles, and the red risk area. You can see the risk rise ahead of each excursion.

Below that is the explanation panel. For the latest alert it shows how much each data stream pushed the risk up or down relative to a typical patient, and then explains it in plain language: current glucose, the twin's forecast peak under the patient's habitual routine, whether a meal is habitually due, and whether last night's sleep or HRV is a factor, ending with a suggested action. Next to it is the twin's physiology, showing how calibration moved this patient's insulin sensitivity and beta-cell response away from what the EHR suggested.

## Slide 12 - What-if: test the intervention on the twin first  (~1.8 min)

This is the feature that only a digital twin can offer: the what-if simulator.

It starts from the twin's live, synchronised state, here at 6:30 in the evening, and simulates the next 24 hours. The grey dashed line is the patient's habitual plan, built from the meal times and portion sizes the twin learned. The doctor can then change four things: tonight's dinner carbohydrate, a walk after dinner of fifteen or thirty minutes, whether tonight's sleep is normal or short, and, for patients on metformin, whether the evening dose is taken or missed.

In this example, halving the dinner carbohydrate brings the post-dinner peak down from 309 to 220 milligrams per decilitre, 89 lower, and cuts the time above 180 after dinner by 65 minutes, which raises 24-hour time in range by five points. A walk after dinner lowers the peak by about another 15 to 20 milligrams per decilitre. Selecting a short night's sleep shows the next day's breakfast and lunch spikes getting worse, because sleep loss reduces insulin sensitivity. A missed metformin dose shifts the whole curve upwards.

Why does this matter clinically? It turns generic advice, eat less rice and walk more, into a personal, quantified conversation: for you, halving tonight's rice avoids about an hour above target. That is far more motivating for a patient, and it lets a doctor compare options before changing a prescription. All curves are generated by the patient's calibrated twin, so they reflect that patient's own physiology.

## Slide 13 - From proof of concept to a Happiest Health pilot  (~1.6 min)

How does this become real? We see three phases, designed around Happiest Health's clinic model.

Phase one, the first three months: retrospective validation. The whole pipeline is built so the synthetic generator can be swapped for real, de-identified data, for example the public OhioT1DM CGM dataset, MIMIC-IV, or de-identified data from a partner clinic collected with consent under the DPDP Act. We would recalibrate the population priors specifically for Indian cohorts.

Phase two, months three to nine: a clinic pilot with 100 to 200 consenting patients who already use a CGM. Doctors and diabetes educators use the dashboard, patients receive nudges in the app, and we measure what actually matters: change in time in range, number of spikes, and alert fatigue, meaning how often alerts are acted on versus dismissed.

Phase three: scale and regulation. Integrate with ABDM using the FHIR resources we already export, and extend the same twin core to related conditions such as hypertension and cardiovascular risk. For clinical deployment, a tool like this would be software as a medical device, so we would follow the CDSCO pathway.

On value: time in range is now an accepted clinical outcome, and studies link higher time in range with fewer complications. GlucoTwin aims to prevent spikes between visits, help care teams prioritise their attention by risk, and give patients advice that is personal and quantified.

## Slide 14 - Limitations and responsible AI  (~1.6 min)

We want to be transparent about limitations, because in healthcare that builds trust.

First and most important: all results are on synthetic data. They show that the method works and that each component adds value, but they are not a claim of clinical accuracy. Real patients are messier, and the numbers will move.

Second, the minimal model is a simplification. It does not model glucagon, and it treats meals as carbohydrate only, without fat, protein or fibre slowing absorption. These are natural extensions, for example moving to the UVA/Padova model.

Third, a big part of the signal comes from habitual meal timing. That is realistic, since most people eat at fairly regular times, but patients with irregular schedules, such as shift workers, will be harder to predict, and we would want to measure that specifically in a pilot.

On the right are the safeguards we built in. Privacy by design: no real data was used, and any pilot would follow DPDP consent and purpose limitation. Human in the loop: GlucoTwin is decision support for clinicians and nudges for patients; it never doses insulin autonomously. Explainability: every alert comes with its reasons, and the physiological model is inspectable. And we check calibration and subgroup performance, and release all the code under the MIT license so it can be audited and improved.

## Slide 15 - Proactive care, one twin at a time (close)  (~1.1 min)

To summarise. GlucoTwin fuses a patient's EHR with their wearable and CGM stream into a calibrated, continuously synchronised virtual patient. That twin powers an early-warning system that flags most glucose spikes about 85 minutes before they happen, with less than one false alarm per patient per day, 4.6 times fewer than a CGM-only approach. And because it is a twin and not just a classifier, a doctor can test interventions on it first and give patients personal, quantified advice.

Everything is reproducible. Clone the repository, run python run_all.py, and in about a minute it regenerates the synthetic cohort, calibrates the hundred twins, trains and evaluates the model, and exports the dashboard. The README walks through every component.

We believe this is a practical foundation for proactive, personalised diabetes care in India, and a natural fit for Happiest Health's clinic network. Thank you very much for your time; we look forward to your questions.
