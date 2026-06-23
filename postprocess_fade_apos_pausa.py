#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pós-processamento para suavizar ataques de cordas após pausas.

Uso para 1 arquivo:
  python3 postprocess_fade_apos_pausa.py --input "arquivo.mp3" --output "saida"

Uso em lote:
  python3 postprocess_fade_apos_pausa.py --input "output_strings_16part" --output "output_strings_16part_suave"

Requisitos:
  pip install pydub numpy
  brew install ffmpeg
"""

import argparse
import os
import glob
import math
from typing import List, Tuple

import numpy as np
from pydub import AudioSegment
from pydub.silence import detect_silence


AUDIO_EXTS = (".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg")


def db_to_gain(db: float) -> float:
    return 10 ** (db / 20.0)


def resolve_audio_files(input_path: str, recursive: bool = False) -> List[str]:
    if os.path.isfile(input_path):
        return [input_path]

    if not os.path.isdir(input_path):
        raise FileNotFoundError(f"Entrada não encontrada: {input_path}")

    pattern = "**/*" if recursive else "*"
    files = []
    for path in glob.glob(os.path.join(input_path, pattern), recursive=recursive):
        if os.path.isfile(path) and path.lower().endswith(AUDIO_EXTS):
            files.append(path)

    return sorted(files)


def make_output_path(src_path: str, input_root: str, output_root: str, suffix: str) -> str:
    base, ext = os.path.splitext(os.path.basename(src_path))

    if os.path.isfile(input_root):
        os.makedirs(output_root, exist_ok=True)
        return os.path.join(output_root, f"{base}{suffix}{ext}")

    rel_dir = os.path.relpath(os.path.dirname(src_path), input_root)
    out_dir = output_root if rel_dir == "." else os.path.join(output_root, rel_dir)
    os.makedirs(out_dir, exist_ok=True)
    return os.path.join(out_dir, f"{base}{suffix}{ext}")


def apply_gain_envelope(samples: np.ndarray, channels: int, sr: int, total_ms: int,
                        start_ms: float, end_ms: float, envelope: np.ndarray) -> None:
    start_sample = int(max(0, start_ms) * sr / 1000)
    end_sample = int(min(total_ms, end_ms) * sr / 1000)

    if end_sample <= start_sample:
        return

    length = end_sample - start_sample

    if len(envelope) != length:
        x_old = np.linspace(0, 1, len(envelope))
        x_new = np.linspace(0, 1, length)
        envelope = np.interp(x_new, x_old, envelope)

    if channels > 1:
        samples[start_sample:end_sample, :] *= envelope[:, None]
    else:
        samples[start_sample:end_sample] *= envelope


def process_audio_file(
    input_path: str,
    output_path: str,
    fade_ms: int = 900,
    lookback_ms: int = 200,
    min_silence_ms: int = 300,
    silence_thresh_dbfs: float | None = None,
    silence_offset_db: float = -24.0,
    floor_db: float = -36.0,
    curve: float = 1.8,
    tail_fade_ms: int = 100,
    tail_reduction_db: float = -2.8,
    ignore_end_ms: int = 1800,
    seek_step_ms: int = 5,
    include_start: bool = False,
    gain_db: float = -2.0,
    dry_run: bool = False,
) -> Tuple[List[Tuple[int, int]], float]:
    audio = AudioSegment.from_file(input_path)

    # Mantém sample rate e canais, mas converte para 16-bit para o processamento ser estável.
    audio = audio.set_sample_width(2)

    total_ms = len(audio)

    if silence_thresh_dbfs is None:
        # Regra genérica: usa o volume médio do próprio arquivo como referência.
        # Ex.: arquivo -13 dBFS + offset -24 = silêncio abaixo de -37 dBFS.
        silence_thresh_dbfs = audio.dBFS + silence_offset_db

    silences = detect_silence(
        audio,
        min_silence_len=min_silence_ms,
        silence_thresh=silence_thresh_dbfs,
        seek_step=seek_step_ms,
    )

    # Pausas internas: ignora silêncio final longo e ignora trechos muito perto do fim.
    pauses = []
    for start_ms, end_ms in silences:
        if end_ms >= total_ms - ignore_end_ms:
            continue
        if end_ms <= 0:
            continue
        pauses.append((start_ms, end_ms))

    if include_start:
        nonsilent = []
        # Detecta primeira entrada audível: o fim do primeiro silêncio inicial.
        for start_ms, end_ms in silences:
            if start_ms == 0 and end_ms < total_ms - ignore_end_ms:
                pauses.insert(0, (start_ms, end_ms))
                break

    if dry_run:
        return pauses, silence_thresh_dbfs

    raw = np.array(audio.get_array_of_samples()).astype(np.float32)
    channels = audio.channels
    sr = audio.frame_rate

    if channels > 1:
        raw = raw.reshape((-1, channels))

    floor_gain = db_to_gain(floor_db)
    tail_gain = db_to_gain(tail_reduction_db)

    # Envelope de entrada: começa bem baixo e cresce como arco de violino,
    # sem ataque seco. A curva > 1 segura mais o começo e abre depois.
    fade_len_samples = max(2, int(fade_ms * sr / 1000))
    t = np.linspace(0, 1, fade_len_samples, endpoint=True)
    shaped = t ** curve
    smoothstep = shaped * shaped * (3 - 2 * shaped)
    fade_in_env = floor_gain + (1.0 - floor_gain) * smoothstep

    # Envelope de final de frase antes da pausa, opcional e discreto.
    if tail_fade_ms > 0:
        tail_len_samples = max(2, int(tail_fade_ms * sr / 1000))
        tt = np.linspace(0, 1, tail_len_samples, endpoint=True)
        tail_smooth = tt * tt * (3 - 2 * tt)
        tail_env = 1.0 + (tail_gain - 1.0) * tail_smooth
    else:
        tail_env = None

    for silence_start_ms, silence_end_ms in pauses:
        # Suaviza discretamente o fim antes do silêncio.
        if tail_env is not None and silence_start_ms - tail_fade_ms > 0:
            apply_gain_envelope(
                raw,
                channels,
                sr,
                total_ms,
                silence_start_ms - tail_fade_ms,
                silence_start_ms,
                tail_env,
            )

        # Suaviza a retomada após o silêncio, recuando lookback_ms para cobrir o ataque da nota.
        fade_start_ms = max(silence_start_ms, silence_end_ms - lookback_ms)
        apply_gain_envelope(
            raw,
            channels,
            sr,
            total_ms,
            fade_start_ms,
            fade_start_ms + fade_ms,
            fade_in_env,
        )

    max_abs = 32767
    processed = np.clip(raw, -max_abs, max_abs).astype(np.int16)

    if channels > 1:
        out_bytes = processed.reshape(-1).tobytes()
    else:
        out_bytes = processed.tobytes()

    out_audio = AudioSegment(
        data=out_bytes,
        sample_width=2,
        frame_rate=sr,
        channels=channels,
    )

    if gain_db != 0.0:
        out_audio = out_audio + gain_db

    ext = os.path.splitext(output_path)[1].lower().replace(".", "")
    if ext == "":
        ext = "mp3"

    export_kwargs = {}
    if ext == "mp3":
        export_kwargs["bitrate"] = "192k"

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    out_audio.export(output_path, format=ext, **export_kwargs)

    return pauses, silence_thresh_dbfs


def main():
    parser = argparse.ArgumentParser(
        description="Suaviza ataques secos de cordas após pausas em arquivos renderizados."
    )

    parser.add_argument("--input", required=True, help="Arquivo de áudio ou pasta com áudios.")
    parser.add_argument("--output", required=True, help="Pasta de saída.")
    parser.add_argument("--recursive", action="store_true", help="Processa subpastas também.")

    parser.add_argument("--fade-ms", type=int, default=900,
                        help="Duração do fade-in após a pausa. Padrão: 900ms.")
    parser.add_argument("--lookback-ms", type=int, default=200,
                        help="Recuo em milissegundos para iniciar o fade-in dentro do silêncio. Padrão: 200ms.")
    parser.add_argument("--min-silence-ms", type=int, default=300,
                        help="Tamanho mínimo da pausa para aplicar o efeito. Padrão: 300ms.")
    parser.add_argument("--silence-thresh-dbfs", type=float, default=None,
                        help="Limiar absoluto de silêncio em dBFS. Se omitido, calcula automaticamente.")
    parser.add_argument("--silence-offset-db", type=float, default=-24.0,
                        help="Offset relativo ao dBFS médio do arquivo. Padrão: -24.")
    parser.add_argument("--floor-db", type=float, default=-36.0,
                        help="Volume inicial do fade-in em dB. Mais negativo = ataque mais macio. Padrão: -36.")
    parser.add_argument("--curve", type=float, default=1.8,
                        help="Curva do fade. 1.0 linear; 1.6-2.2 mais suave. Padrão: 1.8.")
    parser.add_argument("--tail-fade-ms", type=int, default=100,
                        help="Suavização discreta antes da pausa. Use 0 para desligar. Padrão: 100ms.")
    parser.add_argument("--tail-reduction-db", type=float, default=-2.8,
                        help="Redução no fim da frase antes da pausa. Padrão: -2.8dB.")
    parser.add_argument("--ignore-end-ms", type=int, default=1800,
                        help="Ignora pausas muito próximas do final. Padrão: 1800ms.")
    parser.add_argument("--suffix", default="_suave",
                        help="Sufixo dos arquivos processados. Padrão: _suave.")
    parser.add_argument("--gain-db", type=float, default=-2.0,
                        help="Ajuste de ganho final em dB (para evitar clipping). Padrão: -2.0")
    parser.add_argument("--include-start", action="store_true",
                        help="Também aplica fade na primeira entrada do áudio.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Só mostra as pausas detectadas, sem gerar arquivos.")

    args = parser.parse_args()

    files = resolve_audio_files(args.input, recursive=args.recursive)

    if not files:
        print("Nenhum arquivo de áudio encontrado.")
        return

    print("════════════════════════════════════════════════════════════")
    print(" Pós-processamento: fade-in após pausas")
    print(f" Arquivos encontrados: {len(files)}")
    print(f" Fade após pausa: {args.fade_ms}ms (lookback: {args.lookback_ms}ms)")
    print(f" Pausa mínima: {args.min_silence_ms}ms")
    print(f" Piso do fade: {args.floor_db}dB")
    print("════════════════════════════════════════════════════════════")

    total_ok = 0
    total_fail = 0

    for idx, src in enumerate(files, 1):
        try:
            dst = make_output_path(src, args.input, args.output, args.suffix)

            pauses, threshold = process_audio_file(
                input_path=src,
                output_path=dst,
                fade_ms=args.fade_ms,
                lookback_ms=args.lookback_ms,
                min_silence_ms=args.min_silence_ms,
                silence_thresh_dbfs=args.silence_thresh_dbfs,
                silence_offset_db=args.silence_offset_db,
                floor_db=args.floor_db,
                curve=args.curve,
                tail_fade_ms=args.tail_fade_ms,
                tail_reduction_db=args.tail_reduction_db,
                ignore_end_ms=args.ignore_end_ms,
                include_start=args.include_start,
                gain_db=args.gain_db,
                dry_run=args.dry_run,
            )

            pause_desc = ", ".join([f"{e/1000:.2f}s" for _, e in pauses]) or "nenhuma"

            if args.dry_run:
                print(f"[{idx}/{len(files)}] {os.path.basename(src)} | threshold {threshold:.1f} dBFS | retomadas: {pause_desc}")
            else:
                print(f"[{idx}/{len(files)}] ✓ {os.path.basename(src)} | retomadas: {pause_desc}")

            total_ok += 1

        except Exception as exc:
            print(f"[{idx}/{len(files)}] ✗ {os.path.basename(src)} | erro: {exc}")
            total_fail += 1

    print("════════════════════════════════════════════════════════════")
    print(f"Concluído. OK: {total_ok} | Falhas: {total_fail}")


if __name__ == "__main__":
    main()
