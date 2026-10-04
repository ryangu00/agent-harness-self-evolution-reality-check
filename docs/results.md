# Complete results and conditions

All historical values below come from the supplied fact record. Private raw ledgers and transcripts are not distributed, so these tables cannot be independently reconstructed from the synthetic fixtures. Derived values, estimates, design choices and observed results retain their separate status.

## Setting

Conditions: Setting of the single-operator work; the historical software versions are conditions, not requirements for every reader.

| Item | Value |
|---|---|
| OS and scheduler | macOS with launchd user agents (scheduled jobs run with the minimal scheduler PATH `/usr/bin:/bin:/usr/sbin:/sbin`, which causes one case in Chapter 5). |
| Language and shell | Python 3.14.6 (all scripts are standard library only), macOS system bash 3.2.57 (an empty-array expansion under `set -u` bit one script, Chapter 3). |
| Host agent | A command-line coding agent with a hook system; version 2.1.158. Hooks are commands that receive a JSON object on stdin and may print additional context for the agent. Session transcripts are JSONL files, one per session, with sub-agent transcripts in a per-session subdirectory. |
| Second agent | A coding agent from another vendor, used as a cross-vendor reviewer of the stage-0 scripts; a local open-weight reasoning model served as a third reviewer. Their outputs are cited as counts only. |
| Cheap lane | A pay-per-token model router fronting open-weight models, reached from the shell through three wrapper commands (fan-out, verify-loop, autonomous build). The operator's main model runs on a flat-rate subscription with a weekly cap, which is what the routing discipline in Chapter 5 tries to protect. |
| Scale of the data | Eight calendar weeks of labelled task rows (178 tasks, 167 labelled) at the 2026-09-22 freeze; 370 task rows in the event ledger on 2026-10-03; 145 session logs (76,976 assistant turns) in the overhead analysis of 2026-09-27; 187 session logs in its 2026-10-04 re-run. |
| Review process | Every stage-0 script went through two independent reviews (second vendor, local reasoning model) before it was called done. Design drafts went through a four-vote panel (the operator plus three independent models). |

## Chapter 1: The loop nobody closed

### 1.1. Eleven mechanisms

Conditions: Inspection of eleven mechanisms on 2026-09-21, about eleven weeks after the July rebuilds.

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

### 1.2. Consumption evidence

Conditions: Consumption evidence at the 2026-09-21 audit; the failure-label rows do not define a percentage denominator.

| Line | Consumed / produced | Rate | Evidence for the numerator |
|---|---|---|---|
| Routing proposals | 1 of 78 batches | 1.3% | Only batch with an approval marker in its title; the other 77 titles still said "pending review" two months later |
| Calibration labels | 203 of 1,414 ledger rows | 14.4% | Labelling watermark file vs ledger length |
| Promotion candidates | 0 of 626 | 0% | The apply-output file does not exist |
| Failure-mining labels | 2 label rows against 72 unclassified items | n/a | Labels file length |

### 1.3. Proposal sample

Conditions: Proposal sample: 1,333 proposal-type lines; random seed 50; heuristic n=50; hand-read n=12. Approximate hand labels remain approximate.

| Class | Heuristic count (of 50) | Hand-read (of 12) |
|---|---|---|
| Executable routing-rule proposal | 3 | about 1 (barely) |
| "Compliant, nothing to do" statement | 10 | about 5 |
| Same rule repeated (already in the table since creation) | 7 | about 6 |
| Other observation | 30 | 0 |

### 1.4. Stop-state snapshot

Conditions: State on 2026-10-03, twelve days after shipment; all four lines remained paused.

| Line | Last consumed | Days at 2026-10-03 | State |
|---|---|---|---|
| Routing proposals | 2026-09-04 | 29 | paused |
| Calibration review | 2026-07-08 | 87 | paused |
| Failure mining | 2026-07-05 | 89 | paused |
| Promotion candidates | never | n/a | paused |

### 1.5. Failure modes

Conditions: Chapter 1 failure modes observed in the audit and hardening batch; fixes describe the mechanism, not measured improvement.

