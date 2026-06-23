"""
orchestrate.py — Pipeline completo de orquestração de piano para orquestra sinfônica.

Fluxo:
  1. Transcreve o MP3 de piano para MIDI (via basic-pitch / Spotify)
  2. Separa as notas por registro (grave → contrabaixo/cello, médio → viola/violino II,
     agudo → violino I / flauta, harmonia → metais suaves)
  3. Sintetiza o MIDI multi-instrumento em áudio via FluidSynth + soundfont
  4. Exporta como MP3

Dependências do sistema:
  - fluidsynth  (brew install fluidsynth)
  - soundfont orquestral (ver SOUNDFONT_PATH abaixo)

Dependências Python (instale com install_midi_pipeline.sh):
  - basic-pitch, pretty_midi, midi2audio
"""

import subprocess
import sys
from pathlib import Path

import pretty_midi
import numpy as np

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO — edite aqui
# ══════════════════════════════════════════════════════════════════════════════
ARQUIVO_ENTRADA  = "piano eqinox/241- A Justiça divina.mp3"
ARQUIVO_SAIDA    = "output/241_orquestra_midi.mp3"

# Soundfont orquestral — baixe um dos sugeridos abaixo e aponte o caminho:
#   GeneralUser GS  : https://schristiancollins.com/generaluser.php  (~30 MB)
#   Sonatina Symph. : https://sso.mattiaswestlund.net/               (~800 MB, mais realista)
#   MuseScore GM    : vem com MuseScore, geralmente em:
#                     /usr/share/sounds/sf2/FluidR3_GM.sf2  (Linux)
#                     ~/Library/Audio/Sounds/Banks/*.sf2    (macOS via MuseScore)
SOUNDFONT_PATH = "/usr/share/sounds/sf2/FluidR3_GM.sf2"  # ajuste conforme sua máquina

# Registros em MIDI note number (60 = C4 / Dó central)
LIMIAR_GRAVE  = 52   # abaixo: contrabaixo + cello
LIMIAR_MEDIO  = 67   # entre: viola + violino II
                     # acima: violino I + flauta

# Instrumentos GM (General MIDI program numbers, 0-indexed)
PROGRAMA = {
    "violino_I":       40,  # Violin
    "violino_II":      40,  # Violin
    "viola":           41,  # Viola
    "cello":           42,  # Cello
    "contrabaixo":     43,  # Contrabass
    "flauta":          73,  # Flute
    "oboé":            68,  # Oboe
    "trompa":          60,  # French Horn
    "piano_original":   0,  # Acoustic Grand Piano
}

# Canal 9 é reservado para percussão no GM — evitaremos ele
# ══════════════════════════════════════════════════════════════════════════════


def transcrever_para_midi(arquivo_audio: str, arquivo_midi: str):
    """Usa basic-pitch (Spotify) para transcrever áudio polifônico em MIDI."""
    print(f"🎵 Transcrevendo: {arquivo_audio}")
    from basic_pitch.inference import predict_and_save
    from basic_pitch import ICASSP_2022_MODEL_PATH

    predict_and_save(
        [arquivo_audio],
        output_directory=str(Path(arquivo_midi).parent),
        save_midi=True,
        sonify_midi=False,
        save_model_outputs=False,
        save_notes=False,
        model_or_model_path=ICASSP_2022_MODEL_PATH,
    )
    # basic-pitch salva com sufixo _basic_pitch.mid
    gerado = list(Path(arquivo_midi).parent.glob("*_basic_pitch.mid"))
    if not gerado:
        raise FileNotFoundError("basic-pitch não gerou arquivo MIDI")
    gerado[0].rename(arquivo_midi)
    print(f"   ✅ MIDI salvo em: {arquivo_midi}")


