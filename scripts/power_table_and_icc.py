#!/usr/bin/env python3
"""Derived calculation companion; the formula matches the baseline calculator.
Sample size per arm for a two-proportion test, a power table, and a design-effect check by grouping key.
Input: a JSONL file, one task per line: {"ts": "...", "rework": true|false|null, "group": "<goal id>"}.
Usage: power-table-and-icc.py tasks.jsonl [--effect 0.05]
Formula (same constants as the production baseline script): z_alpha=1.96 (two-sided .05), z_beta=0.84 (power .8)
  n = (z_a*sqrt(2*pbar*(1-pbar)) + z_b*sqrt(p1*(1-p1)+p2*(1-p2)))**2 / effect**2, p1=baseline rate, p2=p1-effect, pbar=(p1+p2)/2
"""
import collections, json, math, sys

ZA, ZB = 1.96, 0.84


def raw_n_per_arm(p, effect, za=ZA, zb=ZB):
    if not 0 < effect < p <= 1:
        raise ValueError("not estimable: require 0 < effect < baseline <= 1")
    p1, p2 = p, p - effect
    pb = (p1 + p2) / 2
    return ((za * math.sqrt(2 * pb * (1 - pb)) + zb * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2) / effect ** 2


def n_per_arm(p, effect, za=ZA, zb=ZB):
    return math.ceil(raw_n_per_arm(p, effect, za, zb))


def icc_anova(groups):
    """One-way ANOVA intraclass correlation for 0/1 outcomes; groups = {key: [0/1, ...]}."""
    k = len(groups)
    sizes = [len(v) for v in groups.values()]
    n = sum(sizes)
    if k < 2 or n <= k or any(s == 0 for s in sizes):
        raise ValueError("ICC not estimable for this grouping")
    gm = sum(sum(v) for v in groups.values()) / n
    ssb = sum(len(v) * (sum(v) / len(v) - gm) ** 2 for v in groups.values())
    ssw = sum(sum((x - sum(v) / len(v)) ** 2 for x in v) for v in groups.values())
    msb, msw = ssb / (k - 1), ssw / (n - k)
    n0 = (n - sum(s * s for s in sizes) / n) / (k - 1)
    denominator = msb + (n0 - 1) * msw
    if denominator == 0:
        raise ValueError("ICC not estimable: no outcome variation")
    return (msb - msw) / denominator, n / k


def selftest():
    assert n_per_arm(0.3713, 0.05) == 1419            # the number reported in the book
    assert n_per_arm(0.3713, 0.10) == 341
    g = {f"g{i}": [1, 1, 1, 1] if i % 2 else [0, 0, 0, 0] for i in range(10)}   # perfectly clustered
    icc, m = icc_anova(g)
    assert icc > 0.99, icc
    print("power-table selftest PASSED")


def main():
    if "--selftest" in sys.argv:
        return selftest()
    effect = float(sys.argv[sys.argv.index("--effect") + 1]) if "--effect" in sys.argv else 0.05
    rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
    lab = [r for r in rows if isinstance(r.get("rework"), bool)]
    p = sum(1 for r in lab if r["rework"]) / len(lab)
    print(f"labelled={len(lab)} unknown={len(rows) - len(lab)} baseline_rate={p:.4f}")
    for eff in (0.05, 0.10, 0.15, 0.20):
        print(f"  effect {eff:.2f}: n per arm = {n_per_arm(p, eff)}")
    g = collections.defaultdict(list)
    for r in lab:
        g[r.get("group")].append(1 if r["rework"] else 0)
    icc, mbar = icc_anova(g)
    deff = 1 + (mbar - 1) * icc
    print(f"groups={len(g)} mean_size={mbar:.2f} ICC={icc:.3f} design_effect={deff:.2f} n_per_arm_adjusted({effect})={math.ceil(n_per_arm(p, effect) * deff)}")


if __name__ == "__main__":
    main()
