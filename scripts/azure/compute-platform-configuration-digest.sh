#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:-$(pwd)}"
POLICY="${2:-$REPO_ROOT/config/platform-configuration-digest-v1.yaml}"
[[ -d "$REPO_ROOT" && -f "$POLICY" ]] || { printf 'platform digest: repository/policy missing\n' >&2; exit 2; }

python3 - "$REPO_ROOT" "$POLICY" <<'PY'
import fnmatch, hashlib, json, os, pathlib, stat, sys

root = pathlib.Path(sys.argv[1]).resolve()
policy_path = pathlib.Path(sys.argv[2]).resolve()
policy = json.loads(policy_path.read_text())
if policy.get("schemaVersion") != 1 or policy.get("algorithm") != "sha256-canonical-path-mode-length-content-v1":
    raise SystemExit("platform digest: unsupported policy")

def matches(path, patterns):
    return any(fnmatch.fnmatchcase(path, pattern) or pathlib.PurePosixPath(path).match(pattern) for pattern in patterns)

files = {}
for pattern in policy["includes"]:
    for candidate in root.glob(pattern):
        if candidate.is_file() and not candidate.is_symlink():
            relative = candidate.relative_to(root).as_posix()
            if not matches(relative, policy["excludes"]):
                files[relative.encode()] = candidate

records = []
for encoded in sorted(files):
    path = files[encoded]
    content = path.read_bytes()
    mode = format(stat.S_IMODE(path.stat().st_mode), "04o")
    records.append({"path": encoded.decode(), "mode": mode, "length": len(content), "sha256": hashlib.sha256(content).hexdigest()})
canonical = b"".join(json.dumps(record, sort_keys=True, separators=(",", ":")).encode() + b"\n" for record in records)
print(json.dumps({"schemaVersion": 1, "algorithm": policy["algorithm"], "digest": "sha256:" + hashlib.sha256(canonical).hexdigest(), "recordCount": len(records), "records": records}, sort_keys=True, separators=(",", ":")))
PY
