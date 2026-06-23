import os
import subprocess
import mido
import wave
import struct
import math
import sys

# Sincroniza path para resolver caminhos se executado de subpastas
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

instruments = [
    {"name": "Violins 1", "program": 40, "note": 64},
    {"name": "Violins 2", "program": 40, "note": 64},
    {"name": "Violin 1 (Solo)", "program": 40, "note": 64},
    {"name": "Violin 2 (Solo)", "program": 40, "note": 64},
    {"name": "Violas", "program": 41, "note": 57},
    {"name": "Viola (Solo)", "program": 41, "note": 57},
    {"name": "Violoncellos", "program": 42, "note": 45},
    {"name": "Violoncello (Solo)", "program": 42, "note": 45},
    {"name": "Contrabasses", "program": 43, "note": 33},
    {"name": "Pizzicato Strings", "program": 45, "note": 57},
    {"name": "Tremolo Strings", "program": 44, "note": 57},
    {"name": "Harp", "program": 46, "note": 64}
]

soundfonts_dir = "/Users/jonaspoli/Documents/MuseScore4/SoundFonts/Muse Hub Instruments"
output_dir = "tests/diagnostic_output"
os.makedirs(output_dir, exist_ok=True)

print("======================================================================")
print("Iniciando renderização de notas isoladas para análise de volume RMS...")
print("======================================================================\n")

results = {}

for idx, inst in enumerate(instruments, 1):
    name = inst["name"]
    program = inst["program"]
    note = inst["note"]
    
    # Criar arquivo MIDI de 4 segundos
    mid = mido.MidiFile()
    track = mido.MidiTrack()
    mid.tracks.append(track)
    
    # Tempo = 500000 (120 BPM, 1 batida = 500ms, 4 segundos = 8 batidas = 3840 ticks)
    track.append(mido.MetaMessage('set_tempo', tempo=500000, time=0))
    track.append(mido.MetaMessage('track_name', name=name, time=0))
    track.append(mido.Message('program_change', channel=0, program=program, time=0))
    track.append(mido.Message('control_change', channel=0, control=7, value=100, time=0))
    track.append(mido.Message('control_change', channel=0, control=10, value=64, time=0)) # Pan centralizado
    track.append(mido.Message('control_change', channel=0, control=11, value=100, time=0)) # Expression
    
    # Nota ON
    track.append(mido.Message('note_on', channel=0, note=note, velocity=90, time=0))
    # Nota OFF após 4 segundos (8 batidas * ticks_per_beat)
    # ticks_per_beat padrão do mido é 480, então 8 * 480 = 3840 ticks
    track.append(mido.Message('note_off', channel=0, note=note, velocity=0, time=3840))
    
    safe_name = name.lower().replace(" ", "_").replace("(", "").replace(")", "")
    midi_path = os.path.join(output_dir, f"temp_{safe_name}.mid")
    mp3_path = os.path.join(output_dir, f"temp_{safe_name}.mp3")
    wav_path = os.path.join(output_dir, f"temp_{safe_name}.wav")
    
    mid.save(midi_path)
    
    # Renderizar para MP3 primeiro (pois WAV falha via CLI no MuseScore 4 deste Mac)
    my_env = os.environ.copy()
    my_env["MUSESAMPLER_INSTRUMENT_FOLDER"] = soundfonts_dir
    
    result = subprocess.run([
        "/Applications/MuseScore 4.app/Contents/MacOS/mscore",
        "-o", mp3_path,
        midi_path
    ], env=my_env, capture_output=True, text=True)
    
    # Converter MP3 para WAV usando ffmpeg
    if os.path.exists(mp3_path):
        subprocess.run([
            "ffmpeg", "-y",
            "-i", mp3_path,
            wav_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.remove(mp3_path)
    else:
        if result.returncode != 0:
            print(f"MuseScore error for {name}: {result.stderr}")
            
    # Limpar MIDI temporário
    if os.path.exists(midi_path):
        os.remove(midi_path)
        
    # Calcular RMS
    if os.path.exists(wav_path):
        try:
            with wave.open(wav_path, 'rb') as w:
                num_channels = w.getnchannels()
                sample_width = w.getsampwidth()
                num_frames = w.getnframes()
                data = w.readframes(num_frames)
                
            if sample_width == 2:
                fmt = f"{num_frames * num_channels}h"
                samples = struct.unpack(fmt, data)
                # Evitar divisões por zero se o arquivo estiver vazio
                if len(samples) > 0:
                    sum_squares = sum(s ** 2 for s in samples)
                    rms = math.sqrt(sum_squares / len(samples))
                    results[name] = rms
                    print(f"[{idx}/{len(instruments)}] {name:<20}: RMS = {rms:.2f}")
                else:
                    print(f"[{idx}/{len(instruments)}] {name:<20}: WAV vazio.")
            else:
                print(f"[{idx}/{len(instruments)}] {name:<20}: Formato de largura de amostra {sample_width} não suportado.")
        except Exception as e:
            print(f"[{idx}/{len(instruments)}] {name:<20}: Erro ao ler WAV ({e})")
        finally:
            if os.path.exists(wav_path):
                os.remove(wav_path)
    else:
        print(f"[{idx}/{len(instruments)}] {name:<20}: Falha ao gerar WAV (verifique se MuseScore está instalado corretamente).")

print("\n======================================================================")
print("              RESULTADOS DA CALIBRAÇÃO DE VOLUME (RMS)                ")
print("======================================================================")
if "Violins 1" in results and results["Violins 1"] > 0:
    ref_rms = results["Violins 1"]
    print(f"Usando 'Violins 1' como referência (RMS = {ref_rms:.2f})\n")
    print(f"{'Instrumento':<25} | {'RMS Medido':<12} | {'Fator Sugerido':<15}")
    print("-" * 60)
    for name, rms in results.items():
        # Fator é inverso do RMS normalizado pelo referencial
        modifier = ref_rms / rms if rms > 0 else 1.0
        print(f"{name:<25} | {rms:<12.2f} | {modifier:<15.4f}")
else:
    print("Violins 1 não pôde ser medido para servir de referência.")
print("======================================================================\n")
