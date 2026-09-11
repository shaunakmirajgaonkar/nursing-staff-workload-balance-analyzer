import pandas as pd
import numpy as np

NUMERIC_COLS = [
    'staff_count','scheduled_hours','worked_hours','overtime_hours',
    'patient_load','acuity_index','required_skill_hours','available_skill_hours',
    'absenteeism_rate','vacancy_rate'
]


def _num(s, default=0.0):
    return pd.to_numeric(s, errors='coerce').fillna(default).astype(float)


def normalize_staff(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    defaults = {
        'staff_id':'Unknown','ward':'Unassigned','shift':'Unknown','role':'Unknown',
        'skill_group':'General','staff_count':1,'scheduled_hours':8,'worked_hours':8,
        'overtime_hours':0,'patient_load':0,'acuity_index':1,'required_skill_hours':0,
        'available_skill_hours':0,'absenteeism_rate':0,'vacancy_rate':0
    }
    for c, d in defaults.items():
        if c not in out.columns:
            out[c] = d
    for c in NUMERIC_COLS:
        out[c] = _num(out[c])
    out['overtime_rate'] = np.where(out['scheduled_hours']>0, out['overtime_hours']/out['scheduled_hours']*100, 0)
    out['hours_variance'] = out['worked_hours'] - out['scheduled_hours']
    out['skill_mix_gap'] = np.maximum(out['required_skill_hours'] - out['available_skill_hours'], 0)
    out['load_per_staff'] = np.where(out['staff_count']>0, out['patient_load']/out['staff_count'], out['patient_load'])
    return out


def classify(score):
    if score >= 75: return 'Critical'
    if score >= 55: return 'High'
    if score >= 30: return 'Moderate'
    return 'Low'


def ward_metrics(df: pd.DataFrame) -> pd.DataFrame:
    d = normalize_staff(df)
    g = d.groupby('ward', dropna=False).agg(
        staff_count=('staff_count','sum'),
        scheduled_hours=('scheduled_hours','sum'),
        worked_hours=('worked_hours','sum'),
        overtime_hours=('overtime_hours','sum'),
        patient_load=('patient_load','sum'),
        acuity_index=('acuity_index','mean'),
        required_skill_hours=('required_skill_hours','sum'),
        available_skill_hours=('available_skill_hours','sum'),
        absenteeism_rate=('absenteeism_rate','mean'),
        vacancy_rate=('vacancy_rate','mean')
    ).reset_index()
    g['overtime_rate'] = np.where(g.scheduled_hours>0, g.overtime_hours/g.scheduled_hours*100, 0)
    g['load_per_staff'] = np.where(g.staff_count>0, g.patient_load/g.staff_count, g.patient_load)
    g['skill_mix_gap'] = np.maximum(g.required_skill_hours-g.available_skill_hours,0)
    return g


def workload_balance_score(df: pd.DataFrame) -> pd.DataFrame:
    w = ward_metrics(df)
    load_pressure = np.clip(w['load_per_staff'] / max(w['load_per_staff'].quantile(0.9), 1) * 100, 0, 100)
    overtime_pressure = np.clip(w['overtime_rate'] / 25 * 100, 0, 100)
    acuity_pressure = np.clip((w['acuity_index']-1) / 3 * 100, 0, 100)
    skill_pressure = np.clip(w['skill_mix_gap'] / np.maximum(w['required_skill_hours'],1) * 100, 0, 100)
    absence_pressure = np.clip(w['absenteeism_rate'],0,100)
    vacancy_pressure = np.clip(w['vacancy_rate'],0,100)
    w['pressure_score'] = np.round(
        0.30*load_pressure + 0.20*overtime_pressure + 0.15*acuity_pressure +
        0.15*skill_pressure + 0.10*absence_pressure + 0.10*vacancy_pressure, 1
    )
    w['priority'] = w['pressure_score'].apply(classify)
    return w.sort_values('pressure_score', ascending=False).reset_index(drop=True)


def staff_fairness(df: pd.DataFrame) -> pd.DataFrame:
    d = normalize_staff(df)
    by_role = d.groupby('role')['worked_hours'].transform('mean')
    d['workload_deviation'] = d['worked_hours'] - by_role
    d['fairness_gap_pct'] = np.where(by_role>0, np.abs(d['workload_deviation'])/by_role*100, 0)
    d['fairness_flag'] = np.where(d['fairness_gap_pct']>=25, 'Review', 'Balanced')
    return d


def scenario_ward(base_df: pd.DataFrame, ward: str, add_staff: float=0, overtime_change: float=0) -> dict:
    w = ward_metrics(base_df)
    row = w[w['ward']==ward]
    if row.empty:
        return {'before': None, 'after': None}
    r = row.iloc[0].copy()
    before_load = float(r['load_per_staff'])
    new_staff = max(float(r['staff_count']) + float(add_staff), 0.1)
    after_load = float(r['patient_load']) / new_staff
    new_overtime = max(float(r['overtime_hours']) + float(overtime_change), 0)
    ot_rate = new_overtime/max(float(r['scheduled_hours']) + add_staff*8, 1)*100
    return {'before': {'load_per_staff':before_load,'overtime_rate':float(r['overtime_rate'])},
            'after': {'load_per_staff':after_load,'overtime_rate':ot_rate}}
