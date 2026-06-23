import os
import subprocess
import mido
import sys

# Resolve o diretório raiz do projeto para permitir importações corretas
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

output_dir = "tests/diagnostic_output"
os.makedirs(output_dir, exist_ok=True)

mid = mido.MidiFile()
ticks_per_beat = mid.ticks_per_beat # 480 ticks por tempo por padrão

# Cria trilha de metadados
meta_track = mido.MidiTrack()
mid.tracks.append(meta_track)
meta_track.append(mido.MetaMessage('set_tempo', tempo=500000, time=0)) # 120 BPM

print("Criando MIDI com 16 canais tocando Violins 1 sequencialmente...")

# Cada canal i vai tocar por 1.5s (3 tempos = 1440 ticks)
for ch in range(16):
    track = mido.MidiTrack()
    mid.tracks.append(track)
    
    # Nome da pista e programa (todas com Violins 1, program 40)
    track.append(mido.MetaMessage('track_name', name="Violins 1", time=0))
    track.append(mido.Message('program_change', channel=ch, program=40, time=0))
    track.append(mido.Message('control_change', channel=ch, control=7, value=100, time=0))
    track.append(mido.Message('control_change', channel=ch, control=10, value=64, time=0)) # Pan central
    track.append(mido.Message('control_change', channel=ch, control=11, value=100, time=0))
    
    # Tempo de início absoluto: ch * 1440 ticks
    start_time = ch * 1440
    
    # note_on usa start_time como delta da última mensagem (que estava em t=0)
    track.append(mido.Message('note_on', channel=ch, note=60, velocity=90, time=start_time))
    # note_off ocorre 1440 ticks após o note_on (duração de 1.5s)
    track.append(mido.Message('note_off', channel=ch, note=60, velocity=0, time=1440))

midi_path = os.path.join(output_dir, "diagnostic_channels.mid")
mp3_path = os.path.join(output_dir, "diagnostic_channels.mp3")

mid.save(midi_path)
print("Renderizando com MuseScore 4...")

soundfonts_dir = "/Users/jonaspoli/Documents/MuseScore4/SoundFonts/Muse Hub Instruments"
my_env = os.environ.copy()
my_env["MUSESAMPLER_INSTRUMENT_FOLDER"] = soundfonts_dir

subprocess.run([
    "/Applications/MuseScore 4.app/Contents/MacOS/mscore",
    "-o", mp3_path,
    midi_path
], env=my_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if os.path.exists(midi_path):
    os.remove(midi_path)

print(f"Sucesso! Áudio salvo em: {mp3_path}")
