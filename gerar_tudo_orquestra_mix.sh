#!/bin/bash

# Script utilitário para gerar os 480 hinos e 6 coros nos estilos Orquestra 01 e Orquestra 02
# Uso:
#   ./gerar_tudo_orquestra_mix.sh [--speed-factor 1.0]
#   ./gerar_tudo_orquestra_mix.sh --style orquestra01
#   ./gerar_tudo_orquestra_mix.sh --style orquestra02
#   ./gerar_tudo_orquestra_mix.sh --start 1 --end 10 --speed-factor 1.0
#   ./gerar_tudo_orquestra_mix.sh --skip-coros
#
# Ao final, executa verificação de completude com retry automático.

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "❌ Erro: Ambiente virtual .venv não encontrado em $(pwd)"
    echo "Por favor, crie o ambiente virtual e instale as dependências antes de rodar."
    exit 1
fi

source .venv/bin/activate

echo "🎵 Iniciando a geração dos estilos Orquestra 01 e Orquestra 02 (Hinos + Coros)..."
python -u utils/gerar_lote_orquestra_mix.py "$@"
GEROU_RC=$?

echo ""
echo "══════════════════════════════════════════════════════════════════"
echo "  🔍 Verificação de completude Orquestra Mix com retry..."
echo "══════════════════════════════════════════════════════════════════"

SPEED_FACTOR="1.0"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --speed-factor)
            SPEED_FACTOR="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

python -u utils/verificar_completude_orquestra_mix.py --regerar --max-retries 2 --speed-factor "$SPEED_FACTOR"
VERIF_RC=$?

if [ $VERIF_RC -eq 0 ]; then
    echo ""
    echo "✅ Pipeline completo! Todos os 480 hinos + 6 coros gerados com sucesso para Orquestra 01 e Orquestra 02."
else
    echo ""
    echo "⚠️  Alguns itens ainda estão faltando após retry. Verifique o relatório acima."
fi

exit $VERIF_RC
