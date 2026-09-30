from __future__ import annotations
import re
import pandas as pd

def money(x): return f"₹{float(x):,.0f}"
def pct(x): return 'n/a' if x is None else f"{100*float(x):.1f}%"

def _tool_plan(q):
    q=q.lower()
    tools=[]
    if any(k in q for k in ['increase','rise','why','driver','changed','quarter']): tools += ['period_compare','reason_drivers']
    if any(k in q for k in ['product','sku','model','lot','manufactur']): tools += ['product_root_cause','lot_signals']
    if any(k in q for k in ['agent','team','who']): tools += ['agent_context']
    if any(k in q for k in ['policy','replacement','dual','leak','exception','risk']): tools += ['policy_risk']
    if any(k in q for k in ['ai','model','accuracy','reason code','classifier']): tools += ['ai_validation']
    if any(k in q for k in ['quality','missing','reconcile','wrong','crore','trust','proof']): tools += ['data_quality','reconciliation']
    if not tools: tools=['executive']
    return list(dict.fromkeys(tools))

def answer(question, ws):
    q=(question or '').strip()
    f,a,ai,adv=ws['finance'],ws['audit'],ws['ai'],ws['advanced']
    m=f['metrics']; am=ai['metrics']; au=a['summary']
    plan=_tool_plan(q)
    findings=[]; evidence=[]; cautions=[]; actions=[]
    if 'executive' in plan:
        findings.append(f"Reconciled refunds are {money(au['clean_refund_total'])}; {m['focus_period_label']} contributed {money(m['focus_refund_total'])} across {m['focus_refund_tickets']} refund tickets.")
        evidence += [f"Raw export: {money(au['raw_refund_total'])}", f"Duplicate extras removed: {au['duplicate_extra_rows_removed']:,}", f"Dual-remedy risk: {m['focus_dual_remedy_cases']} cases / {money(m['focus_dual_remedy_value_at_risk'])}"]
        actions.append('Open Policy Risk first, then inspect the largest reason and product signals.')
    if 'period_compare' in plan:
        c=adv['quarter_compare']; direction='up' if c['delta']>=0 else 'down'
        findings.append(f"Latest-quarter refunds are {direction} {money(abs(c['delta']))} ({pct(abs(c['pct']) if c['pct'] is not None else None)}) versus the prior three months.")
        evidence += [f"Current: {money(c['current_total'])}", f"Previous ({c['previous_label']}): {money(c['previous_total'])}"]
        cautions.append('Month attribution uses ticket creation date because no refund-posted accounting timestamp is present.')
    if 'reason_drivers' in plan:
        d=adv['reason_drivers'].head(4)
        if len(d):
            evidence += [f"{r.refund_reason_code}: Δ {money(r.delta)}" for r in d.itertuples()]
            findings.append('The reason-code decomposition identifies which buckets contributed most to the quarter-on-quarter movement; treat this as a prioritisation signal, not proof of improper refunds.')
    if 'product_root_cause' in plan:
        d=adv['product'].head(5)
        evidence += [f"{r.product_sku}: {money(r.refund_amount)} across {int(r.refund_tickets)} tickets" for r in d.itertuples()]
        findings.append('Product concentration can explain refund demand that would otherwise be misattributed to agent behaviour.')
        actions.append('Compare high-value product signals with lot-level concentration before coaching agents.')
    if 'lot_signals' in plan and len(adv['lots']):
        d=adv['lots'].head(5)
        evidence += [f"Lot {getattr(r,'order_lot_code',getattr(r,'lot_code','?'))} / {r.product_sku}: {money(r.refund_amount)}" for r in d.itertuples()]
        cautions.append('Lot concentration is a signal only; shipment volume by lot is not available, so this is not a defect rate.')
    if 'agent_context' in plan:
        d=f['focus_agent'].head(5)
        evidence += [f"{r.name} ({r.team}): {money(r.amount_inr)} / {int(r.tickets)} tickets" for r in d.itertuples()]
        findings.append('Highest refund value should be read with team role and case mix. Returns Desk is expected to process most refunds by design.')
        cautions.append('Do not rank agent quality from refund value alone; volume and assigned work differ by team/tier.')
    if 'policy_risk' in plan:
        findings.append(f"{m['focus_dual_remedy_cases']} focus-quarter tickets show both refund and replacement, with {money(m['focus_dual_remedy_value_at_risk'])} combined planning value at risk.")
        evidence += [f"Refund component: {money(m['focus_dual_remedy_refunds'])}", f"Replacement-cost component: {money(m['focus_dual_remedy_replacement_cost'])}"]
        actions.append(f"Target ≤{m['goal_target_cases_per_quarter']} cases per comparable quarter; estimated opportunity {money(m['goal_quarterly_savings'])}/quarter.")
    if 'ai_validation' in plan:
        findings.append(f"The local reason-code model is review-only: top-1 accuracy {pct(am['top1_accuracy'])}, top-2 coverage {pct(am['top2_accuracy'])} on {am['holdout_size']} holdout tickets.")
        cautions.append('Historical reason codes are proxy labels, not objective ground truth; the model never changes money or source codes automatically.')
        actions.append('Review high-confidence disagreements with large refund values first.')
    if 'reconciliation' in plan:
        findings.append(f"The export is unsafe to sum raw: {money(au['raw_refund_total'])} becomes {money(au['clean_refund_total'])} after legacy-unit normalization and ticket deduplication.")
        evidence += [f"{au['exact_100x_pairs']}/{au['cross_system_refund_pairs']} cross-system refund pairs show the exact 100:1 pattern", f"Observed pair error: {pct(au['normalization_pair_error_rate'])}"]
    if 'data_quality' in plan:
        for r in adv['data_quality'].itertuples(): evidence.append(f"{r.field}: {int(r.missing)} missing ({pct(r.missing_pct)})")
    return {'plan':plan,'finding':' '.join(findings),'evidence':evidence[:12],'caution':' '.join(dict.fromkeys(cautions)) or 'Large values are investigation priorities, not evidence of misconduct.','next_action':' '.join(dict.fromkeys(actions)) or 'Drill into the relevant evidence table and export the supporting rows.'}
