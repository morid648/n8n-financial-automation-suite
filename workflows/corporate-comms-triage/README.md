# Corporate Comms Triage

> Cross-cutting findings live in [`../../docs/PRD.md`](../../docs/PRD.md) Section 3 — this README links back rather than repeating them.

## Overview

Gmail-triggered workflow. Classifies inbound mail into a closed taxonomy (billing, project update, spam, other) and routes only genuinely critical categories to a Telegram executive alert.

**Trigger:** Gmail · **Primary risk:** Low–Medium (alert fatigue if untuned)

## Tech stack

- n8n
- Google Gemini (`Gemini_Inference_Engine` → `NLP_Text_Classifier` / `LLM_Execution_Chain`)
- Gmail, Telegram

## Node reference

_TBD — populate from `Corporate_Comms_Triage.json`._

## Required credentials

- Gemini API key
- Gmail OAuth
- Telegram bot token + chat ID

## Known gaps

- `Gemini_Inference_Engine` has zero connections — not wired to either AI node (PRD 3.8).
- No category branching — every classified message currently flows to `Telegram_Executive_Alert` (PRD 3.6).
- Category taxonomy is free text, not a closed set.
- No "Continue on Fail" / error branch on the AI nodes (PRD Section 4).

## Setup steps

1. Import `Corporate_Comms_Triage.json`.
2. Add all credentials above.
3. Wire `Gemini_Inference_Engine` into both AI nodes via `ai_languageModel`.
4. Constrain the classifier to the T1.8 taxonomy; add an `IF`/`Switch` node so only critical categories alert.
5. Test with a 5–10 message sample spanning every category before enabling live alerting.
