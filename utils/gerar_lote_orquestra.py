#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
utils/gerar_lote_orquestra.py
=============================
Script orquestrador para processar múltiplos hinos em lote, utilizando
a sonoridade e mapeamentos definidos na biblioteca de timbres de orquestra.

Gera para cada hino:
  - O arquivo MP3 final em output/orquestra/
  - O arquivo JSON de letras sincronizadas
  - A pasta de lastro (hino_XXX_partes/) contendo os MSCZ e o arquivo de explicação.md
"""

import sys
import re
import argparse
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT / 'utils'))

from gerar_hino_completo import gerar_hino_completo
from velocidade_hinos import HINOS

def extrair_prefixo_e_id(path: Path) -> (str, int):
    match = re.search(r'(\d+)', path.name)
    hino_id = int(match.group(1)) if match else -1
    prefix = 'coro' if 'coro' in path.name.lower() else 'hino'
    return prefix, hino_id

def processar_lote(start_id: int = None, end_id: int = None, speed_factor: float = 1.0):
    midi_dir = ROOT / 'mid'
    output_dir = ROOT / 'output' / 'orquestra'
    output_dir.mkdir(parents=True, exist_ok=True)

    if not midi_dir.exists():
        print(f"ERRO: Pasta de entrada MIDI não encontrada em: {midi_dir}")
        return

    # Varre os arquivos MIDI
    midi_files = sorted(list(midi_dir.glob("*.mid")))
    to_process = []
    for f in midi_files:
        prefix, hino_id = extrair_prefixo_e_id(f)
        if hino_id != -1:
            if start_id is not None and hino_id < start_id:
                continue
            if end_id is not None and hino_id > end_id:
                continue
            to_process.append((prefix, hino_id, f))

    if not to_process:
        print("Nenhum hino encontrado no intervalo especificado.")
        return

    total = len(to_process)
    print(f"============================================================")
    print(f" INICIANDO PROCESSAMENTO DE LOTE (ORQUESTRA)")
    print(f" Total de hinos a processar: {total}")
    print(f" Pasta de Saída: {output_dir}")
    print(f"============================================================")

    sucessos = 0
    falhas = []
    tempo_inicio = time.time()

    for idx, (prefix, hino_id, midi_path) in enumerate(to_process, 1):
        hino_str = f"{prefix}_{hino_id:03d}"
        output_mp3 = output_dir / f"{hino_str}.mp3"
        
        print(f"\n[{idx}/{total}] Processando {midi_path.name}...")
        print(f"  ➔ Alvo: {output_mp3.name}")
        
        bpm_target = None
        speed_param = None
        if prefix == 'hino' and hino_id in HINOS:
            bpm_base = HINOS[hino_id][0]
            bpm_target = bpm_base * speed_factor
            print(f"  ➔ BPM Base (Tabela): {bpm_base} | Alvo ({speed_factor:.2f}x): {bpm_target:.1f}")
        else:
            speed_param = speed_factor
            print(f"  ➔ Velocidade original do MIDI escalada em: {speed_factor:.2f}x")
            
        t0 = time.time()
        try:
            ok = gerar_hino_completo(str(midi_path), str(output_mp3), bpm_target=bpm_target, speed=speed_param)
            t_elap = time.time() - t0
            if ok:
                print(f"  [OK] Concluído em {t_elap:.1f}s")
                sucessos += 1
            else:
                print(f"  [ERRO] Falha ao renderizar {hino_str}")
                falhas.append(midi_path.name)
        except Exception as e:
            t_elap = time.time() - t0
            print(f"  [EXCEÇÃO] Erro crítico no hino {hino_id}: {e}")
            falhas.append(midi_path.name)

    tempo_total = time.time() - tempo_inicio
    print(f"\n============================================================")
    print(f" FIM DO PROCESSAMENTO")
    print(f" Tempo total: {tempo_total/60:.1f} minutos")
    print(f" Sucessos: {sucessos}/{total}")
    if falhas:
        print(f" Falhas ({len(falhas)}):")
        for f in falhas:
            print(f"  - {f}")
    print(f"============================================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Geração de lote orquestra para hinos.")
    parser.add_argument("--start", type=int, default=None, help="ID inicial do hino (ex: 1)")
    parser.add_argument("--end",   type=int, default=None, help="ID final do hino (ex: 5)")
    parser.add_argument("--speed-factor", type=float, default=1.0, help="Fator de velocidade (ex: 1.0 = padrão, 0.85 = -15%, 1.15 = +15%)")
    args = parser.parse_args()

    processar_lote(args.start, args.end, args.speed_factor)
