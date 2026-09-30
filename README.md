# Vireo Refund Analyst AI — End-to-End Submission


DEMO VIDEO: https://drive.google.com/file/d/1Yk2ILrDntlwjzbBrIoRNTbFSz3s-0gmg/view?usp=sharing


A local, end-to-end refund intelligence system for Vireo Audio. It separates deterministic financial reconciliation from AI-assisted investigation.

## What it does
- auto-detects the five support CSVs by schema (filenames do not matter)
- normalizes legacy refund units and removes migration duplicates
- produces monthly refunds by reason and resolving agent
- flags refund + replacement exceptions and values them using product cost + ₹340 logistics
- compares the latest quarter with the prior three months and decomposes change by reason
- surfaces product, manufacturing-lot, channel and team signals
- runs a measured local text classifier for reason-code review (never auto-recodes)
- provides a tool-using Senior Analyst Agent that selects analysis tools based on the question
- generates board pack PDF, one-page memo, CSV evidence and JSON audit trail
- supports upload of another five-file support pack and reset back to Vireo

## Run
Recommended Python: 3.11 or 3.12.

```powershell
py -3.12 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
python run_agent.py
```

Open `http://127.0.0.1:8765` if the browser does not open automatically.

## Architecture
Browser UI → local HTTP API → workspace orchestrator → deterministic finance engine + advanced analytics + local ML → PDFs/CSVs/JSON.

The agent is intentionally domain-restricted. It can reason over loaded refund/support evidence but does not invent facts or modify source financial data.

## Known limitations
- reporting month uses ticket `created_at`; the pack does not expose the accounting refund-posted timestamp
- lot analysis is concentration, not defect rate, because shipped units by lot are not supplied
- AI validation measures agreement with historical reason codes, not objective truth
- agent refund value is not a performance score; team/tier work differs materially

## Visual analysis workspace upgrade

The analyst workspace now includes motion-based, data-driven visualizations and a real dataset-switch analysis flow:

- animated monthly refund trend line;
- raw-to-reconciled financial transformation view;
- diverging reason-driver bars for period-over-period change;
- product concentration and manufacturing-lot signal cards;
- policy-risk composition visualization;
- AI Top-1 / Top-2 validation gauge;
- detected-file schema map;
- live backend analysis stages when a new five-file support pack is uploaded.

When **Analyze new pack → Analyze & switch workspace** is used, the UI does not immediately replace the current dataset. It keeps the handoff visible and reports the real backend stages: schema mapping, reconciliation, finance views, AI retraining/validation, root-cause scanning, evidence creation and report regeneration. Only after the run succeeds does the workspace switch to the newly calculated dataset.

Animations are explanatory only. They never interpolate or invent financial values; the displayed endpoints are the calculated backend results. `prefers-reduced-motion` is respected.
