# Prompt / change / discard log

Use this as the factual basis for the screen recording; edit wording to match the exact prompts you actually used.

## Prompt direction 1 - reconciliation before UI
"Inspect the support data pack for financial reconciliation traps before building the monthly refund report. Prove any transformation from the data or policy rather than guessing."

### Result
Found two material issues: legacy monetary unit mismatch and duplicated migration/re-import ticket IDs.

## Prompt direction 2 - business control
"After reconciliation, find a measurable and policy-grounded way to reduce avoidable refund cost. Do not call legitimate high-volume refund handling waste."

### Result
Refund + replacement on the same ticket is explicitly prohibited and has a measurable replacement planning cost.

## Prompt direction 3 - AI use
"Use the two free-text fields to help review reason-code quality. Measure holdout error before deciding whether the model can automate anything."

### Version change
Initial concept: auto-predict / auto-recode reason codes.

### Discarded
Autonomous recoding was discarded because top-1 holdout accuracy was only about 56%.

### Kept
Top-two reason suggestions for human review because the true reason appears among the top two about 92% of the time on the fixed holdout.
