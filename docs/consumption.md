# Chapter 1: The loop nobody closed

## Problem

The operator wanted the harness (hooks, routing table, instruction files, memory) to improve itself. Between 2026-07-03 and 2026-07-07 four loops were built or rebuilt around the same design: collect signals, compile them into proposals, a human or the main model approves, apply. By 2026-09-21 an audit asked a simple question: where did the self-improvement go?

## What we built or changed

Eleven mechanisms existed. The audit read each one's code, schedule, output files and logs and classified it. The classification below is generic; each row had its own scheduler entry, script and ledger.

| # | Mechanism (generic) | Intended effect | State at audit (2026-09-21) | Judgement |
|---|---|---|---|---|
| 1 | Self-evolution loop for a fleet of chat bots | Bots improve their own configuration | Retired 2026-07-03 after about 3.5 weeks with no signal | Retired: built "on a road with no traffic" (the fleet had no human messages for a week) |
| 2 | Dispatch-routing feedback loop | Daily audit feeds proposals for the routing table | Ran every day at 08:45; 78 proposal batches, 541 KB, 407 nested records; 1 batch adopted | Produced, not consumed |
| 3 | Instruction-file auto-editor (1,161-line runner, scheduler + cron) | Edit the agent's instruction file from audit signals | Its seven-day human authorization expired 2026-07-14; every later daily run exited 0 with a refusal code (69 of 84 log lines) and told nobody | Stalled silently |
| 4 | Selection-pressure measurement layer for #3 (54 passing tests) | Measure whether a guidance edit reduced recurrence | The ledger it reads has 1 row in total; formally parked 2026-08-23 | Stalled (no upstream signal) |
| 5 | Weekly self-audit script (216 lines) | Cluster four ledgers into a weekly report | Never scheduled; no output file ever existed; declared superseded 2026-08-23 | Never landed |
| 6 | Calibration loop for a write-verification guard | Mine, label, backtest, calibrate | "Review due" reported on 72 of 77 days; labelling watermark frozen at 203 of 1,414 rows; 75 days since last review (threshold 14) | Produced, not consumed |
| 7 | Failure-mining loop | Turn unmatched failures into candidate new guards | Mined transcripts daily (255 + 1,531 on the audit day); 72 items waiting for classification; three planned detectors untouched since 2026-07-05; the labels file has 2 rows | Produced, not consumed |
| 8 | Memory injection on every prompt | Inject past lessons before a task | Alive; injected 8,223 times; outcome feedback recorded 0 times (vector index degraded to a fallback) | Alive but blind |
| 9 | Memory promotion to the knowledge base | Weekly candidate list, human applies | 626 candidates produced; the apply flag was never run; the scheduler entry hard-codes dry-run; the applied-output file does not exist | Never landed |
| 10 | Library of 16 inert self-evolution gates | Safety layer for #3 | All master switches off, waiting for the loop that stopped | Never landed |
| 11 | A public plugin's "disciplined self-evolution" positioning | Branding | Delivered as text; a different system from #1 to #10 | Not part of the loop |

