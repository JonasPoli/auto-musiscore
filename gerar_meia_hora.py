#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gerar_meia_hora.py
==================
Gera arquivos MIDI e MP3 de hinos tocados a 50% da velocidade normal com som
de Órgão Eletrônico (Drawbar Organ, program 16 no General MIDI), ideal para
o estilo "meia-hora" da congregação (CCB).
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
import pretty_midi

# Hinos padrão sugeridos (números dos arquivos)
DEFAULT_HYMNS = [208, 260, 375, 397, 401, 475]
DEFAULT_SF = "/Applications/MuseScore 4.app/Contents/Resources/sound/MS Basic.sf3"

def find_midi_by_number(number, directory="mid"):
    # Tenta encontrar no formato "208-..." ou "0208-..." ou "208 -..."
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"Erro: Diretório de entrada '{directory}' não existe.")
        return None
    
    # Procura arquivos .mid que começam com o número
    for item in dir_path.glob("*.mid"):
        if item.name.startswith("._"):
            continue
        name = item.name
        # Extrai os dígitos iniciais
        digits = ""
        for char in name:
            if char.isdigit():
                digits += char
            elif char in ['-', ' ']:
                # se encontrar hífen ou espaço após números, para a extração
                if digits:
                    break
            else:
                # outro caractere, limpa se não formou um padrão claro
                if not digits:
                    continue
                else:
                    break
        if digits and int(digits) == number:
            return item
            
    # Fallback se não encontrou com a lógica acima
    patterns = [f"{number:03d}-*.mid", f"{number}-*.mid", f"*{number}*.mid"]
    for pattern in patterns:
        matches = [f for f in dir_path.glob(pattern) if not f.name.startswith("._")]
        if matches:
            return matches[0]
            
    return None

def process_single_hymn(input_path, output_path, programs=[16], speed_factor=0.5):
    """
    Carrega o MIDI, remapeia as vozes para os programas MIDI selecionados (com combinação/layering)
    e ajusta a velocidade escalando os tempos por 1/speed_factor.
    """
    print(f"Processando: {input_path.name}")
    pm = pretty_midi.PrettyMIDI(str(input_path))
    
    scale = 1.0 / speed_factor
    
    new_pm = pretty_midi.PrettyMIDI()
    
    # Prepara instrumentos no MIDI de saída para cada program selecionado
    insts_output = []
    for prog in programs:
        name = f"Orgao {prog}"
        inst = pretty_midi.Instrument(program=prog, name=name)
        new_pm.instruments.append(inst)
        insts_output.append((prog, inst))
        
    for original_inst in pm.instruments:
        if original_inst.is_drum:
            continue
            
        for prog, inst in insts_output:
            # Relação de ganho para misturar/combinar os órgãos e não estourar o volume:
            # Drawbar Organ (16) é o principal (ganho maior), Rock Organ (18) entra como brilho
            vel_scale = 1.0
            if len(programs) > 1:
                if prog == 16:
                    vel_scale = 0.85
                elif prog == 18:
                    vel_scale = 0.60
                else:
                    vel_scale = 1.0 / len(programs)
                    
            for note in original_inst.notes:
                scaled_note = pretty_midi.Note(
                    velocity=min(127, max(1, int(note.velocity * vel_scale))),
                    pitch=note.pitch,
                    start=note.start * scale,
                    end=note.end * scale
                )
                inst.notes.append(scaled_note)
                
            for cc in original_inst.control_changes:
                scaled_cc = pretty_midi.ControlChange(
                    number=cc.number,
                    value=cc.value,
                    time=cc.time * scale
                )
                inst.control_changes.append(scaled_cc)
                
            for pb in original_inst.pitch_bends:
                scaled_pb = pretty_midi.PitchBend(
                    pitch=pb.pitch,
                    time=pb.time * scale
                )
                inst.pitch_bends.append(scaled_pb)
            
    output_path.parent.mkdir(parents=True, exist_ok=True)
    new_pm.write(str(output_path))
    print(f"  ✓ MIDI lento gerado em: {output_path.name}")

