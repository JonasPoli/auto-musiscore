#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
comparar_orgaos.py
==================
Gera o Hino 208 utilizando 7 variações de órgãos e pads analógicos/digitais
para comparação do usuário, incluindo renderização via FluidSynth e MuseScore 4.
"""

import os
import subprocess
from pathlib import Path

# Presets para renderizar via FluidSynth (programas GM, 0-indexed)
FLUID_PRESETS = {
    16: "drawbar_organ",      # Hammond tradicional
    18: "rock_organ",         # Hammond com mais drive/brilho
    19: "church_organ",       # Órgão de igreja tradicional (tubos, mas suave)
    89: "warm_synth_pad",     # Synth pad quente e aveludado (estilo fundo de teclado)
    90: "polysynth_organ",    # Órgão sintetizado clássico
    94: "halo_synth_pad"      # Synth pad espacial e etéreo
}

def main():
    hino_id = 208
    out_dir = Path("output_meia_hora/comparacao")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print("════════════════════════════════════════════════════════════")
    print("  INICIANDO COMPARAÇÃO DE TIMBRES DE ÓRGÃOS E PADS")
    print("════════════════════════════════════════════════════════════")
    
    # 1. Gerar os presets do FluidSynth
    for prog, name in FLUID_PRESETS.items():
        print(f"\n▶ Gerando versão FluidSynth: {name} (Program {prog})...")
        temp_out = out_dir / f"temp_{name}"
        
        subprocess.run([
            ".venv/bin/python", "gerar_meia_hora.py",
            "--hinos", str(hino_id),
            "--program", str(prog),
            "--output", str(temp_out)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        mp3s = list(temp_out.glob("*.mp3"))
        if mp3s:
            dest_file = out_dir / f"hino_{hino_id}_{name}.mp3"
            if dest_file.exists():
                dest_file.unlink()
            mp3s[0].rename(dest_file)
            print(f"  ✓ Salvo em: {dest_file}")
        else:
            print(f"  ✗ Falha ao gerar {name}")
            
        # Limpar temporários
        if temp_out.exists():
            for f in (temp_out / "midi").glob("*"):
                f.unlink()
            (temp_out / "midi").rmdir()
            for f in temp_out.glob("*"):
                f.unlink()
            temp_out.rmdir()

    # 2. Gerar a versão usando o Hammond Organ nativo do MuseScore 4 (Muse Sounds)
    print("\n▶ Gerando versão MuseScore 4: musescore_hammond (Muse Sounds)...")
    # Geramos o MIDI lento (program 16) primeiro
    temp_mscore_dir = out_dir / "temp_mscore"
    subprocess.run([
        ".venv/bin/python", "gerar_meia_hora.py",
        "--hinos", str(hino_id),
        "--program", "16",
        "--output", str(temp_mscore_dir)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    midi_lento = list((temp_mscore_dir / "midi").glob("*_lento.mid"))
    if midi_lento:
        dest_mscore_mp3 = out_dir / f"hino_{hino_id}_musescore_hammond.mp3"
        if dest_mscore_mp3.exists():
            dest_mscore_mp3.unlink()
            
        print("  Renderizando com MuseScore 4 CLI...")
        subprocess.run([
            "/Applications/MuseScore 4.app/Contents/MacOS/mscore",
            "-o", str(dest_mscore_mp3),
            str(midi_lento[0])
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if dest_mscore_mp3.exists():
            print(f"  ✓ Salvo em: {dest_mscore_mp3}")
        else:
            print("  ✗ Falha ao renderizar via MuseScore 4 CLI")
    else:
        print("  ✗ Falha ao gerar MIDI lento para o MuseScore")
        
    # Limpar temporários do MuseScore
    if temp_mscore_dir.exists():
        for f in (temp_mscore_dir / "midi").glob("*"):
            f.unlink()
        (temp_mscore_dir / "midi").rmdir()
        for f in temp_mscore_dir.glob("*"):
            f.unlink()
        temp_mscore_dir.rmdir()
            
    print("\n════════════════════════════════════════════════════════════")
    print("  COMPARAÇÃO CONCLUÍDA!")
    print(f"  Confira os arquivos na pasta: {out_dir.absolute()}")
    print("════════════════════════════════════════════════════════════\n")

if __name__ == "__main__":
    main()
