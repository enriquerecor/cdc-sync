#!/usr/bin/env bash

set -euo pipefail

printf '[e2e] ERROR: %s\n' \
  "validate-local.sh está obsoleto temporalmente: dependía del fixture JSON local eliminado en #28. La validación completa queda delegada a #33." >&2
exit 1
