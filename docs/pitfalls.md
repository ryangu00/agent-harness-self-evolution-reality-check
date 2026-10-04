# Pitfalls: symptoms, causes, repairs

These are historical failure modes from the fact record. The public tests exercise mechanisms with artificial input; they do not validate historical rates.

## Chapter 1

| Symptom | Root cause | Fix |
|---|---|---|
| A scheduled runner reported success every day for 69 days | A refusal code ("authorization expired") was mapped to exit 0 and no notification | A refusal that means "the loop is not running" must be loud; or the producer must read the stop state first |
| Four scripts each re-implemented "is this line stopped?" with an inline snippet that swallowed errors | Missing, corrupt or wrong-path state meant "carry on" | One reader, fail closed, covering missing, corrupt, stale and future |
| Consumption evidence looked fresh after a backup | File modification time was used | Prefer a timestamp inside the content; ignore future times |
| A bad date in a marker could crash the guard and leave yesterday's state | One exception in the evaluation | Skip the bad item, keep the rest |
| After a review, the line stayed stopped until the next day | `--consume` did not recompute the state | Recompute and write state immediately, atomically |
| A comment in a producer said "exit code 2 means state missing, treat as not paused" while the reader's code returns 0 for all failure cases | Comment written for an earlier design | Treat comments next to fail-closed logic as suspect; test the actual reader against missing, corrupt, stale and future files |

## Chapter 2

| Symptom | Root cause | Fix |
|---|---|---|
| Rework rate looked better than it was | Missing labels counted as "no rework" | Three-state label; unknown excluded from the denominator and reported |
| "Noise band" too narrow | Interval of the mean of five weekly rates used as a prediction band | Report task-level Wilson interval as the primary band; label any weekly-mean interval as such |
| Weeks needed returned 0 when the observed rate was 0 | Division by an effect that was clipped | Return "not estimable" when the rate is at or below the effect |
| A baseline file silently replaced on the same day | Freeze used a plain write | Exclusive-create freeze; `--force` keeps the old file as `.prev`; check before freeze |
| The seed baseline (4 of 19 rework, 21%) cannot be re-derived | The 2026-07-07 seed rows are no longer present; the reason was not established; only the aggregate survives in a document | Freeze baseline rows, not only the number |
| Tasks per week looked steady | Three empty weeks at the start of the window and one burst week | Report weekly counts, not only the average |

## Chapter 3

| Symptom | Root cause | Fix |
|---|---|---|
| Diagnostic said 0 of 8 | Only top-level transcripts read; sub-agent transcripts live in a per-session subdirectory | Open every transcript file for the session, and attribute the advice to the agent that received it |
| "13 triggers over 70 days" in the report | The 70 was a hard-coded string; the real span was 75 days | Compute spans; do not type them |
| Heartbeat green with no data | Heartbeat written after the collection regardless of source health | Write the heartbeat only from a healthy collection |
| Drill passed with no injection | Placeholder scenarios recorded `pass` | `SKIP` for anything that did not run; assert on this run's id and reason |
| Script crashed only on the production Mac | Empty array expanded under `set -u` in bash 3.2 | Test on the scheduler's shell version; guard empty arrays |
| Frozen baseline overwritten | Plain file write | Exclusive create |
| Compliance rate computed from the guard's own events | Denominator produced by the thing measured | Mark `gate_produced`; evaluate from independent transcripts |

## Chapter 4

| Symptom | Root cause | Fix |
|---|---|---|
| 22% looked like a large opportunity | 77% of it came from a window of 6 turns | Report direct buckets and the window separately; run a sensitivity table |
| Tests green, real run found 2 of 23 table rows | Synthetic fixture used a simpler row format than the real file | Run the parser on the real file once and assert on the count |
| 42% "deviation" in routing | Free-text labels; one concept spelled several ways | Enum with a normalizer; count spelling drift separately from real deviation |
| Shares differ between two runs a day apart | Live sessions keep appending | Snapshot the directory (copy or list by mtime) before measuring |

## Chapter 5

| Symptom | Root cause | Fix |
|---|---|---|
| Adherence 95% but no offload | Work moved from the top model to the mid-tier model on the same subscription | Count offloads against the pay-per-token lane; flag high adherence with zero offloads |
| Audit penalised the dispatch act itself | Spec-writing for a dispatch judged as WASTE | Exceptions for dispatch setup, own-output reads, small diagnostics |
| Compliance series not comparable across months | Rule set changed three times (2026-06-26, 2026-06-29, 2026-09-21), sampling was "largest 6 sessions" | Version the rules, store the rule hash with each row, do not read a trend across versions |
| 18 identical wrong verdicts nobody fixed | No consumer for judge errors | Sample judge verdicts by hand weekly; stop-the-line applies here too |
| Lane failure invisible | A swallowed stderr in the wrapper and a probe that ran only in an interactive shell | Real call with deadline, in the scheduler's environment, stderr to a file |
| "Ledger rows grow" used as proof of delegation | 74% of lines were junk | Count valid rows and require a nonzero delta over the audit window |
| Baseline unrecoverable | Seed rows no longer present; the reason was not established; only the aggregate survives in a document | Freeze the rows |

## How to check the repairs offline

- Consumption: exercise missing, malformed, stale, future and unknown-line state; verify that explicit consumption immediately recomputes state.
- Statistics: preserve unknown labels, empty weeks and an existing freeze. Validate the power formula separately from the time estimate.
- Collection: insert and duplicate source lines, remove a source, and add malformed input. The old heartbeat must survive unchanged when collection degrades.
- Diagnosis: place advice only in a nested transcript while a sibling searches. Only the receiving transcript may contribute compliance.
- Invariants: swap named thresholds, change an environment override, and break a required extraction. A failed check must not re-freeze.
- Drills: verify a fresh run ID and the injected reason, restore the input, then require a different run ID with green state. An unimplemented drill is SKIP.
- Oracle: include a parenthesized criterion after a bold shape name; compare window settings and scan outputs for fixture identities and paths.
- Routing: test both pendulum predicates, a repeated low-adherence trigger and missing judge items. The fixture judge does not establish judge accuracy.

## Source-to-public discrepancies

The supplied state reader did not reject every future or unknown-line state, although the fact record specifies fail-closed behavior. The public reader enforces that documented contract. It also uses elapsed time rather than an integer-day truncation for staleness. Deleting the state file cannot resume a producer; a valid fresh state with explicit `paused: false` is required.

The oracle source included optional per-model and per-session output, and the inventory source included excerpts. The public interfaces remove those outputs to meet the aggregate-only publication boundary. Unknown routes and unknown rework labels remain explicit; they must not become apparent agreement or success.

The historical collector output and audit-ledger category counts are transcribed without silently reconciling their totals. The record does not establish causes for every accounting discrepancy.
