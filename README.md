# Concept Check

Find where a learner stops understanding and starts reciting.

Live app: https://c8-db-fastapi.vercel.app/

A learner explains a Module 2 idea in their own words. An AI model quotes the one
sentence that sounds recited and asks one question about what breaks. The learner
tries again, then answers a fresh case they have not seen. **Python decides the
result. The AI can only ask and point at the learner's words.**

## How it works

```
Learner ──► /api/check ──► Groq: quote one sentence, ask one question
                │               (Python checks: quote is in the text, exactly one question)
                ▼
        explanation + retry saved as practice events (no grade)
                │
Learner ──► /api/assessment/case ──► an unseen case for that concept (signed, 30-minute challenge)
Learner ──► /api/assessment/answer ─► Python grades the answer against reviewed rules
                                       └─ optional: Groq proposes quotes, Python confirms them
```

| Decided by code (same input, same answer) | Decided by AI (judgment) |
|---|---|
| The list of concepts (`concept_app/catalog.py`) | Finding the recited sentence |
| The cases and their reviewed answers (`golden_pairs.json`) | Writing the one follow-up |
| Every attempt, with a time and an event type | Proposing which words state an idea (only a proposal) |
| Pass or not, against the answer key | |

### How grading works (`concept_app/verification/`)

1. **Phrase rules** (`patterns.py`) look for each idea a case needs (`rules.py`)
   and for known bad advice (for example "keep the key in the browser").
2. **Quote check** (`quotes.py`). For ideas the phrase rules missed, the model may
   propose the exact passage that states the idea. Python accepts it only if the
   passage is copied exactly from the answer, and if one real clause in it contains
   every required term, with no negation, quotation or "what if". The model never
   sees the answer key and cannot override bad advice. If the model is down, the
   phrase rules decide alone.
3. **Result.** Pass if every idea is covered and there is no bad advice. Otherwise
   *Almost there (2 of 3 ideas)* or *Not yet*, with what was right and what is missing.

Every graded attempt stores `rule_version` and `source_fingerprint`. If a case's
question or answer changes in the database, grading for it switches off until the
rules are reviewed again.

### Golden pairs

`concept_app/verification/golden_pairs.json` (case IDs 1 to 20, two per concept) is the
only set the grader uses. `concept_check_golden_pairs_20.csv` is the same 20 rows as a
CSV, generated from that JSON. An earlier draft CSV used IDs 11 to 30 with different
questions; it was never used for grading and has been replaced.

## Measuring fairness

`evaluation/` holds answers a human labelled correct or incorrect.
`scripts/measure_unfair_rate.py` reports the **unfair NOT YET rate** (correct answers
not passed) and the **unsafe PASS rate** (incorrect answers passed), using the phrase
rules only.

| Answer set | Before (rules 1.0.2) | After (rules 1.1.0) |
|---|---|---|
| `sample_answers.csv`: the trainer's 2 failing answers + 25 authored, used to write the new rules | 20 of 27 unfair | 0 of 27 unfair |
| `heldout_answers.csv`: 16 correct answers written after the rules, never tuned on | 11 of 16 unfair | 5 of 16 unfair |
| Incorrect answers in both sets | 0 of 20 passed | 0 of 20 passed |

These are authored answers, not real learners. The held-out row is the honest
number for the phrase rules; the quote check exists to close the rest of that gap.
To measure on real learners: export answers (no names), label each one, save as CSV
with columns `case_id,human_label,answer`, then run
`python scripts/measure_unfair_rate.py your_file.csv`.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # then fill in the values
uvicorn api.index:app --reload
```

## Test

```bash
python -m pytest -q
```

Tests make no network calls. They cover every golden pair, the labelled sample
answers, a model that tries to pass everyone, keyword lists, signed sessions,
practice events, duplicate answers, and rate limits.

## Environment variables

| Name | Purpose |
|---|---|
| `GROQ_API_KEY` | Probing and quote proposals |
| `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` | Database (server only) |
| `SESSION_SECRET` | Signs session cookies and case challenges. Must be different from the Supabase key, 32+ characters |

## Database

Tables: `learners`, `cases`, `attempts`, `gaps`. Apply `migrations/001_events_and_grading_provenance.sql`
in the Supabase SQL editor **before** deploying this version. It adds `event_type`
(`explanation`, `retry`, `graded`), `idea_id`, `rule_version` and `source_fingerprint`
to attempts, backfills old rows, and adds a unique index so a learner can submit
only one graded answer per case.

## Privacy

Learners get a random label, never a name. The shared view shows explanations,
not names. Consent comes first: ask before recording a classmate thinking out loud.

## Known limits

* Rate limits are kept in memory on each server instance, so they slow bursts but
  are not a global cap. A shared store such as Upstash would make them global.
* Each concept has two reviewed cases. When both are answered, the app names
  concepts that still have a fresh case.
* The phrase rules and quote check can still miss correct answers in unusual
  words. The app says so on every Not yet result.
