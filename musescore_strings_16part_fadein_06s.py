import mido
import os
import random
import math
import argparse
import subprocess
import glob
import sys
import xml.etree.ElementTree as ET

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

# Controles MIDI usados para a curva de expressão/fade.
# 11 = Expression (padrão MIDI para volume musical)
# 1  = Modulation/Dynamics em algumas bibliotecas, incluindo alguns fluxos com Muse Sounds.
# Por padrão, enviamos nos dois para manter compatibilidade e garantir o fade real de volume.
DEFAULT_EXPR_CONTROLS = [11, 1]
DEFAULT_FADE_IN_SECONDS = 0.60
DEFAULT_PAUSE_THRESHOLD_SECONDS = 0.45
DEFAULT_FADE_RESOLUTION_MS = 10.0
DEFAULT_ATTACK_VELOCITY_SCALE = 0.42
DEFAULT_MIN_ATTACK_VELOCITY = 18
DEFAULT_MAX_FADE_NOTE_RATIO = 0.85

# Coeficientes de normalização de volume para balancear timbres da biblioteca Muse Sounds
VOLUME_MODIFIERS = {
    "Violins 1": 1.0,
    "Violins 2": 1.0,
    "Violin 1 (Solo)": 1.0,
    "Violin 2 (Solo)": 1.0,
    "Violas": 0.68,
    "Viola (Solo)": 0.68,
    "Violoncellos": 1.0,
    "Violoncello (Solo)": 1.0,
    "Contrabasses": 1.0,
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

def clamp_midi(value):
    return max(1, min(127, int(round(value))))

def parse_cc_list(raw_value):
    """Aceita "11", "1", "11,1" etc. e devolve lista única de CCs válidos."""
    if raw_value is None:
        return list(DEFAULT_EXPR_CONTROLS)
    if isinstance(raw_value, (list, tuple)):
        values = raw_value
    else:
        values = str(raw_value).replace(';', ',').split(',')
    controls = []
    for item in values:
        item = str(item).strip()
        if not item:
            continue
        cc = int(item)
        if not 0 <= cc <= 127:
            raise ValueError(f"Controle MIDI inválido: {cc}. Use valores entre 0 e 127.")
        if cc not in controls:
            controls.append(cc)
    return controls or list(DEFAULT_EXPR_CONTROLS)

def smoothstep(x):
    """Curva suave 0→1, sem quina no início nem no fim do fade."""
    x = max(0.0, min(1.0, float(x)))
    return x * x * (3.0 - 2.0 * x)

def get_effective_fade_ticks(duration, tempo, ticks_per_beat, fade_in_seconds, max_note_ratio=DEFAULT_MAX_FADE_NOTE_RATIO):
    wanted = max(1, seconds_to_ticks(fade_in_seconds, tempo, ticks_per_beat))
    # Evita que uma nota curta desapareça inteira no fade.
    allowed_by_note = max(1, int(duration * max_note_ratio))
    return max(1, min(wanted, allowed_by_note))

def get_cc_sample_ticks(
    duration,
    tempo,
    ticks_per_beat,
    is_after_pause,
    fade_in_seconds=DEFAULT_FADE_IN_SECONDS,
    fade_resolution_ms=DEFAULT_FADE_RESOLUTION_MS,
):
    steps = set()
    steps.add(0)
    steps.add(max(0, duration))

    if duration <= 0:
        return [0]

    if is_after_pause:
        fade_win_ticks = get_effective_fade_ticks(duration, tempo, ticks_per_beat, fade_in_seconds)
        step_ticks = max(1, int(seconds_to_ticks(fade_resolution_ms / 1000.0, tempo, ticks_per_beat)))

        # Alta resolução no ataque, pois é aqui que a nota estava soando seca.
        t = 0
        while t < fade_win_ticks and t <= duration:
            steps.add(t)
            t += step_ticks
        steps.add(min(fade_win_ticks, duration))

        # Depois do fade, volta para a amostragem normal da curva musical.
        t = fade_win_ticks
        while t < duration:
            steps.add(t)
            t += SAMPLING_STEP_TICKS
    else:
        t = 0
        while t < duration:
            steps.add(t)
            t += SAMPLING_STEP_TICKS

    return sorted(steps)


def process_midi_to_16part_math(
    input_path,
    output_path,
    mapping,
    use_expression=True,
    speed=1.0,
    fade_in_seconds=DEFAULT_FADE_IN_SECONDS,
    pause_threshold_seconds=DEFAULT_PAUSE_THRESHOLD_SECONDS,
    fade_controls=None,
    fade_resolution_ms=DEFAULT_FADE_RESOLUTION_MS,
    attack_velocity_scale=DEFAULT_ATTACK_VELOCITY_SCALE,
    min_attack_velocity=DEFAULT_MIN_ATTACK_VELOCITY,
    cc7_volume=35,
):
    mid = mido.MidiFile(input_path)
    ticks_per_beat = mid.ticks_per_beat
    fade_controls = parse_cc_list(fade_controls)
    
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

    # O arquivo de saída muda o tempo pelo parâmetro --speed.
    # Portanto, qualquer cálculo em segundos precisa usar o tempo final/renderizado.
    render_tempo = int(tempo / speed) if speed != 1.0 else tempo
                
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
        voice_track.append(mido.Message('control_change', channel=midi_channel, control=7, value=cc7_volume, time=0))
        voice_track.append(mido.Message('control_change', channel=midi_channel, control=11, value=cc7_volume, time=0))
        
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
            for i, note_info in enumerate(notes):
                on_time = note_info["on_time"]
                off_time = note_info["off_time"]
                v_base = note_info["velocity"]
                
                # 1. Timing delay
                sub_num = int(conf["sub_key"].split("_")[-1])
                delay_sec = (sub_num - 1) * 0.020
                    
                delay_ticks = seconds_to_ticks(delay_sec, render_tempo, ticks_per_beat)
                
                note_info["on_time_new"] = max(0, on_time + delay_ticks)
                
                # A duração original deve ser preservada rigorosamente para evitar som de staccato
                duration_original = off_time - on_time
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
                if voice_name == "Baixo":
                    note_info["total_mult"] *= 1.30
                note_info["v_final"] = max(1, min(127, int(v_novo * note_info["total_mult"] * (cc7_volume / 100.0))))
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
                    curr_note["off_time_new"] = max(curr_note["on_time_new"] + 10, next_note["on_time_new"])

            # Passagem 4: Geração das mensagens MIDI finais
            for i, note_info in enumerate(notes):
                note_num = note_info["note"]
                on_time = note_info["on_time"]
                off_time = note_info["off_time"]
                on_time_new = note_info["on_time_new"]
                off_time_new = note_info["off_time_new"]
                v_final = note_info["v_final"]
                total_mult = note_info["total_mult"]
                phrase_idx = note_info["phrase_idx"]
                duration = off_time_new - on_time_new
                
                # Detecta retomada após pausa de forma genérica, em segundos reais do áudio final.
                # Isso funciona em lote para qualquer hino, sem depender de compasso/verso fixo.
                gap_ticks = None if i == 0 else max(0, on_time - notes[i-1]["off_time"])
                gap_seconds = None if gap_ticks is None else ticks_to_seconds(gap_ticks, render_tempo, ticks_per_beat)
                is_after_pause = (i == 0) or (gap_seconds is not None and gap_seconds >= pause_threshold_seconds)
                
                # Detecta se é uma nota antes de pausa de forma genérica
                gap_next_ticks = None if i == len(notes) - 1 else max(0, notes[i+1]["on_time"] - off_time)
                gap_next_seconds = None if gap_next_ticks is None else ticks_to_seconds(gap_next_ticks, render_tempo, ticks_per_beat)
                is_before_pause = (gap_next_seconds is not None and gap_next_seconds >= pause_threshold_seconds)
                
                v_final_note = v_final
                if is_after_pause:
                    # Não usa velocity 10 fixa: em alguns bancos isso pode soar artificial.
                    # Mantém ataque suave, mas ainda com corpo suficiente para cordas.
                    v_final_note = max(min_attack_velocity, int(v_final * attack_velocity_scale))
                    v_final_note = min(127, v_final_note)
                
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
                        v_final_high = max(min_attack_velocity, int(v_final_high * attack_velocity_scale))
                        v_final_high = min(127, v_final_high)
                    
                    # Inicialização explícita do programa e do pan
                    if high_note_channel not in initialized_channels:
                        high_program = 40 if high_note_channel in [0, 1] else 41
                        high_pan = 30 if high_note_channel == 0 else (48 if high_note_channel == 1 else (76 if high_note_channel == 6 else 94))
                        
                        prog_msg = mido.Message('program_change', channel=high_note_channel, program=high_program, time=0)
                        pan_msg = mido.Message('control_change', channel=high_note_channel, control=10, value=high_pan, time=0)
                        vol_msg = mido.Message('control_change', channel=high_note_channel, control=7, value=cc7_volume, time=0)
                        expr_msg = mido.Message('control_change', channel=high_note_channel, control=11, value=cc7_volume, time=0)
                        
                        processed_abs_events.append(prog_msg)
                        processed_abs_events.append(pan_msg)
                        processed_abs_events.append(vol_msg)
                        processed_abs_events.append(expr_msg)
                        initialized_channels.add(high_note_channel)
                        
                    note_on_high = mido.Message('note_on', channel=high_note_channel, note=note_num_high, velocity=v_final_high, time=on_time_new)
                    note_off_high = mido.Message('note_off', channel=high_note_channel, note=note_num_high, velocity=0, time=off_time_new)
                    
                    processed_abs_events.append(note_on_high)
                    processed_abs_events.append(note_off_high)
                    
                # 3. Curva de expressão/volume.
                # Em retomadas após pausa, faz fade-in real de ~0.6s por CC11/CC1.
                if use_expression and (duration >= ticks_per_beat or is_after_pause):
                    sample_steps = get_cc_sample_ticks(
                        duration,
                        render_tempo,
                        ticks_per_beat,
                        is_after_pause,
                        fade_in_seconds=fade_in_seconds,
                        fade_resolution_ms=fade_resolution_ms,
                    )
                    fade_win_ticks = get_effective_fade_ticks(duration, render_tempo, ticks_per_beat, fade_in_seconds)

                    for t_step in sample_steps:
                        factor = math.sin(math.pi * (t_step / duration)) if duration > 0 else 0
                        target_e_val = (EXPR_BASE_VOLUME + EXPR_AMPLITUDE * factor) * total_mult
                        e_val = target_e_val

                        if is_after_pause:
                            fade_pos = 1.0 if fade_win_ticks <= 0 else (t_step / fade_win_ticks)
                            fade_factor = smoothstep(fade_pos)
                            e_val = target_e_val * fade_factor
                            if t_step == 0:
                                e_val = 1.0
                                
                        # 3. Aplica rampa de descida (fade-out) no final da nota se ela precede uma pausa
                        if is_before_pause:
                            fade_out_win_ms = 300.0
                            fade_out_win_ticks = seconds_to_ticks(fade_out_win_ms / 1000.0, render_tempo, ticks_per_beat)
                            t_rem = duration - t_step
                            if t_rem < fade_out_win_ticks and fade_out_win_ticks > 0:
                                ratio = t_rem / fade_out_win_ticks
                                ratio_smooth = ratio * ratio * (3.0 - 2.0 * ratio)
                                e_val = 1.0 + (e_val - 1.0) * ratio_smooth

                        e_final = clamp_midi(e_val * (cc7_volume / 100.0))
                        cc_time = on_time_new + t_step

                        for control_id in fade_controls:
                            cc_msg = mido.Message(
                                'control_change',
                                channel=midi_channel,
                                control=control_id,
                                value=e_final,
                                time=cc_time
                            )
                            processed_abs_events.append(cc_msg)

                            # Se houver nota oitavada ativa em outro canal, envia a expressão para ela também.
                            if high_note_velocity > 0 and high_note_channel != midi_channel:
                                cc_high = mido.Message(
                                    'control_change',
                                    channel=high_note_channel,
                                    control=control_id,
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

def inject_dynamic_to_mscx(mscx_path, velocity_value):
    tree = ET.parse(mscx_path)
    root = tree.getroot()
    
    # Mapear quais IDs de Staff são do Baixo/Contrabaixo sequencialmente
    bass_staff_ids = set()
    current_staff_idx = 0
    parts = root.findall('.//Part')
    for part in parts:
        track_name_elem = part.find('trackName')
        track_name = track_name_elem.text if track_name_elem is not None else ""
        is_bass = any(keyword in track_name.lower() for keyword in ["contrabass", "contrabaixo", "cb.", "baixo", "bass"])
        for staff in part.findall('Staff'):
            current_staff_idx += 1
            if is_bass:
                bass_staff_ids.add(str(current_staff_idx))
                
    # Fallback: Se não detectou por nome, assume que as últimas 4 staves são a 4ª voz (baixo/contrabaixo)
    if not bass_staff_ids and current_staff_idx >= 4:
        for idx in range(current_staff_idx - 3, current_staff_idx + 1):
            bass_staff_ids.add(str(idx))
            
    staffs = root.findall('.//Staff')
    for staff in staffs:
        staff_id = staff.get('id')
        is_bass_staff = (staff_id in bass_staff_ids)
            
        measure = staff.find('.//Measure')
        if measure is not None:
            voice = measure.find('.//voice')
            if voice is not None:
                if voice.find('.//Dynamic') is None:
                    dynamic = ET.Element('Dynamic')
                    subtype = ET.SubElement(dynamic, 'subtype')
                    subtype.text = 'p'
                    vel_elem = ET.SubElement(dynamic, 'velocity')
                    
                    # Se for baixo/contrabaixo, aumenta o volume da dinâmica em ~30%
                    if is_bass_staff:
                        vel_val = min(127, int(velocity_value * 1.30))
                    else:
                        vel_val = velocity_value
                        
                    vel_elem.text = str(vel_val)
                    voice.insert(0, dynamic)
                    
    tree.write(mscx_path, encoding='UTF-8', xml_declaration=True)

def render_score(midi_path, output_mp3, soundfonts_dir, musescore_bin, cc7_volume=35):
    my_env = os.environ.copy()
    my_env["MUSESAMPLER_INSTRUMENT_FOLDER"] = soundfonts_dir

    if not os.path.exists(musescore_bin):
        raise FileNotFoundError(f"MuseScore não encontrado em: {musescore_bin}")

    # Define temporary MSCX path
    base_path = os.path.splitext(midi_path)[0]
    mscx_path = base_path + "_temp.mscx"

    try:
        # 1. Export MIDI to MSCX
        subprocess.run([
            musescore_bin,
            "-o", mscx_path,
            midi_path
        ], env=my_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # 2. Inject dynamic into MSCX
        try:
            inject_dynamic_to_mscx(mscx_path, cc7_volume)
        except Exception as e:
            print(f"\n[AVISO] Falha ao injetar dinâmica no XML ({e}). Renderizando padrão...")

        # 3. Render MSCX to MP3 with MuseSounds sound profile
        subprocess.run([
            musescore_bin,
            "--sound-profile", "MuseSounds",
            "-o", output_mp3,
            mscx_path
        ], env=my_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    finally:
        # 4. Clean up temporary MSCX file
        if os.path.exists(mscx_path):
            os.remove(mscx_path)

def main():
    ap = argparse.ArgumentParser(description="MuseScore 4 Math Orchestrator: Coral 16 Instrumentos")
    ap.add_argument("--midi",       default=None,           help="MIDI de entrada específico. Use para testar apenas 1 arquivo.")
    ap.add_argument("--midi-glob",  default="mid/*.mid",   help="Padrão de busca para lote quando --midi não for usado. Ex.: 'mid/*.mid'")
    ap.add_argument("--preset",     type=int, default=1,    help="Número do preset de 16 cordas (1 a 9)")
    ap.add_argument("--output",     default="output_strings_16part", help="Pasta de saída para os arquivos MIDI/MP3")
    ap.add_argument("--soundfonts", default="/Users/jonaspoli/Documents/MuseScore4/SoundFonts/Muse Hub Instruments",
                    help="Caminho para os instrumentos das Muse Sounds")
    ap.add_argument("--musescore-bin", default="/Applications/MuseScore 4.app/Contents/MacOS/mscore",
                    help="Caminho do executável do MuseScore 4")
    ap.add_argument("--speed",       type=float, default=0.9, help="Fator de velocidade (padrão 0.9 = 90% da velocidade original)")
    ap.add_argument("--volume",     type=int, default=35,    help="Fator de volume geral em porcentagem para evitar clipar (1 a 100). Padrão: 35")

    # Fade-in genérico para retomadas depois de pausa.
    ap.add_argument("--fade-in", type=float, default=DEFAULT_FADE_IN_SECONDS,
                    help="Duração do fade-in após pausa, em segundos. Padrão: 0.60")
    ap.add_argument("--pause-threshold", type=float, default=DEFAULT_PAUSE_THRESHOLD_SECONDS,
                    help="Pausa mínima, em segundos, para aplicar o fade-in. Padrão: 0.45")
    ap.add_argument("--fade-controls", default=",".join(map(str, DEFAULT_EXPR_CONTROLS)),
                    help="CCs MIDI usados na curva. Padrão: 11,1. Use 11 se quiser apenas Expression.")
    ap.add_argument("--fade-resolution-ms", type=float, default=DEFAULT_FADE_RESOLUTION_MS,
                    help="Resolução dos pontos do fade, em milissegundos. Padrão: 10")
    ap.add_argument("--attack-velocity-scale", type=float, default=DEFAULT_ATTACK_VELOCITY_SCALE,
                    help="Multiplicador da velocity da primeira nota após pausa. Padrão: 0.42")
    ap.add_argument("--min-attack-velocity", type=int, default=DEFAULT_MIN_ATTACK_VELOCITY,
                    help="Velocity mínima da primeira nota após pausa. Padrão: 18")
    ap.add_argument("--no-render", action="store_true",
                    help="Gera apenas o MIDI orquestrado, sem chamar o MuseScore para criar MP3.")
    args = ap.parse_args()
    
    os.makedirs(args.output, exist_ok=True)
    
    if args.preset not in STRINGS_16PART_PRESETS:
        print(f"ERRO: Preset {args.preset} inválido. Escolha de 1 a 9.")
        sys.exit(1)
        
    preset = STRINGS_16PART_PRESETS[args.preset]
    print("════════════════════════════════════════════════════════════")
    print(f"  Orquestrador 16 Cordas — Preset {args.preset}: {preset['name']}")
    print(f"  Descrição: {preset['desc']}")
    print(f"  Velocidade: {args.speed}x ({int(round(args.speed * 100))}%)")
    print(f"  Fade após pausa: {args.fade_in:.2f}s | pausa mínima: {args.pause_threshold:.2f}s | CCs: {args.fade_controls}")
    print("════════════════════════════════════════════════════════════\n")
    
    # Coleta arquivos MIDI: 1 arquivo em teste ou lote completo para centenas de hinos.
    midi_files = [args.midi] if args.midi else sorted(glob.glob(args.midi_glob))
    total = len(midi_files)
    
    if total == 0:
        print(f"Nenhum arquivo MIDI encontrado usando o padrão: {args.midi_glob}")
        sys.exit(1)
        
    for idx, path in enumerate(midi_files, 1):
        name = os.path.splitext(os.path.basename(path))[0]
        speed_suffix = f"speed{int(round(args.speed * 100))}"
        out_mp3 = os.path.join(args.output, f"{name}_preset{args.preset}_16part_{speed_suffix}.mp3")
        out_mid = os.path.join(args.output, f"{name}_preset{args.preset}_16part_{speed_suffix}.mid")
        
        print(f"[{idx}/{total}] ▶ {name}...", end="", flush=True)
        
        try:
            process_midi_to_16part_math(
                path,
                out_mid,
                preset["map"],
                use_expression=True,
                speed=args.speed,
                fade_in_seconds=args.fade_in,
                pause_threshold_seconds=args.pause_threshold,
                fade_controls=args.fade_controls,
                fade_resolution_ms=args.fade_resolution_ms,
                attack_velocity_scale=args.attack_velocity_scale,
                min_attack_velocity=args.min_attack_velocity,
                cc7_volume=args.volume,
            )
            
            if args.no_render:
                print(" ✓ MIDI gerado")
            else:
                render_score(out_mid, out_mp3, args.soundfonts, args.musescore_bin, cc7_volume=args.volume)
                print(" ✓ MP3 concluído")
        except Exception as e:
            print(f" ✗ FALHOU (erro: {e})")
 
    print("\n✓ Processamento de 16 instrumentos concluído!")

if __name__ == "__main__":
    main()
