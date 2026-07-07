#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
organ/gerar_hino_orgao_completo.py
===================================
Orquestração de hino individual com progressão de timbres de órgão eletrônico.
Cada frase interna usa uma combinação diferente do pool aprovado,
progredindo de timbres simples (puros) para camadas mais complexas
(layered, pad, split).

Segue o mesmo padrão de utils/gerar_hino_nicho_completo.py.
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
from gerar_testes_timbre import get_tempo, detect_phrases
from midi_humanize import (
    remove_staccato, remove_staccato_from_mscz, set_tempo_in_mscz,
    ajustar_ultimo_compasso_mscz,
)

MSCORE_BIN = "/Applications/MuseScore 4.app/Contents/MacOS/mscore"
SILENCE_THRESHOLD_DB = -45
DECAY_TAIL_S = 0.40

# ─── Canais melódicos (sem canal 9 = percussão) ──────────────────────────────
MELODIC_CHANNELS = [ch for ch in range(16) if ch != 9]


# =============================================================================
#  POOL DE COMBINAÇÕES APROVADAS (curadas pelo usuário)
# =============================================================================

def _combo(cid, name, layers, desc, complexity, vel_scales=None, voice_split=None):
    return {
        "id": cid,
        "name": name,
        "programs": layers,
        "description": desc,
        "complexity": complexity,  # 1=simples, 2=layered, 3=pad, 4=triplo, 5=split
        "vel_scales": vel_scales,
        "voice_split": voice_split,
    }


ORGAN_COMBINATIONS = [
    # Complexidade 1: Puros
    _combo("001", "Drawbar Organ Puro",    [16],    "Hammond clássico", 1),
    _combo("003", "Rock Organ",            [18],    "Hammond com drive", 1),

    # Complexidade 2: Layered (2 camadas)
    _combo("007", "Drawbar + Rock",        [16, 18], "Hammond + drive", 2,
           vel_scales={16: 0.85, 18: 0.60}),
    _combo("008", "Drawbar + Church",      [16, 19], "Hammond + tubos", 2,
           vel_scales={16: 0.80, 19: 0.65}),
    _combo("009", "Drawbar + Reed",        [16, 20], "Hammond + harmonium", 2,
           vel_scales={16: 0.80, 20: 0.65}),
    _combo("010", "Rock + Church",         [18, 19], "Drive + solenidade", 2,
           vel_scales={18: 0.70, 19: 0.75}),
    _combo("011", "Rock + Reed",           [18, 20], "Drive + harmonium", 2,
           vel_scales={18: 0.75, 20: 0.65}),
    _combo("012", "Church + Reed",         [19, 20], "Tubos + harmonium", 2,
           vel_scales={19: 0.80, 20: 0.70}),

    # Complexidade 3: Com Pad
    _combo("013", "Drawbar + Warm Pad",    [16, 89], "Hammond + pad quente", 3,
           vel_scales={16: 0.85, 89: 0.50}),
    _combo("015", "Drawbar + Halo Pad",    [16, 94], "Hammond + pad etéreo", 3,
           vel_scales={16: 0.85, 94: 0.45}),
    _combo("018", "Rock + Polysynth",      [18, 90], "Drive + synth organ", 3,
           vel_scales={18: 0.75, 90: 0.55}),

    # Complexidade 4: Triplos
    _combo("019", "Drawbar + Rock + Warm Pad",    [16, 18, 89], "Triplo layered", 4,
           vel_scales={16: 0.70, 18: 0.50, 89: 0.40}),
    _combo("020", "Drawbar + Church + Warm Pad",  [16, 19, 89], "Corpo completo", 4,
           vel_scales={16: 0.70, 19: 0.55, 89: 0.40}),
    _combo("021", "Drawbar + Reed + Halo Pad",    [16, 20, 94], "Harmonium celestial", 4,
           vel_scales={16: 0.70, 20: 0.55, 94: 0.35}),

    # Complexidade 5: Split por voz
    _combo("023", "Split Clássico",        [18, 16, 16, 19], "Rock melodia + Church baixo", 5,
           voice_split={"Soprano": [18], "Contralto": [16], "Tenor": [16], "Baixo": [19]}),
    _combo("024", "Split Litúrgico",       [19, 19, 20, 20], "Church agudo + Reed grave", 5,
           voice_split={"Soprano": [19], "Contralto": [19], "Tenor": [20], "Baixo": [20]}),
    _combo("026", "Split Rock-Church",     [18, 18, 19, 19], "Rock altas + Church graves", 5,
           voice_split={"Soprano": [18], "Contralto": [18], "Tenor": [19], "Baixo": [19]}),
    _combo("027", "Split Drawbar-Reed",    [16, 16, 20, 20], "Hammond + Harmonium graves", 5,
           voice_split={"Soprano": [16], "Contralto": [16], "Tenor": [20], "Baixo": [20]}),
    _combo("028", "Split Full",            [18, 16, 20, 19], "Cada voz um timbre", 5,
           voice_split={"Soprano": [18], "Contralto": [16], "Tenor": [20], "Baixo": [19]}),
    _combo("029", "Drawbar+Rock (Rock forte)", [16, 18], "Rock mais presente", 2,
           vel_scales={16: 0.60, 18: 0.85}),
    _combo("030", "Drawbar+Church (Church forte)", [16, 19], "Church mais presente", 2,
           vel_scales={16: 0.55, 19: 0.90}),
]


