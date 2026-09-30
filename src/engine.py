from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple
import json

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, top_k_accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


@dataclass
class DataPack:
    tickets: pd.DataFrame
    agents: pd.DataFrame
    orders: pd.DataFrame
    customers: pd.DataFrame
    products: pd.DataFrame
    source_files: Dict[str, str]


SCHEMAS = {
    "tickets": {"ticket_id", "refund_amount_inr", "source_system", "customer_message", "agent_notes"},
    "agents": {"agent_id", "team", "tier"},
    "orders": {"order_id", "lot_code", "order_value_inr"},
    "customers": {"customer_id", "care_plus"},
    "products": {"sku", "unit_cost_inr", "retail_price_inr"},
}


def discover_data(input_dir: str | Path) -> DataPack:
    input_dir = Path(input_dir)
    found: Dict[str, Tuple[Path, pd.DataFrame]] = {}
    csvs = sorted(input_dir.glob("*.csv"))
    if not csvs:
        raise FileNotFoundError(f"No CSV files found in {input_dir}")

    for path in csvs:
        df = pd.read_csv(path)
        cols = set(df.columns)
        for role, required in SCHEMAS.items():
            if role not in found and required.issubset(cols):
                found[role] = (path, df)
                break

    missing = [role for role in SCHEMAS if role not in found]
    if missing:
        raise ValueError(
            "Could not identify required files: " + ", ".join(missing) +
            ". Files are detected from columns, so renaming should not be necessary."
        )

    return DataPack(
        tickets=found["tickets"][1],
        agents=found["agents"][1],
        orders=found["orders"][1],
        customers=found["customers"][1],
        products=found["products"][1],
        source_files={k: str(v[0]) for k, v in found.items()},
    )