def create_combined_midi(midi_paths, output_path, programs=[16], speed_factor=0.5, gap_seconds=6.0):
    """
    Concatenates multiple MIDI files sequentially with a gap of silence between them.
    All times scaled by 1/speed_factor, layering the specified programs.
    """
    print(f"\nConcatenando {len(midi_paths)} hinos em um único MIDI...")
    scale = 1.0 / speed_factor
    combined_pm = pretty_midi.PrettyMIDI()
    
    insts_output = []
    for prog in programs:
        name = f"Orgao {prog}"
        inst = pretty_midi.Instrument(program=prog, name=name)
        combined_pm.instruments.append(inst)
        insts_output.append((prog, inst))
    
    current_offset = 0.0
    for idx, path in enumerate(midi_paths, 1):
        print(f"  [{idx}/{len(midi_paths)}] Adicionando {path.name} no tempo {current_offset:.2f}s")
        pm = pretty_midi.PrettyMIDI(str(path))
        
        for prog, inst in insts_output:
            vel_scale = 1.0
            if len(programs) > 1:
                if prog == 16:
                    vel_scale = 0.85
                elif prog == 18:
                    vel_scale = 0.60
                else:
                    vel_scale = 1.0 / len(programs)
                    
            for original_inst in pm.instruments:
                if original_inst.is_drum:
                    continue
                for note in original_inst.notes:
                    scaled_note = pretty_midi.Note(
                        velocity=min(127, max(1, int(note.velocity * vel_scale))),
                        pitch=note.pitch,
                        start=note.start * scale + current_offset,
                        end=note.end * scale + current_offset
                    )
                    inst.notes.append(scaled_note)
                    
                for cc in original_inst.control_changes:
                    scaled_cc = pretty_midi.ControlChange(
                        number=cc.number,
                        value=cc.value,
                        time=cc.time * scale + current_offset
                    )
                    inst.control_changes.append(scaled_cc)
                    
                for pb in original_inst.pitch_bends:
                    scaled_pb = pretty_midi.PitchBend(
                        pitch=pb.pitch,
                        time=pb.time * scale + current_offset
                    )
                    inst.pitch_bends.append(scaled_pb)
                
        # Atualiza o tempo para o próximo hino
        hymn_duration = pm.get_end_time() * scale
        current_offset += hymn_duration + gap_seconds
        
    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined_pm.write(str(output_path))
    print(f"  ✓ MIDI completo concatenado gerado em: {output_path}")
    print(f"  Duração estimada: {current_offset / 60.0:.2f} minutos")

