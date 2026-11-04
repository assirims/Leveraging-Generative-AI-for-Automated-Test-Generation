# BioMedFn benchmark, domain "dosing": anthropometrics, renal function and precision dosing / pharmacokinetics.
# Same record format as clinical.py.

PROBLEMS = [
dict(entry="body_mass_index", source="WHO definition", topic="anthropometrics",
sig="def body_mass_index(weight_kg: float, height_cm: float) -> float:",
doc="""
Return the body-mass index in kg/m^2, rounded to 1 decimal, from weight in kg
and height in cm. Non-positive height raises ValueError.
""",
body="""
if height_cm <= 0:
    raise ValueError('height must be positive')
h = height_cm / 100
return round(weight_kg / (h * h), 1)
""",
fault=("h = height_cm / 100", "h = height_cm / 10", "unit"),
examples=[[70.0, 175.0], [95.0, 160.0]],
tests=[[50.0, 150.0], [120.0, 190.0], [3.5, 50.0], [60.0, 0.0]]),

dict(entry="bsa_mosteller", source="Mosteller, NEJM 1987", topic="anthropometrics",
imports="import math",
sig="def bsa_mosteller(weight_kg: float, height_cm: float) -> float:",
doc="""
Return the body surface area in m^2 by the Mosteller formula, rounded to 2
decimals: sqrt(height_cm x weight_kg / 3600).
""",
body="""
return round(math.sqrt(height_cm * weight_kg / 3600), 2)
""",
fault=("/ 3600", "/ 3131", "unit"),
examples=[[70.0, 175.0], [20.0, 110.0]],
tests=[[100.0, 190.0], [3.2, 50.0], [55.0, 160.0]]),

dict(entry="bsa_dubois", source="Du Bois & Du Bois, Arch Intern Med 1916", topic="anthropometrics",
sig="def bsa_dubois(weight_kg: float, height_cm: float) -> float:",
doc="""
Return the body surface area in m^2 by the Du Bois formula, rounded to 2
decimals: 0.007184 x weight_kg^0.425 x height_cm^0.725.
""",
body="""
return round(0.007184 * weight_kg ** 0.425 * height_cm ** 0.725, 2)
""",
fault=("weight_kg ** 0.425 * height_cm ** 0.725", "weight_kg ** 0.725 * height_cm ** 0.425", "exponent"),
examples=[[70.0, 175.0], [50.0, 150.0]],
tests=[[100.0, 190.0], [12.0, 85.0], [80.0, 180.0]]),

dict(entry="ideal_body_weight", source="Devine, Drug Intell Clin Pharm 1974", topic="anthropometrics",
sig="def ideal_body_weight(height_cm: float, sex: str) -> float:",
doc="""
Return the ideal body weight in kg by the Devine formula, rounded to 1 decimal:
50 kg (men, 'M') or 45.5 kg (women, 'F') plus 2.3 kg per inch of height above
60 inches (1 inch = 2.54 cm). Heights at or below 60 inches give the base
weight. Other sex values raise ValueError.
""",
body="""
if sex not in ('M', 'F'):
    raise ValueError('sex must be M or F')
base = 50.0 if sex == 'M' else 45.5
inches = height_cm / 2.54
return round(base + 2.3 * max(0.0, inches - 60), 1)
""",
fault=("max(0.0, inches - 60)", "(inches - 60)", "missing bound"),
examples=[[180.0, "M"], [165.0, "F"]],
tests=[[150.0, "F"], [152.4, "M"], [200.0, "M"], [140.0, "M"], [170.0, "X"]]),

dict(entry="adjusted_body_weight", source="standard dosing weight", topic="anthropometrics",
sig="def adjusted_body_weight(actual_kg: float, ideal_kg: float) -> float:",
doc="""
Return the adjusted body weight in kg, rounded to 1 decimal: ideal + 0.4 x
(actual - ideal) when the actual weight exceeds the ideal weight; otherwise the
actual weight.
""",
body="""
if actual_kg > ideal_kg:
    return round(ideal_kg + 0.4 * (actual_kg - ideal_kg), 1)
return round(actual_kg, 1)
""",
fault=("0.4 * (actual_kg - ideal_kg)", "0.3 * (actual_kg - ideal_kg)", "coefficient"),
examples=[[120.0, 70.0], [60.0, 65.0]],
tests=[[150.0, 60.0], [70.0, 70.0], [85.5, 72.3]]),

dict(entry="cockcroft_gault", source="Cockcroft & Gault, Nephron 1976", topic="renal function",
sig="def cockcroft_gault(age: int, weight_kg: float, creatinine_mg_dl: float, sex: str) -> float:",
doc="""
Return the estimated creatinine clearance in mL/min (Cockcroft-Gault), rounded
to 1 decimal: (140 - age) x weight / (72 x serum creatinine), multiplied by 0.85
for women ('F'). Creatinine in mg/dL. Non-positive creatinine or a sex other
than 'M'/'F' raises ValueError.
""",
body="""
if creatinine_mg_dl <= 0 or sex not in ('M', 'F'):
    raise ValueError('invalid input')
crcl = (140 - age) * weight_kg / (72 * creatinine_mg_dl)
if sex == 'F':
    crcl *= 0.85
return round(crcl, 1)
""",
fault=("if sex == 'F':\n    crcl *= 0.85", "if sex == 'M':\n    crcl *= 0.85", "branch"),
examples=[[60, 72.0, 1.0, "M"], [75, 55.0, 1.4, "F"]],
tests=[[40, 90.0, 0.8, "F"], [85, 60.0, 2.5, "M"], [30, 70.0, 0.0, "M"], [50, 80.0, 1.2, "F"]]),

dict(entry="egfr_ckd_epi_2021", source="Inker et al., NEJM 2021", topic="renal function",
sig="def egfr_ckd_epi_2021(creatinine_mg_dl: float, age: int, sex: str) -> float:",
doc="""
Return the eGFR in mL/min/1.73 m^2 by the race-free CKD-EPI 2021 creatinine
equation, rounded to 1 decimal:
142 x min(Scr/k, 1)^a x max(Scr/k, 1)^-1.200 x 0.9938^age x 1.012 [if female],
with k = 0.7 and a = -0.241 for women ('F') and k = 0.9 and a = -0.302 for men
('M'). Non-positive creatinine or another sex value raises ValueError.
""",
body="""
if creatinine_mg_dl <= 0 or sex not in ('M', 'F'):
    raise ValueError('invalid input')
k = 0.7 if sex == 'F' else 0.9
a = -0.241 if sex == 'F' else -0.302
r = creatinine_mg_dl / k
egfr = 142 * min(r, 1) ** a * max(r, 1) ** -1.200 * 0.9938 ** age
if sex == 'F':
    egfr *= 1.012
return round(egfr, 1)
""",
fault=("max(r, 1) ** -1.200", "max(r, 1) ** -1.209", "version"),
examples=[[1.0, 50, "M"], [0.6, 30, "F"]],
tests=[[2.5, 70, "F"], [0.9, 40, "M"], [4.0, 65, "M"], [0.7, 80, "F"], [1.2, 55, "F"]]),

dict(entry="schwartz_bedside", source="Schwartz et al., JASN 2009", topic="paediatric renal function",
sig="def schwartz_bedside(height_cm: float, creatinine_mg_dl: float) -> float:",
doc="""
Return the bedside Schwartz eGFR for children in mL/min/1.73 m^2, rounded to 1
decimal: 0.413 x height (cm) / serum creatinine (mg/dL). Non-positive
creatinine raises ValueError.
""",
body="""
if creatinine_mg_dl <= 0:
    raise ValueError('creatinine must be positive')
return round(0.413 * height_cm / creatinine_mg_dl, 1)
""",
fault=("0.413 * height_cm", "0.55 * height_cm", "version"),
examples=[[120.0, 0.5], [95.0, 0.4]],
tests=[[150.0, 0.8], [70.0, 0.3], [160.0, 1.5]]),

dict(entry="creatinine_umol_to_mg_dl", source="SI conversion (88.4 umol/L per mg/dL)", topic="unit conversion",
sig="def creatinine_umol_to_mg_dl(creatinine_umol_l: float) -> float:",
doc="""
Convert serum creatinine from umol/L to mg/dL (1 mg/dL = 88.4 umol/L), rounded
to 2 decimals. Negative values raise ValueError.
""",
body="""
if creatinine_umol_l < 0:
    raise ValueError('creatinine must be non-negative')
return round(creatinine_umol_l / 88.4, 2)
""",
fault=("creatinine_umol_l / 88.4", "creatinine_umol_l / 88.0", "coefficient"),
examples=[[88.4], [150.0]],
tests=[[60.0], [442.0], [0.0], [1000.0]]),

dict(entry="carboplatin_dose_calvert", source="Calvert et al., JCO 1989; FDA GFR cap", topic="chemotherapy dosing",
sig="def carboplatin_dose_calvert(target_auc: float, gfr_ml_min: float) -> int:",
doc="""
Return the carboplatin dose in mg by the Calvert formula, rounded to the nearest
integer with round(): dose = target AUC x (GFR + 25), where the GFR is capped at
125 mL/min. Non-positive AUC or negative GFR raises ValueError.
""",
body="""
if target_auc <= 0 or gfr_ml_min < 0:
    raise ValueError('invalid input')
gfr = min(gfr_ml_min, 125.0)
return round(target_auc * (gfr + 25))
""",
fault=("gfr = min(gfr_ml_min, 125.0)", "gfr = gfr_ml_min", "missing cap"),
examples=[[5.0, 80.0], [6.0, 150.0]],
tests=[[4.0, 125.0], [2.0, 30.0], [5.0, 200.0], [7.5, 62.5], [0.0, 50.0]]),

dict(entry="elimination_rate_constant", source="first-order pharmacokinetics", topic="pharmacokinetics",
imports="import math",
sig="def elimination_rate_constant(half_life_h: float) -> float:",
doc="""
Return the first-order elimination rate constant k (1/h) from the half-life in
hours, k = ln(2) / t1/2, rounded to 4 decimals. Non-positive half-life raises
ValueError.
""",
body="""
if half_life_h <= 0:
    raise ValueError('half-life must be positive')
return round(math.log(2) / half_life_h, 4)
""",
fault=("math.log(2) / half_life_h", "math.log10(2) / half_life_h", "formula"),
examples=[[6.0], [0.5]],
tests=[[1.0], [24.0], [100.0], [0.0]]),

dict(entry="iv_bolus_concentration", source="one-compartment model", topic="pharmacokinetics",
imports="import math",
sig="def iv_bolus_concentration(dose_mg: float, vd_l: float, k_per_h: float, t_h: float) -> float:",
doc="""
Return the plasma concentration (mg/L) at time t (h) after an intravenous bolus
in a one-compartment model, C = dose / Vd x exp(-k t), rounded to 3 decimals.
Non-positive volume or negative time raises ValueError.
""",
body="""
if vd_l <= 0 or t_h < 0:
    raise ValueError('invalid input')
return round(dose_mg / vd_l * math.exp(-k_per_h * t_h), 3)
""",
fault=("dose_mg / vd_l * math.exp(-k_per_h * t_h)", "dose_mg / vd_l * math.exp(-k_per_h / t_h) if t_h else dose_mg / vd_l", "formula"),
examples=[[500.0, 50.0, 0.1, 0.0], [500.0, 50.0, 0.1, 6.0]],
tests=[[1000.0, 40.0, 0.2, 12.0], [250.0, 25.0, 0.05, 24.0], [100.0, 10.0, 0.693, 1.0], [100.0, 0.0, 0.1, 1.0]]),

dict(entry="loading_dose", source="standard pharmacokinetic dosing", topic="precision dosing",
sig="def loading_dose(target_conc_mg_l: float, vd_l_per_kg: float, weight_kg: float, bioavailability: float = 1.0) -> int:",
doc="""
Return the loading dose in mg, rounded to the nearest integer with round():
target concentration x Vd (L/kg) x weight / bioavailability. Bioavailability
outside (0, 1] raises ValueError.
""",
body="""
if not 0 < bioavailability <= 1:
    raise ValueError('bioavailability must be in (0, 1]')
return round(target_conc_mg_l * vd_l_per_kg * weight_kg / bioavailability)
""",
fault=("weight_kg / bioavailability", "weight_kg * bioavailability", "formula"),
examples=[[15.0, 0.7, 70.0], [2.0, 7.0, 60.0, 0.7]],
tests=[[10.0, 0.5, 80.0, 0.5], [20.0, 0.6, 50.0, 1.0], [1.5, 6.0, 65.0, 0.8], [10.0, 0.5, 80.0, 0.0]]),

dict(entry="maintenance_dose", source="standard pharmacokinetic dosing", topic="precision dosing",
sig="def maintenance_dose(target_css_mg_l: float, clearance_l_h: float, tau_h: float, bioavailability: float = 1.0) -> float:",
doc="""
Return the maintenance dose in mg per dosing interval, rounded to 1 decimal:
target average steady-state concentration x clearance (L/h) x dosing interval
tau (h) / bioavailability. Bioavailability outside (0, 1] or non-positive tau
raises ValueError.
""",
body="""
if not 0 < bioavailability <= 1 or tau_h <= 0:
    raise ValueError('invalid input')
return round(target_css_mg_l * clearance_l_h * tau_h / bioavailability, 1)
""",
fault=("clearance_l_h * tau_h / bioavailability", "clearance_l_h / bioavailability", "omission"),
examples=[[10.0, 3.0, 12.0], [15.0, 4.5, 8.0, 0.9]],
tests=[[2.0, 1.2, 24.0, 0.5], [20.0, 5.0, 6.0], [10.0, 3.0, 1.0], [10.0, 3.0, 0.0]]),

dict(entry="accumulation_factor", source="multiple-dose pharmacokinetics", topic="pharmacokinetics",
imports="import math",
sig="def accumulation_factor(k_per_h: float, tau_h: float) -> float:",
doc="""
Return the accumulation factor at steady state for repeated dosing every tau
hours with elimination rate constant k, R = 1 / (1 - exp(-k tau)), rounded to 3
decimals. Non-positive k or tau raises ValueError.
""",
body="""
if k_per_h <= 0 or tau_h <= 0:
    raise ValueError('k and tau must be positive')
return round(1 / (1 - math.exp(-k_per_h * tau_h)), 3)
""",
fault=("math.exp(-k_per_h * tau_h)", "math.exp(-k_per_h / tau_h)", "formula"),
examples=[[0.1, 12.0], [0.0577, 24.0]],
tests=[[0.693, 1.0], [0.2, 8.0], [0.05, 6.0], [0.0, 12.0]]),

dict(entry="half_life_from_levels", source="two-level pharmacokinetic estimate", topic="therapeutic drug monitoring",
imports="import math",
sig="def half_life_from_levels(c1: float, c2: float, delta_t_h: float) -> float:",
doc="""
Return the elimination half-life in hours from two concentrations measured
delta_t hours apart during the elimination phase, t1/2 = ln(2) x delta_t /
ln(c1 / c2), rounded to 2 decimals. Raises ValueError unless c1 > c2 > 0 and
delta_t > 0.
""",
body="""
if not (c1 > c2 > 0 and delta_t_h > 0):
    raise ValueError('need c1 > c2 > 0 and a positive interval')
return round(math.log(2) * delta_t_h / math.log(c1 / c2), 2)
""",
fault=("math.log(c1 / c2)", "math.log(c1 - c2)", "formula"),
examples=[[20.0, 10.0, 6.0], [30.0, 12.0, 8.0]],
tests=[[40.0, 5.0, 12.0], [8.0, 7.0, 2.0], [10.0, 10.0, 4.0], [12.5, 3.2, 10.0]]),

dict(entry="urine_creatinine_clearance", source="timed urine collection", topic="renal function",
sig="def urine_creatinine_clearance(urine_cr_mg_dl: float, urine_volume_ml: float, serum_cr_mg_dl: float, collection_h: float = 24.0) -> float:",
doc="""
Return the measured creatinine clearance in mL/min from a timed urine
collection, rounded to 1 decimal: (urine creatinine x urine volume) / (serum
creatinine x collection time in minutes). Non-positive serum creatinine or
collection time raises ValueError.
""",
body="""
if serum_cr_mg_dl <= 0 or collection_h <= 0:
    raise ValueError('invalid input')
minutes = collection_h * 60
return round(urine_cr_mg_dl * urine_volume_ml / (serum_cr_mg_dl * minutes), 1)
""",
fault=("minutes = collection_h * 60", "minutes = collection_h", "unit"),
examples=[[100.0, 1440.0, 1.0], [80.0, 900.0, 1.6, 12.0]],
tests=[[120.0, 2000.0, 0.9], [50.0, 600.0, 2.5, 24.0], [100.0, 1500.0, 1.0, 0.0]]),

dict(entry="fractional_excretion_sodium", source="Espinel, JAMA 1976", topic="acute kidney injury",
sig="def fractional_excretion_sodium(urine_na: float, plasma_na: float, urine_cr: float, plasma_cr: float) -> float:",
doc="""
Return the fractional excretion of sodium in percent, rounded to 2 decimals:
(urine Na x plasma creatinine) / (plasma Na x urine creatinine) x 100.
Non-positive plasma sodium or urine creatinine raises ValueError.
""",
body="""
if plasma_na <= 0 or urine_cr <= 0:
    raise ValueError('invalid input')
return round(urine_na * plasma_cr / (plasma_na * urine_cr) * 100, 2)
""",
fault=("urine_na * plasma_cr / (plasma_na * urine_cr)", "urine_na * urine_cr / (plasma_na * plasma_cr)", "swap"),
examples=[[20.0, 140.0, 100.0, 2.0], [60.0, 135.0, 40.0, 3.5]],
tests=[[10.0, 140.0, 150.0, 1.0], [80.0, 130.0, 30.0, 4.0], [25.0, 0.0, 50.0, 1.0]]),

dict(entry="holliday_segar_rate", source="Holliday & Segar, Pediatrics 1957", topic="maintenance fluids",
sig="def holliday_segar_rate(weight_kg: float) -> float:",
doc="""
Return the hourly maintenance fluid rate in mL/h by the 4-2-1 rule, rounded to
1 decimal: 4 mL/kg/h for the first 10 kg, 2 mL/kg/h for the next 10 kg and
1 mL/kg/h for every kg above 20 kg. Negative weight raises ValueError.
""",
body="""
if weight_kg < 0:
    raise ValueError('weight must be non-negative')
rate = 4 * min(weight_kg, 10)
if weight_kg > 10:
    rate += 2 * (min(weight_kg, 20) - 10)
if weight_kg > 20:
    rate += weight_kg - 20
return round(rate, 1)
""",
fault=("rate += 2 * (min(weight_kg, 20) - 10)", "rate += 2 * (weight_kg - 10)", "missing bound"),
examples=[[8.0], [25.0]],
tests=[[10.0], [15.0], [20.0], [70.0], [0.0], [3.5]]),

dict(entry="parkland_first_8h", source="Baxter & Shires, 1968 (Parkland formula)", topic="burn resuscitation",
sig="def parkland_first_8h(weight_kg: float, tbsa_pct: float) -> int:",
doc="""
Return the crystalloid volume in mL to give in the first 8 hours after a burn by
the Parkland formula (4 mL x weight in kg x % total body surface area burned
over 24 hours, half of it in the first 8 hours), rounded to the nearest integer
with round(). A burned area outside 0-100% raises ValueError.
""",
body="""
if not 0 <= tbsa_pct <= 100:
    raise ValueError('TBSA must be between 0 and 100')
total = 4 * weight_kg * tbsa_pct
return round(total / 2)
""",
fault=("return round(total / 2)", "return round(total)", "omission"),
examples=[[70.0, 30.0], [20.0, 15.0]],
tests=[[100.0, 50.0], [65.5, 22.5], [80.0, 0.0], [70.0, 120.0]]),

dict(entry="mifflin_st_jeor", source="Mifflin et al., Am J Clin Nutr 1990", topic="energy requirement",
sig="def mifflin_st_jeor(weight_kg: float, height_cm: float, age: int, sex: str) -> int:",
doc="""
Return the resting energy expenditure in kcal/day by the Mifflin-St Jeor
equation, rounded to the nearest integer with round(): 10 x weight + 6.25 x
height - 5 x age + 5 for men ('M') or - 161 for women ('F'). Other sex values
raise ValueError.
""",
body="""
if sex not in ('M', 'F'):
    raise ValueError('sex must be M or F')
ree = 10 * weight_kg + 6.25 * height_cm - 5 * age
ree += 5 if sex == 'M' else -161
return round(ree)
""",
fault=("ree += 5 if sex == 'M' else -161", "ree += 5 if sex == 'F' else -161", "branch"),
examples=[[70.0, 175.0, 30, "M"], [60.0, 165.0, 45, "F"]],
tests=[[90.0, 180.0, 60, "F"], [50.0, 155.0, 20, "M"], [80.0, 170.0, 40, "U"]]),

dict(entry="weight_based_dose", source="paediatric weight-based dosing with maximum", topic="precision dosing",
sig="def weight_based_dose(dose_mg_per_kg: float, weight_kg: float, max_dose_mg: float) -> float:",
doc="""
Return a weight-based dose in mg, rounded to 1 decimal: dose per kg x weight,
but never more than the maximum dose. Negative inputs raise ValueError.
""",
body="""
if dose_mg_per_kg < 0 or weight_kg < 0 or max_dose_mg < 0:
    raise ValueError('inputs must be non-negative')
return round(min(dose_mg_per_kg * weight_kg, max_dose_mg), 1)
""",
fault=("min(dose_mg_per_kg * weight_kg, max_dose_mg)", "dose_mg_per_kg * weight_kg", "missing cap"),
examples=[[15.0, 20.0, 1000.0], [15.0, 80.0, 1000.0]],
tests=[[10.0, 3.5, 500.0], [50.0, 40.0, 2000.0], [7.5, 12.2, 90.0], [1.0, -5.0, 10.0]]),

dict(entry="infusion_rate_ml_h", source="weight-based continuous infusion", topic="precision dosing",
sig="def infusion_rate_ml_h(dose_mcg_kg_min: float, weight_kg: float, concentration_mg_ml: float) -> float:",
doc="""
Return the pump rate in mL/h for a continuous infusion dosed in micrograms per
kg per minute, rounded to 2 decimals: dose x weight x 60 / (concentration in
mg/mL x 1000). Non-positive concentration raises ValueError.
""",
body="""
if concentration_mg_ml <= 0:
    raise ValueError('concentration must be positive')
return round(dose_mcg_kg_min * weight_kg * 60 / (concentration_mg_ml * 1000), 2)
""",
fault=("weight_kg * 60 /", "weight_kg /", "unit"),
examples=[[5.0, 70.0, 1.6], [0.1, 80.0, 0.064]],
tests=[[10.0, 50.0, 2.0], [0.05, 90.0, 0.016], [3.0, 3.2, 0.4], [5.0, 70.0, 0.0]]),

dict(entry="corrected_phenytoin", source="Sheiner-Tozer equation", topic="therapeutic drug monitoring",
sig="def corrected_phenytoin(measured_mg_l: float, albumin_g_dl: float, end_stage_renal: bool = False) -> float:",
doc="""
Return the albumin-corrected phenytoin concentration in mg/L by the
Sheiner-Tozer equation, rounded to 1 decimal: measured / (0.2 x albumin + 0.1),
or measured / (0.1 x albumin + 0.1) in end-stage renal disease. Albumin in g/dL;
non-positive albumin raises ValueError.
""",
body="""
if albumin_g_dl <= 0:
    raise ValueError('albumin must be positive')
factor = 0.1 if end_stage_renal else 0.2
return round(measured_mg_l / (factor * albumin_g_dl + 0.1), 1)
""",
fault=("factor = 0.1 if end_stage_renal else 0.2", "factor = 0.2 if end_stage_renal else 0.1", "branch"),
examples=[[8.0, 2.5], [8.0, 2.5, True]],
tests=[[12.0, 4.0], [5.0, 1.8, True], [10.0, 3.0, False], [10.0, 0.0]]),
]
