#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
orchestrators/musescore_orquestra_frases.py
============================================
Orquestrador Dinâmico por Frase — CCB

Identifica as frases musicais de um hino MIDI e aplica uma orquestração
diferente em cada frase, sorteada aleatoriamente dentre 16 presets agrupados
em 3 categorias: Abertura, Meio e Encerramento.

Uso:
  python orchestrators/musescore_orquestra_frases.py \
      --midi "mid/Coro 002- Toda a glória a Jesus.mid" \
      --output biblioteca-de-sons/orquestra_frases \
      --variacoes 10
"""

import os
import sys
import mido
import random
import shutil
import argparse
import subprocess
import unicodedata
from pathlib import Path

ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT / 'utils'))
from midi_humanize import remove_staccato, remove_staccato_from_mscz

MSCORE_BIN  = "/Applications/MuseScore 4.app/Contents/MacOS/mscore"
VENV_PYTHON = str(ROOT / ".venv" / "bin" / "python")

# ──────────────────────────────────────────────────────────────────────────────
# Utilitários MIDI
# ──────────────────────────────────────────────────────────────────────────────

def seconds_to_ticks(seconds, tempo, ticks_per_beat):
    return int(seconds * 1_000_000.0 * ticks_per_beat / tempo)

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

def extract_voice_notes(mid, channel_to_voice):
    voice_to_notes = {}
    for track in mid.tracks:
        active = {}
        curr = 0
        for msg in track:
            curr += msg.time
            if msg.is_meta or not hasattr(msg, 'channel'):
                continue
            ch = msg.channel
            if ch not in channel_to_voice:
                continue
            voice = channel_to_voice[ch]
            if msg.type == 'note_on' and msg.velocity > 0:
                active.setdefault(ch, {})[msg.note] = (curr, msg.velocity)
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                if ch in active and msg.note in active.get(ch, {}):
                    on_t, vel = active[ch].pop(msg.note)
                    voice_to_notes.setdefault(voice, []).append((msg.note, on_t, curr, vel))
    for v in voice_to_notes:
        voice_to_notes[v].sort(key=lambda x: x[1])
    return voice_to_notes

# ──────────────────────────────────────────────────────────────────────────────
# Detecção de Frases
# ──────────────────────────────────────────────────────────────────────────────

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

    active = 0
    last_off = 0
    phrase_starts = [0]
    phrase_ends   = []

    for tick, delta in events:
        if delta == 1:
            if active == 0 and tick > 0:
                gap = tick - last_off
                if gap >= min_silence:
                    phrase_start = phrase_starts[-1]
                    if (tick - phrase_start) >= min_phrase:
                        phrase_ends.append(last_off)
                        phrase_starts.append(tick)
            active += 1
        else:
            active = max(0, active - 1)
            if active == 0:
                last_off = tick

    max_tick = events[-1][0] if events else 0
    phrase_ends.append(max_tick)
    return list(zip(phrase_starts, phrase_ends))

# ──────────────────────────────────────────────────────────────────────────────
# Catálogo de Presets
# ──────────────────────────────────────────────────────────────────────────────

PRESETS = {
    "A1": {"name": "Abertura Suave / Devocional", "category": "abertura", "instruments": [
        {"voice": "Soprano",   "name": "Flauta",       "program": 73, "vol": 75},
        {"voice": "Soprano",   "name": "Clarinete",    "program": 71, "vol": 70},
        {"voice": "Soprano",   "name": "Violino 1",    "program": 40, "vol": 70},
        {"voice": "Contralto", "name": "Violino 2",    "program": 40, "vol": 65},
        {"voice": "Contralto", "name": "Viola",        "program": 41, "vol": 65},
        {"voice": "Tenor",     "name": "Cello",        "program": 42, "vol": 70},
        {"voice": "Baixo",     "name": "Contrabaixo",  "program": 43, "vol": 72},
    ]},
    "A2": {"name": "Abertura de Câmara — Cordas", "category": "abertura", "instruments": [
        {"voice": "Soprano",   "name": "Violino 1",    "program": 40, "vol": 80},
        {"voice": "Soprano",   "name": "Violino 2",    "program": 40, "vol": 75},
        {"voice": "Contralto", "name": "Viola",        "program": 41, "vol": 75},
        {"voice": "Tenor",     "name": "Cello",        "program": 42, "vol": 78},
        {"voice": "Tenor",     "name": "Cello 2",      "program": 42, "vol": 72},
        {"voice": "Baixo",     "name": "Contrabaixo",  "program": 43, "vol": 82},
    ]},
    "A3": {"name": "Abertura de Sopros Doces", "category": "abertura", "instruments": [
        {"voice": "Soprano",   "name": "Clarinete 1",  "program": 71, "vol": 80},
        {"voice": "Soprano",   "name": "Clarinete 2",  "program": 71, "vol": 75},
        {"voice": "Soprano",   "name": "Flauta",       "program": 73, "vol": 70},
        {"voice": "Contralto", "name": "Trompa",       "program": 60, "vol": 70},
        {"voice": "Contralto", "name": "Sax Alto",     "program": 65, "vol": 68},
        {"voice": "Tenor",     "name": "Sax Tenor",    "program": 66, "vol": 72},
        {"voice": "Tenor",     "name": "Bombardino",   "program": 61, "vol": 70},
        {"voice": "Baixo",     "name": "Fagote",       "program": 70, "vol": 78},
        {"voice": "Baixo",     "name": "Tuba",         "program": 58, "vol": 72},
    ]},
    "A4": {"name": "Abertura Solene", "category": "abertura", "instruments": [
        {"voice": "Soprano",   "name": "Trompete",     "program": 56, "vol": 72},
        {"voice": "Soprano",   "name": "Clarinete",    "program": 71, "vol": 70},
        {"voice": "Contralto", "name": "Trompa 1",     "program": 60, "vol": 74},
        {"voice": "Contralto", "name": "Trompa 2",     "program": 60, "vol": 70},
        {"voice": "Tenor",     "name": "Trombone",     "program": 57, "vol": 72},
        {"voice": "Baixo",     "name": "Tuba",         "program": 58, "vol": 80},
        {"voice": "Baixo",     "name": "Contrabaixo",  "program": 43, "vol": 75},
    ]},
    "A5": {"name": "Abertura Arpa / Pizzicato", "category": "abertura", "instruments": [
        {"voice": "Soprano",   "name": "Flauta Solo",  "program": 73, "vol": 80},
        {"voice": "Soprano",   "name": "Violino Solo", "program": 40, "vol": 75},
        {"voice": "Contralto", "name": "Arpa",         "program": 46, "vol": 70},
        {"voice": "Contralto", "name": "Viola",        "program": 41, "vol": 65},
        {"voice": "Tenor",     "name": "Clarinete",    "program": 71, "vol": 68},
        {"voice": "Baixo",     "name": "Arpa Grave",   "program": 46, "vol": 72},
    ]},
    "M1": {"name": "Meio — Melodia nas Cordas", "category": "meio", "instruments": [
        {"voice": "Soprano",   "name": "Violino 1",    "program": 40, "vol": 85},
        {"voice": "Contralto", "name": "Violino 2",    "program": 40, "vol": 78},
        {"voice": "Contralto", "name": "Viola",        "program": 41, "vol": 75},
        {"voice": "Tenor",     "name": "Cello",        "program": 42, "vol": 80},
        {"voice": "Baixo",     "name": "Contrabaixo",  "program": 43, "vol": 85},
    ]},
    "M2": {"name": "Meio — Clarinetes Congregacional", "category": "meio", "instruments": [
        {"voice": "Soprano",   "name": "Clarinete 1",  "program": 71, "vol": 82},
        {"voice": "Soprano",   "name": "Clarinete 2",  "program": 71, "vol": 78},
        {"voice": "Soprano",   "name": "Flauta",       "program": 73, "vol": 72},
        {"voice": "Contralto", "name": "Sax Alto",     "program": 65, "vol": 78},
        {"voice": "Contralto", "name": "Trompa",       "program": 60, "vol": 72},
        {"voice": "Tenor",     "name": "Sax Tenor",    "program": 66, "vol": 80},
        {"voice": "Tenor",     "name": "Bombardino",   "program": 61, "vol": 75},
        {"voice": "Baixo",     "name": "Tuba",         "program": 58, "vol": 82},
        {"voice": "Baixo",     "name": "Fagote",       "program": 70, "vol": 75},
    ]},
    "M3": {"name": "Meio — Reforço de Metais", "category": "meio", "instruments": [
        {"voice": "Soprano",   "name": "Trompete 1",   "program": 56, "vol": 85},
        {"voice": "Soprano",   "name": "Violino 1",    "program": 40, "vol": 75},
        {"voice": "Contralto", "name": "Trompa 1",     "program": 60, "vol": 80},
        {"voice": "Contralto", "name": "Sax Alto",     "program": 65, "vol": 75},
        {"voice": "Tenor",     "name": "Trombone",     "program": 57, "vol": 82},
        {"voice": "Tenor",     "name": "Bombardino",   "program": 61, "vol": 78},
        {"voice": "Baixo",     "name": "Tuba",         "program": 58, "vol": 88},
        {"voice": "Baixo",     "name": "Trombone Baixo","program": 57, "vol": 82},
        {"voice": "Baixo",     "name": "Contrabaixo",  "program": 43, "vol": 80},
    ]},
    "M4": {"name": "Meio — Resposta Cordas e Sopros", "category": "meio", "instruments": [
        {"voice": "Soprano",   "name": "Violino 1",    "program": 40, "vol": 80},
        {"voice": "Soprano",   "name": "Flauta",       "program": 73, "vol": 75},
        {"voice": "Contralto", "name": "Viola",        "program": 41, "vol": 75},
        {"voice": "Contralto", "name": "Clarinete",    "program": 71, "vol": 72},
        {"voice": "Tenor",     "name": "Cello",        "program": 42, "vol": 78},
        {"voice": "Tenor",     "name": "Sax Tenor",    "program": 66, "vol": 74},
        {"voice": "Baixo",     "name": "Contrabaixo",  "program": 43, "vol": 80},
        {"voice": "Baixo",     "name": "Fagote",       "program": 70, "vol": 72},
    ]},
    "M5": {"name": "Meio — Textura Cheia (Tutti)", "category": "meio", "instruments": [
        {"voice": "Soprano",   "name": "Violino 1",    "program": 40, "vol": 82},
        {"voice": "Soprano",   "name": "Flauta",       "program": 73, "vol": 78},
        {"voice": "Soprano",   "name": "Clarinete",    "program": 71, "vol": 75},
        {"voice": "Soprano",   "name": "Trompete",     "program": 56, "vol": 80},
        {"voice": "Contralto", "name": "Viola",        "program": 41, "vol": 78},
        {"voice": "Contralto", "name": "Sax Alto",     "program": 65, "vol": 75},
        {"voice": "Contralto", "name": "Trompa",       "program": 60, "vol": 78},
        {"voice": "Tenor",     "name": "Cello",        "program": 42, "vol": 80},
        {"voice": "Tenor",     "name": "Sax Tenor",    "program": 66, "vol": 75},
        {"voice": "Tenor",     "name": "Trombone",     "program": 57, "vol": 80},
        {"voice": "Baixo",     "name": "Tuba",         "program": 58, "vol": 88},
        {"voice": "Baixo",     "name": "Contrabaixo",  "program": 43, "vol": 85},
    ]},
    "M6": {"name": "Meio — Redução Pré-Final", "category": "meio", "instruments": [
        {"voice": "Soprano",   "name": "Violino 1",    "program": 40, "vol": 72},
        {"voice": "Soprano",   "name": "Clarinete",    "program": 71, "vol": 70},
        {"voice": "Contralto", "name": "Viola",        "program": 41, "vol": 68},
        {"voice": "Contralto", "name": "Arpa",         "program": 46, "vol": 65},
        {"voice": "Tenor",     "name": "Cello",        "program": 42, "vol": 72},
        {"voice": "Baixo",     "name": "Contrabaixo",  "program": 43, "vol": 75},
    ]},
    "E1": {"name": "Encerramento — Tutti Completo", "category": "encerramento", "instruments": [
        {"voice": "Soprano",   "name": "Violino 1",    "program": 40, "vol": 85},
        {"voice": "Soprano",   "name": "Flauta",       "program": 73, "vol": 80},
        {"voice": "Soprano",   "name": "Clarinete",    "program": 71, "vol": 78},
        {"voice": "Soprano",   "name": "Trompete",     "program": 56, "vol": 88},
        {"voice": "Contralto", "name": "Viola",        "program": 41, "vol": 80},
        {"voice": "Contralto", "name": "Sax Alto",     "program": 65, "vol": 78},
        {"voice": "Contralto", "name": "Trompa",       "program": 60, "vol": 82},
        {"voice": "Tenor",     "name": "Cello",        "program": 42, "vol": 82},
        {"voice": "Tenor",     "name": "Trombone",     "program": 57, "vol": 85},
        {"voice": "Tenor",     "name": "Bombardino",   "program": 61, "vol": 78},
        {"voice": "Baixo",     "name": "Tuba",         "program": 58, "vol": 92},
        {"voice": "Baixo",     "name": "Contrabaixo",  "program": 43, "vol": 88},
    ]},
    "E2": {"name": "Encerramento — Metais Dominantes", "category": "encerramento", "instruments": [
        {"voice": "Soprano",   "name": "Trompete 1",   "program": 56, "vol": 90},
        {"voice": "Soprano",   "name": "Trompete 2",   "program": 56, "vol": 85},
        {"voice": "Soprano",   "name": "Clarinete",    "program": 71, "vol": 78},
        {"voice": "Contralto", "name": "Trompa 1",     "program": 60, "vol": 85},
        {"voice": "Contralto", "name": "Trompa 2",     "program": 60, "vol": 82},
        {"voice": "Tenor",     "name": "Trombone 1",   "program": 57, "vol": 88},
        {"voice": "Tenor",     "name": "Bombardino",   "program": 61, "vol": 82},
        {"voice": "Baixo",     "name": "Tuba 1",       "program": 58, "vol": 95},
        {"voice": "Baixo",     "name": "Tuba 2",       "program": 58, "vol": 90},
    ]},
    "E3": {"name": "Encerramento — Cordas Sustentadas", "category": "encerramento", "instruments": [
        {"voice": "Soprano",   "name": "Violino 1",    "program": 40, "vol": 88},
        {"voice": "Soprano",   "name": "Violino 2",    "program": 40, "vol": 85},
        {"voice": "Contralto", "name": "Viola 1",      "program": 41, "vol": 82},
        {"voice": "Contralto", "name": "Viola 2",      "program": 41, "vol": 78},
        {"voice": "Tenor",     "name": "Cello 1",      "program": 42, "vol": 85},
        {"voice": "Tenor",     "name": "Cello 2",      "program": 42, "vol": 80},
        {"voice": "Baixo",     "name": "Contrabaixo 1","program": 43, "vol": 90},
        {"voice": "Baixo",     "name": "Contrabaixo 2","program": 43, "vol": 85},
    ]},
    "E4": {"name": "Encerramento — Arpa / Pizzicato Final", "category": "encerramento", "instruments": [
        {"voice": "Soprano",   "name": "Flauta",       "program": 73, "vol": 75},
        {"voice": "Soprano",   "name": "Violino Solo", "program": 40, "vol": 72},
        {"voice": "Contralto", "name": "Arpa 1",       "program": 46, "vol": 78},
        {"voice": "Contralto", "name": "Viola",        "program": 41, "vol": 68},
        {"voice": "Tenor",     "name": "Cello",        "program": 42, "vol": 72},
        {"voice": "Baixo",     "name": "Arpa Grave",   "program": 46, "vol": 70},
        {"voice": "Baixo",     "name": "Contrabaixo",  "program": 43, "vol": 72},
    ]},
    "E5": {"name": "Encerramento — Acorde com Suspensão", "category": "encerramento", "instruments": [
        {"voice": "Soprano",   "name": "Trompete",     "program": 56, "vol": 88},
        {"voice": "Soprano",   "name": "Violino 1",    "program": 40, "vol": 82},
        {"voice": "Soprano",   "name": "Flauta",       "program": 73, "vol": 78},
        {"voice": "Contralto", "name": "Trompa",       "program": 60, "vol": 85},
        {"voice": "Contralto", "name": "Viola",        "program": 41, "vol": 78},
        {"voice": "Tenor",     "name": "Trombone",     "program": 57, "vol": 88},
        {"voice": "Tenor",     "name": "Cello",        "program": 42, "vol": 80},
        {"voice": "Baixo",     "name": "Tuba",         "program": 58, "vol": 95},
        {"voice": "Baixo",     "name": "Contrabaixo",  "program": 43, "vol": 90},
    ]},
}

ABERTURA_IDS     = [k for k, v in PRESETS.items() if v["category"] == "abertura"]
MEIO_IDS         = [k for k, v in PRESETS.items() if v["category"] == "meio"]
ENCERRAMENTO_IDS = [k for k, v in PRESETS.items() if v["category"] == "encerramento"]

# ──────────────────────────────────────────────────────────────────────────────
# Sorteio de Orquestração
# ──────────────────────────────────────────────────────────────────────────────

def assign_orchestration(n_phrases, n_abertura=2, n_encerramento=2):
    plan = []
    last = None

    def pick(pool):
        nonlocal last
        cands = [p for p in pool if p != last] or pool
        chosen = random.choice(cands)
        last = chosen
        return chosen

    for i in range(n_phrases):
        if i < n_abertura:
            plan.append(pick(ABERTURA_IDS))
        elif i >= n_phrases - n_encerramento:
            plan.append(pick(ENCERRAMENTO_IDS))
        else:
            plan.append(pick(MEIO_IDS))
    return plan

# ──────────────────────────────────────────────────────────────────────────────
# Construção do MIDI
# ──────────────────────────────────────────────────────────────────────────────

def build_orchestrated_midi(mid, phrases, orchestration_plan, speed=0.85):
    tempo_orig = get_tempo(mid)
    tempo_new  = int(tempo_orig / speed)
    tpb        = mid.ticks_per_beat

    channel_to_voice = detect_satb_channels(mid)
    voice_to_notes   = extract_voice_notes(mid, channel_to_voice)

    new_mid = mido.MidiFile()
    new_mid.ticks_per_beat = tpb

    # Meta track
    meta = mido.MidiTrack()
    new_mid.tracks.append(meta)
    for track in mid.tracks:
        for msg in track:
            if msg.is_meta and msg.type in ['time_signature', 'key_signature']:
                meta.append(msg.copy())
    meta.append(mido.MetaMessage('set_tempo', tempo=tempo_new, time=0))

    # Acumula todos os eventos em tempo absoluto
    all_events = []
    ch_counter = 0

    # Canal 9 (GM) é reservado para percussão — nunca usado em orquestra
    MELODIC_CHANNELS = [ch for ch in range(16) if ch != 9]  # 15 canais melódicos disponíveis

    voice_pan = {
        "Soprano":   (30, 62),
        "Contralto": (50, 78),
        "Tenor":     (52, 82),
        "Baixo":     (58, 90),
    }

    for phrase_idx, (phrase_start, phrase_end) in enumerate(phrases):
        preset = PRESETS[orchestration_plan[phrase_idx]]

        # Delay único por frase (deslocamento da frase inteira)
        phrase_delay = seconds_to_ticks(random.uniform(0.003, 0.015), tempo_new, tpb)

        for inst in preset["instruments"]:
            voice   = inst["voice"]
            program = inst["program"]
            vol     = inst["vol"]
            pan_lo, pan_hi = voice_pan.get(voice, (40, 88))
            pan     = random.randint(pan_lo, pan_hi)
            midi_ch = MELODIC_CHANNELS[ch_counter % len(MELODIC_CHANNELS)]
            ch_counter += 1

            # Micro-delay de 5–25 ms por instrumento (humanização de ataque)
            inst_delay = seconds_to_ticks(random.uniform(0.005, 0.025), tempo_new, tpb)
            total_delay = phrase_delay + inst_delay

            notes = [
                (note, on_t, off_t, vel)
                for note, on_t, off_t, vel in voice_to_notes.get(voice, [])
                if phrase_start <= on_t < phrase_end
            ]
            if not notes:
                continue

            # Setup do canal
            all_events += [
                mido.Message('program_change', channel=midi_ch, program=program, time=0),
                mido.Message('control_change', channel=midi_ch, control=10, value=pan, time=0),
                mido.Message('control_change', channel=midi_ch, control=7,  value=vol, time=0),
                mido.Message('control_change', channel=midi_ch, control=11, value=127, time=0),
            ]

            for i, (note, on_t, off_t, vel) in enumerate(notes):
                dur = remove_staccato(off_t - on_t, tpb)

                is_after_pause  = (i == 0) or (on_t - notes[i-1][2] >= tpb * 0.25)
                is_before_pause = (i < len(notes)-1) and (notes[i+1][1] - off_t >= tpb * 0.25)

                if is_before_pause:
                    dur = int(dur * 0.70)

                on_new  = on_t + total_delay
                off_new = on_new + max(15, dur)
                v_note  = 10 if is_after_pause else min(127, max(1, vel))

                all_events.append(mido.Message('note_on',  channel=midi_ch, note=note,
                                               velocity=v_note, time=on_new))
                all_events.append(mido.Message('note_off', channel=midi_ch, note=note,
                                               velocity=0, time=off_new))

                if is_after_pause:
                    ramp = int(tpb * 0.5)
                    for step in range(5):
                        t_cc = on_new + int((step / 4) * ramp)
                        val  = int(40 + (step / 4) * 60)
                        all_events.append(mido.Message('control_change', channel=midi_ch,
                                                        control=11, value=val, time=t_cc))

    # Ordena e converte para delta-times
    setup = [m for m in all_events if m.time == 0]
    music = sorted([m for m in all_events if m.time > 0], key=lambda m: m.time)

    note_track = mido.MidiTrack()
    new_mid.tracks.append(note_track)
    prev = 0
    for msg in setup + music:
        note_track.append(msg.copy(time=msg.time - prev))
        prev = msg.time

    return new_mid

# ──────────────────────────────────────────────────────────────────────────────
# Exportação e Geração de Variações
# ──────────────────────────────────────────────────────────────────────────────

def generate_explanations(out_dir, orchestration_plan):
    filename = unicodedata.normalize('NFC', "explicação.md")
    lines = [
        "# Explicação da Variação — Orquestração por Frase\n\n",
        "**Velocidade:** 85% do andamento original.\n\n",
        "| Frase | Categoria | Preset | Instrumentos |\n",
        "|---|---|---|---|\n",
    ]
    for i, pid in enumerate(orchestration_plan):
        p = PRESETS[pid]
        insts = ", ".join(inst["name"] for inst in p["instruments"])
        lines.append(f"| {i+1} | {p['category'].capitalize()} | {p['name']} | {insts} |\n")
    lines += [
        "\n## Humanização\n\n",
        "- Micro-delay por trilha: 5–25 ms aleatório por instrumento\n",
        "- Velocity inicial após pausa: 10 (CC11 ramp 40→100 em 250 ms)\n",
        "- Encurtamento pré-pausa: –30% da duração\n",
        "- Staccato removido: notas < 50% do beat → 85% do beat\n",
        "- Panning aleatório por instrumento (L/R por voz)\n",
    ]
    (out_dir / filename).write_text("".join(lines), encoding='utf-8')


def generate_variations(input_midi, output_dir, n_variacoes=10, letra_path=None, speed=0.70):
    mid     = mido.MidiFile(input_midi)
    tempo   = get_tempo(mid)
    base    = Path(input_midi).stem
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nDetectando frases em: {base}")
    bpm_orig = 60_000_000 // tempo
    bpm_new  = int(bpm_orig * speed)
    print(f"  Velocidade: {speed*100:.0f}% do original ({bpm_orig} BPM → {bpm_new} BPM)")

    phrases = detect_phrases(mid, tempo, min_phrase_seconds=8.0, silence_beats=0.4)

    if len(phrases) < 4:
        # Fallback: divide o MIDI em 4 partes iguais
        max_tick = max(sum(msg.time for msg in t) for t in mid.tracks)
        q = max_tick // 4
        phrases = [(i*q, (i+1)*q) for i in range(4)]

    n_phrases = len(phrases)
    print(f"  Frases detectadas: {n_phrases}")

    for var_num in range(1, n_variacoes + 1):
        label   = f"variacao_{var_num:02d}"
        var_dir = out_dir / label
        var_dir.mkdir(exist_ok=True)

        plan = assign_orchestration(
            n_phrases,
            n_abertura    = min(2, max(1, n_phrases // 4)),
            n_encerramento= min(2, max(1, n_phrases // 4)),
        )
        print(f"\n[{var_num}/{n_variacoes}] {label}: {' → '.join(plan)}")

        # MIDI
        new_mid  = build_orchestrated_midi(mid, phrases, plan, speed=speed)
        midi_out = var_dir / f"{base}.mid"
        new_mid.save(str(midi_out))

        # MP3
        mp3_out = var_dir / f"{base}.mp3"
        subprocess.run([MSCORE_BIN, "-o", str(mp3_out), str(midi_out)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Pós-processador de fade-in (se existir)
        pp = ROOT / "utils" / "postprocess_fade_apos_pausa.py"
        if pp.exists() and mp3_out.exists():
            subprocess.run([VENV_PYTHON, str(pp), "--input", str(mp3_out),
                            "--output", str(var_dir), "--suffix", "", "--lookback-ms", "200"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # MSCZ
        mscz_out = var_dir / f"{base}.mscz"
        subprocess.run([MSCORE_BIN, "-o", str(mscz_out), str(midi_out)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if mscz_out.exists():
            n_rm = remove_staccato_from_mscz(mscz_out)
            print(f"  Staccatos removidos do MSCZ: {n_rm}")

        # Resíduos MuseScore
        for f in ["automation.json", "audiosettings.json", "viewsettings.json"]:
            fp = var_dir / f
            if fp.exists():
                fp.unlink()
        for d in ["META-INF", "Thumbnails"]:
            dp = var_dir / d
            if dp.exists():
                shutil.rmtree(dp, ignore_errors=True)

        # JSON letra
        sync = ROOT / "utils" / "sincronizar_letras.py"
        json_out = var_dir / f"{base}.json"
        if sync.exists() and mp3_out.exists():
            subprocess.run([VENV_PYTHON, str(sync), "--hino", "C2",
                            "--mp3", str(mp3_out), "--output", str(json_out)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # letra.txt
        if letra_path and Path(letra_path).exists():
            shutil.copy(letra_path, var_dir / "letra.txt")

        # explicação.md
        generate_explanations(var_dir, plan)
        print(f"  ✓ {label} concluída!")

    print(f"\n{'='*60}")
    print(f"  {n_variacoes} VARIAÇÕES GERADAS!")
    print(f"  Salvas em: {out_dir}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Orquestrador Dinâmico por Frase")
    parser.add_argument("--midi",      required=True)
    parser.add_argument("--output",    required=True)
    parser.add_argument("--variacoes", type=int,   default=10)
    parser.add_argument("--speed",     type=float, default=0.70,
                        help="Fator de velocidade (0.70 = 70%% do andamento original, default: 0.70)")
    parser.add_argument("--letra",     default=None)
    args = parser.parse_args()

    generate_variations(
        input_midi  = args.midi,
        output_dir  = args.output,
        n_variacoes = args.variacoes,
        letra_path  = args.letra,
        speed       = args.speed,
    )