| Symptom | Root cause | Fix |
|---|---|---|
| A scheduled runner reported success every day for 69 days | A refusal code ("authorization expired") was mapped to exit 0 and no notification | A refusal that means "the loop is not running" must be loud; or the producer must read the stop state first |
| Four scripts each re-implemented "is this line stopped?" with an inline snippet that swallowed errors | Missing, corrupt or wrong-path state meant "carry on" | One reader, fail closed, covering missing, corrupt, stale and future |
| Consumption evidence looked fresh after a backup | File modification time was used | Prefer a timestamp inside the content; ignore future times |
| A bad date in a marker could crash the guard and leave yesterday's state | One exception in the evaluation | Skip the bad item, keep the rest |
| After a review, the line stayed stopped until the next day | `--consume` did not recompute the state | Recompute and write state immediately, atomically |
| A comment in a producer said "exit code 2 means state missing, treat as not paused" while the reader's code returns 0 for all failure cases | Comment written for an earlier design | Treat comments next to fail-closed logic as suspect; test the actual reader against missing, corrupt, stale and future files |

## Chapter 2: Keep-or-revert needs 1,419 labelled tasks per arm

### 2.1. Frozen baseline

Conditions: Frozen at 2026-09-22 16:05; eight complete calendar weeks, 2026-07-27 to 2026-09-21; unknown labels excluded.

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

### 2.2. Weekly rows

Conditions: Same frozen window; empty calendar weeks retained, and weekly rates use labelled tasks only.

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

### 2.3. Throughput comparisons

Conditions: Derived throughput comparisons; fixed requirement 1,419 tasks per arm; the busiest week was a publishing burst.

| Basis for tasks per week | Labelled tasks per week | Weeks for 1,419 |
|---|---|---|
| Frozen eight-week average (3 empty weeks included) | 20.9 | 68 |
| The five active weeks at freeze (167 / 5) | 33.4 | 42.5 |
| Six complete active weeks W34 to W39 as of 2026-10-03 (325 labelled) | 54.2 | 26.2 |
| Busiest single week (W39, 158 labelled) | 158 | 9.0 |

### 2.4. Failure modes

Conditions: Chapter 2 estimator and freeze failure modes; these are implementation findings rather than independent experiments.

| Symptom | Root cause | Fix |
|---|---|---|
| Rework rate looked better than it was | Missing labels counted as "no rework" | Three-state label; unknown excluded from the denominator and reported |
| "Noise band" too narrow | Interval of the mean of five weekly rates used as a prediction band | Report task-level Wilson interval as the primary band; label any weekly-mean interval as such |
| Weeks needed returned 0 when the observed rate was 0 | Division by an effect that was clipped | Return "not estimable" when the rate is at or below the effect |
| A baseline file silently replaced on the same day | Freeze used a plain write | Exclusive-create freeze; `--force` keeps the old file as `.prev`; check before freeze |
| The seed baseline (4 of 19 rework, 21%) cannot be re-derived | The 2026-07-07 seed rows are no longer present; the reason was not established; only the aggregate survives in a document | Freeze baseline rows, not only the number |
| Tasks per week looked steady | Three empty weeks at the start of the window and one burst week | Report weekly counts, not only the average |

## Chapter 3: Stage 0, a read-only loop, and the diagnostic that miscounted

### 3.1. Adopted review findings

Conditions: Stage-0 review findings on 2026-09-22; first reviewer returned 10 findings (4 blockers, 6 major), all adopted.

| Finding class | Example |
|---|---|
| Identity of events | Line-number keys lose or duplicate events on rotation or insertion; no lock on read-then-append |
| Health of collection | Heartbeat refreshed even when every source was missing; bad JSON skipped silently |
| Independence of denominators | Missing rework counted as success; trigger denominator produced by the gate under test; search events not matched per opportunity |
| Knob coverage | Set-based snapshot misses swapped thresholds; environment overrides and classifier code not covered; extraction failure returned empty |
| Time handling | String comparison of ISO times across zones; future events displacing normal weeks; unknown times vanishing uncounted |
| Statistics | Latest weeks with events instead of calendar weeks; weekly-mean interval used as a noise band; power formula mixed estimators; zero weeks for a zero rate |
| Diagnostic validity | Any search counted as compliance; one second before the trigger counted; same-day rework linked without identity |
| Alert delivery | Baseline checked with a file-exists test only; missing watchdog file silent at session start; notifier absent means skip |
| Drills | Old red file plus a crash passed as success; dry-run placeholders recorded as pass; no restore trap |
| Freeze | Same-day re-freeze overwrote the reference; freeze ran before check |

### 3.2. Drill record

Conditions: Complete drill-log record for 2026-09-22; initial placeholder passes were invalid, and later SKIP rows are not passes.

