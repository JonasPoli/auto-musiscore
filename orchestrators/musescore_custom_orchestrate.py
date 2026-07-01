#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orquestrador customizado para os novos modelos de sons:
- Musicbox (Caixa de música com Soprano oitavado no último verso)
- Reeds (Orquestra de paletas reconfigurável por verso)
- Woodwinds (Orquestra de madeira reconfigurável por verso)
- Piano (Piano realista com Soprano e Contralto oitavados no último verso a 75% volume)
- Equinox (Piano realista tipo Equinox a 80% de velocidade)
"""

import os
import sys
import mido
import math
import random
import argparse
import subprocess
from pathlib import Path

# Utilitários de humanização compartilhados
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))
from midi_humanize import remove_staccato

# Configuração da raiz do projeto
ROOT = Path(__file__).parent.parent.absolute()

def seconds_to_ticks(seconds, tempo, ticks_per_beat):
    return int((seconds * 1000000.0 * ticks_per_beat) / tempo)

def get_pitch_stats(mid, sorted_channels):
    pitch_stats = {}
    for ch in sorted_channels:
        notes = []
        for track in mid.tracks:
            for msg in track:
                if not msg.is_meta and msg.type == 'note_on' and msg.channel == ch and msg.velocity > 0:
                    notes.append(msg.note)
        pitch_stats[ch] = sum(notes) / len(notes) if notes else 64
    return pitch_stats

def process_midi_to_custom(input_path, output_midi_path, model, speed=1.0):
    mid = mido.MidiFile(input_path)
    ticks_per_beat = mid.ticks_per_beat
    
    # 1. Detectar canais e mapear para vozes SATB
    active_channels = set()
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'note_on' and msg.velocity > 0:
                active_channels.add(msg.channel)
    sorted_channels = sorted(list(active_channels))
    
    voices = ["Soprano", "Contralto", "Tenor", "Baixo"]
    channel_to_voice = {sorted_channels[i]: voices[i] for i in range(min(len(sorted_channels), len(voices)))}
    
    # 2. Descobrir tempo
    tempo = 500000
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'set_tempo':
                tempo = msg.tempo
                break

    # 3. Detectar limites do último verso
    max_on_time = 0
    for track in mid.tracks:
        curr_time = 0
        for msg in track:
            curr_time += msg.time
            if msg.type == 'note_on' and msg.velocity > 0:
                if curr_time > max_on_time:
                    max_on_time = curr_time

    filename_base = os.path.basename(input_path)
    if "002-" in filename_base and not "Coro" in filename_base:
        intro_end = 4320
        verse_len = 15840
        last_verse_start = 36000
    else:
        if max_on_time < 10000:
            intro_end = 0
            verse_len = max_on_time // 3
            last_verse_start = verse_len * 2
        else:
            intro_end = int(max_on_time * 0.08)
            verse_len = (max_on_time - intro_end) // 3
            last_verse_start = intro_end + verse_len * 2

    # 4. Criar novo arquivo MIDI
    new_mid = mido.MidiFile()
    new_mid.ticks_per_beat = ticks_per_beat
    
    # Adicionar trilha de metadados
    meta_track = mido.MidiTrack()
    new_mid.tracks.append(meta_track)
    for track in mid.tracks:
        for msg in track:
            if msg.is_meta and msg.type in ['set_tempo', 'time_signature', 'key_signature']:
                msg_copy = msg.copy()
                if msg_copy.type == 'set_tempo' and speed != 1.0:
                    msg_copy.tempo = int(msg_copy.tempo / speed)
                meta_track.append(msg_copy)

    # 5. Configurar instrumentos e canais de acordo com o modelo
    if model == "musicbox":
        channels_config = [
            {"voice": "Soprano",   "pan": 48, "program": 8,  "name": "Celesta", "octave": 0, "verse_active": "all", "vol": 80},
            {"voice": "Contralto", "pan": 56, "program": 8,  "name": "Celesta", "octave": 0, "verse_active": "all", "vol": 70},
            {"voice": "Tenor",     "pan": 72, "program": 8,  "name": "Celesta", "octave": 0, "verse_active": "all", "vol": 70},
            {"voice": "Baixo",     "pan": 80, "program": 8,  "name": "Celesta", "octave": 0, "verse_active": "all", "vol": 80},
            {"voice": "Soprano",   "pan": 32, "program": 8,  "name": "Celesta (8ve)", "octave": 12, "verse_active": "last", "vol": 70}
        ]
    elif model in ["piano", "equinox"]:
        channels_config = [
            {"voice": "Soprano",   "pan": 60, "program": 0,  "name": "Acoustic Grand Piano", "octave": 0, "verse_active": "all", "vol": 90},
            {"voice": "Contralto", "pan": 56, "program": 0,  "name": "Acoustic Grand Piano", "octave": 0, "verse_active": "all", "vol": 80},
            {"voice": "Tenor",     "pan": 72, "program": 0,  "name": "Acoustic Grand Piano", "octave": 0, "verse_active": "all", "vol": 80},
            {"voice": "Baixo",     "pan": 68, "program": 0,  "name": "Acoustic Grand Piano", "octave": 0, "verse_active": "all", "vol": 90},
            {"voice": "Soprano",   "pan": 48, "program": 0,  "name": "Acoustic Grand Piano (8ve)", "octave": 12, "verse_active": "last", "vol": 68}, # 75% do volume original (90 * 0.75 ≈ 68)
            {"voice": "Contralto", "pan": 80, "program": 0,  "name": "Acoustic Grand Piano (8ve)", "octave": 12, "verse_active": "last", "vol": 60}  # 75% do volume original (80 * 0.75 ≈ 60)
        ]
    elif model == "reeds":
        # Paletas reconfiguráveis: Oboe (68), English Horn (69), Clarinet (71), Bassoon (70)
        channels_config = [
            # Soprano Oboe (V1/V3) e Clarinet (V2)
            {"voice": "Soprano",   "pan": 48, "program": 68, "name": "Oboe", "octave": 0, "verse_active": "v1_v3_last", "vol": 90},
            {"voice": "Soprano",   "pan": 48, "program": 71, "name": "Bb Clarinet", "octave": 0, "verse_active": "v2_last", "vol": 85},
            # Contralto Clarinet (V1), Oboe (V2), English Horn (V3)
            {"voice": "Contralto", "pan": 56, "program": 71, "name": "Bb Clarinet", "octave": 0, "verse_active": "v1", "vol": 80},
            {"voice": "Contralto", "pan": 56, "program": 68, "name": "Oboe", "octave": 0, "verse_active": "v2", "vol": 80},
            {"voice": "Contralto", "pan": 56, "program": 69, "name": "English Horn", "octave": 0, "verse_active": "last", "vol": 80},
            # Tenor English Horn (V1/V2), Clarinet (V3)
            {"voice": "Tenor",     "pan": 72, "program": 69, "name": "English Horn", "octave": 0, "verse_active": "v1_v2", "vol": 85},
            {"voice": "Tenor",     "pan": 72, "program": 71, "name": "Bb Clarinet", "octave": 0, "verse_active": "last", "vol": 80},
            # Baixo Fagote (Tudo)
            {"voice": "Baixo",     "pan": 80, "program": 70, "name": "Bassoon", "octave": 0, "verse_active": "all", "vol": 90}
        ]
    elif model == "woodwinds":
        # Madeiras reconfiguráveis: Flute (73), Oboe (68), Clarinet (71), Bassoon (70)
        channels_config = [
            # Soprano Flute (V1/V3/Last oitavada), Oboe (V2/Last normal)
            {"voice": "Soprano",   "pan": 45, "program": 73, "name": "Flute", "octave": 0, "verse_active": "v1", "vol": 90},
            {"voice": "Soprano",   "pan": 45, "program": 68, "name": "Oboe", "octave": 0, "verse_active": "v2_last", "vol": 85},
            {"voice": "Soprano",   "pan": 45, "program": 73, "name": "Flute (8ve)", "octave": 12, "verse_active": "last", "vol": 80},
            # Contralto Oboe (V1), Flute (V2), Clarinet (V3)
            {"voice": "Contralto", "pan": 56, "program": 68, "name": "Oboe", "octave": 0, "verse_active": "v1", "vol": 80},
            {"voice": "Contralto", "pan": 56, "program": 73, "name": "Flute", "octave": 0, "verse_active": "v2", "vol": 80},
            {"voice": "Contralto", "pan": 56, "program": 71, "name": "Bb Clarinet", "octave": 0, "verse_active": "last", "vol": 80},
            # Tenor Clarinet (V1/V2), Fagote (V3)
            {"voice": "Tenor",     "pan": 72, "program": 71, "name": "Bb Clarinet", "octave": 0, "verse_active": "v1_v2", "vol": 85},
            {"voice": "Tenor",     "pan": 72, "program": 70, "name": "Bassoon", "octave": 0, "verse_active": "last", "vol": 85},
            # Baixo Fagote (Tudo)
            {"voice": "Baixo",     "pan": 80, "program": 70, "name": "Bassoon", "octave": 0, "verse_active": "all", "vol": 90}
        ]

    # Processamento de notas de entrada
    notes_by_voice = {v: [] for v in voices}
    for ch, v in channel_to_voice.items():
        # Extrair notas cronológicas para esta voz
        active_notes = {}
        for track in mid.tracks:
            has_channel_msgs = any(not msg.is_meta and hasattr(msg, 'channel') and msg.channel == ch for msg in track)
            if not has_channel_msgs:
                continue
                
            curr_time = 0
            for msg in track:
                curr_time += msg.time
                if msg.type == 'note_on' and msg.velocity > 0 and msg.channel == ch:
                    active_notes[msg.note] = curr_time
                elif (msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0)) and msg.channel == ch:
                    if msg.note in active_notes:
                        on_t = active_notes.pop(msg.note)
                        notes_by_voice[v].append({
                            "note": msg.note,
                            "on_time": on_t,
                            "off_time": curr_time,
                            "velocity": msg.velocity
                        })
        notes_by_voice[v].sort(key=lambda x: x["on_time"])

    # 6. Preencher as novas trilhas
    for ch_idx, conf in enumerate(channels_config):
        track_name = conf["name"]
        voice_name = conf["voice"]
        midi_channel = ch_idx
        
        voice_track = mido.MidiTrack()
        new_mid.tracks.append(voice_track)
        
        # Iniciar track
        voice_track.append(mido.MetaMessage('track_name', name=track_name, time=0))
        voice_track.append(mido.Message('program_change', channel=midi_channel, program=conf["program"], time=0))
        voice_track.append(mido.Message('control_change', channel=midi_channel, control=10, value=conf["pan"], time=0))
        voice_track.append(mido.Message('control_change', channel=midi_channel, control=7, value=conf["vol"], time=0))
        voice_track.append(mido.Message('control_change', channel=midi_channel, control=11, value=127, time=0))
        
        input_notes = notes_by_voice[voice_name]
        processed_abs_events = []
        
        # Mapeamento do verso ativo
        active_rule = conf["verse_active"]
        
        # Filtra e aplica humanizações às notas
        valid_notes = []
        for i, note in enumerate(input_notes):
            on_time = note["on_time"]
            
            # Verificar se esta nota cai na regra de ativação por verso
            is_intro = (on_time < intro_end)
            is_v1 = (intro_end <= on_time < intro_end + verse_len)
            is_v2 = (intro_end + verse_len <= on_time < intro_end + 2 * verse_len)
            is_v3_or_last = (on_time >= intro_end + 2 * verse_len)
            
            should_play = False
            if active_rule == "all":
                should_play = True
            elif active_rule == "last":
                should_play = is_v3_or_last
            elif active_rule == "v1":
                should_play = is_intro or is_v1
            elif active_rule == "v2":
                should_play = is_v2
            elif active_rule == "v1_v2":
                should_play = is_intro or is_v1 or is_v2
            elif active_rule == "v1_v3_last":
                should_play = is_intro or is_v1 or is_v3_or_last
            elif active_rule == "v2_last":
                should_play = is_v2 or is_v3_or_last
                
            if not should_play:
                continue
                
            valid_notes.append(note.copy())
            
        # Aplicar humanizações individuais (micro-delays e note-shortening antes de pausas)
        notes_humanized = []
        for i, note in enumerate(valid_notes):
            on_time = note["on_time"]
            off_time = note["off_time"]
            duration_orig = off_time - on_time
            
            # Atraso aleatório (desincronismo humano de 5 a 25 ms por trilha)
            delay_sec = random.uniform(0.005, 0.025)
            delay_ticks = seconds_to_ticks(delay_sec, tempo, ticks_per_beat)
            
            on_time_new = on_time + delay_ticks
            
            # Identificar pausas
            is_after_pause = (i == 0) or (on_time - valid_notes[i-1]["off_time"] >= ticks_per_beat * 0.25)
            is_before_pause = (i < len(valid_notes) - 1) and (valid_notes[i+1]["on_time"] - off_time >= ticks_per_beat * 0.25)
            
            # Remover articulação staccato: estende notas muito curtas para legato
            duration_orig = remove_staccato(duration_orig, ticks_per_beat)
            
            # Pós-pausa: encurta a nota anterior para decair reverb
            if is_before_pause:
                duration_new = int(duration_orig * 0.70)  # Corta 30% da duração
            else:
                duration_new = duration_orig
                
            off_time_new = on_time_new + max(15, duration_new)
            
            notes_humanized.append({
                "note": note["note"] + conf["octave"],
                "on_time_new": on_time_new,
                "off_time_new": off_time_new,
                "velocity_orig": note["velocity"],
                "is_after_pause": is_after_pause
            })
            
        # Correção de sobreposição consecutiva
        for i in range(len(notes_humanized) - 1):
            curr = notes_humanized[i]
            nxt = notes_humanized[i+1]
            if curr["off_time_new"] > nxt["on_time_new"]:
                curr["off_time_new"] = max(curr["on_time_new"] + 10, nxt["on_time_new"])

        # Escrever mensagens MIDI
        for note in notes_humanized:
            v_note = note["velocity_orig"]
            if note["is_after_pause"]:
                v_note = 10  # Ataque de nota pós-pausa suave
                
            processed_abs_events.append(mido.Message('note_on', channel=midi_channel, note=note["note"], velocity=v_note, time=note["on_time_new"]))
            processed_abs_events.append(mido.Message('note_off', channel=midi_channel, note=note["note"], velocity=0, time=note["off_time_new"]))
            
            # Adiciona rampas de dinâmica de expressão CC11 pós-pausa
            if note["is_after_pause"]:
                # Rampa CC11 de 40 a 100 em 250ms
                steps = 5
                ramp_duration = int(ticks_per_beat * 0.5)
                for step in range(steps):
                    t_offset = int((step / (steps - 1)) * ramp_duration)
                    cc_val = int(40 + (step / (steps - 1)) * 60)
                    cc_time = note["on_time_new"] + t_offset
                    processed_abs_events.append(mido.Message('control_change', channel=midi_channel, control=11, value=cc_val, time=cc_time))
                    
        # Ordenar e converter absoluto para delta time relativo
        processed_abs_events.sort(key=lambda x: x.time)
        
        curr_time = 0
        for msg in processed_abs_events:
            delta = msg.time - curr_time
            msg.time = delta
            voice_track.append(msg)
            curr_time += delta
            
    new_mid.save(output_midi_path)
    print(f"  ✓ MIDI orquestrado gerado em: {output_midi_path}")

def render_with_musescore(midi_path, output_mp3):
    mscore_binary = "/Applications/MuseScore 4.app/Contents/MacOS/mscore"
    if not os.path.exists(mscore_binary):
        print(f"ERRO: Executável do MuseScore não encontrado em '{mscore_binary}'.")
        return False
        
    cmd = [mscore_binary, "-o", str(output_mp3), str(midi_path)]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"  ✓ Áudio renderizado com sucesso via MuseScore CLI: {output_mp3}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Erro ao renderizar com MuseScore: {e}")
        return False
    finally:
        # Auto-limpeza de arquivos de runtime criados pelo MuseScore
        dir_to_clean = os.path.dirname(os.path.abspath(output_mp3))
        for f in ["automation.json", "audiosettings.json", "viewsettings.json"]:
            f_path = os.path.join(dir_to_clean, f)
            if os.path.exists(f_path):
                try:
                    os.unlink(f_path)
                except OSError:
                    pass
        for d in ["META-INF", "Thumbnails"]:
            d_path = os.path.join(dir_to_clean, d)
            if os.path.exists(d_path) and os.path.isdir(d_path):
                import shutil
                try:
                    shutil.rmtree(d_path)
                except OSError:
                    pass

def main():
    parser = argparse.ArgumentParser(description="Orquestrador Customizado CCB")
    parser.add_argument("--midi", required=True, help="Arquivo MIDI original de entrada")
    parser.add_argument("--model", required=True, choices=["musicbox", "reeds", "woodwinds", "piano", "equinox"], help="Modelo de som desejado")
    parser.add_argument("--speed", type=float, default=1.0, help="Multiplicador de velocidade")
    parser.add_argument("--output", required=True, help="Pasta de saída do áudio e MIDI gerados")
    
    args = parser.parse_args()
    
    # Criar caminhos de saída
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    midi_name = Path(args.midi).stem
    
    # Ajuste de velocidade default para Equinox
    speed_mult = args.speed
    if args.model == "equinox" and speed_mult == 1.0:
        speed_mult = 0.8
        
    print(f"Orquestrando MIDI: {args.midi}")
    print(f"Modelo: {args.model.upper()} | Velocidade: {speed_mult}x")
    
    output_mid_path = out_dir / f"{midi_name}_{args.model}.mid"
    output_mp3_path = out_dir / f"{midi_name}_{args.model}.mp3"
    
    # Processar MIDI
    process_midi_to_custom(args.midi, output_mid_path, args.model, speed=speed_mult)
    
    # Renderizar para MP3
    render_with_musescore(output_mid_path, output_mp3_path)

if __name__ == "__main__":
    main()
