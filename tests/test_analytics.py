import pandas as pd
from analytics import normalize_staff, ward_metrics, workload_balance_score, staff_fairness, scenario_ward


def sample():
    return pd.DataFrame({
        'staff_id':['A','B','C'], 'ward':['W1','W1','W2'], 'shift':['D','N','D'], 'role':['RN','RN','RN'],
        'skill_group':['X','X','Y'], 'staff_count':[1,1,1], 'scheduled_hours':[8,8,8], 'worked_hours':[10,8,9],
        'overtime_hours':[2,0,1], 'patient_load':[12,8,7], 'acuity_index':[2.5,2.0,1.5],
        'required_skill_hours':[8,7,6], 'available_skill_hours':[6,7,6], 'absenteeism_rate':[2,1,1], 'vacancy_rate':[5,5,2]
    })


def test_normalize_derives_metrics():
    d=normalize_staff(sample())
    assert 'overtime_rate' in d and 'skill_mix_gap' in d
    assert d.loc[0,'overtime_rate']==25


def test_pressure_has_priority():
    w=workload_balance_score(sample())
    assert len(w)==2
    assert w['pressure_score'].between(0,100).all()
    assert set(w['priority']).issubset({'Low','Moderate','High','Critical'})


def test_fairness_and_scenario():
    f=staff_fairness(sample())
    assert 'fairness_gap_pct' in f.columns
    s=scenario_ward(sample(),'W1',2,-2)
    assert s['after']['load_per_staff'] < s['before']['load_per_staff']
    assert s['after']['overtime_rate'] < s['before']['overtime_rate']