| Time (2026-09-22) | Scenario | Recorded result | Note |
|---|---|---|---|
| 15:49 | outage, metrics, bad change, concurrent writer | all four recorded as pass | First version: two of the four were dry-run placeholders that had not run anything |
| 16:00 | outage, metrics | FAIL, FAIL ("red then not green") | New version with run ids; the green phase never turned green; the goal log attributes the failures found on re-verification to an empty-array expansion error under bash 3.2 with `set -u` (the drill row itself does not record a reason) |
| 16:00 | bad change | SKIP | Placeholder |
| 16:01 | outage, metrics | PASS, PASS | Notification result code 0 for the outage alert |

### 3.3. Corrected receiving-agent recount

Conditions: Corrected receiving-agent recount on 2026-10-03 of the original 8 cases; any search is an upper-bound definition and does not establish causation.

| Outcome | Count (of 8) | Detail |
|---|---|---|
| Search or fetch within 15 calls | 1 | Sixth call after the advice; but sibling sub-agents that had not received the advice were searching in the same minute, so the advice cannot be credited |
| Top-level agent, no search in window, searched later | 2 | First search about 10.3 hours later, and 42 minutes later |
| Sub-agent, no search in remaining 9 to 60 calls | 5 | |

### 3.4. Failure modes

Conditions: Chapter 3 diagnostic and drill failure modes; the reported 70-day span was hard-coded, while the real span was 75 days.

| Symptom | Root cause | Fix |
|---|---|---|
| Diagnostic said 0 of 8 | Only top-level transcripts read; sub-agent transcripts live in a per-session subdirectory | Open every transcript file for the session, and attribute the advice to the agent that received it |
| "13 triggers over 70 days" in the report | The 70 was a hard-coded string; the real span was 75 days | Compute spans; do not type them |
| Heartbeat green with no data | Heartbeat written after the collection regardless of source health | Write the heartbeat only from a healthy collection |
| Drill passed with no injection | Placeholder scenarios recorded `pass` | `SKIP` for anything that did not run; assert on this run's id and reason |
| Script crashed only on the production Mac | Empty array expanded under `set -u` in bash 3.2 | Test on the scheduler's shell version; guard empty arrays |
| Frozen baseline overwritten | Plain file write | Exclusive create |
| Compliance rate computed from the guard's own events | Denominator produced by the thing measured | Mark `gate_produced`; evaluate from independent transcripts |

## Chapter 4: Measure the opportunity ceiling first

### 4.1. Oracle classification

Conditions: First-match oracle classification; these are design rules, not measurements of replaceable work.

| Bucket | Rule |
|---|---|
| plan-writing | writes or edits a goal/plan markdown file, or invokes the planning skill |
| routing | reads or greps the routing table or the outcome ledger, or edits the proposals file |
| review | runs a review/verification command (cross-vendor review, panel, reconcile, verifier) or launches a verifier sub-agent |
| question | asks the user a question |
| closeout | writes the work log, the outcome ledger or the memory files |
| text-only | no tool use |
| work | everything else |

### 4.2. Overhead snapshot

Conditions: 2026-09-27: 145 sessions, 76,976 assistant turns, 101.9 million output tokens; window=6. Window turns overlap the text-only/work totals.

| Bucket | Turns | Share of turns | Output tokens | Share of output |
|---|---|---|---|---|
| plan-writing | 679 | 0.88% | 1,680,145 | 1.65% |
| routing | 325 | 0.42% | 710,295 | 0.70% |
| review | 936 | 1.22% | 1,406,091 | 1.38% |
| question | 56 | 0.07% | 196,530 | 0.19% |
| closeout | 1,915 | 2.49% | 2,990,655 | 2.94% |
| **Direct overhead (five buckets)** | **3,911** | **5.08%** | **6,983,716** | **6.85%** |
| Overhead window (turns before those) | 13,084 | 17.00% | 22,289,614 | 21.88% |
| **Total overhead** | **16,995** | **22.08%** | **29,273,330** | **28.73%** |
| text-only (all) | 41,574 | 54.01% | 57,499,455 | 56.43% |
| work (all) | 31,491 | 40.91% | 37,411,742 | 36.72% |

### 4.3. Window sensitivity

Conditions: Derived re-run on 2026-10-04: 187 live sessions, about 82.8 thousand turns; totals vary by a handful as the live session appends.

