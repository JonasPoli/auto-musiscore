import mido
import os
import random
import math
import argparse
import subprocess
import glob
import sys
import zipfile
import json

# ─── Configurações e Presets de Metais (8 Partes) ─────────────────────────────
# 2 Sopranos, 2 Contraltos, 2 Tenores, 2 Baixos
# Panning: Lado 1 (Esquerda = 48), Lado 2 (Direita = 80)
BRASS_PRESETS = {
    1: {
        "name": "Sinfônica Real",
        "desc": "Equilíbrio e Contraste - Trumpet/Flugelhorn, French Horn, Trombone/Euphonium, Bass Trombone/Tuba",
        "map": {
            "Soprano_1":   {"name": "Trumpet",     "program": 56},
            "Soprano_2":   {"name": "Flugelhorn",  "program": 56},
            "Contralto_1": {"name": "French Horn", "program": 60},
            "Contralto_2": {"name": "French Horn", "program": 60},
            "Tenor_1":     {"name": "Trombone",    "program": 57},
            "Tenor_2":     {"name": "Euphonium",   "program": 57},
            "Baixo_1":     {"name": "Bass Trombone", "program": 57},
            "Baixo_2":     {"name": "Tuba",        "program": 58}
        }
    },
    2: {
        "name": "Mellow Brass",
        "desc": "Suave e Aveludada - Flugelhorn/Cornet, French Horn, Euphonium/Trombone, Tuba",
        "map": {
            "Soprano_1":   {"name": "Flugelhorn",  "program": 56},
            "Soprano_2":   {"name": "Cornet",      "program": 56},
            "Contralto_1": {"name": "French Horn", "program": 60},
            "Contralto_2": {"name": "French Horn", "program": 60},
            "Tenor_1":     {"name": "Euphonium",   "program": 57},
            "Tenor_2":     {"name": "Trombone",    "program": 57},
            "Baixo_1":     {"name": "Tuba",        "program": 58},
            "Baixo_2":     {"name": "Tuba",        "program": 58}
        }
    },
    3: {
        "name": "Fanfarra Imperial",
        "desc": "Brilhante e Majestosa - Trumpet duplos, French Horn, Trombone, Bass Trombone/Tuba",
        "map": {
            "Soprano_1":   {"name": "Trumpet",     "program": 56},
            "Soprano_2":   {"name": "Trumpet",     "program": 56},
            "Contralto_1": {"name": "Trumpet",     "program": 56},
            "Contralto_2": {"name": "French Horn", "program": 60},
            "Tenor_1":     {"name": "Trombone",    "program": 57},
            "Tenor_2":     {"name": "Trombone",    "program": 57},
            "Baixo_1":     {"name": "Bass Trombone", "program": 57},
            "Baixo_2":     {"name": "Tuba",        "program": 58}
        }
    },
    4: {
        "name": "Orquestra de Trompas e Trombones",
        "desc": "Som Denso e Macio - French Horn, Alto Horn, Trombone, Bass Trombone/Tuba",
        "map": {
            "Soprano_1":   {"name": "French Horn", "program": 60},
            "Soprano_2":   {"name": "French Horn", "program": 60},
            "Contralto_1": {"name": "French Horn", "program": 60},
            "Contralto_2": {"name": "Alto Horn",   "program": 60},
            "Tenor_1":     {"name": "Trombone",    "program": 57},
            "Tenor_2":     {"name": "Trombone",    "program": 57},
            "Baixo_1":     {"name": "Bass Trombone", "program": 57},
            "Baixo_2":     {"name": "Tuba",        "program": 58}
        }
    },
    5: {
        "name": "Catedral Antiga",
        "desc": "Metais Renascentistas (Sackbuts) - Cornet/Flugelhorn, French Horn, Trombone, Tuba",
        "map": {
            "Soprano_1":   {"name": "Cornet",      "program": 56},
            "Soprano_2":   {"name": "Flugelhorn",  "program": 56},
            "Contralto_1": {"name": "French Horn", "program": 60},
            "Contralto_2": {"name": "Alto Horn",   "program": 60},
            "Tenor_1":     {"name": "Trombone",    "program": 57},
            "Tenor_2":     {"name": "Trombone",    "program": 57},
            "Baixo_1":     {"name": "Tuba",        "program": 58},
            "Baixo_2":     {"name": "Bass Trombone", "program": 57}
        }
    },
    6: {
        "name": "Double Quartet Clássico",
        "desc": "Espelho Esquerda/Direita Perfeito - Trumpet, French Horn, Trombone, Tuba",
        "map": {
            "Soprano_1":   {"name": "Trumpet",     "program": 56},
            "Soprano_2":   {"name": "Trumpet",     "program": 56},
            "Contralto_1": {"name": "French Horn", "program": 60},
            "Contralto_2": {"name": "French Horn", "program": 60},
            "Tenor_1":     {"name": "Trombone",    "program": 57},
            "Tenor_2":     {"name": "Trombone",    "program": 57},
            "Baixo_1":     {"name": "Tuba",        "program": 58},
            "Baixo_2":     {"name": "Tuba",        "program": 58}
        }
    },
    7: {
        "name": "Metais Graves Modernos (Heavy Low Brass)",
        "desc": "Escuro e pesadíssimo - French Horn/Flugelhorn, Trombone/Euphonium, Tuba/VSL Bass Trombones",
        "map": {
            "Soprano_1":   {"name": "French Horn", "program": 60},
            "Soprano_2":   {"name": "Flugelhorn",  "program": 56},
            "Contralto_1": {"name": "French Horn", "program": 60},
            "Contralto_2": {"name": "Trombone",    "program": 57},
            "Tenor_1":     {"name": "Trombone",    "program": 57},
            "Tenor_2":     {"name": "Euphonium",   "program": 57},
            "Baixo_1":     {"name": "Tuba",        "program": 58},
            "Baixo_2":     {"name": "VSL Bass Trombones", "program": 57}
        }
    },
    8: {
        "name": "Quinteto Ampliado",
        "desc": "Brilhante e Espaçoso - Trumpet/Flugelhorn, Cornet/Horn, Trombone/Baritone, Tuba/Bass Trombone",
        "map": {
            "Soprano_1":   {"name": "Trumpet",     "program": 56},
            "Soprano_2":   {"name": "Flugelhorn",  "program": 56},
            "Contralto_1": {"name": "Cornet",      "program": 56},
            "Contralto_2": {"name": "French Horn", "program": 60},
            "Tenor_1":     {"name": "Trombone",    "program": 57},
            "Tenor_2":     {"name": "Baritone Horn", "program": 57},
            "Baixo_1":     {"name": "Tuba",        "program": 58},
            "Baixo_2":     {"name": "Bass Trombone", "program": 57}
        }
    },
    9: {
        "name": "Metais Curtos e Percussivos",
        "desc": "Foco em articulação staccato e seca - Cornet, Alto Horn, Baritone, Tuba",
        "map": {
            "Soprano_1":   {"name": "Cornet",      "program": 56},
            "Soprano_2":   {"name": "Cornet",      "program": 56},
            "Contralto_1": {"name": "Alto Horn",   "program": 60},
            "Contralto_2": {"name": "French Horn", "program": 60},
            "Tenor_1":     {"name": "Baritone Horn", "program": 57},
            "Tenor_2":     {"name": "Trombone",    "program": 57},
            "Baixo_1":     {"name": "Tuba",        "program": 58},
            "Baixo_2":     {"name": "Tuba",        "program": 58}
        }
    },
    10: {
        "name": "Romântica Alemã",
        "desc": "Ar encorpado com foco em Trompas e Eufônios - Flugelhorn, French Horn, Euphonium, Tuba/Bass Trombone",
        "map": {
            "Soprano_1":   {"name": "Flugelhorn",  "program": 56},
            "Soprano_2":   {"name": "Flugelhorn",  "program": 56},
            "Contralto_1": {"name": "French Horn", "program": 60},
            "Contralto_2": {"name": "French Horn", "program": 60},
            "Tenor_1":     {"name": "Euphonium",   "program": 57},
            "Tenor_2":     {"name": "Euphonium",   "program": 57},
            "Baixo_1":     {"name": "Tuba",        "program": 58},
            "Baixo_2":     {"name": "Bass Trombone", "program": 57}
        }
    },
    11: {
        "name": "Som Brilhante de Arena",
        "desc": "Grande destaque de agudos - Trumpet Lead, Flugelhorn/Horn, Trombone, Tuba/Bass Trombone",
        "map": {
            "Soprano_1":   {"name": "Trumpet",     "program": 56},
            "Soprano_2":   {"name": "Trumpet",     "program": 56},
            "Contralto_1": {"name": "Flugelhorn",  "program": 56},
            "Contralto_2": {"name": "French Horn", "program": 60},
            "Tenor_1":     {"name": "Trombone",    "program": 57},
            "Tenor_2":     {"name": "Trombone",    "program": 57},
            "Baixo_1":     {"name": "Tuba",        "program": 58},
            "Baixo_2":     {"name": "Bass Trombone", "program": 57}
        }
    },
    12: {
        "name": "Orquestra Escura",
        "desc": "Muito aveludado e som sombrio - Flugelhorn/Horn, Alto Horn, Trombone, Tuba/VSL Trombones",
        "map": {
            "Soprano_1":   {"name": "Flugelhorn",  "program": 56},
            "Soprano_2":   {"name": "French Horn", "program": 60},
            "Contralto_1": {"name": "French Horn", "program": 60},
            "Contralto_2": {"name": "Alto Horn",   "program": 60},
            "Tenor_1":     {"name": "Trombone",    "program": 57},
            "Tenor_2":     {"name": "Trombone",    "program": 57},
            "Baixo_1":     {"name": "Tuba",        "program": 58},
            "Baixo_2":     {"name": "VSL Bass Trombones", "program": 57}
        }
    },
    13: {
        "name": "Seção de Coros Alternados",
        "desc": "Som responsivo - Trumpet/Cornet, Horn/Alto, Euphonium/Trombone, Tuba/Bass Trombone",
        "map": {
            "Soprano_1":   {"name": "Trumpet",     "program": 56},
            "Soprano_2":   {"name": "Cornet",      "program": 56},
            "Contralto_1": {"name": "French Horn", "program": 60},
            "Contralto_2": {"name": "Alto Horn",   "program": 60},
            "Tenor_1":     {"name": "Euphonium",   "program": 57},
            "Tenor_2":     {"name": "Trombone",    "program": 57},
            "Baixo_1":     {"name": "Tuba",        "program": 58},
            "Baixo_2":     {"name": "Bass Trombone", "program": 57}
        }
    },
    14: {
        "name": "Quarteto Dobrado de Eufônios",
        "desc": "Som extremamente lírico e doce - Flugelhorn, French Horn, Euphonium, Tuba",
        "map": {
            "Soprano_1":   {"name": "Flugelhorn",  "program": 56},
            "Soprano_2":   {"name": "Flugelhorn",  "program": 56},
            "Contralto_1": {"name": "French Horn", "program": 60},
            "Contralto_2": {"name": "French Horn", "program": 60},
            "Tenor_1":     {"name": "Euphonium",   "program": 57},
            "Tenor_2":     {"name": "Euphonium",   "program": 57},
            "Baixo_1":     {"name": "Tuba",        "program": 58},
            "Baixo_2":     {"name": "Tuba",        "program": 58}
        }
    },
    15: {
        "name": "Grande Fanfarra (Metais de Aço)",
        "desc": "Ataques potentes - Trumpet, Trombone, VSL Trombones, Tuba",
        "map": {
            "Soprano_1":   {"name": "Trumpet",     "program": 56},
            "Soprano_2":   {"name": "Trumpet",     "program": 56},
            "Contralto_1": {"name": "Trumpet",     "program": 56},
            "Contralto_2": {"name": "Trombone",    "program": 57},
            "Tenor_1":     {"name": "Trombone",    "program": 57},
            "Tenor_2":     {"name": "Trombone",    "program": 57},
            "Baixo_1":     {"name": "VSL Bass Trombones", "program": 57},
            "Baixo_2":     {"name": "Tuba",        "program": 58}
        }
    },
    16: {
        "name": "Orquestra Pastoral",
        "desc": "Textura de sopros suaves - Flugelhorn/Cornet, French Horn, Baritone/Euphonium, Tuba/Bass Trombone",
        "map": {
            "Soprano_1":   {"name": "Flugelhorn",  "program": 56},
            "Soprano_2":   {"name": "Cornet",      "program": 56},
            "Contralto_1": {"name": "French Horn", "program": 60},
            "Contralto_2": {"name": "French Horn", "program": 60},
            "Tenor_1":     {"name": "Baritone Horn", "program": 57},
            "Tenor_2":     {"name": "Euphonium",   "program": 57},
            "Baixo_1":     {"name": "Tuba",        "program": 58},
            "Baixo_2":     {"name": "Bass Trombone", "program": 57}
        }
    },
    17: {
        "name": "Metais de Transição",
        "desc": "Rico em diversidade de timbres - Cornet/Flugelhorn, French Horn/Trombone, Euphonium, Tuba/Bass Trombone",
        "map": {
            "Soprano_1":   {"name": "Cornet",      "program": 56},
            "Soprano_2":   {"name": "Flugelhorn",  "program": 56},
            "Contralto_1": {"name": "French Horn", "program": 60},
            "Contralto_2": {"name": "Trombone",    "program": 57},
            "Tenor_1":     {"name": "Euphonium",   "program": 57},
            "Tenor_2":     {"name": "Trombone",    "program": 57},
            "Baixo_1":     {"name": "Tuba",        "program": 58},
            "Baixo_2":     {"name": "Bass Trombone", "program": 57}
        }
    },
    18: {
        "name": "Som Híbrido VSL & Muse Brass",
        "desc": "Trombones VSL na base e metais Muse Brass no topo - Trumpet/Flugelhorn, Horn, Trombone, VSL Trombones/Tuba",
        "map": {
            "Soprano_1":   {"name": "Trumpet",     "program": 56},
            "Soprano_2":   {"name": "Flugelhorn",  "program": 56},
            "Contralto_1": {"name": "French Horn", "program": 60},
            "Contralto_2": {"name": "French Horn", "program": 60},
            "Tenor_1":     {"name": "Trombone",    "program": 57},
            "Tenor_2":     {"name": "Trombone",    "program": 57},
            "Baixo_1":     {"name": "VSL Bass Trombones", "program": 57},
            "Baixo_2":     {"name": "Tuba",        "program": 58}
        }
    },
    19: {
        "name": "Orquestra de Metais no Teatro",
        "desc": "Foco em espacialidade natural e reverb largo - Trumpet/Flugelhorn, Horn/Alto, Trombone, Tuba",
        "map": {
            "Soprano_1":   {"name": "Trumpet",     "program": 56},
            "Soprano_2":   {"name": "Flugelhorn",  "program": 56},
            "Contralto_1": {"name": "French Horn", "program": 60},
            "Contralto_2": {"name": "Alto Horn",   "program": 60},
            "Tenor_1":     {"name": "Trombone",    "program": 57},
            "Tenor_2":     {"name": "Trombone",    "program": 57},
            "Baixo_1":     {"name": "Tuba",        "program": 58},
            "Baixo_2":     {"name": "Tuba",        "program": 58}
        }
    },
    20: {
        "name": "Som Denso Sinfônico",
        "desc": "O som mais pesado com todos os instrumentos - Trumpet/Flugelhorn, French Horn, Trombone/Euphonium, Bass Trombone/VSL",
        "map": {
            "Soprano_1":   {"name": "Trumpet",     "program": 56},
            "Soprano_2":   {"name": "Flugelhorn",  "program": 56},
            "Contralto_1": {"name": "French Horn", "program": 60},
            "Contralto_2": {"name": "French Horn", "program": 60},
            "Tenor_1":     {"name": "Trombone",    "program": 57},
            "Tenor_2":     {"name": "Euphonium",   "program": 57},
            "Baixo_1":     {"name": "Bass Trombone", "program": 57},
            "Baixo_2":     {"name": "VSL Bass Trombones", "program": 57}
        }
    }
}