# =============================================================================
#  PROGRESSÃO POR COMPLEXIDADE
# =============================================================================

def get_progressive_complexities(n_phrases: int) -> list:
    """Retorna uma lista de complexidades progressivas para N frases.
    Começa simples (1) e termina complexo (5)."""
    if n_phrases == 1:
        return [3]
    if n_phrases == 2:
        return [1, 5]
    if n_phrases == 3:
        return [1, 3, 5]

    complexities = []
    for i in range(n_phrases):
        progress = i / (n_phrases - 1)
        val = 1 + progress * 4  # 1.0 → 5.0
        complexities.append(max(1, min(5, round(val))))

    # Garante que não decresce
    for i in range(1, len(complexities)):
        if complexities[i] < complexities[i - 1]:
            complexities[i] = complexities[i - 1]

    complexities[0] = 1
    complexities[-1] = 5
    return complexities


def select_progressive_organ_combos(n_phrases: int, seed: int = None) -> list:
    """Seleciona combinações de órgão progressivas para N frases."""
    if seed is not None:
        random.seed(seed)

    target_complexities = get_progressive_complexities(n_phrases)
    selected = []

    for target_c in target_complexities:
        # Busca combinações com a complexidade alvo
        candidates = [c for c in ORGAN_COMBINATIONS if c["complexity"] == target_c]
        if not candidates:
            # Fallback: complexidade mais próxima
            for delta in [1, -1, 2, -2, 3, -3]:
                candidates = [c for c in ORGAN_COMBINATIONS if c["complexity"] == target_c + delta]
                if candidates:
                    break
        if not candidates:
            candidates = ORGAN_COMBINATIONS

        selected.append(random.choice(candidates))

    return selected


# =============================================================================
#  DETECÇÃO SATB
# =============================================================================

def detect_satb_channels(mid):
    pitch_sum, pitch_cnt = {}, {}
    for track in mid.tracks:
        for msg in track:
            if msg.is_meta or not hasattr(msg, 'channel'):
                continue
            if msg.type == 'note_on' and msg.velocity > 0:
                ch = msg.channel
                pitch_sum[ch] = pitch_sum.get(ch, 0) + msg.note
                pitch_cnt[ch] = pitch_cnt.get(ch, 0) + 1
    if not pitch_sum:
        return {}
    avg = {ch: pitch_sum[ch] / pitch_cnt[ch] for ch in pitch_sum}
    sorted_chs = sorted(avg, key=lambda c: avg[c], reverse=True)
    voices = ["Soprano", "Contralto", "Tenor", "Baixo"]
    return {sorted_chs[i]: voices[i] for i in range(min(len(sorted_chs), len(voices)))}


