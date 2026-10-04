#!/usr/bin/env bash
# State and notifier are configurable; no scheduler or notification is installed.
set -uo pipefail
S="${HARNESS_STATE_DIR:-.work/state}"
DRY=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --state-dir) S="$2"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
exec python3 - "$S" "$DRY" <<'PY'
import datetime as dt, json, os, pathlib, shlex, subprocess, sys, uuid
root, dry = pathlib.Path(sys.argv[1]), sys.argv[2] == '1'
now = dt.datetime.now().astimezone()
problems = []
def check(name, maximum, key=None):
    path = root/name
    try:
        if key:
            stamp = dt.datetime.fromisoformat(json.loads(path.read_text())[key].replace('Z', '+00:00'))
            if not stamp.tzinfo:
                stamp = stamp.astimezone()
        else:
            stamp = dt.datetime.fromtimestamp(path.stat().st_mtime).astimezone()
        age = (now-stamp).total_seconds()/3600
        if age < 0:
            problems.append(name+': future')
        elif age > maximum:
            problems.append(name+': stale')
        return age
    except FileNotFoundError:
        problems.append(name+': missing')
    except Exception:
        problems.append(name+': bad')
    return None
heartbeat = check('heartbeat', 168)
check('paused.json', 72, '_ts')
check('baseline-latest.json', 336, 'ts')
run_id = uuid.uuid4().hex
notify_rc = None
if problems and not dry:
    command = os.environ.get('HARNESS_NOTIFY_COMMAND')
    if not command:
        notify_rc = -1
    else:
        try:
            notify_rc = subprocess.run(shlex.split(command)+['; '.join(problems)], check=False).returncode
        except OSError:
            notify_rc = -1
state = dict(ok=not problems, ts=now.isoformat(timespec='seconds'), run_id=run_id,
             heartbeat_age_h=heartbeat, problems=problems, notify_rc=notify_rc)
root.mkdir(parents=True, exist_ok=True)
temporary = root/('watchdog-'+run_id+'.tmp')
temporary.write_text(json.dumps(state)+'\n')
os.replace(temporary, root/'watchdog-last.json')
print('watchdog: '+('ok' if not problems else 'RED')+' run_id='+run_id)
sys.exit(1 if problems else 0)
PY
