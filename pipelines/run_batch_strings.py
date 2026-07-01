#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Processo completo de orquestração e pós-processamento de cordas em lote.
"""

import os
import glob
import subprocess
import shutil
import sys

def main():
    from pathlib import Path
    ROOT = Path(__file__).parent.parent.absolute()
    midi_dir = str(ROOT / "mid")
    temp_dir = str(ROOT / "temp_orchestra")
    output_dir = str(ROOT / "output" / "string")

    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    # Localiza todos os arquivos MIDI na pasta mid
    midi_files = sorted(glob.glob(os.path.join(midi_dir, "*.mid")))
    total = len(midi_files)

    if total == 0:
        print(f"Nenhum arquivo MIDI encontrado na pasta '{midi_dir}'.")
        return

    python_bin = sys.executable
    print("════════════════════════════════════════════════════════════")
    print(f" Iniciando processamento em lote de {total} arquivos MIDI")
    print(f" Interpretador Python: {python_bin}")
    print(f" Pasta de saída final: {output_dir}/")
    print("════════════════════════════════════════════════════════════\n")

    for idx, midi_path in enumerate(midi_files, 1):
        filename = os.path.basename(midi_path)
        name_without_ext = os.path.splitext(filename)[0]
        final_mp3_path = os.path.join(output_dir, f"{name_without_ext}.mp3")

        import datetime
        cutoff_epoch = datetime.datetime(2026, 6, 23, 15, 30, 0).timestamp()

        if os.path.exists(final_mp3_path):
            mtime = os.path.getmtime(final_mp3_path)
            if mtime >= cutoff_epoch:
                # Já é um arquivo orquestrado com Preset 1
                continue
            else:
                print(f"[{idx}/{total}] Arquivo antigo (Preset 9) detectado. Re-processando: {name_without_ext}...")

        print(f"[{idx}/{total}] Processando: {name_without_ext}...")

        try:
            # 1. Rodar orquestração
            print("  -> Executando orquestração (16 instrumentos, preset 1)...")
            cmd_orch = [
                python_bin, str(ROOT / "orchestrators" / "musescore_strings_16part.py"),
                "--midi", midi_path,
                "--preset", "1",
                "--speed", "0.9",
                "--output", temp_dir
            ]
            # Redireciona a saída do processo filho para não poluir o console principal
            subprocess.run(cmd_orch, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # 2. Rodar pós-processador
            raw_mp3_name = f"{name_without_ext}_preset1_16part_speed90.mp3"
            raw_mp3_path = os.path.join(temp_dir, raw_mp3_name)
            
            if not os.path.exists(raw_mp3_path):
                raise FileNotFoundError(f"Arquivo MP3 bruto não gerado: {raw_mp3_path}")

            print("  -> Executando pós-processamento (fade-in suave, lookback=200ms)...")
            cmd_post = [
                python_bin, str(ROOT / "utils" / "postprocess_fade_apos_pausa.py"),
                "--input", raw_mp3_path,
                "--output", temp_dir,
                "--suffix", "_suave",
                "--lookback-ms", "200"
            ]
            subprocess.run(cmd_post, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # 3. Copiar para pasta final com nome original
            suave_mp3_name = f"{name_without_ext}_preset1_16part_speed90_suave.mp3"
            suave_mp3_path = os.path.join(temp_dir, suave_mp3_name)

            if not os.path.exists(suave_mp3_path):
                raise FileNotFoundError(f"Arquivo suavizado não encontrado: {suave_mp3_path}")

            shutil.copy2(suave_mp3_path, final_mp3_path)
            print(f"  ✓ Concluído com sucesso! Salvo em: {final_mp3_path}\n")

            # Limpar arquivos temporários deste arquivo para economizar espaço
            temp_midi_path = os.path.join(temp_dir, f"{name_without_ext}_preset1_16part_speed90.mid")
            for p in [raw_mp3_path, suave_mp3_path, temp_midi_path]:
                if os.path.exists(p):
                    os.remove(p)

        except Exception as e:
            print(f"  ✗ FALHOU no arquivo {name_without_ext}: {e}\n")

    # Remover diretório temporário se estiver vazio
    try:
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)
    except Exception:
        pass

    print("════════════════════════════════════════════════════════════")
    print(" Processamento em lote concluído!")
    print(f" Verifique os áudios finais em: {output_dir}/")
    print("════════════════════════════════════════════════════════════")

if __name__ == "__main__":
    main()
