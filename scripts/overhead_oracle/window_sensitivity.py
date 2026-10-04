#!/usr/bin/env python3
"""Window sensitivity over synthetic or reader-owned transcripts.
Re-runs the overhead oracle (oracle.py, same directory) for several window sizes and prints only aggregate shares.
Usage: oracle-window-sensitivity.py <dir-of-session-jsonl> <classifier-config.json>
"""
import sys
sys.dont_write_bytecode = True
import json, oracle

for w in (0, 2, 6, 12):
    d = oracle.analyze(sys.argv[1], w, json.load(open(sys.argv[2])))
    total_out = sum(d["buckets"][b]["output_tokens"] for b in d["buckets"])
    base_turns = sum(d["buckets"][b]["turns"] for b in oracle.BASE_OVERHEAD)
    base_out = sum(d["buckets"][b]["output_tokens"] for b in oracle.BASE_OVERHEAD)
    print(json.dumps({"window": w, "sessions": d["sessions_scanned"], "turns": d["assistant_turns"],
                      "direct_share_turns": round(base_turns / d["assistant_turns"], 4) if d["assistant_turns"] else None,
                      "direct_share_output": round(base_out / total_out, 4) if total_out else None,
                      "total_share_turns": round(d["share"]["turns"], 4),
                      "total_share_output": round(d["share"]["output_tokens"], 4)}))
