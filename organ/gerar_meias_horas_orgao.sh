#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# gerar_meias_horas_orgao.sh
# ═══════════════════════════════════════════════════════════════════
# Gera hinos completos com progressão de timbres de órgão por frase.
# Cada frase do hino usa uma combinação diferente, progredindo de
# timbres simples (Drawbar puro) até complexos (Split Full).
#
# Uso:
#   cd /Volumes/Dados/work/ia-music
#   bash organ/gerar_meias_horas_orgao.sh
# ═══════════════════════════════════════════════════════════════════

set -e

cd "$(dirname "$0")/.."

PYTHON=".venv/bin/python"
SCRIPT="organ/gerar_hino_orgao_completo.py"
OUTDIR="output/meia_hora/orgao_progressivo"

# Lista de hinos
HINOS=(1 2 15 20 23 27 32 38 39 48 49 61 62 81 96 109 121 131 132 135 150 164 165 189 193 194 199 208 235 247 248 260 262 274 276 278 293 314 346 351 357 363 365 373 374 375 383 397 400 421)

TOTAL=${#HINOS[@]}
CURRENT=0
ERRORS=0

mkdir -p "$OUTDIR"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  GERAÇÃO DE HINOS — ÓRGÃO PROGRESSIVO"
echo "  ${TOTAL} hinos com progressão de timbre por frase"
echo "  Saída: ${OUTDIR}/"
echo "════════════════════════════════════════════════════════════"
echo ""

for HINO in "${HINOS[@]}"; do
  CURRENT=$((CURRENT + 1))

  # Encontra o MIDI correspondente
  MIDI_FILE=$(find mid/ -name "${HINO}-*" -o -name "${HINO} -*" -o -name "0${HINO}-*" -o -name "0${HINO} -*" | grep -v '/\.' | head -1)

  if [ -z "$MIDI_FILE" ]; then
    # Tenta formato com 3 dígitos
    MIDI_FILE=$(find mid/ -name "$(printf '%03d' $HINO)-*" -o -name "$(printf '%03d' $HINO) -*" | grep -v '/\.' | head -1)
  fi

  if [ -z "$MIDI_FILE" ]; then
    echo "[${CURRENT}/${TOTAL}] ⚠️  Hino ${HINO} não encontrado. Pulando."
    ERRORS=$((ERRORS + 1))
    continue
  fi

  BASENAME=$(basename "$MIDI_FILE" .mid)
  OUT_MP3="${OUTDIR}/${BASENAME}_lento.mp3"

  echo "[${CURRENT}/${TOTAL}] Hino ${HINO}: ${BASENAME}"

  $PYTHON $SCRIPT \
    --midi "$MIDI_FILE" \
    --out "$OUT_MP3" \
    --speed 0.5

done

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  ✅ CONCLUÍDO! $((TOTAL - ERRORS))/${TOTAL} hinos gerados."
echo "  Erros: ${ERRORS}"
echo "  Pasta: ${OUTDIR}/"
echo "════════════════════════════════════════════════════════════"
