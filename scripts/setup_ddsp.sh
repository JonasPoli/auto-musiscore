#!/bin/bash
# setup_ddsp.sh - Instala DDSP via conda (resolve llvmlite/numba automaticamente)

set -e

# Sincroniza o diretório de trabalho com a raiz do projeto
cd "$(dirname "$0")/.."

echo "=== DDSP Orchestrator Setup (via conda) ==="
echo ""

# Inicializa conda no script
CONDA_BASE=$(conda info --base 2>/dev/null || echo "")
if [ -z "$CONDA_BASE" ]; then
    echo "ERRO: conda não encontrado. Instale Miniconda ou Anaconda."
    exit 1
fi

source "$CONDA_BASE/etc/profile.d/conda.sh"
echo "conda encontrado em: $CONDA_BASE"

# Cria ambiente conda ddsp se não existir
if conda env list | grep -q "^ddsp "; then
    echo "Ambiente 'ddsp' já existe."
else
    echo "Criando ambiente conda 'ddsp' com Python 3.10..."
    conda create -n ddsp python=3.10 -y --quiet
fi

conda activate ddsp
echo "Ambiente ativo: $(which python) — $(python --version)"
echo ""

# Instala dependências via conda (resolve llvmlite/numba nativamente)
echo "Instalando librosa + numba via conda-forge..."
conda install -c conda-forge -y --quiet \
    numba \
    llvmlite \
    librosa \
    scipy \
    numpy

echo "✓ conda packages instalados"
echo ""

# Instala pacotes Python via pip
echo "Instalando tensorflow + ddsp via pip..."
pip install --quiet \
    "tensorflow>=2.10" \
    "mido" \
    "pydub" \
    "gin-config" \
    "einops" \
    "soundfile"

# crepe com --no-build-isolation (usa setuptools já instalado)
echo "Instalando crepe..."
pip install --quiet --no-build-isolation "crepe==0.0.12" || \
    pip install --quiet --no-build-isolation crepe

echo "Instalando DDSP..."
pip install --quiet ddsp

echo "✓ pip packages instalados"
echo ""

# Baixa modelos DDSP pré-treinados do Google Storage (acesso público)
mkdir -p models

download_model() {
    local name=$1
    local dir="models/$name"
    mkdir -p "$dir"
    local base="https://storage.googleapis.com/ddsp/models/timbre_transfer/$name"

    echo "Baixando modelo: $name"
    for f in "operative_config-0.gin" "ckpt-300.index" "ckpt-300.data-00000-of-00001" "checkpoint"; do
        if [ ! -f "$dir/$f" ]; then
            echo "  → $f"
            curl -sf -o "$dir/$f" "$base/$f" || echo "  (arquivo $f não encontrado, continuando)"
        else
            echo "  ✓ $f (já existe)"
        fi
    done
    echo "  ✓ Modelo $name pronto"
    echo ""
}

download_model "violin"
download_model "flute"

# Verifica instalação
echo "Verificando imports..."
python - << 'PYEOF'
import tensorflow as tf
import ddsp
import librosa
import mido
print(f"  TensorFlow: {tf.__version__}")
print(f"  DDSP: {ddsp.__version__}")
print(f"  librosa: {librosa.__version__}")
print("  ✓ Todos os imports OK")
PYEOF

echo ""
echo "=== Setup concluído! ==="
echo ""
echo "Para testar com um arquivo:"
echo "  conda activate ddsp"
echo "  python ddsp_orchestrate.py --midi 'mid/241- A Justiça divina.mid'"
echo ""
echo "Para processar TODOS os 487 arquivos:"
echo "  conda activate ddsp"
echo "  python ddsp_orchestrate.py"
