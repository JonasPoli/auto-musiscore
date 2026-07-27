#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/testar_orquestra02_mix.py
==================================
Gera 16 amostras de orquestras mistas COM coral (4 vozes a 50% volume)
usando a primeira frase do Hino 003 como referência.

Cada combinação original de 16 instrumentos recebe +4 vozes corais = 20 tracks.
Vozes corais: Soprano (voice.soprano), Contralto (voice.alto),
              Tenor (voice.tenor), Baixo (voice.bass, oitava -1)

Saída: output/testes_orquestra02_mix/<nome>.mp3
"""

import sys
import os
import copy
from pathlib import Path

ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT / 'utils'))
sys.path.insert(0, str(ROOT / 'scripts'))

from testar_orquestra_mix import COMBINATIONS_ORQUESTRA, gerar_amostra

# ═══════════════════════════════════════════════════════════════════════════════
# TRACKS DE CORAL (4 vozes, volume ~50%, pan centralizado)
# Baseado nos timbres do MuseSounds Muse Choir:
#   voice.soprano  → uid=19, setup=voices.choir.soprano,  program=52 (GM Choir Aahs)
#   voice.alto     → uid=20, setup=voices.choir.alto,     program=52
#   voice.tenor    → uid=21, setup=voices.choir.tenor,     program=52
#   voice.bass     → uid=22, setup=voices.choir.bass,      program=52
# ═══════════════════════════════════════════════════════════════════════════════

CORAL_TRACKS = [
    {"voice": "Soprano",   "instrument_name": "Coral Soprano",   "instrument_id": "voice.soprano", "system_name": "Sopranos",  "program": 52, "vol": 42, "pan": 48, "octave": 0},
    {"voice": "Contralto", "instrument_name": "Coral Contralto",  "instrument_id": "voice.alto",    "system_name": "Altos",     "program": 52, "vol": 42, "pan": 56, "octave": 0},
    {"voice": "Tenor",     "instrument_name": "Coral Tenor",      "instrument_id": "voice.tenor",   "system_name": "Tenors",    "program": 52, "vol": 42, "pan": 72, "octave": 0},
    {"voice": "Baixo",     "instrument_name": "Coral Baixo",      "instrument_id": "voice.bass",    "system_name": "Basses",    "program": 52, "vol": 42, "pan": 80, "octave": -1},
]

ORGAN_TRACK = [
    {
        "voice": ["Soprano", "Contralto", "Tenor", "Baixo"],
        "instrument_name": "Rock Organ",
        "instrument_id": "keyboard.organ.rock",
        "system_name": "Rock Organ",
        "program": 18,
        "vol": 12,   # Volume suave de fundo (12)
        "pan": 64,   # Centralizado
        "octave": 0
    }
]


def build_orquestra02_combinations():
    """Cria COMBINATIONS_ORQUESTRA_02 adicionando 4 vozes corais + 1 Rock Organ a cada combo."""
    combos = []
    for orig in COMBINATIONS_ORQUESTRA:
        combo = copy.deepcopy(orig)
        # Atualizar ID e nome
        combo["id"] = combo["id"].replace("_-_", "_02_-_", 1)
        if not combo["id"].startswith(combo["id"][:3] + "_02"):
            # Garantir que o prefixo numérico fica intacto
            parts = combo["id"].split("_-_", 1)
            combo["id"] = parts[0] + "_02_-_" + parts[1] if len(parts) > 1 else combo["id"] + "_02"
        combo["name"] = combo["name"] + " + Coral + Rock Organ"
        combo["tracks"] = combo["tracks"] + copy.deepcopy(CORAL_TRACKS) + copy.deepcopy(ORGAN_TRACK)
        combo["size"] = len(combo["tracks"])  # 16 + 4 + 1 = 21
        combos.append(combo)
    return combos


COMBINATIONS_ORQUESTRA_02 = build_orquestra02_combinations()


def main():
    import time

    midi_path = ROOT / 'mid' / '003- Faz-nos ouvir Tua voz.mid'
    if not midi_path.exists():
        print(f"ERRO: MIDI não encontrado: {midi_path}")
        sys.exit(1)

    output_dir = ROOT / 'output' / 'testes_orquestra02_mix'
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("  🎼 TESTE DE COMBINAÇÕES ORQUESTRA 02 (COM CORAL)")
    print(f"  MIDI: {midi_path.name}")
    print(f"  Saída: {output_dir}")
    print(f"  Total: {len(COMBINATIONS_ORQUESTRA_02)} combinações (20 tracks cada)")
    print("=" * 70)

    sucessos = 0
    falhas = 0
    t0 = time.time()

    for idx, config in enumerate(COMBINATIONS_ORQUESTRA_02, 1):
        name = config["name"]
        safe_name = config["id"]
        output_mp3 = output_dir / f"{safe_name}.mp3"

        if output_mp3.exists():
            print(f"\n[{idx}/{len(COMBINATIONS_ORQUESTRA_02)}] Pulando: {name} (já existe)")
            sucessos += 1
            continue

        print(f"\n[{idx}/{len(COMBINATIONS_ORQUESTRA_02)}] Gerando: {name}")
        print(f"  ({config['size']} instrumentos = 16 orquestra + 4 coral)")

        ok = gerar_amostra(str(midi_path), config, str(output_mp3), bpm_target=68.0, speed=1.0)
        if ok:
            sucessos += 1
        else:
            falhas += 1

    t_total = time.time() - t0
    print(f"\n{'=' * 70}")
    print(f"  Concluído em {t_total/60:.1f} minutos")
    print(f"  Sucessos: {sucessos}/{len(COMBINATIONS_ORQUESTRA_02)}")
    print(f"  Falhas: {falhas}/{len(COMBINATIONS_ORQUESTRA_02)}")
    print(f"\n  📂 Resultados em: {output_dir}")
    print(f"  Ouça os MP3s e diga quais manter/descartar!")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
