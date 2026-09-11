from pathlib import Path
import io
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from analytics import normalize_staff, ward_metrics, workload_balance_score, staff_fairness, scenario_ward, classify

BASE = Path(__file__).parent
st.set_page_config(page_title='NurseBalance Local', page_icon='🏥', layout='wide', initial_sidebar_state='expanded')

st.markdown('''
<style>
:root{--ink:#17324d;--muted:#60758a;--line:#dbe6ee;--bg:#f7fafc;--card:#ffffff;--accent:#276ef1;--teal:#14b8a6;--amber:#f59e0b;--rose:#e11d48;--violet:#7c3aed}
.stApp{background:linear-gradient(180deg,#f7fbff 0%,#f9fbfd 44%,#eef7f5 100%);color:var(--ink)}
.block-container{padding-top:1.4rem;max-width:1450px}
.hero{background:linear-gradient(120deg,#e8f1ff 0%,#edfdfb 48%,#f5edff 100%);border:1px solid #d8e6f3;border-radius:26px;padding:28px 32px;margin-bottom:18px;box-shadow:0 16px 40px rgba(30,70,100,.08)}
.eyebrow{letter-spacing:.12em;text-transform:uppercase;font-size:.73rem;font-weight:800;color:#3b5b7a;margin-bottom:6px}.hero h1{font-size:2.35rem;line-height:1.1;margin:0;color:#17324d}.hero p{font-size:1rem;color:#4b6275;max-width:920px;margin:.65rem 0 0}
.card{background:#fff;border:1px solid #e1eaf1;border-radius:18px;padding:18px 20px;box-shadow:0 10px 28px rgba(33,64,92,.05)}
.kpi{background:#fff;border:1px solid #e1eaf1;border-radius:18px;padding:18px;min-height:120px;box-shadow:0 10px 28px rgba(33,64,92,.05)}
.kpi .label{font-size:.78rem;text-transform:uppercase;letter-spacing:.08em;color:#71869a;font-weight:700}.kpi .value{font-size:1.75rem;font-weight:850;color:#183a56;margin-top:6px}.kpi .sub{font-size:.82rem;color:#6b8092;margin-top:4px}
.section-title{font-size:1.18rem;font-weight:850;color:#17324d;margin:.2rem 0 .75rem}
.small-note{font-size:.82rem;color:#6b8092}
.badge{display:inline-block;padding:5px 10px;border-radius:999px;font-weight:800;font-size:.75rem}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#eef6ff 0%,#f3fbfa 100%);border-right:1px solid #d9e6ee}
[data-testid="stMetricValue"]{color:#17324d!important}
</style>
''', unsafe_allow_html=True)

st.sidebar.markdown('## 🏥 NurseBalance Local')
st.sidebar.caption('100% local workload and staffing analytics • CSV-first • no external APIs')

sample_staff = BASE/'data/sample_staff_workload.csv'
sample_skills = BASE/'data/sample_skill_mix.csv'

def read_upload(upload, fallback):
    if upload is None: return pd.read_csv(fallback)
    return pd.read_csv(upload)

up_staff = st.sidebar.file_uploader('Staff workload CSV', type=['csv'], key='staff')
up_skill = st.sidebar.file_uploader('Skill-mix CSV', type=['csv'], key='skills')
page = st.sidebar.radio('Workspace', ['Overview','Workload Matrix','Overtime & Hours','Skill-Mix Gaps','Ward Pressure','Fairness Review','Scenario Lab','Reports & Export'])

staff = normalize_staff(read_upload(up_staff, sample_staff))
if up_skill is not None:
    skills = pd.read_csv(up_skill)
else:
    skills = pd.read_csv(sample_skills)

wards = workload_balance_score(staff)
fair = staff_fairness(staff)

st.markdown('''<div class="hero"><div class="eyebrow">LOCAL HOSPITAL WORKFORCE INTELLIGENCE</div><h1>NurseBalance • Workload Balance Analyzer</h1><p>Identifies uneven workload, overtime pressure, skill-mix gaps, and ward-level staffing pressure for transparent hospital workforce planning.</p></div>''', unsafe_allow_html=True)

