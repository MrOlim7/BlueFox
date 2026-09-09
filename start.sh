#!/usr/bin/env bash
# Use only this checkout's virtual environment; never install on launch.
set -eu
BLUEFOX_ROOT="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd -- "$BLUEFOX_ROOT"
if [ -x "$BLUEFOX_ROOT/.venv/bin/python" ]; then
    BLUEFOX_PYTHON="$BLUEFOX_ROOT/.venv/bin/python"
elif [ -x "$BLUEFOX_ROOT/venv/bin/python" ]; then
    BLUEFOX_PYTHON="$BLUEFOX_ROOT/venv/bin/python"
else
    echo 'BlueFox: environnement absent. Dans le dossier du dépôt, exécutez :' >&2
    echo '  python3 -m venv .venv' >&2
    echo '  .venv/bin/python -m pip install -e ".[full]"' >&2
    exit 1
fi
if ! "$BLUEFOX_PYTHON" -c 'import sys; sys.exit(0 if (3, 10) <= sys.version_info[:2] <= (3, 14) else 1)'; then
    echo 'BlueFox: recréez le venv avec Python 3.10 à 3.14.' >&2
    exit 1
fi
exec "$BLUEFOX_PYTHON" "$BLUEFOX_ROOT/BlueFox.py" "$@"
