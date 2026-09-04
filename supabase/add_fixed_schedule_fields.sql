alter table public.experiment_trials
  add column if not exists schedule_id text,
  add column if not exists block_type text;

comment on column public.experiment_trials.schedule_id is
  'Fixed schedule assigned to the participant: schedule_1, schedule_2, or schedule_3.';

comment on column public.experiment_trials.block_type is
  'Probability block type: H (50/50), M (65/35), or L (80/20).';
