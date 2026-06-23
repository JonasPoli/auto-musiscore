#!/usr/bin/env bash
# install_v2.sh — instalação cirúrgica para AudioCraft em Intel Mac / Python 3.12
set -e

# Sincroniza o diretório de trabalho com a raiz do projeto
cd "$(dirname "$0")/.."

PIP=".venv/bin/pip"
PYTHON=".venv/bin/python"
SITE=".venv/lib/python3.12/site-packages"

echo "numpy==1.26.4" > .numpy_pin.txt

# ── 1. numpy travado PRIMEIRO ─────────────────────────────────────────────────
echo "[1/8] numpy 1.26.4 (pin)"
$PIP install "numpy==1.26.4" -c .numpy_pin.txt --quiet

# ── 2. PyTorch (CPU, Intel Mac) ───────────────────────────────────────────────
echo "[2/8] PyTorch 2.2.2 CPU"
$PIP install torch==2.2.2 torchaudio==2.2.2 \
    --index-url https://download.pytorch.org/whl/cpu \
    -c .numpy_pin.txt --quiet

# ── 3. AudioCraft (sem deps) ──────────────────────────────────────────────────
echo "[3/8] AudioCraft (no-deps)"
$PIP install git+https://github.com/facebookresearch/audiocraft.git \
    --no-deps -c .numpy_pin.txt --quiet

# ── 4. Patchar audiocraft: tornar spacy e xformers opcionais ─────────────────
echo "[4/8] Patchando audiocraft para deps opcionais"
$PYTHON - << 'PYEOF'
import re, pathlib

SITE = pathlib.Path(".venv/lib/python3.12/site-packages")

patches = [
    # transformer.py: xformers → opcional
    (
        SITE / "audiocraft/modules/transformer.py",
        r"^from xformers import ops$",
        "try:\n    from xformers import ops\nexcept ImportError:\n    ops = None",
    ),
    # conditioners.py: spacy → opcional
    (
        SITE / "audiocraft/modules/conditioners.py",
        r"^import spacy$",
        "try:\n    import spacy\nexcept ImportError:\n    spacy = None",
    ),
]

for path, pattern, replacement in patches:
    if not path.exists():
        print(f"  SKIP (não encontrado): {path.name}")
        continue
    original = path.read_text()
    patched = re.sub(pattern, replacement, original, flags=re.MULTILINE)
    if patched != original:
        path.write_text(patched)
        print(f"  PATCHED: {path.name}")
    else:
        print(f"  JÁ OK (padrão não encontrado): {path.name}")
PYEOF

# ── 5. Transformers stack (pinado) ────────────────────────────────────────────
echo "[5/8] Transformers 4.40.2 + dependências"
$PIP install \
    "transformers==4.40.2" \
    "tokenizers==0.19.1" \
    "huggingface-hub==0.23.4" \
    safetensors regex requests tqdm filelock packaging pyyaml \
    --no-deps -c .numpy_pin.txt --quiet
# charset-normalizer e urllib3 (deps de requests)
$PIP install charset-normalizer urllib3 idna certifi \
    -c .numpy_pin.txt --quiet

# ── 6. Deps core do AudioCraft ────────────────────────────────────────────────
echo "[6/8] AudioCraft runtime deps"
$PIP install \
    einops encodec \
    "omegaconf==2.3.0" \
    "hydra-core==1.3.2" \
    "antlr4-python3-runtime==4.9.3" \
    flashy julius soundfile \
    protobuf sentencepiece num2words \
    av \
    -c .numpy_pin.txt --quiet

# ── 7. librosa (sem numba / sem scikit-learn) ─────────────────────────────────
echo "[7/8] librosa (minimal, sem numba)"
# scipy pinado na 1.x para garantir compatibilidade com numpy 1.26
$PIP install "scipy==1.13.1" -c .numpy_pin.txt --quiet
$PIP install librosa --no-deps -c .numpy_pin.txt --quiet
$PIP install lazy_loader decorator audioread pooch "msgpack>=1.0" soxr \
    -c .numpy_pin.txt --quiet

# ── 8. Stub xformers (fallback para atenção padrão) ──────────────────────────
echo "[8/8] Criando stub xformers"
mkdir -p "$SITE/xformers/ops"
cat > "$SITE/xformers/__init__.py" << 'PYEOF'
"""Stub xformers — CPU fallback sem compilação nativa."""
PYEOF
cat > "$SITE/xformers/ops/__init__.py" << 'PYEOF'
"""Stub xformers.ops — usa atenção padrão do PyTorch."""
import torch

def memory_efficient_attention(q, k, v, attn_bias=None, scale=None, **kw):
    s = scale or (q.shape[-1] ** -0.5)
    a = torch.einsum("bhid,bhjd->bhij", q, k) * s
    if attn_bias is not None:
        a = a + attn_bias
    a = torch.softmax(a, dim=-1)
    return torch.einsum("bhij,bhjd->bhid", a, v)

class LowerTriangularMask:
    def __init__(self): pass
PYEOF

# ── Verificação final ─────────────────────────────────────────────────────────
echo ""
echo "════ Testando imports ════"
$PYTHON - << 'PYEOF'
import warnings; warnings.filterwarnings("ignore")
import numpy as np;  print(f"  numpy      : {np.__version__}")
import torch;        print(f"  torch      : {torch.__version__}")
import torchaudio;   print(f"  torchaudio : OK")
from audiocraft.models import MusicGen
print(f"  MusicGen   : OK")
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"  device     : {device}")
print()
print("✅ Ambiente pronto!")
PYEOF
