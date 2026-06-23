#!/usr/bin/env bash
# install_midi_pipeline.sh — Instala o pipeline de orquestração MIDI
set -e

# Sincroniza o diretório de trabalho com a raiz do projeto
cd "$(dirname "$0")/.."
PIP=".venv/bin/pip"

echo "[1/4] basic-pitch (Spotify — transcrição áudio → MIDI)"
$PIP install basic-pitch --quiet

echo "[2/4] pretty_midi (manipulação e orquestração MIDI)"
$PIP install pretty_midi --quiet

echo "[3/4] midi2audio / FluidSynth binding"
$PIP install midi2audio --quiet

echo "[4/4] Verificando FluidSynth no sistema..."
if command -v fluidsynth &> /dev/null; then
    echo "  ✅ FluidSynth já instalado: $(fluidsynth --version 2>&1 | head -1)"
else
    echo "  ⚠️  FluidSynth NÃO encontrado. Instale com:"
    echo "       brew install fluidsynth"
fi

echo ""
echo "==== Testando imports ===="
.venv/bin/python - << 'PYEOF'
import pretty_midi; print(f"  pretty_midi : OK")
try:
    from basic_pitch.inference import predict
    print(f"  basic-pitch : OK")
except Exception as e:
    print(f"  basic-pitch : {e}")
print("\n✅ Pipeline MIDI pronto!")
PYEOF
