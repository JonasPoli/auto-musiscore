#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
utils/gerar_testes_timbre.py  — v3
====================================
Gera 125 combinações de timbre orquestral para curadoria.
Cada combinação produz:  MP3 + MSCZ  (sem staccato, sem silêncio inicial)

Mudanças v3:
  - Brass removido: Trompete/Trompa/Trombone/Tuba/Bombardino substituídos
    por madeiras (Sax familia + Corne Inglês + Sax Baritono + Fagote)
  - Pan duro: apenas MIDI CC10 = 16 (esquerda) ou 112 (direita)
  - Strings em 50pct do volume quando combinadas com outros instrumentos
  - Normalizacao de volume (ffmpeg loudnorm) após geração
  - Velocidade padrao = 44pct (hino mais lento do hinario: 44 BPM)
  - Sem canal 9 (percussao GM)
"""

import os, sys, mido, random, shutil, argparse, subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT / 'utils'))
sys.path.insert(0, str(ROOT / 'orchestrators'))
from midi_humanize import (remove_staccato, remove_staccato_from_mscz,
                           set_pan_in_mscz, set_tempo_in_mscz,
                           build_and_inject_audiosettings_pan)

MSCORE_BIN       = "/Applications/MuseScore 4.app/Contents/MacOS/mscore"
MELODIC_CHANNELS = [ch for ch in range(16) if ch != 9]

PAN_LEFT  = 16   # equivale a -90 graus no MuseScore
PAN_RIGHT = 112  # equivale a +90 graus no MuseScore

# ── Pools de Instrumentos ───────────────────────────────────────────────────
# Famílias (fam):
#   "str"   → Cordas (violino, viola, cello, contrabaixo, arpa)
#   "wood"  → Madeiras PURAS — sopros de coluna de ar (flauta, oboé, clarinete, fagote)
#   "sax"   → Paletas/Saxofones (sax soprano, alto, tenor, barítono)
#   "brass" → Metais (trompete, trompa, trombone, tuba, flugelhorn)
# Sax fica em "sax" para não misturar com madeiras puras em combos de orquestra.

SOPRANO_POOL = [
    # ── Madeiras puras (coluna de ar) ──
    {"name": "Flauta",       "program": 73, "vol": 78, "fam": "wood"},   # 0
    {"name": "Piccolo",      "program": 72, "vol": 72, "fam": "wood"},   # 1
    {"name": "Oboé",         "program": 68, "vol": 130, "fam": "wood"},   # 2
    {"name": "Clarinete",    "program": 71, "vol": 130, "fam": "wood"},   # 3
    # ── Paletas / Saxofones ──
    {"name": "Sax Soprano",  "program": 64, "vol": 75, "fam": "sax"},    # 4
    # ── Cordas ──
    {"name": "Violino",      "program": 40, "vol": 82, "fam": "str"},    # 5
    # ── Sax ──
    {"name": "Sax Alto",     "program": 65, "vol": 70, "fam": "sax"},    # 6
    # ── Brass (exatamente como biblioteca-de-sons/brass_standard) ──
    {"name": "Trompete",     "program": 56, "vol": 80, "fam": "brass"},  # 7  (Trumpet p56)
    {"name": "Flugelhorn",   "program": 56, "vol": 76, "fam": "brass"},  # 8  (Flugelhorn p56)
    {"name": "Cornet",       "program": 56, "vol": 76, "fam": "brass"},  # 9  (Cornet p56)
    {"name": "Trompa",       "program": 60, "vol": 74, "fam": "brass"},  # 10 (French Horn p60)
]

CONTRALTO_POOL = [
    # ── Cordas ──
    {"name": "Violino 2",    "program": 40, "vol": 76, "fam": "str"},    # 0
    {"name": "Viola",        "program": 41, "vol": 75, "fam": "str"},    # 1
    # ── Madeiras puras ──
    {"name": "Clarinete",    "program": 71, "vol": 74, "fam": "wood"},   # 2
    {"name": "Corne Ingles", "program": 69, "vol": 74, "fam": "wood"},   # 3  ← índice mudou!
    {"name": "Oboé",         "program": 68, "vol": 73, "fam": "wood"},   # 4
    {"name": "Flauta",       "program": 73, "vol": 72, "fam": "wood"},   # 5
    # ── Paletas / Saxofones ──
    {"name": "Sax Alto",     "program": 65, "vol": 76, "fam": "sax"},    # 6  ← índice mudou!
    {"name": "Piano",        "program":  0, "vol": 70, "fam": "keys"},   # 7  (Acoustic Grand Piano p0)
    # ── Brass ──
    {"name": "Trompa",       "program": 60, "vol": 120, "fam": "brass"},  # 8  (French Horn p60)
    {"name": "Alto Horn",    "program": 60, "vol": 72, "fam": "brass"},  # 9  (Alt Horn p60)
]

TENOR_POOL = [
    # ── Cordas ──
    {"name": "Cello",        "program": 42, "vol": 80, "fam": "str"},    # 0
    {"name": "Viola",        "program": 41, "vol": 74, "fam": "str"},    # 1
    # ── Madeiras puras ──
    {"name": "Corne Ingles", "program": 69, "vol": 160, "fam": "wood"},   # 2  ← índice mudou!
    {"name": "Fagote",       "program": 70, "vol": 180, "fam": "wood"},   # 3  ← índice mudou!
    {"name": "Clarinete",    "program": 71, "vol": 180, "fam": "wood"},   # 4  ← índice mudou!
    # ── Paletas / Saxofones ──
    {"name": "Sax Tenor",    "program": 66, "vol": 78, "fam": "sax"},    # 5  ← índice mudou!
    {"name": "Sax Baritono", "program": 67, "vol": 39, "fam": "sax"},    # 6  ← índice mudou!
    # ── Brass ──
    {"name": "Trombone",     "program": 57, "vol": 150, "fam": "brass"},  # 7  (Trombone p57)
    {"name": "Euphonium",    "program": 57, "vol": 78, "fam": "brass"},  # 8  (Euphonium p57)
    {"name": "Baritone Horn","program": 57, "vol": 76, "fam": "brass"},  # 9  (Baritone Horn p57)
]

BAIXO_POOL = [
    # ── Cordas ──
    {"name": "Contrabaixo",  "program": 43, "vol": 85, "fam": "str"},    # 0
    # ── Madeiras puras ──
    {"name": "Fagote",       "program": 70, "vol": 180, "fam": "wood"},   # 1  ← índice mudou!
    {"name": "Cello",        "program": 42, "vol": 80, "fam": "str"},    # 2  ← índice mudou!
    {"name": "Piano",        "program":  0, "vol": 80, "fam": "keys"},   # 3  (Substitui Arpa por Piano realista)
    {"name": "Clarinete",    "program": 71, "vol": 76, "fam": "wood"},   # 4  ← índice mudou!
    # ── Paletas / Saxofones ──
    {"name": "Sax Baritono", "program": 67, "vol": 40, "fam": "sax"},    # 5  ← índice mudou!
    # ── Brass ──
    {"name": "Tuba",         "program": 58, "vol": 84, "fam": "brass"},  # 6  (Tuba p58)
    {"name": "Trombone Baixo","program": 57, "vol": 82, "fam": "brass"}, # 7  (Bass Trombone p57)
]

PREDEFINED = [
    # ── Cordas Puras (como strings_16part da biblioteca) ──
    ([5],       [0,1],    [0],    [0]),     # 001 Violino | Vl2+Viola | Cello | Cbaixo
    ([5],       [1],      [0],    [0]),     # 002
    ([5],       [0],      [0],    [0]),     # 003
    ([5,5],     [0,1],    [0,1],  [0]),     # 004
    ([5],       [0,1],    [0],    [2]),     # 005 B:Cello (idx2)
    # ── Madeiras Puras (sopros de coluna de ar) ──
    ([2],       [2],      [3],    [1]),     # 006 Oboé|Clarinete|Fagote|Fagote
    ([3],       [2],      [3],    [1]),     # 007
    ([0,3],     [2],      [3],    [1]),     # 008
    ([0,3],     [2,6],    [3],    [1]),     # 009 inclui Sax Alto (C:6)
    ([0,3],     [5,2],    [3],    [1]),     # 010 Flauta+Clarinete (C:5=Flauta)
    # ── Sax Family (paletas) ──
    ([6],       [6],      [5],    [5]),     # 011 SaxAlto|SaxAlto|SaxTenor|SaxBar
    ([4,6],     [6,6],    [5],    [5,5]),   # 012
    ([4],       [6],      [2],    [5]),     # 013 T:CorneIngles(idx2)
    ([4],       [6],      [5,2],  [5,1]),   # 014 T:SaxTenor+CorneIngles
    ([3,4],     [6],      [5,2],  [5,1]),   # 015
    # ── Brass Puros (exatamente brass_standard da biblioteca) ──
    ([7],       [8],      [7],    [6]),     # 016 Trompete|Trompa|Trombone|Tuba
    ([8],       [8,8],    [8,7],  [6,6]),   # 017 Flugelhorn|2xTrompa|Euph+Trombone|2xTuba
    ([7,7],     [7,8],    [7,7],  [7,6]),   # 018 2xTrompete|Trompete+Trompa|2xTrombone|TrombBx+Tuba
    ([10,10],   [8,9],    [7,7],  [7,6]),   # 019 2xTrompa|Trompa+AltoHorn|2xTrombone|TrombBx+Tuba
    ([9,8],     [8,9],    [7,7],  [6,7]),   # 020 Cornet+Flugelhorn|Trompa+AltoHorn|2xTrombone|Tuba+TrombBx
    ([7],       [8,8],    [7,7],  [6,6]),   # 021 Trompete|2xTrompa|2xTrombone|2xTuba
    ([7,8],     [8,9],    [7,8],  [6,7]),   # 022 Trompete+Flugelhorn|Trompa+AltoHorn|Trombone+Euph|Tuba+TrombBx
    ([9,9],     [9,8],    [9,7],  [6,7]),   # 023 2xCornet|AltoHorn+Trompa|BaritHorn+Trombone|Tuba+TrombBx
    # ── Brass + Madeiras ──
    ([7,3],     [8,6],    [7,5],  [6,1]),   # 024 Trompete+Clarinete|Trompa+SaxAlto|Trombone+SaxTenor|Tuba+Fagote
    ([7,0],     [8,6],    [7,2],  [6,1]),   # 025
    ([3,7],     [2,8],    [3,7],  [1,6]),   # 026 Clarinete+Trompete|Clarinete+Trompa|Fagote+Trombone|Fagote+Tuba
    # ── CCB-style Sopros ──
    ([3,3],     [2,6],    [1,2],  [1,5]),   # 027
    ([3,0],     [6,3],    [5,2],  [1]),     # 028
    ([3],       [6],      [5],    [1,5]),   # 029
    ([0,3],     [3,6],    [5,2],  [1,5]),   # 030
    ([3],       [2,6],    [5,2],  [5]),     # 031
    # ── Mistas Cordas+Madeiras ──
    ([0,5],     [1,2],    [0,3],  [0,1]),   # 032
    ([3,5],     [1,2],    [0],    [0]),     # 033
    ([0,5],     [1,5],    [0],    [0]),     # 034 C:Flauta(idx5)
    ([5,2],     [1,6],    [0,4],  [0,1]),   # 035 C:SaxAlto(idx6) T:Clarinete(idx4)
    ([5,0],     [1,2],    [0,3],  [0]),     # 036
    ([5,3],     [1],      [0,3],  [0,1]),   # 037
    # ── Mistas Cordas+Sax ──
    ([5,6],     [1,6],    [0,5],  [0,5]),   # 038
    ([5,6],     [0,6],    [0,5],  [0,5]),   # 039
    ([6,5],     [6],      [5,0],  [0,5]),   # 040
    ([5],       [1,6],    [0,5],  [0,5]),   # 041
    # ── Mistas Cordas+Brass ──
    ([5,7],     [1,8],    [0,7],  [0,6]),   # 042 Violino+Trompete|Viola+Trompa|Cello+Trombone|Cbaixo+Tuba
    ([5,8],     [1,8],    [0,8],  [0,6]),   # 043 Violino+Flugelhorn|Viola+Trompa|Cello+Euph|Cbaixo+Tuba
    ([5,10],    [1,8],    [0,7],  [0,6]),   # 044 Violino+Trompa|Viola+Trompa|Cello+Trombone|Cbaixo+Tuba
    # ── Sopros+Cordas ──
    ([0,3,5],   [2,1],    [0,3],  [0,1]),   # 045
    ([0,5],     [5,1],    [0],    [0]),     # 046 C:Flauta(idx5)
    ([3,5],     [2,1],    [4,0],  [1,0]),   # 047 T:Clarinete(idx4)
    # ── Câmara Pequena ──
    ([0],       [2],      [0],    [1]),     # 048 B:Fagote(idx1)
    ([5],       [7],      [0],    [0]),     # 049
    ([0],       [7],      [0],    [0]),     # 050
    ([0],       [7],      [3],    [1]),     # 051 T:Fagote(idx3)
    ([3],       [7],      [0],    [0]),     # 052
    ([5],       [7],      [3],    [1]),     # 053 T:Fagote(idx3)
    ([2],       [1],      [0],    [0]),     # 054
    # ── Tutti Parcial ──
    ([5,0,3],   [1,2,6],  [0,5],  [0,5]),   # 055
    ([5,0,6],   [1,2,6],  [0,5],  [0,5]),   # 056
    ([5,3,6],   [1,6,6],  [0,5,2],[0,5,1]), # 057
    # ── Sax+Madeiras ──
    ([6,3],     [6,6],    [5,5],  [5,1]),   # 058
    ([6,0],     [6,6],    [2,5],  [5,1]),   # 059
    ([3,6],     [2,6],    [3,5],  [1,5]),   # 060
    # ── Arpa+Combinações ──
    ([5,0],     [7,1],    [0],    [3]),     # 061 B:Arpa(idx3)
    ([0],       [7],      [0],    [3,0]),   # 062 B:Arpa(idx3)
    ([5],       [7,1],    [0],    [3,0]),   # 063 B:Arpa(idx3)
    ([0,3],     [7,2],    [3,0],  [1,0]),   # 064
    # ── Oboé como melodia ──
    ([2],       [1,2],    [0,3],  [0,1]),   # 065
    ([2,5],     [1,7],    [0],    [0]),     # 066
    ([2,0],     [2,1],    [3],    [1]),     # 067
    # ── Piccolo ──
    ([1,5],     [1,2],    [0],    [0]),     # 068
    ([1,3],     [2],      [3],    [1]),     # 069
    ([1,0,5],   [2,1],    [0],    [0]),     # 070
]


def get_tempo(mid):
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'set_tempo':
                return msg.tempo
    return 500_000


def detect_satb_channels(mid):
    pitch_sum, pitch_cnt = {}, {}
    for track in mid.tracks:
        curr = 0
        for msg in track:
            curr += msg.time
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


def detect_phrases(mid, tempo, min_phrase_seconds=8.0, silence_beats=0.4):
    tpb = mid.ticks_per_beat
    min_silence = int(silence_beats * tpb)
    min_phrase  = seconds_to_ticks(min_phrase_seconds, tempo, tpb)
    events = []
    for track in mid.tracks:
        curr = 0
        for msg in track:
            curr += msg.time
            if msg.is_meta or not hasattr(msg, 'channel'):
                continue
            if msg.type == 'note_on' and msg.velocity > 0:
                events.append((curr, 1))
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                events.append((curr, -1))
    if not events:
        return []
    events.sort()
    active, last_off = 0, 0
    phrase_starts = [events[0][0]]
    phrase_ends   = []
    for tick, delta in events:
        if delta == 1:
            if active == 0 and tick > 0:
                gap = tick - last_off
                if gap >= min_silence:
                    ph_start = phrase_starts[-1]
                    if (tick - ph_start) >= min_phrase:
                        phrase_ends.append(last_off)
                        phrase_starts.append(tick)
            active += 1
        else:
            active = max(0, active - 1)
            if active == 0:
                last_off = tick
    phrase_ends.append(events[-1][0])
    return list(zip(phrase_starts, phrase_ends))


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


def is_mixed(instruments):
    """Verdadeiro quando cordas (str) coexistem com sopros (wood ou sax).
    Usado para atenuar volume das cordas e evitar que sopros as abafem."""
    all_fams = {i["fam"] for lst in instruments.values() for i in lst}
    return "str" in all_fams and bool(all_fams & {"wood", "sax"})


def assign_pan(voice, local_idx):
    """Pan duro L/R por voz: Soprano/Tenor → direita, Contralto/Baixo → esquerda.
    Instrumentos dobrados alternam o lado."""
    base_right = voice in ("Soprano", "Tenor")
    right = base_right if local_idx % 2 == 0 else not base_right
    return PAN_RIGHT if right else PAN_LEFT


def build_combo_midi(mid, voice_notes, instruments, speed=0.44, phrase_start=0):
    """Retorna (MidiFile, channel_pan_map) onde channel_pan_map={midi_ch: pan_value}."""
    tempo_orig = get_tempo(mid)
    tempo_new  = int(tempo_orig / speed)
    tpb        = mid.ticks_per_beat
    mixed      = is_mixed(instruments)

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
    channel_pan_map = {}  # {midi_channel: pan_value}
    ordered_pans = []
    ordered_vols = []

    for voice, inst_list in instruments.items():
        notes = voice_notes.get(voice, [])
        if not notes:
            continue
        for local_idx, inst in enumerate(inst_list):
            midi_ch = MELODIC_CHANNELS[ch_counter % len(MELODIC_CHANNELS)]
            ch_counter += 1
            pan = assign_pan(voice, local_idx)
            channel_pan_map[midi_ch] = pan  # registra para set_pan_in_mscz
            ordered_pans.append(pan)
            vol = inst["vol"]
            if mixed and inst["fam"] == "str":
                vol = max(20, vol // 2)
            ordered_vols.append(vol)
            # Atraso aleatório por instrumento ( timing offset ): 5 ms a 25 ms (conforme AGENTS.md)
            # Evita cancelamento de fase e dá densidade realista sem poluir a partitura.
            delay_ticks = seconds_to_ticks(random.uniform(0.005, 0.025), tempo_new, tpb)

            all_events += [
                mido.Message('program_change', channel=midi_ch, program=inst["program"], time=0),
                mido.Message('control_change', channel=midi_ch, control=10, value=pan,  time=0),
                mido.Message('control_change', channel=midi_ch, control=7,  value=min(127, max(0, vol)),  time=0),
                mido.Message('control_change', channel=midi_ch, control=11, value=127,  time=0),
            ]

            fam = inst.get('fam', 'str')
            # ── Parâmetros de ataque pós-pausa por família ────────────────────
            # Strings: arco frágil, Velocity=10 + CC11 40→100 (AGENTS.md)
            # Madeiras/Sax: língua/palheta, mais audível desde o início
            # Brass: embocadura, ataque intermédio
            if fam == 'str':
                attack_vel    = 10
                cc11_start    = 40
            elif fam in ('wood', 'sax'):
                attack_vel    = 40
                cc11_start    = 70
            else:  # brass
                attack_vel    = 30
                cc11_start    = 65

            for i, (note, on_t, off_t, vel) in enumerate(notes):
                dur = remove_staccato(off_t - on_t, tpb)
                is_after_pause  = (i == 0) or (on_t - notes[i-1][2] >= tpb * 0.25)
                is_before_pause = (i < len(notes)-1) and (notes[i+1][1] - off_t >= tpb * 0.25)
                if is_before_pause:
                    dur = int(dur * 0.70)
                on_new  = (on_t - phrase_start) + delay_ticks
                off_new = on_new + max(15, dur)
                v_note  = attack_vel if is_after_pause else min(127, max(1, vel))

                all_events.append(mido.Message('note_on',  channel=midi_ch, note=note,
                                               velocity=v_note, time=on_new))
                all_events.append(mido.Message('note_off', channel=midi_ch, note=note,
                                               velocity=0, time=off_new))
                if is_after_pause:
                    # CC11 ramp: 200-250 ms (AGENTS.md), de cc11_start → 100
                    ramp = seconds_to_ticks(0.225, tempo_new, tpb)
                    for step in range(5):
                        t_cc = on_new + int((step / 4) * ramp)
                        cc_val = int(cc11_start + (step / 4) * (100 - cc11_start))
                        all_events.append(mido.Message('control_change', channel=midi_ch,
                                                        control=11, value=cc_val, time=t_cc))


    setup = [m for m in all_events if m.time == 0]
    music = sorted([m for m in all_events if m.time > 0], key=lambda m: m.time)
    note_track = mido.MidiTrack()
    new_mid.tracks.append(note_track)
    prev = 0
    for msg in setup + music:
        note_track.append(msg.copy(time=msg.time - prev))
        prev = msg.time
    channel_pan_map['ordered_pans'] = ordered_pans
    channel_pan_map['ordered_vols'] = ordered_vols
    return new_mid, channel_pan_map


def combo_to_instruments(s_idxs, c_idxs, t_idxs, b_idxs):
    def pick(pool, idxs):
        seen, r = set(), []
        for i in idxs:
            if i < len(pool) and pool[i]["name"] not in seen:
                seen.add(pool[i]["name"]); r.append(dict(pool[i]))
        return r
    return {
        "Soprano":   pick(SOPRANO_POOL,   s_idxs),
        "Contralto": pick(CONTRALTO_POOL, c_idxs),
        "Tenor":     pick(TENOR_POOL,     t_idxs),
        "Baixo":     pick(BAIXO_POOL,     b_idxs),
    }


def short_name(pool, idxs):
    seen, r = set(), []
    for i in idxs:
        if i < len(pool):
            n = pool[i]["name"]
            if n not in seen:
                seen.add(n); r.append(n)
    return " + ".join(r) if r else "x"


# Soundfont do MS Basic que vem com o MuseScore 4
SOUNDFONT = "/Applications/MuseScore 4.app/Contents/Resources/sound/MS Basic.sf3"


def render_midi_to_mp3(midi_path: Path, mp3_path: Path, sf: str = SOUNDFONT) -> bool:
    """
    Renderiza MIDI → MP3 usando FluidSynth + ffmpeg.
    FluidSynth respeita CC10 (pan) e set_tempo do MIDI nativamente,
    diferente do MuseScore 4 que ignora ambos ao importar MIDI.

    Pipeline: midi → fluidsynth → wav (32-bit float) → ffmpeg → mp3
    """
    wav_tmp = midi_path.with_suffix('.wav')
    try:
        # 1. FluidSynth renderiza MIDI → WAV 44100 Hz stereo
        r = subprocess.run(
            ["fluidsynth", "-ni", sf, str(midi_path),
             "-F", str(wav_tmp), "-r", "44100"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        if r.returncode != 0 or not wav_tmp.exists():
            return False

        # 2. ffmpeg: WAV → MP3 (320kbps, loudnorm EBU R128)
        r = subprocess.run(
            ["ffmpeg", "-y", "-i", str(wav_tmp),
             "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
             "-c:a", "libmp3lame", "-q:a", "2", str(mp3_path)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return r.returncode == 0 and mp3_path.exists()
    finally:
        if wav_tmp.exists():
            wav_tmp.unlink()


def normalize_mp3(mp3_path: Path):
    tmp = mp3_path.with_suffix(".tmp.mp3")
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", str(mp3_path),
         "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
         "-c:a", "libmp3lame", "-q:a", "2", str(tmp)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    if r.returncode == 0 and tmp.exists():
        tmp.replace(mp3_path)


def generate_test_combinations(midi_path, output_dir, phrase_index=1, speed=0.44, n_random=60, bpm_target=60.0):
    mid   = mido.MidiFile(midi_path)
    tempo = get_tempo(mid)
    tpb   = mid.ticks_per_beat
    bpm_orig = int(60_000_000 / tempo)
    bpm_new  = int(bpm_orig * speed)

    phrases = detect_phrases(mid, tempo, min_phrase_seconds=8.0, silence_beats=0.4)
    if not phrases: raise RuntimeError("Nenhuma frase detectada.")
    if phrase_index >= len(phrases): phrase_index = 0
    ph_start, ph_end = phrases[phrase_index]
    dur_orig = (ph_end - ph_start) * tempo / (tpb * 1_000_000)
    dur_slow = dur_orig / speed

    print(f"\nMIDI: {Path(midi_path).name}")
    print(f"Frase {phrase_index+1}: {dur_orig:.1f}s → {dur_slow:.1f}s @ {speed*100:.0f}%  ({bpm_orig}→{bpm_new} BPM)")

    voice_notes = extract_phrase_notes(mid, ph_start, ph_end)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    all_combos = list(PREDEFINED)
    random.seed(42)
    seen_keys = {str(c) for c in all_combos}
    attempts = 0
    while len(all_combos) < len(PREDEFINED) + n_random and attempts < 5000:
        attempts += 1
        s = sorted(random.sample(range(len(SOPRANO_POOL)),   random.choice([1,1,2,2,3])))
        c = sorted(random.sample(range(len(CONTRALTO_POOL)), random.choice([1,1,2,2,3])))
        t = sorted(random.sample(range(len(TENOR_POOL)),     random.choice([1,1,2,2,3])))
        b = sorted(random.sample(range(len(BAIXO_POOL)),     random.choice([1,1,2])))
        key = str((s,c,t,b))
        if key not in seen_keys:
            seen_keys.add(key); all_combos.append((s,c,t,b))

    total = len(all_combos)
    print(f"Total de combinacoes: {total}\n")

    catalog = [
        "# Catalogo de Timbres - Curadoria\n\n",
        f"**Referencia:** `{Path(midi_path).name}`, frase {phrase_index+1} ({dur_slow:.0f}s | {bpm_new} BPM)\n\n",
        "| # | Soprano | Contralto | Tenor | Baixo | Misto? | Ok? |\n",
        "|---|---|---|---|---|---|---|\n",
    ]

    ok = 0
    for idx, combo in enumerate(all_combos, 1):
        s_idxs, c_idxs, t_idxs, b_idxs = combo
        instruments = combo_to_instruments(s_idxs, c_idxs, t_idxs, b_idxs)
        s_str = short_name(SOPRANO_POOL,   s_idxs)
        c_str = short_name(CONTRALTO_POOL, c_idxs)
        t_str = short_name(TENOR_POOL,     t_idxs)
        b_str = short_name(BAIXO_POOL,     b_idxs)
        misto = "m" if is_mixed(instruments) else ""

        fn    = f"{idx:03d} - S[{s_str.replace(' ','_')}] C[{c_str.replace(' ','_')}] T[{t_str.replace(' ','_')}] B[{b_str.replace(' ','_')}]"
        midi_tmp = out / f"_tmp_{idx:03d}.mid"
        mscz_out = out / f"{fn}.mscz"
        mp3_out  = out / f"{fn}.mp3"

        print(f"[{idx:03d}/{total}] {s_str} | {c_str} | {t_str} | {b_str}", end="  ", flush=True)

        new_mid, ch_pan_map = build_combo_midi(mid, voice_notes, instruments, speed=speed, phrase_start=ph_start)
        new_mid.save(str(midi_tmp))

        # ── Passo 1: MIDI → MSCZ (MuseScore importa a partitura) ────────────
        subprocess.run([MSCORE_BIN, "-o", str(mscz_out), str(midi_tmp)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        n_rm = n_pan = n_bpm = 0
        if mscz_out.exists():
            # ── Passo 2: Remove staccato + injeta BPM + CC10 fallback ──────
            n_rm = remove_staccato_from_mscz(mscz_out)
            if set_tempo_in_mscz(mscz_out, bpm_target):
                n_bpm = 1
            set_pan_in_mscz(mscz_out, ch_pan_map)  # CC10 fallback (MS Basic)
            # ── Passo 3: audiosettings.json com MuseSounds + balance correto ─
            n_pan = build_and_inject_audiosettings_pan(mscz_out, ch_pan_map)

        # ── Passo 4: MSCZ → MP3 (MuseSounds com balance correto) ───────────
        if mscz_out.exists():
            subprocess.run([MSCORE_BIN, "-o", str(mp3_out), str(mscz_out)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


        if midi_tmp.exists(): midi_tmp.unlink()
        for f in ["automation.json", "audiosettings.json", "viewsettings.json"]:
            fp = out / f
            if fp.exists(): fp.unlink()

        if mp3_out.exists():
            print(f"OK (bpm={n_bpm} pan={n_pan} stacc={n_rm})"); ok += 1
        else:
            print("ERRO")

        catalog.append(f"| `{idx:03d}` | {s_str} | {c_str} | {t_str} | {b_str} | {misto} | |\n")

    (out / "catalogo.md").write_text("".join(catalog), encoding='utf-8')
    print(f"\n{'='*60}")
    print(f"  {ok}/{total} combinacoes geradas!")
    print(f"  Pasta: {out}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--midi",      default="mid/Coro 002- Toda a glória a Jesus.mid")
    parser.add_argument("--output",    default="testes_timbre")
    parser.add_argument("--frase",     type=int,   default=1)
    parser.add_argument("--bpm",       type=float, default=60.0,
                        help="BPM alvo de saída (default: 60). Sobrepõe --speed.")
    parser.add_argument("--speed",     type=float, default=None,
                        help="Fator de velocidade (opcional, sobrepõe --bpm se fornecido)")
    parser.add_argument("--aleatorio", type=int,   default=60)
    args = parser.parse_args()

    # Calcula speed a partir do BPM alvo, a menos que --speed seja especificado
    import mido as _mido_check
    _mid_check = _mido_check.MidiFile(args.midi)
    _tempo_check = get_tempo(_mid_check)
    _bpm_orig = int(60_000_000 / _tempo_check)
    if args.speed is not None:
        speed_final = args.speed
    else:
        speed_final = args.bpm / _bpm_orig
    print(f"BPM original: {_bpm_orig}  →  BPM alvo: {args.bpm}  (speed={speed_final:.3f})")

    generate_test_combinations(args.midi, args.output, args.frase, speed_final, args.aleatorio)
