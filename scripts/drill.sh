#!/usr/bin/env bash
# Real outage/metrics injection; remaining scenarios are explicitly SKIP.
set -uo pipefail
S="${HARNESS_STATE_DIR:-.work/state}"
scen="${1:?usage: drill.sh outage|metrics|badchange|concurrent|all [--no-discord] [--state-dir DIR]}"
shift
WD="$(cd "$(dirname "$0")" && pwd)/watchdog.sh"
DRY=0
NOTIFY=1
while [ "$#" -gt 0 ]; do
  case "$1" in
    --state-dir) S="$2"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    --no-discord|--no-notify) NOTIFY=0; shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
exec python3 - "$S" "$WD" "$scen" "$DRY" "$NOTIFY" <<'PY'
import json, os, pathlib, signal, subprocess, sys, time, uuid
root, watchdog, scenario = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
dry, notify = sys.argv[4] == '1', sys.argv[5] == '1'
scenarios = ['outage','metrics','badchange','concurrent'] if scenario == 'all' else [scenario]
if any(s not in ('outage','metrics','badchange','concurrent') for s in scenarios):
    raise SystemExit('unknown scenario')
root.mkdir(parents=True, exist_ok=True)
def interrupted(signum, frame):
    raise KeyboardInterrupt
signal.signal(signal.SIGINT, interrupted)
signal.signal(signal.SIGTERM, interrupted)
def run():
    cmd = ['/bin/bash', watchdog, '--state-dir', str(root)]
    if not notify:
        cmd.append('--dry-run')
    completed = subprocess.run(cmd, capture_output=True, text=True)
    try:
        state = json.loads((root/'watchdog-last.json').read_text())
    except (OSError, ValueError):
        state = {}
    return completed.returncode, state
failed = False
for scenario in scenarios:
    record = dict(scenario=scenario, run_id=uuid.uuid4().hex, notify_rc=None)
    if dry or scenario in ('badchange','concurrent'):
        record.update(result='SKIP', reason='not implemented' if not dry else 'dry run')
    else:
        target = root/('heartbeat' if scenario == 'outage' else 'baseline-latest.json')
        original = None
        try:
            initial_rc, initial = run()
            if initial_rc != 0 or initial.get('ok') is not True or not initial.get('run_id'):
                raise ValueError('healthy starting state required')
            original = target.read_bytes(), target.stat().st_atime_ns, target.stat().st_mtime_ns
            try:
                if scenario == 'outage':
                    stamp = time.time()-8*86400
                    os.utime(target, (stamp, stamp))
                else:
                    target.unlink()
                red_rc, red = run()
                record['notify_rc'] = red.get('notify_rc')
            finally:
                target.write_bytes(original[0])
                os.utime(target, ns=original[1:])
            green_rc, green = run()
            ids = [initial.get('run_id'), red.get('run_id'), green.get('run_id')]
            passed = (red_rc != 0 and red.get('ok') is False and
                      any(target.name in p for p in red.get('problems', [])) and
                      green_rc == 0 and green.get('ok') is True and
                      all(ids) and len(set(ids)) == len(ids))
            record.update(result='PASS' if passed else 'FAIL', reason='red then green' if passed else 'state assertions failed')
        except (OSError, ValueError) as exc:
            record.update(result='FAIL', reason=str(exc))
    failed |= record['result'] == 'FAIL'
    with (root/'drills.jsonl').open('a') as out:
        out.write(json.dumps(record)+'\n')
    print('drill['+scenario+'] result='+record['result'])
sys.exit(1 if failed else 0)
PY
