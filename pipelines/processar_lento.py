#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
processar_lento.py
Processa e gera os JSONs corretos (com a escala de tempo corrigida)
para todos os MP3s presentes em uma pasta de hinos lentos.
"""

import os
import re
import sys
import argparse
import subprocess
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

ROOT = Path(__file__).parent.parent.absolute()
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"
DEFAULT_DIR = ROOT / "output" / "meia_hora" / "orgao_eletronico_drawbar"

def parse_hino_id(filename):
    name = filename.lower()
    is_coro = "coro" in name
    if is_coro:
        match = re.search(r"coro\s*(\d+)", name)
        if match:
            return f"C{int(match.group(1))}"
            
    match = re.search(r"\d+", filename)
    if not match:
        return None
    num = int(match.group())
    return f"C{num}" if is_coro else str(num)

def process_file(mp3_path, hino_id, output_dir, force=False):
    # O JSON de saída terá o mesmo nome base do MP3, mas com extensão .json
    json_path = output_dir / mp3_path.name.replace(".mp3", ".json")
    
    if not force and json_path.exists():
        return True, mp3_path.name, "skipped"
        
    cmd = [
        str(VENV_PYTHON),
        str(ROOT / "utils" / "sincronizar_letras.py"),
        "--hino", hino_id,
        "--mp3", str(mp3_path),
        "--output", str(json_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return True, mp3_path.name, None
    else:
        return False, mp3_path.name, result.stderr

def main():
    parser = argparse.ArgumentParser(description="Processa em lote e corrige a sincronização das letras para uma pasta de MP3s.")
    parser.add_argument("--dir", type=str, default=str(DEFAULT_DIR), help="Caminho para o diretório com os MP3s (padrão: output_meia_hora/orgao_eletronico_drawbar)")
    parser.add_argument("--force", action="store_true", help="Forçar reprocessamento de todos os arquivos, mesmo os que já possuem JSON.")
    args = parser.parse_args()

    if not VENV_PYTHON.exists():
        print(f"[erro] Python do ambiente virtual não encontrado em: {VENV_PYTHON}")
        sys.exit(1)

    target_dir = Path(args.dir).absolute()
    if not target_dir.exists() or not target_dir.is_dir():
        print(f"[erro] Diretório não encontrado: {target_dir}")
        sys.exit(1)

    print(f"Escaneando pasta: {target_dir.name}...")
    
    tasks = []
    for p in target_dir.glob("*.mp3"):
        if p.name.startswith("._"):
            continue
        hino_id = parse_hino_id(p.name)
        if hino_id:
            tasks.append((p, hino_id))

    total_tasks = len(tasks)
    print(f"Encontrados {total_tasks} arquivos MP3 para alinhar.")

    if total_tasks == 0:
        print("Nenhum arquivo para processar.")
        sys.exit(0)

    print(f"\nIniciando alinhamento paralelo em lote com {os.cpu_count()} workers...")
    
    success_count = 0
    fail_count = 0
    failures = []

    with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        futures = {executor.submit(process_file, t[0], t[1], target_dir, args.force): t for t in tasks}
        
        for idx, future in enumerate(as_completed(futures), 1):
            t = futures[future]
            success, filename, err = future.result()
            hino_id = t[1]
            
            if success:
                success_count += 1
                if err == "skipped":
                    print(f"[{idx}/{total_tasks}] ⏭️ [skip] Hino {hino_id} ({filename})")
                else:
                    print(f"[{idx}/{total_tasks}] ✓ Sincronizado: Hino {hino_id} ({filename})")
            else:
                fail_count += 1
                failures.append((filename, err))
                print(f"[{idx}/{total_tasks}] ✗ Falhou: Hino {hino_id} ({filename})")

    print(f"\n{'='*50}")
    print(f"Sincronização em lote finalizada!")
    print(f"Sucessos: {success_count}/{total_tasks}")
    print(f"Falhas: {fail_count}/{total_tasks}")
    print(f"{'='*50}\n")

    if failures:
        print("Erros detalhados:")
        for name, err in failures[:20]:
            print(f"  - {name}: {err.strip()}")
        if len(failures) > 20:
            print(f"  ... e mais {len(failures)-20} falhas.")

if __name__ == "__main__":
    main()