if page=='Overview':
    st.markdown('<div class="section-title">Command overview</div>', unsafe_allow_html=True)
    c=st.columns(5)
    metrics=[('Wards', len(wards), 'analyzed locally'),('Staff records', len(staff), 'workload records'),('High/Critical', int((wards.priority.isin(['High','Critical'])).sum()), 'wards to review'),('Avg overtime', f"{staff.overtime_hours.mean():.1f} h", 'per record'),('Skill gaps', f"{staff.skill_mix_gap.sum():.0f} h", 'required minus available')]
    for col,(lab,val,sub) in zip(c,metrics):
        col.markdown(f'<div class="kpi"><div class="label">{lab}</div><div class="value">{val}</div><div class="sub">{sub}</div></div>', unsafe_allow_html=True)
    st.write('')
    a,b=st.columns([1.15,1])
    with a:
        st.markdown('<div class="card"><div class="section-title">Ward pressure panorama</div>', unsafe_allow_html=True)
        fig=px.bar(wards, x='ward', y='pressure_score', color='priority', text='pressure_score', height=360)
        fig.update_traces(texttemplate='%{text:.0f}', textposition='outside')
        fig.update_layout(margin=dict(l=10,r=10,t=10,b=10), xaxis_title=None, yaxis_title='Pressure score')
        st.plotly_chart(fig,use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with b:
        st.markdown('<div class="card"><div class="section-title">Workload composition</div>', unsafe_allow_html=True)
        tmp=staff.groupby('role',as_index=False)['worked_hours'].sum().sort_values('worked_hours',ascending=False)
        fig2=px.pie(tmp,names='role',values='worked_hours',hole=.56,height=360)
        fig2.update_layout(margin=dict(l=10,r=10,t=10,b=10),legend_title=None)
        st.plotly_chart(fig2,use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="card"><div class="section-title">Priority wards</div>', unsafe_allow_html=True)
    st.dataframe(wards[['ward','priority','pressure_score','staff_count','patient_load','overtime_rate','skill_mix_gap']].head(8),use_container_width=True,hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

elif page=='Workload Matrix':
    st.markdown('<div class="section-title">Workload matrix</div>', unsafe_allow_html=True)
    x,y=st.columns(2)
    with x: xvar=st.selectbox('Horizontal signal',['load_per_staff','worked_hours','overtime_hours','acuity_index'])
    with y: yvar=st.selectbox('Vertical signal',['fairness_gap_pct','overtime_rate','skill_mix_gap','absenteeism_rate'])
    fig=px.scatter(fair,x=xvar,y=yvar,size='staff_count',color='ward',hover_data=['staff_id','role','shift'],height=520)
    fig.update_layout(margin=dict(l=10,r=10,t=10,b=10))
    st.plotly_chart(fig,use_container_width=True)
    st.dataframe(fair.sort_values('fairness_gap_pct',ascending=False),use_container_width=True,hide_index=True)

elif page=='Overtime & Hours':
    st.markdown('<div class="section-title">Overtime & schedule pressure</div>', unsafe_allow_html=True)
    a,b=st.columns([1.1,1])
    with a:
        d=staff.groupby('ward',as_index=False).agg(overtime_hours=('overtime_hours','sum'),scheduled_hours=('scheduled_hours','sum'))
        d['overtime_rate']=np.where(d.scheduled_hours>0,d.overtime_hours/d.scheduled_hours*100,0)
        fig=px.bar(d.sort_values('overtime_rate',ascending=False),x='ward',y='overtime_rate',text='overtime_rate',height=420)
        fig.update_traces(texttemplate='%{text:.1f}%',textposition='outside')
        fig.update_layout(margin=dict(l=10,r=10,t=10,b=10),yaxis_title='Overtime rate (%)',xaxis_title=None)
        st.plotly_chart(fig,use_container_width=True)
    with b:
        fig2=px.histogram(staff,x='hours_variance',nbins=14,height=420)
        fig2.update_layout(margin=dict(l=10,r=10,t=10,b=10),xaxis_title='Worked − scheduled hours')
        st.plotly_chart(fig2,use_container_width=True)
    st.dataframe(staff[['staff_id','ward','shift','scheduled_hours','worked_hours','overtime_hours','overtime_rate','hours_variance']].sort_values('overtime_hours',ascending=False),use_container_width=True,hide_index=True)

elif page=='Skill-Mix Gaps':
    st.markdown('<div class="section-title">Skill-mix readiness</div>', unsafe_allow_html=True)
    if {'ward','skill_group','required_skill_hours','available_skill_hours'}.issubset(skills.columns):
        sk=skills.copy()
        for c in ['required_skill_hours','available_skill_hours']: sk[c]=pd.to_numeric(sk[c],errors='coerce').fillna(0)
        sk['gap_hours']=(sk.required_skill_hours-sk.available_skill_hours).clip(lower=0)
        p=sk.groupby('skill_group',as_index=False)['gap_hours'].sum().sort_values('gap_hours',ascending=False)
        st.plotly_chart(px.bar(p,x='skill_group',y='gap_hours',text='gap_hours',height=410),use_container_width=True)
        st.dataframe(sk.sort_values('gap_hours',ascending=False),use_container_width=True,hide_index=True)
    else:
        st.warning('Skill CSV needs ward, skill_group, required_skill_hours, available_skill_hours columns.')

elif page=='Ward Pressure':
    st.markdown('<div class="section-title">Ward pressure ranking</div>', unsafe_allow_html=True)
    st.dataframe(wards,use_container_width=True,hide_index=True)
    fig=px.scatter(wards,x='load_per_staff',y='overtime_rate',size='staff_count',color='priority',hover_name='ward',height=500)
    fig.update_layout(margin=dict(l=10,r=10,t=10,b=10),xaxis_title='Patients per staff count',yaxis_title='Overtime rate (%)')
    st.plotly_chart(fig,use_container_width=True)

elif page=='Fairness Review':
    st.markdown('<div class="section-title">Individual workload fairness review</div>', unsafe_allow_html=True)
    threshold=st.slider('Review deviation threshold (%)',10,50,25,5)
    view=fair.copy(); view['review']=np.where(view.fairness_gap_pct>=threshold,'Review','Balanced')
    q=view[view.review=='Review'].sort_values('fairness_gap_pct',ascending=False)
    st.metric('Records needing review',len(q))
    st.dataframe(q[['staff_id','ward','role','shift','worked_hours','overtime_hours','fairness_gap_pct','review']],use_container_width=True,hide_index=True)
    st.caption('Use this as workforce balancing support, not as a performance or disciplinary score.')

elif page=='Scenario Lab':
    st.markdown('<div class="section-title">Scenario lab</div>', unsafe_allow_html=True)
    ward=st.selectbox('Ward',wards['ward'].tolist())
    add=st.slider('Additional staff count',0,10,2,1)
    ot=st.slider('Overtime change (hours)',-20,20,-4,1)
    s=scenario_ward(staff,ward,add,ot)
    if s['before']:
        c=st.columns(4)
        vals=[('Before load/staff',f"{s['before']['load_per_staff']:.1f}"),('After load/staff',f"{s['after']['load_per_staff']:.1f}"),('Before OT rate',f"{s['before']['overtime_rate']:.1f}%"),('After OT rate',f"{s['after']['overtime_rate']:.1f}%")]
        for col,(lab,val) in zip(c,vals): col.metric(lab,val)
        compare=pd.DataFrame({'Measure':['Load / staff','Overtime rate'], 'Before':[s['before']['load_per_staff'],s['before']['overtime_rate']], 'After':[s['after']['load_per_staff'],s['after']['overtime_rate']]})
        st.plotly_chart(px.bar(compare,x='Measure',y=['Before','After'],barmode='group',height=390),use_container_width=True)
        st.info('Scenario values are planning estimates based only on the uploaded local records.')

elif page=='Reports & Export':
    st.markdown('<div class="section-title">Reports & export</div>', unsafe_allow_html=True)
    report=wards.copy()
    report['recommendation']=np.select([report.priority.eq('Critical'),report.priority.eq('High'),report.priority.eq('Moderate')],['Urgent staffing and skill review','Priority workload rebalancing review','Monitor and rebalance'],default='Routine monitoring')
    st.dataframe(report,use_container_width=True,hide_index=True)
    csv=report.to_csv(index=False).encode('utf-8')
    st.download_button('Download ward pressure CSV',csv,'ward_pressure_report.csv','text/csv')
    st.download_button('Download staff fairness CSV',fair.to_csv(index=False).encode('utf-8'),'staff_fairness_report.csv','text/csv')
    st.markdown('<div class="small-note">All calculations are local to this session. The analyzer supports staffing planning and workload review; it does not replace nurse managers, hospital leadership, HR policy, clinical judgment, or safe staffing regulations.</div>',unsafe_allow_html=True)