def reconcile_tickets(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    t = raw.copy()
    t["refund_amount_raw"] = pd.to_numeric(t["refund_amount_inr"], errors="coerce")
    t["refund_amount_clean"] = np.where(
        t["source_system"].eq("legacy_fd"),
        t["refund_amount_raw"] / 100.0,
        t["refund_amount_raw"],
    )
    t["source_rank"] = t["source_system"].map({"helpdesk": 0, "legacy_fd": 1}).fillna(2)
    t["completeness"] = t.notna().sum(axis=1)

    # Prefer the current helpdesk row when migration reconciliation created duplicates.
    clean = (
        t.sort_values(["ticket_id", "source_rank", "completeness"], ascending=[True, True, False])
        .drop_duplicates("ticket_id", keep="first")
        .copy()
    )

    # Evidence for the 100:1 legacy unit conversion.
    paired = []
    duplicated = t[t["ticket_id"].duplicated(False)]
    for ticket_id, g in duplicated.groupby("ticket_id"):
        systems = set(g["source_system"].dropna())
        if {"helpdesk", "legacy_fd"}.issubset(systems):
            h = g.loc[g["source_system"].eq("helpdesk"), "refund_amount_raw"].dropna()
            l = g.loc[g["source_system"].eq("legacy_fd"), "refund_amount_raw"].dropna()
            if len(h) and len(l) and float(h.iloc[0]) != 0:
                ratio = float(l.iloc[0]) / float(h.iloc[0])
                paired.append((ticket_id, float(l.iloc[0]), float(h.iloc[0]), ratio))
    pair_df = pd.DataFrame(paired, columns=["ticket_id", "legacy_value", "helpdesk_value", "ratio"])
    exact_100 = int(np.isclose(pair_df["ratio"], 100.0).sum()) if len(pair_df) else 0

    audit = {
        "raw_rows": int(len(t)),
        "clean_rows": int(len(clean)),
        "duplicate_extra_rows_removed": int(len(t) - len(clean)),
        "raw_refund_total": float(t["refund_amount_raw"].fillna(0).sum()),
        "clean_refund_total": float(clean["refund_amount_clean"].fillna(0).sum()),
        "cross_system_refund_pairs": int(len(pair_df)),
        "exact_100x_pairs": exact_100,
        "normalization_pair_error_rate": float(0 if len(pair_df) == 0 else 1 - exact_100 / len(pair_df)),
    }
    return clean, {"summary": audit, "pairs": pair_df}


def build_finance_views(pack: DataPack, clean: pd.DataFrame) -> dict:
    t = clean.copy()
    t["created_at"] = pd.to_datetime(t["created_at"], errors="coerce")
    t["resolved_at"] = pd.to_datetime(t["resolved_at"], errors="coerce")
    t["report_month"] = t["created_at"].dt.to_period("M").astype(str)

    refunds = t[t["refund_amount_clean"].fillna(0) > 0].copy()

    agents_latest = (
        pack.agents.sort_values(["agent_id", "from_date"], na_position="first")
        .drop_duplicates("agent_id", keep="last")
    )
    refunds = refunds.merge(
        agents_latest[["agent_id", "name", "site", "team", "shift", "tier"]],
        on="agent_id", how="left"
    )
    refunds = refunds.merge(
        pack.products[["sku", "product_name", "family", "unit_cost_inr", "retail_price_inr"]],
        left_on="product_sku", right_on="sku", how="left"
    )
    refunds["replacement_planning_cost"] = np.where(
        refunds["replacement_issued"].eq("Y"), refunds["unit_cost_inr"].fillna(0) + 340, 0
    )
    refunds["dual_remedy_value_at_risk"] = np.where(
        refunds["replacement_issued"].eq("Y"),
        refunds["refund_amount_clean"] + refunds["replacement_planning_cost"],
        0,
    )

    monthly = refunds.groupby("report_month", as_index=False).agg(
        refund_tickets=("ticket_id", "nunique"),
        refund_amount_inr=("refund_amount_clean", "sum"),
    )
    monthly["avg_refund_inr"] = monthly["refund_amount_inr"] / monthly["refund_tickets"]

    reason = refunds.groupby(["report_month", "refund_reason_code"], as_index=False).agg(
        refund_tickets=("ticket_id", "nunique"),
        refund_amount_inr=("refund_amount_clean", "sum"),
    )

    agent = refunds.groupby(["report_month", "agent_id", "name", "team", "tier"], dropna=False, as_index=False).agg(
        refund_tickets=("ticket_id", "nunique"),
        refund_amount_inr=("refund_amount_clean", "sum"),
    )
    agent["avg_refund_inr"] = agent["refund_amount_inr"] / agent["refund_tickets"]

    exceptions = refunds[refunds["replacement_issued"].eq("Y")].copy()
    exceptions = exceptions[[
        "ticket_id", "report_month", "created_at", "agent_id", "name", "team",
        "product_sku", "product_name", "refund_reason_code", "refund_amount_clean",
        "replacement_planning_cost", "dual_remedy_value_at_risk", "customer_message", "agent_notes"
    ]].sort_values("dual_remedy_value_at_risk", ascending=False)

    # Use the latest observed calendar quarter as the focus period. For the supplied
    # Vireo pack this resolves to Q2 2026 (Apr-Jun), preserving the client brief.
    latest_date = refunds["created_at"].dropna().max()
    if pd.isna(latest_date):
        focus_start = pd.Timestamp("1970-01-01")
        focus_end = pd.Timestamp("1970-04-01")
        focus_label = "Latest quarter"
    else:
        quarter = latest_date.to_period("Q")
        focus_start = quarter.start_time.normalize()
        focus_end = (quarter + 1).start_time.normalize()
        focus_label = f"Q{quarter.quarter} {quarter.year}"

    focus = refunds[(refunds["created_at"] >= focus_start) & (refunds["created_at"] < focus_end)].copy()
    focus_ex = focus[focus["replacement_issued"].eq("Y")].copy()
    focus_at_risk = float(focus_ex["dual_remedy_value_at_risk"].sum())
    goal_target_cases = max(1, int(np.floor(len(focus_ex) * 0.20))) if len(focus_ex) else 0
    goal_savings = focus_at_risk * 0.80

    focus_reason = focus.groupby("refund_reason_code", as_index=False).agg(
        tickets=("ticket_id", "nunique"), amount_inr=("refund_amount_clean", "sum")
    ).sort_values("amount_inr", ascending=False)

    focus_agent = focus.groupby(["agent_id", "name", "team", "tier"], dropna=False, as_index=False).agg(
        tickets=("ticket_id", "nunique"), amount_inr=("refund_amount_clean", "sum")
    ).sort_values("amount_inr", ascending=False)

    metrics = {
        "reconciled_refund_total_18m": float(refunds["refund_amount_clean"].sum()),
        "refund_tickets_18m": int(refunds["ticket_id"].nunique()),
        "focus_period_label": focus_label,
        "focus_period_start": str(focus_start.date()),
        "focus_period_end_exclusive": str(focus_end.date()),
        "focus_refund_total": float(focus["refund_amount_clean"].sum()),
        "focus_refund_tickets": int(focus["ticket_id"].nunique()),
        "focus_dual_remedy_cases": int(len(focus_ex)),
        "focus_dual_remedy_refunds": float(focus_ex["refund_amount_clean"].sum()),
        "focus_dual_remedy_replacement_cost": float(focus_ex["replacement_planning_cost"].sum()),
        "focus_dual_remedy_value_at_risk": focus_at_risk,
        "goal_target_cases_per_quarter": goal_target_cases,
        "goal_quarterly_savings": float(goal_savings),
        "goal_annualized_savings": float(goal_savings * 4),
        # Backward-compatible aliases used by the supplied-client board pack.
        "q2_2026_refund_total": float(focus["refund_amount_clean"].sum()),
        "q2_2026_refund_tickets": int(focus["ticket_id"].nunique()),
        "q2_dual_remedy_cases": int(len(focus_ex)),
        "q2_dual_remedy_refunds": float(focus_ex["refund_amount_clean"].sum()),
        "q2_dual_remedy_replacement_cost": float(focus_ex["replacement_planning_cost"].sum()),
        "q2_dual_remedy_value_at_risk": focus_at_risk,
    }

    return {
        "refunds": refunds,
        "monthly": monthly,
        "reason": reason,
        "agent": agent,
        "exceptions": exceptions,
        "focus": focus,
        "focus_exceptions": focus_ex,
        "focus_reason": focus_reason,
        "focus_agent": focus_agent,
        # Backward-compatible names for current reports.
        "q2_reason": focus_reason,
        "q2_agent": focus_agent,
        "metrics": metrics,
    }


def train_reason_assistant(refunds: pd.DataFrame, random_state: int = 42) -> dict:
    labelled = refunds[refunds["refund_reason_code"].notna()].copy()
    labelled["text"] = labelled["customer_message"].fillna("") + " " + labelled["agent_notes"].fillna("")
    X_train, X_test, y_train, y_test = train_test_split(
        labelled["text"], labelled["refund_reason_code"],
        test_size=0.25, random_state=random_state, stratify=labelled["refund_reason_code"]
    )
    model = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=40000, sublinear_tf=True)),
        ("model", LogisticRegression(max_iter=3000, class_weight="balanced", C=2.0)),
    ])
    model.fit(X_train, y_train)
    proba = model.predict_proba(X_test)
    classes = model.named_steps["model"].classes_
    best_idx = np.argsort(proba, axis=1)[:, ::-1]
    pred = classes[best_idx[:, 0]]
    second = classes[best_idx[:, 1]]

    top1 = float(accuracy_score(y_test, pred))
    top2 = float(top_k_accuracy_score(y_test, proba, k=2, labels=classes))

    validation = pd.DataFrame({
        "actual_reason": y_test.to_numpy(),
        "top1_suggestion": pred,
        "top1_confidence": proba[np.arange(len(proba)), best_idx[:, 0]],
        "top2_suggestion": second,
        "top2_confidence": proba[np.arange(len(proba)), best_idx[:, 1]],
        "correct_top1": pred == y_test.to_numpy(),
        "actual_in_top2": [y_test.iloc[i] in {pred[i], second[i]} for i in range(len(y_test))],
        "text": X_test.to_numpy(),
    })

    # Train final model on all labelled rows and score all refund tickets for review.
    final_model = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=40000, sublinear_tf=True)),
        ("model", LogisticRegression(max_iter=3000, class_weight="balanced", C=2.0)),
    ])
    final_model.fit(labelled["text"], labelled["refund_reason_code"])
    all_text = refunds["customer_message"].fillna("") + " " + refunds["agent_notes"].fillna("")
    all_proba = final_model.predict_proba(all_text)
    all_classes = final_model.named_steps["model"].classes_
    all_idx = np.argsort(all_proba, axis=1)[:, ::-1]

    review = refunds[[
        "ticket_id", "report_month", "agent_id", "name", "team", "refund_reason_code",
        "refund_amount_clean", "customer_message", "agent_notes"
    ]].copy()
    review["ai_top1"] = all_classes[all_idx[:, 0]]
    review["ai_top1_confidence"] = all_proba[np.arange(len(review)), all_idx[:, 0]]
    review["ai_top2"] = all_classes[all_idx[:, 1]]
    review["ai_top2_confidence"] = all_proba[np.arange(len(review)), all_idx[:, 1]]
    review["selected_code_differs_from_ai_top1"] = review["refund_reason_code"] != review["ai_top1"]
    review = review.sort_values(
        ["selected_code_differs_from_ai_top1", "ai_top1_confidence", "refund_amount_clean"],
        ascending=[False, False, False]
    )

    return {
        "model": final_model,
        "validation": validation,
        "review": review,
        "metrics": {
            "labelled_refund_tickets": int(len(labelled)),
            "holdout_size": int(len(y_test)),
            "top1_accuracy": top1,
            "top2_accuracy": top2,
            "random_state": random_state,
        },
    }


def write_machine_evidence(path: Path, pack: DataPack, audit: dict, finance: dict, ai: dict) -> None:
    payload = {
        "source_files": pack.source_files,
        "reconciliation": audit["summary"],
        "business_metrics": finance["metrics"],
        "ai_validation": ai["metrics"],
        "reporting_decisions": {
            "refund_month_basis": "ticket created_at",
            "reason": "the export does not contain a refund event timestamp; created_at is complete and keeps every refund ticket in a month",
            "legacy_money_normalization": "divide legacy_fd refund_amount_inr by 100, empirically validated on duplicated cross-system refund tickets",
            "duplicate_resolution": "prefer helpdesk row over legacy_fd for the same ticket_id",
            "ai_role": "review assistant only; never changes financial totals or source reason codes",
        },
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
