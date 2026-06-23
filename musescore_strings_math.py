import mido
import os
import random
import math
import argparse
import subprocess
import glob
import sys

# ─── Configurações e Presets de Cordas (8 Partes) ──────────────────────────────
# 2 Sopranos, 2 Contraltos, 2 Tenores, 2 Baixos
# Panning: Lado 1 (Esquerda = 48), Lado 2 (Direita = 80)
# Program Changes GM: 40 = Violin, 41 = Viola, 42 = Cello, 43 = Contrabass,
#                     44 = Tremolo, 45 = Pizzicato, 46 = Harp
STRINGS_PRESETS = {
    1: {
        "name": "Sinfônica Clássica",
        "desc": "Orquestra de Cordas de Seção Equilibrada - Violins I/II, Violas, Cellos, Contrabasses",
        "map": {
            "Soprano_1":   {"name": "Violins I",     "program": 40},
            "Soprano_2":   {"name": "Violins II",    "program": 40},
            "Contralto_1": {"name": "Violas",        "program": 41},
            "Contralto_2": {"name": "Violas",        "program": 41},
            "Tenor_1":     {"name": "Violoncellos",  "program": 42},
            "Tenor_2":     {"name": "Violoncellos",  "program": 42},
            "Baixo_1":     {"name": "Contrabasses",  "program": 43},
            "Baixo_2":     {"name": "Contrabasses",  "program": 43}
        }
    },
    2: {
        "name": "String Octet Solo",
        "desc": "Cordas Solistas Íntimas - Solo Violin, Solo Viola, Solo Cello, Solo Contrabass",
        "map": {
            "Soprano_1":   {"name": "Solo Violin",   "program": 40},
            "Soprano_2":   {"name": "Solo Violin",   "program": 40},
            "Contralto_1": {"name": "Solo Viola",    "program": 41},
            "Contralto_2": {"name": "Solo Viola",    "program": 41},
            "Tenor_1":     {"name": "Solo Cello",    "program": 42},
            "Tenor_2":     {"name": "Solo Cello",    "program": 42},
            "Baixo_1":     {"name": "Solo Contrabass", "program": 43},
            "Baixo_2":     {"name": "Solo Contrabass", "program": 43}
        }
    },
    3: {
        "name": "Lush Orchestral Section",
        "desc": "Seção de Cordas Encorpada Dobrada com Harpa no Soprano",
        "map": {
            "Soprano_1":   {"name": "Violins I",     "program": 40},
            "Soprano_2":   {"name": "Harp",          "program": 46},
            "Contralto_1": {"name": "Violins II",    "program": 40},
            "Contralto_2": {"name": "Violas",        "program": 41},
            "Tenor_1":     {"name": "Violas",        "program": 41},
            "Tenor_2":     {"name": "Violoncellos",  "program": 42},
            "Baixo_1":     {"name": "Violoncellos",  "program": 42},
            "Baixo_2":     {"name": "Contrabasses",  "program": 43}
        }
    },
    4: {
        "name": "Romantic Dark (Foco Grave)",
        "desc": "Registros Médio-Graves Dominantes - Violas, Cellos e Contrabaixos",
        "map": {
            "Soprano_1":   {"name": "Violas",        "program": 41},
            "Soprano_2":   {"name": "Violas",        "program": 41},
            "Contralto_1": {"name": "Violoncellos",  "program": 42},
            "Contralto_2": {"name": "Violoncellos",  "program": 42},
            "Tenor_1":     {"name": "Violoncellos",  "program": 42},
            "Tenor_2":     {"name": "Contrabasses",  "program": 43},
            "Baixo_1":     {"name": "Contrabasses",  "program": 43},
            "Baixo_2":     {"name": "Contrabasses",  "program": 43}
        }
    },
    5: {
        "name": "Gothic Chamber (Híbrido)",
        "desc": "Contraste Acústico - Solistas no Lado 1 e Seção no Lado 2",
        "map": {
            "Soprano_1":   {"name": "Solo Violin",   "program": 40},
            "Soprano_2":   {"name": "Violins I",     "program": 40},
            "Contralto_1": {"name": "Solo Viola",    "program": 41},
            "Contralto_2": {"name": "Violas",        "program": 41},
            "Tenor_1":     {"name": "Solo Cello",    "program": 42},
            "Tenor_2":     {"name": "Violoncellos",  "program": 42},
            "Baixo_1":     {"name": "Solo Contrabass", "program": 43},
            "Baixo_2":     {"name": "Contrabasses",  "program": 43}
        }
    },
    6: {
        "name": "Double Quartet Mirror",
        "desc": "Espelho Estéreo Perfeito L/R - Violins, Violas, Cellos, Contrabasses",
        "map": {
            "Soprano_1":   {"name": "Violins I",     "program": 40},
            "Soprano_2":   {"name": "Violins I",     "program": 40},
            "Contralto_1": {"name": "Violas",        "program": 41},
            "Contralto_2": {"name": "Violas",        "program": 41},
            "Tenor_1":     {"name": "Violoncellos",  "program": 42},
            "Tenor_2":     {"name": "Violoncellos",  "program": 42},
            "Baixo_1":     {"name": "Contrabasses",  "program": 43},
            "Baixo_2":     {"name": "Contrabasses",  "program": 43}
        }
    },
    7: {
        "name": "Baroque Chamber Ensemble",
        "desc": "Foco Barroco - Cordas Solo sem Contrabaixo no Tenor",
        "map": {
            "Soprano_1":   {"name": "Solo Violin",   "program": 40},
            "Soprano_2":   {"name": "Solo Violin",   "program": 40},
            "Contralto_1": {"name": "Solo Violin",   "program": 40},
            "Contralto_2": {"name": "Solo Viola",    "program": 41},
            "Tenor_1":     {"name": "Solo Viola",    "program": 41},
            "Tenor_2":     {"name": "Solo Cello",    "program": 42},
            "Baixo_1":     {"name": "Solo Cello",    "program": 42},
            "Baixo_2":     {"name": "Solo Contrabass", "program": 43}
        }
    },
    8: {
        "name": "Pizzicato Ensemble",
        "desc": "Toda a Seção em Articulação Pizzicato Dedilhada",
        "map": {
            "Soprano_1":   {"name": "Pizzicato Strings", "program": 45},
            "Soprano_2":   {"name": "Pizzicato Strings", "program": 45},
            "Contralto_1": {"name": "Pizzicato Strings", "program": 45},
            "Contralto_2": {"name": "Pizzicato Strings", "program": 45},
            "Tenor_1":     {"name": "Pizzicato Strings", "program": 45},
            "Tenor_2":     {"name": "Pizzicato Strings", "program": 45},
            "Baixo_1":     {"name": "Pizzicato Strings", "program": 45},
            "Baixo_2":     {"name": "Pizzicato Strings", "program": 45}
        }
    },
    9: {
        "name": "Tremolo Ensemble",
        "desc": "Tensão e Mistério Cinematográfico - Tremolo contínuo",
        "map": {
            "Soprano_1":   {"name": "Tremolo Strings", "program": 44},
            "Soprano_2":   {"name": "Tremolo Strings", "program": 44},
            "Contralto_1": {"name": "Tremolo Strings", "program": 44},
            "Contralto_2": {"name": "Tremolo Strings", "program": 44},
            "Tenor_1":     {"name": "Tremolo Strings", "program": 44},
            "Tenor_2":     {"name": "Tremolo Strings", "program": 44},
            "Baixo_1":     {"name": "Tremolo Strings", "program": 44},
            "Baixo_2":     {"name": "Tremolo Strings", "program": 44}
        }
    },
    10: {
        "name": "Modern Cinematic Strings",
        "desc": "Graves Pesados e Agudos Brilhantes - Grande Amplitude de Panning",
        "map": {
            "Soprano_1":   {"name": "Violins I",     "program": 40},
            "Soprano_2":   {"name": "Violins I",     "program": 40},
            "Contralto_1": {"name": "Violins II",    "program": 40},
            "Contralto_2": {"name": "Violas",        "program": 41},
            "Tenor_1":     {"name": "Violas",        "program": 41},
            "Tenor_2":     {"name": "Violoncellos",  "program": 42},
            "Baixo_1":     {"name": "Violoncellos",  "program": 42},
            "Baixo_2":     {"name": "Contrabasses",  "program": 43}
        }
    },
    11: {
        "name": "Quarteto Dobrado Lírico",
        "desc": "Combinação Suave e Romântica - Mescla de Solo e Seção Clássica",
        "map": {
            "Soprano_1":   {"name": "Solo Violin",   "program": 40},
            "Soprano_2":   {"name": "Violins II",    "program": 40},
            "Contralto_1": {"name": "Solo Viola",    "program": 41},
            "Contralto_2": {"name": "Violas",        "program": 41},
            "Tenor_1":     {"name": "Solo Cello",    "program": 42},
            "Tenor_2":     {"name": "Violoncellos",  "program": 42},
            "Baixo_1":     {"name": "Solo Contrabass", "program": 43},
            "Baixo_2":     {"name": "Contrabasses",  "program": 43}
        }
    },
    12: {
        "name": "Pastoral Strings",
        "desc": "Contemplativa - Textura de Violoncellos e Violas com Harpa de Fundo",
        "map": {
            "Soprano_1":   {"name": "Harp",          "program": 46},
            "Soprano_2":   {"name": "Solo Violin",   "program": 40},
            "Contralto_1": {"name": "Violas",        "program": 41},
            "Contralto_2": {"name": "Violas",        "program": 41},
            "Tenor_1":     {"name": "Violoncellos",  "program": 42},
            "Tenor_2":     {"name": "Violoncellos",  "program": 42},
            "Baixo_1":     {"name": "Contrabasses",  "program": 43},
            "Baixo_2":     {"name": "Contrabasses",  "program": 43}
        }
    },
    13: {
        "name": "Antiga Catedral (Solemne)",
        "desc": "Registro Médio Densificado - Violins II, Violas, Violoncellos e Contrabaixos",
        "map": {
            "Soprano_1":   {"name": "Violins II",    "program": 40},
            "Soprano_2":   {"name": "Violas",        "program": 41},
            "Contralto_1": {"name": "Violas",        "program": 41},
            "Contralto_2": {"name": "Violoncellos",  "program": 42},
            "Tenor_1":     {"name": "Violoncellos",  "program": 42},
            "Tenor_2":     {"name": "Violoncellos",  "program": 42},
            "Baixo_1":     {"name": "Contrabasses",  "program": 43},
            "Baixo_2":     {"name": "Contrabasses",  "program": 43}
        }
    },
    14: {
        "name": "Sinfônica Romântica Pesada",
        "desc": "Destaque Violinos e Violas Dobrados para Máximo Volume",
        "map": {
            "Soprano_1":   {"name": "Violins I",     "program": 40},
            "Soprano_2":   {"name": "Violins I",     "program": 40},
            "Contralto_1": {"name": "Violins II",    "program": 40},
            "Contralto_2": {"name": "Violins II",    "program": 40},
            "Tenor_1":     {"name": "Violas",        "program": 41},
            "Tenor_2":     {"name": "Violoncellos",  "program": 42},
            "Baixo_1":     {"name": "Violoncellos",  "program": 42},
            "Baixo_2":     {"name": "Contrabasses",  "program": 43}
        }
    },
    15: {
        "name": "Solo vs Section Contrast",
        "desc": "Lado 1 Solistas Acústicos, Lado 2 Seção Sinfônica Completa",
        "map": {
            "Soprano_1":   {"name": "Solo Violin",   "program": 40},
            "Soprano_2":   {"name": "Violins I",     "program": 40},
            "Contralto_1": {"name": "Solo Viola",    "program": 41},
            "Contralto_2": {"name": "Violas",        "program": 41},
            "Tenor_1":     {"name": "Solo Cello",    "program": 42},
            "Tenor_2":     {"name": "Violoncellos",  "program": 42},
            "Baixo_1":     {"name": "Solo Contrabass", "program": 43},
            "Baixo_2":     {"name": "Contrabasses",  "program": 43}
        }
    },
    16: {
        "name": "Tension Orchestral (Híbrido Tremolo)",
        "desc": "Metade das Vozes em Legato Normal, Metade em Tremolo Spooky",
        "map": {
            "Soprano_1":   {"name": "Violins I",     "program": 40},
            "Soprano_2":   {"name": "Tremolo Strings", "program": 44},
            "Contralto_1": {"name": "Violas",        "program": 41},
            "Contralto_2": {"name": "Tremolo Strings", "program": 44},
            "Tenor_1":     {"name": "Violoncellos",  "program": 42},
            "Tenor_2":     {"name": "Tremolo Strings", "program": 44},
            "Baixo_1":     {"name": "Contrabasses",  "program": 43},
            "Baixo_2":     {"name": "Tremolo Strings", "program": 44}
        }
    },
    17: {
        "name": "Cello Bass Heavy Ensemble",
        "desc": "Chamber Dark Ensemble - Solo Violin/Viola, Solo Cellos e Contrabaixos",
        "map": {
            "Soprano_1":   {"name": "Solo Violin",   "program": 40},
            "Soprano_2":   {"name": "Solo Viola",    "program": 41},
            "Contralto_1": {"name": "Solo Viola",    "program": 41},
            "Contralto_2": {"name": "Solo Cello",    "program": 42},
            "Tenor_1":     {"name": "Solo Cello",    "program": 42},
            "Tenor_2":     {"name": "Solo Cello",    "program": 42},
            "Baixo_1":     {"name": "Solo Contrabass", "program": 43},
            "Baixo_2":     {"name": "Solo Contrabass", "program": 43}
        }
    },
    18: {
        "name": "High Soaring Strings (Sem Contrabaixo)",
        "desc": "Aéreo e Brilhante - Foco em Violinos/Violas, Violoncellos no Baixo",
        "map": {
            "Soprano_1":   {"name": "Violins I",     "program": 40},
            "Soprano_2":   {"name": "Violins I",     "program": 40},
            "Contralto_1": {"name": "Violins II",    "program": 40},
            "Contralto_2": {"name": "Violins II",    "program": 40},
            "Tenor_1":     {"name": "Violas",        "program": 41},
            "Tenor_2":     {"name": "Violas",        "program": 41},
            "Baixo_1":     {"name": "Violoncellos",  "program": 42},
            "Baixo_2":     {"name": "Violoncellos",  "program": 42}
        }
    },
    19: {
        "name": "Dreamy Harp & Strings",
        "desc": "Lírico e Etereo - Harpa Solo no Soprano, Solistas legatos e base",
        "map": {
            "Soprano_1":   {"name": "Harp",          "program": 46},
            "Soprano_2":   {"name": "Solo Violin",   "program": 40},
            "Contralto_1": {"name": "Solo Viola",    "program": 41},
            "Contralto_2": {"name": "Violins II",    "program": 40},
            "Tenor_1":     {"name": "Violas",        "program": 41},
            "Tenor_2":     {"name": "Solo Cello",    "program": 42},
            "Baixo_1":     {"name": "Violoncellos",  "program": 42},
            "Baixo_2":     {"name": "Contrabasses",  "program": 43}
        }
    },
    20: {
        "name": "Sinfônica Total (Dense Strings)",
        "desc": "Máximo de Cordas Sinfônicas em Uníssono para Grande Densidade",
        "map": {
            "Soprano_1":   {"name": "Violins I",     "program": 40},
            "Soprano_2":   {"name": "Violins II",    "program": 40},
            "Contralto_1": {"name": "Violas",        "program": 41},
            "Contralto_2": {"name": "Violas",        "program": 41},
            "Tenor_1":     {"name": "Violoncellos",  "program": 42},
            "Tenor_2":     {"name": "Violoncellos",  "program": 42},
            "Baixo_1":     {"name": "Contrabasses",  "program": 43},
            "Baixo_2":     {"name": "Contrabasses",  "program": 43}
        }
    }
}

