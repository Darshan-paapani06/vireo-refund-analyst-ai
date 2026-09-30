from __future__ import annotations
import argparse
from pathlib import Path
from src.workspace import build_workspace


def main():
    parser = argparse.ArgumentParser(description="Vireo Refund Intelligence Engine (CLI fallback)")
    parser.add_argument("--input-dir", default="data")
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument("--no-open", action="store_true", help="Compatibility flag; CLI never opens a browser")
    args = parser.parse_args()

    print("[1/5] Detecting task-pack CSVs by schema...")
    ws = build_workspace(args.input_dir, args.output_dir)
    pack, audit, finance, ai = ws["pack"], ws["audit"], ws["finance"], ws["ai"]
    for role, path in pack.source_files.items():
        print(f"      {role:10s} <- {Path(path).name}")

    a = audit["summary"]; m = finance["metrics"]; am = ai["metrics"]
    print("[2/5] Reconciliation complete")
    print(f"      raw rows: {a['raw_rows']:,} | clean tickets: {a['clean_rows']:,}")
    print(f"      raw refund total: Rs {a['raw_refund_total']:,.0f}")
    print(f"      reconciled total: Rs {a['clean_refund_total']:,.0f}")
    print("[3/5] Finance + policy-control views complete")
    print(f"      {m['focus_period_label']} refunds: Rs {m['focus_refund_total']:,.0f} across {m['focus_refund_tickets']} tickets")
    print(f"      dual-remedy cases: {m['focus_dual_remedy_cases']} | Rs {m['focus_dual_remedy_value_at_risk']:,.0f} value at risk")
    print("[4/5] AI reason assistant validated")
    print(f"      holdout: {am['holdout_size']} | top-1 {am['top1_accuracy']:.1%} | top-2 {am['top2_accuracy']:.1%}")
    print("[5/5] Board outputs written")
    print(f"\nBusiness target: <= {m['goal_target_cases_per_quarter']} dual-remedy cases per comparable quarter")
    print(f"Estimated planning value: Rs {m['goal_quarterly_savings']:,.0f}/quarter | Rs {m['goal_annualized_savings']:,.0f}/year")

if __name__ == "__main__":
    main()
