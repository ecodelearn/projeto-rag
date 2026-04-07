#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/ecode/Documents/projetos/projeto-rag"
SRC="$ROOT/sources/rag_memory/02 - RAG with memory"

if [[ ! -d "$SRC" ]]; then
  echo "[erro] fonte nao encontrada: $SRC"
  exit 1
fi

cd "$SRC"

echo "[1/4] preparando shim de compatibilidade..."
if [[ ! -f memory_rag.py ]]; then
  cat > memory_rag.py <<'PY'
from memory import Memory as MemoryRAG
PY
  echo "[ok] criado memory_rag.py"
else
  echo "[ok] memory_rag.py ja existe"
fi

echo "[2/4] subindo redis (docker compose)..."
docker compose up -d

echo "[3/4] preparando ambiente python (uv)..."
if [[ ! -d .venv ]]; then
  uv venv
fi
uv pip install -r requirements.txt
uv pip install python-dotenv redis google-genai streamlit

echo "[4/4] validacoes finais"
if [[ -z "${GEMINI_API_KEY:-}" && -z "${GOOGLE_API_KEY:-}" ]]; then
  echo "[aviso] defina GEMINI_API_KEY (ou GOOGLE_API_KEY) antes de rodar"
fi

echo "\nPronto. Proximos comandos:"
echo "  cd \"$SRC\""
echo "  source .venv/bin/activate"
echo "  export GOOGLE_API_KEY=\"\${GOOGLE_API_KEY:-\${GEMINI_API_KEY:-}}\""
echo "  python main.py"