def seconds_to_ticks(sec, tempo, tpb):
    return int(sec * 1_000_000 * tpb / tempo)


def ticks_to_sec(ticks, tempo_new, tpb):
    return ticks * tempo_new / (tpb * 1_000_000)


def extract_phrase_notes(mid, ph_start, ph_end):
    ch_to_voice = detect_satb_channels(mid)
    voice_notes = {}
    for track in mid.tracks:
        active = {}
        curr = 0
        for msg in track:
            curr += msg.time
            if msg.is_meta or not hasattr(msg, 'channel'):
                continue
            ch = msg.channel
            if ch not in ch_to_voice:
                continue
            voice = ch_to_voice[ch]
            if msg.type == 'note_on' and msg.velocity > 0:
                active.setdefault(ch, {})[msg.note] = (curr, msg.velocity)
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                if ch in active and msg.note in active.get(ch, {}):
                    on_t, vel = active[ch].pop(msg.note)
                    if ph_start <= on_t < ph_end:
                        voice_notes.setdefault(voice, []).append((msg.note, on_t, curr, vel))
    for v in voice_notes:
        voice_notes[v].sort(key=lambda x: x[1])
    return voice_notes


# =============================================================================
#  CONSTRUÇÃO DO MIDI HUMANIZADO PARA ÓRGÃO
# =============================================================================

def build_organ_midi(mid, voice_notes, combo, speed=0.5, phrase_start=0):
    """Constrói MIDI humanizado para a combinação de órgão."""
    tempo_orig = get_tempo(mid)
    tempo_new = int(tempo_orig / speed)
    tpb = mid.ticks_per_beat

    new_mid = mido.MidiFile()
    new_mid.ticks_per_beat = tpb
    meta = mido.MidiTrack()
    new_mid.tracks.append(meta)

    for track in mid.tracks:
        for msg in track:
            if msg.is_meta and msg.type in ['time_signature', 'key_signature']:
                meta.append(msg.copy())
    meta.append(mido.MetaMessage('set_tempo', tempo=tempo_new, time=0))

    all_events = []
    ch_counter = 0

    voice_split = combo.get("voice_split")
    programs = combo["programs"]
    vel_scales = combo.get("vel_scales") or {}

    attack_vel = 10
    cc11_start = 40

    voices_order = ["Soprano", "Contralto", "Tenor", "Baixo"]

    for voice in voices_order:
        notes = voice_notes.get(voice, [])
        if not notes:
            continue

        if voice_split:
            voice_programs = voice_split.get(voice, programs[:1])
        else:
            voice_programs = programs

        for prog in voice_programs:
            midi_ch = MELODIC_CHANNELS[ch_counter % len(MELODIC_CHANNELS)]
            ch_counter += 1

            if vel_scales and prog in vel_scales:
                v_scale = vel_scales[prog]
            elif len(voice_programs) > 1:
                v_scale = 1.0 / len(voice_programs)
            else:
                v_scale = 1.0

            vol = min(127, max(40, int(100 * v_scale)))

            all_events += [
                mido.Message('program_change', channel=midi_ch, program=prog, time=0),
                mido.Message('control_change', channel=midi_ch, control=10, value=64, time=0),
                mido.Message('control_change', channel=midi_ch, control=7,  value=vol, time=0),
                mido.Message('control_change', channel=midi_ch, control=11, value=127, time=0),
            ]

            for i, (note, on_t, off_t, vel) in enumerate(notes):
                dur = remove_staccato(off_t - on_t, tpb)
                is_after_pause = (i == 0) or (on_t - notes[i - 1][2] >= tpb * 0.25)
                is_before_pause = (i < len(notes) - 1) and (notes[i + 1][1] - off_t >= tpb * 0.25)

                if is_before_pause:
                    dur = int(dur * 0.70)

                on_new = on_t - phrase_start
                off_new = on_new + max(15, dur)

                next_start = None
                for nj in notes[i + 1:]:
                    if nj[1] > on_t:
                        next_start = nj[1] - phrase_start
                        break
                if next_start is not None and off_new > next_start:
                    off_new = max(on_new + 5, next_start)

                v_note = attack_vel if is_after_pause else min(127, max(1, int(vel * v_scale)))

                all_events.append(mido.Message(
                    'note_on', channel=midi_ch, note=note,
                    velocity=v_note, time=on_new))
                all_events.append(mido.Message(
                    'note_off', channel=midi_ch, note=note,
                    velocity=0, time=off_new))

                if is_after_pause:
                    ramp = seconds_to_ticks(0.225, tempo_new, tpb)
                    for step in range(5):
                        t_cc = on_new + int((step / 4) * ramp)
                        cc_val = int(cc11_start + (step / 4) * (100 - cc11_start))
                        all_events.append(mido.Message(
                            'control_change', channel=midi_ch,
                            control=11, value=cc_val, time=t_cc))

    setup = [m for m in all_events if m.time == 0]
    music = sorted([m for m in all_events if m.time > 0], key=lambda m: m.time)
    note_track = mido.MidiTrack()
    new_mid.tracks.append(note_track)
    prev = 0
    for msg in setup + music:
        note_track.append(msg.copy(time=msg.time - prev))
        prev = msg.time

    return new_mid


