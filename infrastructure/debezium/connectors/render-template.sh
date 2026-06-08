#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "Uso: $0 <template> <output> <env_file>" >&2
  exit 1
fi

template_path="$1"
output_path="$2"
env_file_path="$3"

if [[ ! -f "$template_path" ]]; then
  echo "Plantilla no encontrada: $template_path" >&2
  exit 1
fi

if [[ ! -f "$env_file_path" ]]; then
  echo "Fichero de entorno no encontrado: $env_file_path" >&2
  exit 1
fi

mkdir -p "$(dirname "$output_path")"

set -a
# shellcheck disable=SC1090
source "$env_file_path"
set +a

perl -pe 's/\$\{([A-Z0-9_]+)\}/exists $ENV{$1} ? $ENV{$1} : die "Falta la variable $1\n"/ge' \
  "$template_path" > "$output_path"