| Window (turns) | Total overhead share of turns | Share of output tokens |
|---|---|---|
| 0 (direct buckets only) | 4.82% | 6.84% |
| 2 | 11.86% | 17.53% |
| 6 (the original setting) | 20.99% | 28.48% |
| 12 | 30.65% | 38.61% |

### 4.4. Failure modes

Conditions: Chapter 4 classifier and enum failure modes; no measured saving follows from the opportunity ceiling.

| Symptom | Root cause | Fix |
|---|---|---|
| 22% looked like a large opportunity | 77% of it came from a window of 6 turns | Report direct buckets and the window separately; run a sensitivity table |
| Tests green, real run found 2 of 23 table rows | Synthetic fixture used a simpler row format than the real file | Run the parser on the real file once and assert on the count |
| 42% "deviation" in routing | Free-text labels; one concept spelled several ways | Enum with a normalizer; count spelling drift separately from real deviation |
| Shares differ between two runs a day apart | Live sessions keep appending | Snapshot the directory (copy or list by mtime) before measuring |

## Chapter 5: A routing-audit loop, scored honestly

### 5.1. Audit trend

Conditions: 387 audit rows, 2026-06-26 to 2026-10-02; 93 daily runs since 2026-07-07; October is partial. Rules and sample changed.

| Month | Audits | Adherence quartiles (25 / 50 / 75) | Mean adherence | Audits with any offload | Offloaded actions / audited actions |
|---|---|---|---|---|---|
| 2026-06 | 13 | 15.0 / 91.7 / 95.5 | 64.7 | 5 | 32 / 654 (4.9%) |
| 2026-07 | 101 | 50.0 / 81.7 / 96.0 | 69.6 | 9 | 26 / 5,272 (0.5%) |
| 2026-08 | 133 | 45.0 / 75.0 / 91.7 | 66.1 | 21 | 109 / 7,861 (1.4%) |
| 2026-09 | 134 | 45.0 / 70.0 / 90.0 | 64.5 | 15 | 44 / 7,946 (0.6%) |
| 2026-10 (to 10-02) | 6 | 0.0 / 55.9 / 77.1 | 46.7 | 0 | 0 / 360 |

### 5.2. Rework rates

Conditions: Ledger snapshot 2026-10-04: 400 rows, 389 labelled; starts 2026-08-23. Seed rows survive only as a 2026-07-07 document aggregate.

| Month | Labelled | Rework | Rate | Wilson 95% |
|---|---|---|---|---|
| 2026-08 (from 08-23) | 30 | 9 | 30.0% | 16.7 to 47.9 |
| 2026-09 | 312 | 121 | 38.8% | 33.5 to 44.3 |
| 2026-10 (to 10-03) | 47 | 18 | 38.3% | 25.8 to 52.6 |
| Seed rows (frozen 2026-07-07 document, not in ledger) | 19 | 4 | 21.1% | 8.5 to 43.3 |

### 5.3. Failure modes

Conditions: Chapter 5 audit failure modes; rule changes were on 2026-06-26, 2026-06-29 and 2026-09-21.

| Symptom | Root cause | Fix |
|---|---|---|
| Adherence 95% but no offload | Work moved from the top model to the mid-tier model on the same subscription | Count offloads against the pay-per-token lane; flag high adherence with zero offloads |
| Audit penalised the dispatch act itself | Spec-writing for a dispatch judged as WASTE | Exceptions for dispatch setup, own-output reads, small diagnostics |
| Compliance series not comparable across months | Rule set changed three times (2026-06-26, 2026-06-29, 2026-09-21), sampling was "largest 6 sessions" | Version the rules, store the rule hash with each row, do not read a trend across versions |
| 18 identical wrong verdicts nobody fixed | No consumer for judge errors | Sample judge verdicts by hand weekly; stop-the-line applies here too |
| Lane failure invisible | A swallowed stderr in the wrapper and a probe that ran only in an interactive shell | Real call with deadline, in the scheduler's environment, stderr to a file |
| "Ledger rows grow" used as proof of delegation | 74% of lines were junk | Count valid rows and require a nonzero delta over the audit window |
| Baseline unrecoverable | Seed rows no longer present; the reason was not established; only the aggregate survives in a document | Freeze the rows |


## Power table and clustering

Conditions: derived calculations from the fact record; alpha .05 two-sided, power .8, rounded z values 1.96 and 0.84, independent-task power formula.

