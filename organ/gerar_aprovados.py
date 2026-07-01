#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gerar_aprovados.py
==================
Gera as 3 versões de órgãos eletrônicos preferidos do usuário (Drawbar, Rock, e o Combinado/Layered 16,18)
junto com a versão do MuseScore 4 Hammond, tudo em uma pasta de comparação limpa.
"""

import os
import subprocess
from pathlib import Path

def main():
    hino_id = 208
    ROOT = Path(__file__).parent.parent.absolute()
    VENV_PYTHON = ROOT / ".venv" / "bin" / "python"
    out_dir = Path("output/meia_hora/comparacao")
    
    # Limpa e recria a pasta de comparação
    if out_dir.exists():
        for f in out_dir.glob("*.mp3"):
            f.unlink()
        for d in out_dir.glob("temp_*"):
            if d.is_dir():
                for f in d.rglob("*"):
                    if f.is_file():
                        f.unlink()
                # remove subdirs
                for sd in d.glob("*"):
                    if sd.is_dir():
                        sd.rmdir()
                d.rmdir()
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Configuração dos presets aprovados e combinados
    presets = {
        "16": "drawbar",
        "18": "rock",
        "16,18": "combinado_drawbar_rock"
    }
    
    print("════════════════════════════════════════════════════════════")
    print("  GERANDO SONS DE ÓRGÃOS APROVADOS E COMBINAÇÃO")
    print("════════════════════════════════════════════════════════════")
    
    # 1. Gerar as versões via FluidSynth
    for prog, name in presets.items():
        print(f"\n▶ Gerando versão: {name} (Program {prog})...")
        temp_out = out_dir / f"temp_{name}"
        
        subprocess.run([
            str(VENV_PYTHON), str(ROOT / "organ" / "gerar_meia_hora.py"),
            "--hinos", str(hino_id),
            "--program", prog,
            "--output", str(temp_out)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        mp3s = [f for f in temp_out.glob("*.mp3") if not f.name.startswith("._")]
        if mp3s:
            dest_file = out_dir / f"hino_{hino_id}_{name}.mp3"
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

    # 2. Gerar a versão usando o Hammond Organ nativo do MuseScore 4
    print("\n▶ Gerando versão MuseScore 4: musescore_hammond...")
    temp_mscore_dir = out_dir / "temp_mscore"
    subprocess.run([
        str(VENV_PYTHON), str(ROOT / "organ" / "gerar_meia_hora.py"),
        "--hinos", str(hino_id),
        "--program", "16",
        "--output", str(temp_mscore_dir)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    midi_lento = [f for f in (temp_mscore_dir / "midi").glob("*_lento.mid") if not f.name.startswith("._")]
    if midi_lento:
        dest_mscore_mp3 = out_dir / f"hino_{hino_id}_musescore_hammond.mp3"
        subprocess.run([
            "/Applications/MuseScore 4.app/Contents/MacOS/mscore",
            "-o", str(dest_mscore_mp3),
            str(midi_lento[0])
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if dest_mscore_mp3.exists():
            print(f"  ✓ Salvo em: {dest_mscore_mp3}")
        else:
            print("  ✗ Falha ao renderizar via MuseScore 4")
    else:
        print("  ✗ Falha ao gerar MIDI para MuseScore")
        
    # Limpar temporários do MuseScore
    if temp_mscore_dir.exists():
        for f in (temp_mscore_dir / "midi").glob("*"):
            f.unlink()
        (temp_mscore_dir / "midi").rmdir()
        for f in temp_mscore_dir.glob("*"):
            f.unlink()
        temp_mscore_dir.rmdir()
            
    print("\n════════════════════════════════════════════════════════════")
    print("  GERAÇÃO DE APROVADOS CONCLUÍDA!")
    print(f"  Arquivos prontos em: {out_dir.absolute()}")
    print("════════════════════════════════════════════════════════════\n")

if __name__ == "__main__":
    main()
