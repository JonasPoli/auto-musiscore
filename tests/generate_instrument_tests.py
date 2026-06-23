import os
import subprocess
import mido

instruments = [
    {"name": "Violins 1", "program": 40, "notes": [55, 60, 64, 67, 72, 76, 79]},
    {"name": "Violins 2", "program": 40, "notes": [55, 60, 64, 67, 72, 76, 79]},
    {"name": "Violin 1 (Solo)", "program": 40, "notes": [55, 60, 64, 67, 72, 76, 79]},
    {"name": "Violin 2 (Solo)", "program": 40, "notes": [55, 60, 64, 67, 72, 76, 79]},
    {"name": "Violas", "program": 41, "notes": [48, 52, 55, 60, 64, 67, 72]},
    {"name": "Viola (Solo)", "program": 41, "notes": [48, 52, 55, 60, 64, 67, 72]},
    {"name": "Violoncellos", "program": 42, "notes": [36, 40, 43, 48, 52, 55, 60]},
    {"name": "Violoncello (Solo)", "program": 42, "notes": [36, 40, 43, 48, 52, 55, 60]},
    {"name": "Contrabasses", "program": 43, "notes": [24, 28, 31, 36, 40, 43, 48]}
]

soundfonts_dir = "/Users/jonaspoli/Documents/MuseScore4/SoundFonts/Muse Hub Instruments"
output_dir = "output_instrument_tests"
os.makedirs(output_dir, exist_ok=True)

print("Iniciando geração dos arquivos de teste de 10 segundos...")

for idx, inst in enumerate(instruments, 1):
    name = inst["name"]
    program = inst["program"]
    notes = inst["notes"]
    
    # Criar arquivo MIDI
    mid = mido.MidiFile()
    track = mido.MidiTrack()
    mid.tracks.append(track)
    
    # Adicionar metadados e controle básico
    track.append(mido.MetaMessage('set_tempo', tempo=500000, time=0)) # 120 BPM
    track.append(mido.MetaMessage('track_name', name=name, time=0))
    track.append(mido.Message('program_change', channel=0, program=program, time=0))
    track.append(mido.Message('control_change', channel=0, control=7, value=100, time=0))
    track.append(mido.Message('control_change', channel=0, control=10, value=64, time=0)) # Pan centralizado
    track.append(mido.Message('control_change', channel=0, control=11, value=100, time=0))
    
    # Tocar 4 notas de meio compasso (2 tempos cada = 960 ticks)
    for note in notes[:4]:
        track.append(mido.Message('note_on', channel=0, note=note, velocity=90, time=0))
        track.append(mido.Message('note_off', channel=0, note=note, velocity=0, time=960))
        
    # Tocar 3 notas de compasso inteiro (4 tempos cada = 1920 ticks)
    for note in notes[4:7]:
        track.append(mido.Message('note_on', channel=0, note=note, velocity=90, time=0))
        track.append(mido.Message('note_off', channel=0, note=note, velocity=0, time=1920))
        
    safe_name = name.lower().replace(" ", "_").replace("(", "").replace(")", "")
    midi_path = os.path.join(output_dir, f"{safe_name}.mid")
    mp3_path = os.path.join(output_dir, f"{safe_name}.mp3")
    
    mid.save(midi_path)
    print(f"[{idx}/{len(instruments)}] Renderizando áudio para: {name}...")
    
    # Chamar o MuseScore 4 em subprocesso com a variável de ambiente correta
    my_env = os.environ.copy()
    my_env["MUSESAMPLER_INSTRUMENT_FOLDER"] = soundfonts_dir
    
    subprocess.run([
        "/Applications/MuseScore 4.app/Contents/MacOS/mscore",
        "-o", mp3_path,
        midi_path
    ], env=my_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Remover o MIDI temporário
    if os.path.exists(midi_path):
        os.remove(midi_path)

print("\nConcluído! Todos os áudios foram salvos na pasta 'output_instrument_tests/'.")
