#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
musescore_strings_render_test.py
================================
Script para testar e comparar os 20 presets de cordas (Strings) no MuseScore 4.
Permite renderizar um arquivo MIDI selecionado com múltiplos presets de cordas para avaliação.

Uso:
  python musescore_strings_render_test.py --presets 1,2,3
  python musescore_strings_render_test.py --presets all --midi mid/002-\ De\ Deus\ tu\ és\ eleita.mid
"""

import os
# Resolve o diretório raiz do projeto para permitir importações corretas
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'orchestrators')))
import argparse
import glob
from pathlib import Path

# Importa as funções e presets diretamente do script de cordas
try:
    from musescore_strings_math import (
        process_midi_to_8part_math, 
        render_score, 
        STRINGS_PRESETS
    )
except ImportError as e:
    print(f"ERRO: Certifique-se de que 'musescore_strings_math.py' está na pasta 'orchestrators'. (Erro: {e})")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Testador de Presets de Cordas - MuseScore 4 Strings Orchestrator")
    parser.add_argument("--midi", default=None, 
                        help="Caminho do MIDI para teste. Se não especificado, pegará o primeiro de 'mid/'")
    parser.add_argument("--presets", default="all", 
                        help="IDs dos presets para testar, separados por vírgula (ex: '1,2,3') ou 'all' para todos os 20")
    parser.add_argument("--output", default="output/strings_test", 
                        help="Pasta de saída para os arquivos de áudio de teste")
    parser.add_argument("--soundfonts", default="/Users/jonaspoli/Documents/MuseScore4/SoundFonts/Muse Hub Instruments", 
                        help="Caminho para os instrumentos das Muse Sounds")
    parser.add_argument("--no-expression", action="store_true", 
                        help="Desativa a expressão dinâmica inteligente")
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
        presets_to_test = sorted(list(STRINGS_PRESETS.keys()))
    else:
        try:
            presets_to_test = [int(p.strip()) for p in args.presets.split(",") if p.strip()]
        except ValueError:
            print("ERRO: Formato de presets inválido. Use números separados por vírgula ou 'all'.")
            sys.exit(1)
            
    # Validação dos presets selecionados
    for p_id in presets_to_test:
        if p_id not in STRINGS_PRESETS:
            print(f"ERRO: Preset {p_id} inválido. Escolha IDs entre 1 e 20.")
            sys.exit(1)
            
    # 3. Preparar diretório de saída
    os.makedirs(args.output, exist_ok=True)
    
    print("\n" + "═"*60)
    print("  INICIANDO RENDERIZAÇÃO DE TESTE DE PRESETS DE CORDAS")
    print(f"  Total de presets a testar: {len(presets_to_test)}")
    print(f"  Expressão dinâmica: {'DESATIVADA' if args.no_expression else 'ATIVA'}")
    print(f"  Velocidade: {args.speed}x")
    print("" + "═"*60 + "\n")
    
    for idx, p_id in enumerate(presets_to_test, 1):
        preset = STRINGS_PRESETS[p_id]
        preset_clean_name = preset["name"].lower().replace(" ", "_").replace("&", "e").replace("(", "").replace(")", "")
        
        # Nome da saída MP3: [MidiName]_preset_[ID]_[Name].mp3
        out_mp3 = os.path.join(args.output, f"{midi_name}_preset_{p_id}_{preset_clean_name}.mp3")
        temp_midi = os.path.join(args.output, f"temp_test_preset_strings_{p_id}.mid")
        
        print(f"[{idx}/{len(presets_to_test)}] Processando Preset {p_id}: {preset['name']}")
        print(f"    ↳ Descrição: {preset['desc']}")
        
        try:
            use_expr = not args.no_expression
            process_midi_to_8part_math(midi_file, temp_midi, preset["map"], use_expression=use_expr, speed=args.speed)
            
            # Chama o render do MuseScore 4
            print("    ↳ Renderizando áudio com Muse Sounds...", end="", flush=True)
            render_score(temp_midi, out_mp3, args.soundfonts)
            
            if os.path.exists(temp_midi):
                os.remove(temp_midi)
                
            if os.path.exists(out_mp3):
                kb = os.path.getsize(out_mp3) // 1024
                print(f" ✓ Concluído ({kb} KB)")
                print(f"    ↳ Áudio gerado: {out_mp3}")
            else:
                print(" ✗ FALHOU (arquivo final não gerado)")
                
        except Exception as e:
            if os.path.exists(temp_midi):
                os.remove(temp_midi)
            print(f" ✗ FALHOU (erro: {e})")
            
    print("\n" + "═"*60)
    print("  TESTE DE PRESETS DE CORDAS CONCLUÍDO!")
    print(f"  Todos os áudios foram salvos na pasta: {args.output}/")
    print("═"*60 + "\n")

if __name__ == "__main__":
    main()