def render_midi_to_audio(midi_path, output_mp3, soundfont_path):
    """
    Renders MIDI to WAV using FluidSynth and converts to MP3 using ffmpeg.
    """
    wav_path = Path(output_mp3).with_suffix(".wav")
    
    # 1. FluidSynth
    cmd_fluid = [
        "fluidsynth",
        "-ni",
        "-a", "file",
        "-F", str(wav_path),
        str(soundfont_path),
        str(midi_path)
    ]
    print(f"\n Renderizando WAV com FluidSynth...")
    print(f"    Comando: {' '.join(cmd_fluid)}")
    res = subprocess.run(cmd_fluid, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Erro no FluidSynth: {res.stderr}")
        return False
        
    # 2. FFmpeg
    cmd_ffmpeg = [
        "ffmpeg",
        "-y",
        "-i", str(wav_path),
        "-codec:a", "libmp3lame",
        "-qscale:a", "2",
        str(output_mp3)
    ]
    print(f" Convertendo para MP3 com FFmpeg...")
    print(f"    Comando: {' '.join(cmd_ffmpeg)}")
    res_ff = subprocess.run(cmd_ffmpeg, capture_output=True, text=True)
    
    # Limpa arquivo WAV temporário
    if wav_path.exists():
        wav_path.unlink()
        
    if res_ff.returncode != 0:
        print(f"Erro no FFmpeg: {res_ff.stderr}")
        return False
        
    print(f"  ✓ MP3 gerado com sucesso: {output_mp3}")
    return True

def main():
    parser = argparse.ArgumentParser(description="Gerador de Hinos Meia-Hora para Órgão Eletrônico (50% de velocidade)")
    parser.add_argument("--hinos", type=str, default=",".join(map(str, DEFAULT_HYMNS)),
                        help="Lista de números de hinos separados por vírgula (ex: '208,260,375')")
    parser.add_argument("--speed", type=float, default=0.5,
                        help="Fator de velocidade (padrão 0.5 = 50% da velocidade)")
    parser.add_argument("--program", type=str, default="16",
                        help="Instrumento(s) General MIDI (padrão 16 = Drawbar Organ). Suporta múltiplos separados por vírgula (ex: '16,18') para combinar timbres.")
    parser.add_argument("--gap", type=float, default=6.0,
                        help="Silêncio entre os hinos em segundos (padrão 6.0)")
    parser.add_argument("--output", type=str, default="output_meia_hora",
                        help="Diretório de saída para os arquivos gerados")
    parser.add_argument("--soundfont", type=str, default=DEFAULT_SF,
                        help="Caminho do arquivo SoundFont (.sf2 ou .sf3)")
    args = parser.parse_args()
    
    # Mapeamento especial para presets conhecidos
    if args.soundfont == "10_orgao_eletronico_drawbar":
        caminhos_busca = [
            Path("/Volumes/Dados/work/mid2mp3/soundfonts/Timbres_of_Heaven.sf2"),
            Path(__file__).parent.parent / "mid2mp3" / "soundfonts" / "Timbres_of_Heaven.sf2",
            Path(__file__).parent / "Timbres_of_Heaven.sf2"
        ]
        sf_encontrado = None
        for caminho in caminhos_busca:
            if caminho.exists():
                sf_encontrado = caminho
                break
        
        if sf_encontrado:
            args.soundfont = str(sf_encontrado)
            # Define o program como 16 (Drawbar Organ) se for o padrão do preset
            args.program = "16"
            print(f"-> Preset '10_orgao_eletronico_drawbar' mapeado para SoundFont: {sf_encontrado}")
        else:
            print("ERRO: SoundFont 'Timbres_of_Heaven.sf2' para o preset '10_orgao_eletronico_drawbar' não foi encontrado.")
            sys.exit(1)

    # Validar caminhos
    soundfont_path = Path(args.soundfont)
    if not soundfont_path.exists():
        print(f"ERRO: SoundFont não encontrado em: {soundfont_path}")
        print("Tente passar o caminho correto usando --soundfont")
        sys.exit(1)
        
    # Parsing dos hinos
    try:
        hymn_numbers = [int(x.strip()) for x in args.hinos.split(",") if x.strip()]
    except ValueError:
        print("ERRO: Formato da lista de hinos inválido. Use números separados por vírgula.")
        sys.exit(1)
        
    # Parsing dos instrumentos (programas MIDI)
    try:
        programs = [int(p.strip()) for p in args.program.split(",") if p.strip()]
    except ValueError:
        print("ERRO: Formato de program(s) inválido. Use números ou múltiplos separados por vírgula.")
        sys.exit(1)
        
    # Buscar os arquivos MIDI correspondentes
    midi_paths = []
    print("Buscando arquivos MIDI correspondentes...")
    for num in hymn_numbers:
        path = find_midi_by_number(num, "mid")
        if path:
            print(f"  Encontrado Hino {num:03d}: {path.name}")
            midi_paths.append(path)
        else:
            print(f"  ⚠️ Hino {num} não encontrado na pasta 'mid/'. Pulando.")
            
    if not midi_paths:
        print("ERRO: Nenhum arquivo MIDI correspondente foi encontrado.")
        sys.exit(1)
        
    # Criar pasta de saída
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_midi_dir = out_dir / "midi"
    out_midi_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Processar cada hino individualmente
    processed_midis = []
    for path in midi_paths:
        name = path.stem
        out_midi = out_midi_dir / f"{name}_lento.mid"
        out_mp3 = out_dir / f"{name}_lento.mp3"
        
        process_single_hymn(path, out_midi, programs=programs, speed_factor=args.speed)
        render_midi_to_audio(out_midi, out_mp3, soundfont_path)
        processed_midis.append(out_midi)
        
    # 2. Criar e renderizar o hino concatenado completo (Meia-Hora)
    combined_midi = out_midi_dir / "meia_hora_completa.mid"
    combined_mp3 = out_dir / "meia_hora_completa.mp3"
    
    create_combined_midi(midi_paths, combined_midi, programs=programs, speed_factor=args.speed, gap_seconds=args.gap)
    render_midi_to_audio(combined_midi, combined_mp3, soundfont_path)
    
    print("\n" + "═"*60)
    print("  PROCESSO CONCLUÍDO!")
    print(f"  Arquivos salvos em: {out_dir.absolute()}")
    print("═"*60 + "\n")

if __name__ == "__main__":
    main()
