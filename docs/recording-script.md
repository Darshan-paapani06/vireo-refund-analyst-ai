# 3-minute screen recording — V4 analyst-agent demo

Target: 2:40-2:55. No slides.

## 0:00-0:20 — Show the build decision
Show `README.md` briefly in VS Code.

Say:
> "The client asked for monthly refund reporting, but the export is not financially safe to sum. I separated deterministic finance reconciliation from AI assistance, then wrapped both in a purpose-built refund analyst workspace."

## 0:20-0:40 — Start the product
In the VS Code terminal:

```powershell
python run_agent.py
```

The browser opens automatically.

## 0:40-1:05 — Executive view
On **Overview**, point to:

- raw refund total: Rs 230,124,081
- reconciled total: Rs 6,709,932
- Q2 2026: Rs 1,279,823 / 473 refund tickets
- policy value at risk: Rs 161,472

Then ask the agent:

**Why is the raw refund total wrong?**

Point out the structured answer: finding, evidence, caution, next action.

## 1:05-1:35 — Policy-control opportunity
Open **Policy risk**.

Say:
> "The policy explicitly disallows refund plus replacement. The tool identifies 32 Q2 cases with Rs 1.61 lakh combined planning value at risk. The measurable goal is <=6 cases per comparable quarter, worth about Rs 1.29 lakh per quarter or Rs 5.17 lakh annualised at the Q2 mix."

Use the search box briefly to show this is a working investigation queue, not a screenshot.

## 1:35-2:05 — AI: what changed and what was discarded
Open **AI review**.

Say:
> "My earlier version treated text classification as an automatic reason-code correction. I discarded that. A fixed 585-ticket holdout gives only 56.4% top-1 accuracy. The historical code appears in the top two 92.3% of the time, so I narrowed AI to human review only. It never changes financial totals or source reason codes."

Show selected code, AI #1/#2 and confidence.

## 2:05-2:25 — Validation
Open **Validation**.

Say:
> "The money logic and AI are validated separately. 125 out of 125 duplicated cross-system refund pairs show the exact observed 100:1 legacy/current monetary ratio. The AI has its own measured holdout error rather than being presented as perfect."

## 2:25-2:40 — Reusable agent workflow
Click **Analyze new pack**.

Say:
> "Vireo is the default case, but another five-file support pack using the same data contract can be uploaded without renaming files. The engine detects the five roles from schema, reruns reconciliation, AI validation and board outputs, and switches the analyst agent to that dataset."

Cancel the upload dialog; do not waste time uploading during the recording.

## 2:40-2:55 — Honest limitation
Finish on **Board outputs** or the memo.

Say:
> "The main reporting shortcut is month assignment: the export has no accounting refund-posted timestamp, so I use ticket creation month. That is the first field I would replace if Finance supplied it. I deliberately left out broad support analytics and autonomous AI decisions because they do not improve this finance control."