# =============================================================================
#  UTILIDADES DE ÁUDIO
# =============================================================================

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


def clean_runtime_files(directory: Path):
    """Limpa resíduos do MuseScore CLI (AGENTS.md §3)."""
    for f in ["automation.json", "audiosettings.json", "viewsettings.json"]:
        fp = directory / f
        if fp.exists():
            try:
                fp.unlink()
            except OSError:
                pass
    for d in ["META-INF", "Thumbnails"]:
        dp = directory / d
        if dp.exists() and dp.is_dir():
            try:
                shutil.rmtree(dp)
            except OSError:
                pass


# =============================================================================
#  RENDERIZAÇÃO DE UMA FRASE VIA MUSESCORE
# =============================================================================

def render_phrase_organ(mid, ph_start, ph_end, combo, speed, bpm_target,
                        work_dir, phrase_idx, partes_dir=None):
    """Renderiza uma frase com a combinação de órgão especificada."""
    progs = "+".join(str(p) for p in combo["programs"])
    print(f'  [F{phrase_idx:02d}] {combo["name"]} (GM {progs})', end='  ')

    voice_notes = extract_phrase_notes(mid, ph_start, ph_end)
    if not voice_notes:
        print('VAZIO')
        return None

    new_mid = build_organ_midi(mid, voice_notes, combo, speed=speed, phrase_start=ph_start)

    pdir = work_dir / f'p{phrase_idx:02d}'
    pdir.mkdir(parents=True, exist_ok=True)
    midi_tmp = pdir / 'input.mid'
    mscz_tmp = pdir / 'score.mscz'
    mp3_raw = pdir / 'raw.mp3'

    new_mid.save(str(midi_tmp))

    try:
        subprocess.run([MSCORE_BIN, '-o', str(mscz_tmp), str(midi_tmp)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not mscz_tmp.exists():
            shutil.rmtree(pdir, ignore_errors=True)
            print('ERRO MSCZ')
            return None

        n_stacc = remove_staccato_from_mscz(mscz_tmp)
        set_tempo_in_mscz(mscz_tmp, bpm_target)
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
            print(f'ERRO MP3 (rc={r.returncode} stacc={n_stacc})')
            return None

        print(f'OK (stacc={n_stacc})')
        return mp3_raw

    finally:
        clean_runtime_files(pdir)


# =============================================================================
#  EXPLICAÇÃO MARKDOWN
# =============================================================================

def escrever_explicacao_md(partes_dir: Path, selected_configs: list, midi_name: str):
    md_path = partes_dir / "explicação.md"

    lines = [
        f"# 🎹 Explicação dos Timbres — {midi_name} (Órgão Eletrônico)",
        "",
        "---",
        "",
        "## 🎧 1. Regras de Humanização Acústica",
        "",
        "1. **Timing Offset**: 0 ms (sem desincronismo)",
        "2. **Dinâmica Pós-Pausa**: Velocity = 10 + CC11 ramp 40→100 em 225ms",
        "3. **Fade-In Hermitiano**: Smoothstep 200ms",
        "4. **Encurtamento Pré-Pausa**: 30%",
        "",
        "---",
        "",
        "## 🎼 2. Detalhamento por Frase",
        ""
    ]

    for f_idx, config in enumerate(selected_configs):
        progs = "+".join(str(p) for p in config["programs"])
        lines.append(f"### 📯 Frase F{f_idx + 1:02d} — {config['name']} (GM {progs})")
        lines.append(f"**Complexidade**: {config['complexity']}/5 | **Descrição**: {config['description']}")
        lines.append("")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  [OK] Explicação: {md_path.name}")


# =============================================================================
#  GERAÇÃO DO HINO COMPLETO
# =============================================================================

def gerar_hino_orgao_completo(midi_path: str, output_mp3: str,
                               bpm_target: float = None, speed: float = 0.5) -> bool:
    mid = mido.MidiFile(midi_path)
    tempo = get_tempo(mid)
    bpm_orig = 60_000_000 / tempo
    tpb = mid.ticks_per_beat

    if bpm_target is None:
        if speed is not None:
            bpm_target = bpm_orig * speed
        else:
            bpm_target = bpm_orig
    if speed is None:
        speed = bpm_target / bpm_orig
    tempo_new = int(60_000_000 / bpm_target)

    print(f'\n{"="*60}')
    print(f'  HINO COMPLETO (ÓRGÃO ELETRÔNICO): {Path(midi_path).name}')
    print(f'  BPM: {bpm_orig:.0f} -> {bpm_target:.0f}  (speed={speed:.3f})')
    print(f'{"="*60}')

    phrases = detect_phrases(mid, tempo, min_phrase_seconds=6.0, silence_beats=0.4)
    if not phrases:
        print('ERRO: nenhuma frase detectada.')
        return False

    print(f'\nFrases ({len(phrases)}):')
    for i, (s, e) in enumerate(phrases):
        dur_tgt = ticks_to_sec(e - s, tempo_new, tpb) / speed
        gap_tgt = ticks_to_sec(phrases[i + 1][0] - e, tempo_new, tpb) if i + 1 < len(phrases) else 0
        print(f'  Frase {i + 1}: {dur_tgt:.1f}s  gap->{gap_tgt:.1f}s')

    # Semente determinística baseada no ID do hino
    match = re.search(r'(\d+)', Path(midi_path).name)
    hino_id = int(match.group(1)) if match else 42
    seed_val = hino_id + 7777  # offset para diferenciar de nichos

    selected = select_progressive_organ_combos(len(phrases), seed=seed_val)
    print(f'\nProgressão dos Timbres:')
    for i, config in enumerate(selected):
        progs = "+".join(str(p) for p in config["programs"])
        print(f'  F{i + 1}: [{config["complexity"]}] {config["name"]} (GM {progs})')

    out_path = Path(output_mp3)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    partes_dir = out_path.parent / (out_path.stem + '_partes')
    shutil.rmtree(partes_dir, ignore_errors=True)
    partes_dir.mkdir(parents=True, exist_ok=True)
    escrever_explicacao_md(partes_dir, selected, Path(midi_path).name)

    work_dir = Path(f'/tmp/_tmp_hino_orgao_{os.getpid()}')
    shutil.rmtree(work_dir, ignore_errors=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    raw_results = []
    for i, (phrase, config) in enumerate(zip(phrases, selected), start=1):
        mp3_raw = render_phrase_organ(mid, phrase[0], phrase[1], config,
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
                shutil.copy(trimmed_mp3, partes_dir / f'F{orig_idx + 1:02d}_trim.mp3')
                mp3_raw.unlink(missing_ok=True)
                trimmed[orig_idx] = trimmed_mp3
                print(f'  F{orig_idx + 1:02d}: OK')
            else:
                mp3_raw.rename(trimmed_mp3)
                shutil.copy(trimmed_mp3, partes_dir / f'F{orig_idx + 1:02d}_trim.mp3')
                trimmed[orig_idx] = trimmed_mp3
                print(f'  F{orig_idx + 1:02d}: OK-notrim')

    succeeded = sorted(trimmed.keys())
    print(f'\n{len(succeeded)}/{len(phrases)} frases prontas.')
    if not succeeded:
        print('ERRO: nenhuma frase renderizada.')
        shutil.rmtree(work_dir, ignore_errors=True)
        return False

    # Concatenação com silêncios entre frases
    sequence = []
    frases_coladas_info = []

    for k, orig_idx in enumerate(succeeded):
        mp3_trimmed = trimmed[orig_idx]
        dur_s = obter_duracao_mp3(mp3_trimmed)
        inicio_s = ticks_to_sec(phrases[orig_idx][0], tempo_new, tpb)

        if k > 0:
            prev_inicio_s, prev_dur_s = frases_coladas_info[-1]
            if orig_idx == succeeded[k - 1] + 1:
                gap_s = inicio_s - (prev_inicio_s + prev_dur_s)
            else:
                gap_s = 1.0
            gap_s = max(0.01, gap_s)
            sil = work_dir / f'sil_{k:02d}.mp3'
            if make_silence_mp3(gap_s, sil):
                sequence.append(sil)
                print(f'  gap F{succeeded[k - 1] + 1}->F{orig_idx + 1}: {gap_s:.2f}s')
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
        # Pós-processamento fade-in (AGENTS.md)
        pp_script = ROOT / 'utils' / 'postprocess_fade_apos_pausa.py'
        if pp_script.exists():
            print("Aplicando fade-in Smoothstep 200ms ...")
            subprocess.run([
                sys.executable, str(pp_script),
                '--input', str(out_path),
                '--output', str(out_path),
                '--fade-ms', '200',
                '--lookback-ms', '20',
                '--min-silence-ms', '250',
                '--include-start'
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        print(f'\nHino completo: {out_path}  ({out_path.stat().st_size // 1024} KB)')

        # Sincronização de letras
        hino_id_str = str(hino_id)
        if 'coro' in Path(midi_path).name.lower():
            hino_id_str = 'C' + hino_id_str
        sinc_script = ROOT / 'utils' / 'sincronizar_letras.py'
        json_path = out_path.with_suffix('.json')
        print(f'Sincronizando letras ...')

        r_sinc = subprocess.run([
            sys.executable, str(sinc_script),
            '--hino', hino_id_str,
            '--mp3', str(out_path),
            '--output', str(json_path)
        ], capture_output=True, text=True)

        if r_sinc.returncode == 0:
            print(f'  [OK] Letras: {json_path.name}')
        else:
            print(f'  [AVISO] Falha ao sincronizar letras (rc={r_sinc.returncode})')

        print(f'{"="*60}\n')
        return True
    else:
        print(f'ERRO concat:\n{r.stderr.decode()}')
        return False


# =============================================================================
#  CLI
# =============================================================================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Gera hino completo com progressão de timbres de órgão eletrônico."
    )
    parser.add_argument('--midi', required=True, help="Caminho do MIDI de entrada")
    parser.add_argument('--out', required=True, help="Caminho do MP3 de saída")
    parser.add_argument('--bpm', type=float, default=None, help="BPM alvo")
    parser.add_argument('--speed', type=float, default=0.5, help="Fator de velocidade (default: 0.5)")
    args = parser.parse_args()

    ok = gerar_hino_orgao_completo(args.midi, args.out, args.bpm, args.speed)
    sys.exit(0 if ok else 1)
