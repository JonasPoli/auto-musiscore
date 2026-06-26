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

# Parâmetros Globais de Expressividade Física (Volume/Sopro Humano)
EXPR_BASE_VOLUME = 70      # Volume base para o sopro (CC11)
EXPR_AMPLITUDE   = 35      # Amplitude do swell do fôlego humano
SAMPLING_STEP_TICKS = 40   # Intervalo em ticks para amostragem dos eventos CC11

# ─── Funções de Processamento Baseadas nas Fórmulas do Coral ─────────────────

def process_midi_to_8part_math(input_path, output_path, mapping, use_expression=True, speed=1.0):
    """
    Processa um arquivo MIDI SATB de 4 canais dividindo em 8 partes (Soprano 1/2, Contralto 1/2, etc.)
    e aplicando as seguintes fórmulas matemáticas solicitadas para humanização:
    
    1. Tempo da nota (Timing):
       T_novo = T_original + R
       - Soprano, Contralto e Tenor: R em [-10, 10] ticks
       - Baixo: R em [-5, 5] ticks
       
    2. Força do toque (Velocity):
       V_novo = V_base + V_aleatorio + V_acento
       - V_aleatorio em [-5, 5]
       - V_acento: +10 no tempo forte do compasso (Beat 1), -5 nos outros tempos
       - Contralto e Tenor: atenuado em 10% (coeficiente 0.9)
       
    3. Curva de volume / Expressão (CC11) para notas longas:
       E(t) = E_base + A * sin(pi * (t / D))
       - D é a duração total, t é o tempo decorrido.
    """
    mid = mido.MidiFile(input_path)
    ticks_per_beat = mid.ticks_per_beat
    
    # Detectar canais originais do MIDI SATB (geralmente são 4 canais ativos)
    active_channels = set()
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'note_on' and msg.velocity > 0:
                active_channels.add(msg.channel)
    sorted_channels = sorted(list(active_channels))
    
    voices = ["Soprano", "Contralto", "Tenor", "Baixo"]
    channel_to_voice = {sorted_channels[i]: voices[i] for i in range(min(len(sorted_channels), len(voices)))}
    
    # Tentar capturar a fórmula de compasso (Time Signature) para detectar tempos fortes
    numerator = 4
    measure_ticks = 4 * ticks_per_beat
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'time_signature':
                if msg.numerator > 1: # Ignora compasso de anacruse (ex: 1/4) para pegar o compasso principal
                    numerator = msg.numerator
                    measure_ticks = numerator * ticks_per_beat
                    break
                
    new_mid = mido.MidiFile()
    new_mid.ticks_per_beat = ticks_per_beat
    
    # Copia a trilha de metadados (Track 0)
    meta_track = mido.MidiTrack()
    new_mid.tracks.append(meta_track)
    
    # Coleta todas as mensagens meta em tempos absolutos para duplicar nas trilhas de notas
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
                
    # Preenche a Track 0 com as mensagens meta relativas
    rel_meta_events = []
    prev_meta_time = 0
    for msg in sorted(abs_meta_events, key=lambda x: x.time):
        delta = msg.time - prev_meta_time
        meta_track.append(msg.copy(time=delta))
        prev_meta_time = msg.time
                
    # Configuração dos 9 instrumentos e da espacialização (Lado 1 esq = 48, Lado 2 dir = 80, Centro = 64)
    instruments_config = [
        {"voice": "Soprano",   "pan": 48, "inst": mapping["Soprano_1"]},
        {"voice": "Soprano",   "pan": 80, "inst": mapping["Soprano_2"]},
        {"voice": "Contralto", "pan": 48, "inst": mapping["Contralto_1"]},
        {"voice": "Contralto", "pan": 80, "inst": mapping["Contralto_2"]},
        {"voice": "Tenor",     "pan": 48, "inst": {"name": "Trombones", "program": 57}},
        {"voice": "Tenor",     "pan": 80, "inst": {"name": "Trombones", "program": 57}},
        {"voice": "Tenor",     "pan": 64, "inst": {"name": "Trombones", "program": 57}}, # Trilha extra com Trombones no centro para reforçar o tenor
        {"voice": "Baixo",     "pan": 48, "inst": mapping["Baixo_1"]},
        {"voice": "Baixo",     "pan": 80, "inst": mapping["Baixo_2"]}
    ]
    
    for idx, conf in enumerate(instruments_config):
        voice_track = mido.MidiTrack()
        new_mid.tracks.append(voice_track)
        
        voice_name = conf["voice"]
        midi_channel = idx
        inst = conf["inst"]
        
        # Cabeçalho da track do instrumento no MuseScore
        voice_track.append(mido.MetaMessage('track_name', name=inst["name"], time=0))
        voice_track.append(mido.Message('program_change', channel=midi_channel, program=inst["program"], time=0))
        voice_track.append(mido.Message('control_change', channel=midi_channel, control=10, value=conf["pan"], time=0))
        
        # Volume do canal (CC 7) - Maximizando o volume do tenor para 127 e atenuando os outros para 75
        vol_val = 127 if voice_name == "Tenor" else 75
        voice_track.append(mido.Message('control_change', channel=midi_channel, control=7, value=vol_val, time=0))
        
        # Encontra qual canal original corresponde a esta voz
        target_channel = None
        for ch, v in channel_to_voice.items():
            if v == voice_name:
                target_channel = ch
                break
                
        if target_channel is None:
            continue
            
        # Extrair e emparelhar notas da pauta original com seus tempos absolutos
        for track in mid.tracks:
            has_channel_msgs = any(not msg.is_meta and hasattr(msg, 'channel') and msg.channel == target_channel for msg in track)
            if not has_channel_msgs:
                continue
                
            abs_events = []
            curr_time = 0
            for msg in track:
                curr_time += msg.time
                if not msg.is_meta and hasattr(msg, 'channel') and msg.channel == target_channel:
                    abs_events.append(msg.copy(time=curr_time))
                    
            # Agrupa note_on e note_off para saber a duração exata das notas
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
            
            # Duplica os eventos meta de tempo e compasso na track de notas (corrige bug do MuseScore)
            for meta_msg in abs_meta_events:
                processed_abs_events.append(meta_msg.copy())
            
            for note_info in notes:
                note_num = note_info["note"]
                on_time = note_info["on_time"]
                off_time = note_info["off_time"]
                v_base = note_info["velocity"]
                
                # 1. Timing: T_novo = T_original + R
                if voice_name == "Baixo":
                    R = random.randint(-5, 5)
                else:
                    R = random.randint(-10, 10)
                    
                on_time_new = max(0, on_time + R)
                off_time_new = max(on_time_new + 10, off_time + R)
                duration = off_time_new - on_time_new
                
                # 2. Velocity: V_novo = V_base + V_aleatorio + V_acento
                v_aleatorio = random.randint(-5, 5)
                
                # Acentuação métrica (tempo forte do compasso = beat 1)
                pos_in_measure = on_time_new % measure_ticks
                if pos_in_measure < (ticks_per_beat * 0.1):
                    v_acento = 10
                else:
                    v_acento = -5
                    
                v_novo = v_base + v_aleatorio + v_acento
                
                # Reduz em 10% se for Contralto
                if voice_name == "Contralto":
                    v_novo = int(v_novo * 0.9)
                # Dá um boost forte para o Tenor para garantir brilho e ataque (Trombone/Euphonium)
                elif voice_name == "Tenor":
                    v_novo = int(v_novo * 1.25) + 15
                    
                v_final = max(1, min(127, v_novo))
                
                # Cria eventos note_on e note_off
                note_on_msg = mido.Message('note_on', channel=midi_channel, note=note_num, velocity=v_final, time=on_time_new)
                note_off_msg = mido.Message('note_off', channel=midi_channel, note=note_num, velocity=0, time=off_time_new)
                
                processed_abs_events.append(note_on_msg)
                processed_abs_events.append(note_off_msg)
                
                # 3. Curva de volume / sopro (CC11) para notas com longa duração (>= 1 batida)
                if use_expression and duration >= ticks_per_beat:
                    # Amostra pontos ao longo da nota
                    for t_step in range(0, duration + 1, SAMPLING_STEP_TICKS):
                        # E(t) = E_base + A * sin(pi * (t / D))
                        factor = math.sin(math.pi * (t_step / duration))
                        e_val = EXPR_BASE_VOLUME + EXPR_AMPLITUDE * factor
                        if voice_name == "Tenor":
                            e_val += 35
                        e_final = max(0, min(127, int(e_val)))
                        
                        cc_time = on_time_new + t_step
                        cc_msg = mido.Message(
                            'control_change', 
                            channel=midi_channel, 
                            control=11, 
                            value=e_final, 
                            time=cc_time
                        )
                        processed_abs_events.append(cc_msg)
                        
            # Ordena todos os eventos cronologicamente
            processed_abs_events.sort(key=lambda x: x.time)
            
            # Converte de tempos absolutos de volta para delta-times (relativos)
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
              "id": sop2_meta["museUID"],
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
    
    # Chama o MuseScore 4 em modo CLI para renderizar o áudio
    subprocess.run([
        "/Applications/MuseScore 4.app/Contents/MacOS/mscore",
        "-o", output_mp3,
        midi_path
    ], env=my_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ─── CLI Main ─────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="MuseScore 4 Math Orchestrator: Coral 8 Partes com Fórmulas de Humanização")
    ap.add_argument("--midi",       default=None,           help="MIDI de entrada específico (para processar apenas 1)")
    ap.add_argument("--preset",     type=int, default=2,    help="Número do preset de metais (1 a 20). Padrão = 2 (Mellow Brass)")
    ap.add_argument("--output",     default="brass", help="Pasta de saída para os arquivos MP3")
    ap.add_argument("--soundfonts", default="/Users/jonaspoli/Documents/MuseScore4/SoundFonts/Muse Hub Instruments", 
                    help="Caminho para os instrumentos das Muse Sounds")
    ap.add_argument("--no-expression", action="store_true", help="Desativa a expressão dinâmica por curva de seno (CC11)")
    ap.add_argument("--speed",       type=float, default=1.0, help="Fator de velocidade/tempo (ex: 0.85 para deixar 15% mais lento)")
    args = ap.parse_args()
    
    os.makedirs(args.output, exist_ok=True)
    
    if args.preset not in BRASS_PRESETS:
        print(f"ERRO: Preset {args.preset} inválido. Escolha de 1 a 20.")
        sys.exit(1)
        
    preset = BRASS_PRESETS[args.preset]
    print("════════════════════════════════════════════════════════════")
    print(f"  Orquestrador Matemático — Preset {args.preset}: {preset['name']}")
    print(f"  Descrição: {preset['desc']}")
    print(f"  Fórmulas Matemáticas de Coral Ativas")
    print(f"  Velocidade: {args.speed}x")
    print(f"  Curva de Expressão CC11: {'DESATIVADA' if args.no_expression else 'ATIVA'}")
    print("════════════════════════════════════════════════════════════\n")
    
    # Coleta arquivos MIDI
    midi_files = [args.midi] if args.midi else sorted(glob.glob("mid/*.mid"))
    total = len(midi_files)
    
    if total == 0:
        print("Nenhum arquivo MIDI encontrado em 'mid/'.")
        sys.exit(1)
        
    for idx, path in enumerate(midi_files, 1):
        name = os.path.splitext(os.path.basename(path))[0]
        out_mp3 = os.path.join(args.output, f"{name}.mp3")
        
        # Pula se já existe (apenas em batch completo)
        if os.path.exists(out_mp3) and not args.midi:
            print(f"[{idx}/{total}] ✓ (já existe) {name}")
            continue
            
        print(f"[{idx}/{total}] ▶ {name}...", end="", flush=True)
        out_mid = os.path.join(args.output, f"{name}.mid")
        out_mscz = os.path.join(args.output, f"{name}.mscz")
        
        try:
            # 1. Processa e humaniza com as fórmulas de coral matemáticas (salva o .mid final)
            create_expression = not args.no_expression
            process_midi_to_8part_math(path, out_mid, preset["map"], use_expression=create_expression, speed=args.speed)
            
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
