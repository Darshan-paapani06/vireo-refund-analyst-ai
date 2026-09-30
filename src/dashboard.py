from __future__ import annotations
from pathlib import Path
import html, json, webbrowser
import pandas as pd


def _money(x):
    return f"₹{float(x):,.0f}"

def _records(df, n=None):
    d = df.head(n).copy() if n else df.copy()
    return json.loads(d.to_json(orient='records', date_format='iso'))

def create_dashboard(finance: dict, audit: dict, ai: dict, out_html: Path, auto_open: bool=False):
    m = finance['metrics']; a = audit['summary']; am = ai['metrics']
    monthly = _records(finance['monthly'])
    q2_reason = _records(finance['q2_reason'])
    q2_agent = _records(finance['q2_agent'].head(20))
    exceptions = _records(finance['exceptions'].head(150))
    review = _records(ai['review'].head(250))
    evidence = _records(ai['validation'].head(120))

    data = json.dumps({
        'monthly': monthly, 'q2_reason': q2_reason, 'q2_agent': q2_agent,
        'exceptions': exceptions, 'review': review, 'evidence': evidence,
        'metrics': m, 'audit': a, 'ai': am
    }, ensure_ascii=False)

    page = r'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Vireo Refund Intelligence</title><style>
:root{--bg:#07111f;--panel:#0d1b2d;--panel2:#12243a;--text:#edf4ff;--muted:#9fb2cb;--line:#233a55;--accent:#67e8f9;--good:#5ee6a8;--warn:#ffca63;--bad:#ff7c8a;--purple:#b69cff}
*{box-sizing:border-box}body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:radial-gradient(circle at 15% 0%,#12335a 0,#07111f 42%);color:var(--text)}
.wrap{max-width:1500px;margin:auto;padding:28px}.hero{display:flex;justify-content:space-between;gap:24px;align-items:flex-start;margin-bottom:18px}.eyebrow{color:var(--accent);font-weight:700;letter-spacing:.13em;font-size:12px}.hero h1{font-size:32px;margin:7px 0 5px}.sub{color:var(--muted);max-width:850px;line-height:1.5}.badge{padding:9px 13px;border:1px solid #27516b;background:#0c2637;border-radius:999px;color:var(--good);font-weight:700;white-space:nowrap}
.nav{display:flex;gap:8px;flex-wrap:wrap;position:sticky;top:0;background:rgba(7,17,31,.92);backdrop-filter:blur(12px);padding:10px 0;z-index:3}.nav button{border:1px solid var(--line);background:#0b1727;color:var(--muted);padding:9px 13px;border-radius:10px;cursor:pointer}.nav button.active{background:#17314b;color:#fff;border-color:#3b6d92}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:18px 0}.card,.panel{background:linear-gradient(180deg,rgba(18,36,58,.96),rgba(11,25,42,.96));border:1px solid var(--line);border-radius:16px;box-shadow:0 12px 35px rgba(0,0,0,.15)}.card{padding:17px}.label{color:var(--muted);font-size:12px}.value{font-size:25px;font-weight:800;margin:8px 0}.hint{font-size:12px;color:var(--muted)}
.panel{padding:18px;margin:14px 0}.panel h2{margin:0 0 4px;font-size:20px}.panel h3{margin:0 0 10px;font-size:15px}.section{display:none}.section.active{display:block}.two{display:grid;grid-template-columns:1.05fr .95fr;gap:14px}.callout{padding:16px;border-left:4px solid var(--accent);background:#0a2034;border-radius:12px;line-height:1.5}.callout strong{color:white}.goal{border-left-color:var(--good)}
.chart{height:290px;display:flex;align-items:flex-end;gap:8px;padding:20px 6px 35px;border-bottom:1px solid var(--line);position:relative}.barwrap{flex:1;height:100%;display:flex;align-items:flex-end;position:relative}.bar{width:100%;background:linear-gradient(180deg,var(--accent),#3888bd);border-radius:8px 8px 2px 2px;min-height:4px}.bar:hover{filter:brightness(1.25)}.barlbl{position:absolute;bottom:-25px;width:100%;text-align:center;color:var(--muted);font-size:10px}.tooltip{position:absolute;display:none;background:#020711;border:1px solid var(--line);padding:8px;border-radius:8px;font-size:12px;pointer-events:none;z-index:5}
.hbars{display:grid;gap:9px}.hrow{display:grid;grid-template-columns:160px 1fr 110px;gap:10px;align-items:center}.track{background:#081421;border:1px solid var(--line);height:17px;border-radius:99px;overflow:hidden}.fill{height:100%;background:linear-gradient(90deg,#8b5cf6,#67e8f9);border-radius:99px}.amt{text-align:right;font-variant-numeric:tabular-nums}.name{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#d9e7f7}
.controls{display:flex;gap:9px;flex-wrap:wrap;margin:12px 0}input,select{background:#071422;color:white;border:1px solid var(--line);border-radius:9px;padding:9px 11px;min-width:220px}table{width:100%;border-collapse:collapse;font-size:12px}th{color:#9fc7e8;text-align:left;border-bottom:1px solid #38536e;padding:9px;position:sticky;top:55px;background:#0d1b2d}td{padding:9px;border-bottom:1px solid #1c3047;vertical-align:top}tr:hover td{background:#122944}.scroll{max-height:510px;overflow:auto}.pill{display:inline-block;border-radius:99px;padding:4px 8px;font-size:10px;font-weight:700}.p-bad{background:#45212b;color:#ff9eaa}.p-good{background:#113a2b;color:#79eabb}.p-warn{background:#423715;color:#ffda73}.mono{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}.footer{color:var(--muted);font-size:11px;text-align:center;padding:28px}
@media(max-width:900px){.grid{grid-template-columns:repeat(2,1fr)}.two{grid-template-columns:1fr}.hero{flex-direction:column}.hrow{grid-template-columns:110px 1fr 85px}}
</style></head><body><div class="wrap">
<div class="hero"><div><div class="eyebrow">VIREO AUDIO · REFUND INTELLIGENCE ENGINE</div><h1>Finance-ready refund control room</h1><div class="sub">Reconciled money, agent/reason views, policy leakage, and measured AI assistance — all generated locally from the support export. AI never changes financial totals.</div></div><div class="badge">● Reconciled & auditable</div></div>
<div class="nav" id="nav"><button class="active" data-tab="exec">Executive</button><button data-tab="trend">Monthly Trend</button><button data-tab="reason">Reason Codes</button><button data-tab="agents">Agents</button><button data-tab="risk">Policy Exceptions</button><button data-tab="ai">AI Review</button><button data-tab="proof">Validation</button></div>
<div id="exec" class="section active"><div class="grid">
<div class="card"><div class="label">RAW EXPORT REFUNDS</div><div class="value" id="raw"></div><div class="hint">Not fit for reporting</div></div>
<div class="card"><div class="label">RECONCILED 18-MONTH REFUNDS</div><div class="value" id="clean"></div><div class="hint">Unit normalization + dedupe</div></div>
<div class="card"><div class="label">Q2 2026 REFUNDS</div><div class="value" id="q2"></div><div class="hint" id="q2t"></div></div>
<div class="card"><div class="label">Q2 POLICY VALUE AT RISK</div><div class="value" id="riskv"></div><div class="hint" id="riskc"></div></div></div>
<div class="two"><div class="panel"><h2>What changed the answer?</h2><div class="callout" id="recon"></div></div><div class="panel"><h2>Measurable business outcome</h2><div class="callout goal" id="goal"></div></div></div>
<div class="panel"><h2>Decision architecture</h2><table><tr><th>Layer</th><th>Method</th><th>Why</th></tr><tr><td>Money</td><td>Deterministic reconciliation</td><td>Board totals must be reproducible and auditable.</td></tr><tr><td>Policy control</td><td>Rule-based exception detection</td><td>Refund + replacement is explicitly disallowed.</td></tr><tr><td>AI assistance</td><td>Top-2 text suggestions</td><td>Prioritises review; never rewrites finance data.</td></tr></table></div></div>
<div id="trend" class="section"><div class="panel"><h2>Monthly refund trend</h2><div class="hint">Reporting month = ticket creation month because refund-posted timestamp is not present in the export.</div><div id="monthlyChart" class="chart"></div></div></div>
<div id="reason" class="section"><div class="panel"><h2>Q2 2026 refund reasons</h2><div class="hint">Largest buckets are investigation priorities, not proof that refunds were invalid.</div><div id="reasonBars" class="hbars" style="margin-top:18px"></div></div></div>
<div id="agents" class="section"><div class="panel"><h2>Q2 resolving agents — with team context</h2><div class="hint">High volume is not automatically poor behaviour; Returns Desk is expected to process many refunds.</div><div id="agentBars" class="hbars" style="margin-top:18px"></div></div></div>
<div id="risk" class="section"><div class="panel"><h2>Policy exception queue: refund + replacement</h2><div class="controls"><input id="riskSearch" placeholder="Search ticket, agent, team, product, reason..."><select id="riskTeam"><option value="">All teams</option></select></div><div class="scroll"><table><thead><tr><th>Ticket</th><th>Month</th><th>Agent / team</th><th>Product</th><th>Reason</th><th>Refund</th><th>Replacement cost</th><th>Value at risk</th></tr></thead><tbody id="riskBody"></tbody></table></div></div></div>
<div id="ai" class="section"><div class="grid"><div class="card"><div class="label">FIXED HOLDOUT</div><div class="value" id="holdout"></div><div class="hint">Unseen labelled tickets</div></div><div class="card"><div class="label">TOP-1 ACCURACY</div><div class="value" id="top1"></div><div class="hint">Too weak for auto-recoding</div></div><div class="card"><div class="label">ACTUAL CODE IN TOP-2</div><div class="value" id="top2"></div><div class="hint">Useful for human review</div></div><div class="card"><div class="label">AI GOVERNANCE</div><div class="value" style="font-size:18px">Review-only</div><div class="hint">Never changes money or recorded code</div></div></div><div class="panel"><h2>High-confidence AI review queue</h2><div class="controls"><input id="aiSearch" placeholder="Search ticket, agent, selected code, suggestion..."></div><div class="scroll"><table><thead><tr><th>Ticket</th><th>Selected</th><th>AI #1</th><th>Confidence</th><th>AI #2</th><th>Confidence</th><th>Refund</th><th>Agent</th></tr></thead><tbody id="aiBody"></tbody></table></div></div></div>
<div id="proof" class="section"><div class="two"><div class="panel"><h2>Financial reconciliation proof</h2><div id="proofRecon" class="callout"></div></div><div class="panel"><h2>AI proof</h2><div id="proofAi" class="callout"></div></div></div><div class="panel"><h2>What this tool deliberately does not claim</h2><ul style="line-height:1.8;color:#c8d7e9"><li>Agent refund volume alone is not evidence of bad behaviour.</li><li>AI suggestions are not authoritative reason-code corrections.</li><li>Ticket creation month is a reporting proxy until Finance provides refund-posted timestamp.</li><li>The savings estimate assumes the Q2 mix and unit costs remain comparable.</li></ul></div></div>
<div class="footer">Generated locally by Vireo Refund Intelligence Engine · No paid model/API call required at runtime</div></div><div class="tooltip" id="tooltip"></div>
<script>
const D=__DATA__; const money=n=>'₹'+Number(n||0).toLocaleString('en-IN',{maximumFractionDigits:0}); const pct=n=>(Number(n)*100).toFixed(1)+'%';
raw.textContent=money(D.audit.raw_refund_total);clean.textContent=money(D.audit.clean_refund_total);q2.textContent=money(D.metrics.q2_2026_refund_total);q2t.textContent=D.metrics.q2_2026_refund_tickets+' refund tickets';riskv.textContent=money(D.metrics.q2_dual_remedy_value_at_risk);riskc.textContent=D.metrics.q2_dual_remedy_cases+' refund + replacement cases';
recon.innerHTML=`The raw export contains <strong>${D.audit.duplicate_extra_rows_removed.toLocaleString()}</strong> extra migration/re-import rows. Across duplicated refund tickets, <strong>${D.audit.exact_100x_pairs}/${D.audit.cross_system_refund_pairs}</strong> cross-system pairs show the exact 100:1 legacy/current money ratio used by the reconciliation.`;
goal.innerHTML=`Reduce Q2-style dual-remedy cases from <strong>${D.metrics.q2_dual_remedy_cases}</strong> to <strong>≤ ${D.metrics.goal_target_cases_per_quarter}</strong> per quarter. Estimated value: <strong>${money(D.metrics.goal_quarterly_savings)}/quarter</strong> or <strong>${money(D.metrics.goal_annualized_savings)}/year</strong>.`;
holdout.textContent=D.ai.holdout_size.toLocaleString();top1.textContent=pct(D.ai.top1_accuracy);top2.textContent=pct(D.ai.top2_accuracy);
proofRecon.innerHTML=`<strong>${D.audit.exact_100x_pairs}/${D.audit.cross_system_refund_pairs}</strong> duplicated cross-system refund pairs match the 100× normalization exactly, for an observed pair-validation error rate of <strong>${pct(D.audit.normalization_pair_error_rate)}</strong>.`;
proofAi.innerHTML=`The reason assistant was measured on a fixed holdout of <strong>${D.ai.holdout_size}</strong> tickets. Top-1 accuracy is <strong>${pct(D.ai.top1_accuracy)}</strong>; the actual code is in the model's top two <strong>${pct(D.ai.top2_accuracy)}</strong> of the time. Therefore the feature is review-only.`;

document.querySelectorAll('.nav button').forEach(b=>b.onclick=()=>{document.querySelectorAll('.nav button').forEach(x=>x.classList.remove('active'));b.classList.add('active');document.querySelectorAll('.section').forEach(s=>s.classList.remove('active'));document.getElementById(b.dataset.tab).classList.add('active')});
function bars(data,el,labelKey,valKey){const max=Math.max(...data.map(x=>+x[valKey])); el.innerHTML=data.map(x=>`<div class="hrow"><div class="name" title="${String(x[labelKey]).replaceAll('"','&quot;')}">${x[labelKey]}</div><div class="track"><div class="fill" style="width:${(+x[valKey]/max*100).toFixed(1)}%"></div></div><div class="amt">${money(x[valKey])}</div></div>`).join('')}
bars(D.q2_reason,reasonBars,'refund_reason_code','amount_inr');bars(D.q2_agent.map(x=>({...x,label:x.name+' · '+x.team})),agentBars,'label','amount_inr');
const maxM=Math.max(...D.monthly.map(x=>+x.refund_amount_inr));monthlyChart.innerHTML=D.monthly.map(x=>`<div class="barwrap"><div class="bar" data-tip="${x.report_month}: ${money(x.refund_amount_inr)} · ${x.refund_tickets} tickets" style="height:${Math.max(3,+x.refund_amount_inr/maxM*100)}%"></div><div class="barlbl">${x.report_month.slice(2)}</div></div>`).join('');
const tip=document.getElementById('tooltip');document.querySelectorAll('.bar').forEach(b=>{b.onmousemove=e=>{tip.style.display='block';tip.style.left=(e.pageX+10)+'px';tip.style.top=(e.pageY-35)+'px';tip.textContent=b.dataset.tip};b.onmouseleave=()=>tip.style.display='none'});
const teams=[...new Set(D.exceptions.map(x=>x.team).filter(Boolean))].sort();teams.forEach(t=>riskTeam.insertAdjacentHTML('beforeend',`<option>${t}</option>`));
function renderRisk(){const q=riskSearch.value.toLowerCase(),team=riskTeam.value;const rows=D.exceptions.filter(x=>(!team||x.team===team)&&JSON.stringify(x).toLowerCase().includes(q)).slice(0,150);riskBody.innerHTML=rows.map(x=>`<tr><td class="mono">${x.ticket_id}</td><td>${x.report_month}</td><td>${x.name}<br><span class="hint">${x.team}</span></td><td>${x.product_name||x.product_sku}</td><td><span class="pill p-bad">${x.refund_reason_code}</span></td><td>${money(x.refund_amount_clean)}</td><td>${money(x.replacement_planning_cost)}</td><td><strong>${money(x.dual_remedy_value_at_risk)}</strong></td></tr>`).join('')};riskSearch.oninput=renderRisk;riskTeam.onchange=renderRisk;renderRisk();
function renderAI(){const q=aiSearch.value.toLowerCase();const rows=D.review.filter(x=>JSON.stringify(x).toLowerCase().includes(q)).slice(0,200);aiBody.innerHTML=rows.map(x=>`<tr><td class="mono">${x.ticket_id}</td><td><span class="pill p-warn">${x.refund_reason_code}</span></td><td><strong>${x.ai_top1}</strong></td><td>${pct(x.ai_top1_confidence)}</td><td>${x.ai_top2}</td><td>${pct(x.ai_top2_confidence)}</td><td>${money(x.refund_amount_clean)}</td><td>${x.name}<br><span class="hint">${x.team}</span></td></tr>`).join('')};aiSearch.oninput=renderAI;renderAI();
</script></body></html>'''
    page = page.replace('__DATA__', data)
    out_html.write_text(page, encoding='utf-8')
    if auto_open:
        webbrowser.open(out_html.resolve().as_uri())
