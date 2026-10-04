# Chapter 5: A routing-audit loop, scored honestly

## Problem

The main model ran on a flat-rate subscription with a weekly cap. Routine work (reading, searching, drafting, mechanical edits) could go to cheaper pay-per-token models through a router, or to a second vendor's agent on its own subscription. Prose discipline ("delegate grunt work") was written many times and kept being ignored, so a measurement loop was built to enforce it.

## What we built or changed

1. **A shape-to-route table.** One row per observable task shape: shape, route, quality gate, basis (a short quote from the lesson that produced the row). Core content: a hard whitelist for the main model (judgement, orchestration, architecture, security, acceptance, writes to production shared files), forbidden zones for cheap lanes (production shared files, incident reports written from memory, secret handling), an escalation rule (a cheap lane fails twice on a task, so the main model takes it and a third dispatch is not attempted), and "unsure and cannot verify means the main model". 69 lines at creation (2026-07-07), 92 now. The generic template and ledger format are in the public `axiom` plugin.
2. **An outcome ledger.** One JSON line per task at closeout: timestamp, goal, task, shape, declared route, actual route, result (done, blocked, wontfix, negative, partial), rework (boolean), one-line note. From 2026-09-21 declared and actual must come from a fixed enum.
3. **A daily audit.** At 08:45 a scheduled job (a) probes the cheap lane (a real call must answer "PONG" within 60 seconds), (b) audits up to the 6 largest top-level sessions modified in the last 24 hours that exceed 100 KB (the last 60 tool actions of each), (c) appends to a trend file, (d) runs the stage-0 signal collection and the stop-the-line guard, (e) appends the proposals producer last (a failure of the producer is reported but does not stop the audit). Mutual-exclusion by an atomic `mkdir` lock with a 2-hour stale-lock timeout; log rotation above 5 MB.
4. **The judge.** Each action is labelled with a handler: executor-did-it-inline, cheap-dispatch (a shell command that starts one of the cheap-lane wrappers or the second vendor's delegate command), subscription-sub-agent (any sub-agent, whatever its model tier, spends the same cap and does not count as offloading), orchestration, workflow-inline-generation (forced WASTE), workflow-cheap-dispatch. A cheap model at temperature 0, with reasoning hidden from the response (not necessarily switched off; see the billing finding below), returns per action `{tier: CHEAP|MAIN, verdict: OK|WASTE|RISK, reason}` and an adherence percentage. WASTE = an independent task that could have gone to a cheap lane as a whole was done inline by the expensive executor; RISK = a cheap model took a task that needs the main model. Exceptions that are not WASTE: reading the output of one's own dispatch, writing the spec for a dispatch, small diagnostics during live integration, accepting a cheap model's output. Since 2026-09-21, "sensitivity first": actions subject to the local-only rule are always OK and never WASTE (a cheap model taking them is RISK).
5. **A pendulum detector.** Added after the operator found (by the operator's own account; the 16% and 95% rows in the trend file are from different sessions fifteen minutes apart) that adherence had been pushed from 16% to 95% by moving all delegable work from the top model to the mid-tier model on the same subscription: both draw on the same cap, and the cheap-dispatch count stayed 0. Rules: `adherence >= 80 and cheap_dispatch == 0 and WASTE > 0` prints PENDULUM; `inline_workflow_agents >= 2 and (cheap dispatches in the audited window) == 0` prints PENDULUM-2 (a workflow script's agents defaulting to the subscription model and generating content without shelling out). A pre-flight hook lints workflow scripts and warns (does not block).
6. **A structural trigger.** Three consecutive audits below 60% adherence print "escalate to a hook or rule".
7. **A proposals producer** that compiles new lessons and outcome rows into proposal batches for a human to apply; it is the line whose consumption was 1 of 78 (Chapter 1).

## Procedure as actually run

- 2026-06-25: first audit of the session that built the tool (adherence 13%, 48 of 55 actions WASTE, zero offloaded).
- 2026-06-26: trend file, structural trigger, pendulum detector (offloaded column 0, 0, 0, 0, then 4 the first time it left zero).
- 2026-06-29: workflow-script audit and PENDULUM-2; first run: adherence 14%, 43 WASTE, with dozens of inline agents and single-digit delegated and offloaded counts in the window (it caught the session that built it).
- 2026-07-07: table written and fact-checked, outcome ledger and daily loop built the same day; baseline frozen in a document.
- 2026-09-14: cheap-lane liveness probe added after a four-day hang whose cause was two layers away (below).
- 2026-09-21: audit hardening: enum labels, sensitivity-first, probe fixed for the scheduler environment.

## Results

**Baseline frozen on 2026-07-07 (estimates):** 1,045 recorded dispatches to the cheap lane; estimated main-model cost was 8.3 times cheap-lane spend; 2 failures of 1,032 recorded with a status (0.2%). The cost comparison uses list-price estimates: the router does not return token usage, so the ledger's token columns are zero. Seed outcome rows: 19, rework 4 of 19 (21%; Wilson 8.5% to 43.3%), all four involving a production shared file or a sandbox boundary.

**Audit trend file** (387 rows, 2026-06-26 to 2026-10-02; 93 daily runs since 2026-07-07):

| Month | Audits | Adherence quartiles (25 / 50 / 75) | Mean adherence | Audits with any offload | Offloaded actions / audited actions |
|---|---|---|---|---|---|
| 2026-06 | 13 | 15.0 / 91.7 / 95.5 | 64.7 | 5 | 32 / 654 (4.9%) |
| 2026-07 | 101 | 50.0 / 81.7 / 96.0 | 69.6 | 9 | 26 / 5,272 (0.5%) |
| 2026-08 | 133 | 45.0 / 75.0 / 91.7 | 66.1 | 21 | 109 / 7,861 (1.4%) |
| 2026-09 | 134 | 45.0 / 70.0 / 90.0 | 64.5 | 15 | 44 / 7,946 (0.6%) |
| 2026-10 (to 10-02) | 6 | 0.0 / 55.9 / 77.1 | 46.7 | 0 | 0 / 360 |

The median fell month by month while the mean stayed flat between 64 and 70; the offloaded share of audited actions in July to September was 179 of 21,079 (0.8%). Neither the median trend nor the flat mean can be read as improvement or decline, for the reasons below.

**Rework rate** in the outcome ledger as it stands on 2026-10-04 (400 rows, 389 labelled; the ledger starts 2026-08-23):

| Month | Labelled | Rework | Rate | Wilson 95% |
|---|---|---|---|---|
| 2026-08 (from 08-23) | 30 | 9 | 30.0% | 16.7 to 47.9 |
| 2026-09 | 312 | 121 | 38.8% | 33.5 to 44.3 |
| 2026-10 (to 10-03) | 47 | 18 | 38.3% | 25.8 to 52.6 |
| Seed rows (frozen 2026-07-07 document, not in ledger) | 19 | 4 | 21.1% | 8.5 to 43.3 |

The seed rate and the later rates are statistically indistinguishable; the one-month acceptance criterion ("rework falls") has no conclusion file and cannot be checked because the baseline rows are no longer present; the reason was not established.

**Systematic judge error:** the same wrong call (local-only actions judged "should be offloaded", in conflict with the rule that sensitive material never leaves the machine) was made 18 times with no rule change; the worst day (2026-09-20) had 12 WASTE rows and adherence 14.3% from that call alone. Fixed on 2026-09-21 by the sensitivity-first rule.

**Cheap-lane availability during the period:** a hang from 2026-09-10 to about 2026-09-14 (two causes, neither in the dispatch chain itself: the cheap-lane worker inherited the orchestrator's entire configuration, dozens of connectors and over a hundred skills, tens of thousands of characters of system prompt, first byte after 22 s, total 122 s per call, until two flags brought it to 3 to 8 s; and a stop-time hook re-ran for 86 to 91 s on every session end for two months because an exact-string match broke when a message was reworded, with the wrapper swallowing stderr), and then six consecutive daily probe failures with exit code 127 under the scheduler's minimal PATH (the probe's `timeout` command was not found) while the lane worked interactively. Both were found by a person, not by the audit.

**Dispatch ledger hygiene (derived, 2026-10-04):** the cheap-lane ledger had 5,538 lines; 4,080 of them were the single character `0` in five contiguous runs (74%), 765 rows had 9 columns and 687 had 7 columns. Cause of the junk lines not established. Among the 765 rows with a status column, 79 were failures (rc 127: 39, rc 1: 38, rc 0: 2), 10.3%. The audit's printed "ledger rows" count included the junk.

**The proposals line:** 78 batches, 541 KB, 1 adopted (Chapter 1).

## What did not work

- The central hypothesis, "measurement will fix it", is not supported by the data we have: adherence did not rise, offloads were under 1.5% of audited actions in every full month, and the rework baseline cannot be compared. The loop did detect one real structural problem (the pendulum) and produced the table; neither is a trend result.
- Offloading short single tasks: one demo run incurred 386K tokens of orchestration overhead. Its estimated overhead cost was about 1.03 times the saving before overhead, yielding a net loss; the ratio is derived from the rounded cost estimates. The saving needs a worker payload much larger than the orchestration overhead. This is one demo, not a series.
- Cheap models in the forbidden zones: production shared files (a self-test wrote 25 test rows into a real file and raced a second writer) and incident reports written from memory (fabrication in 7 of 7 attempts, as recorded in the routing table's basis column).
- Two kinds of cheap-model hallucination recorded in repository-history review: a diff against a non-ancestor baseline read as a large deletion; and a claim that upstream already contained X, with invented line numbers, which a second reviewer plus a plain grep refuted. Any affirmative "upstream has X" from a cheap lane must be re-grepped.
- Blindly adding router-side transformers recommended by general guidance made one model return empty output in the agentic path; rolled back, only the router and provider settings kept. A reasoning-suppression setting that hides reasoning without disabling it still billed about 200 reasoning tokens (default 168 on the test model); only an explicit disable zeroed it. A provider that truncated large tool arguments produced a 114-million-token spin; pinning the provider restored 50 of 50 large tool calls.

## Pitfalls

| Symptom | Root cause | Fix |
|---|---|---|
| Adherence 95% but no offload | Work moved from the top model to the mid-tier model on the same subscription | Count offloads against the pay-per-token lane; flag high adherence with zero offloads |
| Audit penalised the dispatch act itself | Spec-writing for a dispatch judged as WASTE | Exceptions for dispatch setup, own-output reads, small diagnostics |
| Compliance series not comparable across months | Rule set changed three times (2026-06-26, 2026-06-29, 2026-09-21), sampling was "largest 6 sessions" | Version the rules, store the rule hash with each row, do not read a trend across versions |
| 18 identical wrong verdicts nobody fixed | No consumer for judge errors | Sample judge verdicts by hand weekly; stop-the-line applies here too |
| Lane failure invisible | A swallowed stderr in the wrapper and a probe that ran only in an interactive shell | Real call with deadline, in the scheduler's environment, stderr to a file |
| "Ledger rows grow" used as proof of delegation | 74% of lines were junk | Count valid rows and require a nonzero delta over the audit window |
| Baseline unrecoverable | Seed rows no longer present; the reason was not established; only the aggregate survives in a document | Freeze the rows |

## The rule

Do not read a trend from an instrument whose rules, sample and judge changed during the period; version the instrument, validate its verdicts by hand, and judge the loop by an outcome that does not depend on the instrument.

Use the generic table in [axiom](https://github.com/ryangu00/axiom/blob/main/templates/ROUTING.template.md); the private table is excluded. [ryanai-evalbank](https://github.com/ryangu00/ryanai-evalbank) shares the measurement-discipline theme: check the chain before reading the score.

See [offline interfaces](interfaces.md) for the sanitized implementation and [complete results](results.md) for dated tables. Historical numbers are transcribed from the supplied fact record; synthetic tests do not reproduce those observations.
