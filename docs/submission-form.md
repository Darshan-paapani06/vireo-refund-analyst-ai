# Vireo Audio - submission form draft

## What did you build, and what business outcome does it move? State the number and the money.
I built Vireo Refund Intelligence, a one-command local Python tool that auto-detects the supplied CSVs, reconciles legacy monetary units and migration duplicates, produces monthly refund views by reason code and resolving agent, flags refund+replacement policy breaches, validates a local text-based reason-code review assistant, and generates a board-pack PDF, a one-page Finance memo and audit evidence.

The business goal is to reduce refund+replacement cases from 32 in Q2 2026 to 6 or fewer per quarter (80%+ reduction). Those 32 Q2 cases represent about Rs 1.61 lakh combined refund plus replacement planning cost. At the same case mix, an 80% reduction is worth about Rs 1.29 lakh per quarter, or Rs 5.17 lakh annualised.

## What does one run cost, and what would a month cost at Vireo's volume (roughly 650 tickets a week)? Show the arithmetic. If you used no paid calls, say so.
No paid model/API calls are used at runtime. The reason assistant is trained locally with scikit-learn.

650 tickets/week x 52 weeks / 12 months = about 2,817 tickets/month.
2,817 x Rs 0 paid-model cost = Rs 0/month variable paid-model cost.

This excludes local machine/hosting cost and employee time.

## How do you know it works? Sample size, how you checked, error rate, and the kind of case it gets wrong.
Financial reconciliation is deterministic and separately evidenced. The export has 12,238 rows and reconciles to 11,600 unique tickets after removing 638 extra migration/re-import rows. For 125 duplicated refund tickets present in both source systems, all 125 show an exact 100:1 legacy/current monetary ratio, giving 0 observed conversion mismatches in that validation sample.

The AI reason assistant is intentionally treated differently. It was evaluated on a fixed stratified holdout of 585 labelled refund tickets. Top-1 reason accuracy is about 56%, while the actual reason appears among the model's top two suggestions about 92% of the time. It struggles when generic agent notes and overlapping operational reasons do not contain distinctive wording. For that reason it never recodes a ticket or changes money; it only prioritises human review.

## Did you change, narrow, or push back on the client's ask? What, when, and why.
Yes. I kept the requested monthly reason-code and agent views, but pushed back on treating high refund totals as proof an agent is "giving away money". Returns Desk owns most refund processing by design, so I preserve team/tier context.

I also narrowed AI from automatic classification to review assistance after measuring the holdout error. Finally, because the export has no refund-posted timestamp, I made and documented a reporting decision to use ticket creation month so every refund ticket is assigned to a complete period.

## What is wrong with what you are handing us? Be specific: bugs, shortcuts, things you know are off.
The monthly period is a proxy: ticket creation month, not accounting refund-posted month, because the export contains no refund event timestamp. The local text model has only ~56% top-1 accuracy, so it is not suitable for automatic recoding. Replacement planning cost uses the policy standard of unit cost + Rs 340 and does not model recovery. The tool is local/batch, not a production service with access controls, scheduling or monitoring.

## What did you deliberately leave out, and why that rather than something else?
I left out authentication, cloud deployment, a persistent database, broad customer segmentation, full SLA optimisation, autonomous agent scoring and automatic reason-code rewriting. Within the expected five-hour cap, reconciliation accuracy, a board-ready finance output, a policy-grounded leakage control and measurable AI validation were higher-value and lower-risk.

## Anything you built or found that nobody asked for?
Yes. I quantified the refund+replacement policy exception queue and its replacement planning cost, and turned it into a measurable savings target. I also built a machine-readable run evidence file and an AI holdout evidence export so the board numbers and the AI limitations can be independently inspected.

## What did you use AI for? Which tools and models, where they helped, where they wasted your time, what you threw away. Link your three-minute screen recording here.
I used ChatGPT for data-quality hypothesis generation, implementation support, test design, memo wording and challenging the scope. I used a local TF-IDF + logistic-regression classifier in the delivered tool for text-assisted reason review. AI was useful for rapidly surfacing reconciliation hypotheses and structuring the investigation, but an early automatic reason-code concept was not accurate enough and was discarded after validation.

Screen recording: [PASTE LINK]

## Your Public Google Drive Link
[PASTE LINK]

## Someone picks this up on Monday and you are unreachable. The three things they need to know.
1. Do not sum raw `refund_amount_inr`: legacy rows use a different unit and migration created duplicate ticket IDs. Run `python run_vireo.py` and use the generated reconciled outputs.
2. AI reason suggestions are review-only. Never use them to alter finance totals or source reason codes without human verification.
3. Monthly reporting currently uses ticket creation month because no refund-posted timestamp exists. If Finance supplies the accounting date, replace that proxy first.

## Honest hours spent. One number.
[ENTER ACTUAL HOURS]

## Github Repo Link
[PASTE PUBLIC REPO URL]