# Parâmetros Globais de Expressividade Física (Volume/Sopro Humano adaptado para Arco de Cordas)
EXPR_BASE_VOLUME = 70      # Volume base para a pressão do arco (CC11)
EXPR_AMPLITUDE   = 35      # Amplitude do swell do arco
SAMPLING_STEP_TICKS = 40   # Intervalo em ticks para amostragem dos eventos CC11

def process_midi_to_8part_math(input_path, output_path, mapping, use_expression=True, speed=1.0):
    """
    Processa um arquivo MIDI SATB de 4 canais dividindo em 8 partes (Soprano 1/2, Contralto 1/2, etc.)
    e aplicando as mesmas fórmulas matemáticas para humanização:
    
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
    
    # Detectar canais originais do MIDI SATB
    active_channels = set()
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'note_on' and msg.velocity > 0:
                active_channels.add(msg.channel)
    sorted_channels = sorted(list(active_channels))
    
    voices = ["Soprano", "Contralto", "Tenor", "Baixo"]
    channel_to_voice = {sorted_channels[i]: voices[i] for i in range(min(len(sorted_channels), len(voices)))}
    
    # Tentar capturar a fórmula de compasso (Time Signature)
    numerator = 4
    measure_ticks = 4 * ticks_per_beat
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'time_signature':
                if msg.numerator > 1:
                    numerator = msg.numerator
                    measure_ticks = numerator * ticks_per_beat
                    break
                
    new_mid = mido.MidiFile()
    new_mid.ticks_per_beat = ticks_per_beat
    
    # Copia a trilha de metadados (Track 0)
    meta_track = mido.MidiTrack()
    new_mid.tracks.append(meta_track)
    
    # Coleta todas as mensagens meta em tempos absolutos
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
                
    # Configuração dos 8 instrumentos e da espacialização (Lado 1 esq = 48, Lado 2 dir = 80)
    instruments_config = [
        {"voice": "Soprano",   "pan": 48, "inst": mapping["Soprano_1"]},
        {"voice": "Soprano",   "pan": 80, "inst": mapping["Soprano_2"]},
        {"voice": "Contralto", "pan": 48, "inst": mapping["Contralto_1"]},
        {"voice": "Contralto", "pan": 80, "inst": mapping["Contralto_2"]},
        {"voice": "Tenor",     "pan": 48, "inst": mapping["Tenor_1"]},
        {"voice": "Tenor",     "pan": 80, "inst": mapping["Tenor_2"]},
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
                    
            # Agrupa note_on e note_off
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
            
            # Duplica os eventos meta de tempo e compasso na track de notas
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
                
                pos_in_measure = on_time_new % measure_ticks
                if pos_in_measure < (ticks_per_beat * 0.1):
                    v_acento = 10
                else:
                    v_acento = -5
                    
                v_novo = v_base + v_aleatorio + v_acento
                
                # Reduz em 10% se for Contralto ou Tenor
                if voice_name in ["Contralto", "Tenor"]:
                    v_novo = int(v_novo * 0.9)
                    
                v_final = max(1, min(127, v_novo))
                
                # Cria eventos note_on e note_off
                note_on_msg = mido.Message('note_on', channel=midi_channel, note=note_num, velocity=v_final, time=on_time_new)
                note_off_msg = mido.Message('note_off', channel=midi_channel, note=note_num, velocity=0, time=off_time_new)
                
                processed_abs_events.append(note_on_msg)
                processed_abs_events.append(note_off_msg)
                
                # 3. Curva de volume / expressividade (CC11)
                if use_expression and duration >= ticks_per_beat:
                    for t_step in range(0, duration + 1, SAMPLING_STEP_TICKS):
                        factor = math.sin(math.pi * (t_step / duration))
                        e_val = EXPR_BASE_VOLUME + EXPR_AMPLITUDE * factor
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
    ap = argparse.ArgumentParser(description="MuseScore 4 Math Orchestrator: Coral 8 Partes Cordas (Strings)")
    ap.add_argument("--midi",       default=None,           help="MIDI de entrada específico")
    ap.add_argument("--preset",     type=int, default=1,    help="Número do preset de cordas (1 a 20). Padrão = 1 (Sinfônica Clássica)")
    ap.add_argument("--output",     default="strings",      help="Pasta de saída para os arquivos MP3")
    ap.add_argument("--soundfonts", default="/Users/jonaspoli/Documents/MuseScore4/SoundFonts/Muse Hub Instruments", 
                    help="Caminho para os instrumentos das Muse Sounds")
    ap.add_argument("--no-expression", action="store_true", help="Desativa a expressão dinâmica por curva de seno (CC11)")
    ap.add_argument("--speed",       type=float, default=1.0, help="Fator de velocidade/tempo (ex: 0.85 para deixar 15% mais lento)")
    args = ap.parse_args()
    
    os.makedirs(args.output, exist_ok=True)
    
    if args.preset not in STRINGS_PRESETS:
        print(f"ERRO: Preset {args.preset} inválido. Escolha de 1 a 20.")
        sys.exit(1)
        
    preset = STRINGS_PRESETS[args.preset]
    print("════════════════════════════════════════════════════════════")
    print(f"  Orquestrador de Cordas — Preset {args.preset}: {preset['name']}")
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
        
        if os.path.exists(out_mp3) and not args.midi:
            print(f"[{idx}/{total}] ✓ (já existe) {name}")
            continue
            
        print(f"[{idx}/{total}] ▶ {name}...", end="", flush=True)
        temp_midi = os.path.join(args.output, "temp_render_strings_math.mid")
        
        try:
            create_expression = not args.no_expression
            process_midi_to_8part_math(path, temp_midi, preset["map"], use_expression=create_expression, speed=args.speed)
            
            render_score(temp_midi, out_mp3, args.soundfonts)
            
            if os.path.exists(temp_midi):
                os.remove(temp_midi)
            print(" ✓ concluído")
        except Exception as e:
            if os.path.exists(temp_midi):
                os.remove(temp_midi)
            print(f" ✗ FALHOU (erro: {e})")
 
    print("\n✓ Processamento de cordas finalizado!")

if __name__ == "__main__":
    main()
