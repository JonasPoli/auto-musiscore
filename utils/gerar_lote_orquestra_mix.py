#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
utils/gerar_lote_orquestra_mix.py
==================================
Orquestrador em lote para gerar todos os 480 hinos e 6 coros nos estilos:
  - orquestra01 (Nicho puro + Orquestra Mix)
  - orquestra02 (Nicho puro + Orquestra Mix + Coral 50% + Rock Organ 12)

Filtros:
  --start 1 --end 480 : aplica-se a hinos.
  Coros (001-006) são sempre incluídos, a menos que --skip-coros seja especificado.
  --style orquestra01|orquestra02|all

Saída:
  output/orquestra_nicho/orquestra01/hino_XXX.mp3 / coro_XXX.mp3
  output/orquestra_nicho/orquestra02/hino_XXX.mp3 / coro_XXX.mp3
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


def verificar_completude(output_dir: Path, target_styles: list = None) -> dict:
    """Verifica a completude de hinos e coros para orquestra01 e orquestra02."""
    if target_styles is None:
        target_styles = STYLES

    resultado = {}
    for style in target_styles:
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


def imprimir_relatorio_completude(resultado: dict, target_styles: list = None) -> int:
    """Imprime relatório de completude e retorna total de faltantes."""
    if target_styles is None:
        target_styles = list(resultado.keys())

    total_faltantes = 0
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║      📋 RELATÓRIO DE COMPLETUDE — ORQUESTRA MIX (01 & 02)     ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    for style in target_styles:
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
    esperado = (TOTAL_HINOS + TOTAL_COROS) * len(target_styles)
    gerado = esperado - total_faltantes
    if total_faltantes == 0:
        print(f"║  ✅ COMPLETO! {gerado}/{esperado} arquivos gerados.              ║")
    else:
        print(f"║  ⚠️  {total_faltantes} arquivo(s) faltante(s) de {esperado} esperados.       ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    return total_faltantes


def _processar_item(prefix, hino_id, midi_path, style, output_dir,
                    speed_factor, overwrite, idx_global, total):
    """Processa um único item para um estilo (orquestra01 ou orquestra02)."""
    style_dir = output_dir / style
    style_dir.mkdir(parents=True, exist_ok=True)

    hino_str = f"{prefix}_{hino_id:03d}"
    output_mp3 = style_dir / f"{hino_str}.mp3"

    if not overwrite and output_mp3.exists() and output_mp3.stat().st_size > 1000:
        print(f"[{idx_global}/{total}] Pulando {midi_path.name} ({style}) (já existe {output_mp3.name})")
        return 'pulado', None

    print(f"\n[{idx_global}/{total}] Processando {midi_path.name} "
          f"para {style.upper()}...")
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
        if style == "orquestra01":
            ok = gerar_hino_orquestra01(
                str(midi_path), str(output_mp3),
                bpm_target=bpm_target, speed=speed_param,
                overwrite=overwrite
            )
        else:
            ok = gerar_hino_orquestra02(
                str(midi_path), str(output_mp3),
                bpm_target=bpm_target, speed=speed_param,
                overwrite=overwrite
            )

        t_elap = time.time() - t0
        if ok:
            print(f"  [OK] Concluído em {t_elap:.1f}s")
            return 'sucesso', None
        else:
            print(f"  [ERRO] Falha ao renderizar {hino_str} ({style})")
            return 'falha', f"{midi_path.name} ({style})"
    except Exception as e:
        t_elap = time.time() - t0
        print(f"  [EXCEÇÃO] Erro crítico no {prefix} {hino_id} ({style}): {e}")
        return 'falha', f"{midi_path.name} ({style})"


def processar_lote(start_id: int = None, end_id: int = None,
                   style_target: str = "all", speed_factor: float = 1.0,
                   overwrite: bool = False, skip_coros: bool = False):
    midi_dir = ROOT / 'mid'
    output_dir = ROOT / 'output' / 'orquestra_nicho'
    output_dir.mkdir(parents=True, exist_ok=True)

    if not midi_dir.exists():
        print(f"ERRO: Pasta de entrada MIDI não encontrada em: {midi_dir}")
        return

    target_styles = STYLES if style_target == "all" else [style_target]

    midi_files = sorted(list(midi_dir.glob("*.mid")))
    hinos_to_process = []
    coros_to_process = []

    for f in midi_files:
        prefix, hino_id = extrair_prefixo_e_id(f)
        if hino_id == -1:
            continue

        if prefix == 'coro':
            coros_to_process.append((prefix, hino_id, f))
        else:
            if start_id is not None and hino_id < start_id:
                continue
            if end_id is not None and hino_id > end_id:
                continue
            hinos_to_process.append((prefix, hino_id, f))

    to_process = list(hinos_to_process)
    if not skip_coros:
        to_process.extend(coros_to_process)
    elif coros_to_process:
        print(f"\n  ⏭ Pulando {len(coros_to_process)} coro(s) (--skip-coros)")

    if not to_process:
        print("Nenhum arquivo selecionado para processamento.")
        return

    # Total de tarefas = (hinos + coros) * num_estilos
    total_tarefas = len(to_process) * len(target_styles)

    print("=" * 70)
    print("  🎼 PROCESSAMENTO EM LOTE — ORQUESTRA MIX (01 & 02)")
    print(f"  Hinos selecionados: {len(hinos_to_process)}")
    print(f"  Coros selecionados: {len(coros_to_process) if not skip_coros else 0}")
    print(f"  Estilos: {', '.join(s.upper() for s in target_styles)}")
    print(f"  Total de tarefas: {total_tarefas}")
    print(f"  Fator de Velocidade: {speed_factor:.2f}x")
    print(f"  Sobrescrever: {'Sim' if overwrite else 'Não'}")
    print("=" * 70)

    sucessos = 0
    pulados = 0
    falhas = 0
    erros_lista = []

    idx_global = 0
    t_inicio = time.time()

    for style in target_styles:
        for prefix, hino_id, midi_path in to_process:
            idx_global += 1
            status, erro_info = _processar_item(
                prefix, hino_id, midi_path, style, output_dir,
                speed_factor, overwrite, idx_global, total_tarefas
            )
            if status == 'sucesso':
                sucessos += 1
            elif status == 'pulado':
                pulados += 1
            else:
                falhas += 1
                if erro_info:
                    erros_lista.append(erro_info)

    t_total = time.time() - t_inicio

    print("\n" + "=" * 70)
    print("  RESUMO DA EXECUÇÃO")
    print(f"  Tempo total: {t_total/60:.1f} minutos")
    print(f"  Sucessos: {sucessos}")
    print(f"  Pulados:  {pulados}")
    print(f"  Falhas:   {falhas}")
    if erros_lista:
        print("\n  Itens com falha:")
        for err in erros_lista:
            print(f"    - {err}")
    print("=" * 70)

    # Impressão do Relatório de Completude
    res = verificar_completude(output_dir, target_styles)
    imprimir_relatorio_completude(res, target_styles)


def main():
    parser = argparse.ArgumentParser(
        description="Processa hinos e coros em lote para Orquestra 01 e Orquestra 02."
    )
    parser.add_argument('--start', type=int, default=None,
                        help="ID inicial do hino (1-480)")
    parser.add_argument('--end', type=int, default=None,
                        help="ID final do hino (1-480)")
    parser.add_argument('--style', type=str, default="all",
                        choices=["orquestra01", "orquestra02", "all"],
                        help="Estilo alvo (orquestra01, orquestra02 ou all)")
    parser.add_argument('--speed-factor', type=float, default=1.0,
                        help="Fator multiplicador de velocidade (padrão: 1.0)")
    parser.add_argument('--overwrite', action='store_true',
                        help="Força re-geração mesmo se o MP3 já existir")
    parser.add_argument('--skip-coros', action='store_true',
                        help="Pula a geração dos 6 coros")

    args = parser.parse_args()
    processar_lote(
        start_id=args.start,
        end_id=args.end,
        style_target=args.style,
        speed_factor=args.speed_factor,
        overwrite=args.overwrite,
        skip_coros=args.skip_coros
    )


if __name__ == '__main__':
    main()
