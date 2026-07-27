#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
utils/verificar_completude_orquestra_mix.py
============================================
Script de auditoria e retry para garantir que todos os 480 hinos + 6 coros
estejam gerados para Orquestra 01 e Orquestra 02.

Uso:
  python utils/verificar_completude_orquestra_mix.py                 # só verifica
  python utils/verificar_completude_orquestra_mix.py --regerar       # verifica e regera faltantes
  python utils/verificar_completude_orquestra_mix.py --regerar --max-retries 3
"""

import sys
import re
import argparse
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT / 'utils'))

from gerar_hino_orquestra01 import gerar_hino_orquestra01
from gerar_hino_orquestra02 import gerar_hino_orquestra02
from velocidade_hinos import HINOS

TOTAL_HINOS = 480
TOTAL_COROS = 6
STYLES = ["orquestra01", "orquestra02"]


def extrair_prefixo_e_id(path: Path) -> (str, int):
    match = re.search(r'(\d+)', path.name)
    hino_id = int(match.group(1)) if match else -1
    prefix = 'coro' if 'coro' in path.name.lower() else 'hino'
    return prefix, hino_id


def mapear_midis(midi_dir: Path) -> (dict, dict):
    """Mapeia hino_id -> Path para hinos e coros."""
    hinos_map = {}
    coros_map = {}
    for f in midi_dir.glob("*.mid"):
        prefix, hino_id = extrair_prefixo_e_id(f)
        if hino_id != -1:
            if prefix == 'coro':
                coros_map[hino_id] = f
            else:
                hinos_map[hino_id] = f
    return hinos_map, coros_map


def verificar_completude(output_dir: Path) -> dict:
    resultado = {}
    for style in STYLES:
        style_dir = output_dir / style
        hinos_faltantes = []
        coros_faltantes = []

        for i in range(1, TOTAL_HINOS + 1):
            mp3 = style_dir / f"hino_{i:03d}.mp3"
            if not mp3.exists() or mp3.stat().st_size < 1000:
                hinos_faltantes.append(i)

        for i in range(1, TOTAL_COROS + 1):
            mp3 = style_dir / f"coro_{i:03d}.mp3"
            if not mp3.exists() or mp3.stat().st_size < 1000:
                coros_faltantes.append(i)

        resultado[style] = {
            "hinos_faltantes": hinos_faltantes,
            "coros_faltantes": coros_faltantes,
        }
    return resultado


def imprimir_relatorio(resultado: dict) -> int:
    total_faltantes = 0
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║     📋 AUDITORIA DE COMPLETUDE — ORQUESTRA MIX (01 & 02)     ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    for style in STYLES:
        info = resultado[style]
        h_ok = TOTAL_HINOS - len(info["hinos_faltantes"])
        c_ok = TOTAL_COROS - len(info["coros_faltantes"])
        h_status = "✅" if not info["hinos_faltantes"] else "❌"
        c_status = "✅" if not info["coros_faltantes"] else "❌"

        print(f"║  {style.upper():13s} Hinos: {h_ok:3d}/{TOTAL_HINOS} {h_status}  "
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
    esperado = (TOTAL_HINOS + TOTAL_COROS) * len(STYLES)
    gerado = esperado - total_faltantes
    if total_faltantes == 0:
        print(f"║  ✅ TUDO COMPLETO! {gerado}/{esperado} arquivos presentes.          ║")
    else:
        print(f"║  ⚠️  {total_faltantes} arquivo(s) faltante(s) de {esperado} esperados.       ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    return total_faltantes


def regerar_faltantes(resultado: dict, speed_factor: float = 1.0, max_retries: int = 3) -> int:
    midi_dir = ROOT / 'mid'
    output_dir = ROOT / 'output' / 'orquestra_nicho'
    hinos_map, coros_map = mapear_midis(midi_dir)

    for tentativa in range(1, max_retries + 1):
        faltantes = verificar_completude(output_dir)
        total_faltantes = sum(
            len(info["hinos_faltantes"]) + len(info["coros_faltantes"])
            for info in faltantes.values()
        )

        if total_faltantes == 0:
            print(f"\n✅ Todos os arquivos estão presentes!")
            return 0

        print(f"\n🔄 Tentativa de Re-geração {tentativa}/{max_retries} "
              f"({total_faltantes} faltantes)...")

        for style in STYLES:
            info = faltantes[style]
            style_dir = output_dir / style
            style_dir.mkdir(parents=True, exist_ok=True)

            # Regerar hinos faltantes
            for hino_id in info["hinos_faltantes"]:
                midi_path = hinos_map.get(hino_id)
                if not midi_path:
                    print(f"  ❌ MIDI do Hino {hino_id:03d} não encontrado em {midi_dir}")
                    continue

                output_mp3 = style_dir / f"hino_{hino_id:03d}.mp3"
                bpm_base = HINOS.get(hino_id, (60, 10))[0]
                bpm_target = bpm_base * speed_factor

                print(f"  ➔ Regerando Hino {hino_id:03d} ({style})...")
                try:
                    if style == "orquestra01":
                        gerar_hino_orquestra01(str(midi_path), str(output_mp3), bpm_target=bpm_target)
                    else:
                        gerar_hino_orquestra02(str(midi_path), str(output_mp3), bpm_target=bpm_target)
                except Exception as e:
                    print(f"  ❌ Erro ao regerar Hino {hino_id:03d} ({style}): {e}")

            # Regerar coros faltantes
            for coro_id in info["coros_faltantes"]:
                midi_path = coros_map.get(coro_id)
                if not midi_path:
                    print(f"  ❌ MIDI do Coro {coro_id:03d} não encontrado em {midi_dir}")
                    continue

                output_mp3 = style_dir / f"coro_{coro_id:03d}.mp3"

                print(f"  ➔ Regerando Coro {coro_id:03d} ({style})...")
                try:
                    if style == "orquestra01":
                        gerar_hino_orquestra01(str(midi_path), str(output_mp3), speed=speed_factor)
                    else:
                        gerar_hino_orquestra02(str(midi_path), str(output_mp3), speed=speed_factor)
                except Exception as e:
                    print(f"  ❌ Erro ao regerar Coro {coro_id:03d} ({style}): {e}")

    # Verificação final
    resultado_final = verificar_completude(output_dir)
    return imprimir_relatorio(resultado_final)


def main():
    parser = argparse.ArgumentParser(
        description="Auditoria e re-geração de completude para Orquestra 01 e Orquestra 02."
    )
    parser.add_argument('--regerar', action='store_true',
                        help="Regera automaticamente os arquivos faltantes")
    parser.add_argument('--max-retries', type=int, default=3,
                        help="Número máximo de tentativas de re-geração (padrão: 3)")
    parser.add_argument('--speed-factor', type=float, default=1.0,
                        help="Fator multiplicador de velocidade para re-geração")

    args = parser.parse_args()
    output_dir = ROOT / 'output' / 'orquestra_nicho'

    resultado = verificar_completude(output_dir)
    total_faltantes = imprimir_relatorio(resultado)

    if args.regerar and total_faltantes > 0:
        total_faltantes = regerar_faltantes(
            resultado,
            speed_factor=args.speed_factor,
            max_retries=args.max_retries
        )

    sys.exit(0 if total_faltantes == 0 else 1)


if __name__ == '__main__':
    main()
