import mido
import os
import random
import math
import argparse
import subprocess
import glob
import sys

# ─── Configurações e Presets de Cordas (16 Instrumentos - 4 por Voz) ───────────
# Instrumentos autorizados da lista Muse Strings:
# - "Violin 1 (Solo)" (program 40)
# - "Violin 2 (Solo)" (program 40)
# - "Viola (Solo)" (program 41)
# - "Violoncello (Solo)" (program 42)
# - "Violins 1" (program 40)
# - "Violins 2" (program 40)
# - "Violas" (program 41)
# - "Violoncellos" (program 42)
# - "Contrabasses" (program 43)

STRINGS_16PART_PRESETS = {
    1: {
        "name": "Sinfônica de Seção Completa",
        "desc": "Som orquestral clássico utilizando apenas cordas de seção seletiva",
        "map": {
            "Soprano_1":   {"name": "Violins 1",     "program": 40, "pan": 30},
            "Soprano_2":   {"name": "Violins 1",     "program": 40, "pan": 48},
            "Soprano_3":   {"name": "Violins 2",     "program": 40, "pan": 80},
            "Soprano_4":   {"name": "Violins 2",     "program": 40, "pan": 98},
            
            "Contralto_1": {"name": "Violas",        "program": 41, "pan": 34},
            "Contralto_2": {"name": "Violas",        "program": 41, "pan": 52},
            "Contralto_3": {"name": "Violas",        "program": 41, "pan": 76},
            "Contralto_4": {"name": "Violas",        "program": 41, "pan": 94},
            
            "Tenor_1":     {"name": "Violoncellos",  "program": 42, "pan": 38},
            "Tenor_2":     {"name": "Violoncellos",  "program": 42, "pan": 56},
            "Tenor_3":     {"name": "Violoncellos",  "program": 42, "pan": 72},
            "Tenor_4":     {"name": "Violoncellos",  "program": 42, "pan": 90},
            
            "Baixo_1":     {"name": "Contrabasses",  "program": 43, "pan": 42},
            "Baixo_2":     {"name": "Contrabasses",  "program": 43, "pan": 60},
            "Baixo_3":     {"name": "Contrabasses",  "program": 43, "pan": 68},
            "Baixo_4":     {"name": "Contrabasses",  "program": 43, "pan": 86}
        }
    },
    2: {
        "name": "Octeto Solista Dobrado",
        "desc": "Som de câmara aveludado e intimista utilizando apenas as cordas solo (e contrabaixos na base)",
        "map": {
            "Soprano_1":   {"name": "Violin 1 (Solo)", "program": 40, "pan": 30},
            "Soprano_2":   {"name": "Violin 1 (Solo)", "program": 40, "pan": 48},
            "Soprano_3":   {"name": "Violin 2 (Solo)", "program": 40, "pan": 80},
            "Soprano_4":   {"name": "Violin 2 (Solo)", "program": 40, "pan": 98},
            
            "Contralto_1": {"name": "Viola (Solo)",    "program": 41, "pan": 34},
            "Contralto_2": {"name": "Viola (Solo)",    "program": 41, "pan": 52},
            "Contralto_3": {"name": "Viola (Solo)",    "program": 41, "pan": 76},
            "Contralto_4": {"name": "Viola (Solo)",    "program": 41, "pan": 94},
            
            "Tenor_1":     {"name": "Violoncello (Solo)", "program": 42, "pan": 38},
            "Tenor_2":     {"name": "Violoncello (Solo)", "program": 42, "pan": 56},
            "Tenor_3":     {"name": "Violoncello (Solo)", "program": 42, "pan": 72},
            "Tenor_4":     {"name": "Violoncello (Solo)", "program": 42, "pan": 90},
            
            "Baixo_1":     {"name": "Contrabasses",    "program": 43, "pan": 42},
            "Baixo_2":     {"name": "Contrabasses",    "program": 43, "pan": 60},
            "Baixo_3":     {"name": "Contrabasses",    "program": 43, "pan": 68},
            "Baixo_4":     {"name": "Contrabasses",    "program": 43, "pan": 86}
        }
    },
    3: {
        "name": "Híbrido Seção e Solo",
        "desc": "Ataque claro de solistas misturado com a densidade acústica de seções completas",
        "map": {
            "Soprano_1":   {"name": "Violins 1",       "program": 40, "pan": 30},
            "Soprano_2":   {"name": "Violin 1 (Solo)", "program": 40, "pan": 48},
            "Soprano_3":   {"name": "Violins 2",       "program": 40, "pan": 80},
            "Soprano_4":   {"name": "Violin 2 (Solo)", "program": 40, "pan": 98},
            
            "Contralto_1": {"name": "Violas",          "program": 41, "pan": 34},
            "Contralto_2": {"name": "Viola (Solo)",    "program": 41, "pan": 52},
            "Contralto_3": {"name": "Violas",          "program": 41, "pan": 76},
            "Contralto_4": {"name": "Viola (Solo)",    "program": 41, "pan": 94},
            
            "Tenor_1":     {"name": "Violoncellos",    "program": 42, "pan": 38},
            "Tenor_2":     {"name": "Violoncello (Solo)", "program": 42, "pan": 56},
            "Tenor_3":     {"name": "Violoncellos",    "program": 42, "pan": 72},
            "Tenor_4":     {"name": "Violoncello (Solo)", "program": 42, "pan": 90},
            
            "Baixo_1":     {"name": "Contrabasses",    "program": 43, "pan": 42},
            "Baixo_2":     {"name": "Contrabasses",    "program": 43, "pan": 60},
            "Baixo_3":     {"name": "Contrabasses",    "program": 43, "pan": 68},
            "Baixo_4":     {"name": "Contrabasses",    "program": 43, "pan": 86}
        }
    },
    4: {
        "name": "Concerto Chamber Misto",
        "desc": "Foco solista nas primeiras dobras e seção completa nas dobras secundárias",
        "map": {
            "Soprano_1":   {"name": "Violin 1 (Solo)", "program": 40, "pan": 30},
            "Soprano_2":   {"name": "Violins 1",       "program": 40, "pan": 48},
            "Soprano_3":   {"name": "Violins 2",       "program": 40, "pan": 80},
            "Soprano_4":   {"name": "Violins 2",       "program": 40, "pan": 98},
            
            "Contralto_1": {"name": "Viola (Solo)",    "program": 41, "pan": 34},
            "Contralto_2": {"name": "Violas",          "program": 41, "pan": 52},
            "Contralto_3": {"name": "Violas",          "program": 41, "pan": 76},
            "Contralto_4": {"name": "Violas",          "program": 41, "pan": 94},
            
            "Tenor_1":     {"name": "Violoncello (Solo)", "program": 42, "pan": 38},
            "Tenor_2":     {"name": "Violoncellos",    "program": 42, "pan": 56},
            "Tenor_3":     {"name": "Violoncellos",    "program": 42, "pan": 72},
            "Tenor_4":     {"name": "Violoncellos",    "program": 42, "pan": 90},
            
            "Baixo_1":     {"name": "Contrabasses",    "program": 43, "pan": 42},
            "Baixo_2":     {"name": "Contrabasses",    "program": 43, "pan": 60},
            "Baixo_3":     {"name": "Contrabasses",    "program": 43, "pan": 68},
            "Baixo_4":     {"name": "Contrabasses",    "program": 43, "pan": 86}
        }
    },
    5: {
        "name": "Orquestra de Cordas Aprovada",
        "desc": "Preset customizado utilizando exclusivamente os 9 instrumentos de cordas validados nos testes de áudio",
        "map": {
            "Soprano_1":   {"name": "Violins 1",       "program": 40, "pan": 30},
            "Soprano_2":   {"name": "Violin 1 (Solo)", "program": 40, "pan": 48},
            "Soprano_3":   {"name": "Violin 2 (Solo)", "program": 40, "pan": 80},
            "Soprano_4":   {"name": "Violins 2",       "program": 40, "pan": 98},
            
            "Contralto_1": {"name": "Violas",          "program": 41, "pan": 34},
            "Contralto_2": {"name": "Viola (Solo)",    "program": 41, "pan": 52},
            "Contralto_3": {"name": "Viola (Solo)",    "program": 41, "pan": 76},
            "Contralto_4": {"name": "Violas",          "program": 41, "pan": 94},
            
            "Tenor_1":     {"name": "Violoncellos",    "program": 42, "pan": 38},
            "Tenor_2":     {"name": "Violoncello (Solo)", "program": 42, "pan": 56},
            "Tenor_3":     {"name": "Violoncello (Solo)", "program": 42, "pan": 72},
            "Tenor_4":     {"name": "Violoncellos",    "program": 42, "pan": 90},
            
            "Baixo_1":     {"name": "Contrabasses",    "program": 43, "pan": 42},
            "Baixo_2":     {"name": "Violoncellos",    "program": 42, "pan": 60},
            "Baixo_3":     {"name": "Violoncello (Solo)", "program": 42, "pan": 68},
            "Baixo_4":     {"name": "Contrabasses",    "program": 43, "pan": 86}
        }
    },
    6: {
        "name": "Pizzicato Total Ensemble",
        "desc": "Textura totalmente dedilhada (pizzicato) para as 16 partes, gerando um som leve e rítmico",
        "map": {
            "Soprano_1":   {"name": "Pizzicato Strings", "program": 45, "pan": 30},
            "Soprano_2":   {"name": "Pizzicato Strings", "program": 45, "pan": 48},
            "Soprano_3":   {"name": "Pizzicato Strings", "program": 45, "pan": 80},
            "Soprano_4":   {"name": "Pizzicato Strings", "program": 45, "pan": 98},
            
            "Contralto_1": {"name": "Pizzicato Strings", "program": 45, "pan": 34},
            "Contralto_2": {"name": "Pizzicato Strings", "program": 45, "pan": 52},
            "Contralto_3": {"name": "Pizzicato Strings", "program": 45, "pan": 76},
            "Contralto_4": {"name": "Pizzicato Strings", "program": 45, "pan": 94},
            
            "Tenor_1":     {"name": "Pizzicato Strings", "program": 45, "pan": 38},
            "Tenor_2":     {"name": "Pizzicato Strings", "program": 45, "pan": 56},
            "Tenor_3":     {"name": "Pizzicato Strings", "program": 45, "pan": 72},
            "Tenor_4":     {"name": "Pizzicato Strings", "program": 45, "pan": 90},
            
            "Baixo_1":     {"name": "Pizzicato Strings", "program": 45, "pan": 42},
            "Baixo_2":     {"name": "Pizzicato Strings", "program": 45, "pan": 60},
            "Baixo_3":     {"name": "Pizzicato Strings", "program": 45, "pan": 68},
            "Baixo_4":     {"name": "Pizzicato Strings", "program": 45, "pan": 86}
        }
    },
    7: {
        "name": "Cinematic Tremolo Ensemble",
        "desc": "Textura contínua de tremolo em todas as 16 partes, gerando tensão dramática e suspense",
        "map": {
            "Soprano_1":   {"name": "Tremolo Strings",   "program": 44, "pan": 30},
            "Soprano_2":   {"name": "Tremolo Strings",   "program": 44, "pan": 48},
            "Soprano_3":   {"name": "Tremolo Strings",   "program": 44, "pan": 80},
            "Soprano_4":   {"name": "Tremolo Strings",   "program": 44, "pan": 98},
            
            "Contralto_1": {"name": "Tremolo Strings",   "program": 44, "pan": 34},
            "Contralto_2": {"name": "Tremolo Strings",   "program": 44, "pan": 52},
            "Contralto_3": {"name": "Tremolo Strings",   "program": 44, "pan": 76},
            "Contralto_4": {"name": "Tremolo Strings",   "program": 44, "pan": 94},
            
            "Tenor_1":     {"name": "Tremolo Strings",   "program": 44, "pan": 38},
            "Tenor_2":     {"name": "Tremolo Strings",   "program": 44, "pan": 56},
            "Tenor_3":     {"name": "Tremolo Strings",   "program": 44, "pan": 72},
            "Tenor_4":     {"name": "Tremolo Strings",   "program": 44, "pan": 90},
            
            "Baixo_1":     {"name": "Tremolo Strings",   "program": 44, "pan": 42},
            "Baixo_2":     {"name": "Tremolo Strings",   "program": 44, "pan": 60},
            "Baixo_3":     {"name": "Tremolo Strings",   "program": 44, "pan": 68},
            "Baixo_4":     {"name": "Tremolo Strings",   "program": 44, "pan": 86}
        }
    },
    8: {
        "name": "Arpa e Cordas de Câmara",
        "desc": "Lírico e etéreo - Harpas dedilhando o Soprano e Solistas legatos na sustentação da base",
        "map": {
            "Soprano_1":   {"name": "Harp",              "program": 46, "pan": 30},
            "Soprano_2":   {"name": "Harp",              "program": 46, "pan": 48},
            "Soprano_3":   {"name": "Harp",              "program": 46, "pan": 80},
            "Soprano_4":   {"name": "Harp",              "program": 46, "pan": 98},
            
            "Contralto_1": {"name": "Viola (Solo)",      "program": 41, "pan": 34},
            "Contralto_2": {"name": "Viola (Solo)",      "program": 41, "pan": 52},
            "Contralto_3": {"name": "Viola (Solo)",      "program": 41, "pan": 76},
            "Contralto_4": {"name": "Viola (Solo)",      "program": 41, "pan": 94},
            
            "Tenor_1":     {"name": "Violoncello (Solo)", "program": 42, "pan": 38},
            "Tenor_2":     {"name": "Violoncello (Solo)", "program": 42, "pan": 56},
            "Tenor_3":     {"name": "Violoncello (Solo)", "program": 42, "pan": 72},
            "Tenor_4":     {"name": "Violoncello (Solo)", "program": 42, "pan": 90},
            
            "Baixo_1":     {"name": "Contrabasses",      "program": 43, "pan": 42},
            "Baixo_2":     {"name": "Violoncello (Solo)", "program": 42, "pan": 60},
            "Baixo_3":     {"name": "Violoncello (Solo)", "program": 42, "pan": 68},
            "Baixo_4":     {"name": "Contrabasses",      "program": 43, "pan": 86}
        }
    },
    9: {
        "name": "Contraste Estéreo (Solo vs Seção)",
        "desc": "Lado esquerdo (pan < 64) com solistas e lado direito (pan > 64) com seções sinfônicas completas",
        "map": {
            "Soprano_1":   {"name": "Violin 1 (Solo)",   "program": 40, "pan": 30},
            "Soprano_2":   {"name": "Violin 1 (Solo)",   "program": 40, "pan": 48},
            "Soprano_3":   {"name": "Violins 2",         "program": 40, "pan": 80},
            "Soprano_4":   {"name": "Violins 2",         "program": 40, "pan": 98},
            
            "Contralto_1": {"name": "Viola (Solo)",      "program": 41, "pan": 34},
            "Contralto_2": {"name": "Viola (Solo)",      "program": 41, "pan": 52},
            "Contralto_3": {"name": "Violas",            "program": 41, "pan": 76},
            "Contralto_4": {"name": "Violas",            "program": 41, "pan": 94},
            
            "Tenor_1":     {"name": "Violoncello (Solo)", "program": 42, "pan": 38},
            "Tenor_2":     {"name": "Violoncello (Solo)", "program": 42, "pan": 56},
            "Tenor_3":     {"name": "Violoncellos",      "program": 42, "pan": 72},
            "Tenor_4":     {"name": "Violoncellos",      "program": 42, "pan": 90},
            
            "Baixo_1":     {"name": "Contrabasses",      "program": 43, "pan": 42},
            "Baixo_2":     {"name": "Contrabasses",      "program": 43, "pan": 60},
            "Baixo_3":     {"name": "Contrabasses",      "program": 43, "pan": 68},
            "Baixo_4":     {"name": "Contrabasses",      "program": 43, "pan": 86}
        }
    }
}

