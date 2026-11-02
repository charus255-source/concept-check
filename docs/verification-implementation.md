# Deterministic verification implementation

Implementation and regression testing use mocked providers and make no database
writes. Publishing this implementation does not require database migrations or
answer-key edits. The 20 exact authoritative question-answer records were fetched
read-only into the server-only
`concept_app/verification/golden_pairs.json` snapshot.

## Behavior

* `verification/engine.py` checks case-specific assertions and recognized
  contradictions using the finite relation templates in `patterns.py` and the
  required checks in `rules.py`. No model or network call participates in a grade.
* All required checks plus no recognized contradictions gives PASS. Otherwise the
  valid answer gets WRONG. Source drift, authorization errors, malformed requests,
  and unavailable infrastructure do not become WRONG.
* API responses include stable check IDs, exact original evidence spans, rule
  version `1.0.2`, and the authoritative source fingerprint. Expected answers stay
  on the server. The existing attempts table stores the boolean grade; it has no
  per-attempt rule-version columns, so durable grading provenance remains limited.
* Explanations and second tries continue to save `passed = null`. They are practice,
  not automatically graded answers to a case.
* The chat offers “Try a case before practicing.” After explanation, probing, and
  a saved second try, the UI automatically requests another case for the same idea.
  Case selection failures leave a retry-selection button without resubmitting the
  saved practice. History restores this action for unfinished retries only.
  Saved results are shown separately in history. A before/after comparison exists
  only if the learner actually completes both assessments.
* All 20 cases have verification rules. The UI retains its existing seven concepts;
  the assessment API also supports the three additional idea IDs in the authoritative
  set. This change does not add those concepts to the chat's probing selector.
* The legacy `03-fastapi` model verifier is disabled with HTTP 410. It cannot remain
  an alternative model-grading route. That lecture application is not deployed by
  the root Vercel configuration.

## API

`POST /api/assessment/case` accepts `idea_id` and optional `gap_id`. A signed
session is required. An after-practice case requires an owned gap and a saved second
try. The response exposes only the question, identifiers, phase, and a signed
30-minute challenge binding learner, case, gap, and source fingerprint.

`POST /api/assessment/answer` accepts the challenge and `answer`. It validates
ownership, expiry, the current source, and prior graded attempts. It returns the
deterministic result only after the attempt is successfully saved. Client-supplied
expected answers, boolean grades, or case IDs cannot replace the signed challenge.

The source fingerprint covers exact ID, idea, question, and expected answer bytes
via canonical UTF-8 JSON. Changing a source pair disables its grading until a new
reviewed rule/snapshot is shipped. Existing Golden Pairs are not rewritten.

## Matching limits

Version 1.0.2 adds explicit API-auth paraphrases for frontend/backend communication,
server-side key retention, and active/passive backend provider calls. Saying only
that the browser must not call the private API remains incomplete: case 13 still
requires all three safe-design checks. Case 3 additionally requires browser-code
inspection and key extraction. Recognized unsafe key advice overrides a complete
answer. These are Python pattern changes, not model judgments or answer-key edits.

The matcher recognizes explicit English phrase families and bounded relations.
It is not a complete parser or a proof of understanding. Correct unfamiliar
paraphrases, long-distance pronouns, indirect/hypothetical constructions, and
complex negation may be rejected; unrecognized contradictions may be missed.
The UI explains that WRONG means the documented text checks were not met, and
that valid paraphrases may be missed. Do not describe these rules as general
semantic understanding or claim an accuracy score without observed learner data.

Test paraphrases are authored regression fixtures, not human user-testing evidence
and not additions to the authoritative Golden Pair set. Human review with actual
learner answers is still needed before claiming reliable educational measurement.

## Existing-schema limits

Previously graded cases cannot be selected again as fresh cases. Issued but abandoned
questions are not durably recorded: the current schema stores submitted attempts,
not question exposures. Consequently, this implementation cannot certify that a
learner has never glimpsed an abandoned case in another tab/session. It also cannot
atomically reserve cases or prevent simultaneous duplicate submissions across
serverless instances; sequential replay is blocked. Do not claim those guarantees
without additional separately authorized database support.

The post-practice case always excludes the gap's original case. Exhaustion returns
409 instead of repeating a completed case, changing ideas, or inventing a new pair.
Existing two-case-per-idea coverage means no unlimited fresh-case retries.

## Verification

```powershell
python -m unittest discover -s tests -v
node --test tests/test_chat_ui.cjs
node --check public/chat.js
```

Coverage includes all 20 exact references, 60 supported paraphrases, incomplete
answers for every case, appended contradictions for every case, negation, quoted
claims/identifiers, keyword lists, exact numeric targets, evidence offsets, source
drift, deterministic output, no-model grading, session ownership, expired/tampered
tickets, persistence errors, and case exhaustion. Controller tests use a DOM test
double; they do not verify browser rendering.
