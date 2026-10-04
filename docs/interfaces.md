# Offline interfaces and publication adaptations

The public scripts preserve the source mechanisms while replacing private configuration and output with reader-owned inputs. The routing audit is deliberately reduced to classification, a judge interface, trend recording and the warning predicates. Synthetic test output is never evidence for a historical rate.

## Layout and state

Run examples from the repository root. Python programs that write state accept `--state-dir`; its default is `HARNESS_STATE_DIR`, falling back to `.work/state`. Shell programs accept the same argument except `is_paused.sh`, whose second positional argument is the state file. Its default is `$HARNESS_STATE_DIR/paused.json`, or `.work/state/paused.json`.

Set `TMPDIR` to a directory beneath the repository before self-tests. The examples set `PYTHONDONTWRITEBYTECODE=1`. No program installs a scheduled job. The README commands populate local scratch state; remove only reader-created scratch when finished.

| File | Input | Output and contract |
|---|---|---|
| `scripts/power_baseline.py` | `--events` JSONL; `kind: task`, timestamp, tri-state rework; optional `--weeks`, `--now`, `--effect` | Latest baseline; optional exclusive frozen baseline; `--table` for effect sizes |
| `scripts/power_table_and_icc.py` | Task JSONL with timestamp, boolean/null rework and grouping key; optional `--effect` | Power table and one-way ANOVA ICC/design effect |
| `scripts/ledger_collect.py` | `--config`, `--source-root`, optional `--since-days`, `--now` | `events.jsonl`, source status, heartbeat only when healthy |
| `scripts/consumption_guard.py` | Evidence config, state directory; optional `--consume LINE`, `--status` | Atomic `paused.json`; immediate recomputation after consumption |
| `scripts/is_paused.sh` | Line name and optional state filename | Exit 0 paused; exit 1 explicitly active; failures pause |
| `scripts/advisory_diagnosis.py` | Trigger JSONL, transcript directory, marker, repeated search-tool arguments | Aggregate counts plus anonymous per-trigger verdicts in `diagnosis.json` |
| `scripts/knob_invariants.py` | Extraction/hash config, input root; `--snapshot`, `--freeze`, `--check` | Named effective values and required hashes; informational hashes separately |
| `scripts/watchdog.sh` | State directory; optional `--dry-run` | Atomic latest watchdog state with run ID, reasons and notifier status |
| `scripts/drill.sh` | Scenario, state directory; `--no-discord` or `--no-notify` | Fault/recovery assertions and `drills.jsonl`; unfinished scenarios SKIP |
| `scripts/proposals_producer.sh` | Lesson and outcome files, state directory | Synthetic aggregate batches and byte/line offsets; never applies a rule |
| `scripts/routing_audit.py` | Transcript, handler config, fixed judge JSON | Aggregate verdicts, pendulum warnings and versioned trend JSONL |
| `scripts/overhead_oracle/oracle.py` | Transcript directory, classifier config, window | Bucket and window aggregates only |
| `scripts/overhead_oracle/window_sensitivity.py` | Transcript directory and classifier config | Aggregate shares for windows 0, 2, 6 and 12 |
| `scripts/overhead_oracle/shapes.py` | Goal directory and a synthetic or reader-owned shape table | Aggregate statuses, routes, task counts and precedent coverage |
| `scripts/overhead_oracle/declared_actual.py` | Outcome JSONL; optional date filter | Enum agreement, spelling normalization, unknowns and labelled rework rates |
| `scripts/make_fixtures.py` | `--out` directory | Artificial fixtures for every public interface |

The synthetic routing table is only a parser fixture. The private routing policy is not reproduced.

## Baseline and power

A source row may use `rework: true`, `false` or `null`; non-boolean values also count as unknown. Only labelled rows enter the pooled denominator. The primary interval is Wilson at 95%. The weekly bootstrap is an interval of the weekly mean, not a prediction band.

Complete ISO weeks precede the current week. Empty weeks remain in the throughput denominator. Unknown/unparseable times and future times are counted and excluded. `--now` makes the fixture window deterministic. Without it, an old fixture can legitimately produce an empty current window.

