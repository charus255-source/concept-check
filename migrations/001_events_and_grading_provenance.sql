-- Run once in the Supabase SQL editor BEFORE deploying the matching app version.
-- Safe to re-run. It changes the attempts table only.

-- 1. Practice is its own event type, separate from graded case answers.
alter table attempts add column if not exists event_type text;
alter table attempts add column if not exists idea_id text;
-- 2. Every graded attempt records which rules graded it and which case text they saw.
alter table attempts add column if not exists rule_version text;
alter table attempts add column if not exists source_fingerprint text;
-- Explanations and second tries no longer point at a case the learner never saw.
alter table attempts alter column case_id drop not null;

-- Backfill existing rows.
update attempts a set idea_id = c.idea_id
  from cases c where a.case_id = c.case_id and a.idea_id is null;
update attempts set event_type = case
    when passed is not null then 'graded'
    when gap_id is not null then 'retry'
    else 'explanation' end
  where event_type is null;
alter table attempts alter column event_type set not null;

do $$ begin
  alter table attempts add constraint attempts_event_type_valid
    check (event_type in ('explanation', 'retry', 'graded'));
exception when duplicate_object then null; end $$;
do $$ begin
  alter table attempts add constraint attempts_graded_has_case_and_result
    check (event_type <> 'graded' or (case_id is not null and passed is not null));
exception when duplicate_object then null; end $$;

-- 3. One graded answer per learner per case, enforced by the database.
-- If this fails, earlier duplicates exist. List them with:
--   select learner_id, case_id, count(*) from attempts
--   where event_type = 'graded' group by 1, 2 having count(*) > 1;
-- and decide which row to keep before re-running.
create unique index if not exists attempts_one_graded_answer_per_case
  on attempts (learner_id, case_id) where event_type = 'graded';
