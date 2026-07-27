#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/testar_orquestra_mix.py
================================
Gera 16 amostras de orquestras mistas (cordas + metais + palhetas + sopros)
usando a primeira frase do Coro 001 como referência.

Cada combinação tem um grupo "dominante" (volume normal) e os demais com
volume reduzido pela metade.

Saída: output/testes_orquestra_mix/<nome_da_combinacao>.mp3
"""

import sys
import os
import subprocess
import shutil
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT / 'utils'))

from gerar_bibliotecas_nicho import (
    get_tempo, extract_phrase_notes, build_combo_midi,
    MSCORE_BIN,
)
from gerar_testes_timbre import detect_phrases
from midi_humanize import (
    remove_staccato_from_mscz, set_tempo_in_mscz, set_pan_in_mscz,
    build_and_inject_audiosettings_pan, ajustar_ultimo_compasso_mscz,
)
import mido

# ═══════════════════════════════════════════════════════════════════════════════
# 16 COMBINAÇÕES DE ORQUESTRA MISTA (STRINGS + BRASS + PALETAS + SOPROS)
#
# Cada combo tem 16 tracks. Um grupo é "dominante" (volume normal),
# os demais são "acompanhamento" (volume reduzido ~50%).
#
# Instrumentos disponíveis por família (referência instrument_id):
#   STRINGS: strings.violin, strings.viola, strings.cello, strings.contrabass
#   BRASS:   brass.trumpet, brass.french-horn, brass.trombone, brass.tuba,
#            brass.flugelhorn, brass.euphonium, brass.cornet, brass.tenor-horn,
#            brass.baritone-horn
#   PALETAS: sax.soprano, sax.alto, sax.tenor, sax.baritone,
#            woodwind.reed.clarinet, woodwind.reed.oboe, woodwind.reed.bassoon,
#            woodwind.reed.english-horn
#   SOPROS:  woodwind.flutes.flute, woodwind.flutes.piccolo
# ═══════════════════════════════════════════════════════════════════════════════

COMBINATIONS_ORQUESTRA = [
    # ── 01: Dominância Cordas — Orquestra Sinfônica Clássica ──────────────────
    {
        "id": "001_-_Sinfonica_Classica_Cordas_Dom",
        "name": "Sinfônica Clássica (Cordas Dominantes)",
        "size": 16,
        "tracks": [
            # CORDAS (8) — volume normal (dominante)
            {"voice": "Soprano",   "instrument_name": "Violino I-1",   "instrument_id": "strings.violin",     "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 16, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Violino I-2",   "instrument_id": "strings.violin",     "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 28, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Violino II",    "instrument_id": "strings.violin",     "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 40, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola I",       "instrument_id": "strings.viola",      "system_name": "Viola (Solo)",    "program": 41, "vol": 80, "pan": 52, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Viola II",      "instrument_id": "strings.viola",      "system_name": "Viola (Solo)",    "program": 41, "vol": 80, "pan": 64, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello I",       "instrument_id": "strings.cello",      "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 76, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Cello II",      "instrument_id": "strings.cello",      "system_name": "Violoncello (Solo)", "program": 42, "vol": 85, "pan": 88, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo",   "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 85, "pan": 100, "octave": 0},
            # SOPROS (2) — volume reduzido
            {"voice": "Soprano",   "instrument_name": "Flauta I",      "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 30, "pan": 36, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Flauta II",     "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 30, "pan": 68, "octave": 0},
            # PALHETAS (4) — volume reduzido
            {"voice": "Contralto", "instrument_name": "Oboe",          "instrument_id": "woodwind.reed.oboe",    "system_name": "Oboe", "program": 68, "vol": 40, "pan": 48, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Clarinete",     "instrument_id": "woodwind.reed.clarinet","system_name": "Clarinet in Bb", "program": 71, "vol": 40, "pan": 80, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Corne Ingles",  "instrument_id": "woodwind.reed.english-horn", "system_name": "Horns a6", "program": 69, "vol": 40, "pan": 72, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Fagote",        "instrument_id": "woodwind.reed.bassoon", "system_name": "Bassoon", "program": 70, "vol": 42, "pan": 112, "octave": 0},
            # METAIS (2) — volume reduzido
            {"voice": "Tenor",     "instrument_name": "Trompa",        "instrument_id": "brass.french-horn",   "system_name": "Horn in F", "program": 60, "vol": 40, "pan": 92, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Trombone",      "instrument_id": "brass.trombone",      "system_name": "Trombone", "program": 57, "vol": 40, "pan": 120, "octave": 0},
        ]
    },
    # ── 02: Dominância Metais — Brass Sinfônico com Cordas e Madeiras ─────────
    {
        "id": "002_-_Brass_Sinfonico_Metais_Dom",
        "name": "Brass Sinfônico (Metais Dominantes)",
        "size": 16,
        "tracks": [
            # METAIS (8) — volume normal (dominante)
            {"voice": "Soprano",   "instrument_name": "Trompete I",    "instrument_id": "brass.trumpet",      "system_name": "Trumpet", "program": 56, "vol": 85, "pan": 20, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Trompete II",   "instrument_id": "brass.trumpet",      "system_name": "Trumpet", "program": 56, "vol": 85, "pan": 36, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Trompa I",      "instrument_id": "brass.french-horn",   "system_name": "Horn in F", "program": 60, "vol": 80, "pan": 52, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Trompa II",     "instrument_id": "brass.french-horn",   "system_name": "Horn in F", "program": 60, "vol": 80, "pan": 68, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Trombone I",    "instrument_id": "brass.trombone",      "system_name": "Trombone", "program": 57, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Euphonium",     "instrument_id": "brass.euphonium",     "system_name": "Euphonium", "program": 57, "vol": 80, "pan": 92, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Tuba I",        "instrument_id": "brass.tuba",          "system_name": "Tuba", "program": 58, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Trombone Baixo","instrument_id": "brass.trombone",      "system_name": "Trombone", "program": 57, "vol": 85, "pan": 120, "octave": 0},
            # CORDAS (4) — volume reduzido
            {"voice": "Soprano",   "instrument_name": "Violino",       "instrument_id": "strings.violin",     "system_name": "Violin 1 (Solo)", "program": 40, "vol": 42, "pan": 24, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola",         "instrument_id": "strings.viola",      "system_name": "Viola (Solo)",    "program": 41, "vol": 40, "pan": 48, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello",         "instrument_id": "strings.cello",      "system_name": "Violoncello (Solo)", "program": 42, "vol": 40, "pan": 76, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo",   "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 42, "pan": 104, "octave": 0},
            # SOPROS (2) — volume reduzido
            {"voice": "Soprano",   "instrument_name": "Flauta",        "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 30, "pan": 44, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Oboe",          "instrument_id": "woodwind.reed.oboe",    "system_name": "Oboe", "program": 68, "vol": 40, "pan": 60, "octave": 0},
            # PALHETAS (2) — volume reduzido
            {"voice": "Tenor",     "instrument_name": "Clarinete",     "instrument_id": "woodwind.reed.clarinet","system_name": "Clarinet in Bb", "program": 71, "vol": 40, "pan": 88, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Fagote",        "instrument_id": "woodwind.reed.bassoon", "system_name": "Bassoon", "program": 70, "vol": 42, "pan": 100, "octave": 0},
        ]
    },
    # ── 03: Dominância Palhetas — Ensemble de Palhetas com Acompanhamento ─────
    {
        "id": "003_-_Palhetas_Ensemble_Dom",
        "name": "Ensemble de Palhetas (Palhetas Dominantes)",
        "size": 16,
        "tracks": [
            # PALHETAS (8) — volume normal (dominante)
            {"voice": "Soprano",   "instrument_name": "Sax Soprano",   "instrument_id": "sax.soprano",        "system_name": "Soprano Sax", "program": 64, "vol": 80, "pan": 20, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Oboe I",        "instrument_id": "woodwind.reed.oboe", "system_name": "Oboe", "program": 68, "vol": 85, "pan": 36, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Sax Alto",      "instrument_id": "sax.alto",           "system_name": "Alto Sax", "program": 65, "vol": 80, "pan": 52, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Clarinete I",   "instrument_id": "woodwind.reed.clarinet","system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 68, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Sax Tenor",     "instrument_id": "sax.tenor",          "system_name": "Tenor Sax", "program": 66, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Corne Ingles",  "instrument_id": "woodwind.reed.english-horn", "system_name": "Horns a6", "program": 69, "vol": 80, "pan": 92, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Sax Baritono",  "instrument_id": "sax.baritone",       "system_name": "Baritone Sax", "program": 67, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Fagote",        "instrument_id": "woodwind.reed.bassoon","system_name": "Bassoon", "program": 70, "vol": 85, "pan": 120, "octave": 0},
            # CORDAS (4) — volume reduzido
            {"voice": "Soprano",   "instrument_name": "Violino",       "instrument_id": "strings.violin",     "system_name": "Violin 1 (Solo)", "program": 40, "vol": 42, "pan": 24, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola",         "instrument_id": "strings.viola",      "system_name": "Viola (Solo)",    "program": 41, "vol": 40, "pan": 56, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello",         "instrument_id": "strings.cello",      "system_name": "Violoncello (Solo)", "program": 42, "vol": 40, "pan": 88, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo",   "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 42, "pan": 104, "octave": 0},
            # METAIS (2) — volume reduzido
            {"voice": "Soprano",   "instrument_name": "Flugelhorn",    "instrument_id": "brass.flugelhorn",   "system_name": "Flugelhorn", "program": 56, "vol": 40, "pan": 44, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Trompa",        "instrument_id": "brass.french-horn",  "system_name": "Horn in F", "program": 60, "vol": 40, "pan": 64, "octave": 0},
            # SOPROS (2) — volume reduzido
            {"voice": "Tenor",     "instrument_name": "Flauta",        "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 30, "pan": 76, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Clarinete Baixo","instrument_id": "woodwind.reed.clarinet","system_name": "Clarinet in Bb", "program": 71, "vol": 42, "pan": 96, "octave": 0},
        ]
    },
    # ── 04: Dominância Sopros — Sopros de Madeira com Coloração Orquestral ────
    {
        "id": "004_-_Sopros_Madeira_Dom",
        "name": "Sopros de Madeira (Sopros Dominantes)",
        "size": 16,
        "tracks": [
            # SOPROS/MADEIRAS (8) — volume normal (dominante)
            {"voice": "Soprano",   "instrument_name": "Piccolo",       "instrument_id": "woodwind.flutes.piccolo","system_name": "Piccolo", "program": 72, "vol": 75, "pan": 16, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Flauta I",      "instrument_id": "woodwind.flutes.flute","system_name": "Flute", "program": 73, "vol": 85, "pan": 28, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Flauta II",     "instrument_id": "woodwind.flutes.flute","system_name": "Flute", "program": 73, "vol": 80, "pan": 44, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Oboe I",        "instrument_id": "woodwind.reed.oboe",  "system_name": "Oboe", "program": 68, "vol": 80, "pan": 52, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Oboe II",       "instrument_id": "woodwind.reed.oboe",  "system_name": "Oboe", "program": 68, "vol": 80, "pan": 68, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Clarinete I",   "instrument_id": "woodwind.reed.clarinet","system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Clarinete II",  "instrument_id": "woodwind.reed.clarinet","system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 92, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Fagote I",      "instrument_id": "woodwind.reed.bassoon","system_name": "Bassoon", "program": 70, "vol": 85, "pan": 112, "octave": 0},
            # CORDAS (4) — volume reduzido
            {"voice": "Soprano",   "instrument_name": "Violino",       "instrument_id": "strings.violin",     "system_name": "Violin 1 (Solo)", "program": 40, "vol": 42, "pan": 32, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola",         "instrument_id": "strings.viola",      "system_name": "Viola (Solo)",    "program": 41, "vol": 40, "pan": 60, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello",         "instrument_id": "strings.cello",      "system_name": "Violoncello (Solo)", "program": 42, "vol": 40, "pan": 84, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo",   "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 42, "pan": 104, "octave": 0},
            # METAIS (2) — volume reduzido
            {"voice": "Contralto", "instrument_name": "Trompa",        "instrument_id": "brass.french-horn",  "system_name": "Horn in F", "program": 60, "vol": 40, "pan": 76, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Tuba",          "instrument_id": "brass.tuba",         "system_name": "Tuba", "program": 58, "vol": 42, "pan": 120, "octave": 0},
            # PALHETAS (2) — volume reduzido
            {"voice": "Tenor",     "instrument_name": "Sax Tenor",     "instrument_id": "sax.tenor",          "system_name": "Tenor Sax", "program": 66, "vol": 40, "pan": 72, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Sax Baritono",  "instrument_id": "sax.baritone",       "system_name": "Baritone Sax", "program": 67, "vol": 40, "pan": 96, "octave": 0},
        ]
    },
    # ── 05: Cordas + Trompas — Sonoridade Romântica ───────────────────────────
    {
        "id": "005_-_Romantica_Cordas_Trompas",
        "name": "Romântica: Cordas + Trompas",
        "size": 16,
        "tracks": [
            # CORDAS (10) — dominante
            {"voice": "Soprano",   "instrument_name": "Violino I-1",   "instrument_id": "strings.violin",     "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 16, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Violino I-2",   "instrument_id": "strings.violin",     "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 24, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Violino I-3",   "instrument_id": "strings.violin",     "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 32, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Violino II-1",  "instrument_id": "strings.violin",     "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 40, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Violino II-2",  "instrument_id": "strings.violin",     "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 48, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola",         "instrument_id": "strings.viola",      "system_name": "Viola (Solo)",    "program": 41, "vol": 80, "pan": 56, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Viola II",      "instrument_id": "strings.viola",      "system_name": "Viola (Solo)",    "program": 41, "vol": 80, "pan": 64, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello I",       "instrument_id": "strings.cello",      "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 72, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Cello II",      "instrument_id": "strings.cello",      "system_name": "Violoncello (Solo)", "program": 42, "vol": 85, "pan": 80, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo",   "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 85, "pan": 88, "octave": 0},
            # METAIS/TROMPAS (3) — volume reduzido
            {"voice": "Soprano",   "instrument_name": "Trompa I",      "instrument_id": "brass.french-horn",  "system_name": "Horn in F", "program": 60, "vol": 40, "pan": 44, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Trompa II",     "instrument_id": "brass.french-horn",  "system_name": "Horn in F", "program": 60, "vol": 40, "pan": 68, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Trompa III",    "instrument_id": "brass.french-horn",  "system_name": "Horn in F", "program": 60, "vol": 40, "pan": 92, "octave": 0},
            # SOPRO (1) — volume reduzido
            {"voice": "Soprano",   "instrument_name": "Flauta",        "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 30, "pan": 36, "octave": 0},
            # PALHETAS (2) — volume reduzido
            {"voice": "Tenor",     "instrument_name": "Fagote",        "instrument_id": "woodwind.reed.bassoon","system_name": "Bassoon", "program": 70, "vol": 42, "pan": 104, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Clarinete",     "instrument_id": "woodwind.reed.clarinet","system_name": "Clarinet in Bb", "program": 71, "vol": 40, "pan": 112, "octave": 0},
        ]
    },
    # ── 06: Metais + Palhetas — Banda Sinfônica ──────────────────────────────
    {
        "id": "006_-_Banda_Sinfonica",
        "name": "Banda Sinfônica: Metais + Palhetas",
        "size": 16,
        "tracks": [
            # METAIS (5) — volume normal
            {"voice": "Soprano",   "instrument_name": "Trompete I",    "instrument_id": "brass.trumpet",      "system_name": "Trumpet", "program": 56, "vol": 85, "pan": 20, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Trompete II",   "instrument_id": "brass.trumpet",      "system_name": "Trumpet", "program": 56, "vol": 80, "pan": 36, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Trompa",        "instrument_id": "brass.french-horn",  "system_name": "Horn in F", "program": 60, "vol": 80, "pan": 52, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Trombone",      "instrument_id": "brass.trombone",     "system_name": "Trombone", "program": 57, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Tuba",          "instrument_id": "brass.tuba",         "system_name": "Tuba", "program": 58, "vol": 85, "pan": 112, "octave": 0},
            # PALHETAS (5) — volume normal
            {"voice": "Soprano",   "instrument_name": "Clarinete I",   "instrument_id": "woodwind.reed.clarinet","system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 28, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Sax Alto",      "instrument_id": "sax.alto",           "system_name": "Alto Sax", "program": 65, "vol": 80, "pan": 60, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Oboe",          "instrument_id": "woodwind.reed.oboe", "system_name": "Oboe", "program": 68, "vol": 80, "pan": 68, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Sax Tenor",     "instrument_id": "sax.tenor",          "system_name": "Tenor Sax", "program": 66, "vol": 80, "pan": 88, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Fagote",        "instrument_id": "woodwind.reed.bassoon","system_name": "Bassoon", "program": 70, "vol": 85, "pan": 120, "octave": 0},
            # CORDAS (4) — volume reduzido
            {"voice": "Soprano",   "instrument_name": "Violino",       "instrument_id": "strings.violin",     "system_name": "Violin 1 (Solo)", "program": 40, "vol": 42, "pan": 24, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola",         "instrument_id": "strings.viola",      "system_name": "Viola (Solo)",    "program": 41, "vol": 40, "pan": 56, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello",         "instrument_id": "strings.cello",      "system_name": "Violoncello (Solo)", "program": 42, "vol": 40, "pan": 84, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo",   "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 42, "pan": 104, "octave": 0},
            # SOPROS (2) — volume reduzido
            {"voice": "Soprano",   "instrument_name": "Flauta",        "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 30, "pan": 44, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Corne Ingles",  "instrument_id": "woodwind.reed.english-horn","system_name": "Horns a6", "program": 69, "vol": 40, "pan": 76, "octave": 0},
        ]
    },
    # ── 07: Cordas + Sopros — Seresta Camerística ─────────────────────────────
    {
        "id": "007_-_Seresta_Cameristica",
        "name": "Seresta Camerística: Cordas + Flautas",
        "size": 16,
        "tracks": [
            # CORDAS (7) — dominante
            {"voice": "Soprano",   "instrument_name": "Violino I",     "instrument_id": "strings.violin",     "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 16, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Violino II",    "instrument_id": "strings.violin",     "system_name": "Violin 2 (Solo)", "program": 40, "vol": 85, "pan": 28, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Violino III",   "instrument_id": "strings.violin",     "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 40, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola I",       "instrument_id": "strings.viola",      "system_name": "Viola (Solo)",    "program": 41, "vol": 80, "pan": 56, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola II",      "instrument_id": "strings.viola",      "system_name": "Viola (Solo)",    "program": 41, "vol": 80, "pan": 68, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello I",       "instrument_id": "strings.cello",      "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello II",      "instrument_id": "strings.cello",      "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 92, "octave": 0},
            # SOPROS/FLAUTAS (5) — dominante
            {"voice": "Soprano",   "instrument_name": "Piccolo",       "instrument_id": "woodwind.flutes.piccolo","system_name": "Piccolo", "program": 72, "vol": 75, "pan": 24, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Flauta I",      "instrument_id": "woodwind.flutes.flute","system_name": "Flute", "program": 73, "vol": 85, "pan": 48, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Flauta II",     "instrument_id": "woodwind.flutes.flute","system_name": "Flute", "program": 73, "vol": 80, "pan": 60, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Flauta III",    "instrument_id": "woodwind.flutes.flute","system_name": "Flute", "program": 73, "vol": 80, "pan": 72, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Flauta IV",     "instrument_id": "woodwind.flutes.flute","system_name": "Flute", "program": 73, "vol": 80, "pan": 104, "octave": 0},
            # PALHETAS (2) — volume reduzido
            {"voice": "Tenor",     "instrument_name": "Clarinete",     "instrument_id": "woodwind.reed.clarinet","system_name": "Clarinet in Bb", "program": 71, "vol": 40, "pan": 84, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Fagote",        "instrument_id": "woodwind.reed.bassoon","system_name": "Bassoon", "program": 70, "vol": 42, "pan": 112, "octave": 0},
            # METAIS (2) — volume reduzido
            {"voice": "Contralto", "instrument_name": "Trompa",        "instrument_id": "brass.french-horn",  "system_name": "Horn in F", "program": 60, "vol": 40, "pan": 64, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Cello III",     "instrument_id": "strings.cello",      "system_name": "Violoncello (Solo)", "program": 42, "vol": 42, "pan": 120, "octave": 0},
        ]
    },
    # ── 08: Equilibrada — Tutti Orquestal 4+4+4+4 ────────────────────────────
    {
        "id": "008_-_Tutti_Equilibrada",
        "name": "Tutti Orquestal Equilibrada (4+4+4+4)",
        "size": 16,
        "tracks": [
            # CORDAS (4)
            {"voice": "Soprano",   "instrument_name": "Violino",       "instrument_id": "strings.violin",     "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 16, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola",         "instrument_id": "strings.viola",      "system_name": "Viola (Solo)",    "program": 41, "vol": 80, "pan": 40, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello",         "instrument_id": "strings.cello",      "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 72, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo",   "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 85, "pan": 96, "octave": 0},
            # METAIS (4)
            {"voice": "Soprano",   "instrument_name": "Trompete",      "instrument_id": "brass.trumpet",      "system_name": "Trumpet", "program": 56, "vol": 85, "pan": 24, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Trompa",        "instrument_id": "brass.french-horn",  "system_name": "Horn in F", "program": 60, "vol": 80, "pan": 48, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Trombone",      "instrument_id": "brass.trombone",     "system_name": "Trombone", "program": 57, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Tuba",          "instrument_id": "brass.tuba",         "system_name": "Tuba", "program": 58, "vol": 85, "pan": 104, "octave": 0},
            # PALHETAS (4)
            {"voice": "Soprano",   "instrument_name": "Oboe",          "instrument_id": "woodwind.reed.oboe", "system_name": "Oboe", "program": 68, "vol": 85, "pan": 32, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Clarinete",     "instrument_id": "woodwind.reed.clarinet","system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 56, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Corne Ingles",  "instrument_id": "woodwind.reed.english-horn","system_name": "Horns a6", "program": 69, "vol": 80, "pan": 88, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Fagote",        "instrument_id": "woodwind.reed.bassoon","system_name": "Bassoon", "program": 70, "vol": 85, "pan": 112, "octave": 0},
            # SOPROS (4)
            {"voice": "Soprano",   "instrument_name": "Piccolo",       "instrument_id": "woodwind.flutes.piccolo","system_name": "Piccolo", "program": 72, "vol": 30, "pan": 36, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Flauta I",      "instrument_id": "woodwind.flutes.flute","system_name": "Flute", "program": 73, "vol": 30, "pan": 64, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Flauta II",     "instrument_id": "woodwind.flutes.flute","system_name": "Flute", "program": 73, "vol": 30, "pan": 84, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Flauta III",    "instrument_id": "woodwind.flutes.flute","system_name": "Flute", "program": 73, "vol": 30, "pan": 120, "octave": 0},
        ]
    },
    # ── 09: Cordas grandes + Sax — Jazz Sinfônico ────────────────────────────
    {
        "id": "009_-_Jazz_Sinfonico",
        "name": "Jazz Sinfônico: Cordas + Saxofones",
        "size": 16,
        "tracks": [
            # CORDAS (8) — dominante
            {"voice": "Soprano",   "instrument_name": "Violino I-1",   "instrument_id": "strings.violin",     "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 16, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Violino I-2",   "instrument_id": "strings.violin",     "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 28, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Violino II",    "instrument_id": "strings.violin",     "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 40, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola",         "instrument_id": "strings.viola",      "system_name": "Viola (Solo)",    "program": 41, "vol": 80, "pan": 56, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello I",       "instrument_id": "strings.cello",      "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 72, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello II",      "instrument_id": "strings.cello",      "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 84, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Cello III",     "instrument_id": "strings.cello",      "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 88, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo",   "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 85, "pan": 100, "octave": 0},
            # SAX/PALHETAS (6) — volume reduzido
            {"voice": "Soprano",   "instrument_name": "Sax Soprano",   "instrument_id": "sax.soprano",        "system_name": "Soprano Sax", "program": 64, "vol": 40, "pan": 24, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Sax Alto",      "instrument_id": "sax.alto",           "system_name": "Alto Sax", "program": 65, "vol": 40, "pan": 48, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Sax Tenor",     "instrument_id": "sax.tenor",          "system_name": "Tenor Sax", "program": 66, "vol": 40, "pan": 76, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Sax Baritono",  "instrument_id": "sax.baritone",       "system_name": "Baritone Sax", "program": 67, "vol": 42, "pan": 112, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Clarinete",     "instrument_id": "woodwind.reed.clarinet","system_name": "Clarinet in Bb", "program": 71, "vol": 40, "pan": 60, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Fagote",        "instrument_id": "woodwind.reed.bassoon","system_name": "Bassoon", "program": 70, "vol": 42, "pan": 96, "octave": 0},
            # SOPRO (1) — volume reduzido
            {"voice": "Soprano",   "instrument_name": "Flauta",        "instrument_id": "woodwind.flutes.flute","system_name": "Flute", "program": 73, "vol": 30, "pan": 36, "octave": 0},
            # METAL (1) — volume reduzido
            {"voice": "Baixo",     "instrument_name": "Trombone",      "instrument_id": "brass.trombone",     "system_name": "Trombone", "program": 57, "vol": 40, "pan": 120, "octave": 0},
        ]
    },
    # ── 10: Metais Mellow + Cordas — Sonho Orquestal ─────────────────────────
    {
        "id": "010_-_Sonho_Orquestal",
        "name": "Sonho Orquestal: Flugelhorns + Cordas",
        "size": 16,
        "tracks": [
            # METAIS MELLOW (6) — dominante
            {"voice": "Soprano",   "instrument_name": "Flugelhorn I",  "instrument_id": "brass.flugelhorn",   "system_name": "Flugelhorn", "program": 56, "vol": 85, "pan": 20, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Flugelhorn II", "instrument_id": "brass.flugelhorn",   "system_name": "Flugelhorn", "program": 56, "vol": 80, "pan": 36, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Trompa I",      "instrument_id": "brass.french-horn",  "system_name": "Horn in F", "program": 60, "vol": 80, "pan": 52, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Trompa II",     "instrument_id": "brass.french-horn",  "system_name": "Horn in F", "program": 60, "vol": 80, "pan": 68, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Euphonium",     "instrument_id": "brass.euphonium",    "system_name": "Euphonium", "program": 57, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Tuba",          "instrument_id": "brass.tuba",         "system_name": "Tuba", "program": 58, "vol": 85, "pan": 112, "octave": 0},
            # CORDAS (6) — dominante
            {"voice": "Soprano",   "instrument_name": "Violino I",     "instrument_id": "strings.violin",     "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 24, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Violino II",    "instrument_id": "strings.violin",     "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 32, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola I",       "instrument_id": "strings.viola",      "system_name": "Viola (Solo)",    "program": 41, "vol": 80, "pan": 48, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola II",      "instrument_id": "strings.viola",      "system_name": "Viola (Solo)",    "program": 41, "vol": 80, "pan": 60, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello",         "instrument_id": "strings.cello",      "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 72, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo",   "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 85, "pan": 96, "octave": 0},
            # SOPROS (2) — volume reduzido
            {"voice": "Soprano",   "instrument_name": "Flauta",        "instrument_id": "woodwind.flutes.flute","system_name": "Flute", "program": 73, "vol": 30, "pan": 28, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Flauta II",     "instrument_id": "woodwind.flutes.flute","system_name": "Flute", "program": 73, "vol": 30, "pan": 88, "octave": 0},
            # PALHETAS (2) — volume reduzido
            {"voice": "Tenor",     "instrument_name": "Clarinete",     "instrument_id": "woodwind.reed.clarinet","system_name": "Clarinet in Bb", "program": 71, "vol": 40, "pan": 92, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Fagote",        "instrument_id": "woodwind.reed.bassoon","system_name": "Bassoon", "program": 70, "vol": 42, "pan": 120, "octave": 0},
        ]
    },
    # ── 11: Palhetas + Flautas — Ensemble de Câmara ──────────────────────────
    {
        "id": "011_-_Camara_Palhetas_Flautas",
        "name": "Câmara: Palhetas + Flautas",
        "size": 16,
        "tracks": [
            # PALHETAS (6) — dominante
            {"voice": "Soprano",   "instrument_name": "Oboe I",        "instrument_id": "woodwind.reed.oboe", "system_name": "Oboe", "program": 68, "vol": 85, "pan": 20, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Clarinete I",   "instrument_id": "woodwind.reed.clarinet","system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 36, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Oboe II",       "instrument_id": "woodwind.reed.oboe", "system_name": "Oboe", "program": 68, "vol": 80, "pan": 52, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Clarinete II",  "instrument_id": "woodwind.reed.clarinet","system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 68, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Corne Ingles",  "instrument_id": "woodwind.reed.english-horn","system_name": "Horns a6", "program": 69, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Fagote I",      "instrument_id": "woodwind.reed.bassoon","system_name": "Bassoon", "program": 70, "vol": 85, "pan": 112, "octave": 0},
            # FLAUTAS (5) — dominante
            {"voice": "Soprano",   "instrument_name": "Piccolo",       "instrument_id": "woodwind.flutes.piccolo","system_name": "Piccolo", "program": 72, "vol": 75, "pan": 24, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Flauta I",      "instrument_id": "woodwind.flutes.flute","system_name": "Flute", "program": 73, "vol": 85, "pan": 44, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Flauta II",     "instrument_id": "woodwind.flutes.flute","system_name": "Flute", "program": 73, "vol": 80, "pan": 72, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Flauta III",    "instrument_id": "woodwind.flutes.flute","system_name": "Flute", "program": 73, "vol": 80, "pan": 88, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Fagote II",     "instrument_id": "woodwind.reed.bassoon","system_name": "Bassoon", "program": 70, "vol": 85, "pan": 120, "octave": 0},
            # CORDAS (3) — volume reduzido
            {"voice": "Soprano",   "instrument_name": "Violino",       "instrument_id": "strings.violin",     "system_name": "Violin 1 (Solo)", "program": 40, "vol": 42, "pan": 28, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola",         "instrument_id": "strings.viola",      "system_name": "Viola (Solo)",    "program": 41, "vol": 40, "pan": 60, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello",         "instrument_id": "strings.cello",      "system_name": "Violoncello (Solo)", "program": 42, "vol": 40, "pan": 84, "octave": 0},
            # METAIS (2) — volume reduzido
            {"voice": "Contralto", "instrument_name": "Trompa",        "instrument_id": "brass.french-horn",  "system_name": "Horn in F", "program": 60, "vol": 40, "pan": 64, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Trombone",      "instrument_id": "brass.trombone",     "system_name": "Trombone", "program": 57, "vol": 40, "pan": 104, "octave": 0},
        ]
    },
    # ── 12: Cordas + Clarinetes — Cinema Orquestal ───────────────────────────
    {
        "id": "012_-_Cinema_Orquestal",
        "name": "Cinema Orquestal: Cordas + Clarinetes",
        "size": 16,
        "tracks": [
            # CORDAS (7) — dominante
            {"voice": "Soprano",   "instrument_name": "Violino I-1",   "instrument_id": "strings.violin",     "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 16, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Violino I-2",   "instrument_id": "strings.violin",     "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 28, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Violino II",    "instrument_id": "strings.violin",     "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 40, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola",         "instrument_id": "strings.viola",      "system_name": "Viola (Solo)",    "program": 41, "vol": 80, "pan": 56, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello I",       "instrument_id": "strings.cello",      "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 72, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello II",      "instrument_id": "strings.cello",      "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 84, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo",   "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 85, "pan": 96, "octave": 0},
            # CLARINETES (4) — volume reduzido
            {"voice": "Soprano",   "instrument_name": "Clarinete I",   "instrument_id": "woodwind.reed.clarinet","system_name": "Clarinet in Bb", "program": 71, "vol": 40, "pan": 36, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Clarinete II",  "instrument_id": "woodwind.reed.clarinet","system_name": "Clarinet in Bb", "program": 71, "vol": 40, "pan": 52, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Clarinete III", "instrument_id": "woodwind.reed.clarinet","system_name": "Clarinet in Bb", "program": 71, "vol": 40, "pan": 76, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Clarinete Baixo","instrument_id": "woodwind.reed.clarinet","system_name": "Clarinet in Bb", "program": 71, "vol": 42, "pan": 108, "octave": 0},
            # SOPROS (2) — volume reduzido
            {"voice": "Soprano",   "instrument_name": "Flauta",        "instrument_id": "woodwind.flutes.flute","system_name": "Flute", "program": 73, "vol": 30, "pan": 24, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Oboe",          "instrument_id": "woodwind.reed.oboe", "system_name": "Oboe", "program": 68, "vol": 40, "pan": 64, "octave": 0},
            # METAIS (3) — volume reduzido
            {"voice": "Tenor",     "instrument_name": "Trompa",        "instrument_id": "brass.french-horn",  "system_name": "Horn in F", "program": 60, "vol": 40, "pan": 88, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Fagote",        "instrument_id": "woodwind.reed.bassoon","system_name": "Bassoon", "program": 70, "vol": 42, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Trombone",      "instrument_id": "brass.trombone",     "system_name": "Trombone", "program": 57, "vol": 40, "pan": 120, "octave": 0},
        ]
    },
    # ── 13: Metais Brilhantes + Sax — Big Band Sacra ─────────────────────────
    {
        "id": "013_-_Big_Band_Sacra",
        "name": "Big Band Sacra: Trompetes + Sax",
        "size": 16,
        "tracks": [
            # METAIS (5) — dominante
            {"voice": "Soprano",   "instrument_name": "Trompete I",    "instrument_id": "brass.trumpet",      "system_name": "Trumpet", "program": 56, "vol": 85, "pan": 20, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Trompete II",   "instrument_id": "brass.trumpet",      "system_name": "Trumpet", "program": 56, "vol": 85, "pan": 32, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Trompete III",  "instrument_id": "brass.trumpet",      "system_name": "Trumpet", "program": 56, "vol": 80, "pan": 44, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Trombone I",    "instrument_id": "brass.trombone",     "system_name": "Trombone", "program": 57, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Trombone II",   "instrument_id": "brass.trombone",     "system_name": "Trombone", "program": 57, "vol": 80, "pan": 92, "octave": 0},
            # SAX (5) — dominante
            {"voice": "Soprano",   "instrument_name": "Sax Soprano",   "instrument_id": "sax.soprano",        "system_name": "Soprano Sax", "program": 64, "vol": 80, "pan": 28, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Sax Alto I",    "instrument_id": "sax.alto",           "system_name": "Alto Sax", "program": 65, "vol": 80, "pan": 52, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Sax Alto II",   "instrument_id": "sax.alto",           "system_name": "Alto Sax", "program": 65, "vol": 80, "pan": 68, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Sax Tenor",     "instrument_id": "sax.tenor",          "system_name": "Tenor Sax", "program": 66, "vol": 80, "pan": 84, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Sax Baritono",  "instrument_id": "sax.baritone",       "system_name": "Baritone Sax", "program": 67, "vol": 85, "pan": 112, "octave": 0},
            # CORDAS (3) — volume reduzido
            {"voice": "Soprano",   "instrument_name": "Violino",       "instrument_id": "strings.violin",     "system_name": "Violin 1 (Solo)", "program": 40, "vol": 42, "pan": 24, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola",         "instrument_id": "strings.viola",      "system_name": "Viola (Solo)",    "program": 41, "vol": 40, "pan": 56, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello",         "instrument_id": "strings.cello",      "system_name": "Violoncello (Solo)", "program": 42, "vol": 40, "pan": 76, "octave": 0},
            # METAIS COMPLEMENTO (2) — volume reduzido
            {"voice": "Contralto", "instrument_name": "Trompa",        "instrument_id": "brass.french-horn",  "system_name": "Horn in F", "program": 60, "vol": 40, "pan": 64, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Tuba",          "instrument_id": "brass.tuba",         "system_name": "Tuba", "program": 58, "vol": 42, "pan": 120, "octave": 0},
            # SOPRO (1) — volume reduzido
            {"voice": "Baixo",     "instrument_name": "Fagote",        "instrument_id": "woodwind.reed.bassoon","system_name": "Bassoon", "program": 70, "vol": 42, "pan": 104, "octave": 0},
        ]
    },
    # ── 14: Cordas dominantes + trio de madeiras — Pastoral ──────────────────
    {
        "id": "014_-_Pastoral",
        "name": "Pastoral: Cordas + Trio de Madeiras",
        "size": 16,
        "tracks": [
            # CORDAS (10) — dominante
            {"voice": "Soprano",   "instrument_name": "Violino I-1",   "instrument_id": "strings.violin",     "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 16, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Violino I-2",   "instrument_id": "strings.violin",     "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 24, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Violino I-3",   "instrument_id": "strings.violin",     "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 32, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Violino II-1",  "instrument_id": "strings.violin",     "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 40, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Violino II-2",  "instrument_id": "strings.violin",     "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 48, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola I",       "instrument_id": "strings.viola",      "system_name": "Viola (Solo)",    "program": 41, "vol": 80, "pan": 56, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Viola II",      "instrument_id": "strings.viola",      "system_name": "Viola (Solo)",    "program": 41, "vol": 80, "pan": 64, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Viola III",     "instrument_id": "strings.viola",      "system_name": "Viola (Solo)",    "program": 41, "vol": 80, "pan": 72, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello I",       "instrument_id": "strings.cello",      "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Cello II",      "instrument_id": "strings.cello",      "system_name": "Violoncello (Solo)", "program": 42, "vol": 85, "pan": 88, "octave": 0},
            # MADEIRAS (3) — volume reduzido
            {"voice": "Soprano",   "instrument_name": "Flauta",        "instrument_id": "woodwind.flutes.flute","system_name": "Flute", "program": 73, "vol": 30, "pan": 28, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Oboe",          "instrument_id": "woodwind.reed.oboe", "system_name": "Oboe", "program": 68, "vol": 40, "pan": 52, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Clarinete",     "instrument_id": "woodwind.reed.clarinet","system_name": "Clarinet in Bb", "program": 71, "vol": 40, "pan": 76, "octave": 0},
            # METAIS (2) — volume reduzido
            {"voice": "Contralto", "instrument_name": "Trompa",        "instrument_id": "brass.french-horn",  "system_name": "Horn in F", "program": 60, "vol": 40, "pan": 68, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Fagote",        "instrument_id": "woodwind.reed.bassoon","system_name": "Bassoon", "program": 70, "vol": 42, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo",   "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 85, "pan": 120, "octave": 0},
        ]
    },
    # ── 15: Cordas + Metais + Flautas — Épica Sinfônica ──────────────────────
    {
        "id": "015_-_Epica_Sinfonica",
        "name": "Épica Sinfônica: Cordas + Metais + Flautas",
        "size": 16,
        "tracks": [
            # CORDAS (8) — dominante
            {"voice": "Soprano",   "instrument_name": "Violino I-1",   "instrument_id": "strings.violin",     "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 16, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Violino I-2",   "instrument_id": "strings.violin",     "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 28, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Violino II",    "instrument_id": "strings.violin",     "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 40, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola",         "instrument_id": "strings.viola",      "system_name": "Viola (Solo)",    "program": 41, "vol": 80, "pan": 56, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello I",       "instrument_id": "strings.cello",      "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 72, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello II",      "instrument_id": "strings.cello",      "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 84, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Cello III",     "instrument_id": "strings.cello",      "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 88, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo",   "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 85, "pan": 96, "octave": 0},
            # METAIS (4) — volume reduzido
            {"voice": "Soprano",   "instrument_name": "Trompete I",    "instrument_id": "brass.trumpet",      "system_name": "Trumpet", "program": 56, "vol": 42, "pan": 24, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Trompete II",   "instrument_id": "brass.trumpet",      "system_name": "Trumpet", "program": 56, "vol": 42, "pan": 36, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Trompa I",      "instrument_id": "brass.french-horn",  "system_name": "Horn in F", "program": 60, "vol": 40, "pan": 52, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Trompa II",     "instrument_id": "brass.french-horn",  "system_name": "Horn in F", "program": 60, "vol": 40, "pan": 68, "octave": 0},
            # FLAUTAS (3) — volume reduzido
            {"voice": "Soprano",   "instrument_name": "Flauta I",      "instrument_id": "woodwind.flutes.flute","system_name": "Flute", "program": 73, "vol": 30, "pan": 32, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Flauta II",     "instrument_id": "woodwind.flutes.flute","system_name": "Flute", "program": 73, "vol": 30, "pan": 64, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Clarinete",     "instrument_id": "woodwind.reed.clarinet","system_name": "Clarinet in Bb", "program": 71, "vol": 40, "pan": 80, "octave": 0},
            # BAIXO COMPLEMENTO (1) — volume reduzido
            {"voice": "Baixo",     "instrument_name": "Tuba",          "instrument_id": "brass.tuba",         "system_name": "Tuba", "program": 58, "vol": 42, "pan": 120, "octave": 0},
        ]
    },
    # ── 16: Cordas + Oboés/Fagotes — Barroco Moderno ─────────────────────────
    {
        "id": "016_-_Barroco_Moderno",
        "name": "Barroco Moderno: Cordas + Oboés + Fagotes",
        "size": 16,
        "tracks": [
            # CORDAS (6) — dominante
            {"voice": "Soprano",   "instrument_name": "Violino I-1",   "instrument_id": "strings.violin",     "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 16, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Violino I-2",   "instrument_id": "strings.violin",     "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 28, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Violino I-3",   "instrument_id": "strings.violin",     "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 40, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola",         "instrument_id": "strings.viola",      "system_name": "Viola (Solo)",    "program": 41, "vol": 80, "pan": 56, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello I",       "instrument_id": "strings.cello",      "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 72, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello II",      "instrument_id": "strings.cello",      "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 88, "octave": 0},
            # PALHETAS (6) — dominante
            {"voice": "Soprano",   "instrument_name": "Oboe I",        "instrument_id": "woodwind.reed.oboe", "system_name": "Oboe", "program": 68, "vol": 85, "pan": 24, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Oboe II",       "instrument_id": "woodwind.reed.oboe", "system_name": "Oboe", "program": 68, "vol": 80, "pan": 48, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Clarinete I",   "instrument_id": "woodwind.reed.clarinet","system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 60, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Clarinete II",  "instrument_id": "woodwind.reed.clarinet","system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 68, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Fagote I",      "instrument_id": "woodwind.reed.bassoon","system_name": "Bassoon", "program": 70, "vol": 85, "pan": 80, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Fagote II",     "instrument_id": "woodwind.reed.bassoon","system_name": "Bassoon", "program": 70, "vol": 85, "pan": 112, "octave": 0},
            # METAIS (2) — volume reduzido
            {"voice": "Tenor",     "instrument_name": "Trompa",        "instrument_id": "brass.french-horn",  "system_name": "Horn in F", "program": 60, "vol": 40, "pan": 84, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Trombone",      "instrument_id": "brass.trombone",     "system_name": "Trombone", "program": 57, "vol": 40, "pan": 120, "octave": 0},
            # SOPROS (2) — volume reduzido
            {"voice": "Soprano",   "instrument_name": "Flauta",        "instrument_id": "woodwind.flutes.flute","system_name": "Flute", "program": 73, "vol": 30, "pan": 36, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo",   "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 42, "pan": 104, "octave": 0},
        ]
    },
]

# Remover combinações descartadas pelo usuário (003, 005, 007)
COMBINATIONS_ORQUESTRA = [
    c for c in COMBINATIONS_ORQUESTRA
    if not any(c["id"].startswith(d) for d in ("003_", "005_", "007_"))
]


# ═══════════════════════════════════════════════════════════════════════════════
# GERADOR DE AMOSTRAS DE TESTE
# ═══════════════════════════════════════════════════════════════════════════════

MELODIC_CHANNELS = [ch for ch in range(16) if ch != 9]

def gerar_amostra(midi_path, config, output_mp3, bpm_target=60.0, speed=1.0):
    """Gera uma amostra MP3 usando a primeira frase do MIDI com a configuração dada."""
    mid = mido.MidiFile(midi_path)
    tempo = get_tempo(mid)
    bpm_orig = 60_000_000 / tempo
    tpb = mid.ticks_per_beat

    if speed is None:
        speed = bpm_target / bpm_orig
    tempo_new = int(60_000_000 / bpm_target)

    # Detectar frases e pegar a primeira
    phrases = detect_phrases(mid, tempo, min_phrase_seconds=4.0, silence_beats=0.4)
    if not phrases:
        print(f"  ERRO: nenhuma frase detectada em {midi_path}")
        return False

    ph_start, ph_end = phrases[0]
    voice_notes = extract_phrase_notes(mid, ph_start, ph_end)
    if not voice_notes:
        print(f"  ERRO: nenhuma nota encontrada na frase")
        return False

    new_mid, ch_pan_map = build_combo_midi(mid, voice_notes, config, speed=speed, phrase_start=ph_start)

    work_dir = Path(f'/tmp/_tmp_orq_test_{os.getpid()}')
    shutil.rmtree(work_dir, ignore_errors=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    midi_tmp = work_dir / 'input.mid'
    mscz_tmp = work_dir / 'score.mscz'
    mp3_raw = work_dir / 'raw.mp3'

    new_mid.save(str(midi_tmp))
    subprocess.run([MSCORE_BIN, '-o', str(mscz_tmp), str(midi_tmp)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not mscz_tmp.exists():
        shutil.rmtree(work_dir, ignore_errors=True)
        print(f"  ERRO: falha ao criar MSCZ")
        return False

    n_stacc = remove_staccato_from_mscz(mscz_tmp)
    set_tempo_in_mscz(mscz_tmp, bpm_target)
    set_pan_in_mscz(mscz_tmp, ch_pan_map)
    n_pan = build_and_inject_audiosettings_pan(mscz_tmp, ch_pan_map)
    ajustar_ultimo_compasso_mscz(mscz_tmp)

    midi_tmp.unlink(missing_ok=True)

    # Renderizar com retry
    MAX_RETRIES = 3
    for attempt in range(1, MAX_RETRIES + 1):
        r = subprocess.run([MSCORE_BIN, '-o', str(mp3_raw), str(mscz_tmp)],
                           capture_output=True, text=True)
        if mp3_raw.exists():
            break
        if attempt < MAX_RETRIES:
            print(f"    RETRY {attempt}/{MAX_RETRIES} (rc={r.returncode})")
            time.sleep(2)

    mscz_tmp.unlink(missing_ok=True)

    if not mp3_raw.exists():
        shutil.rmtree(work_dir, ignore_errors=True)
        print(f"  ERRO MP3 (rc={r.returncode})")
        return False

    # Normalizar e salvar
    out_path = Path(output_mp3)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = ['ffmpeg', '-y', '-i', str(mp3_raw),
           '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11',
           '-c:a', 'libmp3lame', '-q:a', '2', str(out_path)]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    shutil.rmtree(work_dir, ignore_errors=True)

    if out_path.exists():
        print(f"  ✅ {out_path.name} ({out_path.stat().st_size//1024} KB)")
        return True
    else:
        print(f"  ❌ Falha na normalização")
        return False


def main():
    midi_path = ROOT / 'mid' / 'Coro 001- Aleluia! Aleluia.mid'
    if not midi_path.exists():
        print(f"ERRO: MIDI não encontrado: {midi_path}")
        sys.exit(1)

    output_dir = ROOT / 'output' / 'testes_orquestra_mix'
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("  🎼 TESTE DE COMBINAÇÕES DE ORQUESTRA MISTA")
    print(f"  MIDI: {midi_path.name}")
    print(f"  Saída: {output_dir}")
    print(f"  Total: {len(COMBINATIONS_ORQUESTRA)} combinações")
    print("=" * 70)

    sucessos = 0
    falhas = 0
    t0 = time.time()

    for idx, config in enumerate(COMBINATIONS_ORQUESTRA, 1):
        name = config["name"]
        safe_name = config["id"]
        output_mp3 = output_dir / f"{safe_name}.mp3"

        if output_mp3.exists():
            print(f"\n[{idx}/{len(COMBINATIONS_ORQUESTRA)}] Pulando: {name} (já existe)")
            sucessos += 1
            continue

        print(f"\n[{idx}/{len(COMBINATIONS_ORQUESTRA)}] Gerando: {name}")
        print(f"  ({config['size']} instrumentos)")

        ok = gerar_amostra(str(midi_path), config, str(output_mp3), bpm_target=60.0, speed=1.0)
        if ok:
            sucessos += 1
        else:
            falhas += 1

    t_total = time.time() - t0
    print(f"\n{'=' * 70}")
    print(f"  Concluído em {t_total/60:.1f} minutos")
    print(f"  Sucessos: {sucessos}/{len(COMBINATIONS_ORQUESTRA)}")
    print(f"  Falhas: {falhas}/{len(COMBINATIONS_ORQUESTRA)}")
    print(f"\n  📂 Resultados em: {output_dir}")
    print(f"  Ouça os MP3s e diga quais manter/descartar!")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
