#!/bin/bash
# run_math_batch.sh — Processa todos os MIDIs 1 por vez usando musescore_orchestrate_math.py
# Retoma de onde parou (pula arquivos já gerados).
# Uso: bash run_math_batch.sh [pasta_mid] [pasta_saida]

set -euo pipefail

# Sincroniza o diretório de trabalho com a raiz do projeto
cd "$(dirname "$0")/.."

MIDI_DIR="${1:-mid}"
OUT_DIR="${2:-brass}"
LOG_FILE="$OUT_DIR/batch_math.log"
PAUSE_BETWEEN=2    # segundos de pausa entre arquivos (deixa CPU esfriar)
PRESET=2           # Default para Mellow Brass (seu preset preferido!)
SPEED=1.0          # Fator de velocidade padrão (1.0x = 80 BPM original)

# Inicializa conda
CONDA_BASE=$(conda info --base 2>/dev/null || echo "")
if [ -n "$CONDA_BASE" ]; then
    source "$CONDA_BASE/etc/profile.d/conda.sh"
    conda activate ddsp 2>/dev/null || true
fi

mkdir -p "$OUT_DIR"

# Lista todos os MIDIs em ordem
MIDIS=()
while IFS= read -r line; do
    [ -n "$line" ] && MIDIS+=("$line")
done < <(ls -1 "$MIDI_DIR"/*.mid 2>/dev/null | sort)
TOTAL=${#MIDIS[@]}

if [ "$TOTAL" -eq 0 ]; then
    echo "Nenhum arquivo .mid encontrado em '$MIDI_DIR'"
    exit 1
fi

echo "════════════════════════════════════════════════════════════"
echo "  MuseScore Math Batch — $TOTAL arquivos MIDI → $OUT_DIR/"
echo "  Preset Selecionado   : $PRESET (Mellow Brass)"
echo "  Velocidade           : ${SPEED}x"
echo "  Log: $LOG_FILE"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "════════════════════════════════════════════════════════════"
echo ""

DONE=0
SKIP=0
FAIL=0

for i in "${!MIDIS[@]}"; do
    MIDI="${MIDIS[$i]}"
    NUM=$((i + 1))
    BASENAME=$(basename "$MIDI" .mid)
    # musescore_orchestrate_math.py salva com o mesmo nome e extensão .mp3
    OUT_MP3="$OUT_DIR/${BASENAME}.mp3"

    # Pula se já existe
    if [ -f "$OUT_MP3" ]; then
        echo "[$NUM/$TOTAL] ✓ (já existe) $BASENAME"
        SKIP=$((SKIP + 1))
        continue
    fi

    echo "[$NUM/$TOTAL] ▶ $BASENAME..."

    START=$(date +%s)

    # Processa 1 arquivo
    if python musescore_orchestrate_math.py --midi "$MIDI" --output "$OUT_DIR" --preset "$PRESET" --speed "$SPEED" >> "$LOG_FILE" 2>&1; then
        END=$(date +%s)
        ELAPSED=$((END - START))
        echo "    → concluído em ${ELAPSED}s"
        echo "$(date '+%H:%M:%S') OK  [$NUM/$TOTAL] $BASENAME (${ELAPSED}s)" >> "$LOG_FILE"
        DONE=$((DONE + 1))
    else
        echo "    → FALHOU"
        echo "$(date '+%H:%M:%S') ERR [$NUM/$TOTAL] $BASENAME" >> "$LOG_FILE"
        FAIL=$((FAIL + 1))
    fi

    # Pausa breve
    if [ "$NUM" -lt "$TOTAL" ]; then
        sleep "$PAUSE_BETWEEN"
    fi
done

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Concluído!"
echo "  ✓ Gerados:  $DONE"
echo "  → Pulados:  $SKIP (já existiam)"
echo "  ✗ Falhas:   $FAIL"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "════════════════════════════════════════════════════════════"
