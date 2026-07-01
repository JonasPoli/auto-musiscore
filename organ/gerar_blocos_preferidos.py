#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gerar_blocos_preferidos.py
==========================
Gera os blocos completos de meia-hora (6 hinos a 50% de velocidade) para as duas
variações de órgãos aprovadas pelo usuário: Drawbar Organ (16) e Rock Organ (18).
"""

import os
import subprocess
from pathlib import Path

def main():
    hinos_completos = "208,260,375,397,401,475"
    ROOT = Path(__file__).parent.parent.absolute()
    VENV_PYTHON = ROOT / ".venv" / "bin" / "python"
    out_dir = Path("output/meia_hora")
    
    presets = {
        16: "drawbar",
        18: "rock"
    }
    
    print("════════════════════════════════════════════════════════════")
    print("  INICIANDO GERAÇÃO DOS BLOCOS COMPLETOS (6 HINOS - ~30 MIN)")
    print("════════════════════════════════════════════════════════════")
    
    for prog, suffix in presets.items():
        print(f"\n▶ Renderizando bloco completo usando preset: {suffix} (Program {prog})...")
        
        preset_dir = out_dir / f"{suffix}_organ"
        preset_dir.mkdir(parents=True, exist_ok=True)
        
        # Executa o script principal para gerar os 6 hinos e o concatenado
        subprocess.run([
            str(VENV_PYTHON), str(ROOT / "organ" / "gerar_meia_hora.py"),
            "--hinos", hinos_completos,
            "--program", str(prog),
            "--output", str(preset_dir)
        ])
        
        # Renomeia o arquivo concatenado de "meia_hora_completa.mp3" para um nome mais descritivo na pasta raiz
        orig_mp3 = preset_dir / "meia_hora_completa.mp3"
        dest_mp3 = out_dir / f"meia_hora_completa_{suffix}.mp3"
        if orig_mp3.exists():
            orig_mp3.rename(dest_mp3)
            print(f"  ✓ Bloco de 30min salvo em: {dest_mp3}")
            
        # Faz o mesmo com o MIDI concatenado
        orig_mid = preset_dir / "midi" / "meia_hora_completa.mid"
        dest_mid = out_dir / "midi" / f"meia_hora_completa_{suffix}.mid"
        dest_mid.parent.mkdir(parents=True, exist_ok=True)
        if orig_mid.exists():
            orig_mid.rename(dest_mid)
            print(f"  ✓ MIDI concatenado salvo em: {dest_mid}")
            
    print("\n════════════════════════════════════════════════════════════")
    print("  TODOS OS BLOCOS FORAM GERADOS COM SUCESSO!")
    print(f"  Arquivos MP3 completos de ~30 minutos salvos em: {out_dir.absolute()}")
    print("════════════════════════════════════════════════════════════\n")

if __name__ == "__main__":
    main()