# ─── Funções Auxiliares de Modelagem Acústica e Expressiva ────────────────────

def seconds_to_ticks(seconds, tempo, ticks_per_beat):
    ticks_per_sec = ticks_per_beat * (1000000.0 / tempo)
    return int(seconds * ticks_per_sec)

def get_pitch_stats(mid, sorted_channels):
    pitch_stats = {}
    for ch in sorted_channels:
        pitches = []
        for track in mid.tracks:
            for msg in track:
                if not msg.is_meta and hasattr(msg, 'channel') and msg.channel == ch:
                    if msg.type == 'note_on' and msg.velocity > 0:
                        pitches.append(msg.note)
        if pitches:
            pitch_stats[ch] = sum(pitches) / len(pitches)
        else:
            pitch_stats[ch] = 64
    return pitch_stats

def calculate_expressive_velocity(msg, abs_time, avg_pitch, phrase_boundaries, voice, ticks_per_beat):
    # 1. Base Velocity (Mezzo-Forte / Volume normal = 78)
    base_vel = 78
    
    # 2. Fator Melódico (Pitch Height)
    # Toca mais forte conforme o agudo sobe
    pitch_diff = msg.note - avg_pitch
    factor_melodic = pitch_diff * 1.6
    
    # 3. Fator de Fraseado (Arco da estrofe: piano -> forte/fortissimo -> pianissimo)
    factor_phrase = 0
    phrase_idx = -1
    current_phrase = None
    for idx, (start_t, end_t) in enumerate(phrase_boundaries):
        if start_t <= abs_time < end_t:
            current_phrase = (start_t, end_t)
            phrase_idx = idx
            break
            
    if current_phrase:
        start_t, end_t = current_phrase
        phrase_len = end_t - start_t
        if phrase_len > 0:
            rel_pos = (abs_time - start_t) / phrase_len
            
            # Curva senoidal expressiva
            factor_phrase = -15 + 32 * math.sin(math.pi * (rel_pos ** 0.85))
            
            # Solo de vozes intermediárias (Frases 1 e 4 nunca mudam)
            # Frase 2: Destaca o Contralto
            if phrase_idx == 1 and voice == "Contralto":
                factor_phrase += 15
            # Frase 3: Destaca o Tenor
            elif phrase_idx == 2 and voice == "Tenor":
                factor_phrase += 15
                
    # 4. Fator Métrico (Acentuação no tempo 1 do compasso)
    factor_metric = 0
    measure_ticks = 4 * ticks_per_beat
    pos_in_measure = abs_time % measure_ticks
    if pos_in_measure < (ticks_per_beat * 0.1): # tempo 1
        factor_metric = 6
    elif (ticks_per_beat * 2.0) <= pos_in_measure < (ticks_per_beat * 2.1): # tempo 3
        factor_metric = 3
    elif (ticks_per_beat * 1.0) <= pos_in_measure < (ticks_per_beat * 1.1) or (ticks_per_beat * 3.0) <= pos_in_measure < (ticks_per_beat * 3.1): # tempos fracos
        factor_metric = -4
        
    final_vel = base_vel + factor_melodic + factor_phrase + factor_metric
    if voice == "Tenor":
        final_vel = final_vel * 1.25 + 15
    return max(40, min(120, int(final_vel)))

