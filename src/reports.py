from __future__ import annotations
from pathlib import Path
import textwrap
import pandas as pd
import matplotlib
matplotlib.use("Agg", force=True)  # server-safe, non-GUI backend
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


def rupees(v):
    return f"Rs {v:,.0f}"


def _save_chart_monthly(monthly: pd.DataFrame, path: Path):
    fig, ax = plt.subplots(figsize=(9, 4.6))
    d = monthly[monthly["report_month"].between("2025-01", "2026-06")]
    ax.plot(d["report_month"], d["refund_amount_inr"] / 100000, marker="o", linewidth=2)
    ax.set_title("Reconciled monthly refunds")
    ax.set_ylabel("Rs lakh")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(alpha=.25)
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def _save_chart_reason(q2_reason: pd.DataFrame, path: Path, focus_label: str = "Focus period"):
    d = q2_reason.sort_values("amount_inr", ascending=True)
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.barh(d["refund_reason_code"], d["amount_inr"] / 100000)
    ax.set_title(f"{focus_label} refunds by reason")
    ax.set_xlabel("Rs lakh")
    ax.grid(axis="x", alpha=.2)
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def _save_chart_agents(q2_agent: pd.DataFrame, path: Path, focus_label: str = "Focus period"):
    d = q2_agent.head(10).sort_values("amount_inr", ascending=True)
    labels = d.apply(lambda r: f"{r['name']} | {r['team']}", axis=1)
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.barh(labels, d["amount_inr"] / 100000)
    ax.set_title(f"{focus_label} resolving-agent refund value - context included")
    ax.set_xlabel("Rs lakh")
    ax.grid(axis="x", alpha=.2)
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def create_board_pack(finance: dict, audit: dict, ai: dict, out_pdf: Path, temp_dir: Path):
    temp_dir.mkdir(parents=True, exist_ok=True)
    c1, c2, c3 = temp_dir/"monthly.png", temp_dir/"reason.png", temp_dir/"agents.png"
    _save_chart_monthly(finance["monthly"], c1)
    _save_chart_reason(finance["q2_reason"], c2, finance["metrics"].get("focus_period_label", "Focus period"))
    _save_chart_agents(finance["q2_agent"], c3, finance["metrics"].get("focus_period_label", "Focus period"))

    m = finance["metrics"]
    a = audit["summary"]
    ai_m = ai["metrics"]

    with PdfPages(out_pdf) as pdf:
        fig = plt.figure(figsize=(11.69, 8.27))
        fig.suptitle("Vireo Audio Refund Intelligence | Board Pack", fontsize=22, fontweight="bold", x=.06, ha="left")
        fig.text(.06,.88,"Reconciled financial view - Jan 2025 to Jun 2026",fontsize=11)
        cards = [
            ("Raw export refund total", rupees(a["raw_refund_total"]), "Not fit for reporting"),
            ("Reconciled refund total", rupees(a["clean_refund_total"]), "After unit normalization + dedupe"),
            (f"{m.get('focus_period_label', 'Focus period')} refunds", rupees(m["q2_2026_refund_total"]), f"{m['q2_2026_refund_tickets']} refund tickets"),
            (f"{m.get('focus_period_label', 'Focus')} policy-risk cases", str(m["q2_dual_remedy_cases"]), rupees(m["q2_dual_remedy_value_at_risk"]) + " value at risk"),
        ]
        x0=.06
        for i,(title,val,sub) in enumerate(cards):
            x=x0+i*.235
            fig.text(x,.76,title,fontsize=10,fontweight="bold")
            fig.text(x,.69,val,fontsize=19,fontweight="bold")
            fig.text(x,.64,sub,fontsize=9)
        fig.text(.06,.52,"Business outcome",fontsize=14,fontweight="bold")
        fig.text(.06,.45,
                 f"Cut refund+replacement cases from {m['q2_dual_remedy_cases']} to <= {m['goal_target_cases_per_quarter']} per quarter (80%+ reduction),\n"
                 f"worth about {rupees(m['goal_quarterly_savings'])} per quarter / {rupees(m['goal_annualized_savings'])} annualized at the focus-period case mix.",
                 fontsize=15, linespacing=1.5)
        fig.text(.06,.27,"Why Finance's total was wrong",fontsize=14,fontweight="bold")
        fig.text(.06,.20,
                 f"The export contains {a['duplicate_extra_rows_removed']} extra migration/re-import rows. Legacy refund values are 100x the current-helpdesk rupee unit; "
                 f"{a['exact_100x_pairs']}/{a['cross_system_refund_pairs']} cross-system refund pairs validate that conversion exactly.",
                 fontsize=11, wrap=True)
        fig.text(.06,.08,"Decision: AI never changes financial totals. It only prioritizes text cases for human review.",fontsize=10,fontweight="bold")
        plt.axis("off"); pdf.savefig(fig,bbox_inches="tight"); plt.close(fig)

        for title, img, note in [
            ("Monthly trend", c1, "Reporting month uses ticket created_at because the export has no refund-event timestamp."),
            ("Reason-code view", c2, "The largest reason bucket is an investigation queue, not proof of invalid refunds."),
            ("Agent view", c3, "Agent totals are presented with team context. Returns Desk is expected to process the majority of refunds by design."),
        ]:
            fig=plt.figure(figsize=(11.69,8.27));fig.suptitle(title,fontsize=20,fontweight="bold",x=.06,ha="left")
            arr=plt.imread(img);ax=fig.add_axes([.06,.18,.88,.68]);ax.imshow(arr);ax.axis("off")
            fig.text(.06,.08,note,fontsize=10)
            pdf.savefig(fig,bbox_inches="tight");plt.close(fig)

        fig=plt.figure(figsize=(11.69,8.27));fig.suptitle("AI-assisted reason review | measured, not trusted blindly",fontsize=20,fontweight="bold",x=.06,ha="left")
        fig.text(.06,.79,"Fixed stratified holdout",fontsize=12,fontweight="bold")
        fig.text(.06,.70,f"{ai_m['holdout_size']} tickets",fontsize=22,fontweight="bold")
        fig.text(.35,.79,"Top-1 accuracy",fontsize=12,fontweight="bold")
        fig.text(.35,.70,f"{ai_m['top1_accuracy']:.1%}",fontsize=22,fontweight="bold")
        fig.text(.63,.79,"Actual code in top-2",fontsize=12,fontweight="bold")
        fig.text(.63,.70,f"{ai_m['top2_accuracy']:.1%}",fontsize=22,fontweight="bold")
        fig.text(.06,.55,"Product decision",fontsize=14,fontweight="bold")
        fig.text(.06,.46,
                 "A single automatic reason-code rewrite would be unsafe. The tool therefore surfaces the model's two most likely codes and confidence for review, "
                 "while preserving the agent-selected code and all financial reporting unchanged.",fontsize=12,wrap=True)
        fig.text(.06,.27,"What this is good for",fontsize=14,fontweight="bold")
        fig.text(.06,.19,"Prioritising messy free-text tickets for audit, spotting plausible miscoding, and making the human review queue smaller - not autonomous finance decisions.",fontsize=11,wrap=True)
        plt.axis("off");pdf.savefig(fig,bbox_inches="tight");plt.close(fig)


