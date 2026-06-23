#!/usr/bin/env bash
# install.sh — Instala o ambiente AudioCraft com versões pinadas e na ordem certa
set -e

# Sincroniza o diretório de trabalho com a raiz do projeto
cd "$(dirname "$0")/.."
PIP=".venv/bin/pip"

echo "==== [1/9] Pinando numpy 1.26.4 PRIMEIRO ===="
$PIP install "numpy==1.26.4" --quiet

echo "==== [2/9] PyTorch 2.2.2 (CPU, Intel Mac) ===="
$PIP install torch==2.2.2 torchaudio==2.2.2 torchvision==0.17.2 \
  --index-url https://download.pytorch.org/whl/cpu --quiet

echo "==== [3/9] AudioCraft (sem deps) ===="
$PIP install git+https://github.com/facebookresearch/audiocraft.git --no-deps --quiet

echo "==== [4/9] Transformers stack (pinado) ===="
$PIP install \
  "transformers==4.40.2" \
  "tokenizers==0.19.1" \
  "huggingface_hub==0.23.4" \
  "safetensors" "regex" "requests" "tqdm" "filelock" "packaging" "pyyaml" \
  --no-deps --quiet

echo "==== [5/9] AudioCraft runtime core ===="
$PIP install \
  einops encodec \
  "omegaconf==2.3.0" "hydra-core==1.3.2" "antlr4-python3-runtime==4.9.3" \
  flashy julius soundfile protobuf "sentencepiece" num2words \
  --quiet

echo "==== [6/9] av (wheel pré-compilada) ===="
$PIP install av --quiet

echo "==== [7/9] spacy 3.7.6 (compilado contra numpy 1.26.4) ===="
$PIP install "spacy==3.7.6" --quiet

echo "==== [8/9] librosa (sem numba) ===="
$PIP install librosa --no-deps --quiet
$PIP install lazy_loader decorator soxr pooch \
  "scikit-learn" "scipy" --quiet

echo "==== [9/9] Stubs: xformers ===="
mkdir -p .venv/lib/python3.12/site-packages/xformers/ops
cat > .venv/lib/python3.12/site-packages/xformers/__init__.py << 'PYEOF'
"""Stub xformers — CPU fallback, sem compilação nativa."""
PYEOF
cat > .venv/lib/python3.12/site-packages/xformers/ops/__init__.py << 'PYEOF'
"""Stub xformers.ops — fallback para atenção padrão do torch."""
import torch

def memory_efficient_attention(q, k, v, attn_bias=None, scale=None, **kwargs):
    s = scale or (q.shape[-1] ** -0.5)
    attn = torch.einsum("bhid,bhjd->bhij", q, k) * s
    if attn_bias is not None:
        attn = attn + attn_bias
    attn = torch.softmax(attn, dim=-1)
    return torch.einsum("bhij,bhjd->bhid", attn, v)

class LowerTriangularMask:
    def __init__(self): pass
PYEOF

echo ""
echo "==== Testando imports ===="
.venv/bin/python - << 'PYEOF'
import warnings; warnings.filterwarnings('ignore')
import numpy as np; print(f"  numpy  : {np.__version__}")
import torch;       print(f"  torch  : {torch.__version__}")
import torchaudio;  print(f"  torchaudio OK")
from audiocraft.models import MusicGen; print(f"  MusicGen OK")
d = "cuda" if torch.cuda.is_available() else "cpu"
print(f"  device : {d}")
print("\n✅ Ambiente pronto!")
PYEOF
