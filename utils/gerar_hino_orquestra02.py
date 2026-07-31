#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
utils/gerar_hino_orquestra02.py
================================
Orquestração de hino completo no estilo "Orquestra 02":
intercala frases usando dois agrupamentos:

  Agrupamento 1: STRINGS + BRASS + PALETAS + SOPROS (nicho puro)
  Agrupamento 2: COMBINATIONS_ORQUESTRA_02 (mix de orquestra + coral + Rock Organ em 1 trilha)

Padrão de frases:
  F1: Agrupamento 1  (ex: um quarteto de cordas)
  F2: Agrupamento 2  (ex: Sinfônica Clássica + Coral + Rock Organ)
  F3: Agrupamento 1  (ex: octeto de metais)
  F4: Agrupamento 2  (ex: Tutti Equilibrada + Coral + Rock Organ)
  ...
  FN: Agrupamento 2  (ex: Épica Sinfônica + Coral + Rock Organ)  ← SEMPRE termina com Agrupamento 2

Saída: output/orquestra_nicho/orquestra02/hino_XXX.mp3 (+ _partes/)
"""

import sys
import os
import subprocess
import shutil
import argparse
import random
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT / 'utils'))
sys.path.insert(0, str(ROOT / 'scripts'))

import mido
from gerar_testes_timbre import detect_phrases
from gerar_hino_nicho_completo import (
    get_tempo, ticks_to_sec, trim_mp3, make_silence_mp3, obter_duracao_mp3,
    render_phrase_nicho, get_progressive_sizes,
    MSCORE_BIN, SILENCE_THRESHOLD_DB, DECAY_TAIL_S,
)
from gerar_bibliotecas_nicho import (
    COMBINATIONS_STRINGS, COMBINATIONS_BRASS, COMBINATIONS_PALETAS, COMBINATIONS_SOPROS,
    build_combo_midi, extract_phrase_notes,
)
from midi_humanize import _MUSE_LOOKUP
from testar_orquestra02_mix import COMBINATIONS_ORQUESTRA_02

# ── Agrupamentos ────────────────────────────────────────────────────────────
AGRUPAMENTO_1 = COMBINATIONS_STRINGS + COMBINATIONS_BRASS + COMBINATIONS_PALETAS + COMBINATIONS_SOPROS
AGRUPAMENTO_2 = COMBINATIONS_ORQUESTRA_02


def select_orquestra02_combos(n_phrases: int, seed: int = None) -> list:
    """
    Seleciona combos alternando entre Agrupamento 1 e Agrupamento 2 (Orquestra 02).
    - Frases ímpares (1, 3, 5...): Agrupamento 1 (nicho puro)
    - Frases pares (2, 4, 6...): Agrupamento 2 (orquestra + coral + Rock Organ)
    - Última frase SEMPRE é Agrupamento 2
    """
    if seed is not None:
        random.seed(seed)

    sizes = get_progressive_sizes(n_phrases)

    if n_phrases == 1:
        config = _pick_by_size(AGRUPAMENTO_2, sizes[0])
        return [("AG2", config)]

    selected = []
    for i in range(n_phrases):
        target_size = sizes[i]
        if i == n_phrases - 1:
            # Última frase: SEMPRE Agrupamento 2
            config = _pick_by_size(AGRUPAMENTO_2, target_size)
            selected.append(("AG2", config))
        elif i % 2 == 0:
            # Frases índice 0, 2, 4... → Agrupamento 1
            config = _pick_by_size(AGRUPAMENTO_1, target_size)
            selected.append(("AG1", config))
        else:
            # Frases índice 1, 3, 5... → Agrupamento 2
            config = _pick_by_size(AGRUPAMENTO_2, target_size)
            selected.append(("AG2", config))

    return selected


def _pick_by_size(pool: list, target_size: int) -> dict:
    """Seleciona um combo aleatório do pool que tenha o tamanho mais próximo."""
    by_size = [c for c in pool if c["size"] == target_size]
    if by_size:
        return random.choice(by_size)
    return random.choice(pool)


def escrever_explicacao_md(partes_dir: Path, selected: list, midi_name: str):
    """Gera o arquivo explicação.md detalhando cada frase."""
    md_path = partes_dir / "explicação.md"
    lines = [
        f"# 🎹 Explicação dos Timbres e Dinâmicas — {midi_name} (Orquestra 02)",
        "",
        "Este arquivo detalha as especificações técnicas dos arranjos intercalados.",
        "",
        "## Padrão de Alternância",
        "- **Agrupamento 1**: Instrumentos de nicho puro (Cordas, Metais, Palhetas ou Sopros)",
        "- **Agrupamento 2**: Orquestra mista + Coral 50% + Rock Organ (SATB em trilha única) 12",
        "- A última frase é SEMPRE Agrupamento 2.",
        "",
        "---",
        "",
        "## 🎧 Regras de Humanização Acústica",
        "",
        "1. **Timing Offset**: **0 ms** para evitar atraso.",
        "2. **Dinâmica Pós-Pausa**: Velocity = 10, CC11 ramp 40→100 em 225 ms.",
        "3. **Fade-In Hermitiano**: 200 ms Smoothstep.",
        "4. **Encurtamento Pré-Pausa**: 30% da duração original.",
        "",
        "---",
        "",
        "## 🎼 Detalhamento dos Instrumentos por Frase",
        ""
    ]

    for f_idx, (grupo, config) in enumerate(selected):
        grupo_label = "Nicho Puro" if grupo == "AG1" else "Orquestra 02 Mix"
        lines.append(f"### 📯 Frase F{f_idx+1:02d} — [{grupo_label}] {config['name']} ({config['size']} partes)")
        lines.append("")
        for track in config["tracks"]:
            vname = track["voice"]
            iname = track["instrument_name"]
            vol = track["vol"]
            prog = track["program"]
            pan = track["pan"]
            octave = track["octave"]

            muse_info = _MUSE_LOOKUP.get(track["instrument_id"])
            if isinstance(muse_info, list):
                muse_info = muse_info[0]

            if muse_info:
                muse_str = f"MuseSounds (UID: `{muse_info['uid']}`, Pack: `{muse_info['pack']}`)"
            else:
                muse_str = "MS Basic (Fallback SoundFont)"

            octave_str = f", Oitava: `{octave:+d}`" if octave != 0 else ""
            lines.append(f"* **{vname}**: {iname} (Vol: `{vol}`, Pan: `{pan}`, Prog: `{prog}`{octave_str}) ➔ {muse_str}")
        lines.append("")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  [OK] Explicação gerada em: {md_path.name}")


def gerar_hino_orquestra02(midi_path: str, output_mp3: str, bpm_target: float = 60.0, speed: float = None, overwrite: bool = False) -> bool:
    """Gera um hino completo no estilo Orquestra 02 (intercalação AG1/AG2 com Coral e Rock Organ)."""
    out_path = Path(output_mp3)
    if not overwrite and out_path.exists() and out_path.stat().st_size > 1000:
        print(f"  [PULADO] {out_path.name} já existe ({out_path.stat().st_size//1024} KB)")
        return True

    mid      = mido.MidiFile(midi_path)
    tempo    = get_tempo(mid)
    bpm_orig = 60_000_000 / tempo
    tpb      = mid.ticks_per_beat

    if bpm_target is None:
        bpm_target = bpm_orig * speed if speed else bpm_orig
    if speed is None:
        speed = bpm_target / bpm_orig
    tempo_new = int(60_000_000 / bpm_target)

    print(f'\n{"="*60}')
    print(f'  HINO COMPLETO (ORQUESTRA 02): {Path(midi_path).name}')
    print(f'  BPM: {bpm_orig:.0f} -> {bpm_target:.0f}  (speed={speed:.3f})')
    print(f'{"="*60}')

    phrases = detect_phrases(mid, tempo, min_phrase_seconds=6.0, silence_beats=0.4)
    if not phrases:
        print('ERRO: nenhuma frase detectada.')
        return False

    print(f'\nFrases ({len(phrases)}):')
    for i, (s, e) in enumerate(phrases):
        dur_tgt = ticks_to_sec(e - s, tempo_new, tpb) / speed
        gap_tgt = ticks_to_sec(phrases[i+1][0] - e, tempo_new, tpb) if i+1 < len(phrases) else 0
        print(f'  Frase {i+1}: {dur_tgt:.1f}s  gap->{gap_tgt:.1f}s')

    # Semente determinística baseada no ID do hino
    match = re.search(r'(\d+)', Path(midi_path).name)
    hino_id = int(match.group(1)) if match else 42
    seed_val = hino_id + 8888  # Offset único para Orquestra 02

    selected = select_orquestra02_combos(len(phrases), seed=seed_val)
    print(f'\nProgressão dos Arranjos (ORQUESTRA 02):')
    for i, (grupo, config) in enumerate(selected):
        grupo_tag = "AG1-Nicho" if grupo == "AG1" else "AG2-Orq02"
        print(f'  F{i+1}: [{grupo_tag}] {config["size"]:2d} instr | {config["name"]}')

    out_path = Path(output_mp3)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    partes_dir = out_path.parent / (out_path.stem + '_partes')
    shutil.rmtree(partes_dir, ignore_errors=True)
    partes_dir.mkdir(parents=True, exist_ok=True)
    escrever_explicacao_md(partes_dir, selected, Path(midi_path).name)

    work_dir = Path(f'/tmp/_tmp_hino_orq02_{os.getpid()}')
    shutil.rmtree(work_dir, ignore_errors=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    raw_results = []
    for i, (phrase, (grupo, config)) in enumerate(zip(phrases, selected), start=1):
        mp3_raw = render_phrase_nicho(mid, phrase[0], phrase[1], config,
                                      speed=speed, bpm_target=bpm_target,
                                      work_dir=work_dir, phrase_idx=i,
                                      partes_dir=partes_dir)
        raw_results.append((i - 1, mp3_raw))

    # ── Trimming ────────────────────────────────────────────────────────────
    print(f'\nTrimming silêncio:')
    trimmed = {}
    for orig_idx, mp3_raw in raw_results:
        if mp3_raw and mp3_raw.exists():
            trimmed_mp3 = work_dir / f'frase_{orig_idx:02d}.mp3'
            if trim_mp3(mp3_raw, trimmed_mp3):
                shutil.copy(trimmed_mp3, partes_dir / f'F{orig_idx+1:02d}_trim.mp3')
                mp3_raw.unlink(missing_ok=True)
                trimmed[orig_idx] = trimmed_mp3
                print(f'  F{orig_idx+1:02d}: OK')
            else:
                mp3_raw.rename(trimmed_mp3)
                shutil.copy(trimmed_mp3, partes_dir / f'F{orig_idx+1:02d}_trim.mp3')
                trimmed[orig_idx] = trimmed_mp3
                print(f'  F{orig_idx+1:02d}: OK-notrim')

    succeeded = sorted(trimmed.keys())
    print(f'\n{len(succeeded)}/{len(phrases)} frases prontas.')
    if not succeeded:
        print('ERRO: nenhuma frase.')
        shutil.rmtree(work_dir, ignore_errors=True)
        return False

    # ── Concatenação ────────────────────────────────────────────────────────
    sequence = []
    frases_coladas_info = []

    for k, orig_idx in enumerate(succeeded):
        mp3_trimmed = trimmed[orig_idx]
        dur_s = obter_duracao_mp3(mp3_trimmed)
        inicio_s = ticks_to_sec(phrases[orig_idx][0], tempo_new, tpb)

        if k > 0:
            prev_inicio_s, prev_dur_s = frases_coladas_info[-1]
            if orig_idx == succeeded[k-1] + 1:
                gap_s = inicio_s - (prev_inicio_s + prev_dur_s)
            else:
                gap_s = 1.0
            gap_s = max(0.01, gap_s)
            sil = work_dir / f'sil_{k:02d}.mp3'
            if make_silence_mp3(gap_s, sil):
                sequence.append(sil)
                print(f'  gap F{succeeded[k-1]+1}->F{orig_idx+1}: {gap_s:.2f}s')
                frases_coladas_info[-1] = (prev_inicio_s, prev_dur_s + gap_s)

        sequence.append(mp3_trimmed)
        frases_coladas_info.append((inicio_s, dur_s))

    print(f'\nConcatenando {len(sequence)} segmentos -> {out_path.name} ...')
    inputs = []
    filter_chunks = []
    for idx, seg in enumerate(sequence):
        inputs += ['-i', str(seg.resolve())]
        filter_chunks.append(f'[{idx}:a]')

    filter_str = "".join(filter_chunks) + f"concat=n={len(sequence)}:v=0:a=1[concatout];[concatout]loudnorm=I=-16:TP=-1.5:LRA=11[outa]"

    cmd = ['ffmpeg', '-y'] + inputs + [
        '-filter_complex', filter_str,
        '-map', '[outa]',
        '-c:a', 'libmp3lame', '-q:a', '2', str(out_path)
    ]
    r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    shutil.rmtree(work_dir, ignore_errors=True)

    if out_path.exists():
        # Pós-processamento de fade-in
        pp_script = Path(__file__).parent / 'postprocess_fade_apos_pausa.py'
        if pp_script.exists():
            print("Aplicando pós-processamento de fade-in (Smoothstep 200 ms) ...")
            subprocess.run([
                sys.executable, str(pp_script),
                '--input', str(out_path),
                '--output', str(out_path),
                '--fade-ms', '200',
                '--lookback-ms', '20',
                '--min-silence-ms', '250',
                '--include-start'
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        print(f'\nHino completo: {out_path}  ({out_path.stat().st_size//1024} KB)')

        # Sincronização automática de letras
        hino_id_str = str(hino_id)
        if 'coro' in Path(midi_path).name.lower():
            hino_id_str = 'C' + hino_id_str
        sinc_script = Path(__file__).parent / 'sincronizar_letras.py'
        json_path = out_path.with_suffix('.json')
        print(f'Sincronizando letras (MIDI+MP3+TXT -> JSON) ...')

        r_sinc = subprocess.run([
            sys.executable, str(sinc_script),
            '--hino', hino_id_str,
            '--midi', str(midi_path),
            '--mp3', str(out_path),
            '--output', str(json_path),
            '--partes-dir', str(partes_dir),
            '--bpm-target', str(bpm_target),
            '--speed-factor', str(speed)
        ], capture_output=True, text=True)

        if r_sinc.returncode == 0:
            print(f'  [OK] Letras sincronizadas gravadas em: {json_path.name}')
        else:
            print(f'  [AVISO] Falha ao sincronizar letras (rc={r_sinc.returncode})')
            if r_sinc.stderr.strip():
                print(f'  STDERR do alinhador:\n{r_sinc.stderr.strip()}')

        print(f'{"="*60}\n')
        return True
    else:
        print(f'ERRO concat:\n{r.stderr.decode()}')
        return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Gerar hino no estilo Orquestra 02 (intercalação nicho/mix com Coral e Rock Organ)."
    )
    parser.add_argument('--midi',  required=True, help='Caminho para o MIDI')
    parser.add_argument('--out',   required=True, help='Caminho do MP3 de saída')
    parser.add_argument('--bpm',   type=float, default=None)
    parser.add_argument('--speed', type=float, default=None)
    args = parser.parse_args()
    ok = gerar_hino_orquestra02(args.midi, args.out, args.bpm, args.speed)
    sys.exit(0 if ok else 1)