The power formula retains z=1.96 and z=0.84. The baseline rounds its pooled rate as in the supplied calculator. Rates at or below the effect and empty labelled samples are not estimable. The companion ICC calculation requires multiple groups, within-group replication and outcome variation; invalid inputs must not become numerical evidence.

Freeze uses exclusive create and returns 3 if the reference exists. An explicit `--force` preserves the previous file with a `.prev-` suffix. The freeze contains the computed baseline; retain the input rows independently if you need to reconstruct it. The auxiliary private metric block was removed as permitted by the publication specification; its historical results remain in the book.

## Collector configuration

Each source declares a unique `name`, relative `path`, `kind_mapper`, and optionally `denom`, `kind_field`, `fields` and `gate_produced`. A string mapper means one constant kind; a mapping translates source event values to generic kinds. Unmapped event types are outside that source's selected schema. The `fields` list is an explicit allowlist for additional fields.

JSONL inputs report existing/readable status, line count and bad-object count. The synthetic snapshot source uses `format: snapshot`, a timestamp capture regex, and a constant kind. Its entire text is hashed for identity; text is not included in the event output.

The content key is source name plus the first 20 hex characters of SHA-1 over the raw line. Identical rows collapse because there is no independent event identity with which to distinguish them. Reordering and insertion do not change keys. Collection and append share a POSIX exclusive lock.

Missing sources or more than 5% malformed lines produce degraded status and exit 1. The previous heartbeat is retained. Missing times remain null, and timestamps more than five minutes into the future are flagged. The source window is 60 days by default; unknown and future times remain visible. A historical snapshot's source counts need not sum to event counts after filtering and deduplication.

## Consumption evidence and reader

`configs/consumption.json` demonstrates a marker capture group, an archive glob, a review watermark and content timestamps. Paths resolve beneath the state directory. Every registered line also accepts a touch file under `consumed/LINE`.

Marker dates that cannot parse are skipped. JSONL evidence prefers the largest content timestamp; as in the supplied source, it falls back to mtime only when no content timestamp parses. Use that fallback only with the source's review-evidence convention. Future evidence beyond the five-minute allowance is ignored. The public copy applies the future filter consistently to all evidence kinds.

The state contract is `_ts` plus a per-line object with a boolean `paused`. The public reader tightens the supplied copy to the fact record's contract: missing line, non-boolean pause value, malformed timestamp, future state, and elapsed age greater than 3 days all pause. This is shape compatibility with the sibling reader, not a claim of byte identity with an independently fetched copy.

`--status` evaluates without writing. `--consume` records explicit review and immediately writes fresh state, even if combined with `--status`. It is an attestation that the output was actually handled, not an automatic review mechanism. Deleting state does not resume production because the reader fails closed.

The optional producer retains byte/line offsets, resets an offset after source shrinkage, and exits successfully for no new fuel or a paused line. Its first run starts lesson bytes at the current end and outcome lines at the beginning, matching the source skeleton. It emits only aggregate fixture batches; no model call or original proposal text is included.

## Receiving-agent diagnosis

Trigger rows use a reader-owned `session` lookup key and `ts`. For each key, inspect both its top-level JSONL and every nested JSONL. The marker and search-tool names are command-line parameters. The marker locates actual advice receipt; the source recount's near-trigger matching window is retained.

Count only tool calls after receipt in the matching transcript and stop at that transcript's next advice. Never attribute a sibling's search to the recipient. If the recipient cannot be uniquely identified, report `unresolved-receiver`; do not guess. The output omits lookup keys, paths, transcript text and tool arguments.

The five established categories are search within the window, late search, ignored advice, ending at the trigger, and no transcript. The public copy also exposes unresolved attribution. A search counts regardless of topic, so the result remains an upper bound on compliance, not a causal finding. Same-day rework was weak unlinked context in the source; it is not used for a public causal verdict. The recount method is integrated here; no standalone session-specific recount is shipped.

## Invariants, watchdog and drills

Invariant entries declare `name`, `file`, capture `regex`, and optionally an environment override name. A required capture must still exist when an environment override is set; both default and effective value are recorded. Required file hashes join the compared parameters. Informational file hashes can change without claiming a parameter change.

