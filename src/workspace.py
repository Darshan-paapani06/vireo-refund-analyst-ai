from __future__ import annotations
from pathlib import Path
import shutil
from typing import Callable, Optional

from .engine import discover_data, reconcile_tickets, build_finance_views, train_reason_assistant, write_machine_evidence
from .reports import create_board_pack, create_memo
from .advanced import build_advanced_views

ProgressFn = Optional[Callable[[str, int, str], None]]


def _emit(progress: ProgressFn, stage: str, percent: int, detail: str) -> None:
    if progress:
        progress(stage, percent, detail)


def build_workspace(input_dir: str | Path, output_dir: str | Path, progress: ProgressFn = None) -> dict:
    input_dir = Path(input_dir)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    tmp = out / "_tmp"
    tmp.mkdir(exist_ok=True)

    _emit(progress, "schema", 8, "Identifying tickets, agents, orders, customers and products from columns")
    pack = discover_data(input_dir)

    _emit(progress, "reconcile", 24, "Normalizing legacy money and resolving migration duplicates")
    clean, audit = reconcile_tickets(pack.tickets)

    _emit(progress, "finance", 40, "Rebuilding monthly, reason, agent and policy-control views")
    finance = build_finance_views(pack, clean)

    _emit(progress, "ai", 57, "Training and validating the local reason-code review model")
    ai = train_reason_assistant(finance["refunds"])

    _emit(progress, "root_cause", 69, "Scanning product, manufacturing-lot, channel and quarter-change signals")
    advanced = build_advanced_views(pack, finance)

    _emit(progress, "evidence", 78, "Writing audit evidence and analytical drill-down files")
    finance["monthly"].to_csv(out / "01_monthly_refunds.csv", index=False)
    finance["reason"].to_csv(out / "02_monthly_refunds_by_reason.csv", index=False)
    finance["agent"].to_csv(out / "03_monthly_refunds_by_agent.csv", index=False)
    finance["exceptions"].to_csv(out / "04_policy_exceptions_refund_plus_replacement.csv", index=False)
    ai["review"].head(500).to_csv(out / "05_ai_reason_review_queue.csv", index=False)
    ai["validation"].to_csv(out / "06_ai_holdout_evidence.csv", index=False)
    audit["pairs"].to_csv(out / "07_legacy_100x_validation_pairs.csv", index=False)
    write_machine_evidence(out / "08_run_evidence.json", pack, audit, finance, ai)
    advanced["product"].to_csv(out / "09_product_root_cause.csv", index=False)
    advanced["lots"].to_csv(out / "10_lot_signals.csv", index=False)

    _emit(progress, "reports", 89, "Regenerating the board pack and one-page Finance memo")
    create_board_pack(finance, audit, ai, out / "Vireo_Board_Pack.pdf", tmp)
    create_memo(finance, audit, ai, out / "Memo_to_Arjun_Mehta.pdf")
    shutil.rmtree(tmp, ignore_errors=True)

    _emit(progress, "complete", 100, "Analysis complete — switching the workspace to the new dataset")
    return {"pack": pack, "clean": clean, "audit": audit, "finance": finance, "ai": ai, "advanced": advanced, "output_dir": out}
