#!/bin/bash
# run_strings_16part_test.sh — Executa os 2 testes com 16 instrumentos (Presets 1 e 2) a 90% de velocidade
set -euo pipefail

# Sincroniza o diretório de trabalho com a raiz do projeto
cd "$(dirname "$0")/.."

CONDA_BASE=$(conda info --base 2>/dev/null || echo "")
if [ -n "$CONDA_BASE" ]; then
    source "$CONDA_BASE/etc/profile.d/conda.sh"
    conda activate ddsp 2>/dev/null || true
fi

# Encontra o MIDI 002
MIDI_FILE=$(ls -1 mid/002-*.mid 2>/dev/null | head -n 1 || echo "")
if [ -z "$MIDI_FILE" ]; then
    MIDI_FILE=$(ls -1 mid/*.mid 2>/dev/null | head -n 1 || echo "")
fi

if [ -z "$MIDI_FILE" ]; then
    echo "Erro: Nenhum arquivo MIDI encontrado em 'mid/'"
    exit 1
fi

echo "========================================================"
echo "Iniciando 2 testes com 16 cordas (4 por voz) a 90% da velocidade"
echo "Arquivo MIDI: $MIDI_FILE"
echo "========================================================"

# Teste 1: Sinfônica de Seção Completa
echo "▶ Executando Modelo 1: Sinfônica de Seção Completa..."
python musescore_strings_16part.py --midi "$MIDI_FILE" --preset 1 --speed 0.9 --output output_strings_16part

# Teste 2: Octeto Solista Dobrado
echo "▶ Executando Modelo 2: Octeto Solista Dobrado..."
python musescore_strings_16part.py --midi "$MIDI_FILE" --preset 2 --speed 0.9 --output output_strings_16part

# Teste 3: Híbrido Seção e Solo
echo "▶ Executando Modelo 3: Híbrido Seção e Solo..."
python musescore_strings_16part.py --midi "$MIDI_FILE" --preset 3 --speed 0.9 --output output_strings_16part

# Teste 4: Concerto Chamber Misto
echo "▶ Executando Modelo 4: Concerto Chamber Misto..."
python musescore_strings_16part.py --midi "$MIDI_FILE" --preset 4 --speed 0.9 --output output_strings_16part

# Teste 5: Orquestra de Cordas Aprovada
echo "▶ Executando Modelo 5: Orquestra de Cordas Aprovada (Personalizada)..."
python musescore_strings_16part.py --midi "$MIDI_FILE" --preset 5 --speed 0.9 --output output_strings_16part

# Teste 6: Pizzicato Total Ensemble
echo "▶ Executando Modelo 6: Pizzicato Total Ensemble..."
python musescore_strings_16part.py --midi "$MIDI_FILE" --preset 6 --speed 0.9 --output output_strings_16part

# Teste 7: Cinematic Tremolo Ensemble
echo "▶ Executando Modelo 7: Cinematic Tremolo Ensemble..."
python musescore_strings_16part.py --midi "$MIDI_FILE" --preset 7 --speed 0.9 --output output_strings_16part

# Teste 8: Arpa e Cordas de Câmara
echo "▶ Executando Modelo 8: Arpa e Cordas de Câmara..."
python musescore_strings_16part.py --midi "$MIDI_FILE" --preset 8 --speed 0.9 --output output_strings_16part

# Teste 9: Contraste Estéreo (Solo vs Seção)
echo "▶ Executando Modelo 9: Contraste Estéreo (Solo vs Seção)..."
python musescore_strings_16part.py --midi "$MIDI_FILE" --preset 9 --speed 0.9 --output output_strings_16part

echo "--------------------------------------------------------"
echo "Processo concluído! Os áudios estão em output_strings_16part/"
ls -lh output_strings_16part/
echo "--------------------------------------------------------"