A required extraction failure returns 2. `--check` reports changed names with exit 1; even `--check --freeze --force` cannot replace the reference after a failed check. A repeated ordinary freeze returns 3. File paths are local configuration, not hidden defaults.

The watchdog reads heartbeat mtime, stop-state `_ts`, and baseline `ts`. Its limits retain 168 hours, 72 hours and 14 days. Missing, bad or future inputs are red. Each run replaces the state atomically and records a unique run ID.

`HARNESS_NOTIFY_COMMAND` is a reader-owned command string parsed into arguments; the reason is appended as one argument, without a shell evaluation. An absent or unexecutable notifier records -1. `--dry-run` records null and does not attempt delivery. A real delivery endpoint is not supplied. The shell entry points use embedded standard-library Python for portable timestamps and restoration, avoiding the historical empty-array failure.

Drills require an initially healthy fixture state. `outage` back-dates the heartbeat by 8 days; `metrics` removes the baseline. Both restore the original bytes and mtime even when interrupted. Assertions require different nonempty run IDs for initial, fault and recovery state, the correct reason, and matching exit/status values. `badchange` and `concurrent` remain SKIP, matching the source's unimplemented status. `--dry-run` is also SKIP.

The real scheduler registration, session-start hook and enabled-marker integration are environment-specific and were not supplied as public components. Their historical behavior is documented; no scheduler or hook is installed by these examples. The whole daily job is intentionally excluded because it contains unrelated private probes.

## Oracle and normalized routes

The oracle processes top-level JSONL files, as in the supplied overhead analysis. This is different from the advisory diagnostic, which must recurse to identify recipients. Freeze your reader-owned input snapshot before comparisons; the historical sensitivity run instead used live files and disclosed that limitation.

Classifier rules are first-match by bucket, then tool and configured input-field regex. Direct buckets are plan-writing, routing, review, question and closeout. Only the other four direct buckets anchor preceding windows; question does not. A turn is counted at most once in the window, and direct turns are not counted there again.

The public copy removes per-session and per-model output and goal excerpts. Statuses and routes are normalized before aggregation, so an unrecognized free-text value is not echoed. The inventory's optional `shape:` metadata supports synthetic completed-precedent counting; the exact historical assignment of plans to shapes is not available.

The route normalizer uses generic lane enums, keeps the main/main-self distinction visible, and counts known spelling aliases separately. Unknown routes are not credited as agreement. Unknown rework is excluded from each rate denominator. These defensive publication changes mean the public synthetic comparison is not a way to recreate the historical route table from private free text.

## Reduced routing audit

`classify(tool, inputs, config)` distinguishes inline execution, cheap dispatch, subscription sub-agents, orchestration and normalized workflow-agent actions. The original workflow-script crawler is not shipped; an integration must supply workflow-agent actions explicitly. Command names are configurable examples, not installed executables.

`audit(actions, judge)` accepts a function returning `items` with `n`, `tier`, `verdict`, and `reason`. The fixture judge returns fixed synthetic items. Every action needs exactly one valid verdict; workflow-inline generation forces WASTE. Adherence is recomputed from verdict counts, not trusted from the judge's headline.

The prompt constant is a new generic schema skeleton, not the private judge prompt. The reduced parser emits handlers only. A real judge integration needs a reader-owned action-description adapter and policy; the fixture cannot judge work content. Nothing here sends transcript material to an API.

Both pendulum predicates are exposed. The public trend is JSONL with a hash of the prompt skeleton and handler config. Unlike the historical unversioned trend, the structural trigger does not cross rule hashes. A real integration must include the actual policy and judge version in its hash as well. The source's private lessons writer, credentials lookup, provider routing, full daily wrapper and cumulative raw-line counter are omitted.

## Banner and templates

`docs/make_banner.py` preserves the supplied drawing geometry, typography, comments and output logic. Changes are confined to wordmark, tagline/caption and small diagram/right-hand labels, including the hardware footer label, which now says `ONE OPERATOR`. The tagline is `Power, consumption, instruments, ceilings.`

The recipe imports Pillow; Pillow availability and the optional system fonts have not been checked. They are not dependencies of the offline scripts. The license and ignore file are copied byte-for-byte from the supplied templates, including the license's public copyright credit.
