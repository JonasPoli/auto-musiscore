#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
processar_todos.py — Processa todos os arquivos de brass e string gerados no lote.
"""

import os
import re
import sys
import subprocess
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

ROOT = Path(__file__).parent.absolute()
BRASS_DIR = ROOT / "brass"
STRING_DIR = ROOT / "string"
OUTPUT_LYRICS_DIR = ROOT / "output" / "lyrics"
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"

def parse_hino_id(filename):
    name = filename.lower()
    is_coro = "coro" in name
    match = re.search(r"\d+", filename)
    if not match:
        return None
    num = int(match.group())
    return f"C{num}" if is_coro else str(num)

def process_file(mp3_path, output_dir, hino_id, force=False):
    output_path = output_dir / f"hino-{hino_id}.json"
    
    if not force and output_path.exists():
        return True, mp3_path.name, "skipped"
        
    cmd = [
        str(VENV_PYTHON),
        str(ROOT / "sincronizar_letras.py"),
        "--hino", hino_id,
        "--mp3", str(mp3_path),
        "--output", str(output_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return True, mp3_path.name, None
    else:
        return False, mp3_path.name, result.stderr

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Processa todos os arquivos de brass e string.")
    parser.add_argument("--force", action="store_true", help="Forçar reprocessamento de todos os arquivos, mesmo os que já possuem JSON.")
    args = parser.parse_args()

    if not VENV_PYTHON.exists():
        print(f"[erro] Virtual environment python não encontrado em: {VENV_PYTHON}")
        sys.exit(1)
        
    tasks = []
    
    # 1. Escanear Brass
    if BRASS_DIR.exists():
        brass_out = OUTPUT_LYRICS_DIR / "brass"
        brass_out.mkdir(parents=True, exist_ok=True)
        for p in BRASS_DIR.glob("*.mp3"):
            if p.name.startswith("._"):
                continue
            hino_id = parse_hino_id(p.name)
            if hino_id:
                tasks.append((p, brass_out, hino_id, "brass"))
                
    # 2. Escanear String
    if STRING_DIR.exists():
        string_out = OUTPUT_LYRICS_DIR / "string"
        string_out.mkdir(parents=True, exist_ok=True)
        for p in STRING_DIR.glob("*.mp3"):
            if p.name.startswith("._"):
                continue
            hino_id = parse_hino_id(p.name)
            if hino_id:
                tasks.append((p, string_out, hino_id, "string"))
                
    total_tasks = len(tasks)
    print(f"Encontrados {total_tasks} arquivos MP3 para processar ({len([t for t in tasks if t[3] == 'brass'])} de brass, {len([t for t in tasks if t[3] == 'string'])} de string).")
    
    if total_tasks == 0:
        print("Nenhum arquivo para processar.")
        sys.exit(0)
        
    # Executar em paralelo
    success_count = 0
    fail_count = 0
    failures = []
    
    print(f"Iniciando processamento paralelo com {os.cpu_count()} workers...")
    
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        futures = {executor.submit(process_file, t[0], t[1], t[2], args.force): t for t in tasks}
        
        for idx, future in enumerate(as_completed(futures), 1):
            t = futures[future]
            success, filename, err = future.result()
            category = t[3]
            hino_id = t[2]
            
            if success:
                success_count += 1
                if err == "skipped":
                    print(f"[{idx}/{total_tasks}] ⏭️ [skip] [{category}] Hino {hino_id} ({filename})")
                else:
                    print(f"[{idx}/{total_tasks}] ✓ [{category}] Hino {hino_id} ({filename})")
            else:
                fail_count += 1
                failures.append((filename, err))
                print(f"[{idx}/{total_tasks}] ✗ [{category}] Hino {hino_id} ({filename}) - FALHOU")
                
    print(f"\n{'='*50}")
    print(f"Processamento concluído!")
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