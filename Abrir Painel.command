#!/bin/bash
# Lancador do Painel Multicorder. Basta dar DOIS CLIQUES neste arquivo.
cd "$(dirname "$0")"

echo "🎬 Preparando o Painel Multicorder..."

# cria o ambiente na primeira vez
if [ ! -d ".venv" ]; then
  echo "Primeira execucao: instalando (pode levar 1-2 min)..."
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -q --upgrade pip
  pip install -q -r requirements.txt
else
  source .venv/bin/activate
fi

# abre o navegador automaticamente alguns segundos depois
( sleep 3 && open "http://127.0.0.1:5001" ) &

echo "✅ Abrindo o painel em http://127.0.0.1:5001"
echo "   (Para FECHAR o painel, feche esta janela do Terminal ou aperte Ctrl+C.)"
echo ""
python webapp/app.py