| Baseline | Labelled sample | 5 points | 10 points | 15 points | 20 points |
|---|---|---|---|---|---|
| Frozen 0.3713 | 167 | 1,419 | 341 | 145 | 77 |
| Grown ledger 0.376 | 359 | 1,428 | 344 | 146 | 78 |

Conditions: one-way ANOVA of rework grouped by goal file, derived 2026-10-04; time dependence was not tested.

| Quantity | Value |
|---|---|
| Task rows / goal files | 370 / 66 |
| Largest group / labelled singleton groups | 21 / 14 |
| ICC / mean group size | 0.002 / 5.52 |
| Design effect / effective n | 1.01 / 356 of 359 |
| Adjusted / unadjusted tasks per arm | 1,442 / 1,428 |

Conditions: proxy and supporting signals in the same eight-week frozen window; the advisory ledger denominator is explicitly not independent.

| Signal | Recorded values |
|---|---|
| Outbound gate | 209 blocks; 93 overrides; rate 0.3079; Wilson [0.2586, 0.3622] |
| Power for that proxy | 1,272 per arm for 5 points; 302 events in 8 weeks; 37.8 weekly; about 34 weeks |
| Probe canary | 57 runs; red rate 0.0526; 3 of 57, all in one week |
| Advisory ledger self-report | 1 of 7; 0.1429; not independent |
| Write-verification fires | 38; 0.2275 per labelled task |

## Routing spelling and measurement coverage

Conditions: 101 outcome rows since the enum rule of 2026-09-21; these are the historical categories, not the public normalizer's synthetic output.

| Quantity | Value |
|---|---|
| Declared equals actual / differs | 82 / 19 |
| Main-route spelling split among differences | 14 |
| Other differences | 5: 2 to another coding lane, 1 to a sub-agent, 2 with an unrecognized actual value |
| Matching-row rework | 27 of 82; 32.9% |
| Differing-row rework | 10 of 19; 52.6%; small n, intervals overlap |
| Before enum rule | 90 of 216 rows (42%) looked like deviations; mostly free-text spelling |
| Completed precedents | Only two shapes had at least five completed goal files, with 6 and 8 |
| Original bold-name parser | 2 of 23 rows recognized; synthetic tests missed the real syntax |

## Collection snapshot

Conditions: historical 2026-10-03 event ledger; source rows are filtered and deduplicated, and snapshot events are included separately.

| Quantity | Value |
|---|---|
| Total events | 1,126 |
| Task / outbound block / outbound override | 370 / 333 / 139 |
| Write-verification fire / second verification fire | 103 / 69 |
| Probe / advisory trigger / snapshot / advisory search | 86 / 13 / 11 / 2 |
| Source line counts | 370 / 1,838 / 20 / 92 |
| Identical lines collapsed / unknown time | 127 / 74 |
| First run on 2026-09-22 / after review fixes | 1,104 events / 769 unique events |

## Historical cost estimates and dispatch-ledger hygiene

Conditions: 2026-07-07 frozen document; list-price estimates, router usage unavailable and token columns zero.

| Quantity | Value |
|---|---|
| Recorded cheap-lane dispatches | 1,045 |
| Estimated main-model cost / cheap-lane spend | 8.3 times; list-price estimate |
| Status-bearing failures | 2 of 1,032; 0.2% |
| Seed rework | 4 of 19; 21%; Wilson 8.5% to 43.3% |

The seed rows are no longer present; the reason was not established. The seed table elsewhere reports the same rate as 21.1%; both precisions are retained from the fact record.

Conditions: derived ledger inspection on 2026-10-04; categories below are reported as supplied, without inferring a complete line reconciliation.

| Quantity | Value |
|---|---|
| Total lines | 5,538 |
| Single-character zero lines | 4,080, in five contiguous runs; 74% |
| Rows with 9 / 7 columns | 765 / 687 |
| Failures among status-bearing rows | 79 of 765; 10.3% |
| Failure return-code breakdown | rc 127: 39; rc 1: 38; rc 0: 2 |

The cause of the zero lines was not established. A status class and an exit code are not interchangeable; the record includes failures carrying rc 0.

Conditions: one short-task offload demo, not a series; the fact record does not give its date. The cost ratio is derived from the rounded estimates in that record.

| Quantity | Value |
|---|---|
| Net result | Loss |
| Orchestration overhead | 386K tokens |
| Estimated overhead cost / saving before overhead | about 1.03 times |
