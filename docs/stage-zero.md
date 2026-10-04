# Chapter 3: Stage 0, a read-only loop, and the diagnostic that miscounted

## Problem

With the outcome metric ruled out as a verdict and no consumer for proposals, the remaining useful work was to build the part of the loop that needs no human: an honest record of what happens, a frozen baseline, a diagnosis of where the existing advisory loop breaks, an external alarm if collection stops, and drills that prove the alarm. Stage 0 was explicitly read-only: no knob was allowed to change.

## What we built or changed

Six components, all standard-library scripts with self-tests.

**1. Event ledger** (append-only JSONL, one file; five source ledgers normalised into events with fields `src, kind, denom, key, ts, future, ...`).

- Dedup key = source name + first 20 hex characters of the SHA-1 of the raw line. An earlier version used the line number; rotation or insertion at the top of a source reused keys and lost or duplicated events (review finding).
- Read and append happen under one exclusive file lock; byte-identical raw lines inside one batch collapse to one event and the number collapsed is recorded in the status file (343 early lines without timestamps at the first run; 127 at the 2026-10-03 run, after older rows aged out of the 60-day window).
- Time parsing accepts ISO strings, epoch numbers and epoch strings; anything unparseable is `ts: null` and counted as unknown; events more than five minutes in the future are flagged `future: true` and counted. Nothing is silently dropped.
- Per-source read status (exists, lines, bad lines). If any source is missing or more than 5% of its lines are unparseable, the collection is `degraded`: the heartbeat file is not refreshed, the script exits 1, and a status file says which source (an early version refreshed the heartbeat unconditionally, so an all-sources-missing run still looked healthy).
- The rework flag keeps three states. Events whose denominator is produced by the gate being measured are marked `gate_produced: true` and may only be used as supporting evidence.
- Output at 2026-10-03: 1,126 events (task 370, egress block 333, egress override 139, write-verification fire 103, second write-verification fire 69, probe 86, advisory trigger 13, snapshot 11, advisory search-after-trigger 2); source line counts 370 / 1,838 / 20 / 92; 127 identical lines collapsed; 74 events with unknown time. At first run (2026-09-22) 1,104 events; after the review fixes 769 unique events.

**2. Frozen baseline** (Chapter 2).

**3. Advisory-hook chain diagnosis.** The advisory hook in question fires when 3 similar failed commands occur in one session inside 30 minutes (similarity: Jaccard of command-token sets at least 0.4; per-class thresholds 3 for deterministic errors and 2 for resource errors), prints "stop retrying and search the web for an existing fix" into the agent's context, then holds a 10-minute cooldown (polling commands and parallel-cancelled calls do not count). Knobs frozen for the stage: default threshold 3, window 1,800 s, cooldown 600 s, similarity 0.4, same-hash minimum 3. The diagnostic, for each trigger, took the agent's next 15 tool calls from the transcript and recorded whether a search or fetch tool was among them, whether one came later, how many errors followed, and whether the day had a rework row. Verdicts: complied in window, late, ignored, ended at trigger, no transcript.

**4. Invariants snapshot** proving no knob changed: each threshold is saved by name with its effective value (environment overrides included), plus hashes of the code that classifies failures, of the routing table's main section, of the audit rules and of the hook registration; extraction failure of a required field blocks (exit 2) instead of returning an empty hash; file hashes of all guard scripts are informational; the frozen reference is created exclusively; `--check` always runs before `--freeze`. First version used sets (swapping two thresholds went undetected) and only read the default of one environment variable.

**5. External watchdog** (scheduler, every 6 hours). Red when: the collection heartbeat is missing, older than 168 hours or in the future; the stop-the-line state file is missing, unparseable, older than 72 hours or in the future; the baseline file is missing, unparseable, older than 14 days or in the future. Each run writes a run id, the heartbeat age, the problem list and the notification result code to a state file; the alert goes to a chat webhook and the result code (or -1 when the notifier does not exist) is persisted. At agent session start a status line is shown, and once an "enabled" marker exists a missing watchdog file is itself an alert.

**6. Fault-injection drills.** Scenarios: *outage* (back-date the heartbeat by 8 days, expect red naming the heartbeat under a new run id, restore, expect green under another new run id) and *metrics* (move the baseline away, expect red naming the baseline, restore, expect green). Two more scenarios (a bad change that must be rolled back; a concurrent writer that must be refused) exist as dry-run placeholders that record SKIP. A restore trap puts files back on exit or interrupt; any failure exits 1; the notification result code is recorded as delivery evidence.

## Procedure as actually run

Stage 0 was scoped, built and closed on 2026-09-22 (about 15 hours: goal opened 01:30, closed 16:20), right after a four-vote design panel the same night. Order: retire the old loop; ledger; baseline; diagnosis; watchdog with scheduler entry; drills; invariants; then two reviews.

Design panel verdicts (design, not measured). Three external reviewers agreed the first draft could not be switched on for automatic changes but collection could start now. Resulting design invariants for stages 1 and 2:

