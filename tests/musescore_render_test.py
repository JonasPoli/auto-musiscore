#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
musescore_render_test.py
========================
Script para testar e comparar os presets de metais (Brass) no MuseScore 4.
Permite renderizar um arquivo MIDI selecionado com múltiplos presets para avaliação do usuário.

Uso:
  python musescore_render_test.py --presets 1,2,3
  python musescore_render_test.py --presets all --midi mid/algum_arquivo.mid
"""

import os
import sys
# Resolve o diretório raiz do projeto para permitir importações corretas
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import argparse
import glob
from pathlib import Path

# Importa as funções e presets diretamente do script principal
try:
    from musescore_orchestrate import (
        process_midi_to_8part, 
        render_score, 
        BRASS_PRESETS
    )
except ImportError:
    print("ERRO: Certifique-se de que 'musescore_orchestrate.py' está no mesmo diretório.")
    sys.exit(1)

# Tenta importar a lógica matemática de humanização se disponível
try:
    from musescore_orchestrate_math import process_midi_to_8part_math
except ImportError:
    process_midi_to_8part_math = None

def main():
    parser = argparse.ArgumentParser(description="Testador de Presets - MuseScore 4 Brass Orchestrator")
    parser.add_argument("--midi", default=None, 
                        help="Caminho do MIDI para teste. Se não especificado, pegará o primeiro de 'mid/'")
    parser.add_argument("--presets", default="1,2,3", 
                        help="IDs dos presets para testar, separados por vírgula (ex: '1,2,3') ou 'all' para todos os 20")
    parser.add_argument("--output", default="output_presets_test", 
                        help="Pasta de saída para os arquivos de áudio de teste")
    parser.add_argument("--soundfonts", default="/Users/jonaspoli/Documents/MuseScore4/SoundFonts/Muse Hub Instruments", 
                        help="Caminho para os instrumentos das Muse Sounds")
    parser.add_argument("--no-expression", action="store_true", 
                        help="Desativa a expressão dinâmica inteligente")
    parser.add_argument("--math", action="store_true",
                        help="Usa as fórmulas matemáticas de humanização (Timing em ticks, velocity linear + acento, e curva de volume CC11)")
    parser.add_argument("--speed", type=float, default=1.0,
                        help="Fator de velocidade/tempo (ex: 0.85 para deixar 15% mais lento)")
    
    args = parser.parse_args()
    
    # 1. Definir MIDI a ser usado
    midi_file = args.midi
    if not midi_file:
        midis = sorted(glob.glob("mid/*.mid"))
        if not midis:
            print("ERRO: Nenhum arquivo MIDI encontrado na pasta 'mid/'. Crie ou forneça o caminho com --midi.")
            sys.exit(1)
        midi_file = midis[0]
        
    if not os.path.exists(midi_file):
        print(f"ERRO: Arquivo MIDI não encontrado: {midi_file}")
        sys.exit(1)
        
    midi_name = Path(midi_file).stem
    print(f"🎵 MIDI selecionado para teste: {midi_file}")
    
    # 2. Definir os presets a serem executados
    if args.presets.lower() == "all":
        presets_to_test = sorted(list(BRASS_PRESETS.keys()))
    else:
        try:
            presets_to_test = [int(p.strip()) for p in args.presets.split(",") if p.strip()]
        except ValueError:
            print("ERRO: Formato de presets inválido. Use números separados por vírgula ou 'all'.")
            sys.exit(1)
            
    # Validação dos presets selecionados
    for p_id in presets_to_test:
        if p_id not in BRASS_PRESETS:
            print(f"ERRO: Preset {p_id} inválido. Escolha IDs entre 1 e 20.")
            sys.exit(1)
            
    # 3. Preparar diretório de saída
    os.makedirs(args.output, exist_ok=True)
    
    print("\n" + "═"*60)
    print("  INICIANDO RENDERIZAÇÃO DE TESTE DE PRESETS")
    print(f"  Total de presets a testar: {len(presets_to_test)}")
    print(f"  Expressão dinâmica: {'DESATIVADA' if args.no_expression else 'ATIVA'}")
    print(f"  Velocidade: {args.speed}x")
    print(f"  Engine: {'Matemático (Ticks/CC11)' if args.math else 'Original (Acoustic Model)'}")
    print("" + "═"*60 + "\n")
    
    for idx, p_id in enumerate(presets_to_test, 1):
        preset = BRASS_PRESETS[p_id]
        preset_clean_name = preset["name"].lower().replace(" ", "_").replace("&", "e").replace("(", "").replace(")", "")
        
        # Nome da saída MP3: [MidiName]_preset_[ID]_[Name].mp3
        suffix = "_math" if args.math else ""
        out_mp3 = os.path.join(args.output, f"{midi_name}_preset_{p_id}_{preset_clean_name}{suffix}.mp3")
        temp_midi = os.path.join(args.output, f"temp_test_preset_{p_id}{suffix}.mid")
        
        print(f"[{idx}/{len(presets_to_test)}] Processando Preset {p_id}: {preset['name']}")
        print(f"    ↳ Descrição: {preset['desc']}")
        print(f"    ↳ Engine: {'Matemático (Ticks/CC11)' if args.math else 'Original (Acoustic Model)'}")
        
        try:
            # Gera o MIDI temporário humanizado e espacializado com o preset atual
            use_expr = not args.no_expression
            if args.math:
                if process_midi_to_8part_math is None:
                    print("ERRO: 'musescore_orchestrate_math.py' não foi encontrado ou falhou ao importar.")
                    sys.exit(1)
                process_midi_to_8part_math(midi_file, temp_midi, preset["map"], use_expression=use_expr, speed=args.speed)
            else:
                process_midi_to_8part(midi_file, temp_midi, preset["map"], use_expression=use_expr, speed=args.speed)
            
            # Chama o render do MuseScore 4
            print("    ↳ Renderizando áudio com Muse Sounds...", end="", flush=True)
            render_score(temp_midi, out_mp3, args.soundfonts)
            
            if os.path.exists(temp_midi):
                os.remove(temp_midi)
                
            if os.path.exists(out_mp3):
                kb = os.path.getsize(out_mp3) // 1024
                print(f" ✓ Concluído ({kb} KB)")
                print(f"    ↳ Áudio gerado: [link]({out_mp3})")
            else:
                print(" ✗ FALHOU (arquivo final não gerado)")
                
        except Exception as e:
            if os.path.exists(temp_midi):
                os.remove(temp_midi)
            print(f" ✗ FALHOU (erro: {e})")
            
    print("\n" + "═"*60)
    print("  TESTE DE PRESETS CONCLUÍDO!")
    print(f"  Todos os áudios foram salvos na pasta: {args.output}/")
    print("═"*60 + "\n")

if __name__ == "__main__":
    main()
