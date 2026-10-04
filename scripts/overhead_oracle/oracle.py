import argparse, json, re
from pathlib import Path

BUCKETS = ("plan-writing", "routing", "review", "question", "closeout", "text-only", "work")
BASE_OVERHEAD = ("plan-writing", "routing", "review", "question", "closeout")
METRICS = ("turns", "output_tokens", "cache_read_tokens", "cache_creation_tokens")


def empty():
    return {k: 0 for k in METRICS}


def add(dst, usage):
    dst["turns"] += 1
    dst["output_tokens"] += int(usage.get("output_tokens", 0) or 0)
    dst["cache_read_tokens"] += int(usage.get("cache_read_input_tokens", 0) or 0)
    dst["cache_creation_tokens"] += int(usage.get("cache_creation_input_tokens", 0) or 0)


def tool_text(tool):
    inp = tool.get("input") or {}
    return str(inp.get("file_path", "")) + " " + str(inp.get("command", ""))


def classify(blocks, config):
    tools = [b for b in blocks if isinstance(b, dict) and b.get("type") == "tool_use"]
    for bucket in BASE_OVERHEAD:
        for rule in config["rules"][bucket]:
            for tool in tools:
                if tool.get("name") not in rule["tools"]:
                    continue
                inputs = tool.get("input") or {}
                value = str(inputs.get(rule.get("field", ""), ""))
                if re.search(rule.get("pattern", ".*"), value, re.I):
                    return bucket
    return "text-only" if not tools else "work"


def analyze(sessions, window, config):
    buckets = {b: empty() for b in BUCKETS}
    overhead_window = empty()
    by_session, skipped, assistant_turns = [], 0, 0
    for index, path in enumerate(sorted(Path(sessions).glob("*.jsonl"))):
        turns = []
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            skipped += 1
            continue
        for line in lines:
            try:
                obj = json.loads(line)
            except (TypeError, ValueError):
                skipped += 1
                continue
            if not isinstance(obj, dict) or obj.get("type") != "assistant":
                continue
            msg = obj.get("message")
            blocks = msg.get("content") if isinstance(msg, dict) else None
            if not isinstance(blocks, list) or not blocks:
                continue
            usage = msg.get("usage") if isinstance(msg, dict) else {}
            usage = usage if isinstance(usage, dict) else {}
            bucket = classify(blocks, config)
            turns.append((bucket, usage))
            assistant_turns += 1
            add(buckets[bucket], usage)
        for i, (bucket, usage) in enumerate(turns):
            if bucket in ("text-only", "work") and any(turns[j][0] in ("plan-writing", "routing", "review", "closeout")
                                                        for j in range(i + 1, min(len(turns), i + window + 1))):
                add(overhead_window, usage)
        by_session.append(len(turns))
    total_overhead = empty()
    for b in BASE_OVERHEAD:
        for key in METRICS:
            total_overhead[key] += buckets[b][key]
    for key in METRICS:
        total_overhead[key] += overhead_window[key]
    total_output = sum(buckets[b]["output_tokens"] for b in BUCKETS)
    share = {"turns": total_overhead["turns"] / assistant_turns if assistant_turns else 0.0,
             "output_tokens": total_overhead["output_tokens"] / total_output if total_output else 0.0,
             "overhead": total_overhead}
    return {"buckets": buckets, "overhead_window": overhead_window,
            "sessions_scanned": len(by_session), "lines_skipped": skipped,
            "assistant_turns": assistant_turns, "share": share}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sessions", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--window", type=int, default=6)
    a = p.parse_args()
    Path(a.out).write_text(json.dumps(analyze(a.sessions, max(0, a.window), json.loads(Path(a.config).read_text())), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
