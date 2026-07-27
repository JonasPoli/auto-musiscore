#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
utils/gerar_bibliotecas_nicho.py
==================================
Gera as bibliotecas de timbres para orquestras de nicho: Strings, Brass, Paletas e Sopros.
Suporta geração individual ou completa via argumento `--group`.
Caminho de saída: output/biblioteca-de-tombres-2/<Categoria>/
"""

import os
import sys
import mido
import shutil
import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT / 'utils'))

from midi_humanize import (remove_staccato, remove_staccato_from_mscz,
                            set_pan_in_mscz, set_tempo_in_mscz,
                            build_and_inject_audiosettings_pan)

MSCORE_BIN = "/Applications/MuseScore 4.app/Contents/MacOS/mscore"
MELODIC_CHANNELS = [ch for ch in range(16) if ch != 9]

PAN_LEFT   = 16
PAN_CENTER = 64
PAN_RIGHT  = 112

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÕES DECLARATIVAS DAS COMBINAÇÕES POR FAMÍLIA DE INSTRUMENTO
# ─────────────────────────────────────────────────────────────────────────────

COMBINATIONS_STRINGS = [
    # ─── 4 INSTRUMENTOS (QUARTETOS) ──────────────────────────────────────────
    {
        "id": "001_-_Quarteto_Classico_Solista",
        "name": "Quarteto Clássico Solista",
        "size": 4,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Violino", "instrument_id": "strings.violin", "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 32, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Violino 2", "instrument_id": "strings.violin", "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 48, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Viola", "instrument_id": "strings.viola", "system_name": "Viola (Solo)", "program": 41, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Cello", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 85, "pan": 96, "octave": 0}
        ]
    },
    {
        "id": "002_-_Quarteto_de_Camara_com_Contrabaixo",
        "name": "Quarteto de Câmara com Contrabaixo",
        "size": 4,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Violino", "instrument_id": "strings.violin", "system_name": "Violin 1 (Solo)", "program": 40, "vol": 90, "pan": 16, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola", "instrument_id": "strings.viola", "system_name": "Viola (Solo)", "program": 41, "vol": 85, "pan": 48, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 85, "pan": 80, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo", "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 90, "pan": 112, "octave": 0}
        ]
    },
    {
        "id": "003_-_Quarteto_de_Cello",
        "name": "Quarteto de Violoncelos (Cello Quartet)",
        "size": 4,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Cello", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 85, "pan": 32, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Cello 2", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 48, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello 3", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Cello 4", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 85, "pan": 96, "octave": 0}
        ]
    },
    {
        "id": "004_-_Quarteto_Classico_Oitavado",
        "name": "Quarteto Clássico Oitavado (Soprano 8ve)",
        "size": 4,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Violino (8ve)", "instrument_id": "strings.violin", "system_name": "Violin 1 (Solo)", "program": 40, "vol": 75, "pan": 32, "octave": 12},
            {"voice": "Contralto", "instrument_name": "Violino 2", "instrument_id": "strings.violin", "system_name": "Violin 2 (Solo)", "program": 40, "vol": 85, "pan": 48, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Viola", "instrument_id": "strings.viola", "system_name": "Viola (Solo)", "program": 41, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Cello", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 85, "pan": 96, "octave": 0}
        ]
    },
    # ─── 8 INSTRUMENTOS (OCTETOS) ────────────────────────────────────────────
    {
        "id": "005_-_Octeto_Sinfonico_Classico",
        "name": "Octeto Sinfônico Clássico",
        "size": 8,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Violino I", "instrument_id": "strings.violin", "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 30, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Violino II", "instrument_id": "strings.violin", "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 42, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Violino 2", "instrument_id": "strings.violin", "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 54, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola I", "instrument_id": "strings.viola", "system_name": "Viola (Solo)", "program": 41, "vol": 80, "pan": 66, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello I", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 78, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Viola II", "instrument_id": "strings.viola", "system_name": "Viola (Solo)", "program": 41, "vol": 75, "pan": 90, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo", "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Cello II", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 98, "octave": 0}
        ]
    },
    {
        "id": "006_-_Octeto_Solista_Oitavado",
        "name": "Octeto Solista Oitavado (Soprano 2 8ve)",
        "size": 8,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Violino I", "instrument_id": "strings.violin", "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 30, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Violino I (8ve)", "instrument_id": "strings.violin", "system_name": "Violin 1 (Solo)", "program": 40, "vol": 70, "pan": 42, "octave": 12},
            {"voice": "Contralto", "instrument_name": "Violino 2", "instrument_id": "strings.violin", "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 54, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola I", "instrument_id": "strings.viola", "system_name": "Viola (Solo)", "program": 41, "vol": 80, "pan": 66, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello I", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 78, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Viola II", "instrument_id": "strings.viola", "system_name": "Viola (Solo)", "program": 41, "vol": 75, "pan": 90, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo", "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Cello II", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 98, "octave": 0}
        ]
    },
    {
        "id": "007_-_Octeto_com_Baixo_Pizzicato",
        "name": "Octeto com Baixo Staccato/Pizzicato",
        "size": 8,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Violino I", "instrument_id": "strings.violin", "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 30, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Violino II", "instrument_id": "strings.violin", "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 42, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Violino 2", "instrument_id": "strings.violin", "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 54, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola I", "instrument_id": "strings.viola", "system_name": "Viola (Solo)", "program": 41, "vol": 80, "pan": 66, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello I", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 78, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Viola II", "instrument_id": "strings.viola", "system_name": "Viola (Solo)", "program": 41, "vol": 75, "pan": 90, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Baixo Pizzicato", "instrument_id": "strings.contrabass", "system_name": "Pizzicato Strings", "program": 45, "vol": 95, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Cello II (Pizzicato)", "instrument_id": "strings.cello", "system_name": "Pizzicato Strings", "program": 45, "vol": 90, "pan": 98, "octave": 0}
        ]
    },
    {
        "id": "008_-_Octeto_Grave_Double_Cello",
        "name": "Octeto Grave (Double Cello + Double Contrabaixo)",
        "size": 8,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Violino I", "instrument_id": "strings.violin", "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 32, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Viola I", "instrument_id": "strings.viola", "system_name": "Viola (Solo)", "program": 41, "vol": 80, "pan": 48, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola II", "instrument_id": "strings.viola", "system_name": "Viola (Solo)", "program": 41, "vol": 80, "pan": 64, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Cello I", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello II", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 72, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello III", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 75, "pan": 88, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo I", "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo II", "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 85, "pan": 120, "octave": 0}
        ]
    },
    # ─── 12 INSTRUMENTOS ─────────────────────────────────────────────────────
    {
        "id": "009_-_Orquestra_12Part_Classica",
        "name": "Orquestra de 12 Cordas Clássica",
        "size": 12,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Violino I-1", "instrument_id": "strings.violin", "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 16, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Violino I-2", "instrument_id": "strings.violin", "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 28, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Violino I-3", "instrument_id": "strings.violin", "system_name": "Violin 1 (Solo)", "program": 40, "vol": 80, "pan": 40, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Violino II-1", "instrument_id": "strings.violin", "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 52, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Violino II-2", "instrument_id": "strings.violin", "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 64, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola I", "instrument_id": "strings.viola", "system_name": "Viola (Solo)", "program": 41, "vol": 80, "pan": 76, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello I-1", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 88, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello I-2", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 100, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Viola II", "instrument_id": "strings.viola", "system_name": "Viola (Solo)", "program": 41, "vol": 75, "pan": 64, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo I", "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo II", "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 85, "pan": 120, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Cello II", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 52, "octave": 0}
        ]
    },
    {
        "id": "010_-_Orquestra_12Part_Soprano_Oitavado",
        "name": "Orquestra de 12 Cordas com Soprano Oitavado (Soprano 3 8ve)",
        "size": 12,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Violino I-1", "instrument_id": "strings.violin", "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 16, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Violino I-2", "instrument_id": "strings.violin", "system_name": "Violin 1 (Solo)", "program": 40, "vol": 80, "pan": 28, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Violino I-3 (8ve)", "instrument_id": "strings.violin", "system_name": "Violin 1 (Solo)", "program": 40, "vol": 70, "pan": 40, "octave": 12},
            {"voice": "Contralto", "instrument_name": "Violino II-1", "instrument_id": "strings.violin", "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 52, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Violino II-2", "instrument_id": "strings.violin", "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 64, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola I", "instrument_id": "strings.viola", "system_name": "Viola (Solo)", "program": 41, "vol": 80, "pan": 76, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello I-1", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 88, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello I-2", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 100, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Viola II", "instrument_id": "strings.viola", "system_name": "Viola (Solo)", "program": 41, "vol": 75, "pan": 64, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo I", "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo II", "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 85, "pan": 120, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Cello II", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 52, "octave": 0}
        ]
    },
    {
        "id": "011_-_Orquestra_12Part_Viola_Oitavada",
        "name": "Orquestra de 12 Cordas com Violas Oitavadas (Viola 8ve)",
        "size": 12,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Violino I-1", "instrument_id": "strings.violin", "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 16, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Violino I-2", "instrument_id": "strings.violin", "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 28, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Violino I-3", "instrument_id": "strings.violin", "system_name": "Violin 1 (Solo)", "program": 40, "vol": 80, "pan": 40, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Violino II-1", "instrument_id": "strings.violin", "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 52, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Violino II-2", "instrument_id": "strings.violin", "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 64, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola I (8ve)", "instrument_id": "strings.viola", "system_name": "Viola (Solo)", "program": 41, "vol": 70, "pan": 76, "octave": 12},
            {"voice": "Tenor",     "instrument_name": "Cello I-1", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 88, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello I-2", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 100, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Viola II (8ve)", "instrument_id": "strings.viola", "system_name": "Viola (Solo)", "program": 41, "vol": 70, "pan": 64, "octave": 12},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo I", "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo II", "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 85, "pan": 120, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Cello II", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 52, "octave": 0}
        ]
    },
    # ─── 16 INSTRUMENTOS (GRANDES ORQUESTRAS) ────────────────────────────────
    {
        "id": "012_-_Grande_Orquestra_16Part",
        "name": "Grande Orquestra de Cordas de 16 Partes",
        "size": 16,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Violino I-1", "instrument_id": "strings.violin", "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 20, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Violino I-2", "instrument_id": "strings.violin", "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 36, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Violino I-3", "instrument_id": "strings.violin", "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 52, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Violino I-4", "instrument_id": "strings.violin", "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 68, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Violino II-1", "instrument_id": "strings.violin", "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 40, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola I", "instrument_id": "strings.viola", "system_name": "Viola (Solo)", "program": 41, "vol": 80, "pan": 56, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola II", "instrument_id": "strings.viola", "system_name": "Viola (Solo)", "program": 41, "vol": 80, "pan": 72, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola III", "instrument_id": "strings.viola", "system_name": "Viola (Solo)", "program": 41, "vol": 75, "pan": 88, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Viola IV", "instrument_id": "strings.viola", "system_name": "Viola (Solo)", "program": 41, "vol": 75, "pan": 48, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello I-1", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 64, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello I-2", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello I-3", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 75, "pan": 96, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Cello II", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 60, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo I", "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 85, "pan": 100, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo II", "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo III", "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 85, "pan": 120, "octave": 0}
        ]
    },
    {
        "id": "013_-_Grande_Orquestra_16Part_Soprano_Oitavado",
        "name": "Grande Orquestra de 16 Partes com Soprano Oitavado (Soprano 4 8ve)",
        "size": 16,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Violino I-1", "instrument_id": "strings.violin", "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 20, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Violino I-2", "instrument_id": "strings.violin", "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 36, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Violino I-3", "instrument_id": "strings.violin", "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 52, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Violino I-4 (8ve)", "instrument_id": "strings.violin", "system_name": "Violin 2 (Solo)", "program": 40, "vol": 70, "pan": 68, "octave": 12},
            {"voice": "Contralto", "instrument_name": "Violino II-1", "instrument_id": "strings.violin", "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 40, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola I", "instrument_id": "strings.viola", "system_name": "Viola (Solo)", "program": 41, "vol": 80, "pan": 56, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola II", "instrument_id": "strings.viola", "system_name": "Viola (Solo)", "program": 41, "vol": 80, "pan": 72, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola III", "instrument_id": "strings.viola", "system_name": "Viola (Solo)", "program": 41, "vol": 75, "pan": 88, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Viola IV", "instrument_id": "strings.viola", "system_name": "Viola (Solo)", "program": 41, "vol": 75, "pan": 48, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello I-1", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 64, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello I-2", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello I-3", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 75, "pan": 96, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Cello II", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 60, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo I", "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 85, "pan": 100, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo II", "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo III", "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 85, "pan": 120, "octave": 0}
        ]
    },
    {
        "id": "014_-_Grande_Orquestra_16Part_Solista_Espalhada",
        "name": "Grande Orquestra de 16 Partes Solista Espalhada",
        "size": 16,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Violino I-1 (Solo)", "instrument_id": "strings.violin", "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 16, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Violino I-2 (Solo)", "instrument_id": "strings.violin", "system_name": "Violin 1 (Solo)", "program": 40, "vol": 85, "pan": 32, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Violino II-1 (Solo)", "instrument_id": "strings.violin", "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 48, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Violino II-2 (Solo)", "instrument_id": "strings.violin", "system_name": "Violin 2 (Solo)", "program": 40, "vol": 80, "pan": 64, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola I (Solo)", "instrument_id": "strings.viola", "system_name": "Viola (Solo)", "program": 41, "vol": 80, "pan": 30, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola II (Solo)", "instrument_id": "strings.viola", "system_name": "Viola (Solo)", "program": 41, "vol": 80, "pan": 46, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola III (Solo)", "instrument_id": "strings.viola", "system_name": "Viola (Solo)", "program": 41, "vol": 80, "pan": 62, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Viola IV (Solo)", "instrument_id": "strings.viola", "system_name": "Viola (Solo)", "program": 41, "vol": 78, "pan": 78, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello I (Solo)", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 68, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello II (Solo)", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 84, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello III (Solo)", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 100, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Cello IV (Solo)", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 78, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Cello V (Solo)", "instrument_id": "strings.cello", "system_name": "Violoncello (Solo)", "program": 42, "vol": 80, "pan": 56, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo I (Solo)", "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 85, "pan": 104, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo II (Solo)", "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Contrabaixo III (Solo)", "instrument_id": "strings.contrabass", "system_name": "Contrabasses (Solo)", "program": 43, "vol": 85, "pan": 120, "octave": 0}
        ]
    }
]

COMBINATIONS_BRASS = [
    # ─── 4 INSTRUMENTOS (QUARTETOS) ──────────────────────────────────────────
    {
        "id": "001_-_Quarteto_de_Tromboni",
        "name": "Quarteto de Trombones",
        "size": 4,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Trombone", "instrument_id": "brass.trombone", "system_name": "Trombone", "program": 57, "vol": 80, "pan": 32, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Trombone 2", "instrument_id": "brass.trombone", "system_name": "Trombone", "program": 57, "vol": 80, "pan": 48, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Trombone 3", "instrument_id": "brass.trombone", "system_name": "Trombone", "program": 57, "vol": 85, "pan": 80, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Trombone Baixo", "instrument_id": "brass.trombone", "system_name": "Trombone", "program": 57, "vol": 85, "pan": 96, "octave": 0}
        ]
    },
    {
        "id": "002_-_Quarteto_de_Trompa",
        "name": "Quarteto de Trompas (Horn Quartet)",
        "size": 4,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Trompa", "instrument_id": "brass.french-horn", "system_name": "Horn in F", "program": 60, "vol": 120, "pan": 32, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Trompa 2", "instrument_id": "brass.french-horn", "system_name": "Horn in F", "program": 60, "vol": 120, "pan": 48, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Trompa 3", "instrument_id": "brass.french-horn", "system_name": "Horn in F", "program": 60, "vol": 120, "pan": 80, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Trompa 4", "instrument_id": "brass.french-horn", "system_name": "Horn in F", "program": 60, "vol": 85, "pan": 96, "octave": 0}
        ]
    },
    {
        "id": "003_-_Quarteto_de_Metais_Classico",
        "name": "Quarteto de Metais Clássico",
        "size": 4,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Trompete", "instrument_id": "brass.trumpet", "system_name": "Trumpet", "program": 56, "vol": 85, "pan": 32, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Trompa", "instrument_id": "brass.french-horn", "system_name": "Horn in F", "program": 60, "vol": 80, "pan": 48, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Trombone", "instrument_id": "brass.trombone", "system_name": "Trombone", "program": 57, "vol": 85, "pan": 80, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Tuba", "instrument_id": "brass.tuba", "system_name": "Tuba", "program": 58, "vol": 90, "pan": 96, "octave": 0}
        ]
    },
    {
        "id": "004_-_Quarteto_de_Trompete_e_Flugel",
        "name": "Quarteto de Trompetes e Flugelhorns",
        "size": 4,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Trompete 1", "instrument_id": "brass.trumpet", "system_name": "Trumpet", "program": 56, "vol": 85, "pan": 24, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Trompete 2", "instrument_id": "brass.trumpet", "system_name": "Trumpet", "program": 56, "vol": 80, "pan": 40, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Flugelhorn", "instrument_id": "brass.flugelhorn", "system_name": "Flugelhorn", "program": 56, "vol": 85, "pan": 88, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Cornet", "instrument_id": "brass.cornet", "system_name": "Cornet", "program": 56, "vol": 60, "pan": 104, "octave": 0}
        ]
    },
    # ─── 8 INSTRUMENTOS (OCTETOS) ────────────────────────────────────────────
    {
        "id": "005_-_Octeto_Brass_Sinfonico",
        "name": "Octeto de Metais Sinfônico",
        "size": 8,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Trompete I", "instrument_id": "brass.trumpet", "system_name": "Trumpet", "program": 56, "vol": 85, "pan": 20, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Flugelhorn", "instrument_id": "brass.flugelhorn", "system_name": "Flugelhorn", "program": 56, "vol": 80, "pan": 36, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Trompa I", "instrument_id": "brass.french-horn", "system_name": "Horn in F", "program": 60, "vol": 80, "pan": 52, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Trompa II", "instrument_id": "brass.french-horn", "system_name": "Horn in F", "program": 60, "vol": 80, "pan": 68, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Trombone I", "instrument_id": "brass.trombone", "system_name": "Trombone", "program": 57, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Euphonium", "instrument_id": "brass.euphonium", "system_name": "Euphonium", "program": 57, "vol": 80, "pan": 92, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Tuba", "instrument_id": "brass.tuba", "system_name": "Tuba", "program": 58, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Trombone Baixo", "instrument_id": "brass.trombone", "system_name": "Trombone", "program": 57, "vol": 80, "pan": 100, "octave": 0}
        ]
    },
    {
        "id": "006_-_Octeto_de_Tromboni",
        "name": "Octeto de Trombones e Eufônios",
        "size": 8,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Trombone I", "instrument_id": "brass.trombone", "system_name": "Trombone", "program": 57, "vol": 80, "pan": 24, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Trombone II", "instrument_id": "brass.trombone", "system_name": "Trombone", "program": 57, "vol": 75, "pan": 36, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Trombone III", "instrument_id": "brass.trombone", "system_name": "Trombone", "program": 57, "vol": 80, "pan": 48, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Euphonium I", "instrument_id": "brass.euphonium", "system_name": "Euphonium", "program": 57, "vol": 80, "pan": 60, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Trombone IV", "instrument_id": "brass.trombone", "system_name": "Trombone", "program": 57, "vol": 80, "pan": 84, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Euphonium II", "instrument_id": "brass.euphonium", "system_name": "Euphonium", "program": 57, "vol": 80, "pan": 96, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Trombone Baixo I", "instrument_id": "brass.trombone", "system_name": "Trombone", "program": 57, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Trombone Baixo II", "instrument_id": "brass.trombone", "system_name": "Trombone", "program": 57, "vol": 85, "pan": 120, "octave": 0}
        ]
    },
    {
        "id": "007_-_Octeto_de_Trompa_Dobrado",
        "name": "Octeto de French Horns (Trompas)",
        "size": 8,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Trompa I", "instrument_id": "brass.french-horn", "system_name": "Horn in F", "program": 60, "vol": 80, "pan": 20, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Trompa II ", "instrument_id": "brass.french-horn", "system_name": "Horn in F", "program": 60, "vol": 80, "pan": 36, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Trompa III", "instrument_id": "brass.french-horn", "system_name": "Horn in F", "program": 60, "vol": 80, "pan": 52, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Trompa IV", "instrument_id": "brass.french-horn", "system_name": "Horn in F", "program": 60, "vol": 80, "pan": 68, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Trompa V", "instrument_id": "brass.french-horn", "system_name": "Horn in F", "program": 60, "vol": 50, "pan": 80, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Trompa VI", "instrument_id": "brass.french-horn", "system_name": "Horn in F", "program": 60, "vol": 50, "pan": 92, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Trompa VII", "instrument_id": "brass.french-horn", "system_name": "Horn in F", "program": 60, "vol": 50, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Trompa VIII", "instrument_id": "brass.french-horn", "system_name": "Horn in F", "program": 60, "vol": 50, "pan": 120, "octave": 0}
        ]
    },
    {
        "id": "008_-_Octeto_Mellow_Brass",
        "name": "Octeto Mellow Brass (Metais Aveludados)",
        "size": 8,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Flugelhorn I", "instrument_id": "brass.flugelhorn", "system_name": "Flugelhorn", "program": 56, "vol": 85, "pan": 24, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Flugelhorn II", "instrument_id": "brass.flugelhorn", "system_name": "Flugelhorn", "program": 56, "vol": 80, "pan": 38, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Trompa I", "instrument_id": "brass.french-horn", "system_name": "Horn in F", "program": 60, "vol": 80, "pan": 54, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Tenor Horn", "instrument_id": "brass.tenor-horn", "system_name": "Alto Horn", "program": 56, "vol": 80, "pan": 68, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Baritone Horn", "instrument_id": "brass.baritone-horn", "system_name": "Baritone Horn", "program": 57, "vol": 80, "pan": 82, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Euphonium", "instrument_id": "brass.euphonium", "system_name": "Euphonium", "program": 57, "vol": 80, "pan": 94, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Tuba I", "instrument_id": "brass.tuba", "system_name": "Tuba", "program": 58, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Tuba II", "instrument_id": "brass.tuba", "system_name": "Tuba", "program": 58, "vol": 80, "pan": 104, "octave": 0}
        ]
    },
    # ─── 12 INSTRUMENTOS ─────────────────────────────────────────────────────
    {
        "id": "009_-_Orquestra_Brass_12Part_Sinfonica",
        "name": "Orquestra de Metais de 12 Partes Sinfônica",
        "size": 12,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Trompete I-1", "instrument_id": "brass.trumpet", "system_name": "Trumpet", "program": 56, "vol": 85, "pan": 16, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Trompete I-2", "instrument_id": "brass.trumpet", "system_name": "Trumpet", "program": 56, "vol": 85, "pan": 28, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Flugelhorn", "instrument_id": "brass.flugelhorn", "system_name": "Flugelhorn", "program": 56, "vol": 80, "pan": 40, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Trompa I-1", "instrument_id": "brass.french-horn", "system_name": "Horn in F", "program": 60, "vol": 80, "pan": 52, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Trompa I-2", "instrument_id": "brass.french-horn", "system_name": "Horn in F", "program": 60, "vol": 80, "pan": 64, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Tenor Horn", "instrument_id": "brass.tenor-horn", "system_name": "Alto Horn", "program": 56, "vol": 80, "pan": 76, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Trombone I-1", "instrument_id": "brass.trombone", "system_name": "Trombone", "program": 57, "vol": 80, "pan": 88, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Trombone I-2", "instrument_id": "brass.trombone", "system_name": "Trombone", "program": 57, "vol": 80, "pan": 100, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Euphonium", "instrument_id": "brass.euphonium", "system_name": "Euphonium", "program": 57, "vol": 75, "pan": 64, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Tuba I", "instrument_id": "brass.tuba", "system_name": "Tuba", "program": 58, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Tuba II", "instrument_id": "brass.tuba", "system_name": "Tuba", "program": 58, "vol": 85, "pan": 120, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Trombone Baixo", "instrument_id": "brass.trombone", "system_name": "Trombone", "program": 57, "vol": 80, "pan": 52, "octave": 0}
        ]
    },
    {
        "id": "010_-_Orquestra_Brass_12Part_Tromboni_Espalhada",
        "name": "Orquestra de 12 Trombones e Eufônios",
        "size": 12,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Trombone I-1 ", "instrument_id": "brass.trombone", "system_name": "Trombone", "program": 57, "vol": 80, "pan": 16, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Trombone I-2 ", "instrument_id": "brass.trombone", "system_name": "Trombone", "program": 57, "vol": 80, "pan": 32, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Euphonium I-1 ", "instrument_id": "brass.euphonium", "system_name": "Euphonium", "program": 57, "vol": 75, "pan": 48, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Trombone II-1 ", "instrument_id": "brass.trombone", "system_name": "Trombone", "program": 57, "vol": 80, "pan": 40, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Trombone II-2 ", "instrument_id": "brass.trombone", "system_name": "Trombone", "program": 57, "vol": 80, "pan": 56, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Euphonium I-2 ", "instrument_id": "brass.euphonium", "system_name": "Euphonium", "program": 57, "vol": 75, "pan": 72, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Trombone III-1", "instrument_id": "brass.trombone", "system_name": "Trombone", "program": 57, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Trombone III-2", "instrument_id": "brass.trombone", "system_name": "Trombone", "program": 57, "vol": 80, "pan": 96, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Euphonium II-1", "instrument_id": "brass.euphonium", "system_name": "Euphonium", "program": 57, "vol": 75, "pan": 68, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Trombone Baixo I", "instrument_id": "brass.trombone", "system_name": "Trombone", "program": 57, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Trombone Baixo II", "instrument_id": "brass.trombone", "system_name": "Trombone", "program": 57, "vol": 85, "pan": 120, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Euphonium II-2", "instrument_id": "brass.euphonium", "system_name": "Euphonium", "program": 57, "vol": 80, "pan": 56, "octave": 0}
        ]
    },
    # ─── 16 INSTRUMENTOS (GRANDES ORQUESTRAS) ────────────────────────────────
    {
        "id": "011_-_Grande_Orquestra_Brass_16Part",
        "name": "Grande Orquestra de Metais de 16 Partes",
        "size": 16,
        "tracks": [
            # Soprano (4 Trumpets)
            {"voice": "Soprano",   "instrument_name": "Trompete I-1", "instrument_id": "brass.trumpet", "system_name": "Trumpet", "program": 56, "vol": 85, "pan": 20, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Trompete I-2", "instrument_id": "brass.trumpet", "system_name": "Trumpet", "program": 56, "vol": 85, "pan": 36, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Trompete I-3", "instrument_id": "brass.trumpet", "system_name": "Trumpet", "program": 56, "vol": 80, "pan": 52, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Flugelhorn I", "instrument_id": "brass.flugelhorn", "system_name": "Flugelhorn", "program": 56, "vol": 80, "pan": 68, "octave": 0},
            # Contralto (4 Horns)
            {"voice": "Contralto", "instrument_name": "Trompa I-1", "instrument_id": "brass.french-horn", "system_name": "Horn in F", "program": 60, "vol": 80, "pan": 40, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Trompa I-2", "instrument_id": "brass.french-horn", "system_name": "Horn in F", "program": 60, "vol": 80, "pan": 56, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Trompa I-3", "instrument_id": "brass.french-horn", "system_name": "Horn in F", "program": 60, "vol": 80, "pan": 72, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Tenor Horn", "instrument_id": "brass.tenor-horn", "system_name": "Alto Horn", "program": 56, "vol": 75, "pan": 88, "octave": 0},
            # Tenor (4 Trombones)
            {"voice": "Tenor",     "instrument_name": "Trombone I-1", "instrument_id": "brass.trombone", "system_name": "Trombone", "program": 57, "vol": 80, "pan": 48, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Trombone I-2", "instrument_id": "brass.trombone", "system_name": "Trombone", "program": 57, "vol": 80, "pan": 64, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Euphonium I-1", "instrument_id": "brass.euphonium", "system_name": "Euphonium", "program": 57, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Baritone Horn", "instrument_id": "brass.baritone-horn", "system_name": "Baritone Horn", "program": 57, "vol": 100, "pan": 96, "octave": 0},
            # Baixo (4 Tubas/Basses)
            {"voice": "Baixo",     "instrument_name": "Trombone Baixo I", "instrument_id": "brass.trombone", "system_name": "Trombone", "program": 57, "vol": 85, "pan": 60, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Tuba I", "instrument_id": "brass.tuba", "system_name": "Tuba", "program": 58, "vol": 85, "pan": 100, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Tuba II", "instrument_id": "brass.tuba", "system_name": "Tuba", "program": 58, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Tuba III", "instrument_id": "brass.tuba", "system_name": "Tuba", "program": 58, "vol": 85, "pan": 120, "octave": 0}
        ]
    },
    {
        "id": "012_-_Grande_Orquestra_Brass_16Part_Mellow",
        "name": "Grande Orquestra de Metais Mellow (Metais Suaves)",
        "size": 16,
        "tracks": [
            # Soprano (4 Flugelhorns)
            {"voice": "Soprano",   "instrument_name": "Flugelhorn I-1", "instrument_id": "brass.flugelhorn", "system_name": "Flugelhorn", "program": 56, "vol": 85, "pan": 20, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Flugelhorn I-2", "instrument_id": "brass.flugelhorn", "system_name": "Flugelhorn", "program": 56, "vol": 85, "pan": 36, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Flugelhorn I-3", "instrument_id": "brass.flugelhorn", "system_name": "Flugelhorn", "program": 56, "vol": 80, "pan": 52, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Cornet I-1", "instrument_id": "brass.cornet", "system_name": "Cornet", "program": 56, "vol": 80, "pan": 68, "octave": 0},
            # Contralto (4 Horns)
            {"voice": "Contralto", "instrument_name": "Trompa I-1", "instrument_id": "brass.french-horn", "system_name": "Horn in F", "program": 60, "vol": 80, "pan": 40, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Trompa I-2", "instrument_id": "brass.french-horn", "system_name": "Horn in F", "program": 60, "vol": 80, "pan": 56, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Tenor Horn I-1", "instrument_id": "brass.tenor-horn", "system_name": "Alto Horn", "program": 56, "vol": 80, "pan": 72, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Tenor Horn I-2", "instrument_id": "brass.tenor-horn", "system_name": "Alto Horn", "program": 56, "vol": 75, "pan": 88, "octave": 0},
            # Tenor (4 Baritones/Euphoniums)
            {"voice": "Tenor",     "instrument_name": "Baritone Horn I-1", "instrument_id": "brass.baritone-horn", "system_name": "Baritone Horn", "program": 57, "vol": 80, "pan": 48, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Baritone Horn I-2", "instrument_id": "brass.baritone-horn", "system_name": "Baritone Horn", "program": 57, "vol": 80, "pan": 64, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Euphonium I-1", "instrument_id": "brass.euphonium", "system_name": "Euphonium", "program": 57, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Euphonium I-2", "instrument_id": "brass.euphonium", "system_name": "Euphonium", "program": 57, "vol": 75, "pan": 96, "octave": 0},
            # Baixo (4 Tubas)
            {"voice": "Baixo",     "instrument_name": "Tuba I-1", "instrument_id": "brass.tuba", "system_name": "Tuba", "program": 58, "vol": 85, "pan": 60, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Tuba I-2", "instrument_id": "brass.tuba", "system_name": "Tuba", "program": 58, "vol": 85, "pan": 100, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Tuba I-3", "instrument_id": "brass.tuba", "system_name": "Tuba", "program": 58, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Tuba I-4", "instrument_id": "brass.tuba", "system_name": "Tuba", "program": 58, "vol": 85, "pan": 120, "octave": 0}
        ]
    }
]

COMBINATIONS_PALETAS = [
    # ─── 4 INSTRUMENTOS (QUARTETOS) ──────────────────────────────────────────
    {
        "id": "001_-_Quarteto_de_Sax_Classico",
        "name": "Quarteto de Saxofones Clássico (SATB)",
        "size": 4,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Sax Soprano", "instrument_id": "sax.soprano", "system_name": "Soprano Sax", "program": 64, "vol": 80, "pan": 32, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Sax Alto", "instrument_id": "sax.alto", "system_name": "Alto Sax", "program": 65, "vol": 80, "pan": 48, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Sax Tenor", "instrument_id": "sax.tenor", "system_name": "Tenor Sax", "program": 66, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Sax Baritono", "instrument_id": "sax.baritone", "system_name": "Baritone Sax", "program": 67, "vol": 85, "pan": 96, "octave": 0}
        ]
    },
    {
        "id": "002_-_Quarteto_de_Clarinete",
        "name": "Quarteto de Clarinetes",
        "size": 4,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Clarinete I ", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 32, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Clarinete II ", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 48, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Clarinete III", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 85, "pan": 80, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Clarinete Baixo", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 85, "pan": 96, "octave": 0}
        ]
    },
    {
        "id": "003_-_Quarteto_de_Paletas_Classico",
        "name": "Quarteto de Paletas Clássico",
        "size": 4,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Oboe", "instrument_id": "woodwind.reed.oboe", "system_name": "Oboe", "program": 68, "vol": 85, "pan": 32, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Clarinete", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 48, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Corne Ingles", "instrument_id": "woodwind.reed.english-horn", "system_name": "Horns a6", "program": 69, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Fagote", "instrument_id": "woodwind.reed.bassoon", "system_name": "Bassoon", "program": 70, "vol": 85, "pan": 96, "octave": 0}
        ]
    },
    {
        "id": "004_-_Quarteto_Sax_Alto_Tenor",
        "name": "Quarteto de Saxofones (Alto/Tenor)",
        "size": 4,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Sax Alto 1", "instrument_id": "sax.alto", "system_name": "Alto Sax", "program": 65, "vol": 85, "pan": 24, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Sax Alto 2", "instrument_id": "sax.alto", "system_name": "Alto Sax", "program": 65, "vol": 80, "pan": 40, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Sax Tenor", "instrument_id": "sax.tenor", "system_name": "Tenor Sax", "program": 66, "vol": 100, "pan": 88, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Sax Baritono", "instrument_id": "sax.baritone", "system_name": "Baritone Sax", "program": 67, "vol": 85, "pan": 104, "octave": 0}
        ]
    },
    # ─── 8 INSTRUMENTOS (OCTETOS) ────────────────────────────────────────────
    {
        "id": "005_-_Octeto_de_Saxofones",
        "name": "Octeto de Saxofones",
        "size": 8,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Sax Soprano I", "instrument_id": "sax.soprano", "system_name": "Soprano Sax", "program": 64, "vol": 80, "pan": 20, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Sax Soprano II", "instrument_id": "sax.soprano", "system_name": "Soprano Sax", "program": 64, "vol": 75, "pan": 36, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Sax Alto I", "instrument_id": "sax.alto", "system_name": "Alto Sax", "program": 65, "vol": 80, "pan": 52, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Sax Alto II", "instrument_id": "sax.alto", "system_name": "Alto Sax", "program": 65, "vol": 80, "pan": 68, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Sax Tenor I", "instrument_id": "sax.tenor", "system_name": "Tenor Sax", "program": 66, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Sax Tenor II", "instrument_id": "sax.tenor", "system_name": "Tenor Sax", "program": 66, "vol": 100, "pan": 110, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Sax Baritono I", "instrument_id": "sax.baritone", "system_name": "Baritone Sax", "program": 67, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Sax Baritono II", "instrument_id": "sax.baritone", "system_name": "Baritone Sax", "program": 67, "vol": 85, "pan": 120, "octave": 0}
        ]
    },
    {
        "id": "006_-_Octeto_de_Clarinetes",
        "name": "Octeto de Clarinetes (Clarinet Choir)",
        "size": 8,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Clarinete I", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 24, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Clarinete II", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 75, "pan": 38, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Clarinete III", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 54, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Clarinete IV", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 68, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Clarinete V", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 82, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Clarinete VI", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 94, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Clarinete Baixo I", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Clarinete Baixo II", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 85, "pan": 120, "octave": 0}
        ]
    },
    {
        "id": "007_-_Octeto_Paletas_Sinfonico",
        "name": "Octeto de Paletas Sinfônico",
        "size": 8,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Oboe I", "instrument_id": "woodwind.reed.oboe", "system_name": "Oboe", "program": 68, "vol": 85, "pan": 20, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Clarinete I", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 36, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Oboe II", "instrument_id": "woodwind.reed.oboe", "system_name": "Oboe", "program": 68, "vol": 80, "pan": 52, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Clarinete II", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 68, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Corne Ingles I", "instrument_id": "woodwind.reed.english-horn", "system_name": "Horns a6", "program": 69, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Clarinete III", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 75, "pan": 92, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Fagote I", "instrument_id": "woodwind.reed.bassoon", "system_name": "Bassoon", "program": 70, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Fagote II", "instrument_id": "woodwind.reed.bassoon", "system_name": "Bassoon", "program": 70, "vol": 85, "pan": 120, "octave": 0}
        ]
    },
    {
        "id": "008_-_Octeto_Sax_Clarinet_Misto",
        "name": "Octeto Sax/Clarinete Misto",
        "size": 8,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Sax Soprano", "instrument_id": "sax.soprano", "system_name": "Soprano Sax", "program": 64, "vol": 80, "pan": 24, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Clarinete I ", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 38, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Sax Alto", "instrument_id": "sax.alto", "system_name": "Alto Sax", "program": 65, "vol": 80, "pan": 54, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Clarinete II", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 68, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Sax Tenor", "instrument_id": "sax.tenor", "system_name": "Tenor Sax", "program": 66, "vol": 80, "pan": 82, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Clarinete III", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 75, "pan": 94, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Sax Baritono", "instrument_id": "sax.baritone", "system_name": "Baritone Sax", "program": 67, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Clarinete Baixo", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 85, "pan": 104, "octave": 0}
        ]
    },
    # ─── 12 INSTRUMENTOS ─────────────────────────────────────────────────────
    {
        "id": "009_-_Orquestra_Paletas_12Part_Classica",
        "name": "Orquestra de Paletas de 12 Partes Clássica",
        "size": 12,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Oboe I", "instrument_id": "woodwind.reed.oboe", "system_name": "Oboe", "program": 68, "vol": 85, "pan": 16, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Clarinete I", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 85, "pan": 28, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Sax Soprano", "instrument_id": "sax.soprano", "system_name": "Soprano Sax", "program": 64, "vol": 80, "pan": 40, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Clarinete II", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 52, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Corne Ingles I", "instrument_id": "woodwind.reed.english-horn", "system_name": "Horns a6", "program": 69, "vol": 80, "pan": 64, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Sax Alto", "instrument_id": "sax.alto", "system_name": "Alto Sax", "program": 65, "vol": 80, "pan": 76, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Clarinete III", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 88, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Corne Ingles II", "instrument_id": "woodwind.reed.english-horn", "system_name": "Horns a6", "program": 69, "vol": 80, "pan": 100, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Sax Tenor", "instrument_id": "sax.tenor", "system_name": "Tenor Sax", "program": 66, "vol": 75, "pan": 64, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Fagote I", "instrument_id": "woodwind.reed.bassoon", "system_name": "Bassoon", "program": 70, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Sax Baritono", "instrument_id": "sax.baritone", "system_name": "Baritone Sax", "program": 67, "vol": 85, "pan": 120, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Fagote II", "instrument_id": "woodwind.reed.bassoon", "system_name": "Bassoon", "program": 70, "vol": 120, "pan": 52, "octave": 0}
        ]
    },
    {
        "id": "010_-_Orquestra_Paletas_12Part_Sax",
        "name": "Orquestra de Saxofones de 12 Partes",
        "size": 12,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Sax Soprano I", "instrument_id": "sax.soprano", "system_name": "Soprano Sax", "program": 64, "vol": 85, "pan": 16, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Sax Soprano II", "instrument_id": "sax.soprano", "system_name": "Soprano Sax", "program": 64, "vol": 85, "pan": 32, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Sax Alto 1", "instrument_id": "sax.alto", "system_name": "Alto Sax", "program": 65, "vol": 80, "pan": 48, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Sax Alto 2", "instrument_id": "sax.alto", "system_name": "Alto Sax", "program": 65, "vol": 80, "pan": 40, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Sax Alto 3", "instrument_id": "sax.alto", "system_name": "Alto Sax", "program": 65, "vol": 80, "pan": 56, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Sax Tenor 1", "instrument_id": "sax.tenor", "system_name": "Tenor Sax", "program": 66, "vol": 80, "pan": 72, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Sax Tenor 2", "instrument_id": "sax.tenor", "system_name": "Tenor Sax", "program": 66, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Sax Tenor 3", "instrument_id": "sax.tenor", "system_name": "Tenor Sax", "program": 66, "vol": 80, "pan": 96, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Sax Baritono 1 (8ve)", "instrument_id": "sax.baritone", "system_name": "Baritone Sax", "program": 67, "vol": 75, "pan": 68, "octave": 12},
            {"voice": "Baixo",     "instrument_name": "Sax Baritono 2", "instrument_id": "sax.baritone", "system_name": "Baritone Sax", "program": 67, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Sax Baritono 3", "instrument_id": "sax.baritone", "system_name": "Baritone Sax", "program": 67, "vol": 85, "pan": 120, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Sax Alto 4", "instrument_id": "sax.alto", "system_name": "Alto Sax", "program": 65, "vol": 80, "pan": 56, "octave": 0}
        ]
    },
    # ─── 16 INSTRUMENTOS (GRANDES ORQUESTRAS) ────────────────────────────────
    {
        "id": "011_-_Grande_Orquestra_Paletas_16Part",
        "name": "Grande Orquestra de Paletas de 16 Partes",
        "size": 16,
        "tracks": [
            # Soprano
            {"voice": "Soprano",   "instrument_name": "Oboe I", "instrument_id": "woodwind.reed.oboe", "system_name": "Oboe", "program": 68, "vol": 85, "pan": 20, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Oboe II", "instrument_id": "woodwind.reed.oboe", "system_name": "Oboe", "program": 68, "vol": 85, "pan": 36, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Clarinete I", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 52, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Sax Soprano I", "instrument_id": "sax.soprano", "system_name": "Soprano Sax", "program": 64, "vol": 80, "pan": 68, "octave": 0},
            # Contralto
            {"voice": "Contralto", "instrument_name": "Clarinete II", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 40, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Corne Ingles I", "instrument_id": "woodwind.reed.english-horn", "system_name": "Horns a6", "program": 69, "vol": 80, "pan": 56, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Sax Alto I", "instrument_id": "sax.alto", "system_name": "Alto Sax", "program": 65, "vol": 80, "pan": 72, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Sax Alto II", "instrument_id": "sax.alto", "system_name": "Alto Sax", "program": 65, "vol": 75, "pan": 88, "octave": 0},
            # Tenor
            {"voice": "Tenor",     "instrument_name": "Clarinete III", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 48, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Corne Ingles II", "instrument_id": "woodwind.reed.english-horn", "system_name": "Horns a6", "program": 69, "vol": 80, "pan": 64, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Sax Tenor I", "instrument_id": "sax.tenor", "system_name": "Tenor Sax", "program": 66, "vol": 100, "pan": 80, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Sax Tenor II", "instrument_id": "sax.tenor", "system_name": "Tenor Sax", "program": 66, "vol": 75, "pan": 96, "octave": 0},
            # Baixo
            {"voice": "Baixo",     "instrument_name": "Fagote I", "instrument_id": "woodwind.reed.bassoon", "system_name": "Bassoon", "program": 70, "vol": 85, "pan": 60, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Fagote II", "instrument_id": "woodwind.reed.bassoon", "system_name": "Bassoon", "program": 70, "vol": 100, "pan": 100, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Sax Baritono I", "instrument_id": "sax.baritone", "system_name": "Baritone Sax", "program": 67, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Sax Baritono II", "instrument_id": "sax.baritone", "system_name": "Baritone Sax", "program": 67, "vol": 100, "pan": 120, "octave": 0}
        ]
    },
    {
        "id": "012_-_Grande_Orquestra_Paletas_16Part_Sax_Clarinet",
        "name": "Grande Orquestra Sax/Clarinete de 16 Partes",
        "size": 16,
        "tracks": [
            # Soprano (4 Clarinetes/Sax)
            {"voice": "Soprano",   "instrument_name": "Clarinete I", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 20, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Clarinete II", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 36, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Sax Soprano I", "instrument_id": "sax.soprano", "system_name": "Soprano Sax", "program": 64, "vol": 85, "pan": 52, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Sax Soprano II", "instrument_id": "sax.soprano", "system_name": "Soprano Sax", "program": 64, "vol": 80, "pan": 68, "octave": 0},
            # Contralto (4 Clarinetes/Sax)
            {"voice": "Contralto", "instrument_name": "Clarinete III", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 40, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Clarinete IV", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 56, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Sax Alto I", "instrument_id": "sax.alto", "system_name": "Alto Sax", "program": 65, "vol": 80, "pan": 72, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Sax Alto II", "instrument_id": "sax.alto", "system_name": "Alto Sax", "program": 65, "vol": 75, "pan": 88, "octave": 0},
            # Tenor (4 Clarinetes/Sax)
            {"voice": "Tenor",     "instrument_name": "Clarinete V", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 48, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Clarinete VI", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 64, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Sax Tenor I", "instrument_id": "sax.tenor", "system_name": "Tenor Sax", "program": 66, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Sax Tenor II", "instrument_id": "sax.tenor", "system_name": "Tenor Sax", "program": 66, "vol": 75, "pan": 96, "octave": 0},
            # Baixo (4 Bass Clarinets/Baritones)
            {"voice": "Baixo",     "instrument_name": "Clarinete Baixo I", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 85, "pan": 60, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Clarinete Baixo II", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 85, "pan": 100, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Sax Baritono I", "instrument_id": "sax.baritone", "system_name": "Baritone Sax", "program": 67, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Sax Baritono II", "instrument_id": "sax.baritone", "system_name": "Baritone Sax", "program": 67, "vol": 85, "pan": 120, "octave": 0}
        ]
    }
]

COMBINATIONS_SOPROS = [
    # ─── 4 INSTRUMENTOS (QUARTETOS) ──────────────────────────────────────────
    {
        "id": "001_-_Quarteto_de_Madeiras_Classico",
        "name": "Quarteto de Madeiras Clássico",
        "size": 4,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Flauta", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 60, "pan": 32, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Oboe", "instrument_id": "woodwind.reed.oboe", "system_name": "Oboe", "program": 68, "vol": 80, "pan": 100, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Clarinete", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 100, "pan": 80, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Fagote", "instrument_id": "woodwind.reed.bassoon", "system_name": "Bassoon", "program": 70, "vol": 100, "pan": 96, "octave": 0}
        ]
    },
    {
        "id": "002_-_Quarteto_de_Flautas",
        "name": "Quarteto de Flautas (Flute Choir)",
        "size": 4,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Piccolo", "instrument_id": "woodwind.flutes.piccolo", "system_name": "Piccolo", "program": 72, "vol": 120, "pan": 32, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Flauta I", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 85, "pan": 48, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Flauta II", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Flauta III", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 100, "pan": 96, "octave": 0}
        ]
    },
    {
        "id": "003_-_Quarteto_de_Clarinete_e_Flauta",
        "name": "Quarteto de Clarinete e Flauta",
        "size": 4,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Flauta 1", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 70, "pan": 24, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Flauta 2", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 80, "pan": 40, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Clarinete 1", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 100, "vol": 85, "pan": 88, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Clarinete 2", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 85, "pan": 104, "octave": 0}
        ]
    },
    {
        "id": "004_-_Quarteto_Oboe_Fagote",
        "name": "Quarteto de Oboés e Fagotes",
        "size": 4,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Oboe 1", "instrument_id": "woodwind.reed.oboe", "system_name": "Oboe", "program": 68, "vol": 85, "pan": 32, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Oboe 2", "instrument_id": "woodwind.reed.oboe", "system_name": "Oboe", "program": 68, "vol": 80, "pan": 48, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Fagote 1", "instrument_id": "woodwind.reed.bassoon", "system_name": "Bassoon", "program": 70, "vol": 100, "pan": 80, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Fagote 2", "instrument_id": "woodwind.reed.bassoon", "system_name": "Bassoon", "program": 70, "vol": 100, "pan": 96, "octave": 0}
        ]
    },
    # ─── 8 INSTRUMENTOS (OCTETOS) ────────────────────────────────────────────
    {
        "id": "005_-_Octeto_de_Madeiras_Sinfonico",
        "name": "Octeto de Madeiras Sinfônico",
        "size": 8,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Piccolo", "instrument_id": "woodwind.flutes.piccolo", "system_name": "Piccolo", "program": 72, "vol": 75, "pan": 20, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Flauta I", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 60, "pan": 36, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Oboe I", "instrument_id": "woodwind.reed.oboe", "system_name": "Oboe", "program": 68, "vol": 80, "pan": 52, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Clarinete I", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 68, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Clarinete II", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Corne Ingles", "instrument_id": "woodwind.reed.english-horn", "system_name": "Horns a6", "program": 100, "vol": 80, "pan": 92, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Fagote I", "instrument_id": "woodwind.reed.bassoon", "system_name": "Bassoon", "program": 70, "vol": 100, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Fagote II", "instrument_id": "woodwind.reed.bassoon", "system_name": "Bassoon", "program": 70, "vol": 100, "pan": 100, "octave": 0}
        ]
    },
    {
        "id": "006_-_Octeto_de_Flautas",
        "name": "Octeto de Flautas e Piccolos",
        "size": 8,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Piccolo I", "instrument_id": "woodwind.flutes.piccolo", "system_name": "Piccolo", "program": 72, "vol": 75, "pan": 24, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Piccolo II", "instrument_id": "woodwind.flutes.piccolo", "system_name": "Piccolo", "program": 72, "vol": 75, "pan": 36, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Flauta I", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 60, "pan": 48, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Flauta II", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 60, "pan": 60, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Flauta III", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 100, "pan": 84, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Flauta IV", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 100, "pan": 96, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Flauta V (8ve -12)", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 100, "pan": 112, "octave": -12},
            {"voice": "Baixo",     "instrument_name": "Flauta VI (8ve -12)", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 100, "pan": 120, "octave": -12}
        ]
    },
    {
        "id": "007_-_Octeto_de_Clarinetes_e_Flautas",
        "name": "Octeto de Clarinetes e Flautas",
        "size": 8,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Flauta I", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 85, "pan": 20, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Clarinete I", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 36, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Flauta II", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 80, "pan": 52, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Clarinete II", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 68, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Flauta III", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Clarinete III", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 92, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Fagote I", "instrument_id": "woodwind.reed.bassoon", "system_name": "Bassoon", "program": 70, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Clarinete Baixo", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 85, "pan": 100, "octave": 0}
        ]
    },
    {
        "id": "008_-_Octeto_Madeiras_Foco_Agudo",
        "name": "Octeto de Madeiras Foco Agudo",
        "size": 8,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Piccolo", "instrument_id": "woodwind.flutes.piccolo", "system_name": "Piccolo", "program": 72, "vol": 75, "pan": 24, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Flauta I", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 60, "pan": 38, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Flauta II", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 60, "pan": 54, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Oboe I", "instrument_id": "woodwind.reed.oboe", "system_name": "Oboe", "program": 68, "vol": 80, "pan": 68, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Clarinete I", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 100, "pan": 82, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Clarinete II", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 100, "pan": 94, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Fagote I", "instrument_id": "woodwind.reed.bassoon", "system_name": "Bassoon", "program": 70, "vol": 100, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Fagote II", "instrument_id": "woodwind.reed.bassoon", "system_name": "Bassoon", "program": 70, "vol": 100, "pan": 120, "octave": 0}
        ]
    },
    # ─── 12 INSTRUMENTOS ─────────────────────────────────────────────────────
    {
        "id": "009_-_Orquestra_Madeiras_12Part_Classica",
        "name": "Orquestra de Madeiras de 12 Partes Clássica",
        "size": 12,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Piccolo", "instrument_id": "woodwind.flutes.piccolo", "system_name": "Piccolo", "program": 72, "vol": 75, "pan": 16, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Flauta I", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 60, "pan": 28, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Oboe I", "instrument_id": "woodwind.reed.oboe", "system_name": "Oboe", "program": 68, "vol": 80, "pan": 40, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Flauta II", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 60, "pan": 52, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Oboe II", "instrument_id": "woodwind.reed.oboe", "system_name": "Oboe", "program": 68, "vol": 80, "pan": 64, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Clarinete I", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 76, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Clarinete II", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 88, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Corne Ingles", "instrument_id": "woodwind.reed.english-horn", "system_name": "Horns a6", "program": 69, "vol": 80, "pan": 100, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Fagote I", "instrument_id": "woodwind.reed.bassoon", "system_name": "Bassoon", "program": 70, "vol": 100, "pan": 64, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Fagote II", "instrument_id": "woodwind.reed.bassoon", "system_name": "Bassoon", "program": 70, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Fagote III", "instrument_id": "woodwind.reed.bassoon", "system_name": "Bassoon", "program": 70, "vol": 85, "pan": 120, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Clarinete Baixo", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 100, "pan": 52, "octave": 0}
        ]
    },
    {
        "id": "010_-_Orquestra_Madeiras_12Part_Flautas",
        "name": "Orquestra de Flautas de 12 Partes",
        "size": 12,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Piccolo I", "instrument_id": "woodwind.flutes.piccolo", "system_name": "Piccolo", "program": 72, "vol": 75, "pan": 16, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Piccolo II", "instrument_id": "woodwind.flutes.piccolo", "system_name": "Piccolo", "program": 72, "vol": 75, "pan": 32, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Flauta I (8ve)", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 60, "pan": 48, "octave": 12},
            {"voice": "Contralto", "instrument_name": "Flauta II", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 85, "pan": 40, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Flauta III", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 80, "pan": 56, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Flauta IV (8ve)", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 80, "pan": 72, "octave": 12},
            {"voice": "Tenor",     "instrument_name": "Flauta V", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Flauta VI", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 80, "pan": 96, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Flauta VII (8ve)", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 75, "pan": 68, "octave": 12},
            {"voice": "Baixo",     "instrument_name": "Flauta VIII (8ve -12)", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 85, "pan": 112, "octave": -12},
            {"voice": "Baixo",     "instrument_name": "Flauta IX (8ve -12)", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 85, "pan": 120, "octave": -12},
            {"voice": "Baixo",     "instrument_name": "Flauta X", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 80, "pan": 56, "octave": 0}
        ]
    },
    # ─── 16 INSTRUMENTOS (GRANDES ORQUESTRAS) ────────────────────────────────
    {
        "id": "011_-_Grande_Orquestra_Madeiras_16Part",
        "name": "Grande Orquestra de Madeiras de 16 Partes",
        "size": 16,
        "tracks": [
            # Soprano
            {"voice": "Soprano",   "instrument_name": "Piccolo I", "instrument_id": "woodwind.flutes.piccolo", "system_name": "Piccolo", "program": 72, "vol": 75, "pan": 20, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Flauta I", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 60, "pan": 36, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Oboe I", "instrument_id": "woodwind.reed.oboe", "system_name": "Oboe", "program": 68, "vol": 80, "pan": 52, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Clarinete I", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 68, "octave": 0},
            # Contralto
            {"voice": "Contralto", "instrument_name": "Flauta II", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 60, "pan": 40, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Oboe II", "instrument_id": "woodwind.reed.oboe", "system_name": "Oboe", "program": 68, "vol": 80, "pan": 56, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Clarinete II", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 72, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Corne Ingles I", "instrument_id": "woodwind.reed.english-horn", "system_name": "Horns a6", "program": 69, "vol": 75, "pan": 88, "octave": 0},
            # Tenor
            {"voice": "Tenor",     "instrument_name": "Flauta III", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 80, "pan": 48, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Clarinete III", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 64, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Fagote I", "instrument_id": "woodwind.reed.bassoon", "system_name": "Bassoon", "program": 70, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Corne Ingles II", "instrument_id": "woodwind.reed.english-horn", "system_name": "Horns a6", "program": 69, "vol": 75, "pan": 96, "octave": 0},
            # Baixo
            {"voice": "Baixo",     "instrument_name": "Fagote II", "instrument_id": "woodwind.reed.bassoon", "system_name": "Bassoon", "program": 70, "vol": 85, "pan": 60, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Fagote III", "instrument_id": "woodwind.reed.bassoon", "system_name": "Bassoon", "program": 70, "vol": 85, "pan": 100, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Clarinete Baixo I", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Clarinete Baixo II", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 85, "pan": 120, "octave": 0}
        ]
    },
    {
        "id": "012_-_Grande_Orquestra_Madeiras_16Part_Solista",
        "name": "Grande Orquestra de Madeiras Solista (16 Partes)",
        "size": 16,
        "tracks": [
            # Soprano (4 Flutes/Oboe)
            {"voice": "Soprano",   "instrument_name": "Piccolo (Solo)", "instrument_id": "woodwind.flutes.piccolo", "system_name": "Piccolo", "program": 72, "vol": 75, "pan": 20, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Flauta I (Solo)", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 85, "pan": 36, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Flauta II (Solo)", "instrument_id": "woodwind.flutes.flute", "system_name": "Flute", "program": 73, "vol": 80, "pan": 52, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Oboe I (Solo)", "instrument_id": "woodwind.reed.oboe", "system_name": "Oboe", "program": 68, "vol": 80, "pan": 68, "octave": 0},
            # Contralto (4 Oboes/Clarinetes)
            {"voice": "Contralto", "instrument_name": "Oboe II (Solo)", "instrument_id": "woodwind.reed.oboe", "system_name": "Oboe", "program": 68, "vol": 80, "pan": 40, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Clarinete I (Solo)", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 56, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Clarinete II (Solo)", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 72, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Corne Ingles I (Solo)", "instrument_id": "woodwind.reed.english-horn", "system_name": "Horns a6", "program": 69, "vol": 75, "pan": 88, "octave": 0},
            # Tenor (4 Clarinetes/Fagotes)
            {"voice": "Tenor",     "instrument_name": "Clarinete III (Solo)", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 80, "pan": 48, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Fagote I (Solo)", "instrument_id": "woodwind.reed.bassoon", "system_name": "Bassoon", "program": 70, "vol": 80, "pan": 64, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Fagote II (Solo)", "instrument_id": "woodwind.reed.bassoon", "system_name": "Bassoon", "program": 70, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Corne Ingles II (Solo)", "instrument_id": "woodwind.reed.english-horn", "system_name": "Horns a6", "program": 69, "vol": 75, "pan": 96, "octave": 0},
            # Baixo (4 Fagotes/Basses)
            {"voice": "Baixo",     "instrument_name": "Fagote III (Solo)", "instrument_id": "woodwind.reed.bassoon", "system_name": "Bassoon", "program": 70, "vol": 85, "pan": 60, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Fagote IV (Solo)", "instrument_id": "woodwind.reed.bassoon", "system_name": "Bassoon", "program": 70, "vol": 85, "pan": 100, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Clarinete Baixo I", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Clarinete Baixo II", "instrument_id": "woodwind.reed.clarinet", "system_name": "Clarinet in Bb", "program": 71, "vol": 85, "pan": 120, "octave": 0}
        ]
    }
]

COMBINATIONS_CORAL = [
    # ─── 4 VOZES (QUARTETOS DE CORAL) ──────────────────────────────────────────
    {
        "id": "001_-_Coral_Classico_SATB",
        "name": "Coral Clássico SATB",
        "size": 4,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Soprano", "instrument_id": "voice.soprano", "system_name": "Sopranos", "program": 52, "vol": 85, "pan": 32, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Alto", "instrument_id": "voice.alto", "system_name": "Altos", "program": 52, "vol": 85, "pan": 48, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Tenor", "instrument_id": "voice.tenor", "system_name": "Tenors", "program": 52, "vol": 85, "pan": 80, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Bass", "instrument_id": "voice.bass", "system_name": "Basses", "program": 52, "vol": 85, "pan": 96, "octave": 0}
        ]
    },
    {
        "id": "002_-_Coral_com_Soprano_Oitavado",
        "name": "Coral com Soprano Oitavado",
        "size": 4,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Soprano (8ve)", "instrument_id": "voice.soprano", "system_name": "Sopranos", "program": 52, "vol": 75, "pan": 32, "octave": 12},
            {"voice": "Contralto", "instrument_name": "Alto", "instrument_id": "voice.alto", "system_name": "Altos", "program": 52, "vol": 85, "pan": 48, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Tenor", "instrument_id": "voice.tenor", "system_name": "Tenors", "program": 52, "vol": 85, "pan": 80, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Bass", "instrument_id": "voice.bass", "system_name": "Basses", "program": 52, "vol": 85, "pan": 96, "octave": 0}
        ]
    },
    {
        "id": "003_-_Coral_com_Tenor_Oitavado",
        "name": "Coral com Tenores Oitavados",
        "size": 4,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Soprano", "instrument_id": "voice.soprano", "system_name": "Sopranos", "program": 52, "vol": 85, "pan": 32, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Alto", "instrument_id": "voice.alto", "system_name": "Altos", "program": 52, "vol": 85, "pan": 48, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Tenor (8ve)", "instrument_id": "voice.tenor", "system_name": "Tenors", "program": 52, "vol": 75, "pan": 80, "octave": 12},
            {"voice": "Baixo",     "instrument_name": "Bass", "instrument_id": "voice.bass", "system_name": "Basses", "program": 52, "vol": 85, "pan": 96, "octave": 0}
        ]
    },
    {
        "id": "004_-_Coral_Classico_Suave",
        "name": "Coral Clássico Suave (Blended)",
        "size": 4,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Soprano", "instrument_id": "voice.soprano", "system_name": "Sopranos", "program": 52, "vol": 70, "pan": 32, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Alto", "instrument_id": "voice.alto", "system_name": "Altos", "program": 52, "vol": 70, "pan": 48, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Tenor", "instrument_id": "voice.tenor", "system_name": "Tenors", "program": 52, "vol": 70, "pan": 80, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Bass", "instrument_id": "voice.bass", "system_name": "Basses", "program": 52, "vol": 70, "pan": 96, "octave": 0}
        ]
    },
    # ─── 8 VOZES (OCTETOS DE CORAL / DUPLO CORAL) ────────────────────────────
    {
        "id": "005_-_Duplo_Coral_Estereo",
        "name": "Duplo Coral Estéreo (Choir L / Choir R)",
        "size": 8,
        "tracks": [
            # Coral 1 (Esquerda)
            {"voice": "Soprano",   "instrument_name": "Soprano I", "instrument_id": "voice.soprano", "system_name": "Sopranos", "program": 52, "vol": 80, "pan": 20, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Alto I", "instrument_id": "voice.alto", "system_name": "Altos", "program": 52, "vol": 80, "pan": 36, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Tenor I", "instrument_id": "voice.tenor", "system_name": "Tenors", "program": 52, "vol": 80, "pan": 52, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Bass I", "instrument_id": "voice.bass", "system_name": "Basses", "program": 52, "vol": 80, "pan": 68, "octave": 0},
            # Coral 2 (Direita)
            {"voice": "Soprano",   "instrument_name": "Soprano II", "instrument_id": "voice.soprano", "system_name": "Sopranos", "program": 52, "vol": 80, "pan": 60, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Alto II", "instrument_id": "voice.alto", "system_name": "Altos", "program": 52, "vol": 80, "pan": 76, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Tenor II", "instrument_id": "voice.tenor", "system_name": "Tenors", "program": 52, "vol": 80, "pan": 92, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Bass II", "instrument_id": "voice.bass", "system_name": "Basses", "program": 52, "vol": 80, "pan": 108, "octave": 0}
        ]
    },
    {
        "id": "006_-_Octeto_Coral_Espalhado",
        "name": "Octeto de Coral Espalhado",
        "size": 8,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Soprano I", "instrument_id": "voice.soprano", "system_name": "Sopranos", "program": 52, "vol": 80, "pan": 30, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Soprano II", "instrument_id": "voice.soprano", "system_name": "Sopranos", "program": 52, "vol": 75, "pan": 42, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Alto I", "instrument_id": "voice.alto", "system_name": "Altos", "program": 52, "vol": 80, "pan": 54, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Alto II", "instrument_id": "voice.alto", "system_name": "Altos", "program": 52, "vol": 80, "pan": 66, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Tenor I", "instrument_id": "voice.tenor", "system_name": "Tenors", "program": 52, "vol": 80, "pan": 78, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Tenor II", "instrument_id": "voice.tenor", "system_name": "Tenors", "program": 52, "vol": 80, "pan": 90, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Bass I", "instrument_id": "voice.bass", "system_name": "Basses", "program": 52, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Bass II", "instrument_id": "voice.bass", "system_name": "Basses", "program": 52, "vol": 80, "pan": 98, "octave": 0}
        ]
    },
    {
        "id": "007_-_Octeto_Coral_Soprano_Oitavado",
        "name": "Octeto de Coral com Soprano Oitavado (Soprano 2 8ve)",
        "size": 8,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Soprano I", "instrument_id": "voice.soprano", "system_name": "Sopranos", "program": 52, "vol": 80, "pan": 30, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Soprano II (8ve)", "instrument_id": "voice.soprano", "system_name": "Sopranos", "program": 52, "vol": 70, "pan": 42, "octave": 12},
            {"voice": "Contralto", "instrument_name": "Alto I", "instrument_id": "voice.alto", "system_name": "Altos", "program": 52, "vol": 80, "pan": 54, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Alto II", "instrument_id": "voice.alto", "system_name": "Altos", "program": 52, "vol": 80, "pan": 66, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Tenor I", "instrument_id": "voice.tenor", "system_name": "Tenors", "program": 52, "vol": 80, "pan": 78, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Tenor II", "instrument_id": "voice.tenor", "system_name": "Tenors", "program": 52, "vol": 80, "pan": 90, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Bass I", "instrument_id": "voice.bass", "system_name": "Basses", "program": 52, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Bass II", "instrument_id": "voice.bass", "system_name": "Basses", "program": 52, "vol": 80, "pan": 98, "octave": 0}
        ]
    },
    {
        "id": "008_-_Octeto_Coral_Tenor_Oitavado",
        "name": "Octeto de Coral com Tenor Oitavado (Tenor 2 8ve)",
        "size": 8,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Soprano I", "instrument_id": "voice.soprano", "system_name": "Sopranos", "program": 52, "vol": 80, "pan": 30, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Soprano II", "instrument_id": "voice.soprano", "system_name": "Sopranos", "program": 52, "vol": 80, "pan": 42, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Alto I", "instrument_id": "voice.alto", "system_name": "Altos", "program": 52, "vol": 80, "pan": 54, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Alto II", "instrument_id": "voice.alto", "system_name": "Altos", "program": 52, "vol": 80, "pan": 66, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Tenor I", "instrument_id": "voice.tenor", "system_name": "Tenors", "program": 52, "vol": 80, "pan": 78, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Tenor II (8ve)", "instrument_id": "voice.tenor", "system_name": "Tenors", "program": 52, "vol": 70, "pan": 90, "octave": 12},
            {"voice": "Baixo",     "instrument_name": "Bass I", "instrument_id": "voice.bass", "system_name": "Basses", "program": 52, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Bass II", "instrument_id": "voice.bass", "system_name": "Basses", "program": 52, "vol": 80, "pan": 98, "octave": 0}
        ]
    },
    # ─── 12 VOZES (GRANDE CORAL) ─────────────────────────────────────────────
    {
        "id": "009_-_Grande_Coral_12Part",
        "name": "Grande Coral de 12 Partes",
        "size": 12,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Soprano I-1", "instrument_id": "voice.soprano", "system_name": "Sopranos", "program": 52, "vol": 85, "pan": 16, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Soprano I-2", "instrument_id": "voice.soprano", "system_name": "Sopranos", "program": 52, "vol": 85, "pan": 28, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Soprano I-3", "instrument_id": "voice.soprano", "system_name": "Sopranos", "program": 52, "vol": 80, "pan": 40, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Alto I-1", "instrument_id": "voice.alto", "system_name": "Altos", "program": 52, "vol": 80, "pan": 52, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Alto I-2", "instrument_id": "voice.alto", "system_name": "Altos", "program": 52, "vol": 80, "pan": 64, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Alto I-3", "instrument_id": "voice.alto", "system_name": "Altos", "program": 52, "vol": 80, "pan": 76, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Tenor I-1", "instrument_id": "voice.tenor", "system_name": "Tenors", "program": 52, "vol": 80, "pan": 88, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Tenor I-2", "instrument_id": "voice.tenor", "system_name": "Tenors", "program": 52, "vol": 80, "pan": 100, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Tenor I-3", "instrument_id": "voice.tenor", "system_name": "Tenors", "program": 52, "vol": 75, "pan": 64, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Bass I-1", "instrument_id": "voice.bass", "system_name": "Basses", "program": 52, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Bass I-2", "instrument_id": "voice.bass", "system_name": "Basses", "program": 52, "vol": 85, "pan": 120, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Bass I-3", "instrument_id": "voice.bass", "system_name": "Basses", "program": 52, "vol": 80, "pan": 52, "octave": 0}
        ]
    },
    {
        "id": "010_-_Grande_Coral_12Part_Oitavado",
        "name": "Grande Coral de 12 Partes com Oitavações (Soprano & Tenor 8ve)",
        "size": 12,
        "tracks": [
            {"voice": "Soprano",   "instrument_name": "Soprano I-1", "instrument_id": "voice.soprano", "system_name": "Sopranos", "program": 52, "vol": 85, "pan": 16, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Soprano I-2", "instrument_id": "voice.soprano", "system_name": "Sopranos", "program": 52, "vol": 80, "pan": 28, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Soprano I-3 (8ve)", "instrument_id": "voice.soprano", "system_name": "Sopranos", "program": 52, "vol": 70, "pan": 40, "octave": 12},
            {"voice": "Contralto", "instrument_name": "Alto I-1", "instrument_id": "voice.alto", "system_name": "Altos", "program": 52, "vol": 80, "pan": 52, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Alto I-2", "instrument_id": "voice.alto", "system_name": "Altos", "program": 52, "vol": 80, "pan": 64, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Alto I-3", "instrument_id": "voice.alto", "system_name": "Altos", "program": 52, "vol": 80, "pan": 76, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Tenor I-1", "instrument_id": "voice.tenor", "system_name": "Tenors", "program": 52, "vol": 80, "pan": 88, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Tenor I-2", "instrument_id": "voice.tenor", "system_name": "Tenors", "program": 52, "vol": 80, "pan": 100, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Tenor I-3 (8ve)", "instrument_id": "voice.tenor", "system_name": "Tenors", "program": 52, "vol": 70, "pan": 64, "octave": 12},
            {"voice": "Baixo",     "instrument_name": "Bass I-1", "instrument_id": "voice.bass", "system_name": "Basses", "program": 52, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Bass I-2", "instrument_id": "voice.bass", "system_name": "Basses", "program": 52, "vol": 85, "pan": 120, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Bass I-3", "instrument_id": "voice.bass", "system_name": "Basses", "program": 52, "vol": 80, "pan": 52, "octave": 0}
        ]
    },
    # ─── 16 VOZES (GRANDES CORAIS / DUPLO OCTETO) ────────────────────────────
    {
        "id": "011_-_Grande_Coral_16Part",
        "name": "Grande Coral de 16 Partes",
        "size": 16,
        "tracks": [
            # Soprano (4 Sopranos)
            {"voice": "Soprano",   "instrument_name": "Soprano I-1", "instrument_id": "voice.soprano", "system_name": "Sopranos", "program": 52, "vol": 85, "pan": 20, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Soprano I-2", "instrument_id": "voice.soprano", "system_name": "Sopranos", "program": 52, "vol": 85, "pan": 36, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Soprano I-3", "instrument_id": "voice.soprano", "system_name": "Sopranos", "program": 52, "vol": 80, "pan": 52, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Soprano I-4", "instrument_id": "voice.soprano", "system_name": "Sopranos", "program": 52, "vol": 80, "pan": 68, "octave": 0},
            # Contralto (4 Altos)
            {"voice": "Contralto", "instrument_name": "Alto I-1", "instrument_id": "voice.alto", "system_name": "Altos", "program": 52, "vol": 80, "pan": 40, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Alto I-2", "instrument_id": "voice.alto", "system_name": "Altos", "program": 52, "vol": 80, "pan": 56, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Alto I-3", "instrument_id": "voice.alto", "system_name": "Altos", "program": 52, "vol": 80, "pan": 72, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Alto I-4", "instrument_id": "voice.alto", "system_name": "Altos", "program": 52, "vol": 75, "pan": 88, "octave": 0},
            # Tenor (4 Tenors)
            {"voice": "Tenor",     "instrument_name": "Tenor I-1", "instrument_id": "voice.tenor", "system_name": "Tenors", "program": 52, "vol": 80, "pan": 48, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Tenor I-2", "instrument_id": "voice.tenor", "system_name": "Tenors", "program": 52, "vol": 80, "pan": 64, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Tenor I-3", "instrument_id": "voice.tenor", "system_name": "Tenors", "program": 52, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Tenor I-4", "instrument_id": "voice.tenor", "system_name": "Tenors", "program": 52, "vol": 75, "pan": 96, "octave": 0},
            # Baixo (4 Basses)
            {"voice": "Baixo",     "instrument_name": "Bass I-1", "instrument_id": "voice.bass", "system_name": "Basses", "program": 52, "vol": 80, "pan": 60, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Bass I-2", "instrument_id": "voice.bass", "system_name": "Basses", "program": 52, "vol": 85, "pan": 100, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Bass I-3", "instrument_id": "voice.bass", "system_name": "Basses", "program": 52, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Bass I-4", "instrument_id": "voice.bass", "system_name": "Basses", "program": 52, "vol": 85, "pan": 120, "octave": 0}
        ]
    },
    {
        "id": "012_-_Grande_Coro_16Part_Oitavado",
        "name": "Grande Coral de 16 Partes com Soprano e Tenor Oitavados",
        "size": 16,
        "tracks": [
            # Soprano (4 Sopranos)
            {"voice": "Soprano",   "instrument_name": "Soprano I-1", "instrument_id": "voice.soprano", "system_name": "Sopranos", "program": 52, "vol": 85, "pan": 20, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Soprano I-2", "instrument_id": "voice.soprano", "system_name": "Sopranos", "program": 52, "vol": 85, "pan": 36, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Soprano I-3", "instrument_id": "voice.soprano", "system_name": "Sopranos", "program": 52, "vol": 80, "pan": 52, "octave": 0},
            {"voice": "Soprano",   "instrument_name": "Soprano I-4 (8ve)", "instrument_id": "voice.soprano", "system_name": "Sopranos", "program": 52, "vol": 70, "pan": 68, "octave": 12},
            # Contralto (4 Altos)
            {"voice": "Contralto", "instrument_name": "Alto I-1", "instrument_id": "voice.alto", "system_name": "Altos", "program": 52, "vol": 80, "pan": 40, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Alto I-2", "instrument_id": "voice.alto", "system_name": "Altos", "program": 52, "vol": 80, "pan": 56, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Alto I-3", "instrument_id": "voice.alto", "system_name": "Altos", "program": 52, "vol": 80, "pan": 72, "octave": 0},
            {"voice": "Contralto", "instrument_name": "Alto I-4", "instrument_id": "voice.alto", "system_name": "Altos", "program": 52, "vol": 75, "pan": 88, "octave": 0},
            # Tenor (4 Tenors)
            {"voice": "Tenor",     "instrument_name": "Tenor I-1", "instrument_id": "voice.tenor", "system_name": "Tenors", "program": 52, "vol": 80, "pan": 48, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Tenor I-2", "instrument_id": "voice.tenor", "system_name": "Tenors", "program": 52, "vol": 80, "pan": 64, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Tenor I-3", "instrument_id": "voice.tenor", "system_name": "Tenors", "program": 52, "vol": 80, "pan": 80, "octave": 0},
            {"voice": "Tenor",     "instrument_name": "Tenor I-4 (8ve)", "instrument_id": "voice.tenor", "system_name": "Tenors", "program": 52, "vol": 70, "pan": 96, "octave": 12},
            # Baixo (4 Basses)
            {"voice": "Baixo",     "instrument_name": "Bass I-1", "instrument_id": "voice.bass", "system_name": "Basses", "program": 52, "vol": 80, "pan": 60, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Bass I-2", "instrument_id": "voice.bass", "system_name": "Basses", "program": 52, "vol": 85, "pan": 100, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Bass I-3", "instrument_id": "voice.bass", "system_name": "Basses", "program": 52, "vol": 85, "pan": 112, "octave": 0},
            {"voice": "Baixo",     "instrument_name": "Bass I-4", "instrument_id": "voice.bass", "system_name": "Basses", "program": 52, "vol": 85, "pan": 120, "octave": 0}
        ]
    }
]

GROUPS = {
    "strings": {"combinations": COMBINATIONS_STRINGS, "folder": "Strings", "name": "Cordas (Strings)"},
    "brass":   {"combinations": COMBINATIONS_BRASS,   "folder": "Brass",   "name": "Metais (Brass)"},
    "paletas": {"combinations": COMBINATIONS_PALETAS, "folder": "Paletas", "name": "Paletas (Sax/Clarinetes)"},
    "sopros":  {"combinations": COMBINATIONS_SOPROS,  "folder": "Sopros",  "name": "Sopros (Woodwinds)"},
    "coral":   {"combinations": COMBINATIONS_CORAL,   "folder": "Coral",   "name": "Coral (Muse Choir)"}
}

# ─────────────────────────────────────────────────────────────────────────────
# AUXILIAR MIDI & PROCESSAMENTO
# ─────────────────────────────────────────────────────────────────────────────

def get_tempo(mid):
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'set_tempo':
                return msg.tempo
    return 500_000

def detect_satb_channels(mid):
    pitch_sum, pitch_cnt = {}, {}
    for track in mid.tracks:
        for msg in track:
            if msg.is_meta or not hasattr(msg, 'channel'):
                continue
            if msg.type == 'note_on' and msg.velocity > 0:
                ch = msg.channel
                pitch_sum[ch] = pitch_sum.get(ch, 0) + msg.note
                pitch_cnt[ch] = pitch_cnt.get(ch, 0) + 1
    if not pitch_sum:
        return {}
    avg = {ch: pitch_sum[ch] / pitch_cnt[ch] for ch in pitch_sum}
    sorted_chs = sorted(avg, key=lambda c: avg[c], reverse=True)
    voices = ["Soprano", "Contralto", "Tenor", "Baixo"]
    return {sorted_chs[i]: voices[i] for i in range(min(len(sorted_chs), len(voices)))}

def seconds_to_ticks(sec, tempo, tpb):
    return int(sec * 1_000_000 * tpb / tempo)

def extract_phrase_notes(mid, ph_start, ph_end):
    ch_to_voice = detect_satb_channels(mid)
    voice_notes = {}
    for track in mid.tracks:
        active = {}
        curr = 0
        for msg in track:
            curr += msg.time
            if msg.is_meta or not hasattr(msg, 'channel'):
                continue
            ch = msg.channel
            if ch not in ch_to_voice:
                continue
            voice = ch_to_voice[ch]
            if msg.type == 'note_on' and msg.velocity > 0:
                active.setdefault(ch, {})[msg.note] = (curr, msg.velocity)
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                if ch in active and msg.note in active.get(ch, {}):
                    on_t, vel = active[ch].pop(msg.note)
                    if ph_start <= on_t < ph_end:
                        voice_notes.setdefault(voice, []).append((msg.note, on_t, curr, vel))
    for v in voice_notes:
        voice_notes[v].sort(key=lambda x: x[1])
    return voice_notes

def build_combo_midi(mid, voice_notes, config, speed=0.55, phrase_start=0):
    tempo_orig = get_tempo(mid)
    tempo_new  = int(tempo_orig / speed)
    tpb        = mid.ticks_per_beat

    new_mid = mido.MidiFile()
    new_mid.ticks_per_beat = tpb
    meta = mido.MidiTrack()
    new_mid.tracks.append(meta)
    for track in mid.tracks:
        for msg in track:
            if msg.is_meta and msg.type in ['time_signature', 'key_signature']:
                meta.append(msg.copy())
    meta.append(mido.MetaMessage('set_tempo', tempo=tempo_new, time=0))

    all_events = []
    channel_pan_map = {}
    ordered_pans = []
    ordered_vols = []

    # Delays micro-temporais removidos (timing offset = 0)
    voice_delays = {"Soprano": 0.0, "Contralto": 0.0, "Tenor": 0.0, "Baixo": 0.0}

    for ch_idx, track_conf in enumerate(config["tracks"]):
        voice_spec = track_conf["voice"]
        if isinstance(voice_spec, list):
            voice_list = voice_spec
        else:
            voice_list = [voice_spec]

        midi_ch = MELODIC_CHANNELS[ch_idx % len(MELODIC_CHANNELS)]
        pan = track_conf["pan"]
        vol = track_conf["vol"]
        octave_shift = track_conf["octave"]

        channel_pan_map[midi_ch] = pan
        ordered_pans.append(pan)
        ordered_vols.append(vol)

        all_events += [
            mido.Message('program_change', channel=midi_ch, program=track_conf["program"], time=0),
            mido.Message('control_change', channel=midi_ch, control=10, value=pan,  time=0),
            mido.Message('control_change', channel=midi_ch, control=7,  value=min(127, max(0, vol)),  time=0),
            mido.Message('control_change', channel=midi_ch, control=11, value=127,  time=0),
        ]

        # Parâmetros de ataque pós-pausa escalados pelo volume da track
        vol_ratio     = vol / 85.0
        attack_vel    = max(1, int(10 * vol_ratio))
        cc11_start    = max(5, int(40 * vol_ratio))
        cc11_max      = max(10, int(100 * vol_ratio))

        for v_name in voice_list:
            notes = voice_notes.get(v_name, [])
            if not notes:
                continue

            delay_ticks = seconds_to_ticks(voice_delays.get(v_name, 0.0), tempo_new, tpb)

            for i, (note, on_t, off_t, vel) in enumerate(notes):
                dur = remove_staccato(off_t - on_t, tpb)
                is_after_pause  = (i == 0) or (on_t - notes[i-1][2] >= tpb * 0.25)
                is_before_pause = (i < len(notes)-1) and (notes[i+1][1] - off_t >= tpb * 0.25)
                if is_before_pause:
                    dur = int(dur * 0.70)
                on_new  = (on_t - phrase_start) + delay_ticks
                off_new = on_new + max(15, dur)
                
                next_start = None
                for nj in notes[i+1:]:
                    if nj[1] > on_t:
                        next_start = (nj[1] - phrase_start) + delay_ticks
                        break
                if next_start is not None and off_new > next_start:
                    off_new = max(on_new + 5, next_start)
                    
                scaled_vel = min(127, max(1, int(vel * vol_ratio)))
                v_note     = min(attack_vel, scaled_vel) if is_after_pause else scaled_vel
                v_note     = min(127, max(1, v_note))
                final_note = min(127, max(0, note + octave_shift))

                all_events.append(mido.Message('note_on',  channel=midi_ch, note=final_note,
                                               velocity=v_note, time=on_new))
                all_events.append(mido.Message('note_off', channel=midi_ch, note=final_note,
                                               velocity=0, time=off_new))
                if is_after_pause:
                    # Rampa CC11 de cc11_start a cc11_max ao longo de 225ms
                    ramp = seconds_to_ticks(0.225, tempo_new, tpb)
                    for step in range(5):
                        t_cc = on_new + int((step / 4) * ramp)
                        cc_val = max(0, min(127, int(cc11_start + (step / 4) * (cc11_max - cc11_start))))
                        all_events.append(mido.Message('control_change', channel=midi_ch,
                                                        control=11, value=cc_val, time=t_cc))

    setup = [m for m in all_events if m.time == 0]
    music = sorted([m for m in all_events if m.time > 0], key=lambda m: m.time)
    note_track = mido.MidiTrack()
    new_mid.tracks.append(note_track)
    prev = 0
    for msg in setup + music:
        note_track.append(msg.copy(time=msg.time - prev))
        prev = msg.time
    channel_pan_map['ordered_pans'] = ordered_pans
    channel_pan_map['ordered_vols'] = ordered_vols
    return new_mid, channel_pan_map

def normalize_mp3(mp3_path: Path):
    tmp = mp3_path.with_suffix(".tmp.mp3")
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", str(mp3_path),
         "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
         "-c:a", "libmp3lame", "-q:a", "2", str(tmp)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    if r.returncode == 0 and tmp.exists():
        tmp.replace(mp3_path)

def clean_runtime_files(directory: Path):
    for f in ["automation.json", "audiosettings.json", "viewsettings.json"]:
        f_p = directory / f
        if f_p.exists():
            try: f_p.unlink()
            except OSError: pass
    for d in ["META-INF", "Thumbnails"]:
        d_p = directory / d
        if d_p.exists() and d_p.is_dir():
            try: shutil.rmtree(d_p)
            except OSError: pass

# ─────────────────────────────────────────────────────────────────────────────
# LOOP PRINCIPAL DE GERAÇÃO
# ─────────────────────────────────────────────────────────────────────────────

def process_group(group_key, mid, voice_notes, speed, ph_start, ph_end, tempo, bpm_target):
    info = GROUPS[group_key]
    output_dir = ROOT / "output" / "biblioteca-de-tombres-2" / info["folder"]
    
    if output_dir.exists():
        shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n========================================================")
    print(f"Gerando biblioteca: {info['name']}")
    print(f"Saída: {output_dir}")
    print(f"========================================================")

    combinations = info["combinations"]
    catalog = [
        f"# Catálogo de Timbres - {info['name']}\n\n",
        f"**Referência:** `{ROOT.name}`, Frase 1 (ticks {ph_start} a {ph_end})\n\n",
        "| ID | Orquestra | Tamanho | Detalhe das Tracks | MP3 | MSCZ |\n",
        "|---|---|---|---|---|---|\n",
    ]

    for idx, config in enumerate(combinations, 1):
        fn = config["id"]
        
        midi_tmp = output_dir / f"_tmp_{idx:03d}.mid"
        mscz_out = output_dir / f"{fn}.mscz"
        mp3_out  = output_dir / f"{fn}.mp3"
        raw_mp3  = output_dir / f"_tmp_{idx:03d}.mp3"

        tracks_desc_list = []
        for t in config["tracks"]:
            oct_str = f" (+12)" if t["octave"] == 12 else (f" (-12)" if t["octave"] == -12 else "")
            tracks_desc_list.append(f"{t['voice']}: {t['instrument_name']}{oct_str} (vol={t['vol']} pan={t['pan']})")
        tracks_desc = "<br>".join(tracks_desc_list)

        print(f"[{idx}/{len(combinations)}] Gerando: {config['name']} ({config['size']} partes)...")

        # Gera o MIDI temporário humanizado
        new_mid, ch_pan_map = build_combo_midi(mid, voice_notes, config, speed=speed, phrase_start=ph_start)
        new_mid.save(str(midi_tmp))

        # Conversão e patch no MSCZ e renderização do MP3 temporário
        try:
            # 1. MIDI -> MSCZ
            res1 = subprocess.run([MSCORE_BIN, "-o", str(mscz_out), str(midi_tmp)],
                                  capture_output=True, text=True)
            if res1.returncode != 0:
                print(f"  [Erro MIDI->MSCZ] code={res1.returncode}\nstdout: {res1.stdout}\nstderr: {res1.stderr}")

            if mscz_out.exists():
                # 2. Patch MSCZ
                remove_staccato_from_mscz(mscz_out)
                set_tempo_in_mscz(mscz_out, bpm_target)
                set_pan_in_mscz(mscz_out, ch_pan_map)
                build_and_inject_audiosettings_pan(mscz_out, ch_pan_map)

                # 3. MSCZ -> MP3 temporário
                res2 = subprocess.run([MSCORE_BIN, "-o", str(raw_mp3), str(mscz_out)],
                                      capture_output=True, text=True)
                if res2.returncode != 0:
                    print(f"  [Erro MSCZ->MP3] code={res2.returncode}\nstdout: {res2.stdout}\nstderr: {res2.stderr}")
        except Exception as e:
            print(f"  [EXCEÇÃO] {e}")
        finally:
            if midi_tmp.exists():
                midi_tmp.unlink()
            clean_runtime_files(output_dir)

        # 4. Pós-processamento de fade-in de 200ms no MP3 final se gerado com sucesso
        if raw_mp3.exists():
            subprocess.run([
                sys.executable, str(ROOT / "utils" / "postprocess_fade_apos_pausa.py"),
                "--input", str(raw_mp3),
                "--output", str(output_dir),
                "--suffix", "",
                "--lookback-ms", "200",
                "--include-start"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Renomeia para o arquivo MP3 definitivo
            if raw_mp3.exists():
                raw_mp3.rename(mp3_out)
                
            normalize_mp3(mp3_out)
            print(f"  ✓ Concluído com sucesso!")
        else:
            print(f"  ❌ Erro ao renderizar MP3 para {fn}")

        catalog.append(f"| `{idx:03d}` | {config['name']} | {config['size']} | {tracks_desc} | [MP3]({fn}.mp3) | [MSCZ]({fn}.mscz) |\n")

    # Salva o catálogo
    (output_dir / "catalogo.md").write_text("".join(catalog), encoding='utf-8')
    print(f"✓ Catálogo salvo em: {output_dir / 'catalogo.md'}")

def main():
    parser = argparse.ArgumentParser(description="Gera bibliotecas de timbres para orquestras de nicho.")
    parser.add_argument("--group", choices=["strings", "brass", "paletas", "sopros", "coral", "all"], default="all",
                        help="Família de instrumentos a gerar (default: all)")
    args = parser.parse_args()

    midi_ref = ROOT / "mid" / "Coro 002- Toda a glória a Jesus.mid"
    print(f"Lendo midi de referência: {midi_ref.name}")
    mid = mido.MidiFile(midi_ref)
    tempo = get_tempo(mid)
    
    # Frase 1 (primeira linha do Coro, ticks 4320 a 12240)
    ph_start, ph_end = 4320, 12240
    voice_notes = extract_phrase_notes(mid, ph_start, ph_end)

    bpm_target = 60.0
    bpm_orig = int(60_000_000 / tempo)
    speed = bpm_target / bpm_orig

    to_process = GROUPS.keys() if args.group == "all" else [args.group]
    
    for g in to_process:
        process_group(g, mid, voice_notes, speed, ph_start, ph_end, tempo, bpm_target)

if __name__ == "__main__":
    main()