def create_memo(finance: dict, audit: dict, ai: dict, out_pdf: Path):
    m=finance["metrics"]; a=audit["summary"]; ai_m=ai["metrics"]
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Small",parent=styles["BodyText"],fontSize=8.6,leading=11,spaceAfter=5))
    styles.add(ParagraphStyle(name="Head",parent=styles["Heading2"],fontSize=10.5,leading=12,spaceBefore=4,spaceAfter=3,textColor=colors.HexColor("#17365D")))
    doc=SimpleDocTemplate(str(out_pdf),pagesize=A4,rightMargin=13*mm,leftMargin=13*mm,topMargin=12*mm,bottomMargin=11*mm)
    story=[]
    story.append(Paragraph("Vireo Audio - Refunds: reconciled view and immediate control",styles["Title"]))
    story.append(Paragraph("To: Arjun Mehta, Finance Controller | Scope: Jan 2025-Jun 2026",styles["Small"]))
    story.append(Paragraph("Bottom line",styles["Head"]))
    story.append(Paragraph(
        f"The raw export's refund column totals <b>{rupees(a['raw_refund_total'])}</b>, but that figure is not reportable. After normalising legacy money units and removing migration duplicates, the reconciled 18-month refund total is <b>{rupees(a['clean_refund_total'])}</b>. "
        f"For {m.get('focus_period_label', 'the latest quarter')}, refunds were <b>{rupees(m['q2_2026_refund_total'])}</b> across <b>{m['q2_2026_refund_tickets']}</b> tickets.",styles["Small"]))
    story.append(Paragraph("Why the export overstated refunds",styles["Head"]))
    story.append(Paragraph(
        f"I removed <b>{a['duplicate_extra_rows_removed']}</b> extra migration/re-import rows by ticket ID, preferring the current helpdesk row. I also converted legacy refund values to rupees. That conversion is directly evidenced by <b>{a['exact_100x_pairs']} of {a['cross_system_refund_pairs']}</b> duplicated refund tickets showing an exact 100:1 legacy/current value ratio.",styles["Small"]))
    story.append(Paragraph(f"What is driving {m.get('focus_period_label', 'the focus period')}",styles["Head"]))
    q=finance["q2_reason"].head(5)
    rows=[["Reason","Tickets","Focus value"]]+[[r.refund_reason_code,str(int(r.tickets)),rupees(r.amount_inr)] for r in q.itertuples()]
    tbl=Table(rows,colWidths=[45*mm,25*mm,32*mm]);tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#17365D")),("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8),
        ("GRID",(0,0),(-1,-1),.25,colors.HexColor("#C9D2DF")),("ALIGN",(1,1),(-1,-1),"RIGHT"),
        ("BOTTOMPADDING",(0,0),(-1,-1),4),("TOPPADDING",(0,0),(-1,-1),4)
    ]));story.append(tbl)
    story.append(Spacer(1,4))
    story.append(Paragraph("Control opportunity",styles["Head"]))
    story.append(Paragraph(
        f"The policy prohibits giving both a refund and replacement for the same order. I found <b>{m['q2_dual_remedy_cases']}</b> such focus-period tickets with <b>{rupees(m['q2_dual_remedy_value_at_risk'])}</b> combined refund plus replacement planning cost. My measurable goal is to reduce these to <b>{m['goal_target_cases_per_quarter']} or fewer per quarter</b>, worth about <b>{rupees(m['goal_quarterly_savings'])} per quarter</b> or <b>{rupees(m['goal_annualized_savings'])} annualised</b> at the same mix.",styles["Small"]))
    story.append(Paragraph("Agent view - use with context",styles["Head"]))
    story.append(Paragraph(
        "The accompanying board pack provides monthly amount and count by resolving agent, but I would not read the largest totals as 'giving away money'. Returns Desk is expected to process most refunds; team and tier are kept beside each agent so Finance can distinguish process ownership from unusual behaviour.",styles["Small"]))
    story.append(Paragraph("AI assistance and confidence",styles["Head"]))
    story.append(Paragraph(
        f"A local text classifier was tested on a fixed holdout of <b>{ai_m['holdout_size']}</b> labelled refund tickets. Top-1 accuracy is only <b>{ai_m['top1_accuracy']:.1%}</b>, while the actual code is among the model's top two suggestions <b>{ai_m['top2_accuracy']:.1%}</b> of the time. I therefore use it only to prioritise review; it never changes the financial totals or the recorded reason code.",styles["Small"]))
    story.append(Paragraph("Reporting assumption",styles["Head"]))
    story.append(Paragraph(
        "The export has no refund-event timestamp. Monthly reporting therefore uses ticket creation month so every refund ticket is placed in a complete period. If Finance later supplies the accounting refund-posted date, that field should replace this proxy without changing the reconciliation logic.",styles["Small"]))
    doc.build(story)
