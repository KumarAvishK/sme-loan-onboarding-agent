import streamlit as st
from datetime import datetime

st.set_page_config(page_title='EXL Bank | SME Loan', page_icon='🏦', layout='wide')

st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html,body,[class*="css"]{font-family:Inter,sans-serif}.stApp{background:#f7f8fa;color:#172033}.block-container{padding-top:1rem;max-width:1240px}
.header{background:white;border-bottom:1px solid #e7ebf0;padding:12px 24px;display:flex;justify-content:space-between;margin:-1rem -2rem 1rem}.logo{font-size:22px;font-weight:800}.logo span{color:#f36f21}.top{color:#687386;font-size:12px;margin-left:22px}
.hero{background:linear-gradient(135deg,#fff,#fff7f1);border:1px solid #eee3dc;border-radius:18px;padding:34px}.hero h1{font-size:36px;margin:0}.hero p{color:#687386;max-width:700px}.card,.metric,.agent{background:#fff;border:1px solid #e3e8ee;border-radius:14px;padding:16px}.metric .v{font-size:24px;font-weight:800}.metric .l{font-size:10px;color:#7a8494;text-transform:uppercase}.agent{margin:8px 0}.small{font-size:11px;color:#748095}.pill{padding:4px 8px;border-radius:20px;font-size:10px;font-weight:700}.green{background:#e6f5ec;color:#238b57}.orange{background:#fff0e7;color:#d85c19}.blue{background:#eaf2fb;color:#3268a8}.notice{background:#fff8f3;border-left:4px solid #f36f21;padding:12px;border-radius:8px;font-size:12px}.officer{background:#111e31;color:#fff;border-radius:16px;padding:20px}.officer h2{color:#fff}.stepbar{display:flex;gap:6px;margin:18px 0}.step{flex:1;text-align:center;font-size:10px;color:#8a94a3;padding:8px;border-bottom:3px solid #dfe4ea}.active{color:#f36f21;border-color:#f36f21!important;font-weight:700}.done{color:#238b57;border-color:#238b57!important}
</style>''',unsafe_allow_html=True)

if 'layer' not in st.session_state: st.session_state.layer='Customer Portal'
if 'stage' not in st.session_state: st.session_state.stage=0
if 'uploaded' not in st.session_state: st.session_state.uploaded=set()
if 'audit' not in st.session_state: st.session_state.audit=[]
if 'assessment' not in st.session_state: st.session_state.assessment=False
if 'decision' not in st.session_state: st.session_state.decision='Pending'

def audit(a,d): st.session_state.audit.append((datetime.now().strftime('%H:%M:%S'),a,d))
def assess():
    st.session_state.assessment=True
    events=[('Application Intake Agent','Application structured'),('KYC / KYB Agent','PAN / GST / entity verification'),('Document Intelligence Agent','Documents classified and reconciled'),('Credit Bureau Agent','Bureau score 748 retrieved'),('GST / Tax Agent','Turnover reconciled at ₹4.8 Cr'),('Banking / Cash Flow Agent','Monthly surplus ₹6.8L'),('Financial Analysis Agent','DSCR 1.72'),('Fraud / Anomaly Agent','No material anomalies'),('Credit Risk Agent','Risk grade A'),('Policy Engine','Outcome REFER'),('Credit Memo Agent','Evidence-grounded memo generated')]
    st.session_state.audit=events

st.markdown('<div class="header"><div class="logo">EXL <span>Bank</span></div><div><span class="top">Business Loans</span><span class="top">How it works</span><span class="top">Support</span><span class="top">🔒 Secure</span></div></div>',unsafe_allow_html=True)

c1,c2,c3=st.columns(3)
if c1.button('👤 Customer Portal',use_container_width=True): st.session_state.layer='Customer Portal'
if c2.button('🤖 Agent Control Tower',use_container_width=True): st.session_state.layer='Agent Control Tower'
if c3.button('🧑‍💼 Credit Officer',use_container_width=True): st.session_state.layer='Credit Officer'

# CUSTOMER
if st.session_state.layer=='Customer Portal':
    st.markdown('<div class="hero"><h1>Business funding,<br><span style="color:#f36f21">simplified.</span></h1><p>Tell us what your business needs. Our digital onboarding assistant guides you through eligibility, documents and credit assessment.</p></div>',unsafe_allow_html=True)
    names=['Loan Need','Business','Documents','Assessment','Offer']
    st.markdown('<div class="stepbar">'+''.join(f'<div class="step {"active" if i==st.session_state.stage else "done" if i<st.session_state.stage else ""}">{i+1}. {n}</div>' for i,n in enumerate(names))+'</div>',unsafe_allow_html=True)
    if st.session_state.stage==0:
        st.markdown('<div class="card"><h3>How much funding do you need?</h3>',unsafe_allow_html=True)
        amt=st.number_input('Loan amount (₹)',100000,10000000,2500000,100000)
        purpose=st.selectbox('What will you use it for?', ['Working Capital','Expansion','Equipment','Other'])
        if st.button('Check eligibility',type='primary',use_container_width=True): audit('Application Intake Agent',f'{purpose} • ₹{amt:,.0f}'); st.session_state.stage=1; st.rerun()
        st.markdown('</div>',unsafe_allow_html=True)
    elif st.session_state.stage==1:
        st.markdown('<div class="card"><h3>Tell us about your business</h3>',unsafe_allow_html=True)
        st.text_input('Business name','ABC Distributors Pvt Ltd'); st.selectbox('Business constitution',['Private Limited Company','LLP','Partnership Firm','Proprietorship']); st.text_input('GSTIN','22ABCDE1234F1Z5'); st.number_input('Annual turnover (₹)',0,100000000,48000000,100000)
        st.info('The KYC/KYB agent will determine the exact checklist from entity type, loan purpose and amount.')
        if st.button('Continue to Documents',type='primary',use_container_width=True): audit('KYC / KYB Agent','Business profile initialized'); st.session_state.stage=2; st.rerun()
        st.markdown('</div>',unsafe_allow_html=True)
    elif st.session_state.stage==2:
        docs=['Company PAN','Certificate of Incorporation','GST Certificate','MOA','AOA','Director PAN','Director OVD','Board Resolution','GSTR-1','GSTR-3B','Bank Statement — 12 months','Audited Financials']
        st.markdown('<div class="card"><h3>Documents required for your business</h3><div class="small">Checklist dynamically determined by entity, purpose and facility size.</div>',unsafe_allow_html=True)
        for d in docs:
            uploaded=d in st.session_state.uploaded
            st.markdown(f'<div class="agent"><b>{d}</b> &nbsp; <span class="pill {"green" if uploaded else "orange"}">{"VALID" if uploaded else "PENDING"}</span></div>',unsafe_allow_html=True)
        pending=[d for d in docs[:-1] if d not in st.session_state.uploaded]
        if pending:
            pick=st.selectbox('Upload document',pending); f=st.file_uploader('Choose file',type=['pdf','png','jpg','jpeg'])
            if f: st.session_state.uploaded.add(pick); audit('Document Intelligence Agent',pick+' validated'); st.rerun()
            st.markdown('<div class="notice">Continue is locked until mandatory documents are present or an authorized exception is recorded.</div>',unsafe_allow_html=True)
        if st.button('Continue to Assessment',disabled=bool(pending),type='primary',use_container_width=True): st.session_state.stage=3; st.rerun()
        st.markdown('</div>',unsafe_allow_html=True)
    elif st.session_state.stage==3:
        st.markdown('<div class="card"><h3>AI-powered assessment</h3><p class="small">Specialist agents will gather evidence, calculate financial signals and apply policy.</p></div>',unsafe_allow_html=True)
        if st.button('Start assessment',type='primary',use_container_width=True): assess(); st.session_state.stage=4; st.rerun()
    else:
        a,b,c,d=st.columns(4)
        for col,v,l in [(a,'748','Bureau score'),(b,'1.72','DSCR'),(c,'₹6.8L','Monthly surplus'),(d,'A','Risk grade')]: col.markdown(f'<div class="metric"><div class="v">{v}</div><div class="l">{l}</div></div>',unsafe_allow_html=True)
        st.markdown('<br><div class="notice"><b>Policy outcome: REFER</b><br>Evidence is ready for credit-officer review. Final authorization is not automated.</div>',unsafe_allow_html=True)
        if st.button('View Credit Officer Review',type='primary',use_container_width=True): st.session_state.layer='Credit Officer'; st.rerun()

# CONTROL TOWER
elif st.session_state.layer=='Agent Control Tower':
    st.markdown('<div class="hero"><h1>Agent <span style="color:#f36f21">Control Tower</span></h1><p>Live view of specialist agents, tool/evidence flow, deterministic controls, routing and audit state.</p></div>',unsafe_allow_html=True)
    if not st.session_state.assessment:
        st.warning('No assessment has been run yet.')
        if st.button('Run demonstration assessment',type='primary'): assess(); st.rerun()
    else:
        a,b,c,d=st.columns(4)
        for col,v,l in [(a,'11','Agents executed'),(b,'100%','Evidence captured'),(c,'0','Material anomalies'),(d,'REFER','Policy outcome')]: col.markdown(f'<div class="metric"><div class="v">{v}</div><div class="l">{l}</div></div>',unsafe_allow_html=True)
        st.markdown('### Agent execution trace')
        for t,a,d in st.session_state.audit: st.markdown(f'<div class="agent"><span class="pill green">✓ COMPLETE</span> <b>{a}</b><div class="small">{d} • {t}</div></div>',unsafe_allow_html=True)
        x,y,z=st.columns(3)
        x.markdown('<div class="card"><b>Typed tools</b><br><span class="small">verify_gstin() • pull_business_bureau() • get_gst_returns() • get_bank_statements()</span></div>',unsafe_allow_html=True)
        y.markdown('<div class="card"><b>Deterministic engines</b><br><span class="small">DSCR • ratios • eligibility • document completeness • policy rules</span></div>',unsafe_allow_html=True)
        z.markdown('<div class="card"><b>Checkpoint / memory</b><br><span class="small">Application state + evidence + audit trace persisted for recovery.</span></div>',unsafe_allow_html=True)

# OFFICER
else:
    st.markdown('<div class="officer"><h2>Credit Officer Workbench</h2><div class="small">Human-in-the-loop control point — review evidence before authorization.</div></div>',unsafe_allow_html=True)
    a,b,c,d=st.columns(4)
    for col,v,l in [(a,'ABC Distributors Pvt Ltd','Applicant'),(b,'₹25L','Requested facility'),(c,'748','Bureau'),(d,'A','Risk grade')]: col.markdown(f'<div class="metric"><div class="v">{v}</div><div class="l">{l}</div></div>',unsafe_allow_html=True)
    left,right=st.columns(2)
    with left:
        st.markdown('### Evidence pack')
        for a,b,d in [('KYC / KYB','PASS','PAN, GST and entity identity'),('Documents','PASS','Mandatory set complete'),('Financials','PASS','Turnover ₹4.8 Cr • EBITDA ₹42L'),('Cash Flow','PASS','Monthly surplus ₹6.8L'),('Bureau','PASS','Score 748 • DPD 0'),('Fraud / Anomaly','PASS','No material anomalies'),('Policy','REFER','Human review required')]: st.markdown(f'<div class="agent"><b>{a}</b> <span class="pill {"green" if b=="PASS" else "orange"}">{b}</span><div class="small">{d}</div></div>',unsafe_allow_html=True)
    with right:
        st.markdown('### Agent recommendation'); st.markdown('<div class="card"><h3>Refer to Credit Officer</h3><p class="small">The agents assembled an evidence-grounded case; the deterministic policy engine routed it to HITL.</p><b>Proposed facility</b> ₹25,00,000<br><b>DSCR</b> 1.72<br><b>Risk grade</b> A<br><b>Document completeness</b> 100%</div>',unsafe_allow_html=True)
        st.markdown('### Decision')
        q1,q2,q3=st.columns(3)
        if q1.button('Approve',type='primary',use_container_width=True): st.session_state.decision='Approved by officer'; audit('Credit Officer','Final authorization: APPROVED')
        if q2.button('Reject',use_container_width=True): st.session_state.decision='Rejected by officer'; audit('Credit Officer','Final authorization: REJECTED')
        if q3.button('Request Info',use_container_width=True): st.session_state.decision='Information requested'; audit('Credit Officer','Additional evidence requested')
        st.info('Current decision: '+st.session_state.decision)
    st.markdown('### Credit memo')
    memo=f'''EXL BANK — SME CREDIT MEMO\n\nApplicant: ABC Distributors Pvt Ltd\nFacility: ₹25,00,000\nBureau: 748\nDSCR: 1.72\nMonthly cash surplus: ₹6.8L\nRisk grade: A\nPolicy outcome: REFER\nOfficer decision: {st.session_state.decision}\n\nSynthetic data for demonstration.'''
    st.download_button('Download credit memo (demo)',memo,'credit_memo_demo.txt','text/plain')
    st.markdown('### Audit trail')
    for t,a,d in reversed(st.session_state.audit): st.markdown(f'<div class="small"><b>{t}</b> — {a}: {d}</div>',unsafe_allow_html=True)

st.markdown('---')
st.caption('EXL Bank concept demonstration • Synthetic data • External government, bureau and banking integrations are represented by mock adapters. No real loan decision or disbursement occurs.')
