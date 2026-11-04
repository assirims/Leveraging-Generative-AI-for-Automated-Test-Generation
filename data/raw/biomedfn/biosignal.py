# BioMedFn benchmark, domain "biosignal": physiological signals, wearables and digital-health metrics.
# Same record format as clinical.py.

PROBLEMS = [
dict(entry="heart_rate_from_rr", source="standard ECG/PPG metric", topic="heart rate",
sig="def heart_rate_from_rr(rr_ms: list) -> float:",
doc="""
Return the mean heart rate in beats per minute from a list of RR intervals in
milliseconds, 60000 / mean RR, rounded to 1 decimal. An empty list or a
non-positive interval raises ValueError.
""",
body="""
if not rr_ms or any(r <= 0 for r in rr_ms):
    raise ValueError('invalid RR intervals')
return round(60000 / (sum(rr_ms) / len(rr_ms)), 1)
""",
fault=("60000 / (sum(rr_ms) / len(rr_ms))", "60 / (sum(rr_ms) / len(rr_ms))", "unit"),
examples=[[[800, 820, 780]], [[1000]]],
tests=[[[600, 600]], [[1200, 1000, 1100, 900]], [[]], [[800, 0]], [[333, 350, 341]]]),

dict(entry="sdnn", source="Task Force of the ESC/NASPE, Circulation 1996", topic="heart rate variability",
sig="def sdnn(rr_ms: list) -> float:",
doc="""
Return SDNN, the sample standard deviation (dividing by n - 1) of the RR
intervals in milliseconds, rounded to 2 decimals. Fewer than two intervals raise
ValueError.
""",
body="""
n = len(rr_ms)
if n < 2:
    raise ValueError('need at least two intervals')
mean = sum(rr_ms) / n
return round((sum((r - mean) ** 2 for r in rr_ms) / (n - 1)) ** 0.5, 2)
""",
fault=("/ (n - 1)) ** 0.5", "/ n) ** 0.5", "estimator"),
examples=[[[800, 810, 790, 805]], [[1000, 1000]]],
tests=[[[700, 900]], [[650, 700, 750, 800, 850]], [[800]], [[812, 798, 845, 790, 803, 820]]]),

dict(entry="rmssd", source="Task Force of the ESC/NASPE, Circulation 1996", topic="heart rate variability",
sig="def rmssd(rr_ms: list) -> float:",
doc="""
Return RMSSD, the square root of the mean of the squared differences between
successive RR intervals (milliseconds), rounded to 2 decimals. Fewer than two
intervals raise ValueError.
""",
body="""
if len(rr_ms) < 2:
    raise ValueError('need at least two intervals')
d = [b - a for a, b in zip(rr_ms, rr_ms[1:])]
return round((sum(x * x for x in d) / len(d)) ** 0.5, 2)
""",
fault=("/ len(d)) ** 0.5", "/ len(rr_ms)) ** 0.5", "denominator"),
examples=[[[800, 810, 790, 805]], [[1000, 1100]]],
tests=[[[700, 700, 700]], [[600, 650, 600, 650]], [[800]], [[812, 798, 845, 790, 803, 820]]]),

dict(entry="pnn50", source="Task Force of the ESC/NASPE, Circulation 1996", topic="heart rate variability",
sig="def pnn50(rr_ms: list) -> float:",
doc="""
Return pNN50, the percentage of successive RR-interval differences whose
absolute value exceeds 50 ms (strictly), rounded to 2 decimals. Fewer than two
intervals raise ValueError.
""",
body="""
if len(rr_ms) < 2:
    raise ValueError('need at least two intervals')
d = [abs(b - a) for a, b in zip(rr_ms, rr_ms[1:])]
return round(100 * sum(1 for x in d if x > 50) / len(d), 2)
""",
fault=("if x > 50)", "if x >= 50)", "boundary"),
examples=[[[800, 860, 800, 820]], [[1000, 1050]]],
tests=[[[700, 751]], [[600, 700, 650, 600, 649]], [[800]], [[900, 840, 900, 960, 1010]]]),

dict(entry="qtc_bazett", source="Bazett, Heart 1920", topic="ECG interval correction",
sig="def qtc_bazett(qt_ms: float, rr_ms: float) -> int:",
doc="""
Return the heart-rate-corrected QT interval (Bazett) in milliseconds, rounded to
the nearest integer with round(): QTc = QT / sqrt(RR), with RR expressed in
seconds. A non-positive RR interval raises ValueError.
""",
body="""
if rr_ms <= 0:
    raise ValueError('RR must be positive')
return round(qt_ms / (rr_ms / 1000) ** 0.5)
""",
fault=("(rr_ms / 1000) ** 0.5", "(rr_ms / 100) ** 0.5", "unit"),
examples=[[400.0, 1000.0], [360.0, 640.0]],
tests=[[440.0, 810.0], [380.0, 1200.0], [500.0, 0.0], [350.0, 500.0]]),

dict(entry="qtc_fridericia", source="Fridericia, Acta Med Scand 1920", topic="ECG interval correction",
sig="def qtc_fridericia(qt_ms: float, heart_rate_bpm: float) -> int:",
doc="""
Return the heart-rate-corrected QT interval (Fridericia) in milliseconds,
rounded to the nearest integer with round(): QTc = QT / RR^(1/3), with
RR = 60 / heart rate in seconds. A non-positive heart rate raises ValueError.
""",
body="""
if heart_rate_bpm <= 0:
    raise ValueError('heart rate must be positive')
rr = 60 / heart_rate_bpm
return round(qt_ms / rr ** (1 / 3))
""",
fault=("rr ** (1 / 3)", "rr ** (1 / 2)", "exponent"),
examples=[[400.0, 60.0], [360.0, 100.0]],
tests=[[420.0, 75.0], [380.0, 45.0], [300.0, 150.0], [400.0, 0.0]]),

dict(entry="qtc_framingham", source="Sagie et al., Am J Cardiol 1992", topic="ECG interval correction",
sig="def qtc_framingham(qt_ms: float, heart_rate_bpm: float) -> int:",
doc="""
Return the heart-rate-corrected QT interval (Framingham) in milliseconds,
rounded to the nearest integer with round(): QTc = QT + 154 x (1 - RR), with
RR = 60 / heart rate in seconds. A non-positive heart rate raises ValueError.
""",
body="""
if heart_rate_bpm <= 0:
    raise ValueError('heart rate must be positive')
rr = 60 / heart_rate_bpm
return round(qt_ms + 154 * (1 - rr))
""",
fault=("154 * (1 - rr)", "145 * (1 - rr)", "coefficient"),
examples=[[400.0, 60.0], [360.0, 100.0]],
tests=[[420.0, 75.0], [380.0, 45.0], [300.0, 150.0], [400.0, -5.0]]),

dict(entry="moving_average", source="standard signal smoothing", topic="signal filtering",
sig="def moving_average(signal: list, window: int) -> list:",
doc="""
Smooth a signal with a trailing moving average of the given window length and
return a list of the same length, each value rounded to 3 decimals: output i is
the mean of the samples from max(0, i - window + 1) to i. A window below 1
raises ValueError.
""",
body="""
if window < 1:
    raise ValueError('window must be at least 1')
out = []
for i in range(len(signal)):
    seg = signal[max(0, i - window + 1):i + 1]
    out.append(round(sum(seg) / len(seg), 3))
return out
""",
fault=("seg = signal[max(0, i - window + 1):i + 1]", "seg = signal[max(0, i - window):i + 1]", "off-by-one"),
examples=[[[1, 2, 3, 4, 5], 3], [[10, 0, 10, 0], 2]],
tests=[[[], 3], [[5, 5, 5], 1], [[1, 4, 9, 16, 25, 36], 4], [[2, 4], 0], [[0.5, 1.5, 2.5], 10]]),

dict(entry="detect_peaks", source="threshold peak detection with refractory period", topic="ECG/PPG peak detection",
sig="def detect_peaks(signal: list, threshold: float, refractory: int) -> list:",
doc="""
Return the indices of detected peaks in a sampled signal, in increasing order.
Index i (excluding the first and last sample) is a peak if signal[i] >
threshold, signal[i] >= signal[i - 1] and signal[i] > signal[i + 1], and it is
at least `refractory` samples after the previously detected peak (i - previous
>= refractory). A negative refractory period raises ValueError.
""",
body="""
if refractory < 0:
    raise ValueError('refractory period must be non-negative')
peaks = []
for i in range(1, len(signal) - 1):
    x = signal[i]
    if x > threshold and x >= signal[i - 1] and x > signal[i + 1]:
        if not peaks or i - peaks[-1] >= refractory:
            peaks.append(i)
return peaks
""",
fault=("i - peaks[-1] >= refractory", "i - peaks[-1] > refractory", "boundary"),
examples=[[[0, 1, 5, 1, 0, 1, 6, 2, 0], 3.0, 2], [[0, 2, 0, 2, 0], 1.0, 3]],
tests=[[[0, 5, 0, 5, 0, 5, 0], 1.0, 2], [[1, 1, 1], 0.5, 1], [[], 0.0, 1], [[0, 3, 3, 0], 2.0, 1], [[0, 4, 0], 1.0, -1], [[0, 9, 1, 8, 1, 7, 0], 0.0, 0]]),

dict(entry="respiratory_rate", source="breath-interval estimate", topic="respiration",
sig="def respiratory_rate(breath_times_s: list) -> float:",
doc="""
Return the respiratory rate in breaths per minute from the times (seconds, in
increasing order) of successive breath onsets: 60 x (number of intervals) /
(last time - first time), rounded to 1 decimal. Fewer than two times or a
non-increasing sequence raises ValueError.
""",
body="""
n = len(breath_times_s)
if n < 2 or any(b <= a for a, b in zip(breath_times_s, breath_times_s[1:])):
    raise ValueError('need increasing breath times')
return round(60 * (n - 1) / (breath_times_s[-1] - breath_times_s[0]), 1)
""",
fault=("60 * (n - 1)", "60 * n", "off-by-one"),
examples=[[[0.0, 4.0, 8.0, 12.0]], [[1.0, 3.5, 6.0]]],
tests=[[[0.0, 2.0]], [[0.0, 3.0, 7.0, 10.5, 13.9]], [[5.0]], [[0.0, 2.0, 2.0]]]),

dict(entry="spo2_ratio_of_ratios", source="pulse-oximetry empirical calibration", topic="pulse oximetry",
sig="def spo2_ratio_of_ratios(ac_red: float, dc_red: float, ac_ir: float, dc_ir: float) -> float:",
doc="""
Estimate SpO2 (%) from photoplethysmographic signals with the ratio of ratios
R = (AC_red / DC_red) / (AC_ir / DC_ir) and the empirical calibration
SpO2 = 110 - 25 R, clipped to the range 0-100 and rounded to 1 decimal.
Non-positive DC components or AC_ir raise ValueError.
""",
body="""
if dc_red <= 0 or dc_ir <= 0 or ac_ir <= 0:
    raise ValueError('invalid signal components')
r = (ac_red / dc_red) / (ac_ir / dc_ir)
return round(min(100.0, max(0.0, 110 - 25 * r)), 1)
""",
fault=("min(100.0, max(0.0, 110 - 25 * r))", "max(0.0, 110 - 25 * r)", "missing cap"),
examples=[[0.02, 1.0, 0.04, 1.0], [0.05, 1.0, 0.05, 1.0]],
tests=[[0.01, 1.0, 0.05, 1.0], [0.3, 1.0, 0.05, 1.0], [0.02, 2.0, 0.03, 1.5], [0.02, 0.0, 0.04, 1.0]]),

dict(entry="step_count", source="threshold-crossing pedometer", topic="wearables",
sig="def step_count(accel_magnitude: list, threshold: float) -> int:",
doc="""
Count steps in an accelerometer-magnitude signal: a step is counted at every
sample that is above the threshold while the previous sample is at or below the
threshold. The first sample never counts.
""",
body="""
steps = 0
for prev, cur in zip(accel_magnitude, accel_magnitude[1:]):
    if cur > threshold and prev <= threshold:
        steps += 1
return steps
""",
fault=("prev <= threshold", "prev < threshold", "boundary"),
examples=[[[9.8, 11.5, 9.0, 12.0, 12.5, 9.5], 10.5], [[11.0, 11.0], 10.0]],
tests=[[[], 1.0], [[10.0, 10.5, 10.0, 10.5], 10.0], [[0, 1, 0, 1, 0, 1], 0.5], [[5, 5, 5], 4]]),

dict(entry="snr_db", source="signal-to-noise ratio (power)", topic="signal quality",
imports="import math",
sig="def snr_db(signal_power: float, noise_power: float) -> float:",
doc="""
Return the signal-to-noise ratio in decibels for given signal and noise powers,
10 log10(signal / noise), rounded to 2 decimals. Non-positive powers raise
ValueError.
""",
body="""
if signal_power <= 0 or noise_power <= 0:
    raise ValueError('powers must be positive')
return round(10 * math.log10(signal_power / noise_power), 2)
""",
fault=("10 * math.log10", "20 * math.log10", "coefficient"),
examples=[[100.0, 1.0], [2.0, 4.0]],
tests=[[1.0, 1.0], [0.5, 0.001], [10.0, 0.0], [3.3, 1.1]]),

dict(entry="min_max_normalize", source="standard normalisation", topic="signal preprocessing",
sig="def min_max_normalize(values: list) -> list:",
doc="""
Rescale values linearly to the range [0, 1], (x - min) / (max - min), each
rounded to 4 decimals. A constant (or single-value) list returns a list of
zeros; an empty list returns [].
""",
body="""
if not values:
    return []
lo, hi = min(values), max(values)
if hi == lo:
    return [0.0] * len(values)
return [round((x - lo) / (hi - lo), 4) for x in values]
""",
fault=("round((x - lo) / (hi - lo), 4)", "round((x - lo) / hi, 4)", "formula"),
examples=[[[2.0, 4.0, 6.0]], [[-1.0, 0.0, 3.0]]],
tests=[[[]], [[5.0]], [[3.0, 3.0]], [[10.0, 20.0, 15.0, 12.5]]]),

dict(entry="linear_resample", source="linear interpolation", topic="signal resampling",
sig="def linear_resample(times: list, values: list, new_times: list) -> list:",
doc="""
Linearly interpolate a signal sampled at strictly increasing `times` at each of
`new_times` and return the interpolated values rounded to 3 decimals. New times
before the first or after the last sample take the first or last value (no
extrapolation). Lists of different length, fewer than two samples or
non-increasing times raise ValueError.
""",
body="""
if len(times) != len(values) or len(times) < 2 or any(b <= a for a, b in zip(times, times[1:])):
    raise ValueError('invalid samples')
out = []
for t in new_times:
    if t <= times[0]:
        out.append(round(values[0], 3))
        continue
    if t >= times[-1]:
        out.append(round(values[-1], 3))
        continue
    j = 1
    while times[j] < t:
        j += 1
    t0, t1, v0, v1 = times[j - 1], times[j], values[j - 1], values[j]
    out.append(round(v0 + (v1 - v0) * (t - t0) / (t1 - t0), 3))
return out
""",
fault=("    if t <= times[0]:\n        out.append(round(values[0], 3))\n        continue\n", "", "missing clamp"),
examples=[[[0.0, 1.0, 2.0], [0.0, 10.0, 20.0], [0.5, 1.5]], [[0.0, 2.0], [1.0, 3.0], [-1.0, 1.0, 3.0]]],
tests=[[[0.0, 1.0], [5.0, 5.0], [0.25, 0.75]], [[0.0, 0.5, 2.0], [0.0, 1.0, -1.0], [0.25, 1.0, 2.0]], [[0.0], [1.0], [0.0]],
       [[0.0, 1.0, 1.0], [1.0, 2.0, 3.0], [0.5]], [[1.0, 2.0, 4.0], [10.0, 20.0, 0.0], [0.0, 3.0, 5.0]]]),

dict(entry="count_bradycardia_episodes", source="rhythm-monitoring episode detection", topic="arrhythmia monitoring",
sig="def count_bradycardia_episodes(hr_series: list, threshold: float = 50.0, min_length: int = 3) -> int:",
doc="""
Count bradycardia episodes in a heart-rate series: maximal runs of consecutive
samples with heart rate strictly below the threshold that last at least
min_length samples. A min_length below 1 raises ValueError.
""",
body="""
if min_length < 1:
    raise ValueError('min_length must be at least 1')
episodes = 0
run = 0
for hr in list(hr_series) + [float('inf')]:
    if hr < threshold:
        run += 1
    else:
        if run >= min_length:
            episodes += 1
        run = 0
return episodes
""",
fault=("if run >= min_length:", "if run > min_length:", "boundary"),
examples=[[[60, 48, 47, 45, 60, 49, 49, 70]], [[40, 40, 40, 40], 45.0, 2]],
tests=[[[]], [[50, 50, 50]], [[49, 49, 49]], [[30, 30, 60, 30, 30, 30, 30], 50.0, 4], [[45, 46, 47], 50.0, 0]]),

dict(entry="glucose_time_in_range", source="Battelino et al., Diabetes Care 2019", topic="continuous glucose monitoring",
sig="def glucose_time_in_range(glucose_mg_dl: list) -> float:",
doc="""
Return the percentage of continuous-glucose-monitoring readings within the
target range 70-180 mg/dL (inclusive), rounded to 1 decimal. An empty list
raises ValueError.
""",
body="""
if not glucose_mg_dl:
    raise ValueError('no readings')
inside = sum(1 for g in glucose_mg_dl if 70 <= g <= 180)
return round(100 * inside / len(glucose_mg_dl), 1)
""",
fault=("70 <= g <= 180", "70 <= g < 180", "boundary"),
examples=[[[65, 90, 150, 200, 110]], [[100, 120]]],
tests=[[[70, 180]], [[69, 181]], [[]], [[55, 140, 180, 250, 175, 90, 300]]]),

dict(entry="glucose_management_indicator", source="Bergenstal et al., Diabetes Care 2018", topic="continuous glucose monitoring",
sig="def glucose_management_indicator(glucose_mg_dl: list) -> float:",
doc="""
Return the glucose management indicator (GMI, %) from continuous-glucose-
monitoring readings in mg/dL, GMI = 3.31 + 0.02392 x mean glucose, rounded to 1
decimal. An empty list raises ValueError.
""",
body="""
if not glucose_mg_dl:
    raise ValueError('no readings')
mean = sum(glucose_mg_dl) / len(glucose_mg_dl)
return round(3.31 + 0.02392 * mean, 1)
""",
fault=("3.31 + 0.02392 * mean", "3.13 + 0.02392 * mean", "coefficient"),
examples=[[[150, 160, 170]], [[100]]],
tests=[[[90, 110, 130, 250]], [[300, 280]], [[]], [[70]]]),

dict(entry="glucose_cv", source="Battelino et al., Diabetes Care 2019", topic="continuous glucose monitoring",
sig="def glucose_cv(glucose_mg_dl: list) -> float:",
doc="""
Return the glycaemic variability as the coefficient of variation in percent,
100 x SD / mean, rounded to 1 decimal, with the sample standard deviation
(dividing by n - 1). Fewer than two readings raise ValueError.
""",
body="""
n = len(glucose_mg_dl)
if n < 2:
    raise ValueError('need at least two readings')
mean = sum(glucose_mg_dl) / n
sd = (sum((g - mean) ** 2 for g in glucose_mg_dl) / (n - 1)) ** 0.5
return round(100 * sd / mean, 1)
""",
fault=("/ (n - 1)) ** 0.5", "/ n) ** 0.5", "estimator"),
examples=[[[100, 150, 200]], [[120, 120, 120]]],
tests=[[[80, 240]], [[90, 110, 95, 180, 210, 60]], [[100]]]),

dict(entry="karvonen_target_hr", source="Karvonen et al., Ann Med Exp Biol Fenn 1957", topic="exercise prescription",
sig="def karvonen_target_hr(age: int, resting_hr: int, intensity: float) -> int:",
doc="""
Return the target exercise heart rate (beats per minute) by the Karvonen
heart-rate-reserve method, rounded to the nearest integer with round():
(HRmax - resting HR) x intensity + resting HR, with HRmax = 220 - age and the
intensity as a fraction. Intensity outside [0, 1] raises ValueError.
""",
body="""
if not 0 <= intensity <= 1:
    raise ValueError('intensity must be between 0 and 1')
hr_max = 220 - age
return round((hr_max - resting_hr) * intensity + resting_hr)
""",
fault=("(hr_max - resting_hr) * intensity + resting_hr", "hr_max * intensity", "formula"),
examples=[[40, 60, 0.7], [25, 70, 0.5]],
tests=[[60, 80, 0.6], [30, 55, 0.85], [50, 65, 0.0], [45, 60, 1.2]]),

dict(entry="sleep_efficiency", source="standard actigraphy/polysomnography metric", topic="sleep",
sig="def sleep_efficiency(total_sleep_min: float, time_in_bed_min: float) -> float:",
doc="""
Return sleep efficiency in percent, 100 x total sleep time / time in bed,
rounded to 1 decimal. A non-positive time in bed or a sleep time that is
negative or exceeds the time in bed raises ValueError.
""",
body="""
if time_in_bed_min <= 0 or total_sleep_min < 0 or total_sleep_min > time_in_bed_min:
    raise ValueError('invalid sleep times')
return round(100 * total_sleep_min / time_in_bed_min, 1)
""",
fault=("or total_sleep_min > time_in_bed_min:", ":", "missing check"),
examples=[[420.0, 480.0], [300.0, 450.0]],
tests=[[480.0, 480.0], [0.0, 400.0], [500.0, 480.0], [400.0, 0.0], [389.5, 455.0]]),

dict(entry="fever_burden_hours", source="temperature-monitoring burden", topic="digital health",
sig="def fever_burden_hours(temps_c: list, interval_min: float, threshold: float = 38.0) -> float:",
doc="""
Return the fever burden in hours from equally spaced temperature readings: the
number of readings at or above the threshold times the sampling interval
(minutes) divided by 60, rounded to 2 decimals. A non-positive interval raises
ValueError.
""",
body="""
if interval_min <= 0:
    raise ValueError('interval must be positive')
n = sum(1 for t in temps_c if t >= threshold)
return round(n * interval_min / 60, 2)
""",
fault=("if t >= threshold)", "if t > threshold)", "boundary"),
examples=[[[37.0, 38.0, 38.5, 37.9], 30.0], [[39.0, 39.2], 15.0, 39.0]],
tests=[[[], 10.0], [[38.0, 38.0, 38.0], 60.0], [[36.5, 37.2], 5.0], [[38.4, 38.6], 0.0]]),

dict(entry="heart_rate_from_r_peaks", source="ECG R-peak interval heart rate", topic="heart rate",
sig="def heart_rate_from_r_peaks(r_peak_indices: list, fs_hz: float) -> float:",
doc="""
Return the mean heart rate in beats per minute from the sample indices of
successive ECG R peaks and the sampling frequency fs (Hz): 60 x fs / mean
difference between successive indices, rounded to 1 decimal. Fewer than two
peaks, non-increasing indices or non-positive fs raise ValueError.
""",
body="""
if fs_hz <= 0 or len(r_peak_indices) < 2 or any(b <= a for a, b in zip(r_peak_indices, r_peak_indices[1:])):
    raise ValueError('invalid input')
d = [b - a for a, b in zip(r_peak_indices, r_peak_indices[1:])]
return round(60 * fs_hz / (sum(d) / len(d)), 1)
""",
fault=("60 * fs_hz /", "fs_hz /", "unit"),
examples=[[[0, 250, 500, 750], 250.0], [[100, 460, 830], 360.0]],
tests=[[[0, 500], 500.0], [[10, 210, 400, 600, 790], 200.0], [[5], 250.0], [[0, 100], 0.0]]),

dict(entry="activity_energy_kcal", source="Ainsworth et al., Compendium of Physical Activities 2011", topic="physical activity",
sig="def activity_energy_kcal(mets: float, weight_kg: float, minutes: float) -> float:",
doc="""
Return the energy expenditure of an activity in kcal, rounded to 1 decimal:
METs x 3.5 x body weight (kg) / 200 x duration (min). Negative inputs raise
ValueError.
""",
body="""
if mets < 0 or weight_kg < 0 or minutes < 0:
    raise ValueError('inputs must be non-negative')
return round(mets * 3.5 * weight_kg / 200 * minutes, 1)
""",
fault=("mets * 3.5 * weight_kg / 200", "mets * 3.0 * weight_kg / 200", "coefficient"),
examples=[[8.0, 70.0, 30.0], [3.5, 60.0, 45.0]],
tests=[[1.0, 80.0, 60.0], [12.3, 55.0, 20.0], [6.0, 0.0, 10.0], [4.0, 70.0, -5.0]]),

dict(entry="pulse_pressure", source="standard haemodynamic measure", topic="blood pressure",
sig="def pulse_pressure(sbp: float, dbp: float) -> float:",
doc="""
Return the pulse pressure in mmHg (systolic minus diastolic), rounded to 1
decimal. A diastolic pressure above the systolic pressure raises ValueError.
""",
body="""
if dbp > sbp:
    raise ValueError('diastolic above systolic')
return round(sbp - dbp, 1)
""",
fault=("if dbp > sbp:", "if dbp >= sbp:", "boundary"),
examples=[[120.0, 80.0], [150.5, 70.0]],
tests=[[100.0, 100.0], [90.0, 95.0], [180.0, 60.0]]),
]