def process_midi_to_8part(input_path, output_path, mapping, use_expression=True, speed=1.0):
    mid = mido.MidiFile(input_path)
    
    # Detectar canais originais do MIDI SATB
    active_channels = set()
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'note_on' and msg.velocity > 0:
                active_channels.add(msg.channel)
    sorted_channels = sorted(list(active_channels))
    
    voices = ["Soprano", "Contralto", "Tenor", "Baixo"]
    channel_to_voice = {sorted_channels[i]: voices[i] for i in range(min(len(sorted_channels), len(voices)))}
    
    # Tessitura média para as vozes
    pitch_stats = get_pitch_stats(mid, sorted_channels)
    
    # Tempo e limites de frase
    tempo = 500000
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'set_tempo':
                tempo = msg.tempo
                break

    max_abs_time = 0
    for track in mid.tracks:
        curr_time = 0
        for msg in track:
            curr_time += msg.time
        if curr_time > max_abs_time:
            max_abs_time = curr_time
            
    phrase_duration = max_abs_time / 4.0
    phrase_boundaries = [
        (0.0, phrase_duration),
        (phrase_duration, phrase_duration * 2.0),
        (phrase_duration * 2.0, phrase_duration * 3.0),
        (phrase_duration * 3.0, max_abs_time + 1000)
    ]
    
    new_mid = mido.MidiFile()
    new_mid.ticks_per_beat = mid.ticks_per_beat
    
    # Meta track
    meta_track = mido.MidiTrack()
    new_mid.tracks.append(meta_track)
    for track in mid.tracks:
        for msg in track:
            if msg.is_meta and msg.type in ['set_tempo', 'time_signature', 'key_signature']:
                msg_copy = msg.copy()
                if msg_copy.type == 'set_tempo' and speed != 1.0:
                    msg_copy.tempo = int(msg_copy.tempo / speed)
                meta_track.append(msg_copy)
                
    # 9 Instrumentos orquestrais configurados (Canais 0 a 8)
    instruments_config = [
        # Sopranos (Lado 1 na Esquerda / Lado 2 na Direita)
        {"voice": "Soprano",   "pan": 48, "inst": mapping["Soprano_1"]},
        {"voice": "Soprano",   "pan": 80, "inst": mapping["Soprano_2"]},
        # Contraltos
        {"voice": "Contralto", "pan": 48, "inst": mapping["Contralto_1"]},
        {"voice": "Contralto", "pan": 80, "inst": mapping["Contralto_2"]},
        # Tenores
        {"voice": "Tenor",     "pan": 48, "inst": {"name": "Trombones", "program": 57}},
        {"voice": "Tenor",     "pan": 80, "inst": {"name": "Trombones", "program": 57}},
        {"voice": "Tenor",     "pan": 64, "inst": {"name": "Trombones", "program": 57}}, # Trilha extra com Trombones no centro para reforçar o tenor
        # Baixos
        {"voice": "Baixo",     "pan": 48, "inst": mapping["Baixo_1"]},
        {"voice": "Baixo",     "pan": 80, "inst": mapping["Baixo_2"]}
    ]
    
    for idx, conf in enumerate(instruments_config):
        voice_track = mido.MidiTrack()
        new_mid.tracks.append(voice_track)
        
        voice_name = conf["voice"]
        midi_channel = idx
        inst = conf["inst"]
        
        # Metaevento de track_name para o MuseScore associar o timbre correto
        voice_track.append(mido.MetaMessage('track_name', name=inst["name"], time=0))
        # Program change
        voice_track.append(mido.Message('program_change', channel=midi_channel, program=inst["program"], time=0))
        # Panning (CC 10) estéreo
        voice_track.append(mido.Message('control_change', channel=midi_channel, control=10, value=conf["pan"], time=0))
        
        # Volume do canal (CC 7) - Maximizando o volume do tenor para 127 e atenuando os outros para 75
        vol_val = 127 if voice_name == "Tenor" else 75
        voice_track.append(mido.Message('control_change', channel=midi_channel, control=7, value=vol_val, time=0))
        
        target_channel = None
        for ch, v in channel_to_voice.items():
            if v == voice_name:
                target_channel = ch
                break
                
        if target_channel is None:
            continue
            
        avg_pitch = pitch_stats.get(target_channel, 64)
        
        for track in mid.tracks:
            has_channel_msgs = any(not msg.is_meta and hasattr(msg, 'channel') and msg.channel == target_channel for msg in track)
            if not has_channel_msgs:
                continue
                
            # Conversão local para absoluto
            abs_track = []
            curr_time = 0
            for msg in track:
                curr_time += msg.time
                abs_track.append(msg.copy(time=curr_time))
                
            active_notes = {}
            processed_abs_events = []
            
            for msg in abs_track:
                if msg.is_meta:
                    continue
                if hasattr(msg, 'channel') and msg.channel == target_channel:
                    if msg.type == 'note_on' and msg.velocity > 0:
                        # Humanização de ataque independente para cada pauta
                        if voice_name == "Soprano":
                            delay_sec = 0.0
                        else:
                            delay_sec = random.choice([0.0, 0.015, 0.05, 0.10])
                        delay_ticks = seconds_to_ticks(delay_sec, tempo, mid.ticks_per_beat)
                        active_notes[msg.note] = delay_ticks
                        
                        new_msg = msg.copy(channel=midi_channel, time=msg.time + delay_ticks)
                        
                        # Expressão dinâmica baseada em velocity
                        if use_expression:
                            new_msg.velocity = calculate_expressive_velocity(
                                msg, msg.time, avg_pitch, phrase_boundaries, voice_name, mid.ticks_per_beat
                            )
                        else:
                            # Sem expressão: volume padrão fixo (80)
                            vel_offset = int(80 * random.uniform(-0.04, 0.04))
                            new_msg.velocity = 80 + vel_offset
                            
                        processed_abs_events.append(new_msg)
                        
                    elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                        # Release com o mesmo delay da nota
                        delay_ticks = active_notes.pop(msg.note, 0)
                        new_msg = msg.copy(channel=midi_channel, time=msg.time + delay_ticks)
                        processed_abs_events.append(new_msg)
            
            processed_abs_events.sort(key=lambda x: x.time)
            rel_events = []
            prev_time = 0
            for msg in processed_abs_events:
                delta = msg.time - prev_time
                rel_events.append(msg.copy(time=delta))
                prev_time = msg.time
                
            for r_msg in rel_events:
                voice_track.append(r_msg)
                
    new_mid.save(output_path)