EXPR_BASE_VOLUME = 70
EXPR_AMPLITUDE   = 35
SAMPLING_STEP_TICKS = 40
EXPR_CONTROL = 1

# Coeficientes de normalização de volume para balancear timbres da biblioteca Muse Sounds
VOLUME_MODIFIERS = {
    "Violins 1": 1.0,
    "Violins 2": 1.0,
    "Violin 1 (Solo)": 1.0,
    "Violin 2 (Solo)": 1.0,
    "Violas": 0.68,
    "Viola (Solo)": 0.68,
    "Violoncellos": 0.74,
    "Violoncello (Solo)": 0.74,
    "Contrabasses": 0.44,
    "Pizzicato Strings": 1.23,
    "Tremolo Strings": 1.23,
    "Harp": 1.93
}

def seconds_to_ticks(seconds, tempo, ticks_per_beat):
    ticks_per_sec = ticks_per_beat * (1000000.0 / tempo)
    return int(seconds * ticks_per_sec)

def ticks_to_seconds(ticks, tempo, ticks_per_beat):
    ticks_per_sec = ticks_per_beat * (1000000.0 / tempo)
    return ticks / ticks_per_sec

def get_msg_priority(msg):
    if msg.is_meta:
        return 0
    if msg.type == 'program_change':
        return 1
    if msg.type == 'control_change':
        return 2
    if msg.type == 'note_off':
        return 3
    if msg.type == 'note_on':
        if hasattr(msg, 'velocity') and msg.velocity == 0:
            return 3
        return 4
    return 5

