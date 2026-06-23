"""
Script de Teste — MusicGen Melody
Gera uma nova música a partir de um arquivo de áudio de referência (melodia)
combinado com um prompt de texto.
"""

import torch
import torchaudio
from audiocraft.models import MusicGen

# =============================================================================
# VARIÁVEIS DE CONFIGURAÇÃO — edite aqui antes de rodar
# =============================================================================
PROMPT_TEXTO   = "a calm and ethereal piano melody, cinematic, orchestral strings"
DURACAO_SEG    = 15                          # duração da música gerada (segundos)
ARQUIVO_ENTRADA = "input/piano_original.wav" # caminho do áudio de referência
ARQUIVO_SAIDA   = "output/musica_gerada.wav" # caminho do arquivo de saída
# =============================================================================

def main():
    # Seleciona o dispositivo disponível (GPU com CUDA ou CPU)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Dispositivo em uso: {device}")

    # --- 1. Carrega o modelo ---
    print("Carregando o modelo facebook/musicgen-melody...")
    model = MusicGen.get_pretrained("facebook/musicgen-melody")
    model.set_generation_params(duration=DURACAO_SEG)

    # --- 2. Lê o arquivo de áudio de entrada ---
    print(f"Lendo o arquivo de entrada: {ARQUIVO_ENTRADA}")
    melody_waveform, sample_rate = torchaudio.load(ARQUIVO_ENTRADA)

    # Adiciona dimensão de batch: shape (1, canais, amostras)
    melody_waveform = melody_waveform.unsqueeze(0)

    # --- 3. Gera a música com condicionamento de melodia ---
    print("Gerando música... (pode levar alguns minutos)")
    output = model.generate_with_chroma(
        descriptions=[PROMPT_TEXTO],
        melody_wavs=melody_waveform,
        melody_sample_rate=sample_rate,
        progress=True,
    )

    # --- 4. Salva o áudio gerado ---
    # output shape: (batch, canais, amostras) — pega o primeiro item do batch
    audio_tensor = output[0].cpu()

    # torchaudio.save espera (canais, amostras)
    torchaudio.save(
        ARQUIVO_SAIDA,
        audio_tensor,
        sample_rate=model.sample_rate,
    )
    print(f"Áudio salvo em: {ARQUIVO_SAIDA}")


if __name__ == "__main__":
    main()
