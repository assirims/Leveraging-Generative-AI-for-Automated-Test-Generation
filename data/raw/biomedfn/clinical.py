# BioMedFn benchmark, domain "clinical": clinical scores and decision-support calculations.
# Each problem: entry point, specification (signature + docstring), reference body, one seeded domain fault
# (old -> new text replacement in the reference body, with its fault class), two documented examples and the
# developer test inputs. Expected outputs are computed from the reference by 02b_build_biomed.py.
# Formulas follow the cited clinical sources; the code was written for this benchmark.

PROBLEMS = [
dict(entry="cha2ds2_vasc", source="Lip et al., Chest 2010", topic="stroke risk in atrial fibrillation",
sig="def cha2ds2_vasc(age: int, sex: str, chf: bool, hypertension: bool, diabetes: bool, stroke_tia: bool, vascular: bool) -> int:",
doc="""
Return the CHA2DS2-VASc stroke-risk score of a patient with atrial fibrillation.

Points: congestive heart failure 1; hypertension 1; age >= 75 years 2; diabetes
mellitus 1; prior stroke, TIA or thromboembolism 2; vascular disease 1;
age 65-74 years 1; female sex 1. `sex` is 'M' or 'F'; any other value raises
ValueError.
""",
body="""
if sex not in ('M', 'F'):
    raise ValueError('sex must be M or F')
score = int(chf) + int(hypertension) + int(diabetes) + 2 * int(stroke_tia) + int(vascular)
if age >= 75:
    score += 2
elif age >= 65:
    score += 1
if sex == 'F':
    score += 1
return score
""",
fault=("if age >= 75:", "if age > 75:", "boundary"),
examples=[[70, "F", False, True, False, False, False], [80, "M", True, True, True, True, True]],
tests=[[50, "M", False, False, False, False, False], [64, "F", False, False, False, False, False], [65, "M", False, False, False, False, False],
       [75, "M", False, False, False, False, False], [74, "F", True, False, True, False, True], [90, "F", True, True, True, True, True],
       [30, "M", False, False, False, True, False], [75, "X", False, False, False, False, False]]),

dict(entry="has_bled", source="Pisters et al., Chest 2010", topic="bleeding risk on anticoagulation",
sig="def has_bled(hypertension: bool, abnormal_renal: bool, abnormal_liver: bool, stroke: bool, bleeding: bool, labile_inr: bool, age: int, drugs: bool, alcohol: bool) -> int:",
doc="""
Return the HAS-BLED bleeding-risk score.

One point each for: uncontrolled hypertension, abnormal renal function,
abnormal liver function, prior stroke, bleeding history or predisposition,
labile INR, elderly (age > 65 years), concomitant antiplatelet or NSAID drugs,
and alcohol use (>= 8 drinks per week).
""",
body="""
score = sum(int(x) for x in (hypertension, abnormal_renal, abnormal_liver, stroke, bleeding, labile_inr, drugs, alcohol))
if age > 65:
    score += 1
return score
""",
fault=("if age > 65:", "if age >= 65:", "boundary"),
examples=[[True, False, False, False, False, False, 70, True, False], [False, False, False, False, False, False, 40, False, False]],
tests=[[False, False, False, False, False, False, 65, False, False], [False, False, False, False, False, False, 66, False, False],
       [True, True, True, True, True, True, 80, True, True], [True, False, True, False, True, False, 50, False, True],
       [False, True, False, True, False, True, 64, True, False]]),

dict(entry="curb65", source="Lim et al., Thorax 2003", topic="pneumonia severity",
sig="def curb65(confusion: bool, urea_mmol_l: float, resp_rate: int, sbp: int, dbp: int, age: int) -> int:",
doc="""
Return the CURB-65 severity score for community-acquired pneumonia.

One point each for: confusion; blood urea > 7 mmol/L; respiratory rate >= 30
per minute; low blood pressure (systolic < 90 mmHg or diastolic <= 60 mmHg);
age >= 65 years.
""",
body="""
score = int(confusion)
if urea_mmol_l > 7:
    score += 1
if resp_rate >= 30:
    score += 1
if sbp < 90 or dbp <= 60:
    score += 1
if age >= 65:
    score += 1
return score
""",
fault=("if sbp < 90 or dbp <= 60:", "if sbp < 90 or dbp < 60:", "boundary"),
examples=[[False, 5.0, 18, 120, 80, 50], [True, 9.5, 32, 85, 55, 78]],
tests=[[False, 7.0, 29, 90, 61, 64], [False, 7.1, 30, 120, 60, 65], [True, 6.0, 20, 89, 70, 40], [False, 12.0, 35, 100, 70, 70],
       [False, 3.0, 12, 130, 85, 30]]),

dict(entry="qsofa", source="Seymour et al., JAMA 2016", topic="sepsis screening",
sig="def qsofa(resp_rate: int, sbp: int, altered_mentation: bool) -> int:",
doc="""
Return the quick SOFA (qSOFA) score.

One point each for: respiratory rate >= 22 per minute; systolic blood pressure
<= 100 mmHg; altered mentation.
""",
body="""
score = 0
if resp_rate >= 22:
    score += 1
if sbp <= 100:
    score += 1
if altered_mentation:
    score += 1
return score
""",
fault=("if sbp <= 100:", "if sbp < 100:", "boundary"),
examples=[[24, 95, False], [16, 130, False]],
tests=[[22, 100, True], [21, 101, False], [30, 80, True], [18, 100, False], [22, 140, False]]),

dict(entry="glasgow_coma_scale", source="Teasdale & Jennett, Lancet 1974", topic="level of consciousness",
sig="def glasgow_coma_scale(eye: int, verbal: int, motor: int) -> int:",
doc="""
Return the Glasgow Coma Scale total (3-15).

Eye opening is scored 1-4, verbal response 1-5 and motor response 1-6. A
component outside its range raises ValueError.
""",
body="""
if not 1 <= eye <= 4 or not 1 <= verbal <= 5 or not 1 <= motor <= 6:
    raise ValueError('component out of range')
return eye + verbal + motor
""",
fault=("not 1 <= motor <= 6", "not 1 <= motor <= 5", "range"),
examples=[[4, 5, 6], [2, 2, 4]],
tests=[[1, 1, 1], [4, 5, 5], [3, 4, 6], [0, 3, 3], [4, 6, 6], [2, 3, 7]]),

dict(entry="apgar_score", source="Apgar, Curr Res Anesth Analg 1953", topic="newborn assessment",
sig="def apgar_score(heart_rate: int, respiration: int, muscle_tone: int, reflex: int, color: int) -> int:",
doc="""
Return the Apgar score of a newborn (0-10).

Heart rate is given in beats per minute and scored 0 if absent (0 bpm), 1 if
below 100 bpm and 2 if 100 bpm or more. Respiration, muscle tone, reflex
irritability and color are already scored 0-2 each; a value outside 0-2 raises
ValueError.
""",
body="""
for v in (respiration, muscle_tone, reflex, color):
    if v not in (0, 1, 2):
        raise ValueError('component must be 0, 1 or 2')
if heart_rate <= 0:
    hr = 0
elif heart_rate < 100:
    hr = 1
else:
    hr = 2
return hr + respiration + muscle_tone + reflex + color
""",
fault=("elif heart_rate < 100:", "elif heart_rate <= 100:", "boundary"),
examples=[[140, 2, 2, 2, 1], [80, 1, 1, 1, 0]],
tests=[[0, 0, 0, 0, 0], [100, 2, 2, 2, 2], [99, 1, 2, 1, 2], [120, 3, 1, 1, 1], [60, 0, 1, 0, 0]]),

dict(entry="wells_pe", source="Wells et al., Thromb Haemost 2000", topic="pulmonary embolism probability",
sig="def wells_pe(dvt_signs: bool, pe_most_likely: bool, heart_rate: int, immobilization_or_surgery: bool, previous_vte: bool, hemoptysis: bool, malignancy: bool) -> float:",
doc="""
Return the Wells score for pulmonary embolism.

Points: clinical signs of deep vein thrombosis 3; PE the most likely diagnosis
3; heart rate > 100 per minute 1.5; immobilization >= 3 days or surgery in the
previous 4 weeks 1.5; previous DVT or PE 1.5; hemoptysis 1; malignancy 1.
""",
body="""
score = 0.0
if dvt_signs:
    score += 3.0
if pe_most_likely:
    score += 3.0
if heart_rate > 100:
    score += 1.5
if immobilization_or_surgery:
    score += 1.5
if previous_vte:
    score += 1.5
if hemoptysis:
    score += 1.0
if malignancy:
    score += 1.0
return score
""",
fault=("if heart_rate > 100:", "if heart_rate >= 100:", "boundary"),
examples=[[False, True, 110, False, False, False, False], [True, True, 90, True, True, True, True]],
tests=[[False, False, 100, False, False, False, False], [False, False, 101, False, False, False, False], [True, False, 80, False, True, False, True],
       [False, False, 70, True, False, True, False], [True, True, 120, True, True, True, True]]),

dict(entry="wells_pe_tier", source="Wells et al., Thromb Haemost 2000", topic="pulmonary embolism probability",
sig="def wells_pe_tier(score: float) -> str:",
doc="""
Return the two-tier interpretation of a Wells score for pulmonary embolism:
'PE likely' if the score is greater than 4, otherwise 'PE unlikely'. A
negative score raises ValueError.
""",
body="""
if score < 0:
    raise ValueError('score must be non-negative')
return 'PE likely' if score > 4 else 'PE unlikely'
""",
fault=("if score > 4 else", "if score >= 4 else", "boundary"),
examples=[[6.0], [1.5]],
tests=[[4.0], [4.5], [0.0], [12.5], [-1.0]]),

dict(entry="mcisaac_score", source="McIsaac et al., CMAJ 1998", topic="streptococcal pharyngitis",
sig="def mcisaac_score(age: int, exudate_or_swelling: bool, tender_anterior_nodes: bool, fever_history: bool, cough_absent: bool) -> int:",
doc="""
Return the modified Centor (McIsaac) score for streptococcal pharyngitis.

One point each for tonsillar exudate or swelling, tender or swollen anterior
cervical lymph nodes, temperature > 38 C (history of fever) and absence of
cough. Age adjustment: 3-14 years +1, 15-44 years 0, 45 years or older -1.
Ages below 3 raise ValueError.
""",
body="""
if age < 3:
    raise ValueError('score is defined from age 3')
score = int(exudate_or_swelling) + int(tender_anterior_nodes) + int(fever_history) + int(cough_absent)
if age <= 14:
    score += 1
elif age >= 45:
    score -= 1
return score
""",
fault=("if age <= 14:", "if age < 14:", "boundary"),
examples=[[10, True, True, False, True], [50, False, False, True, False]],
tests=[[14, False, False, False, False], [15, True, True, True, True], [44, True, False, False, False], [45, False, False, False, False],
       [3, True, True, True, True], [2, False, False, False, False]]),

dict(entry="alvarado_score", source="Alvarado, Ann Emerg Med 1986", topic="acute appendicitis",
sig="def alvarado_score(migration: bool, anorexia: bool, nausea_vomiting: bool, rlq_tenderness: bool, rebound: bool, temp_c: float, wbc: float, neutrophil_pct: float) -> int:",
doc="""
Return the Alvarado score for acute appendicitis (0-10).

Points: migration of pain to the right lower quadrant 1; anorexia 1; nausea or
vomiting 1; right lower quadrant tenderness 2; rebound pain 1; temperature
>= 37.3 C 1; leukocytosis (white cell count > 10 x 10^9/L) 2; left shift
(neutrophils > 75%) 1.
""",
body="""
score = int(migration) + int(anorexia) + int(nausea_vomiting) + int(rebound)
if rlq_tenderness:
    score += 2
if temp_c >= 37.3:
    score += 1
if wbc > 10:
    score += 2
if neutrophil_pct > 75:
    score += 1
return score
""",
fault=("if rlq_tenderness:\n    score += 2", "if rlq_tenderness:\n    score += 1", "weight"),
examples=[[True, True, False, True, True, 37.8, 13.5, 80.0], [False, False, True, False, False, 36.8, 7.2, 60.0]],
tests=[[False, False, False, True, False, 37.2, 10.0, 75.0], [False, False, False, False, False, 37.3, 10.1, 75.1],
       [True, True, True, True, True, 39.0, 18.0, 90.0], [True, False, True, False, True, 36.5, 9.0, 70.0]]),

dict(entry="child_pugh_points", source="Pugh et al., Br J Surg 1973", topic="cirrhosis severity",
sig="def child_pugh_points(bilirubin_mg_dl: float, albumin_g_dl: float, inr: float, ascites: str, encephalopathy: str) -> int:",
doc="""
Return the Child-Pugh score (5-15) of a patient with cirrhosis.

Bilirubin (mg/dL): < 2 gives 1 point, 2-3 gives 2, > 3 gives 3.
Albumin (g/dL): > 3.5 gives 1, 2.8-3.5 gives 2, < 2.8 gives 3.
INR: < 1.7 gives 1, 1.7-2.3 gives 2, > 2.3 gives 3.
Ascites and encephalopathy are 'none' (1 point), 'mild' (2) or 'severe' (3);
any other grade raises ValueError.
""",
body="""
grade = {'none': 1, 'mild': 2, 'severe': 3}
if ascites not in grade or encephalopathy not in grade:
    raise ValueError('unknown grade')
if bilirubin_mg_dl < 2:
    b = 1
elif bilirubin_mg_dl <= 3:
    b = 2
else:
    b = 3
if albumin_g_dl > 3.5:
    a = 1
elif albumin_g_dl >= 2.8:
    a = 2
else:
    a = 3
if inr < 1.7:
    i = 1
elif inr <= 2.3:
    i = 2
else:
    i = 3
return b + a + i + grade[ascites] + grade[encephalopathy]
""",
fault=("elif bilirubin_mg_dl <= 3:", "elif bilirubin_mg_dl < 3:", "boundary"),
examples=[[1.0, 4.0, 1.1, "none", "none"], [3.5, 2.5, 2.5, "severe", "mild"]],
tests=[[2.0, 3.5, 1.7, "mild", "none"], [3.0, 2.8, 2.3, "none", "none"], [3.1, 2.7, 2.4, "severe", "severe"], [1.9, 3.6, 1.6, "none", "mild"],
       [1.0, 4.0, 1.0, "moderate", "none"]]),

dict(entry="child_pugh_class", source="Pugh et al., Br J Surg 1973", topic="cirrhosis severity",
sig="def child_pugh_class(points: int) -> str:",
doc="""
Return the Child-Pugh class for a Child-Pugh score: 'A' for 5-6 points, 'B' for
7-9 points and 'C' for 10-15 points. Scores outside 5-15 raise ValueError.
""",
body="""
if points < 5 or points > 15:
    raise ValueError('score must be between 5 and 15')
if points <= 6:
    return 'A'
if points <= 9:
    return 'B'
return 'C'
""",
fault=("if points <= 9:", "if points < 9:", "boundary"),
examples=[[6], [11]],
tests=[[5], [7], [9], [10], [15], [4], [16]]),

dict(entry="meld_score", source="Kamath et al., Hepatology 2001 (UNOS implementation)", topic="end-stage liver disease",
imports="import math",
sig="def meld_score(bilirubin_mg_dl: float, inr: float, creatinine_mg_dl: float, dialysis_twice_weekly: bool) -> int:",
doc="""
Return the (original) MELD score, rounded to the nearest integer with round().

MELD = 3.78 ln(bilirubin) + 11.2 ln(INR) + 9.57 ln(creatinine) + 6.43, where
laboratory values below 1.0 are set to 1.0, creatinine is capped at 4.0 mg/dL,
and creatinine is set to 4.0 mg/dL for patients on dialysis at least twice a
week.
""",
body="""
bili = max(bilirubin_mg_dl, 1.0)
i = max(inr, 1.0)
cr = 4.0 if dialysis_twice_weekly else min(max(creatinine_mg_dl, 1.0), 4.0)
meld = 3.78 * math.log(bili) + 11.2 * math.log(i) + 9.57 * math.log(cr) + 6.43
return round(meld)
""",
fault=("bili = max(bilirubin_mg_dl, 1.0)", "bili = bilirubin_mg_dl", "missing bound"),
examples=[[2.0, 1.5, 1.2, False], [6.0, 2.2, 1.0, True]],
tests=[[0.5, 0.9, 0.7, False], [1.0, 1.0, 1.0, False], [10.0, 3.0, 5.0, False], [0.4, 1.2, 1.5, False], [3.2, 1.8, 2.1, True]]),

dict(entry="meld_na", source="Kim et al., NEJM 2008; UNOS policy 2016", topic="end-stage liver disease",
sig="def meld_na(meld: int, sodium_mmol_l: float) -> int:",
doc="""
Return the MELD-Na score, rounded to the nearest integer with round().

If meld <= 11 the MELD score is returned unchanged. Otherwise sodium is bounded
to 125-137 mmol/L and MELD-Na = MELD + 1.32 (137 - Na) - 0.033 MELD (137 - Na).
""",
body="""
if meld <= 11:
    return meld
na = min(max(sodium_mmol_l, 125.0), 137.0)
return round(meld + 1.32 * (137 - na) - 0.033 * meld * (137 - na))
""",
fault=("na = min(max(sodium_mmol_l, 125.0), 137.0)", "na = min(max(sodium_mmol_l, 120.0), 137.0)", "bound"),
examples=[[20, 130.0], [10, 120.0]],
tests=[[11, 125.0], [12, 137.0], [25, 118.0], [30, 140.0], [15, 128.5]]),

dict(entry="fib4_index", source="Sterling et al., Hepatology 2006", topic="liver fibrosis",
imports="import math",
sig="def fib4_index(age: int, ast: float, alt: float, platelets: float) -> float:",
doc="""
Return the FIB-4 index, rounded to 2 decimals.

FIB-4 = (age x AST) / (platelets x sqrt(ALT)), with age in years, AST and ALT
in U/L and platelets in 10^9/L. Non-positive ALT or platelets raise ValueError.
""",
body="""
if alt <= 0 or platelets <= 0:
    raise ValueError('ALT and platelets must be positive')
return round(age * ast / (platelets * math.sqrt(alt)), 2)
""",
fault=("platelets * math.sqrt(alt)", "platelets * alt", "formula"),
examples=[[55, 40.0, 36.0, 200.0], [70, 80.0, 49.0, 120.0]],
tests=[[30, 20.0, 25.0, 250.0], [62, 55.0, 1.0, 150.0], [45, 100.0, 16.0, 90.0], [50, 30.0, 0.0, 200.0]]),

dict(entry="apri_score", source="Wai et al., Hepatology 2003", topic="liver fibrosis",
sig="def apri_score(ast: float, ast_uln: float, platelets: float) -> float:",
doc="""
Return the AST-to-platelet ratio index (APRI), rounded to 2 decimals:
APRI = (AST / upper limit of normal of AST) / platelets (10^9/L) x 100.
Non-positive upper limit or platelets raise ValueError.
""",
body="""
if ast_uln <= 0 or platelets <= 0:
    raise ValueError('ULN and platelets must be positive')
return round(ast / ast_uln / platelets * 100, 2)
""",
fault=("/ platelets * 100", "/ platelets * 10", "unit"),
examples=[[80.0, 40.0, 150.0], [35.0, 35.0, 250.0]],
tests=[[120.0, 40.0, 60.0], [40.0, 40.0, 100.0], [200.0, 50.0, 80.0], [50.0, 0.0, 100.0]]),

dict(entry="mean_arterial_pressure", source="standard haemodynamic formula", topic="blood pressure",
sig="def mean_arterial_pressure(sbp: float, dbp: float) -> float:",
doc="""
Return the mean arterial pressure in mmHg, rounded to 1 decimal:
MAP = (SBP + 2 DBP) / 3. Raises ValueError if the diastolic pressure exceeds
the systolic pressure.
""",
body="""
if dbp > sbp:
    raise ValueError('diastolic above systolic')
return round((sbp + 2 * dbp) / 3, 1)
""",
fault=("(sbp + 2 * dbp) / 3", "(2 * sbp + dbp) / 3", "formula"),
examples=[[120.0, 80.0], [90.0, 50.0]],
tests=[[140.0, 90.0], [100.0, 100.0], [180.0, 110.0], [70.0, 80.0]]),

dict(entry="anion_gap", source="Figge et al., Crit Care Med 1998 (albumin correction)", topic="acid-base",
sig="def anion_gap(sodium: float, chloride: float, bicarbonate: float, albumin_g_dl: float = None) -> float:",
doc="""
Return the serum anion gap in mmol/L, rounded to 1 decimal.

AG = Na - (Cl + HCO3). If albumin (g/dL) is given, the albumin-corrected anion
gap AG + 2.5 x (4.0 - albumin) is returned instead.
""",
body="""
ag = sodium - (chloride + bicarbonate)
if albumin_g_dl is not None:
    ag += 2.5 * (4.0 - albumin_g_dl)
return round(ag, 1)
""",
fault=("ag += 2.5 * (4.0 - albumin_g_dl)", "ag += 2.5 * (albumin_g_dl - 4.0)", "sign"),
examples=[[140.0, 104.0, 24.0], [138.0, 100.0, 14.0, 2.0]],
tests=[[135.0, 100.0, 25.0, 4.0], [142.0, 98.0, 10.0, 3.0], [140.0, 110.0, 22.0], [130.0, 95.0, 20.0, 1.5]]),

dict(entry="corrected_calcium", source="Payne et al., BMJ 1973", topic="electrolytes",
sig="def corrected_calcium(calcium_mg_dl: float, albumin_g_dl: float) -> float:",
doc="""
Return the albumin-corrected total calcium in mg/dL, rounded to 2 decimals:
corrected Ca = Ca + 0.8 x (4.0 - albumin), with albumin in g/dL.
""",
body="""
return round(calcium_mg_dl + 0.8 * (4.0 - albumin_g_dl), 2)
""",
fault=("0.8 * (4.0 - albumin_g_dl)", "0.08 * (4.0 - albumin_g_dl)", "coefficient"),
examples=[[8.0, 2.5], [9.5, 4.0]],
tests=[[7.6, 2.0], [10.2, 4.5], [8.4, 3.1], [9.0, 1.8]]),

dict(entry="corrected_sodium", source="Katz, NEJM 1973", topic="electrolytes",
sig="def corrected_sodium(sodium: float, glucose_mg_dl: float) -> float:",
doc="""
Return the sodium concentration corrected for hyperglycemia (Katz), in mmol/L,
rounded to 1 decimal: Na + 1.6 x (glucose - 100) / 100, with glucose in mg/dL.
No correction is applied when glucose is 100 mg/dL or lower.
""",
body="""
if glucose_mg_dl <= 100:
    return round(sodium, 1)
return round(sodium + 1.6 * (glucose_mg_dl - 100) / 100, 1)
""",
fault=("1.6 * (glucose_mg_dl - 100)", "2.4 * (glucose_mg_dl - 100)", "coefficient"),
examples=[[130.0, 600.0], [140.0, 90.0]],
tests=[[128.0, 400.0], [135.0, 100.0], [125.0, 1000.0], [138.0, 101.0]]),

dict(entry="serum_osmolality", source="standard clinical formula", topic="electrolytes",
sig="def serum_osmolality(sodium: float, glucose_mg_dl: float, bun_mg_dl: float) -> float:",
doc="""
Return the calculated serum osmolality in mOsm/kg, rounded to 1 decimal:
2 x Na + glucose / 18 + BUN / 2.8, with glucose and blood urea nitrogen in mg/dL.
""",
body="""
return round(2 * sodium + glucose_mg_dl / 18 + bun_mg_dl / 2.8, 1)
""",
fault=("glucose_mg_dl / 18", "glucose_mg_dl / 1.8", "unit"),
examples=[[140.0, 90.0, 14.0], [130.0, 540.0, 56.0]],
tests=[[135.0, 100.0, 10.0], [150.0, 180.0, 28.0], [125.0, 1200.0, 70.0]]),

dict(entry="aa_gradient", source="alveolar gas equation", topic="respiratory physiology",
sig="def aa_gradient(fio2: float, pao2: float, paco2: float, patm: float = 760.0, ph2o: float = 47.0, rq: float = 0.8) -> float:",
doc="""
Return the alveolar-arterial oxygen gradient in mmHg, rounded to 1 decimal.

The alveolar oxygen pressure is PAO2 = FiO2 x (Patm - PH2O) - PaCO2 / RQ, with
FiO2 as a fraction (0.21-1.0); the gradient is PAO2 - PaO2. FiO2 outside
0.21-1.0 raises ValueError.
""",
body="""
if not 0.21 <= fio2 <= 1.0:
    raise ValueError('FiO2 must be a fraction between 0.21 and 1.0')
p_alv = fio2 * (patm - ph2o) - paco2 / rq
return round(p_alv - pao2, 1)
""",
fault=("- paco2 / rq", "- paco2 * rq", "formula"),
examples=[[0.21, 90.0, 40.0], [0.5, 120.0, 35.0]],
tests=[[1.0, 400.0, 40.0], [0.21, 60.0, 50.0], [0.3, 80.0, 45.0, 700.0], [0.2, 90.0, 40.0]]),

dict(entry="ards_severity", source="ARDS Definition Task Force, JAMA 2012 (Berlin)", topic="respiratory failure",
sig="def ards_severity(pao2: float, fio2: float) -> str:",
doc="""
Classify oxygenation by the PaO2/FiO2 ratio (Berlin definition), with FiO2 as a
fraction: ratio > 300 'none', 200 < ratio <= 300 'mild', 100 < ratio <= 200
'moderate', ratio <= 100 'severe'. Non-positive FiO2 raises ValueError.
""",
body="""
if fio2 <= 0:
    raise ValueError('FiO2 must be positive')
ratio = pao2 / fio2
if ratio > 300:
    return 'none'
if ratio > 200:
    return 'mild'
if ratio > 100:
    return 'moderate'
return 'severe'
""",
fault=("if ratio > 200:", "if ratio >= 200:", "boundary"),
examples=[[90.0, 0.21], [80.0, 0.6]],
tests=[[60.0, 0.2], [100.0, 0.5], [50.0, 0.5], [150.0, 0.5], [30.0, 0.4], [70.0, 0.0]]),

dict(entry="shock_index", source="Allgower & Burri, 1967", topic="haemodynamic instability",
sig="def shock_index(heart_rate: float, sbp: float) -> float:",
doc="""
Return the shock index (heart rate divided by systolic blood pressure), rounded
to 2 decimals. A non-positive systolic pressure raises ValueError.
""",
body="""
if sbp <= 0:
    raise ValueError('systolic pressure must be positive')
return round(heart_rate / sbp, 2)
""",
fault=("return round(heart_rate / sbp, 2)", "return round(sbp / heart_rate, 2)", "formula"),
examples=[[110.0, 100.0], [70.0, 140.0]],
tests=[[130.0, 80.0], [60.0, 120.0], [100.0, 100.0], [90.0, 0.0]]),

dict(entry="news2_score", source="Royal College of Physicians, NEWS2 2017", topic="early warning",
sig="def news2_score(resp_rate: int, spo2: int, on_oxygen: bool, sbp: int, pulse: int, alert: bool, temp_c: float) -> int:",
doc="""
Return the National Early Warning Score 2 (SpO2 scale 1).

Respiration rate: <= 8 -> 3, 9-11 -> 1, 12-20 -> 0, 21-24 -> 2, >= 25 -> 3.
SpO2 (%): <= 91 -> 3, 92-93 -> 2, 94-95 -> 1, >= 96 -> 0.
Supplemental oxygen: 2, room air: 0.
Systolic BP: <= 90 -> 3, 91-100 -> 2, 101-110 -> 1, 111-219 -> 0, >= 220 -> 3.
Pulse: <= 40 -> 3, 41-50 -> 1, 51-90 -> 0, 91-110 -> 1, 111-130 -> 2, >= 131 -> 3.
Consciousness: alert 0, otherwise (new confusion, voice, pain, unresponsive) 3.
Temperature (C): <= 35.0 -> 3, 35.1-36.0 -> 1, 36.1-38.0 -> 0, 38.1-39.0 -> 1,
>= 39.1 -> 2.
""",
body="""
s = 0
if resp_rate <= 8:
    s += 3
elif resp_rate <= 11:
    s += 1
elif resp_rate <= 20:
    s += 0
elif resp_rate <= 24:
    s += 2
else:
    s += 3
if spo2 <= 91:
    s += 3
elif spo2 <= 93:
    s += 2
elif spo2 <= 95:
    s += 1
if on_oxygen:
    s += 2
if sbp <= 90:
    s += 3
elif sbp <= 100:
    s += 2
elif sbp <= 110:
    s += 1
elif sbp >= 220:
    s += 3
if pulse <= 40:
    s += 3
elif pulse <= 50:
    s += 1
elif pulse <= 90:
    s += 0
elif pulse <= 110:
    s += 1
elif pulse <= 130:
    s += 2
else:
    s += 3
if not alert:
    s += 3
if temp_c <= 35.0:
    s += 3
elif temp_c <= 36.0:
    s += 1
elif temp_c <= 38.0:
    s += 0
elif temp_c <= 39.0:
    s += 1
else:
    s += 2
return s
""",
fault=("elif resp_rate <= 24:\n    s += 2", "elif resp_rate <= 24:\n    s += 1", "weight"),
examples=[[18, 97, False, 125, 75, True, 37.0], [26, 90, True, 88, 135, False, 39.5]],
tests=[[22, 95, False, 105, 95, True, 38.5], [8, 92, False, 220, 40, True, 35.0], [12, 96, False, 111, 51, True, 36.1],
       [21, 93, True, 100, 111, True, 36.0], [25, 94, False, 91, 130, False, 39.1]]),

dict(entry="abcd2_score", source="Johnston et al., Lancet 2007", topic="stroke risk after TIA",
sig="def abcd2_score(age: int, sbp: int, dbp: int, unilateral_weakness: bool, speech_disturbance: bool, duration_min: int, diabetes: bool) -> int:",
doc="""
Return the ABCD2 score for stroke risk after a transient ischaemic attack.

Age >= 60 years 1; blood pressure >= 140/90 mmHg (systolic >= 140 or diastolic
>= 90) 1; clinical features: unilateral weakness 2, otherwise speech
disturbance without weakness 1; duration >= 60 min 2, 10-59 min 1; diabetes 1.
""",
body="""
s = 0
if age >= 60:
    s += 1
if sbp >= 140 or dbp >= 90:
    s += 1
if unilateral_weakness:
    s += 2
elif speech_disturbance:
    s += 1
if duration_min >= 60:
    s += 2
elif duration_min >= 10:
    s += 1
if diabetes:
    s += 1
return s
""",
fault=("elif duration_min >= 10:", "elif duration_min > 10:", "boundary"),
examples=[[72, 150, 85, True, False, 45, True], [45, 120, 80, False, True, 5, False]],
tests=[[60, 140, 70, False, False, 10, False], [59, 139, 90, True, True, 60, False], [80, 130, 85, False, True, 9, True], [65, 160, 95, True, True, 120, True]]),

dict(entry="revised_cardiac_risk_index", source="Lee et al., Circulation 1999", topic="perioperative cardiac risk",
sig="def revised_cardiac_risk_index(high_risk_surgery: bool, ischemic_heart_disease: bool, heart_failure: bool, cerebrovascular_disease: bool, insulin_treatment: bool, creatinine_mg_dl: float) -> int:",
doc="""
Return the Revised Cardiac Risk Index (Lee): one point each for high-risk
surgery, ischemic heart disease, congestive heart failure, cerebrovascular
disease, insulin treatment, and preoperative creatinine > 2.0 mg/dL.
""",
body="""
s = sum(int(x) for x in (high_risk_surgery, ischemic_heart_disease, heart_failure, cerebrovascular_disease, insulin_treatment))
if creatinine_mg_dl > 2.0:
    s += 1
return s
""",
fault=("if creatinine_mg_dl > 2.0:", "if creatinine_mg_dl >= 2.0:", "boundary"),
examples=[[True, True, False, False, False, 1.1], [True, True, True, True, True, 2.5]],
tests=[[False, False, False, False, False, 2.0], [False, False, False, False, False, 2.01], [True, False, True, False, True, 0.9]]),

dict(entry="perc_negative", source="Kline et al., J Thromb Haemost 2004", topic="pulmonary embolism rule-out",
sig="def perc_negative(age: int, heart_rate: int, spo2: int, leg_swelling: bool, hemoptysis: bool, recent_surgery_or_trauma: bool, prior_vte: bool, hormone_use: bool) -> bool:",
doc="""
Return True if the PERC rule is negative, i.e. all eight criteria are met:
age < 50 years, heart rate < 100 per minute, SpO2 >= 95%, no unilateral leg
swelling, no hemoptysis, no surgery or trauma within 4 weeks, no prior DVT or
PE, and no hormone use.
""",
body="""
return (age < 50 and heart_rate < 100 and spo2 >= 95 and not leg_swelling and not hemoptysis
        and not recent_surgery_or_trauma and not prior_vte and not hormone_use)
""",
fault=("spo2 >= 95", "spo2 > 95", "boundary"),
examples=[[35, 80, 98, False, False, False, False, False], [55, 80, 98, False, False, False, False, False]],
tests=[[49, 99, 95, False, False, False, False, False], [30, 100, 99, False, False, False, False, False], [40, 70, 94, False, False, False, False, False],
       [25, 60, 99, False, False, False, False, True], [20, 65, 97, True, False, False, False, False]]),

dict(entry="sirs_criteria_count", source="Bone et al., Chest 1992", topic="systemic inflammation",
sig="def sirs_criteria_count(temp_c: float, heart_rate: int, resp_rate: int, paco2: float, wbc: float, bands_pct: float) -> int:",
doc="""
Return the number of SIRS criteria met (0-4): temperature > 38 C or < 36 C;
heart rate > 90 per minute; respiratory rate > 20 per minute or PaCO2 < 32 mmHg;
white cell count > 12 or < 4 x 10^9/L or bands > 10%.
""",
body="""
n = 0
if temp_c > 38 or temp_c < 36:
    n += 1
if heart_rate > 90:
    n += 1
if resp_rate > 20 or paco2 < 32:
    n += 1
if wbc > 12 or wbc < 4 or bands_pct > 10:
    n += 1
return n
""",
fault=("if heart_rate > 90:", "if heart_rate >= 90:", "boundary"),
examples=[[38.5, 110, 24, 30.0, 15.0, 5.0], [37.0, 80, 16, 40.0, 8.0, 2.0]],
tests=[[38.0, 90, 20, 32.0, 12.0, 10.0], [35.9, 91, 21, 40.0, 3.9, 0.0], [36.0, 75, 18, 31.0, 9.0, 11.0], [39.0, 120, 30, 25.0, 20.0, 15.0]]),

dict(entry="bishop_score", source="Bishop, Obstet Gynecol 1964", topic="cervical ripening",
sig="def bishop_score(dilation_cm: float, effacement_pct: float, station: int, consistency: str, position: str) -> int:",
doc="""
Return the Bishop score for induction of labour (0-13).

Dilation (cm): < 1 -> 0, 1 to < 3 -> 1, 3 to < 5 -> 2, >= 5 -> 3.
Effacement (%): < 40 -> 0, 40 to < 60 -> 1, 60 to < 80 -> 2, >= 80 -> 3.
Station: <= -3 -> 0, -2 -> 1, -1 or 0 -> 2, >= +1 -> 3.
Consistency: 'firm' 0, 'medium' 1, 'soft' 2. Position: 'posterior' 0, 'mid' 1,
'anterior' 2. Unknown consistency or position raises ValueError.
""",
body="""
cons = {'firm': 0, 'medium': 1, 'soft': 2}
pos = {'posterior': 0, 'mid': 1, 'anterior': 2}
if consistency not in cons or position not in pos:
    raise ValueError('unknown consistency or position')
if dilation_cm < 1:
    d = 0
elif dilation_cm < 3:
    d = 1
elif dilation_cm < 5:
    d = 2
else:
    d = 3
if effacement_pct < 40:
    e = 0
elif effacement_pct < 60:
    e = 1
elif effacement_pct < 80:
    e = 2
else:
    e = 3
if station <= -3:
    s = 0
elif station == -2:
    s = 1
elif station <= 0:
    s = 2
else:
    s = 3
return d + e + s + cons[consistency] + pos[position]
""",
fault=("elif dilation_cm < 3:", "elif dilation_cm <= 3:", "boundary"),
examples=[[2.0, 50.0, -1, "medium", "mid"], [5.0, 80.0, 1, "soft", "anterior"]],
tests=[[0.5, 30.0, -3, "firm", "posterior"], [3.0, 60.0, -2, "soft", "mid"], [1.0, 40.0, 0, "medium", "anterior"], [4.5, 79.0, 2, "firm", "mid"],
       [2.0, 50.0, -1, "hard", "mid"]]),

dict(entry="timi_ua_nstemi", source="Antman et al., JAMA 2000", topic="acute coronary syndrome",
sig="def timi_ua_nstemi(age: int, risk_factors: int, known_cad: bool, aspirin_last_7d: bool, angina_episodes_24h: int, st_deviation: bool, positive_marker: bool) -> int:",
doc="""
Return the TIMI risk score for unstable angina / NSTEMI (0-7): one point each
for age >= 65 years; at least 3 coronary risk factors; known coronary stenosis
>= 50%; aspirin use in the past 7 days; at least 2 anginal episodes in 24 hours;
ST deviation >= 0.5 mm; positive cardiac marker.
""",
body="""
s = 0
if age >= 65:
    s += 1
if risk_factors >= 3:
    s += 1
if known_cad:
    s += 1
if aspirin_last_7d:
    s += 1
if angina_episodes_24h >= 2:
    s += 1
if st_deviation:
    s += 1
if positive_marker:
    s += 1
return s
""",
fault=("if risk_factors >= 3:", "if risk_factors > 3:", "boundary"),
examples=[[70, 3, True, True, 2, True, True], [50, 1, False, False, 0, False, False]],
tests=[[65, 2, False, False, 1, False, False], [64, 3, False, True, 2, False, True], [80, 4, True, False, 3, True, False]]),

dict(entry="blood_pressure_category", source="Whelton et al., ACC/AHA guideline 2017", topic="hypertension staging",
sig="def blood_pressure_category(sbp: int, dbp: int) -> str:",
doc="""
Classify an office or home blood-pressure reading (ACC/AHA 2017), checking the
categories in this order: 'crisis' if systolic > 180 or diastolic > 120;
'stage 2' if systolic >= 140 or diastolic >= 90; 'stage 1' if systolic 130-139
or diastolic 80-89; 'elevated' if systolic 120-129 and diastolic < 80;
otherwise 'normal'.
""",
body="""
if sbp > 180 or dbp > 120:
    return 'crisis'
if sbp >= 140 or dbp >= 90:
    return 'stage 2'
if sbp >= 130 or dbp >= 80:
    return 'stage 1'
if sbp >= 120:
    return 'elevated'
return 'normal'
""",
fault=("if sbp >= 130 or dbp >= 80:", "if sbp >= 130 or dbp > 80:", "boundary"),
examples=[[118, 76], [135, 85]],
tests=[[120, 79], [129, 80], [140, 70], [181, 100], [110, 90], [150, 121], [130, 60]]),

dict(entry="pack_years", source="standard smoking-exposure measure", topic="smoking exposure",
sig="def pack_years(cigarettes_per_day: float, years_smoked: float) -> float:",
doc="""
Return the smoking exposure in pack-years, rounded to 1 decimal: (cigarettes
per day / 20) x years smoked. Negative inputs raise ValueError.
""",
body="""
if cigarettes_per_day < 0 or years_smoked < 0:
    raise ValueError('inputs must be non-negative')
return round(cigarettes_per_day / 20 * years_smoked, 1)
""",
fault=("cigarettes_per_day / 20", "cigarettes_per_day / 10", "unit"),
examples=[[20.0, 30.0], [10.0, 15.0]],
tests=[[40.0, 25.0], [5.0, 2.0], [0.0, 10.0], [15.0, -1.0]]),
]
