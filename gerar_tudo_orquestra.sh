#!/bin/bash

# Script utilitário para gerar a orquestra completa (todos os hinos e coros)
# Uso:
#   ./gerar_tudo_orquestra.sh [--speed-factor 1.0]
#   ./gerar_tudo_orquestra.sh --start 1 --end 5 --speed-factor 0.85

# Garante que estamos na pasta correta
cd "$(dirname "$0")"

# Verifica se o ambiente virtual existe
if [ ! -d ".venv" ]; then
    echo "❌ Erro: Ambiente virtual .venv não encontrado."
    echo "Por favor, crie o ambiente virtual e instale as dependências antes de rodar."
    exit 1
fi

# Ativa o ambiente virtual
source .venv/bin/activate

echo "🎵 Iniciando a geração da orquestra..."
python utils/gerar_lote_orquestra.py "$@"
