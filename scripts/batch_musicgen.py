"""
Script de Lote — MusicGen Melody
Processa todos os arquivos de áudio de uma pasta de origem e salva
os resultados em uma pasta de destino.
"""

import os
import torch
import torchaudio
from pathlib import Path
from audiocraft.models import MusicGen

# =============================================================================
# VARIÁVEIS DE CONFIGURAÇÃO — edite aqui antes de rodar
# =============================================================================
PASTA_ENTRADA   = "input"                        # pasta com os 500 arquivos originais
PASTA_SAIDA     = "output"                       # pasta onde os arquivos gerados serão salvos
PROMPT_TEXTO    = "a calm and ethereal piano melody, cinematic, orchestral strings"
DURACAO_SEG     = 15                             # duração de cada geração (segundos)
EXTENSOES_VALIDAS = {".wav", ".mp3", ".flac", ".ogg", ".aiff"}
# =============================================================================


def processar_arquivo(model, caminho_entrada: Path, caminho_saida: Path) -> None:
    """Gera e salva um arquivo de música usando o arquivo de entrada como melodia."""
    # Lê o áudio de referência
    melody_waveform, sample_rate = torchaudio.load(str(caminho_entrada))
    melody_waveform = melody_waveform.unsqueeze(0)  # adiciona dimensão de batch

    # Geração com condicionamento de melodia
    output = model.generate_with_chroma(
        descriptions=[PROMPT_TEXTO],
        melody_wavs=melody_waveform,
        melody_sample_rate=sample_rate,
        progress=False,  # desliga a barra individual para manter o log limpo
    )

    # Salva o resultado mantendo o mesmo nome do arquivo original
    audio_tensor = output[0].cpu()
    torchaudio.save(
        str(caminho_saida),
        audio_tensor,
        sample_rate=model.sample_rate,
    )


def main():
    # --- Configuração de device ---
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Dispositivo em uso: {device}\n")

    # --- Garante que a pasta de saída existe ---
    Path(PASTA_SAIDA).mkdir(parents=True, exist_ok=True)

    # --- Carrega o modelo uma única vez antes do loop ---
    print("Carregando o modelo facebook/musicgen-melody...")
    model = MusicGen.get_pretrained("facebook/musicgen-melody")
    model.set_generation_params(duration=DURACAO_SEG)
    print("Modelo carregado com sucesso.\n")

    # --- Coleta os arquivos de áudio na pasta de entrada ---
    arquivos = sorted(
        f for f in Path(PASTA_ENTRADA).iterdir()
        if f.is_file() and f.suffix.lower() in EXTENSOES_VALIDAS
    )

    total = len(arquivos)
    if total == 0:
        print(f"Nenhum arquivo de áudio encontrado em '{PASTA_ENTRADA}'.")
        return

    print(f"Total de arquivos encontrados: {total}\n")
    print("=" * 60)

    # --- Loop principal de processamento ---
    concluidos = 0
    erros = 0

    for indice, caminho_entrada in enumerate(arquivos, start=1):
        # Define o caminho de saída com extensão .wav
        caminho_saida = Path(PASTA_SAIDA) / (caminho_entrada.stem + "_gerado.wav")

        print(f"[{indice}/{total}] Processando: {caminho_entrada.name}")

        try:
            processar_arquivo(model, caminho_entrada, caminho_saida)
            print(f"        ✓ Salvo em: {caminho_saida.name}")
            concluidos += 1

        except Exception as erro:
            # Captura qualquer exceção sem interromper o batch inteiro
            print(f"        ✗ ERRO em '{caminho_entrada.name}': {erro}")
            erros += 1

    # --- Resumo final ---
    print("\n" + "=" * 60)
    print(f"Processamento concluído.")
    print(f"  ✓ Arquivos gerados com sucesso : {concluidos}")
    print(f"  ✗ Arquivos com erro            : {erros}")
    print(f"  Total processados              : {indice}")


if __name__ == "__main__":
    main()