# ─── Renderização ─────────────────────────────────────────────────────────────

def apply_mixer_boost(mscz_path, mapping):
    """
    Unzips the .mscz file, injects custom audio settings (volume and instrument selection)
    for the Tenor and Soprano tracks into audiosettings.json, and zips it back.
    """
    temp_path = mscz_path + ".tmp"
    
    # Soprano instrument data mapping (Flugelhorn/Cornet map to Trumpet to avoid sample range limits causing muting on high notes)
    muse_brass_sounds = {
        "Trumpet": {
            "instrumentId": "bb-trumpet",
            "museName": "Trumpet",
            "museUID": "110",
            "playbackSetupData": "winds.trumpet"
        },
        "Flugelhorn": {
            "instrumentId": "bb-trumpet",
            "museName": "Trumpet",
            "museUID": "110",
            "playbackSetupData": "winds.trumpet"
        },
        "Cornet": {
            "instrumentId": "bb-trumpet",
            "museName": "Trumpet",
            "museUID": "110",
            "playbackSetupData": "winds.trumpet"
        },
        "French Horn": {
            "instrumentId": "horn",
            "museName": "Horn in F",
            "museUID": "108",
            "playbackSetupData": "winds.horn.french:in_f"
        }
    }
    
    sop1_name = mapping.get("Soprano_1", {}).get("name", "Trumpet")
    sop2_name = mapping.get("Soprano_2", {}).get("name", "Trumpet")
    
    sop1_meta = muse_brass_sounds.get(sop1_name, muse_brass_sounds["Trumpet"])
    sop2_meta = muse_brass_sounds.get(sop2_name, muse_brass_sounds["Trumpet"])
    
    injected_tracks = [
        # Soprano 1 (Part 1, left)
        {
          "in": {
            "resourceMeta": {
              "attributes": {
                "museCategory": "Muse Brass",
                "museName": sop1_meta["museName"],
                "musePack": "Muse Brass",
                "museUID": sop1_meta["museUID"],
                "museVendorName": "Muse",
                "playbackSetupData": sop1_meta["playbackSetupData"]
              },
              "hasNativeEditorSupport": False,
              "id": sop1_meta["museUID"],
              "type": "muse_sampler_sound_pack",
              "vendor": "MuseSounds"
            },
            "unitConfiguration": {}
          },
          "instrumentId": sop1_meta["instrumentId"],
          "out": {
            "auxSends": [
              {"active": True, "signalAmount": 0.4},
              {"active": True, "signalAmount": 0.3}
            ],
            "balance": -0.42,
            "fxChain": {},
            "volumeDb": 2.0
          },
          "partId": "1"
        },
        # Soprano 2 (Part 2, right)
        {
          "in": {
            "resourceMeta": {
              "attributes": {
                "museCategory": "Muse Brass",
                "museName": sop2_meta["museName"],
                "musePack": "Muse Brass",
                "museUID": sop2_meta["museUID"],
                "museVendorName": "Muse",
                "playbackSetupData": sop2_meta["playbackSetupData"]
              },
              "hasNativeEditorSupport": False,
              "id": "2",
              "type": "muse_sampler_sound_pack",
              "vendor": "MuseSounds"
            },
            "unitConfiguration": {}
          },
          "instrumentId": sop2_meta["instrumentId"],
          "out": {
            "auxSends": [
              {"active": True, "signalAmount": 0.4},
              {"active": True, "signalAmount": 0.3}
            ],
            "balance": 0.43,
            "fxChain": {},
            "volumeDb": 2.0
          },
          "partId": "2"
        },
        # Tenor 1 (Part 5, left)
        {
          "in": {
            "resourceMeta": {
              "attributes": {
                "museCategory": "Muse Brass",
                "museName": "Trombones a3",
                "musePack": "Muse Brass",
                "museUID": "111",
                "museVendorName": "Muse",
                "playbackSetupData": "winds.trombone.section"
              },
              "hasNativeEditorSupport": False,
              "id": "111",
              "type": "muse_sampler_sound_pack",
              "vendor": "MuseSounds"
            },
            "unitConfiguration": {}
          },
          "instrumentId": "trombone",
          "out": {
            "auxSends": [
              {"active": True, "signalAmount": 0.4},
              {"active": True, "signalAmount": 0.3}
            ],
            "balance": -0.42,
            "fxChain": {},
            "volumeDb": -2.5
          },
          "partId": "5"
        },
        # Tenor 2 (Part 6, right)
        {
          "in": {
            "resourceMeta": {
              "attributes": {
                "museCategory": "Muse Brass",
                "museName": "Trombones a3",
                "musePack": "Muse Brass",
                "museUID": "111",
                "museVendorName": "Muse",
                "playbackSetupData": "winds.trombone.section"
              },
              "hasNativeEditorSupport": False,
              "id": "111",
              "type": "muse_sampler_sound_pack",
              "vendor": "MuseSounds"
            },
            "unitConfiguration": {}
          },
          "instrumentId": "trombone",
          "out": {
            "auxSends": [
              {"active": True, "signalAmount": 0.4},
              {"active": True, "signalAmount": 0.3}
            ],
            "balance": 0.43,
            "fxChain": {},
            "volumeDb": -2.5
          },
          "partId": "6"
        },
        # Tenor 3 (Part 7, center reinforcement)
        {
          "in": {
            "resourceMeta": {
              "attributes": {
                "museCategory": "Muse Brass",
                "museName": "Trombones a3",
                "musePack": "Muse Brass",
                "museUID": "111",
                "museVendorName": "Muse",
                "playbackSetupData": "winds.trombone.section"
              },
              "hasNativeEditorSupport": False,
              "id": "111",
              "type": "muse_sampler_sound_pack",
              "vendor": "MuseSounds"
            },
            "unitConfiguration": {}
          },
          "instrumentId": "trombone",
          "out": {
            "auxSends": [
              {"active": True, "signalAmount": 0.4},
              {"active": True, "signalAmount": 0.3}
            ],
            "balance": 0.0,
            "fxChain": {},
            "volumeDb": -1.5
          },
          "partId": "7"
        }
    ]
    
    with zipfile.ZipFile(mscz_path, 'r') as yin:
        with zipfile.ZipFile(temp_path, 'w') as yout:
            for item in yin.infolist():
                data = yin.read(item.filename)
                if item.filename == "audiosettings.json":
                    try:
                        settings = json.loads(data.decode('utf-8'))
                    except Exception:
                        settings = {}
                    settings["tracks"] = injected_tracks
                    settings["activeSoundProfile"] = "MuseSounds"
                    data = json.dumps(settings, indent=2).encode('utf-8')
                yout.writestr(item, data)
                
    os.replace(temp_path, mscz_path)


