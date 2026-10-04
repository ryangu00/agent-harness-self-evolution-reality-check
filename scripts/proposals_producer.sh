#!/usr/bin/env bash
# Synthetic producer skeleton: byte and line offsets, no model or network calls.
set -euo pipefail
S="${HARNESS_STATE_DIR:-.work/state}"
if [ "${1:-}" = --state-dir ]; then S="$2"; shift 2; fi
lessons="${1:?usage: proposals_producer.sh [--state-dir DIR] lessons outcomes}"
outcomes="${2:?outcomes file required}"
reader="$(cd "$(dirname "$0")" && pwd)/is_paused.sh"
if bash "$reader" proposals "$S/paused.json"; then
  echo 'producer: paused'
  exit 0
fi
exec python3 - "$S" "$lessons" "$outcomes" <<'PY'
import json, os, pathlib, sys
root, lessons, outcomes = map(pathlib.Path, sys.argv[1:])
root.mkdir(parents=True, exist_ok=True)
size = len(lessons.read_bytes())
count = len(outcomes.read_text().splitlines())
state = root/'producer-offsets.json'
previous = json.loads(state.read_text()) if state.exists() else {'bytes':size, 'lines':0}
left = previous['bytes'] if size >= previous['bytes'] else 0
rows = previous['lines'] if count >= previous['lines'] else 0
if size <= left and count <= rows:
    print('producer: no new fuel')
    raise SystemExit(0)
with (root/'proposals.jsonl').open('a') as out:
    out.write(json.dumps({'new_bytes':size-left,'new_rows':count-rows,'status':'pending review'})+'\n')
temporary = root/'producer-offsets.json.tmp'
temporary.write_text(json.dumps({'bytes':size,'lines':count})+'\n')
os.replace(temporary, state)
print('producer: appended synthetic batch')
PY
