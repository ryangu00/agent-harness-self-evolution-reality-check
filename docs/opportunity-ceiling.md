# Chapter 4: Measure the opportunity ceiling first

## Problem

A proposal was on the table to build a fast lane for routine orchestration decisions (plan-file writing, routing, review, questions, closeout) so the expensive model would spend fewer turns on them. Before building, we asked how many turns and output tokens that work actually takes in our own sessions.

## What we built or changed

A 234-line oracle (three scripts, one test file, standard library only) that reads session transcripts and prints only aggregates: no message text, paths or session IDs.

Classification of each assistant turn (first match wins):

| Bucket | Rule |
|---|---|
| plan-writing | writes or edits a goal/plan markdown file, or invokes the planning skill |
| routing | reads or greps the routing table or the outcome ledger, or edits the proposals file |
| review | runs a review/verification command (cross-vendor review, panel, reconcile, verifier) or launches a verifier sub-agent |
| question | asks the user a question |
| closeout | writes the work log, the outcome ledger or the memory files |
| text-only | no tool use |
| work | everything else |

"Overhead" = the five named buckets plus an **overhead window**: text-only or work turns that fall within the 6 turns before a plan-writing, routing, review or closeout turn in the same session. The window stands for "the model thinking about routing or acceptance".

Two sibling scripts: a goal-file inventory (status, task counts, route values, shapes that have at least five completed precedents) and a declared-versus-actual comparison over the outcome ledger with an enum normalizer.

## Procedure as actually run

Built from a spec that allowed only synthetic fixtures; run locally by the operator on 2026-09-27 over the session directory (145 sessions, 0 skipped lines); three unit tests; then re-run by us on 2026-10-04 over the same directory as it stands (187 sessions) at four window sizes.

## Results

**Snapshot of 2026-09-27 (145 sessions, 76,976 assistant turns, 101.9 million output tokens):**

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

The window contributes 77% of the overhead turns. The headline "22.1% of turns, 28.7% of output tokens" is mostly a statement about the window parameter.

**Sensitivity to the window** (derived: re-run 2026-10-04 on 187 sessions, about 82.8 thousand turns; turn counts vary by a handful between runs because the live session kept writing):

| Window (turns) | Total overhead share of turns | Share of output tokens |
|---|---|---|
| 0 (direct buckets only) | 4.82% | 6.84% |
| 2 | 11.86% | 17.53% |
| 6 (the original setting) | 20.99% | 28.48% |
| 12 | 30.65% | 38.61% |

The direct-bucket share is stable (5.08% in the first sample, 4.82% in the second); everything above it is a function of how many preceding turns you decide to call routing-related.

**Declared versus actual routing** (outcome-ledger rows since the enum rule of 2026-09-21; 101 rows): declared equals actual in 82 rows, differs in 19. Of the 19, 14 are one enum spelling split (two enum values for "the main model did it") and 5 are other differences (2 to another coding lane, 1 to a sub-agent, 2 where the actual value was not a recognised enum value). Rework rate: 32.9% for matching rows (27 of 82) versus 52.6% for differing rows (10 of 19); small n, intervals overlap. For contrast, before the enum rule, 90 of 216 ledger rows (42%) looked like deviations; most of that was free-text spelling.

**Other first-hand facts from the same measurement:**

- Only two task shapes in the whole routing table had at least five completed goal files as precedent (one with 6, one with 8).
- Of 23 bold row names in the routing table, the first version of the parser recognised 2 (the real rows put a parenthesised criterion after the bold name); the test fixture used the simple form, so the three tests passed anyway. Fixed by the orchestrator when run on the real file.
- Three unit tests, 14 synthetic assistant turns in the fixture, assertions include "no session id and no path appear in the output".
- The plan's own initial go bar for this measurement was recorded as 25%; the task-share measured 22.1% (just under) and the output-token share 28.7% (over), and the project went ahead. Treat the figure as a ceiling that did not decisively clear its own bar.

## What did not work

- Reading 22.1% as "routine judgment". It is overhead plus a guessed window. The independent acceptance review of this measurement graded it partial for the same reason: it measures the total overhead ceiling, not the share a specific mechanism could actually take over.
- Using the free-text declared and actual fields for any comparison.
- A parser validated only on its own synthetic fixture.

## Pitfalls

| Symptom | Root cause | Fix |
|---|---|---|
| 22% looked like a large opportunity | 77% of it came from a window of 6 turns | Report direct buckets and the window separately; run a sensitivity table |
| Tests green, real run found 2 of 23 table rows | Synthetic fixture used a simpler row format than the real file | Run the parser on the real file once and assert on the count |
| 42% "deviation" in routing | Free-text labels; one concept spelled several ways | Enum with a normalizer; count spelling drift separately from real deviation |
| Shares differ between two runs a day apart | Live sessions keep appending | Snapshot the directory (copy or list by mtime) before measuring |

## The rule

Measure the ceiling from your own logs before you build an efficiency mechanism, split the measurement into what is directly identified and what depends on a tunable window, and show how the number moves when you change the window.
See [offline interfaces](interfaces.md) for the sanitized implementation and [complete results](results.md) for dated tables. Historical numbers are transcribed from the supplied fact record; synthetic tests do not reproduce those observations.
