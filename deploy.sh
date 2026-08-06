#!/bin/bash
# Deploy with the SERVED COMMIT stamped exactly.
#
# `ui/build.py` reads CG_COMMIT or runs/BUILD at import. Both are written HERE, from the
# real HEAD at push time, so the stamp cannot lag: a file committed into git would name its
# own parent, and an env var set by hand would name whatever was set last.
set -euo pipefail
cd "$(dirname "$0")"
COMMIT=$(git rev-parse HEAD | cut -c1-12)
DIRTY=$(git status --porcelain | wc -l)
if [ "$DIRTY" -ne 0 ]; then
  echo "refusing to deploy a dirty tree: $DIRTY uncommitted change(s)." >&2
  echo "the served stamp would name a commit that is not what is being served." >&2
  exit 1
fi
echo "$COMMIT" > runs/BUILD
echo "deploying $COMMIT"
railway up --detach