Counting only the mechanisms that were supposed to produce proposals for a person to consume (#2, #6, #7, #9), the consumption evidence was:

| Line | Consumed / produced | Rate | Evidence for the numerator |
|---|---|---|---|
| Routing proposals | 1 of 78 batches | 1.3% | Only batch with an approval marker in its title; the other 77 titles still said "pending review" two months later |
| Calibration labels | 203 of 1,414 ledger rows | 14.4% | Labelling watermark file vs ledger length |
| Promotion candidates | 0 of 626 | 0% | The apply-output file does not exist |
| Failure-mining labels | 2 label rows against 72 unclassified items | n/a | Labels file length |

Three more facts framed the finding:

- The routing table had been edited by hand six times since creation; only one of the six edits (2026-09-04) came through the proposals pipeline. The others were direct edits made while writing decision records or goal files. No proposal was ever rejected, which means nobody reviewed them, not that review was strict.
- Two self-set review checkpoints (a one-month acceptance check, due 2026-08-07, and a decision, due 2026-07-21) were 45 and 62 days overdue on 2026-09-21.
- On 2026-07-07 the system's own design note had said "feedback: disconnected, lessons accumulate but no pipeline compiles them back into rules". The audit found exactly that, eleven weeks later.

What was built in response: a **stop-the-line guard** for every periodic line that produces proposals, alerts or candidates.

Mechanism (re-implementable):

1. Each line has one function that returns "last time a human or the main model left a verifiable trace of consuming this line's output". Four kinds of evidence were used: (a) an approval marker with a date in the proposals file (and its archive); (b) the modification time of a watermark file that only a review run writes; (c) the largest `ts` field inside a labels JSONL (content time beats file time, because backups and editors touch mtimes); (d) a per-line touch file written by an explicit `--consume <line>` command that the weekly review runs after it really looked at and handled the line.
2. The guard takes the newest evidence per line. If it is older than 14 days or absent, the line is `paused: true`. File times more than five minutes in the future are ignored (clock or sync error), and a bad date inside a marker is skipped instead of crashing the evaluation.
3. The state is one JSON file, written atomically (temp file plus rename), with a top-level `_ts` and `_threshold_days`, and one object per line: `{paused, last_consumed, days}`.
4. Every producing script starts with one call to a reader `is-paused <line>`. Exit code 0 means paused; the reader treats a missing file, an unparseable file, a `_ts` older than 3 days (the guard itself has stopped) and a `_ts` in the future all as paused, with the reason on stderr. The reasoning: this mechanism stops useless output, so a failure to decide costs one day of output, while the opposite default (a failure to decide means produce) was the hole the audit found.
5. A session-start line shows which lines are stopped.
6. Recovery is only by consuming: `--consume <line>` writes the touch file and recomputes the state immediately (an early version did not recompute until the next daily run), Deleting the state file leaves the fail-closed reader paused; deletion alone is not recovery.
7. The guard runs once a day from the existing daily job.

The decision was not an experiment. The operator had proposed a degradation path (a line that is not consumed for two weeks drops to monthly frequency and low-risk items auto-apply). Three of four panel votes preferred stopping outright, for a recursive reason: degradation is itself one more signal a person has to consume, whereas a stopped line breaks the silence and cannot be missed. The 14-day figure was a compromise between the three stop proposals (one said 60 days, one said 7-day TTL, one said "pause production" without a number).

## Procedure as actually run

1. 2026-09-21: audit by five read-only sub-agents (one per question) over the harness; the orchestrator re-verified every headline number by hand and corrected two sub-agent errors (a "no scheduler entry" claim for a job that did have one, and a bytes-versus-characters confusion in a size limit).
2. Same evening: four-vote panel (the operator, a second-vendor coding agent, a pay-per-token open-weight model, a local reasoning model) on a common redacted prompt. The operator's own ranking (a consolidated weekly review first) was rejected by three of four, and the operator's degrade-instead-of-stop path was replaced. Outcome: a probe-per-guard volume first, then the stop-the-line volume.
3. That night (2026-09-21 into 2026-09-22): the stop-the-line guard, the reader and the integration into four producing scripts shipped as part of a six-item hardening batch; the first evaluation paused all four lines (days since last consumption: 17, 75, 78 and never). Review of the batch: a local reasoning model returned 14 findings (12 adopted) and a second-vendor coding agent 12 (10 adopted). Findings that touched the guard: atomic state writes, immediate state recompute on `--consume`, a single fail-closed reader, a date parse that cannot crash the evaluation, content timestamps over file times.
4. Blind sample of the proposal stream (below).
5. 2026-10-03 snapshot: all four lines still paused; days since last consumption 29, 87, 89 and never.

## Results

**Blind sample of the 1,333 proposal-type lines** (random seed 50, sample of 50, classified by a keyword heuristic; the orchestrator then hand-read 12):

| Class | Heuristic count (of 50) | Hand-read (of 12) |
|---|---|---|
| Executable routing-rule proposal | 3 | about 1 (barely) |
| "Compliant, nothing to do" statement | 10 | about 5 |
| Same rule repeated (already in the table since creation) | 7 | about 6 |
| Other observation | 30 | 0 |

Reading: the proposal stream had low signal density, so "the backlog is a human-budget problem" was an over-attribution; the other half of the problem was that the output was often not worth consuming. The heuristic classifier put 30 of 50 into "other", so its "should delete" rate (34%) is a lower bound; the hand-read rate (11 of 12) has n=12.

**Dispatch-compliance series for the same period** (the routing audit that fed line #2): monthly mean 66.1% in August and 65.6% for September up to the audit date, seven weeks without improvement; Chapter 5 has the full series.

**State twelve days after the guard shipped:**

| Line | Last consumed | Days at 2026-10-03 | State |
|---|---|---|---|
| Routing proposals | 2026-09-04 | 29 | paused |
| Calibration review | 2026-07-08 | 87 | paused |
| Failure mining | 2026-07-05 | 89 | paused |
| Promotion candidates | never | n/a | paused |

The planned consumption step was a two-week manual weekly review (at most three decisions per sheet, each with owner, expiry date, consequence of not deciding and a recommendation). Two sheets were written on 2026-09-21 and 2026-09-22; at the time of this snapshot their decision-record fields (decisions made, date, number decided) were blank and the trial's due date (2026-10-05) had not arrived. One of the three decisions on the first sheet is itself a "bankruptcy" option: advance the labelling watermark to the current ledger length and start from zero instead of labelling 1,211 old rows.

**Why the loop failed to close, as the audit stated it** (three causes spanning all symptoms):
1. The feedback arm had no human budget: every line was "approve before applying", and nothing said when, how much, or what to do if nobody could.
2. Whether a guard was alive was not observable: liveness was judged by exact strings, environment variables and exit 0 (four cases of the same shape).
3. Free-text fields prevented machine loops from closing: the goal-file `status` field had 14 spellings, 9 goal files had none, and in the route-outcome ledger 44% of the first 178 rows had declared/actual values that could not be compared.

## What did not work

- A loop with a mandatory human gate and no allotted human time: 77 of 78 batches never reviewed.
- Self-set review checkpoints, which are one more item to consume and were not.
- A measurement layer built before there was a signal to measure (54 green tests, 1 data row).
- A stop-the-line rule as a cure: after 12 days no line had resumed and the weekly review that should consume had no recorded decisions. The honest summary is that the rule converts silent waste into visible retirement; it does not create a consumer.
- The audit's own summary called the span "four months": the dated evidence spans about eleven weeks (the loops were built or rebuilt between 2026-07-03 and 2026-07-07 and audited on 2026-09-21). The dated span is about eleven weeks.

## Pitfalls

| Symptom | Root cause | Fix |
|---|---|---|
| A scheduled runner reported success every day for 69 days | A refusal code ("authorization expired") was mapped to exit 0 and no notification | A refusal that means "the loop is not running" must be loud; or the producer must read the stop state first |
| Four scripts each re-implemented "is this line stopped?" with an inline snippet that swallowed errors | Missing, corrupt or wrong-path state meant "carry on" | One reader, fail closed, covering missing, corrupt, stale and future |
| Consumption evidence looked fresh after a backup | File modification time was used | Prefer a timestamp inside the content; ignore future times |
| A bad date in a marker could crash the guard and leave yesterday's state | One exception in the evaluation | Skip the bad item, keep the rest |
| After a review, the line stayed stopped until the next day | `--consume` did not recompute the state | Recompute and write state immediately, atomically |
| A comment in a producer said "exit code 2 means state missing, treat as not paused" while the reader's code returns 0 for all failure cases | Comment written for an earlier design | Treat comments next to fail-closed logic as suspect; test the actual reader against missing, corrupt, stale and future files |

## The rule

Every periodic line that produces something a person must read needs a registered, verifiable trace of the last time someone consumed it and a hard stop after N days without one (fail closed on any doubt); and you should expect the stop to work as retirement, not as a prompt.

The state-file contract is compatible with the [sibling fail-closed reader](https://github.com/ryangu00/agent-guards-that-fail-silently/blob/main/scripts/is_paused.sh): `_ts` plus a per-line boolean `paused`. The public [axiom plugin](https://github.com/ryangu00/axiom) publishes the human-approval stance. These measurements concern a private harness, not that plugin.

See [offline interfaces](interfaces.md) for the sanitized implementation and [complete results](results.md) for dated tables. Historical numbers are transcribed from the supplied fact record; synthetic tests do not reproduce those observations.
