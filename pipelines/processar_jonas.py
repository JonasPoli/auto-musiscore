#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
processar_jonas.py — Processa todos os arquivos de mudicbox, orgao e piano eqinox para gerar JSONs ao lado de cada MP3.
"""

import os
import re
import sys
import subprocess
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

ROOT = Path(__file__).parent.parent.absolute()
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"

DIRS_TO_PROCESS = [
    Path("/Volumes/Dados/documentos-jonas/hinario/mp3 dp jonas/mudicbox"),
    Path("/Volumes/Dados/documentos-jonas/hinario/mp3 dp jonas/orgão"),
    Path("/Volumes/Dados/documentos-jonas/hinario/mp3 dp jonas/piano eqinox")
]

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

def process_file(mp3_path, hino_id, force=False):
    # Salvar o JSON ao lado do MP3 original com a extensão .json
    output_path = mp3_path.with_suffix(".json")
    
    if not force and output_path.exists():
        return True, mp3_path.name, "skipped"
        
    cmd = [
        str(VENV_PYTHON),
        str(ROOT / "utils" / "sincronizar_letras.py"),
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
    parser = argparse.ArgumentParser(description="Processa todos os arquivos de mudicbox, orgao e piano eqinox.")
    parser.add_argument("--force", action="store_true", help="Forçar reprocessamento de todos os arquivos, mesmo os que já possuem JSON.")
    args = parser.parse_args()

    if not VENV_PYTHON.exists():
        print(f"[erro] Virtual environment python não encontrado em: {VENV_PYTHON}")
        sys.exit(1)
        
    tasks = []
    
    for folder in DIRS_TO_PROCESS:
        if not folder.exists():
            print(f"[aviso] Diretório não encontrado, pulando: {folder}")
            continue
            
        print(f"Escaneando diretório: {folder.name}...")
        for p in folder.glob("*.mp3"):
            if p.name.startswith("._"):
                continue
            hino_id = parse_hino_id(p.name)
            if hino_id:
                tasks.append((p, hino_id, folder.name))
                
    total_tasks = len(tasks)
    print(f"\nEncontrados {total_tasks} arquivos MP3 para processar no total.")
    
    if total_tasks == 0:
        print("Nenhum arquivo para processar.")
        sys.exit(0)
        
    # Executar em paralelo
    success_count = 0
    fail_count = 0
    failures = []
    
    print(f"Iniciando processamento paralelo com {os.cpu_count()} workers...")
    
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        futures = {executor.submit(process_file, t[0], t[1], args.force): t for t in tasks}
        
        for idx, future in enumerate(as_completed(futures), 1):
            t = futures[future]
            success, filename, err = future.result()
            folder_name = t[2]
            hino_id = t[1]
            
            if success:
                success_count += 1
                if err == "skipped":
                    print(f"[{idx}/{total_tasks}] ⏭️ [skip] [{folder_name}] Hino {hino_id} ({filename})")
                else:
                    print(f"[{idx}/{total_tasks}] ✓ [{folder_name}] Hino {hino_id} ({filename})")
            else:
                fail_count += 1
                failures.append((filename, folder_name, err))
                print(f"[{idx}/{total_tasks}] ✗ [{folder_name}] Hino {hino_id} ({filename}) - FALHOU")
                
    print(f"\n{'='*50}")
    print(f"Processamento completo de pastas de Jonas finalizado!")
    print(f"Sucessos: {success_count}/{total_tasks}")
    print(f"Falhas: {fail_count}/{total_tasks}")
    print(f"{'='*50}\n")
    
    if failures:
        print("Erros detalhados:")
        for name, folder, err in failures[:20]:
            print(f"  - [{folder}] {name}: {err.strip()}")
        if len(failures) > 20:
            print(f"  ... e mais {len(failures)-20} falhas.")

if __name__ == "__main__":
    main()