def render_score(midi_path, output_mp3, soundfonts_dir):
    my_env = os.environ.copy()
    my_env["MUSESAMPLER_INSTRUMENT_FOLDER"] = soundfonts_dir
    
    # Chama o MuseScore 4 via linha de comando
    subprocess.run([
        "/Applications/MuseScore 4.app/Contents/MacOS/mscore",
        "-o", output_mp3,
        midi_path
    ], env=my_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ─── CLI Main ─────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="MuseScore 4 Orchestrator: MIDI SATB -> Orquestra de Metais 8 Partes")
    ap.add_argument("--midi",       default=None,           help="MIDI de entrada específico (caso queira processar apenas 1)")
    ap.add_argument("--preset",     type=int, default=2,    help="Número do preset de metais (1 a 20). Padrão = 2 (Mellow Brass)")
    ap.add_argument("--output",     default="output_musescore", help="Pasta de saída para os arquivos MP3")
    ap.add_argument("--soundfonts", default="/Users/jonaspoli/Documents/MuseScore4/SoundFonts/Muse Hub Instruments", 
                    help="Caminho para os instrumentos das Muse Sounds")
    ap.add_argument("--no-expression", action="store_true", help="Desativa a expressão dinâmica inteligente (crescendo, p, f, ff)")
    ap.add_argument("--speed",       type=float, default=1.0, help="Fator de velocidade/tempo (ex: 0.85 para deixar 15% mais lento)")
    args = ap.parse_args()
    
    os.makedirs(args.output, exist_ok=True)
    
    # Valida preset
    if args.preset not in BRASS_PRESETS:
        print(f"ERRO: Preset {args.preset} inválido. Escolha de 1 a 20.")
        sys.exit(1)
        
    preset = BRASS_PRESETS[args.preset]
    print("════════════════════════════════════════════════════════════")
    print(f"  MuseScore Orchestrate — Preset {args.preset}: {preset['name']}")
    print(f"  Descrição: {preset['desc']}")
    print(f"  Velocidade: {args.speed}x")
    print(f"  Expressão Dinâmica: {'DESATIVADA' if args.no_expression else 'ATIVA'}")
    print("════════════════════════════════════════════════════════════\n")
    
    # Coleta arquivos MIDI
    midi_files = [args.midi] if args.midi else sorted(glob.glob("mid/*.mid"))
    total = len(midi_files)
    
    if total == 0:
        print("Nenhum arquivo MIDI encontrado em 'mid/'.")
        sys.exit(1)
        
    for idx, path in enumerate(midi_files, 1):
        name = os.path.splitext(os.path.basename(path))[0]
        out_mp3 = os.path.join(args.output, f"{name}_orquestra_mscore.mp3")
        
        # Pula se já existe
        if os.path.exists(out_mp3) and not args.midi:
            print(f"[{idx}/{total}] ✓ (já existe) {name}")
            continue
            
        print(f"[{idx}/{total}] ▶ {name}...", end="", flush=True)
        out_mid = os.path.join(args.output, f"{name}_orquestra_mscore.mid")
        out_mscz = os.path.join(args.output, f"{name}_orquestra_mscore.mscz")
        
        try:
            # 1. Processa e humaniza o MIDI dividindo em 9 partes
            create_expression = not args.no_expression
            process_midi_to_8part(path, out_mid, preset["map"], use_expression=create_expression, speed=args.speed)
            
            # 2. Renderiza a partitura MSCZ no MuseScore 4
            render_score(out_mid, out_mscz, args.soundfonts)
            
            # 3. Aplica o boost do Tenor diretamente no Mixer (audiosettings.json) do MSCZ
            apply_mixer_boost(out_mscz, preset["map"])
            
            # 4. Renderiza o MP3 final a partir do MSCZ modificado
            render_score(out_mscz, out_mp3, args.soundfonts)
            print(" ✓ concluído")
        except Exception as e:
            print(f" ✗ FALHOU (erro: {e})")

    print("\n✓ Processamento de lote finalizado!")

if __name__ == "__main__":
    main()
