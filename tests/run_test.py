"""
run_test.py — Execução única de teste com o arquivo sorteado.

CORREÇÕES v2:
- Input cropado para a mesma duração do output (melhora o alinhamento do croma)
- Prompt mais neutro para não dominar o condicionamento melódico
- Trecho do meio da música selecionado para pegar a parte mais desenvolvida

Arquivo de entrada : piano eqinox/241- A Justiça divina.mp3
Duração gerada     : 15 segundos
Saída              : output/241_orquestra_v2.mp3
"""

import torch
import torchaudio
import subprocess
from pathlib import Path
from audiocraft.models import MusicGen

# ── Configuração ──────────────────────────────────────────────────────────────
ARQUIVO_ENTRADA = "piano eqinox/241- A Justiça divina.mp3"
ARQUIVO_SAIDA   = "output/241_orquestra_v2.mp3"

# Prompt neutro: indica o instrumento-alvo mas não sobrecarrega o condicionamento
# Quanto menos específico, mais o modelo segue a melodia do input
PROMPT_TEXTO = "orchestral strings and piano, smooth and melodic"

# Duração gerada — quanto menor, mais fiel à melodia original
# (o croma do input será alinhado à mesma janela de tempo)
DURACAO_SEG = 15

# Segundo do input a partir do qual o trecho será recortado
# (pula a intro e pega a parte mais desenvolvida da música)
INICIO_CROP_SEG = 30
# ─────────────────────────────────────────────────────────────────────────────


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"\n🎻 Dispositivo       : {device}")
    print(f"📂 Entrada           : {ARQUIVO_ENTRADA}")
    print(f"💾 Saída             : {ARQUIVO_SAIDA}")
    print(f"⏱  Duração gerada    : {DURACAO_SEG}s")
    print(f"✂️  Início do crop    : {INICIO_CROP_SEG}s\n")

    Path(ARQUIVO_SAIDA).parent.mkdir(parents=True, exist_ok=True)

    # ── Carrega modelo ────────────────────────────────────────────────────────
    print("⏳ Carregando modelo facebook/musicgen-melody...")
    model = MusicGen.get_pretrained("facebook/musicgen-melody")
    model.set_generation_params(duration=DURACAO_SEG)
    print("✅ Modelo carregado.\n")

    # ── Lê e cropa o áudio de entrada ─────────────────────────────────────────
    print("🎹 Lendo arquivo de entrada...")
    melody_waveform, sample_rate = torchaudio.load(ARQUIVO_ENTRADA)
    dur_total = melody_waveform.shape[-1] / sample_rate
    print(f"   Duração total : {dur_total:.1f}s  |  Sample rate: {sample_rate} Hz")

    # Recorta exatamente DURACAO_SEG segundos a partir de INICIO_CROP_SEG
    inicio_amostras = int(INICIO_CROP_SEG * sample_rate)
    fim_amostras    = int((INICIO_CROP_SEG + DURACAO_SEG) * sample_rate)
    melody_crop     = melody_waveform[:, inicio_amostras:fim_amostras]
    dur_crop        = melody_crop.shape[-1] / sample_rate
    print(f"   Trecho usado  : {INICIO_CROP_SEG}s → {INICIO_CROP_SEG + dur_crop:.1f}s ({dur_crop:.1f}s)\n")

    # Adiciona dimensão de batch: (1, canais, amostras)
    melody_crop = melody_crop.unsqueeze(0)

    # ── Geração ───────────────────────────────────────────────────────────────
    print("🎼 Gerando... (o model produz saída condicionada na melodia do trecho)\n")
    output = model.generate_with_chroma(
        descriptions=[PROMPT_TEXTO],
        melody_wavs=melody_crop,
        melody_sample_rate=sample_rate,
        progress=True,
    )

    # ── Salva WAV e converte para MP3 ─────────────────────────────────────────
    wav_temp    = Path(ARQUIVO_SAIDA).with_suffix(".wav")
    audio_tensor = output[0].cpu()

    if audio_tensor.shape[0] == 1:
        audio_tensor = audio_tensor.repeat(2, 1)  # mono → estéreo

    torchaudio.save(str(wav_temp), audio_tensor, sample_rate=model.sample_rate)
    print(f"\n✅ WAV salvo: {wav_temp}")

    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(wav_temp),
         "-codec:a", "libmp3lame", "-qscale:a", "2", ARQUIVO_SAIDA],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        wav_temp.unlink()
        print(f"🎵 MP3 final: {ARQUIVO_SAIDA}\n")
    else:
        print(f"⚠️  ffmpeg erro — WAV disponível em: {wav_temp}\n{result.stderr}")


if __name__ == "__main__":
    main()
