#!/bin/bash
# Deploy with the SERVED COMMIT stamped exactly.
#
# `ui/build.py` reads CG_COMMIT or runs/BUILD at import. Both are written HERE, from the
# real HEAD at push time, so the stamp cannot lag: a file committed into git would name its
# own parent, and an env var set by hand would name whatever was set last.
set -euo pipefail
cd "$(dirname "$0")"
COMMIT=$(git rev-parse HEAD | cut -c1-12)
# SOURCE dirtiness only. `runs/` is evidence, not build output — the daemon appends to its
# walk log continuously, so including it would mean the tree is never clean while the
# sampler runs and this guard would refuse forever. What the stamp names is the CODE being
# served, and evidence appended by a running process does not change the code.
DIRTY=$(git status --porcelain -- . ':(exclude)runs' | wc -l)
if [ "$DIRTY" -ne 0 ]; then
  echo "refusing to deploy: $DIRTY uncommitted SOURCE change(s)." >&2
  echo "the served stamp would name a commit that is not what is being served." >&2
  git status --short -- . ':(exclude)runs' >&2
  exit 1
fi
# The stamp reaches the image as an ENV VAR, not a file. `runs/BUILD` is gitignored and
# `railway up` honours gitignore, so the file never shipped — which is precisely why the
# first stamped deploy still reported `unknown`. The variable is set from the real HEAD
# here, immediately before the push, so it cannot name anything else.
echo "$COMMIT" > runs/BUILD          # for a local run, which reads the file
echo "deploying $COMMIT"
railway variables --set "CG_COMMIT=$COMMIT" --skip-deploys >/dev/null
railway up --detach

# ─── A DEPLOY IS NOT LANDED UNTIL ITS BATTERY RUN IS ATTACHED ────────────────────────────
#
# Green tests have twice coexisted with a served page that could not answer, and every defect
# the live-fire battery checks for was found by the operator reading a transcript AFTER a green
# suite. So "deployed" and "landed" are different words here: `railway up` returns as soon as
# the image is accepted, and what follows is the part that decides whether the thing that is
# now serving works.
#
# It waits for the SERVED stamp to be the commit it just pushed — not for the build to finish,
# which is a different fact — and then fires the battery at it. Findings do not fail the
# deploy: the deploy already happened, and a script that pretended otherwise would be lying
# about state. They fail the LANDING, which is a claim this script then declines to make.
if [ "${CG_SKIP_AUDIT:-}" = "1" ]; then
  echo "battery skipped (CG_SKIP_AUDIT=1) — this deploy is DEPLOYED, not LANDED"
  exit 0
fi
if [ -z "${CG_URL:-}" ] || [ -z "${CG_TOKEN:-}" ]; then
  echo "CG_URL/CG_TOKEN unset — cannot audit the deploy; DEPLOYED, not LANDED" >&2
  exit 0
fi
echo "waiting for $COMMIT to serve..."
for i in $(seq 1 40); do
  SERVED=$(curl -s --max-time 20 "$CG_URL/corpus?t=$CG_TOKEN" \
           | python3 -c 'import sys,json;print(json.load(sys.stdin).get("build",{}).get("served",""))' 2>/dev/null || true)
  [ "$SERVED" = "$COMMIT" ] && break
  sleep 20
done
if [ "$SERVED" != "$COMMIT" ]; then
  echo "the deploy never began serving $COMMIT (last seen: ${SERVED:-none}) — NOT LANDED" >&2
  exit 1
fi
echo "serving $COMMIT — running the live-fire battery"
python3 tools/livefire.py --out runs/livefire && LANDED=1 || LANDED=0
if [ "$LANDED" = "1" ]; then
  echo "LANDED $COMMIT — battery clean, artifact at runs/livefire/$COMMIT.json"
else
  echo "DEPLOYED $COMMIT, NOT LANDED — the battery raised findings; see runs/livefire/$COMMIT.json" >&2
  exit 1
fi
