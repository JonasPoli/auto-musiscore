#!/bin/bash
# run_strings_test.sh — Compara os 20 presets de cordas usando 002- De Deus tu és eleita.mid
set -euo pipefail

# Sincroniza o diretório de trabalho com a raiz do projeto
cd "$(dirname "$0")/.."

# Inicializa conda se disponível
CONDA_BASE=$(conda info --base 2>/dev/null || echo "")
if [ -n "$CONDA_BASE" ]; then
    source "$CONDA_BASE/etc/profile.d/conda.sh"
    conda activate ddsp 2>/dev/null || true
fi

# Acha o arquivo MIDI 002
MIDI_FILE=$(ls -1 mid/002-*.mid 2>/dev/null | head -n 1 || echo "")

if [ -z "$MIDI_FILE" ]; then
    # Se não achar o 002, pega o primeiro da pasta
    MIDI_FILE=$(ls -1 mid/*.mid 2>/dev/null | head -n 1 || echo "")
fi

if [ -z "$MIDI_FILE" ]; then
    echo "Erro: Nenhum arquivo MIDI encontrado em 'mid/'"
    exit 1
fi

echo "Iniciando a renderização de teste para cordas com o arquivo: $MIDI_FILE"
python tests/musescore_strings_render_test.py --midi "$MIDI_FILE" --presets all --output output_strings_test

echo "--------------------------------------------------------"
echo "Processo concluído! Os áudios estão em output_strings_test/"
ls -1 output_strings_test/
echo "--------------------------------------------------------"
