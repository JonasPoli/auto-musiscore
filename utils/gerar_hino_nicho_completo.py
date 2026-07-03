#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
utils/gerar_hino_nicho_completo.py
==================================
Orquestração de hino individual pertencente a um nicho instrumental específico
(Cordas, Metais, Sopros ou Paletas). As frases internas progridem em tamanho de 4 a 16
partes, alternando aleatoriamente entre os arranjos daquela mesma família.
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

import mido
from gerar_testes_timbre import (
    get_tempo, detect_phrases,
    MSCORE_BIN,
)
from midi_humanize import (
    remove_staccato_from_mscz, set_tempo_in_mscz, set_pan_in_mscz,
    build_and_inject_audiosettings_pan, ajustar_ultimo_compasso_mscz,
)
from gerar_bibliotecas_nicho import (
    COMBINATIONS_STRINGS, COMBINATIONS_BRASS, COMBINATIONS_PALETAS, COMBINATIONS_SOPROS,
    build_combo_midi, extract_phrase_notes,
)

SILENCE_THRESHOLD_DB = -45
DECAY_TAIL_S = 0.40

def ticks_to_sec(ticks: int, tempo_new: int, tpb: int) -> float:
    return ticks * tempo_new / (tpb * 1_000_000)

def trim_mp3(src: Path, dst: Path) -> bool:
    thr = f'{SILENCE_THRESHOLD_DB}dB'
    af = (
        f'silenceremove=start_periods=1:start_silence=0.05:start_threshold={thr},'
        f'areverse,'
        f'silenceremove=start_periods=1:start_silence={DECAY_TAIL_S}:start_threshold={thr},'
        f'areverse'
    )
    r = subprocess.run(
        ['ffmpeg', '-y', '-i', str(src), '-af', af,
         '-c:a', 'libmp3lame', '-q:a', '2', str(dst)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return r.returncode == 0 and dst.exists()

def make_silence_mp3(duration_s: float, dst: Path) -> bool:
    if duration_s <= 0.01:
        return False
    r = subprocess.run(
        ['ffmpeg', '-y', '-f', 'lavfi', '-t', f'{duration_s:.3f}', '-i', 'aevalsrc=0:s=44100:c=stereo',
         '-c:a', 'libmp3lame', '-q:a', '2', str(dst)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return r.returncode == 0 and dst.exists()

def obter_duracao_mp3(path: Path) -> float:
    cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', str(path)
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        try:
            return float(r.stdout.strip())
        except ValueError:
            pass
    return 0.0

def get_progressive_sizes(n_phrases: int) -> list:
    if n_phrases == 1:
        return [8]
    if n_phrases == 2:
        return [4, 16]
    
    sizes = []
    for i in range(n_phrases):
        progress = i / (n_phrases - 1)
        val = 4 + progress * 12
        if val < 6:
            size = 4
        elif val < 10:
            size = 8
        elif val < 14:
            size = 12
        else:
            size = 16
        sizes.append(size)
        
    for i in range(1, len(sizes)):
        if sizes[i] < sizes[i-1]:
            sizes[i] = sizes[i-1]
            
    sizes[0] = 4
    sizes[-1] = 16
    return sizes

def select_progressive_nicho_combos(group: str, n_phrases: int, seed: int = None) -> list:
    if seed is not None:
        random.seed(seed)
    
    family_configs = {
        "strings": COMBINATIONS_STRINGS,
        "brass": COMBINATIONS_BRASS,
        "paletas": COMBINATIONS_PALETAS,
        "sopros": COMBINATIONS_SOPROS
    }
    
    configs = family_configs[group]
    sizes = get_progressive_sizes(n_phrases)
    
    selected = []
    for size in sizes:
        size_configs = [c for c in configs if c["size"] == size]
        if not size_configs:
            size_configs = configs
        selected.append(random.choice(size_configs))
        
    return selected

def escrever_explicacao_md(partes_dir: Path, selected_configs: list, midi_name: str, group: str):
    md_path = partes_dir / "explicação.md"
    
    group_labels = {
        "strings": "Cordas (Strings)",
        "brass": "Metais (Brass)",
        "paletas": "Paletas (Sax/Clarinetes)",
        "sopros": "Sopros (Woodwinds)"
    }
    
    lines = [
        f"# 🎹 Explicação dos Timbres e Dinâmicas — {midi_name} (Nicho: {group_labels.get(group, group)})",
        "",
        "Este arquivo detalha as especificações técnicas, volumes, UIDs e configurações do MuseSounds aplicadas a cada frase.",
        "",
        "---",
        "",
        "## 🎧 1. Regras de Humanização Acústica",
        "",
        "1. **Timing Offset**: Ajustado estritamente como **0 ms** (timing offset = 0) para evitar atraso ou embolamento de notas.",
        "2. **Dinâmica Pós-Pausa (Velocity & CC11 Ramp)**: A primeira nota tocada pós-silêncio (pausa >= 0.25 tempos) tem a velocidade inicial limitada a **Velocity = 10**. Um crescendo dinâmico via **CC11 (Expression)** sobe de 40 a 100 ao longo de 225 ms.",
        "3. **Fade-In Hermitiano**: Um fade-in de 200 ms usando uma curva Hermitiana (Smoothstep) é aplicado na renderização final para amortecer o ataque.",
        "4. **Encurtamento Pré-Pausa**: Notas que precedem uma pausa (silêncio >= 0.25 tempos) são encurtadas em **30%** de sua duração original.",
        "",
        "---",
        "",
        "## 🎼 2. Detalhamento dos Instrumentos por Frase",
        ""
    ]

    for f_idx, config in enumerate(selected_configs):
        lines.append(f"### 📯 Frase F{f_idx+1:02d} — {config['name']} ({config['size']} partes)")
        lines.append("")
        for track in config["tracks"]:
            vname = track["voice"]
            iname = track["instrument_name"]
            vol = track["vol"]
            prog = track["program"]
            pan = track["pan"]
            octave = track["octave"]
            
            from midi_humanize import _MUSE_LOOKUP
            muse_info = _MUSE_LOOKUP.get(track["instrument_id"])
            if isinstance(muse_info, list):
                muse_info = muse_info[0]
                
            if muse_info:
                muse_str = f"MuseSounds (UID: `{muse_info['uid']}`, Setup: `{muse_info['setup']}`, Pack: `{muse_info['pack']}`)"
            else:
                muse_str = "MS Basic (Fallback SoundFont)"
                
            octave_str = f", Oitava: `{octave:+d}`" if octave != 0 else ""
            lines.append(f"* **{vname}**: {iname} (Volume: `{vol}`, Pan: `{pan}`, Prog GM: `{prog}`{octave_str}) ➔ {muse_str}")
        lines.append("")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  [OK] Explicação gerada em: {md_path.name}")

def render_phrase_nicho(mid, ph_start, ph_end, config, speed, bpm_target, work_dir, phrase_idx, partes_dir=None):
    n = config["size"]
    print(f'  [F{phrase_idx:02d}] {n} instr | {config["name"]}', end='  ')

    voice_notes = extract_phrase_notes(mid, ph_start, ph_end)
    if not voice_notes:
        print('VAZIO')
        return None

    new_mid, ch_pan_map = build_combo_midi(
        mid, voice_notes, config, speed=speed, phrase_start=ph_start
    )

    pdir = work_dir / f'p{phrase_idx:02d}'
    pdir.mkdir(parents=True, exist_ok=True)
    midi_tmp = pdir / 'input.mid'
    mscz_tmp = pdir / 'score.mscz'
    mp3_raw  = pdir / 'raw.mp3'

    new_mid.save(str(midi_tmp))
    subprocess.run([MSCORE_BIN, '-o', str(mscz_tmp), str(midi_tmp)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not mscz_tmp.exists():
        shutil.rmtree(pdir, ignore_errors=True)
        print('ERRO MSCZ')
        return None

    n_stacc = remove_staccato_from_mscz(mscz_tmp)
    set_tempo_in_mscz(mscz_tmp, bpm_target)
    set_pan_in_mscz(mscz_tmp, ch_pan_map)
    n_pan = build_and_inject_audiosettings_pan(mscz_tmp, ch_pan_map)
    ajustar_ultimo_compasso_mscz(mscz_tmp)
    
    if partes_dir:
        partes_dir.mkdir(parents=True, exist_ok=True)
        if midi_tmp.exists():
            shutil.copy(midi_tmp, partes_dir / f'F{phrase_idx:02d}.mid')
        if mscz_tmp.exists():
            shutil.copy(mscz_tmp, partes_dir / f'F{phrase_idx:02d}.mscz')

    midi_tmp.unlink(missing_ok=True)

    r = subprocess.run([MSCORE_BIN, '-o', str(mp3_raw), str(mscz_tmp)],
                       capture_output=True, text=True)
    
    if partes_dir and mp3_raw.exists():
        shutil.copy(mp3_raw, partes_dir / f'F{phrase_idx:02d}_raw.mp3')

    mscz_tmp.unlink(missing_ok=True)

    if not mp3_raw.exists():
        shutil.rmtree(pdir, ignore_errors=True)
        print(f'ERRO MP3 (rc={r.returncode} pan={n_pan} stacc={n_stacc})')
        if r.stdout.strip(): print(f'  STDOUT: {r.stdout.strip()}')
        if r.stderr.strip(): print(f'  STDERR: {r.stderr.strip()}')
        return None

    print(f'RAW OK (pan={n_pan} stacc={n_stacc})')
    return mp3_raw

def gerar_hino_nicho_completo(midi_path: str, output_mp3: str, group: str, bpm_target: float = 60.0, speed: float = None) -> bool:
    mid      = mido.MidiFile(midi_path)
    tempo    = get_tempo(mid)
    bpm_orig = 60_000_000 / tempo
    tpb      = mid.ticks_per_beat
    if bpm_target is None:
        if speed is not None:
            bpm_target = bpm_orig * speed
        else:
            bpm_target = bpm_orig
            
    if speed is None:
        speed = bpm_target / bpm_orig
    tempo_new = int(60_000_000 / bpm_target)

    print(f'\n{"="*60}')
    print(f'  HINO COMPLETO (NICHO {group.upper()}): {Path(midi_path).name}')
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

    # Extrai o ID do hino/coro para usar como semente determinística
    match = re.search(r'(\d+)', Path(midi_path).name)
    hino_id = int(match.group(1)) if match else 42
    
    # Semente baseada no hino_id e na família (para que sejam diferentes mas consistentes)
    seed_val = hino_id + hash(group) % 1000
    
    selected = select_progressive_nicho_combos(group, len(phrases), seed=seed_val)
    print(f'\nProgressão dos Arranjos ({group.upper()}):')
    for i, config in enumerate(selected):
        print(f'  F{i+1}: {config["size"]} instr | {config["name"]}')

    out_path = Path(output_mp3)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    partes_dir = out_path.parent / (out_path.stem + '_partes')
    shutil.rmtree(partes_dir, ignore_errors=True)
    partes_dir.mkdir(parents=True, exist_ok=True)
    escrever_explicacao_md(partes_dir, selected, Path(midi_path).name, group)

    work_dir = Path(f'/tmp/_tmp_hino_nicho_{group}_{os.getpid()}')
    shutil.rmtree(work_dir, ignore_errors=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    raw_results = []
    for i, (phrase, config) in enumerate(zip(phrases, selected), start=1):
        mp3_raw = render_phrase_nicho(mid, phrase[0], phrase[1], config,
                                      speed=speed, bpm_target=bpm_target,
                                      work_dir=work_dir, phrase_idx=i,
                                      partes_dir=partes_dir)
        raw_results.append((i - 1, mp3_raw))

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
                print(f'  gap F{succeeded[k-1]+1}->F{orig_idx+1}: {gap_s:.2f}s (ajustado)')
                frases_coladas_info[-1] = (prev_inicio_s, prev_dur_s + gap_s)
        
        sequence.append(mp3_trimmed)
        frases_coladas_info.append((inicio_s, dur_s))

    print(f'\nConcatenando {len(sequence)} segmentos via filter_complex -> {out_path.name} ...')
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
            '--mp3', str(out_path),
            '--output', str(json_path)
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
    parser = argparse.ArgumentParser()
    parser.add_argument('--midi',  required=True)
    parser.add_argument('--out',   required=True)
    parser.add_argument('--group', required=True, choices=["strings", "brass", "paletas", "sopros"])
    parser.add_argument('--bpm',   type=float, default=None)
    parser.add_argument('--speed', type=float, default=None)
    args = parser.parse_args()
    ok = gerar_hino_nicho_completo(args.midi, args.out, args.group, args.bpm, args.speed)
    sys.exit(0 if ok else 1)
