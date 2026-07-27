#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
utils/verificar_completude_nicho.py
====================================
Script de auditoria e retry para garantir que todos os 480 hinos + 6 coros
estejam gerados em cada um dos 4 nichos (strings, brass, paletas, sopros).

Uso:
  python utils/verificar_completude_nicho.py                 # só verifica
  python utils/verificar_completude_nicho.py --regerar       # verifica e regera faltantes
  python utils/verificar_completude_nicho.py --regerar --max-retries 3

Exit codes:
  0 = tudo completo
  1 = há faltantes (após tentativas de retry, se aplicável)
"""

import sys
import re
import argparse
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT / 'utils'))

TOTAL_HINOS = 480
TOTAL_COROS = 6
GROUPS = ["strings", "brass", "paletas", "sopros"]


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


def imprimir_relatorio(resultado: dict) -> int:
    """Imprime relatório detalhado e retorna total de faltantes."""
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


def encontrar_midi(midi_dir: Path, prefix: str, hino_id: int) -> Path | None:
    """Encontra o arquivo MIDI correspondente a um hino ou coro."""
    for f in midi_dir.glob("*.mid"):
        name_lower = f.name.lower()
        is_coro = 'coro' in name_lower
        detected_prefix = 'coro' if is_coro else 'hino'
        if detected_prefix != prefix:
            continue
        match = re.search(r'(\d+)', f.name)
        if match and int(match.group(1)) == hino_id:
            return f
    return None


def regerar_faltantes(resultado: dict, output_dir: Path,
                      speed_factor: float = 1.0) -> int:
    """Tenta regerar os itens faltantes. Retorna o total que ainda falta."""
    from gerar_hino_nicho_completo import gerar_hino_nicho_completo
    from velocidade_hinos import HINOS

    midi_dir = ROOT / 'mid'
    if not midi_dir.exists():
        print(f"ERRO: Pasta MIDI não encontrada: {midi_dir}")
        return -1

    # Coletar todos os itens faltantes: (prefix, id, group)
    itens_faltantes = []
    for group in GROUPS:
        info = resultado[group]
        for hino_id in info["hinos_faltantes"]:
            itens_faltantes.append(("hino", hino_id, group))
        for coro_id in info["coros_faltantes"]:
            itens_faltantes.append(("coro", coro_id, group))

    if not itens_faltantes:
        return 0

    total = len(itens_faltantes)
    print(f"\n🔄 Tentando regerar {total} item(ns) faltante(s)...")
    print(f"{'='*60}")

    sucessos = 0
    falhas = 0
    t0 = time.time()

    for idx, (prefix, item_id, group) in enumerate(itens_faltantes, 1):
        midi_path = encontrar_midi(midi_dir, prefix, item_id)
        if midi_path is None:
            print(f"\n  [{idx}/{total}] ❌ MIDI não encontrado para "
                  f"{prefix}_{item_id:03d}")
            falhas += 1
            continue

        group_dir = output_dir / group
        group_dir.mkdir(parents=True, exist_ok=True)
        item_str = f"{prefix}_{item_id:03d}"
        output_mp3 = group_dir / f"{item_str}.mp3"

        print(f"\n  [{idx}/{total}] Regerando {item_str} ({group.upper()})...")

        bpm_target = None
        speed_param = None
        if prefix == 'hino' and item_id in HINOS:
            bpm_base = HINOS[item_id][0]
            bpm_target = bpm_base * speed_factor
        else:
            speed_param = speed_factor

        try:
            ok = gerar_hino_nicho_completo(
                str(midi_path), str(output_mp3),
                group=group, bpm_target=bpm_target, speed=speed_param
            )
            if ok:
                print(f"  ✅ {item_str} ({group}) regerado com sucesso!")
                sucessos += 1
            else:
                print(f"  ❌ Falha ao regerar {item_str} ({group})")
                falhas += 1
        except Exception as e:
            print(f"  ❌ Exceção ao regerar {item_str} ({group}): {e}")
            falhas += 1

    t_total = time.time() - t0
    print(f"\n{'='*60}")
    print(f"  Retry concluído em {t_total/60:.1f} minutos")
    print(f"  Sucessos: {sucessos}/{total}")
    print(f"  Falhas:   {falhas}/{total}")
    print(f"{'='*60}")

    return falhas


def main():
    parser = argparse.ArgumentParser(
        description="Verificar e opcionalmente regerar hinos/coros faltantes "
                    "nos nichos (strings, brass, paletas, sopros)."
    )
    parser.add_argument("--regerar", action="store_true",
                        help="Tentar regerar automaticamente os itens faltantes")
    parser.add_argument("--max-retries", type=int, default=2,
                        help="Número máximo de tentativas de retry (padrão: 2)")
    parser.add_argument("--speed-factor", type=float, default=1.0,
                        help="Fator de velocidade para a geração")
    args = parser.parse_args()

    output_dir = ROOT / 'output' / 'orquestra_nicho'

    if not output_dir.exists():
        print(f"ERRO: Pasta de saída não encontrada: {output_dir}")
        print("Execute primeiro o gerar_lote_nicho.py para criar a estrutura.")
        sys.exit(1)

    # ── Verificação inicial ─────────────────────────────────────────────
    resultado = verificar_completude(output_dir)
    total_faltantes = imprimir_relatorio(resultado)

    if total_faltantes == 0:
        print("\n✅ Todos os hinos e coros estão completos em todos os nichos!")
        sys.exit(0)

    if not args.regerar:
        print(f"\n💡 Use --regerar para tentar gerar os {total_faltantes} "
              "item(ns) faltante(s) automaticamente.")
        sys.exit(1)

    # ── Retry loop ──────────────────────────────────────────────────────
    for tentativa in range(1, args.max_retries + 1):
        print(f"\n{'#'*60}")
        print(f"  TENTATIVA DE RETRY {tentativa}/{args.max_retries}")
        print(f"{'#'*60}")

        falhas_restantes = regerar_faltantes(
            resultado, output_dir, args.speed_factor
        )

        # Re-verificar
        resultado = verificar_completude(output_dir)
        total_faltantes = imprimir_relatorio(resultado)

        if total_faltantes == 0:
            print(f"\n✅ Tudo completo após tentativa {tentativa}!")
            sys.exit(0)

        if tentativa < args.max_retries:
            print(f"\n⏳ Ainda restam {total_faltantes} faltante(s). "
                  "Tentando novamente...")

    print(f"\n⚠️  Após {args.max_retries} tentativa(s), ainda restam "
          f"{total_faltantes} item(ns) faltante(s).")
    sys.exit(1)


if __name__ == "__main__":
    main()