def orquestrar_midi(arquivo_midi_entrada: str, arquivo_midi_saida: str):
    """
    Lê o MIDI transcrito e distribui as notas entre naipes orquestrais
    com base no registro (altura) de cada nota.
    """
    print("🎻 Orquestrando por registro de notas...")
    piano = pretty_midi.PrettyMIDI(arquivo_midi_entrada)

    orquestra = pretty_midi.PrettyMIDI(initial_tempo=piano.estimate_tempo())

    # Cria instrumentos
    instrumentos = {
        nome: pretty_midi.Instrument(
            program=prog,
            name=nome,
            is_drum=False
        )
        for nome, prog in PROGRAMA.items()
    }

    # Contadores para acompanhamento
    contagem = {k: 0 for k in instrumentos}

    for track in piano.instruments:
        for nota in track.notes:
            pitch = nota.pitch

            # Piano original — sempre incluso (volume reduzido)
            nota_piano = pretty_midi.Note(
                velocity=max(1, nota.velocity // 3),
                pitch=pitch,
                start=nota.start,
                end=nota.end,
            )
            instrumentos["piano_original"].notes.append(nota_piano)
            contagem["piano_original"] += 1

            if pitch < LIMIAR_GRAVE:
                # Registro grave → contrabaixo (staccato) + cello (sustentado)
                for nome_inst in ["contrabaixo", "cello"]:
                    vel = nota.velocity if nome_inst == "cello" else nota.velocity // 2
                    instrumentos[nome_inst].notes.append(
                        pretty_midi.Note(vel, pitch, nota.start, nota.end))
                    contagem[nome_inst] += 1

            elif pitch < LIMIAR_MEDIO:
                # Registro médio → viola + violino II
                for nome_inst in ["viola", "violino_II"]:
                    vel = nota.velocity
                    # Viola uma oitava acima para soar mais pleno
                    p = min(pitch + 12, 127) if nome_inst == "violino_II" else pitch
                    instrumentos[nome_inst].notes.append(
                        pretty_midi.Note(vel, p, nota.start, nota.end))
                    contagem[nome_inst] += 1

            else:
                # Registro agudo → violino I + flauta (8va)
                instrumentos["violino_I"].notes.append(
                    pretty_midi.Note(nota.velocity, pitch, nota.start, nota.end))
                contagem["violino_I"] += 1

                # Flauta dobra as notas mais agudas (acima de C5 = 72)
                if pitch > 72:
                    instrumentos["flauta"].notes.append(
                        pretty_midi.Note(nota.velocity // 2, pitch, nota.start, nota.end))
                    contagem["flauta"] += 1

            # Trompa — dobra a harmonia no médio-grave com volume suave
            if LIMIAR_GRAVE <= pitch < LIMIAR_MEDIO + 5:
                instrumentos["trompa"].notes.append(
                    pretty_midi.Note(nota.velocity // 3, pitch, nota.start, nota.end))
                contagem["trompa"] += 1

    # Adiciona os instrumentos ao MIDI final
    canal = 0
    for nome, inst in instrumentos.items():
        if inst.notes:
            inst.name = nome
            orquestra.instruments.append(inst)
            print(f"   {nome:20s}: {contagem[nome]:4d} notas  (canal {canal})")
            canal += 1

    orquestra.write(arquivo_midi_saida)
    print(f"\n   ✅ MIDI orquestrado: {arquivo_midi_saida}")


def sintetizar(arquivo_midi: str, arquivo_saida: str, soundfont: str):
    """Converte MIDI em áudio via FluidSynth e depois em MP3 via ffmpeg."""
    print(f"\n🔊 Sintetizando com FluidSynth...")
    print(f"   Soundfont: {soundfont}")

    if not Path(soundfont).exists():
        print(f"\n❌ Soundfont não encontrado em: {soundfont}")
        print("   Baixe um soundfont e ajuste SOUNDFONT_PATH no início do script.")
        print("   Sugestão rápida:")
        print("     curl -L https://github.com/musescore/MuseScore/raw/master/"
              "share/sound/FluidR3Mono_GM.sf3 -o ~/FluidR3_GM.sf3")
        sys.exit(1)

    wav_temp = Path(arquivo_saida).with_suffix(".wav")

    # Sinteza MIDI → WAV via FluidSynth
    result = subprocess.run([
        "fluidsynth",
        "-ni",                  # não interativo
        "-g", "1.0",            # ganho
        "-r", "44100",          # sample rate
        soundfont,
        arquivo_midi,
        "-F", str(wav_temp),    # output WAV
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ FluidSynth falhou:\n{result.stderr}")
        sys.exit(1)

    print(f"   ✅ WAV gerado: {wav_temp}")

    # WAV → MP3 via ffmpeg
    result = subprocess.run([
        "ffmpeg", "-y",
        "-i", str(wav_temp),
        "-codec:a", "libmp3lame",
        "-qscale:a", "2",
        arquivo_saida,
    ], capture_output=True, text=True)

    if result.returncode == 0:
        wav_temp.unlink()
        tamanho = Path(arquivo_saida).stat().st_size / 1024
        print(f"🎵 MP3 final: {arquivo_saida}  ({tamanho:.0f} KB)")
    else:
        print(f"⚠️  ffmpeg falhou. WAV disponível: {wav_temp}\n{result.stderr}")


def main():
    Path("output").mkdir(exist_ok=True)
    Path("midi").mkdir(exist_ok=True)

    nome_base     = Path(ARQUIVO_ENTRADA).stem
    midi_original = f"midi/{nome_base}_original.mid"
    midi_orquestrado = f"midi/{nome_base}_orquestra.mid"

    print(f"\n{'═'*60}")
    print(f"  Pipeline de Orquestração MIDI")
    print(f"  Entrada : {ARQUIVO_ENTRADA}")
    print(f"  Saída   : {ARQUIVO_SAIDA}")
    print(f"{'═'*60}\n")

    # Etapa 1: áudio → MIDI
    if not Path(midi_original).exists():
        transcrever_para_midi(ARQUIVO_ENTRADA, midi_original)
    else:
        print(f"⏭  MIDI original já existe, pulando transcrição: {midi_original}")

    # Etapa 2: MIDI → MIDI orquestrado
    orquestrar_midi(midi_original, midi_orquestrado)

    # Etapa 3: MIDI orquestrado → MP3
    sintetizar(midi_orquestrado, ARQUIVO_SAIDA, SOUNDFONT_PATH)

    print(f"\n{'═'*60}")
    print(f"  ✅ Orquestração concluída!")
    print(f"  Arquivo: {ARQUIVO_SAIDA}")
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    main()
