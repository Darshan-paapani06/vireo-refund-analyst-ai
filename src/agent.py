from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class AgentAnswer:
    title: str
    answer: str
    evidence: list[str]
    caution: str
    next_action: str
    intent: str


def _money(x: float) -> str:
    return f"₹{float(x):,.0f}"


def _pct(x: float) -> str:
    return f"{100*float(x):.1f}%"


def _month_name(s: str) -> str:
    try:
        return pd.Period(s, freq="M").strftime("%b %Y")
    except Exception:
        return str(s)


def answer_question(question: str, finance: dict, audit: dict, ai: dict) -> AgentAnswer:
    q = re.sub(r"\s+", " ", (question or "").strip().lower())
    m = finance["metrics"]
    a = audit["summary"]
    am = ai["metrics"]
    monthly = finance["monthly"].copy()
    reason = finance["focus_reason"].copy()
    agents = finance["focus_agent"].copy()
    exceptions = finance["focus_exceptions"].copy()
    focus_label = m["focus_period_label"]

    if not q:
        q = "executive summary"

    if any(k in q for k in ["crore", "reconcile", "wrong total", "overstat", "duplicate", "legacy"]) or ("raw" in q and any(k in q for k in ["wrong", "why", "total"])):
        return AgentAnswer(
            title="Why the raw refund total is wrong",
            answer=(
                f"The raw export totals {_money(a['raw_refund_total'])}, but the reconciled total is "
                f"{_money(a['clean_refund_total'])}. The gap is driven by two data-quality issues: legacy monetary "
                f"values require a 100× unit normalization, and migration/re-import created duplicate ticket rows."
            ),
            evidence=[
                f"{a['duplicate_extra_rows_removed']:,} extra rows removed by ticket_id.",
                f"{a['exact_100x_pairs']}/{a['cross_system_refund_pairs']} duplicated cross-system refund pairs validate the exact 100:1 ratio.",
                f"Observed normalization pair error rate: {_pct(a['normalization_pair_error_rate'])}.",
            ],
            caution="The 100× rule is evidenced for the supplied export pattern; a materially different source system should be revalidated before applying it.",
            next_action="Use the reconciled total for reporting and keep the pair-level evidence with the board pack.",
            intent="reconciliation",
        )

    if any(k in q for k in ["reason", "driver", "driving", "why refund", "goodwill", "gw-other"]):
        top = reason.head(3)
        if len(top) == 0:
            return AgentAnswer("Reason-code analysis", "No refund reason data is available in the current focus period.", [], "No conclusion can be drawn without coded refunds.", "Check the input schema and period coverage.", "reasons")
        first = top.iloc[0]
        total = float(reason["amount_inr"].sum()) or 1
        evidence = [f"{r.refund_reason_code}: {_money(r.amount_inr)} across {int(r.tickets)} tickets." for r in top.itertuples()]
        return AgentAnswer(
            title=f"Refund drivers — {focus_label}",
            answer=(
                f"{first['refund_reason_code']} is the largest coded refund bucket at {_money(first['amount_inr'])}, "
                f"or {first['amount_inr']/total:.1%} of refund value in {focus_label}. That makes it the first review queue, "
                "not proof that those refunds were invalid."
            ),
            evidence=evidence,
            caution="Reason codes are agent-selected operational labels. Volume concentration is an investigation signal, not evidence of misconduct or incorrect refunds.",
            next_action="Sample the largest reason bucket against customer messages and closing notes, then compare the AI top-2 suggestions only as review assistance.",
            intent="reasons",
        )

    if any(k in q for k in ["agent", "who", "give away", "highest refund", "top agent"]):
        top = agents.head(5)
        if len(top) == 0:
            return AgentAnswer("Agent analysis", "No resolving-agent refund data is available for the current focus period.", [], "Agent comparisons require resolved refund tickets and roster matches.", "Check agent_id joins and roster coverage.", "agents")
        evidence = [f"{r.name} ({r.team}): {_money(r.amount_inr)} across {int(r.tickets)} tickets." for r in top.itertuples()]
        leader = top.iloc[0]
        return AgentAnswer(
            title=f"Resolving-agent view — {focus_label}",
            answer=(
                f"{leader['name']} has the highest resolving-agent refund value in {focus_label} at {_money(leader['amount_inr'])}. "
                "That should not be interpreted as 'giving away money' without team context, because refund-processing ownership is structural."
            ),
            evidence=evidence,
            caution="Agent refund value is an ownership metric, not a performance score. Team, tier, case mix and policy exceptions matter before escalation.",
            next_action="Prioritise agents with policy exceptions or unusual reason mix rather than ranking agents by refund value alone.",
            intent="agents",
        )

    if any(k in q for k in ["policy", "replacement", "dual", "leak", "risk", "exception"]):
        return AgentAnswer(
            title=f"Policy-control opportunity — {focus_label}",
            answer=(
                f"I found {m['focus_dual_remedy_cases']} refund tickets in {focus_label} that also show a replacement. "
                f"Their combined refund plus replacement planning cost is {_money(m['focus_dual_remedy_value_at_risk'])}."
            ),
            evidence=[
                f"Refund component: {_money(m['focus_dual_remedy_refunds'])}.",
                f"Replacement planning-cost component: {_money(m['focus_dual_remedy_replacement_cost'])}.",
                f"Exception queue contains {len(exceptions):,} cases in the focus period.",
            ],
            caution="The flag identifies records that satisfy the data rule. Confirm operational context before treating every row as realized financial leakage.",
            next_action=f"Reduce cases from {m['focus_dual_remedy_cases']} to ≤ {m['goal_target_cases_per_quarter']} per comparable quarter and review the highest-value exceptions first.",
            intent="risk",
        )

    if any(k in q for k in ["ai", "model", "accuracy", "classifier", "confidence", "reason assistant"]):
        return AgentAnswer(
            title="AI reason-code assistant — measured use",
            answer=(
                f"The local text model reaches {_pct(am['top1_accuracy'])} top-1 accuracy on a fixed holdout of {am['holdout_size']} tickets. "
                f"The actual recorded code appears in the model's top two suggestions {_pct(am['top2_accuracy'])} of the time. "
                "That is useful for review prioritisation, but not safe for automatic recoding."
            ),
            evidence=[
                f"Labelled refund tickets: {am['labelled_refund_tickets']:,}.",
                f"Fixed holdout: {am['holdout_size']:,}.",
                f"Top-1: {_pct(am['top1_accuracy'])}; top-2 coverage: {_pct(am['top2_accuracy'])}.",
            ],
            caution="The benchmark uses existing reason codes as labels, so it measures agreement with historical coding rather than objective ground truth.",
            next_action="Keep the model review-only and manually inspect high-confidence disagreements with large refund values.",
            intent="ai",
        )

    if any(k in q for k in ["trend", "month", "increase", "decrease", "spike", "changed"]):
        if len(monthly) < 2:
            return AgentAnswer("Monthly trend", "There is not enough monthly history to calculate a trend.", [], "At least two reporting months are needed.", "Load a longer history.", "trend")
        d = monthly.sort_values("report_month").copy()
        d["delta"] = d["refund_amount_inr"].diff()
        peak = d.loc[d["refund_amount_inr"].idxmax()]
        rise = d.loc[d["delta"].idxmax()] if d["delta"].notna().any() else peak
        latest = d.iloc[-1]
        prev = d.iloc[-2]
        change = latest["refund_amount_inr"] - prev["refund_amount_inr"]
        pct_change = change / prev["refund_amount_inr"] if prev["refund_amount_inr"] else 0
        return AgentAnswer(
            title="Monthly refund trend",
            answer=(
                f"The latest month, {_month_name(latest['report_month'])}, recorded {_money(latest['refund_amount_inr'])}. "
                f"That is {'up' if change >= 0 else 'down'} {_money(abs(change))} ({abs(pct_change):.1%}) versus the prior month."
            ),
            evidence=[
                f"Peak month: {_month_name(peak['report_month'])} at {_money(peak['refund_amount_inr'])}.",
                f"Largest month-on-month increase: {_month_name(rise['report_month'])}, +{_money(max(float(rise.get('delta', 0)), 0))}.",
                f"Latest month ticket count: {int(latest['refund_tickets'])}.",
            ],
            caution="Monthly reporting uses ticket creation month because the source pack does not provide a refund-posted accounting timestamp.",
            next_action="Use the reason-code drill-down for the months with the largest increases before attributing cause.",
            intent="trend",
        )

    if any(k in q for k in ["goal", "saving", "outcome", "business case", "target", "money"]):
        return AgentAnswer(
            title="Business outcome",
            answer=(
                f"The proposed control target is to reduce dual-remedy cases from {m['focus_dual_remedy_cases']} to "
                f"≤ {m['goal_target_cases_per_quarter']} per comparable quarter. At the {focus_label} case mix, that is worth about "
                f"{_money(m['goal_quarterly_savings'])} per quarter or {_money(m['goal_annualized_savings'])} annualised."
            ),
            evidence=[
                f"Current focus-period value at risk: {_money(m['focus_dual_remedy_value_at_risk'])}.",
                "Savings model assumes an 80% reduction in comparable dual-remedy value at risk.",
                f"Focus period: {focus_label}.",
            ],
            caution="The annualised value is a planning estimate, not booked savings; it assumes similar refund/replacement mix and product costs.",
            next_action="Track exception count and value at risk monthly, then replace the annualised estimate with realized avoided cost after one quarter.",
            intent="goal",
        )

    if any(k in q for k in ["validate", "proof", "evidence", "works", "error rate", "trust"]):
        return AgentAnswer(
            title="How the tool is validated",
            answer=(
                "Financial reconciliation and AI assistance are validated separately. The money logic is deterministic and tested on duplicated cross-system pairs; "
                "the AI is measured on an unseen fixed holdout and is deliberately prevented from changing source financial data."
            ),
            evidence=[
                f"Reconciliation: {a['exact_100x_pairs']}/{a['cross_system_refund_pairs']} exact 100× pairs; {_pct(a['normalization_pair_error_rate'])} observed pair error.",
                f"AI: {am['holdout_size']} holdout tickets; {_pct(am['top1_accuracy'])} top-1; {_pct(am['top2_accuracy'])} top-2 coverage.",
                f"Duplicate extras removed: {a['duplicate_extra_rows_removed']:,}.",
            ],
            caution="Pair validation confirms the observed duplicate pattern, not every possible future source system or accounting rule.",
            next_action="For a new helpdesk export, review the reconciliation evidence before accepting the generated board figures.",
            intent="proof",
        )

    # Executive/default response.
    top_reason = reason.iloc[0] if len(reason) else None
    top_reason_text = f"{top_reason['refund_reason_code']} is the largest focus-period reason at {_money(top_reason['amount_inr'])}." if top_reason is not None else "No focus-period reason bucket is available."
    return AgentAnswer(
        title="Executive refund assessment",
        answer=(
            f"The reconciled refund total is {_money(a['clean_refund_total'])} across {m['refund_tickets_18m']:,} refund tickets. "
            f"In {focus_label}, refunds were {_money(m['focus_refund_total'])} across {m['focus_refund_tickets']} tickets. "
            f"{top_reason_text} The clearest controllable risk is {m['focus_dual_remedy_cases']} refund+replacement cases worth "
            f"{_money(m['focus_dual_remedy_value_at_risk'])} in combined planning value."
        ),
        evidence=[
            f"Raw export refund total: {_money(a['raw_refund_total'])}; reconciled: {_money(a['clean_refund_total'])}.",
            f"{a['duplicate_extra_rows_removed']:,} migration/re-import extras removed.",
            f"Business target value: {_money(m['goal_quarterly_savings'])}/quarter; {_money(m['goal_annualized_savings'])}/year annualised.",
        ],
        caution="This workspace separates descriptive facts from judgment: large reason/agent totals are review priorities, not proof of bad behaviour.",
        next_action="Start with the Policy Risk queue, then inspect the largest reason bucket and high-confidence AI disagreements.",
        intent="executive",
    )
