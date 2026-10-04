#!/usr/bin/env bash
# Exit 0 = paused, including uncertainty. Exit 1 = explicitly active.
# Compatible shape: top-level _ts, then one object per line with paused.
line="${1:?usage: is_paused.sh line [state-file]}"
state="${2:-${HARNESS_STATE_DIR:-.work/state}/paused.json}"
exec python3 - "$state" "$line" <<'PY'
import datetime, json, sys
try:
    with open(sys.argv[1]) as source:
        state = json.load(source)
    stamp = datetime.datetime.fromisoformat(state['_ts'].replace('Z', '+00:00'))
    age = (datetime.datetime.now().astimezone() - stamp).total_seconds()
    if age < 0 or age > 3 * 86400:
        raise ValueError('future or stale state')
    paused = state[sys.argv[2]]['paused']
    if not isinstance(paused, bool):
        raise ValueError('paused must be boolean')
    sys.exit(0 if paused else 1)
except Exception as exc:
    print('is-paused: fail-closed: ' + type(exc).__name__ + ': ' + str(exc), file=sys.stderr)
    sys.exit(0)
PY
