# Chapter 2: Keep-or-revert needs 1,419 labelled tasks per arm

## Problem

The design for stage 1 of the loop was: change one knob, watch an outcome metric (the rate at which a task needed rework), keep or revert. Before running any such experiment we asked how long one verdict would take.

## What we built or changed

A power calculation on the operator's own history, frozen so it could not be quietly re-tuned.

Definitions:

- A **task** is one row of the route-outcome ledger, written at closeout of each task in a goal file.
- **Rework** is a boolean in that row: the task needed rework, a downgrade or a re-dispatch. It is written by the orchestrating model at closeout (self-reported; validity unmeasured).
- **Unknown** (rework missing) is its own state. It is counted separately and excluded from the denominator.

Estimator (identical to the shipped script):

```
p1 = baseline rework rate (pooled over labelled tasks), p2 = p1 - effect, pbar = (p1 + p2)/2
n_per_arm = (1.96*sqrt(2*pbar*(1-pbar)) + 0.84*sqrt(p1*(1-p1) + p2*(1-p2)))^2 / effect^2
weeks_needed = ceil(n_per_arm / labelled_tasks_per_week)
```

with alpha .05 two-sided (z 1.96), power .8 (z 0.84, the rounded value), effect 0.05 (5 percentage points), independent-task assumption. Rules in the script: window = the last N complete ISO calendar weeks (not the current week), empty weeks counted as zero, not skipped; future and unknown-time events excluded and counted; the primary rate is task-level pooled with a Wilson 95% interval; a weekly-mean bootstrap interval is output but labelled "interval of the weekly mean, not a prediction band"; if the rate is at or below the effect size, or there are no labelled tasks, the result is "not estimable" and not zero weeks.

## Procedure as actually run

1. 2026-09-22 15:55: the first baseline run gave about 24 tasks a week, a 34% rework rate (95% band 25.5 to 42.0) and 56 weeks per arm.
2. After the two independent reviews (Chapter 3), the estimator was rewritten (pooled task-level rate with Wilson interval, unknown excluded, complete calendar weeks including empty ones) and frozen at 2026-09-22 16:05 with exclusive-create semantics: 68 weeks per arm.
3. 2026-10-03/04: we recomputed from the grown ledger (derived) and checked clustering by goal file (derived).

## Results

**Frozen baseline (window 2026-07-27 to 2026-09-21, eight complete calendar weeks):**

| Quantity | Value |
|---|---|
| Tasks in window / labelled / unknown label | 178 / 167 / 11 |
| Rework tasks | 62 |
| Pooled rework rate | 0.3713, Wilson 95% [0.3016, 0.4467] |
| Events excluded: unknown time / future time | 74 / 1 |
| Labelled tasks per week | 20.9 |
| Effect size | 0.05 |
| n per arm for the effect | 1,419 labelled tasks |
| Weeks per arm at 20.9 a week | 68 |
| Weekly-mean bootstrap | mean 0.3639, 95% interval of the mean [0.2515, 0.4515], n = 5 weeks |

**Weekly rows in the frozen window** (the weekly rates show how noisy a single week is):

| ISO week | Tasks | Labelled | Rework rate |
|---|---|---|---|
| W31 | 0 | 0 | n/a |
| W32 | 0 | 0 | n/a |
| W33 | 0 | 0 | n/a |
| W34 | 12 | 12 | 0.500 |
| W35 | 18 | 18 | 0.167 |
| W36 | 63 | 54 | 0.407 |
| W37 | 43 | 43 | 0.395 |
| W38 | 42 | 40 | 0.350 |

The three empty weeks are an artefact: no task row in the ledger as it now exists carries a timestamp before 2026-08-22, so the first three weeks of the window are empty because the ledger starts then, not because work paused. Treating them as zero is correct for the estimator but it makes "68 weeks" depend on the window.

**How the weeks figure depends on the rate you pick** (derived; the task count is fixed at 1,419):

| Basis for tasks per week | Labelled tasks per week | Weeks for 1,419 |
|---|---|---|
| Frozen eight-week average (3 empty weeks included) | 20.9 | 68 |
| The five active weeks at freeze (167 / 5) | 33.4 | 42.5 |
| Six complete active weeks W34 to W39 as of 2026-10-03 (325 labelled) | 54.2 | 26.2 |
| Busiest single week (W39, 158 labelled) | 158 | 9.0 |

