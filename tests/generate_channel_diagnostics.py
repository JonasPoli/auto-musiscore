import os
import subprocess
import mido
import sys

# Resolve o diretório raiz do projeto para permitir importações corretas
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'orchestrators')))

# Importar o mapeamento do Preset 5
try:
    from musescore_strings_16part import STRINGS_16PART_PRESETS
except ImportError as e:
    print(f"ERRO: Não foi possível importar o preset. (Erro: {e})")
    sys.exit(1)

preset_map = STRINGS_16PART_PRESETS[5]["map"]
output_dir = "tests/channel_diagnostics"
os.makedirs(output_dir, exist_ok=True)

soundfonts_dir = "/Users/jonaspoli/Documents/MuseScore4/SoundFonts/Muse Hub Instruments"

# Configuração de notas adequadas para os registros das vozes
note_presets = {
    "Soprano":   [55, 60, 64, 67, 72, 76, 79],
    "Contralto": [48, 52, 55, 60, 64, 67, 72],
    "Tenor":     [36, 40, 43, 48, 52, 55, 60],
    "Baixo":     [24, 28, 31, 36, 40, 43, 48]
}

# Mapeamento do nome da voz pelo índice do canal (0-3 Soprano, 4-7 Contralto, 8-11 Tenor, 12-15 Baixo)
def get_voice_name(channel_index):
    if channel_index < 4:
        return "Soprano", f"Soprano_{channel_index + 1}"
    elif channel_index < 8:
        return "Contralto", f"Contralto_{channel_index - 3}"
    elif channel_index < 12:
        return "Tenor", f"Tenor_{channel_index - 7}"
    else:
        return "Baixo", f"Baixo_{channel_index - 11}"

print("Gerando arquivos de teste individuais para cada canal (0 a 15)...")

for ch in range(16):
    voice_cat, sub_key = get_voice_name(ch)
    inst_info = preset_map[sub_key]
    name = inst_info["name"]
    program = inst_info["program"]
    notes = note_presets[voice_cat]
    
    # Criar arquivo MIDI contendo apenas este canal
    mid = mido.MidiFile()
    track = mido.MidiTrack()
    mid.tracks.append(track)
    
    # Adicionar metadados e controle básico
    track.append(mido.MetaMessage('set_tempo', tempo=500000, time=0)) # 120 BPM
    track.append(mido.MetaMessage('track_name', name=name, time=0))
    track.append(mido.Message('program_change', channel=ch, program=program, time=0))
    track.append(mido.Message('control_change', channel=ch, control=7, value=100, time=0))
    track.append(mido.Message('control_change', channel=ch, control=10, value=64, time=0)) # Pan central
    track.append(mido.Message('control_change', channel=ch, control=11, value=100, time=0))
    
    # Tocar 4 notas de meio compasso (2 tempos cada = 960 ticks)
    for note in notes[:4]:
        track.append(mido.Message('note_on', channel=ch, note=note, velocity=90, time=0))
        track.append(mido.Message('note_off', channel=ch, note=note, velocity=0, time=960))
        
    # Tocar 3 notas de compasso inteiro (4 tempos cada = 1920 ticks)
    for note in notes[4:7]:
        track.append(mido.Message('note_on', channel=ch, note=note, velocity=90, time=0))
        track.append(mido.Message('note_off', channel=ch, note=note, velocity=0, time=1920))
        
    safe_inst_name = name.lower().replace(" ", "_").replace("(", "").replace(")", "")
    file_prefix = f"{ch:02d}_{sub_key.lower()}_{safe_inst_name}"
    
    midi_path = os.path.join(output_dir, f"{file_prefix}.mid")
    mp3_path = os.path.join(output_dir, f"{file_prefix}.mp3")
    
    mid.save(midi_path)
    print(f"[{ch+1}/16] Renderizando canal {ch} ({sub_key} - {name})...")
    
    # Renderizar com MuseScore 4
    my_env = os.environ.copy()
    my_env["MUSESAMPLER_INSTRUMENT_FOLDER"] = soundfonts_dir
    
    subprocess.run([
        "/Applications/MuseScore 4.app/Contents/MacOS/mscore",
        "-o", mp3_path,
        midi_path
    ], env=my_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if os.path.exists(midi_path):
        os.remove(midi_path)

print("\nConcluído! Todos os 16 áudios foram salvos em 'tests/channel_diagnostics/'.")
