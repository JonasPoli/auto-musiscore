#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
utils/gerar_lote_nicho.py
=========================
Script orquestrador para processar múltiplos hinos E coros em lote, gerando para
cada um 4 versões de nicho (Strings, Brass, Paletas, Sopros) independentemente.

O filtro --start/--end aplica-se APENAS a hinos (001-480).
Coros (001-006) são SEMPRE incluídos, a menos que --skip-coros seja passado.

Ao final, imprime um relatório de completude verificando:
  - 480 hinos (hino_001.mp3 ... hino_480.mp3) por nicho
  - 6 coros  (coro_001.mp3 ... coro_006.mp3) por nicho
"""

import sys
import re
import argparse
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT / 'utils'))

from gerar_hino_nicho_completo import gerar_hino_nicho_completo
from velocidade_hinos import HINOS

TOTAL_HINOS = 480
TOTAL_COROS = 6
GROUPS = ["strings", "brass", "paletas", "sopros"]


def extrair_prefixo_e_id(path: Path) -> (str, int):
    match = re.search(r'(\d+)', path.name)
    hino_id = int(match.group(1)) if match else -1
    prefix = 'coro' if 'coro' in path.name.lower() else 'hino'
    return prefix, hino_id


def verificar_completude(output_dir: Path) -> dict:
    """Verifica a completude de hinos e coros em cada nicho.
    
    Retorna dict {grupo: {"hinos_faltantes": [...], "coros_faltantes": [...]}}.
    """
    resultado = {}
    for group in GROUPS:
        group_dir = output_dir / group
        hinos_faltantes = []
        coros_faltantes = []

        for i in range(1, TOTAL_HINOS + 1):
            mp3 = group_dir / f"hino_{i:03d}.mp3"
            if not mp3.exists():
                hinos_faltantes.append(i)

        for i in range(1, TOTAL_COROS + 1):
            mp3 = group_dir / f"coro_{i:03d}.mp3"
            if not mp3.exists():
                coros_faltantes.append(i)

        resultado[group] = {
            "hinos_faltantes": hinos_faltantes,
            "coros_faltantes": coros_faltantes,
        }
    return resultado


def imprimir_relatorio_completude(resultado: dict) -> int:
    """Imprime relatório de completude e retorna total de faltantes."""
    total_faltantes = 0
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║         📋 RELATÓRIO DE COMPLETUDE — NICHOS                ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    for group in GROUPS:
        info = resultado[group]
        h_ok = TOTAL_HINOS - len(info["hinos_faltantes"])
        c_ok = TOTAL_COROS - len(info["coros_faltantes"])
        h_status = "✅" if not info["hinos_faltantes"] else "❌"
        c_status = "✅" if not info["coros_faltantes"] else "❌"

        print(f"║  {group.upper():10s}  Hinos: {h_ok:3d}/{TOTAL_HINOS} {h_status}  "
              f"Coros: {c_ok}/{TOTAL_COROS} {c_status}       ║")

        if info["hinos_faltantes"]:
            nums = ", ".join(str(n) for n in info["hinos_faltantes"][:20])
            if len(info["hinos_faltantes"]) > 20:
                nums += f" ... (+{len(info['hinos_faltantes'])-20})"
            print(f"║    Hinos faltantes: {nums:<40s}║")
            total_faltantes += len(info["hinos_faltantes"])

        if info["coros_faltantes"]:
            nums = ", ".join(str(n) for n in info["coros_faltantes"])
            print(f"║    Coros faltantes: {nums:<40s}║")
            total_faltantes += len(info["coros_faltantes"])

    print("╠══════════════════════════════════════════════════════════════╣")
    esperado = (TOTAL_HINOS + TOTAL_COROS) * len(GROUPS)
    gerado = esperado - total_faltantes
    if total_faltantes == 0:
        print(f"║  ✅ COMPLETO! {gerado}/{esperado} arquivos gerados.              ║")
    else:
        print(f"║  ⚠️  {total_faltantes} arquivo(s) faltante(s) de {esperado} esperados.       ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    return total_faltantes


def _processar_item(prefix, hino_id, midi_path, group, output_dir,
                    speed_factor, overwrite, idx_global, total):
    """Processa um único item (hino ou coro) para um nicho.
    
    Retorna: ('sucesso' | 'pulado' | 'falha', nome_para_log)
    """
    group_dir = output_dir / group
    group_dir.mkdir(parents=True, exist_ok=True)

    hino_str = f"{prefix}_{hino_id:03d}"
    output_mp3 = group_dir / f"{hino_str}.mp3"

    if not overwrite and output_mp3.exists():
        print(f"\n[{idx_global}/{total}] Pulando {midi_path.name} ({group}) "
              f"(já existe {output_mp3.name})")
        return 'pulado', None

    print(f"\n[{idx_global}/{total}] Processando {midi_path.name} "
          f"para o Nicho {group.upper()}...")
    print(f"  ➔ Alvo: {output_mp3.relative_to(ROOT)}")

    bpm_target = None
    speed_param = None
    if prefix == 'hino' and hino_id in HINOS:
        bpm_base = HINOS[hino_id][0]
        bpm_target = bpm_base * speed_factor
        print(f"  ➔ BPM Base (Tabela): {bpm_base} | "
              f"Alvo ({speed_factor:.2f}x): {bpm_target:.1f}")
    else:
        speed_param = speed_factor
        print(f"  ➔ Velocidade original do MIDI escalada em: "
              f"{speed_factor:.2f}x")

    t0 = time.time()
    try:
        ok = gerar_hino_nicho_completo(
            str(midi_path), str(output_mp3),
            group=group, bpm_target=bpm_target, speed=speed_param
        )
        t_elap = time.time() - t0
        if ok:
            print(f"  [OK] Concluído em {t_elap:.1f}s")
            return 'sucesso', None
        else:
            print(f"  [ERRO] Falha ao renderizar {hino_str} ({group})")
            return 'falha', f"{midi_path.name} ({group})"
    except Exception as e:
        t_elap = time.time() - t0
        print(f"  [EXCEÇÃO] Erro crítico no {prefix} {hino_id} ({group}): {e}")
        return 'falha', f"{midi_path.name} ({group})"


def processar_lote(start_id: int = None, end_id: int = None,
                   speed_factor: float = 1.0, overwrite: bool = False,
                   skip_coros: bool = False):
    midi_dir = ROOT / 'mid'
    output_dir = ROOT / 'output' / 'orquestra_nicho'
    output_dir.mkdir(parents=True, exist_ok=True)

    if not midi_dir.exists():
        print(f"ERRO: Pasta de entrada MIDI não encontrada em: {midi_dir}")
        return

    # ── Varre os arquivos MIDI separando hinos de coros ──────────────────
    midi_files = sorted(list(midi_dir.glob("*.mid")))
    hinos_to_process = []
    coros_to_process = []

    for f in midi_files:
        prefix, hino_id = extrair_prefixo_e_id(f)
        if hino_id == -1:
            continue

        if prefix == 'coro':
            # Coros: sempre incluídos (não respeitam --start/--end)
            coros_to_process.append((prefix, hino_id, f))
        else:
            # Hinos: respeitam --start/--end
            if start_id is not None and hino_id < start_id:
                continue
            if end_id is not None and hino_id > end_id:
                continue
            hinos_to_process.append((prefix, hino_id, f))

    # Combina: hinos primeiro, depois coros (se não pulados)
    to_process = list(hinos_to_process)
    if not skip_coros:
        to_process.extend(coros_to_process)
    elif coros_to_process:
        print(f"\n  ⏭ Pulando {len(coros_to_process)} coro(s) (--skip-coros)")

    if not to_process:
        print("Nenhum hino/coro encontrado no intervalo especificado.")
        return

    n_hinos = len(hinos_to_process)
    n_coros = len(coros_to_process) if not skip_coros else 0
    total = len(to_process) * len(GROUPS)

    print(f"============================================================")
    print(f" INICIANDO PROCESSAMENTO DE LOTE (NICHO INDIVIDUAL)")
    print(f" Hinos: {n_hinos} | Coros: {n_coros}")
    print(f" Total de arquivos a gerar: {total} "
          f"({len(to_process)} itens x {len(GROUPS)} nichos)")
    print(f" Pasta de Saída: {output_dir}")
    print(f"============================================================")

    sucessos = 0
    pulados = 0
    falhas = []
    tempo_inicio = time.time()

    idx_global = 1
    for idx, (prefix, hino_id, midi_path) in enumerate(to_process, 1):
        for group in GROUPS:
            status, nome = _processar_item(
                prefix, hino_id, midi_path, group, output_dir,
                speed_factor, overwrite, idx_global, total
            )
            if status == 'sucesso':
                sucessos += 1
            elif status == 'pulado':
                pulados += 1
            else:
                falhas.append(nome)
            idx_global += 1

    tempo_total = time.time() - tempo_inicio
    print(f"\n============================================================")
    print(f" FIM DO PROCESSAMENTO")
    print(f" Tempo total: {tempo_total/60:.1f} minutos")
    print(f" Sucessos: {sucessos}/{total}")
    if pulados > 0:
        print(f" Pulados (já existentes): {pulados}/{total}")
    if falhas:
        print(f" Falhas ({len(falhas)}):")
        for f in falhas:
            print(f"  - {f}")
    print(f"============================================================")

    # ── Relatório de completude ──────────────────────────────────────────
    resultado = verificar_completude(output_dir)
    total_faltantes = imprimir_relatorio_completude(resultado)
    return total_faltantes


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Geração de lote de nichos individuais para hinos e coros."
    )
    parser.add_argument("--start", type=int, default=None,
                        help="ID inicial do hino (ex: 1). Não afeta coros.")
    parser.add_argument("--end", type=int, default=None,
                        help="ID final do hino (ex: 480). Não afeta coros.")
    parser.add_argument("--speed-factor", type=float, default=1.0,
                        help="Fator de velocidade (ex: 1.0 = padrão, "
                             "0.85 = -15%%, 1.15 = +15%%)")
    parser.add_argument("--overwrite", action="store_true",
                        help="Força a regeração mesmo se o MP3 já existir")
    parser.add_argument("--skip-coros", action="store_true",
                        help="Pular geração dos coros (processar somente hinos)")
    args = parser.parse_args()

    faltantes = processar_lote(
        args.start, args.end, args.speed_factor,
        overwrite=args.overwrite, skip_coros=args.skip_coros
    )
    sys.exit(0 if (faltantes is None or faltantes == 0) else 1)