def get_cc_sample_ticks(duration, tempo, ticks_per_beat, is_after_pause):
    steps = set()
    steps.add(0)
    steps.add(duration)
    
    if is_after_pause:
        # High resolution sampling (every 10ms) inside the fade-in window (fixed 250ms)
        fade_win_ms = 250.0
        fade_win_ticks = int(seconds_to_ticks(fade_win_ms / 1000.0, tempo, ticks_per_beat))
        
        # 10ms in ticks
        step_ticks = max(1, int(seconds_to_ticks(0.010, tempo, ticks_per_beat)))
        
        t = 0
        while t < fade_win_ticks and t <= duration:
            steps.add(t)
            t += step_ticks
        # Add the end of the fade window
        if fade_win_ticks <= duration:
            steps.add(fade_win_ticks)
            
        # Standard sampling for the remainder of the note
        t = fade_win_ticks
        while t < duration:
            steps.add(t)
            t += SAMPLING_STEP_TICKS
    else:
        # Standard sampling for the whole note
        t = 0
        while t < duration:
            steps.add(t)
            t += SAMPLING_STEP_TICKS
            
    return sorted(list(steps))


def process_midi_to_16part_math(input_path, output_path, mapping, use_expression=True, speed=1.0):
    mid = mido.MidiFile(input_path)
    ticks_per_beat = mid.ticks_per_beat
    
    # Detectar canais originais do MIDI SATB
    active_channels = set()
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'note_on' and msg.velocity > 0:
                active_channels.add(msg.channel)
    sorted_channels = sorted(list(active_channels))
    
    voices = ["Soprano", "Contralto", "Tenor", "Baixo"]
    channel_to_voice = {sorted_channels[i]: voices[i] for i in range(min(len(sorted_channels), len(voices)))}
    
    # Detecta a fórmula de compasso e tempo
    numerator = 4
    measure_ticks = 4 * ticks_per_beat
    tempo = 500000
    
    # Varre por tempo e time signature
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'time_signature':
                if msg.numerator > 1:
                    numerator = msg.numerator
                    measure_ticks = numerator * ticks_per_beat
            elif msg.type == 'set_tempo':
                tempo = msg.tempo
                
    # Configurações de fraseado e versos para o hino 002 ou detecção dinâmica
    if "002" in os.path.basename(input_path):
        intro_end = 4320
        verse_len = 15840
        last_verse_start = 36000
    else:
        # Fallback para outros arquivos baseando-se no tempo total
        max_on_time = 0
        for track in mid.tracks:
            curr_time = 0
            for msg in track:
                curr_time += msg.time
                if msg.type == 'note_on' and msg.velocity > 0:
                    if curr_time > max_on_time:
                        max_on_time = curr_time
        if max_on_time < 10000:
            intro_end = 0
            verse_len = max_on_time // 3
            last_verse_start = verse_len * 2
        else:
            intro_end = int(max_on_time * 0.08) # ~8% de intro
            verse_len = (max_on_time - intro_end) // 3
            last_verse_start = intro_end + verse_len * 2
                
    new_mid = mido.MidiFile()
    new_mid.ticks_per_beat = ticks_per_beat
    
    # Trilha de metadados
    meta_track = mido.MidiTrack()
    new_mid.tracks.append(meta_track)
    
    abs_meta_events = []
    for track in mid.tracks:
        curr_time = 0
        for msg in track:
            curr_time += msg.time
            if msg.is_meta and msg.type in ['set_tempo', 'time_signature', 'key_signature']:
                msg_copy = msg.copy(time=curr_time)
                if msg_copy.type == 'set_tempo' and speed != 1.0:
                    msg_copy.tempo = int(msg_copy.tempo / speed)
                abs_meta_events.append(msg_copy)
                
    prev_meta_time = 0
    for msg in sorted(abs_meta_events, key=lambda x: x.time):
        delta = msg.time - prev_meta_time
        meta_track.append(msg.copy(time=delta))
        prev_meta_time = msg.time
                
    # Define a lista linear dos 16 instrumentos baseados nas sub-partes
    instruments_config = []
    sub_keys = {
        "Soprano":   ["Soprano_1", "Soprano_2", "Soprano_3", "Soprano_4"],
        "Contralto": ["Contralto_1", "Contralto_2", "Contralto_3", "Contralto_4"],
        "Tenor":     ["Tenor_1", "Tenor_2", "Tenor_3", "Tenor_4"],
        "Baixo":     ["Baixo_1", "Baixo_2", "Baixo_3", "Baixo_4"]
    }
    
    channels_map = [
        0, 1, 2, 3,       # Soprano 1, 2, 3, 4
        4, 5, 6, 7,       # Contralto 1, 2, 3, 4
        8, 10, 11, 12,    # Tenor 1, 2, 3, 4 (pula canal 9)
        13, 14, 15, 13    # Baixo 1, 2, 3, 4 (Baixo 4 compartilha canal 13 com Baixo 1)
    ]
    
    idx = 0
    for voice_name in voices:
        for sub_key in sub_keys[voice_name]:
            inst_def = mapping[sub_key]
            midi_ch = channels_map[idx]
            # Se for o canal compartilhado 13 (Contrabaixos), centraliza o pan
            pan_val = 64 if midi_ch == 13 else inst_def["pan"]
            instruments_config.append({
                "voice": voice_name,
                "sub_key": sub_key,
                "channel": midi_ch,
                "pan": pan_val,
                "inst": inst_def
            })
            idx += 1
            
    # Processa cada um dos 16 instrumentos para canais MIDI 0 a 15
    for conf in instruments_config:
        voice_track = mido.MidiTrack()
        new_mid.tracks.append(voice_track)
        
        voice_name = conf["voice"]
        midi_channel = conf["channel"]
        inst = conf["inst"]
        
        voice_track.append(mido.MetaMessage('track_name', name=inst["name"], time=0))
        voice_track.append(mido.Message('program_change', channel=midi_channel, program=inst["program"], time=0))
        voice_track.append(mido.Message('control_change', channel=midi_channel, control=10, value=conf["pan"], time=0))
        
        target_channel = None
        for ch, v in channel_to_voice.items():
            if v == voice_name:
                target_channel = ch
                break
                
        if target_channel is None:
            continue
            
        for track in mid.tracks:
            has_channel_msgs = any(not msg.is_meta and hasattr(msg, 'channel') and msg.channel == target_channel for msg in track)
            if not has_channel_msgs:
                continue
                
            initialized_channels = {midi_channel}
            abs_events = []
            curr_time = 0
            for msg in track:
                curr_time += msg.time
                if not msg.is_meta and hasattr(msg, 'channel') and msg.channel == target_channel:
                    abs_events.append(msg.copy(time=curr_time))
                    
            notes = []
            active_notes = {}
            for msg in abs_events:
                if msg.type == 'note_on' and msg.velocity > 0:
                    active_notes[msg.note] = (msg.time, msg.velocity)
                elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                    if msg.note in active_notes:
                        on_time, vel = active_notes.pop(msg.note)
                        notes.append({
                            "note": msg.note,
                            "on_time": on_time,
                            "off_time": msg.time,
                            "velocity": vel
                        })
            
            processed_abs_events = []
            
            # Duplica os metadados de tempo na trilha de notas
            for meta_msg in abs_meta_events:
                processed_abs_events.append(meta_msg.copy())
            
            # Ordena as notas por on_time original para garantir ordem cronológica
            notes.sort(key=lambda x: x["on_time"])
            
            # Passagem 1: Calcula delays, velocidades, e tempos iniciais
            for note_info in notes:
                on_time = note_info["on_time"]
                off_time = note_info["off_time"]
                v_base = note_info["velocity"]
                
                # 1. Timing delay
                if conf["sub_key"] == "Soprano_1":
                    delay_sec = 0.0
                else:
                    delay_sec = random.choice([0.0, 0.05, 0.1, 0.15])
                    
                delay_ticks = seconds_to_ticks(delay_sec, tempo, ticks_per_beat)
                
                note_info["on_time_new"] = max(0, on_time + delay_ticks)
                # A duração original deve ser preservada rigorosamente:
                duration_original = off_time - on_time
                # O novo off time acompanha o atraso, não cortando a nota prematuramente
                note_info["off_time_new"] = max(note_info["on_time_new"] + 10, note_info["on_time_new"] + duration_original)
                
                # 2. Velocity
                v_aleatorio = random.randint(-5, 5)
                pos_in_measure = note_info["on_time_new"] % measure_ticks
                if pos_in_measure < (ticks_per_beat * 0.1):
                    v_acento = 8
                else:
                    v_acento = -4
                v_novo = v_base + v_aleatorio + v_acento
                
                # Normalização de volume e fraseado
                mod = VOLUME_MODIFIERS.get(inst["name"], 1.0)
                phrase_idx = on_time // (4 * measure_ticks)
                nipes = ["Soprano", "Contralto", "Tenor", "Baixo"]
                destaque_nipe = nipes[phrase_idx % len(nipes)]
                phrase_mult = 1.15 if voice_name == destaque_nipe else 0.90
                
                note_info["total_mult"] = mod * phrase_mult
                note_info["v_final"] = max(1, min(127, int(v_novo * note_info["total_mult"])))
                note_info["phrase_idx"] = phrase_idx

            # Passagem 2: Correção de ordem cronológica dos inícios (on_time_new)
            for i in range(len(notes) - 1):
                curr_note = notes[i]
                next_note = notes[i+1]
                if next_note["on_time_new"] < curr_note["on_time_new"]:
                    # Ajusta o início da próxima nota para ser após a atual
                    next_note["on_time_new"] = curr_note["on_time_new"] + 10
                    # Ajusta o off_time_new correspondente
                    next_note["off_time_new"] = max(next_note["on_time_new"] + 10, next_note["off_time_new"])

            # Passagem 3: Prevenção de sobreposição consecutiva (corta o off_time_new da atual se invadir a próxima)
            for i in range(len(notes) - 1):
                curr_note = notes[i]
                next_note = notes[i+1]
                if curr_note["off_time_new"] > next_note["on_time_new"]:
                    curr_note["off_time_new"] = max(curr_note["on_time_new"] + 10, next_note["on_time_new"] - 10)

            # Passagem 4: Geração das mensagens MIDI finais
            for i, note_info in enumerate(notes):
                note_num = note_info["note"]
                on_time = note_info["on_time"]
                on_time_new = note_info["on_time_new"]
                off_time_new = note_info["off_time_new"]
                v_final = note_info["v_final"]
                total_mult = note_info["total_mult"]
                phrase_idx = note_info["phrase_idx"]
                duration = off_time_new - on_time_new
                
                # Identifica se é uma nota após pausa de pelo menos 0.2 tempos (ou início da faixa)
                is_after_pause = (i == 0) or (on_time - notes[i-1]["off_time"] >= ticks_per_beat * 0.2)
                
                v_final_note = v_final
                if is_after_pause:
                    v_final_note = 10
                
                note_on_msg = mido.Message('note_on', channel=midi_channel, note=note_num, velocity=v_final_note, time=on_time_new)
                note_off_msg = mido.Message('note_off', channel=midi_channel, note=note_num, velocity=0, time=off_time_new)
                
                processed_abs_events.append(note_on_msg)
                processed_abs_events.append(note_off_msg)
                
                # 4. Lógica avançada de duplicação de oitava (Violino no Soprano, Viola no Tenor)
                is_last_verse = (on_time >= last_verse_start)
                high_note_velocity = 0
                high_note_channel = midi_channel
                
                if voice_name == "Soprano":
                    if is_last_verse:
                        # Último verso: 50% na primeira metade, 75% na segunda metade. Pan esquerdo.
                        half_last_verse = last_verse_start + verse_len // 2
                        if on_time < half_last_verse:
                            high_note_velocity = int(v_final * 0.50)
                        else:
                            high_note_velocity = int(v_final * 0.75)
                        
                        # Roteia para canais do Soprano no lado esquerdo (0 e 1)
                        high_note_channel = 0 if conf["sub_key"] in ["Soprano_1", "Soprano_3"] else 1
                    else:
                        # Música inteira (Intro, Versos 1 e 2): 0% na primeira metade da frase, 50% na segunda metade
                        if on_time < intro_end:
                            is_second_half = (on_time >= (intro_end // 2))
                        else:
                            v_offset = (on_time - intro_end) % verse_len
                            # Cada verso padrão tem 4 frases
                            if v_offset < 3840:
                                is_second_half = (v_offset >= 1920)
                            elif v_offset < 7680:
                                is_second_half = (v_offset >= 5760)
                            elif v_offset < 11520:
                                is_second_half = (v_offset >= 9600)
                            else:
                                phrase4_len = verse_len - 11520
                                is_second_half = (v_offset >= (11520 + phrase4_len // 2))
                        
                        if is_second_half:
                            high_note_velocity = int(v_final * 0.50)
                            
                elif voice_name == "Tenor" and is_last_verse:
                    # Viola oitavada no Tenor apenas no último verso: 50% no início, 75% na metade. Pan direito.
                    half_last_verse = last_verse_start + verse_len // 2
                    if on_time < half_last_verse:
                        high_note_velocity = int(v_final * 0.50)
                    else:
                        high_note_velocity = int(v_final * 0.75)
                    
                    # Roteia para canais do Contralto no lado direito (6 e 7)
                    high_note_channel = 6 if conf["sub_key"] in ["Tenor_1", "Tenor_3"] else 7
                    
                if high_note_velocity > 0:
                    note_num_high = min(127, note_num + 12)
                    v_final_high = max(1, min(127, high_note_velocity))
                    if is_after_pause:
                        v_final_high = 10
                    
                    # Inicialização explícita do programa e do pan
                    if high_note_channel not in initialized_channels:
                        high_program = 40 if high_note_channel in [0, 1] else 41
                        high_pan = 30 if high_note_channel == 0 else (48 if high_note_channel == 1 else (76 if high_note_channel == 6 else 94))
                        
                        prog_msg = mido.Message('program_change', channel=high_note_channel, program=high_program, time=0)
                        pan_msg = mido.Message('control_change', channel=high_note_channel, control=10, value=high_pan, time=0)
                        
                        processed_abs_events.append(prog_msg)
                        processed_abs_events.append(pan_msg)
                        initialized_channels.add(high_note_channel)
                        
                    note_on_high = mido.Message('note_on', channel=high_note_channel, note=note_num_high, velocity=v_final_high, time=on_time_new)
                    note_off_high = mido.Message('note_off', channel=high_note_channel, note=note_num_high, velocity=0, time=off_time_new)
                    
                    processed_abs_events.append(note_on_high)
                    processed_abs_events.append(note_off_high)
                    
                # 3. Curva de volume (CC11)
                # Adiciona curva se a duração for suficiente ou se necessitar do fade-in após pausa
                if use_expression and (duration >= ticks_per_beat or is_after_pause):
                    sample_steps = get_cc_sample_ticks(duration, tempo, ticks_per_beat, is_after_pause)
                    for t_step in sample_steps:
                        factor = math.sin(math.pi * (t_step / duration)) if duration > 0 else 0
                        
                        # 1. Calcula o alvo final da onda senoide
                        target_e_val = (EXPR_BASE_VOLUME + EXPR_AMPLITUDE * factor) * total_mult
                        e_val = target_e_val
                        
                        # 2. Desvincula o ataque inicial da curva de porcentagem
                        if is_after_pause:
                            t_ms = ticks_to_seconds(t_step, tempo, ticks_per_beat) * 1000.0
                            if t_ms < 250.0:
                                e_val = target_e_val * (t_ms / 250.0)
                            if t_step == 0:
                                e_val = 1.0
                            
                        e_final = max(1, min(127, int(e_val)))
                        
                        cc_time = on_time_new + t_step
                        cc_msg = mido.Message(
                            'control_change', 
                            channel=midi_channel, 
                            control=EXPR_CONTROL, 
                            value=e_final, 
                            time=cc_time
                        )
                        processed_abs_events.append(cc_msg)
                        
                        # Se houver nota oitavada ativa em outro canal, envia a expressão para ela também!
                        if high_note_velocity > 0 and high_note_channel != midi_channel:
                            cc_high = mido.Message(
                                'control_change',
                                channel=high_note_channel,
                                control=EXPR_CONTROL,
                                value=e_final,
                                time=cc_time
                            )
                            processed_abs_events.append(cc_high)
                        
            processed_abs_events.sort(key=lambda x: (x.time, get_msg_priority(x)))
            
            rel_events = []
            prev_time = 0
            for msg in processed_abs_events:
                delta = msg.time - prev_time
                rel_events.append(msg.copy(time=delta))
                prev_time = msg.time
                
            for r_msg in rel_events:
                voice_track.append(r_msg)
                
    new_mid.save(output_path)

def render_score(midi_path, output_mp3, soundfonts_dir):
    my_env = os.environ.copy()
    my_env["MUSESAMPLER_INSTRUMENT_FOLDER"] = soundfonts_dir
    
    subprocess.run([
        "/Applications/MuseScore 4.app/Contents/MacOS/mscore",
        "-o", output_mp3,
        midi_path
    ], env=my_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main():
    ap = argparse.ArgumentParser(description="MuseScore 4 Math Orchestrator: Coral 16 Instrumentos")
    ap.add_argument("--midi",       default=None,           help="MIDI de entrada específico")
    ap.add_argument("--preset",     type=int, default=1,    help="Número do preset de 16 cordas (1 a 9)")
    ap.add_argument("--output",     default="output_strings_16part", help="Pasta de saída para os arquivos MP3")
    ap.add_argument("--soundfonts", default="/Users/jonaspoli/Documents/MuseScore4/SoundFonts/Muse Hub Instruments", 
                    help="Caminho para os instrumentos das Muse Sounds")
    ap.add_argument("--speed",       type=float, default=0.9, help="Fator de velocidade (padrão 0.9 = 90%% da velocidade original)")
    args = ap.parse_args()
    
    os.makedirs(args.output, exist_ok=True)
    
    if args.preset not in STRINGS_16PART_PRESETS:
        print(f"ERRO: Preset {args.preset} inválido. Escolha de 1 a 9.")
        sys.exit(1)
        
    preset = STRINGS_16PART_PRESETS[args.preset]
    print("════════════════════════════════════════════════════════════")
    print(f"  Orquestrador 16 Cordas — Preset {args.preset}: {preset['name']}")
    print(f"  Descrição: {preset['desc']}")
    print(f"  Velocidade: {args.speed}x (90%)")
    print("════════════════════════════════════════════════════════════\n")
    
    # Coleta arquivos MIDI
    midi_files = [args.midi] if args.midi else sorted(glob.glob("mid/*.mid"))
    total = len(midi_files)
    
    if total == 0:
        print("Nenhum arquivo MIDI encontrado em 'mid/'.")
        sys.exit(1)
        
    for idx, path in enumerate(midi_files, 1):
        name = os.path.splitext(os.path.basename(path))[0]
        out_mp3 = os.path.join(args.output, f"{name}_preset{args.preset}_16part_speed90.mp3")
        out_mid = os.path.join(args.output, f"{name}_preset{args.preset}_16part_speed90.mid")
        
        print(f"[{idx}/{total}] ▶ {name}...", end="", flush=True)
        
        try:
            process_midi_to_16part_math(path, out_mid, preset["map"], use_expression=True, speed=args.speed)
            
            render_score(out_mid, out_mp3, args.soundfonts)
            
            print(" ✓ concluído")
        except Exception as e:
            print(f" ✗ FALHOU (erro: {e})")
 
    print("\n✓ Processamento de 16 instrumentos concluído!")

if __name__ == "__main__":
    main()