Interpretation: report the task count (about 1,420 per arm) as the result, and give the weeks as a 26 to 68 range, with the best single week as an outlier that came from a publishing burst.

**Sample size by effect size** (derived, baseline 0.3713, same formula): 5 points 1,419; 10 points 341; 15 points 145; 20 points 77. On the grown ledger (359 labelled, rate 0.376): 1,428 / 344 / 146 / 78. A loop that can only detect 20-point changes is not tuning anything.

**Does clustering by goal file inflate this?** (derived, 2026-10-04) 370 task rows sit in 66 goal files (largest 21 rows; 14 singletons among labelled groups). One-way ANOVA intraclass correlation of the rework flag by goal file: ICC 0.002, mean group size 5.52, design effect 1.01, effective n 356 of 359, adjusted n per arm 1,442 versus 1,428. So grouping by goal file is not the problem. That does not establish independence: time-ordered dependence (same operator, changing environment, changing labeller) was not tested, and the ICC estimate from small groups is noisy.

**High-frequency proxies do not rescue it** (derived): the outbound-data gate had 209 blocks and 93 overrides in the same window (override rate 0.3079, Wilson [0.2586, 0.3622]). For a 5-point shift on a rate of 0.3079 the same formula gives 1,272 events per arm. At 302 events in 8 weeks (37.8 a week) that is about 34 weeks per arm. A faster event stream helps only when its baseline rate is far from 50% or the effect to detect is large.

**Auxiliary signals in the frozen file:** probe canary: 57 runs, red rate 0.0526 (3 of 57, all in one week); advisory-hook compliance as self-reported by the hook's own ledger: 1 of 7 (0.1429), flagged "not independent" because the denominator is produced by the hook being evaluated; write-verification fires: 38 (0.2275 per labelled task).

## What did not work

- Using the outcome metric to judge changes. At 1,419 tasks per arm it is not a verdict, it is a calendar.
- The first estimate (56 weeks) was wrong in a way that mattered: according to the review of the first version of the script, that version counted unknown labels as successes, used the most recent weeks that had events instead of complete calendar weeks, and applied a weekly-mean interval as if it were a noise band. The corrected figure was 68; a later look at the grown ledger gives 26 for the busiest recent window. Whatever number you report, state the window.
- "Replace outcome metrics with deterministic replay and high-frequency events" is the design we adopted for stage 1, but it is a design (voted by a four-model panel) and has not been run at scale: stage 1 did not start, and the weekly decision that would choose the first experiment was due 2026-10-12. Replay is not a tested result.
- Weekly-resolution decisions: with 12 to 63 tasks per week, weekly rework ranged from 17% to 50%.
- One compliance rate with four coexisting definitions (1 of 7 in the ledger's own self-report for the window, 1 of 13 over the whole ledger, 0 of 8 by a transcript diagnostic that was later found wrong, 2 of 18 on 2026-10-03). Pick one definition per metric and keep its denominator independent of the thing being measured.

## Pitfalls

| Symptom | Root cause | Fix |
|---|---|---|
| Rework rate looked better than it was | Missing labels counted as "no rework" | Three-state label; unknown excluded from the denominator and reported |
| "Noise band" too narrow | Interval of the mean of five weekly rates used as a prediction band | Report task-level Wilson interval as the primary band; label any weekly-mean interval as such |
| Weeks needed returned 0 when the observed rate was 0 | Division by an effect that was clipped | Return "not estimable" when the rate is at or below the effect |
| A baseline file silently replaced on the same day | Freeze used a plain write | Exclusive-create freeze; `--force` keeps the old file as `.prev`; check before freeze |
| The seed baseline (4 of 19 rework, 21%) cannot be re-derived | The 2026-07-07 seed rows are no longer present; the reason was not established; only the aggregate survives in a document | Freeze baseline rows, not only the number |
| Tasks per week looked steady | Three empty weeks at the start of the window and one burst week | Report weekly counts, not only the average |

## The rule

Before you build a keep-or-revert loop on an outcome metric, compute n per arm for the smallest effect you would act on and divide by your own labelled tasks per week; if the answer is more than a quarter, the metric is an observation, not a verdict.
See [offline interfaces](interfaces.md) for the sanitized implementation and [complete results](results.md) for dated tables. Historical numbers are transcribed from the supplied fact record; synthetic tests do not reproduce those observations.
