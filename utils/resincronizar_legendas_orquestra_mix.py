#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
utils/resincronizar_legendas_orquestra_mix.py
=============================================
Utilitário para re-sincronizar todas as legendas (.json) geradas nas pastas
output/orquestra_nicho/orquestra01 e output/orquestra_nicho/orquestra02
utilizando a reconstrução da linha do tempo por frases (_partes).

Uso:
  python utils/resincronizar_legendas_orquestra_mix.py [--style orquestra01|orquestra02|all] [--speed-factor 1.0]
"""

import sys
import re
import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent.absolute()
sinc_script = ROOT / "utils" / "sincronizar_letras.py"


def resincronizar_estilo(style: str, speed_factor: float = 1.0):
    style_dir = ROOT / "output" / "orquestra_nicho" / style
    if not style_dir.exists():
        print(f"⚠️ Diretório do estilo {style} não encontrado em: {style_dir}")
        return 0, 0

    mp3_files = sorted([f for f in style_dir.glob("*.mp3") if not f.name.startswith("._")])
    if not mp3_files:
        print(f"⚠️ Nenhum arquivo MP3 encontrado em {style_dir}")
        return 0, 0

    print(f"\n🔄 Re-sincronizando legendas para {style.upper()} ({len(mp3_files)} arquivos MP3)...")
    sucessos = 0
    falhas = 0

    for idx, mp3_path in enumerate(mp3_files, 1):
        # Extrair hino/coro ID
        is_coro = 'coro' in mp3_path.name.lower()
        match = re.search(r'(\d+)', mp3_path.name)
        if not match:
            continue
        num_id = int(match.group(1))
        hino_id_str = f"C{num_id}" if is_coro else str(num_id)

        json_path = mp3_path.with_suffix('.json')
        partes_dir = mp3_path.parent / f"{mp3_path.stem}_partes"

        cmd = [
            sys.executable, str(sinc_script),
            '--hino', hino_id_str,
            '--mp3', str(mp3_path),
            '--output', str(json_path),
            '--speed-factor', str(speed_factor)
        ]
        if partes_dir.exists():
            cmd += ['--partes-dir', str(partes_dir)]

        print(f"[{idx}/{len(mp3_files)}] {mp3_path.name} -> {json_path.name} ... ", end="", flush=True)
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            print("✅ OK")
            sucessos += 1
        else:
            print(f"❌ FALHA (rc={r.returncode})")
            if r.stderr:
                print(f"   STDERR: {r.stderr.strip()[:200]}")
            falhas += 1

    return sucessos, falhas


def main():
    parser = argparse.ArgumentParser(description="Re-sincroniza legendas JSON dos estilos Orquestra 01 e 02.")
    parser.add_argument('--style', type=str, default="all", choices=["orquestra01", "orquestra02", "all"],
                        help="Estilo alvo (orquestra01, orquestra02 ou all)")
    parser.add_argument('--speed-factor', type=float, default=1.0,
                        help="Fator multiplicador de velocidade utilizado na geração (padrão: 1.0)")

    args = parser.parse_args()
    styles = ["orquestra01", "orquestra02"] if args.style == "all" else [args.style]

    tot_suc = 0
    tot_fal = 0
    for st in styles:
        suc, fal = resincronizar_estilo(st, speed_factor=args.speed_factor)
        tot_suc += suc
        tot_fal += fal

    print("\n" + "=" * 60)
    print("📋 RESUMO DA RE-SINCRONIZAÇÃO DE LEGENDAS")
    print(f"  Sucessos: {tot_suc}")
    print(f"  Falhas:   {tot_fal}")
    print("=" * 60)


if __name__ == '__main__':
    main()
