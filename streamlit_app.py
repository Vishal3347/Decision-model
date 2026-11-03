from __future__ import annotations
import os, sys, json
from pathlib import Path
from dataclasses import replace

import streamlit as st
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))
from app.main import AppState
from app.config import get_settings
from app.db import q, q1, loads
from app.schemas import Mode, StepEdit
from app.engine import preferences as prefs_mod

st.set_page_config(page_title="Decision Intelligence Simulator", page_icon="🧭", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
.stApp { background:#0b1020; color:#e8edf7; }
[data-testid="stSidebar"] { background:#10182b; border-right:1px solid #26334b; }
[data-testid="stMetric"] { background:#121d32; border:1px solid #273651; padding:14px 16px; border-radius:12px; }
[data-testid="stMetricValue"] { color:#f3f6ff; font-weight:750; }
[data-testid="stMetricLabel"] { color:#9eacc5; }
div[data-testid="stVerticalBlockBorderWrapper"] { border-color:#283752 !important; border-radius:12px; }
.stButton>button { border-radius:8px; border:1px solid #354765; background:#17243b; color:#eaf0ff; font-weight:600; }
.stButton>button[kind="primary"] { background:#6475e8; border-color:#6475e8; color:white; }
.stTextInput input,.stTextArea textarea,.stSelectbox div[data-baseweb="select"] { background:#111c30; color:#e8edf7; }
.small-muted { color:#9aa9c2; font-size:12px; }
.hero { padding:18px 22px; border:1px solid #2a3a59; border-radius:14px; background:linear-gradient(120deg,#17243c,#111a2e); margin-bottom:18px; }
.hero h1 { margin:0; font-size:26px; letter-spacing:-.6px; }
.hero p { margin:5px 0 0; color:#9eacc5; font-size:13px; }
.pill { display:inline-block; padding:3px 9px; border-radius:30px; background:#1c3150; color:#aebfff; font-size:11px; margin-right:5px; }
hr { border-color:#263651; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_state():
    settings = replace(get_settings(), database_path=os.environ.get("DATABASE_PATH", "/tmp/decision_intelligence_simulator.db"), sync_runs=True, stage_delay_ms=0)
    return AppState(settings)

S = get_state(); svc = S.svc; orch = S.orch; db = S.db

def refresh():
    st.rerun()

def rows(sql, params=()):
    with db.connect() as conn: return q(conn, sql, params)

def one(sql, params=()):
    with db.connect() as conn: return q1(conn, sql, params)

def fmt(v):
    return str(v).replace('_',' ').title() if v is not None else '—'

def badge(v):
    colors = {'Critical':'#7f1d1d','High':'#78350f','Medium':'#713f12','Low':'#14532d','pending':'#713f12','processed':'#14532d','failed':'#7f1d1d','AUTO_EXECUTE':'#14532d','ESCALATE':'#7f1d1d','DRAFT_AND_APPROVE':'#713f12'}
    c=colors.get(str(v), '#263651')
    st.markdown(f'<span class="pill" style="background:{c};color:#f4f6fb">{fmt(v)}</span>', unsafe_allow_html=True)

def header(title, subtitle):
    st.markdown(f'<div class="hero"><h1>{title}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True)

def current_mode():
    with db.connect() as conn: return orch.mode(conn).value

def set_mode(mode):
    with db.connect() as conn:
        from app.db import set_setting
        set_setting(conn, 'mode', mode)
        orch.log(conn, 'Mode', f'Operating mode switched to {fmt(mode)}.')

# Sidebar navigation mirrors the original application sections.
with st.sidebar:
    st.markdown("## 🧭 Decision Intelligence")
    st.caption("SIMULATOR · EXECUTIVE WORKSPACE")
    page = st.radio("WORKSPACE", ["Dashboard", "Smart Inbox", "Decision Models", "Approval Centre", "Scenarios", "Activity", "Briefing"], label_visibility="collapsed")
    st.divider()
    st.caption("OPERATING MODE")
    mode = st.selectbox("Mode", ["AUTONOMOUS", "HUMAN_CONTROLLED"], index=0 if current_mode()=="AUTONOMOUS" else 1, format_func=fmt, label_visibility="collapsed")
    if mode != current_mode(): set_mode(mode); st.toast("Operating mode updated")
    st.caption(f"LLM · {S.provider.public_info.get('provider','mock') if isinstance(S.provider.public_info,dict) else 'mock'}")
    if st.button("↻ Reset demo data", use_container_width=True):
        svc.reset(); st.success("Demo data reset."); refresh()
    st.markdown("<div class='small-muted'>All actions are simulated. No real emails, payments, contracts or records are changed.</div>", unsafe_allow_html=True)

# ---------------- Dashboard ----------------
if page == "Dashboard":
    header("Executive Dashboard", "A live overview of decisions, risk, approvals and agent activity.")
    d=svc.dashboard(); m=d['metrics']
    cols=st.columns(4)
    metrics=[("Emails processed",f"{m['emails_processed']} / {m['total_emails']}"),("Autonomous actions",m['autonomous_actions']),("Pending approvals",m['pending_approvals']),("Critical alerts",m['critical_alerts']), ("Follow-up tasks",m['tasks_awaiting_followup']), ("Avg decision time",f"{m['avg_decision_ms']} ms" if m['avg_decision_ms'] is not None else '—'), ("Automation success",f"{m['automation_success_rate']}%" if m['automation_success_rate'] is not None else '—')]
    for i,(label,val) in enumerate(metrics):
        with cols[i%4]: st.metric(label,val)
    st.divider(); a,b,c=st.columns([1.2,1,1])
    with a:
        st.subheader("Priority distribution")
        p=pd.DataFrame(d['priority_distribution']).set_index('label')
        if p['count'].sum(): st.bar_chart(p, height=220)
        else: st.info("Process the inbox to see priority distribution.")
    with b:
        st.subheader("Task completion")
        t=d['task_completion']; st.metric("Completed",t['completed']); st.metric("Open",t['open'])
        if t['open']+t['completed']: st.progress(t['completed']/(t['open']+t['completed']))
    with c:
        st.subheader("Decisions made")
        if d['decision_distribution']: st.dataframe(pd.DataFrame(d['decision_distribution']), hide_index=True, use_container_width=True)
        else: st.info("No decisions yet.")
    left,right=st.columns(2)
    with left:
        st.subheader("Pending decisions")
        if d['pending_decisions']:
            st.dataframe(pd.DataFrame(d['pending_decisions'])[['subject','reason','priority_label','risk_label']], hide_index=True, use_container_width=True)
            if st.button("Open Approval Centre →"): st.session_state['nav_target']='Approval Centre'; refresh()
        else: st.success("Nothing waiting for you.")
    with right:
        st.subheader("Recent agent activity")
        for x in d['recent_activity'][:8]: st.write(f"`{str(x.get('ts',''))[-8:]}`  {x.get('message','')}")

# ---------------- Smart Inbox ----------------
elif page == "Smart Inbox":
    header("Smart Inbox", "Inspect incoming messages, process them and compare autonomous vs human-controlled behaviour.")
    f1,f2,f3,f4=st.columns([2,1,1,1])
    search=f1.text_input("Search emails", placeholder="Sender, subject or content")
    cats=sorted({r['category'] for r in rows('SELECT DISTINCT category FROM emails')})
    cat=f2.selectbox("Category",["All"]+cats); pri=f3.selectbox("Priority",["All","Critical","High","Medium","Low"]); status=f4.selectbox("Status",["All","new","processing","processed","awaiting_approval","failed","archived"])
    order=st.selectbox("Sort",["Newest","Oldest","Priority","Sender"], horizontal=True)
    sql="SELECT * FROM emails WHERE 1=1"; params=[]
    if search: sql+=" AND (subject LIKE ? OR body LIKE ? OR sender_name LIKE ?)"; params += [f"%{search}%"]*3
    if cat!="All": sql+=" AND category=?"; params.append(cat)
    if pri!="All": sql+=" AND priority=?"; params.append(pri)
    if status!="All": sql+=" AND status=?"; params.append(status)
    sql += {"Newest":" ORDER BY timestamp DESC","Oldest":" ORDER BY timestamp ASC","Priority":" ORDER BY CASE priority WHEN 'Critical' THEN 0 WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END, timestamp DESC","Sender":" ORDER BY sender_name ASC"}[order]
    emails=rows(sql,params)
    c1,c2=st.columns([3,1]); c1.caption(f"{len(emails)} messages")
    if c2.button("▶ Process entire inbox", type="primary", use_container_width=True):
        ids=svc.unprocessed_ids()
        if ids: svc.start_run('inbox',ids,None,0); st.success(f"Processed {len(ids)} messages."); refresh()
        else: st.info("No unprocessed emails. Reset demo data to start again.")
    if emails:
        labels=[f"{e['id']} · {e['sender_name']} — {e['subject']} [{e['status']}]" for e in emails]
        chosen=st.selectbox("Select an email",labels)
        e=emails[labels.index(chosen)]
        with st.container(border=True):
            st.subheader(e['subject']); st.caption(f"{e['sender_name']} <{e['sender_email']}> · {e['timestamp']} · {e['category']} · {e['id']}")
            st.write(e['body'])
            x,y,z=st.columns(3)
            with x: badge(e['priority'])
            with y: badge(e['status'])
            with z:
                if e['status'] in ('new','failed') and st.button("Process this email",type="primary"):
                    svc.start_run('single',[e['id']],None,0); st.success("Email processed."); refresh()
            if e['decision_id']:
                rec,processed=svc.record_for(e['id'])
                st.divider(); st.subheader("Agent decision")
                st.write(rec.explanation)
                k1,k2,k3=st.columns(3); k1.metric("Priority",f"{rec.priority.score} · {rec.priority.label}"); k2.metric("Risk",f"{rec.risk.score} · {rec.risk.label}"); k3.metric("Decision time",f"{rec.duration_ms} ms")
                st.write("**Proposed plan**")
                for step in rec.plan:
                    st.write(f"• {step.title} — {step.status} · risk {step.risk_score} · {'approval required' if step.requires_approval else 'automatic' if not step.blocked_reason else 'blocked'}")
            else: st.info("Not processed yet. Process this email to see the decision trace.")
            with st.expander("Same email, two operating modes"):
                cmp=svc.compare_modes(e['id'])
                ca,cb=st.columns(2)
                for col,key in [(ca,'AUTONOMOUS'),(cb,'HUMAN_CONTROLLED')]:
                    with col:
                        st.markdown(f"**{fmt(key)}** · {cmp[key]['final_decision']}")
                        for step in cmp[key]['steps']: st.write(f"• {step['title']}: {step['behaviour']}")
            if st.button("Explore decision models for this email"):
                st.session_state['model_email']=e['id']; st.session_state['go_models']=True; st.info("Choose Decision Models in the sidebar.")
    else: st.info("No emails match these filters.")

# ---------------- Decision Models ----------------
elif page == "Decision Models":
    header("Decision Models", "Explore the reasoning behind every decision — from expected utility to policy overrides and human gates.")
    emails=rows("SELECT id,subject,status FROM emails ORDER BY timestamp DESC")
    if emails:
        ids=[e['id'] for e in emails]; default=st.session_state.get('model_email',ids[0]); idx=ids.index(default) if default in ids else 0
        eid=st.selectbox("Email",ids,index=idx,format_func=lambda x: f"{x} · {next(e['subject'] for e in emails if e['id']==x)[:65]}")
        m=svc.models(eid); st.caption(("Stored decision" if m['processed'] else "Live preview — nothing executed")+f" · {fmt(m['mode'])}")
        tabs=st.tabs(["Expected Utility","Satisficing","Decision Tree","Weighted Matrix","Rule-Based","Markov (MDP)","Human-in-the-Loop","Agent Loop"])
        with tabs[0]:
            st.caption(m['expected_utility']['formula']+". Probabilities and values are transparent heuristics.")
            st.dataframe(pd.DataFrame(m['expected_utility']['options'])[['rank','label','p_success','benefit','loss','effort','preference_adjustment','llm_bonus','expected_utility']],hide_index=True,use_container_width=True)
            st.success(f"Selected action: {m['expected_utility']['selected']}")
        with tabs[1]:
            s=m['satisficing']; st.write(f"Criteria: fit ≥ {s['criteria']['min_fit']}, risk ≤ {s['criteria']['max_risk']}, expected utility ≥ {s['criteria']['aspiration_eu']}")
            st.dataframe(pd.DataFrame(s['trace']),hide_index=True,use_container_width=True); st.info(f"Satisficer: {s['chosen']} · Optimal: {s['optimal']} · Match: {s['matches_optimal']}")
        with tabs[2]:
            for n in m['decision_tree']:
                with st.container(border=True):
                    st.write(f"**{n['rank']}. {n['label']}** {'✓ SELECTED' if n['chosen'] else ''} · Expected value {n['expected_value']} · Risk {n['risk']}")
                    st.dataframe(pd.DataFrame(n['branches']),hide_index=True,use_container_width=True)
        with tabs[3]:
            wm=m['weighted_matrix']; st.dataframe(pd.DataFrame([{'Dimension':k,'Score':wm[k],'Weight':wm['weights'][k],'Contribution':wm['contributions'][k]} for k in ['urgency','business_impact','time_sensitivity','customer_importance']]),hide_index=True,use_container_width=True)
            st.metric("Priority score",f"{wm['score']} · {wm['label']}")
            st.caption("Weights can be configured in the original backend; this view displays the active scoring matrix.")
        with tabs[4]:
            rb=m['rule_based']; st.write(f"LLM proposed **{rb['llm_proposed']}** → final **{rb['final']}** · policy override: **{rb['overridden']}**")
            for r in rb['triggered']:
                with st.container(border=True): st.write(f"**{r['rule_id']} · {r['name']}** — {r['kind']}"); st.caption(r['description']); st.write(f"→ {r['effect']} {r.get('detail','')}")
            with st.expander(f"All {len(rb['all_rules'])} rules"): st.dataframe(pd.DataFrame(rb['all_rules']),hide_index=True,use_container_width=True)
        with tabs[5]:
            st.warning(m['mdp']['note']); st.dataframe(pd.DataFrame(m['mdp']['trajectory']),hide_index=True,use_container_width=True); st.dataframe(pd.DataFrame(m['mdp']['q_values']),hide_index=True,use_container_width=True)
        with tabs[6]:
            h=m['human_in_loop']; st.metric("Overall risk",f"{h['overall_risk']} · {h['risk_label']}"); st.write(f"Human approval required: **{h['requires_human']}**")
            st.dataframe(pd.DataFrame(h['steps']),hide_index=True,use_container_width=True)
            for r in h['routing']: st.write(f"{'YES' if r['answer'] else 'NO'} · {r['question']} — {r['evidence']}")
        with tabs[7]:
            for l in m['agent_loop']:
                with st.container(border=True): st.write(f"**Iteration {l['iteration']}** · {l['tool']}"); st.write(f"Observe: {l['observe']}"); st.write(f"Reason: {l['reason']}"); st.write(f"Gate: {l['gate']} · Result: {l['result']}"); st.caption(f"Decide again: {l['decide_again']}")
    else: st.info("No emails available.")

# ---------------- Approval Centre ----------------
elif page == "Approval Centre":
    header("Approval Centre", "Human-in-the-loop controls. Every proposed action is revalidated before simulated execution.")
    approvals=rows("SELECT a.*,e.subject,e.sender_name,e.sender_email,e.body,e.category,d.priority_score,d.priority_label,d.risk_score,d.risk_label,d.final_decision,d.intent,d.summary,d.mode FROM approvals a JOIN emails e ON e.id=a.email_id JOIN decisions d ON d.id=a.decision_id ORDER BY (a.status='pending') DESC,d.priority_score DESC,a.id DESC")
    pending=[a for a in approvals if a['status']=='pending']; done=[a for a in approvals if a['status']!='pending']
    st.subheader(f"Pending approvals ({len(pending)})")
    if not pending: st.success("No pending approvals. Process the inbox or run a scenario to generate requests.")
    for a in pending:
        with st.container(border=True):
            st.subheader(a['subject']); st.caption(f"{a['sender_name']} · {a['email_id']} · {fmt(a['mode'])}")
            x,y,z=st.columns(3); x.metric("Priority",a['priority_score']); y.metric("Risk",a['risk_score']); z.write(f"Status: {a['status']}")
            l,r=st.columns(2)
            with l: st.markdown("**Original email**"); st.text(a['body'][:1800])
            with r: st.markdown("**Decision summary**"); st.write(a['summary']); st.markdown("**Why approval is needed**"); st.write(a['reason']); st.caption("Rules: "+str(loads(a['rule_ids_json'],[])))
            proposed=loads(a['proposed_steps_json'],[])
            st.markdown("**Proposed actions (simulated)**")
            for step in proposed: st.write(f"• {step.get('title')} · {step.get('tool')} · risk {step.get('risk_score')} · params `{json.dumps(step.get('params',{}),ensure_ascii=False)}`")
            feedback=st.text_input("Optional feedback",key=f"fb_{a['id']}",placeholder="Recorded as a preference signal; does not retrain the model")
            c1,c2=st.columns(2)
            with c1:
                if st.button("✓ Approve & execute",key=f"ap_{a['id']}",type="primary",use_container_width=True):
                    try: res=orch.approve(a['id'],feedback or None); st.success("Approval resolved and simulated actions executed."); st.json(res); refresh()
                    except Exception as ex: st.error(str(ex))
            with c2:
                if st.button("✕ Reject",key=f"re_{a['id']}",use_container_width=True):
                    try: orch.reject(a['id'],feedback or None); st.warning("Approval rejected."); refresh()
                    except Exception as ex: st.error(str(ex))
            with st.expander("Modify proposed action parameters"):
                edited=[]
                for i,step in enumerate(proposed):
                    raw=st.text_area(f"{step.get('title')} parameters (JSON)",json.dumps(step.get('params',{}),indent=2),key=f"edit_{a['id']}_{i}")
                    edited.append((step,raw))
                modfb=st.text_input("Modification feedback",key=f"mfb_{a['id']}")
                if st.button("Apply edits & execute",key=f"mod_{a['id']}"):
                    try:
                        edits=[StepEdit(step_id=s['step_id'],tool=s['tool'],params=json.loads(raw)) for s,raw in edited]
                        res=orch.modify(a['id'],edits,modfb or None); st.success("Modified action revalidated."); st.json(res); refresh()
                    except Exception as ex: st.error(f"Could not apply edits: {ex}")
    if done:
        st.subheader("Approval history")
        st.dataframe(pd.DataFrame([{k:a.get(k) for k in ['id','subject','email_id','status','reason','feedback','created_at','resolved_at']} for a in done]),hide_index=True,use_container_width=True)
    with st.expander("Learned preferences (feedback counters)"):
        with db.connect() as conn: prefs=prefs_mod.summary(conn)
        if prefs: st.dataframe(pd.DataFrame(prefs),hide_index=True,use_container_width=True)
        st.caption("Feedback adjusts preference counters used by the decision engine. The underlying language model is not retrained.")

# ---------------- Scenarios ----------------
elif page == "Scenarios":
    header("Demo Scenarios", "Repeatable enterprise situations that demonstrate agent reasoning, policy gates and simulated tool execution.")
    st.info("Each scenario run resets demo data to a clean inbox so runs are repeatable and isolated.")
    if st.button("▶ Run All Scenarios",type="primary",use_container_width=True):
        try: svc.run_scenario(None,0); st.success("All scenarios completed."); refresh()
        except Exception as ex: st.error(str(ex))
    for s in svc.scenario_status():
        with st.container(border=True):
            st.subheader(s['title']); st.write(s['blurb'])
            if s.get('final_decision'): badge(s['final_decision'])
            checks=s.get('checks') or [{'label':x,'passed':None} for x in s['expected']]
            for c in checks: st.write(f"{'✅' if c['passed'] else '◯'} {c['label']}")
            if st.button(f"Run {s['title']}",key=f"sc_{s['key']}"):
                try: svc.run_scenario(s['key'],0); st.success("Scenario completed."); refresh()
                except Exception as ex: st.error(str(ex))

# ---------------- Activity ----------------
elif page == "Activity":
    header("Agent Activity", "Chronological trace of observations, reasoning stages, policy decisions and tool execution.")
    ev=rows("SELECT * FROM activity ORDER BY id DESC LIMIT 250")
    if ev:
        st.dataframe(pd.DataFrame(ev),hide_index=True,use_container_width=True,height=650)
    else: st.info("No activity yet. Process an email or run a scenario.")

# ---------------- Briefing ----------------
elif page == "Briefing":
    header("Daily Executive Briefing", "Generate a concise leadership view from the current inbox, tasks, approvals and agent activity.")
    if st.button("▤ Generate Briefing",type="primary"):
        try: svc.briefing(); st.success("Briefing generated."); refresh()
        except Exception as ex: st.error(str(ex))
    b=svc.latest_briefing()
    if not b: st.info("No briefing yet. Generate one from the current demo state.")
    else:
        st.caption(f"Generated {b['generated_at']} · narrative by {b['narrative_provider']}")
        with st.container(border=True): st.subheader(b['headline']); st.write(b['summary'])
        sections=[('Critical issues','critical_issues'),('Pending approvals','pending_approvals'),('Completed actions','completed_actions'),('Important customer communications','customer_communications'),('Upcoming meetings','upcoming_meetings'),('Follow-ups','follow_ups'),('Tasks requiring attention','tasks_attention')]
        for i in range(0,len(sections),2):
            cols=st.columns(2)
            for col,(title,key) in zip(cols,sections[i:i+2]):
                with col:
                    with st.container(border=True):
                        st.markdown(f"**{title} ({len(b.get(key,[]))})**")
                        items=b.get(key,[])
                        if not items: st.caption("None")
                        else:
                            for item in items:
                                st.write("• "+str(item.get('subject') or item.get('title') or item.get('message') or item.get('headline') or item.get('sender_name') or item))

st.markdown("<hr><div class='small-muted'>Decision Intelligence Simulator · Educational demo · All external actions are simulated.</div>",unsafe_allow_html=True)
