# Start here
1. Open this folder in VS Code.
2. Keep the supplied five CSVs in `data/` (clean names or original names are both fine).
3. Create/activate Python 3.12 venv.
4. `python -m pip install -r requirements.txt`
5. `python -m pytest -q`
6. `python run_agent.py`
7. Browser opens the Refund Analyst AI workspace.

For the 3-minute recording: show one-command launch → reconciliation → ask “Why did refunds change this quarter?” → Policy Risk → AI Review → Validation → Analyze New Pack → Board Outputs.

## Best way to demonstrate a dataset change

1. Start the application with `python run_agent.py`.
2. Click **Analyze new pack**.
3. Select all five CSVs and give the pack a visible name.
4. Click **Analyze & switch workspace**.
5. Keep the analysis dialog on screen: it now shows the real backend stages and progress.
6. When complete, the workspace transitions to the new dataset and all visualizations, agent answers, validation metrics and downloadable outputs reflect that pack.

The monthly trend, reconciliation bridge, reason-driver changes, product/lot signals, policy-risk composition and AI validation visuals animate from the newly computed values.