- Knobs are tiered by behavioural impact: anything that can weaken a gate or widen what the agent can do (model, tools, network, write scope) is propose-only; tier 1 is pure parameters that can neither weaken protection nor widen capability; tier 2 is routing-table rows.
- Waiver of human sign-off only for tier 1 and machine-bounded: whitelisted fields, per-change increment cap, cumulative-drift cap, diff at most 20 lines, no edits to the judge, metric, collector, tests or the loop's own parameters; tier 2 may only reach shadow mode automatically, promotion needs one human approval; authorization renewed quarterly, and four weeks without a consumer drops the loop to propose-only.
- One live experiment at a time; cadence set by evidence (minimum sample, effect size, interval), not the calendar; insufficient evidence means "undecided", not "keep"; honest throughput about one experiment a month.
- Primary metric is an outcome (rework disappears, task time); compliance and block counts are supporting only; denominators come from independently identified failure opportunities; a four-week-old baseline stays frozen to catch drift; the same feedback may drive at most one change in four weeks, then two weeks of cooling.
- Shadow runs are counted in events (at least 30 triggers), not days; 28 days without that goes to the weekly review.
- The proposal queue itself is bounded, deduplicated, expires, and is subject to the stop-the-line rule.
- The operator's own draft lost on four points (waive all sign-off; weekly cadence; start by changing the advisory threshold; degrade instead of stop).

Reviews of the scripts: a second-vendor coding agent returned 10 findings (4 blockers, 6 major), all adopted; a local reasoning model returned a review with the same problems plus three new adopted items (epoch-as-string times parsed; the diagnostic's definition labelled an upper bound; the baseline's compliance rate taken from the transcript-verified value, with the ledger's self-report as a comparison only). The two reviews also disagreed with the operator's own first-pass numbers (56 weeks).

## Results

**Review findings that changed the design** (counts from the first reviewer; every item adopted):

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

**Drill record** (every row of the drill log):

| Time (2026-09-22) | Scenario | Recorded result | Note |
|---|---|---|---|
| 15:49 | outage, metrics, bad change, concurrent writer | all four recorded as pass | First version: two of the four were dry-run placeholders that had not run anything |
| 16:00 | outage, metrics | FAIL, FAIL ("red then not green") | New version with run ids; the green phase never turned green; the goal log attributes the failures found on re-verification to an empty-array expansion error under bash 3.2 with `set -u` (the drill row itself does not record a reason) |
| 16:00 | bad change | SKIP | Placeholder |
| 16:01 | outage, metrics | PASS, PASS | Notification result code 0 for the outage alert |

**Watchdog in production:** one row every 6 hours; the last recorded run (2026-10-03 21:14) was ok. Heartbeat age cycles 0, 6, 12, 18 hours because collection runs daily.

**Stage-0 closing state:** all four self-tests green; 769 unique events; frozen baseline; diagnosis report; watchdog scheduled and alert delivered; drills pass; invariants CLEAN (the snapshot diff of knobs and hooks is empty). Stage 1 (one tier-1 experiment through the whole loop, with the two placeholder drills made real) had not started at 2026-10-03.

The original diagnostic read only top-level transcripts and reported 0 of 8. Advice was actually delivered inside sub-agents in 6 of those 8 cases. The corrected receiving-agent count was **1 of 8 within 15 calls**, then **1 of 10** in the 2026-10-03 re-run with 18 triggers. The observed search cannot be attributed to the advice; no single case shows the advice changing the next action. See [case 24 of the sibling guards book](https://github.com/ryangu00/agent-guards-that-fail-silently) for the full correction.

## What did not work

- Treating a diagnostic's headline as a finding before it had been validated against the files it did not read. The same shape (a script that reads "the" transcript file) is how the first reading arose.
- Letting a drill pass because the final state file said "ok": an old red file plus a crash looked like a pass.
- A heartbeat that is refreshed regardless of source health.
- Stage 1 itself: designed, not run, so nothing in this chapter says a loop of this kind improves anything.

## Pitfalls

| Symptom | Root cause | Fix |
|---|---|---|
| Diagnostic said 0 of 8 | Only top-level transcripts read; sub-agent transcripts live in a per-session subdirectory | Open every transcript file for the session, and attribute the advice to the agent that received it |
| "13 triggers over 70 days" in the report | The 70 was a hard-coded string; the real span was 75 days | Compute spans; do not type them |
| Heartbeat green with no data | Heartbeat written after the collection regardless of source health | Write the heartbeat only from a healthy collection |
| Drill passed with no injection | Placeholder scenarios recorded `pass` | `SKIP` for anything that did not run; assert on this run's id and reason |
| Script crashed only on the production Mac | Empty array expanded under `set -u` in bash 3.2 | Test on the scheduler's shell version; guard empty arrays |
| Frozen baseline overwritten | Plain file write | Exclusive create |
| Compliance rate computed from the guard's own events | Denominator produced by the thing measured | Mark `gate_produced`; evaluate from independent transcripts |

## The rule

A loop that measures itself needs its own instruments checked against ground truth the same day they are built: validate the diagnostic on a case you can read by hand, make every alarm prove it fires on an injected fault, and refuse to refresh a heartbeat from degraded input.

The judge/actor boundary has an evaluation-side counterpart in [westpoint-agent-eval-rigged-sandbox](https://github.com/ryangu00/westpoint-agent-eval-rigged-sandbox). The [two-coding-agents-side-by-side](https://github.com/ryangu00/two-coding-agents-side-by-side) and [sandboxed-coding-agent-workers](https://github.com/ryangu00/sandboxed-coding-agent-workers) books provide adjacent review and worker-isolation context.

See [offline interfaces](interfaces.md) for the sanitized implementation and [complete results](results.md) for dated tables. Historical numbers are transcribed from the supplied fact record; synthetic tests do not reproduce those observations.
