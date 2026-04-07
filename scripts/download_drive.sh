#!/usr/bin/env bash
set -euo pipefail
OUT_DIR="${1:-/home/ecode/Documents/projetos/projeto-rag/downloads}"
mkdir -p "$OUT_DIR"

download_file(){
  local id="$1"
  local out="$2"
  local cookie html confirm
  cookie=$(mktemp)
  html=$(mktemp)
  trap 'rm -f "$cookie" "$html"' RETURN

  curl -s -L -c "$cookie" "https://drive.google.com/uc?export=download&id=${id}" -o "$html"
  confirm=$(grep -o 'confirm=[0-9A-Za-z_-]*' "$html" | head -n1 | cut -d= -f2 || true)

  if [[ -n "${confirm}" ]]; then
    curl -s -L -b "$cookie" "https://drive.google.com/uc?export=download&confirm=${confirm}&id=${id}" -o "$out"
  else
    # Small/public files may download directly
    if grep -qi '<html' "$html"; then
      # try alternate endpoint
      curl -s -L "https://drive.usercontent.google.com/download?id=${id}&export=download&confirm=t" -o "$out"
    else
      cp "$html" "$out"
    fi
  fi

  # sanity check: avoid saving HTML error pages
  if file "$out" | grep -qi 'HTML'; then
    echo "[ERRO] Falha ao baixar ${id} -> ${out} (retornou HTML)" >&2
    return 1
  fi

  echo "[OK] $(basename "$out")"
}

# name|id
while IFS='|' read -r name id; do
  [[ -z "$name" ]] && continue
  download_file "$id" "$OUT_DIR/$name"
done <<'EOF'
rag_classico.zip|14dVRCmtToqm2VXlhwPnGx6RBeY52-zpC
rag_memory.zip|1yo4KgA8R0FYTXqPpe5gTmHPgxZ4oQYFQ
agentic_rag.zip|1DA8-2FojaY2fo_TOk8RF0JgZKHOiaq-u
crag.zip|15cA6zXkkbbgFkBgWn2nq7p1o38pQOf1-
adaptative_rag.zip|1xgePXMMWpKn2dL95DNtyFCbAMKlUd-iq
rag_fusion.zip|1OR6BZBabwd5gkIbaX4mFsP9iBRGYE2qI
hyde_rag.zip|1OR6BZBabwd5gkIbaX4mFsP9iBRGYE2qI
EOF
