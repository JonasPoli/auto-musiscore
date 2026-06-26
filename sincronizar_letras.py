#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sincronizar_letras.py — Sincronizador inteligente de letras para hinos (MIDI + MP3 + TXT -> JSON).

Uso:
  python sincronizar_letras.py --hino 5 --mp3 output_strings_test/005_orquestra.mp3 --output output/hino-005.json
  python sincronizar_letras.py --midi mid/001-Cristo.mid --mp3 output/001.mp3 --txt hinos_txt/letras_separadas/hino-001.txt --output output/hino-001.json
"""

import os
import re
import csv
import sys
import json
import argparse
import subprocess
import time
import numpy as np
import pretty_midi
from pathlib import Path

ROOT = Path(__file__).parent.absolute()
LETRAS_DIR = ROOT / "hinos_txt" / "letras_separadas"
MIDI_DIR = ROOT / "mid"

# ==============================================================================
# 1. PARSER DE LETRAS (TXT)
# ==============================================================================

def text_is_content(text):
    if not text:
        return False
    if re.match(r"^[\d\s\-\.]+$", text):
        return False
    return True

def carregar_letra_hino(hino_id, txt_path: Path = None) -> dict:
    """
    Carrega a letra do hino e estrutura em versos e coro.
    """
    if txt_path is None:
        indice_path = LETRAS_DIR / "_indice.csv"
        if not indice_path.exists():
            raise FileNotFoundError(f"[erro] _indice.csv não encontrado em {LETRAS_DIR}")

        hino_id_str = str(hino_id).strip()
        is_coro = hino_id_str.upper().startswith("C")
        if is_coro:
            tipo_busca = "coro"
            num_busca = int(hino_id_str[1:])
        else:
            tipo_busca = "hino"
            num_busca = int(hino_id_str)

        arquivo = None
        with open(indice_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                tipo_csv = row.get("tipo", "").strip().lower()
                try:
                    num_csv = int(row.get("numero", "").strip())
                except (ValueError, AttributeError):
                    continue
                if tipo_csv == tipo_busca and num_csv == num_busca:
                    arquivo = row.get("arquivo", "").strip()
                    break

        if not arquivo:
            raise ValueError(f"[erro] {tipo_busca.capitalize()} {num_busca} não encontrado no _indice.csv")

        txt_path = LETRAS_DIR / arquivo

    if not txt_path.exists():
        raise FileNotFoundError(f"[erro] Arquivo de letra {txt_path} não existe.")

    linhas = txt_path.read_text(encoding="utf-8").splitlines()
    if not linhas:
        raise ValueError("[erro] Arquivo de letra está vazio.")

    # Primeira linha é o título
    titulo = linhas[0].strip()
    if "hino" in titulo.lower() or "coro" in titulo.lower():
        titulo = re.sub(r"^(hino|coro)\s+\d+\s*-\s*", "", titulo, flags=re.IGNORECASE)

    verses = []
    chorus = None
    estrofe_atual = []
    is_coro_atual = False

    for i in range(1, len(linhas)):
        linha = linhas[i].strip()
        if not text_is_content(linha):
            if estrofe_atual:
                if is_coro_atual:
                    chorus = estrofe_atual
                else:
                    verses.append(estrofe_atual)
                estrofe_atual = []
                is_coro_atual = False
            continue

        coro_match = re.match(r"^coro\b:?\s*(.*)$", linha, flags=re.IGNORECASE)
        if coro_match:
            is_coro_atual = True
            resto = coro_match.group(1).strip()
            if resto:
                estrofe_atual.append(resto)
            continue
        
        linha_limpa = re.sub(r"^\d+\.\s*", "", linha).strip()
        if linha_limpa:
            estrofe_atual.append(linha_limpa)

    if estrofe_atual:
        if is_coro_atual:
            chorus = estrofe_atual
        else:
            verses.append(estrofe_atual)

    return {
        'titulo': titulo,
        'verses': verses,
        'chorus': chorus
    }

# ==============================================================================
# 2. ANALISADOR MIDI E DETECÇÃO DE INTRODUÇÃO
# ==============================================================================

def find_melody_track(pm):
    best_inst = None
    max_avg_pitch = 0
    for inst in pm.instruments:
        if inst.is_drum or len(inst.notes) < 20:
            continue
        avg_pitch = sum(n.pitch for n in inst.notes) / len(inst.notes)
        if avg_pitch > max_avg_pitch:
            max_avg_pitch = avg_pitch
            best_inst = inst
    return best_inst

def detectar_introducao(notes):
    """
    Busca N notes correspondentes à introdução (repetição exata de pitches do início do hino).
    Retorna o número de notas N e o tempo (segundos no MIDI) de fim da introdução.
    """
    pitches = [n.pitch for n in notes]
    # Tenta casamento exato
    for N in range(5, len(pitches) // 2):
        if pitches[0:N] == pitches[N:2*N]:
            return N, notes[N-1].end

    # Fallback se não encontrar casamento exato (ex: pequena diferença de articulação/divisão)
    # Busca por menor distância de Hamming relativa
    best_N = None
    min_dist = 9999
    for N in range(8, min(40, len(pitches) // 2)):
        p1 = pitches[0:N]
        p2 = pitches[N:2*N]
        dist = sum(1 for a, b in zip(p1, p2) if a != b)
        rel_dist = dist / N
        if rel_dist < 0.15 and dist < min_dist:
            min_dist = dist
            best_N = N

    if best_N is not None:
        return best_N, notes[best_N-1].end

    # Fallback absoluto: busca a primeira pausa longa (gap > 1.5s nos primeiros 20 segundos)
    for i in range(1, len(notes)):
        gap = notes[i].start - notes[i-1].end
        if gap > 1.5 and notes[i-1].end < 25.0:
            return i, notes[i-1].end

    # Fallback final: estima que a introdução é de 15 segundos ou 15 notas
    idx = min(15, len(notes) - 1)
    return idx, notes[idx-1].end

# ==============================================================================
# 3. ESTIMADOR DE VELOCIDADE (ALINHAMENTO MP3/MIDI VIA ENVELOPE)
# ==============================================================================

def load_audio_pcm(mp3_path, sr=16000):
    cmd = [
        'ffmpeg', '-y', '-i', str(mp3_path),
        '-f', 'f32le', '-acodec', 'pcm_f32le', '-ar', str(sr), '-ac', '1', '-'
    ]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    stdout, _ = process.communicate()
    if process.returncode != 0 and (not stdout):
        raise RuntimeError(f"FFmpeg falhou ao decodificar {mp3_path}")
    return np.frombuffer(stdout, dtype=np.float32)

def compute_onset_strength(audio, sr=16000, frame_size=1024, hop_size=256):
    n_frames = (len(audio) - frame_size) // hop_size
    if n_frames <= 0:
        return np.array([0.0]), np.array([0.0])
    
    shape = (n_frames, frame_size)
    strides = (audio.strides[0] * hop_size, audio.strides[0])
    windows = np.lib.stride_tricks.as_strided(audio, shape=shape, strides=strides)
    
    energy = np.sum(windows**2, axis=1)
    log_energy = np.log1p(1000.0 * energy)
    diff = np.diff(log_energy)
    onset_strength = np.maximum(0.0, diff)
    
    frame_times = (np.arange(len(onset_strength)) + 1) * hop_size / sr
    return frame_times, onset_strength

def estimar_speed_scale(midi_onsets, mp3_path):
    """
    Compara o padrão de onsets do MIDI com o envelope de energia do MP3
    para encontrar a escala de velocidade real (alpha).
    """
    try:
        audio = load_audio_pcm(mp3_path)
    except Exception as e:
        print(f"  [aviso] Falha ao ler áudio via FFmpeg: {e}. Usando speed_scale padrão = 1.0")
        return 1.0
        
    frame_times, onset_strength = compute_onset_strength(audio)
    if len(onset_strength) <= 1:
        return 1.0

    # Grid search para alpha (fator multiplicador de tempo)
    # Procuramos de 0.70 (30% mais rápido) a 1.45 (45% mais lento) com passo fino
    alphas = np.arange(0.70, 1.45, 0.0005)
    best_alpha = 1.0
    best_score = -1.0

    for alpha in alphas:
        mapped_times = midi_onsets * alpha
        scores = np.interp(mapped_times, frame_times, onset_strength)
        score = np.sum(scores)
        if score > best_score:
            best_score = score
            best_alpha = alpha

    return best_alpha

# ==============================================================================
# 4. MAPEADOR E SEGMENTADOR DE FRASES
# ==============================================================================

def process_lines_timing(notes_segment, lines, alpha):
    L = len(lines)
    P = len(notes_segment)
    char_counts = [len(l) for l in lines]
    C_total = sum(char_counts)
    
    boundaries = [0]
    for j in range(1, L):
        expected_b = int(P * sum(char_counts[:j]) / C_total)
        best_b = expected_b
        max_gap = -1.0
        
        search_min = max(boundaries[-1] + 1, expected_b - 5)
        search_max = min(P - (L - j), expected_b + 5)
        
        for idx in range(search_min, search_max + 1):
            gap = notes_segment[idx].start - notes_segment[idx-1].end
            score = gap - 0.02 * abs(idx - expected_b)
            if score > max_gap:
                max_gap = score
                best_b = idx
        boundaries.append(best_b)
    boundaries.append(P)
    
    line_timings = []
    for j in range(L):
        start_note = notes_segment[boundaries[j]]
        end_note = notes_segment[boundaries[j+1] - 1]
        
        t_start = start_note.start * alpha
        t_end = end_note.end * alpha
        
        if boundaries[j+1] < P:
            next_start = notes_segment[boundaries[j+1]].start * alpha
            t_end = min(t_end + 0.5, next_start - 0.05)
        else:
            t_end = t_end + 0.5
            
        line_timings.append({
            "texto": lines[j],
            "inicio": round(t_start, 3),
            "fim": round(t_end, 3),
            "num_linha": j + 1
        })
    return line_timings

def mapear_letra_para_notes(letra: dict, notes: list, intro_notes_count: int, alpha: float) -> list:
    singing_notes = notes[intro_notes_count:]
    verses = letra['verses']
    chorus = letra['chorus']
    
    total_blocks = len(verses)
    notes_per_block = len(singing_notes) // total_blocks
    
    aligned_lines = []
    current_note_idx = 0

    for block_idx in range(total_blocks):
        block_notes = singing_notes[current_note_idx : current_note_idx + notes_per_block]
        current_note_idx += notes_per_block

        if chorus:
            # Dividir o bloco em Verso e Coro
            char_count_v = sum(len(l) for l in verses[block_idx])
            char_count_c = sum(len(l) for l in chorus)
            f = char_count_v / (char_count_v + char_count_c)
            expected_n_v = int(len(block_notes) * f)

            best_split = expected_n_v
            max_gap = -1.0
            search_min = max(5, expected_n_v - 10)
            search_max = min(len(block_notes) - 5, expected_n_v + 10)

            for i in range(search_min, search_max):
                gap = block_notes[i].start - block_notes[i-1].end
                score = gap - 0.02 * abs(i - expected_n_v)
                if score > max_gap:
                    max_gap = score
                    best_split = i

            v_notes = block_notes[:best_split]
            c_notes = block_notes[best_split:]

            # Adicionar tempos do Verso
            v_timings = process_lines_timing(v_notes, verses[block_idx], alpha)
            for item in v_timings:
                item["tipo"] = "verso"
                item["num_verso"] = block_idx + 1
                aligned_lines.append(item)

            # Adicionar tempos do Coro
            c_timings = process_lines_timing(c_notes, chorus, alpha)
            for item in c_timings:
                item["tipo"] = "coro"
                item["num_verso"] = block_idx + 1
                aligned_lines.append(item)
        else:
            # Sem coro
            v_timings = process_lines_timing(block_notes, verses[block_idx], alpha)
            for item in v_timings:
                item["tipo"] = "verso"
                item["num_verso"] = block_idx + 1
                aligned_lines.append(item)

    return aligned_lines

# ==============================================================================
# 5. CLI E FLUXO PRINCIPAL
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Sincronizador Automático de Letras de Hinos.")
    parser.add_argument("--hino", type=str, help="Número do hino/coro (ex: 26 ou C1) a processar")
    parser.add_argument("--midi", help="Caminho explícito para o arquivo MIDI original")
    parser.add_argument("--mp3", required=True, help="Caminho para o arquivo MP3 gerado (orquestra)")
    parser.add_argument("--txt", help="Caminho explícito para o TXT da letra")
    parser.add_argument("--output", required=True, help="Caminho para salvar o JSON de saída")
    parser.add_argument("--skip-existing", action="store_true", help="Pular processamento se o arquivo de saída já existir")
    args = parser.parse_args()

    # Se skip-existing estiver ativo e o arquivo de saída já existir, pula imediatamente
    output_path = Path(args.output)
    if args.skip_existing and output_path.exists():
        print(f"⏭️ [skip] Arquivo de saída já existe: {output_path}. Pulando.")
        return

    hino_id = args.hino

    # 1. Resolver caminhos
    midi_path = None
    txt_path = None

    if hino_id is not None:
        hino_id_str = str(hino_id).strip()
        is_coro = hino_id_str.upper().startswith("C")
        if is_coro:
            try:
                num_val = int(hino_id_str[1:])
            except ValueError:
                num_val = hino_id_str
            # Coro 001- ou Coro 1-
            pattern = f"Coro {num_val:03d}- *.mid"
            midi_files = list(MIDI_DIR.glob(pattern))
            if not midi_files:
                midi_files = list(MIDI_DIR.glob(f"*Coro {num_val}*.mid"))
            if not midi_files:
                midi_files = list(MIDI_DIR.glob(f"*Coro*{num_val}*.mid"))
        else:
            try:
                num_val = int(hino_id_str)
            except ValueError:
                num_val = hino_id_str
            if isinstance(num_val, int):
                pattern = f"{num_val:03d}- *.mid"
                midi_files = list(MIDI_DIR.glob(pattern))
            else:
                midi_files = []
            if not midi_files:
                midi_files = list(MIDI_DIR.glob(f"*{hino_id_str}*.mid"))
                # Pular coro se buscamos hino
                midi_files = [f for f in midi_files if "coro" not in f.name.lower()]
        
        if midi_files:
            midi_path = midi_files[0]
            
        # O TXT será resolvido por carregar_letra_hino via _indice.csv
    else:
        if args.midi:
            midi_path = Path(args.midi)
        if args.txt:
            txt_path = Path(args.txt)

    if not midi_path or not midi_path.exists():
        print(f"[erro] Arquivo MIDI não encontrado ou não especificado.")
        sys.exit(1)

    mp3_path = Path(args.mp3)
    if not mp3_path.exists():
        print(f"[erro] Arquivo MP3 {mp3_path} não encontrado.")
        sys.exit(1)

    print(f"🎵 Iniciando Sincronização do Hino {hino_id if hino_id else midi_path.stem}...")

    # 2. Carregar Letra
    try:
        letra = carregar_letra_hino(hino_id, txt_path)
        print(f"   [letra] Título: {letra['titulo']}")
        print(f"   [letra] Estrofes: {len(letra['verses'])} versos, Coro: {'Sim' if letra['chorus'] else 'Não'}")
    except Exception as e:
        print(f"[erro] Falha ao ler letra do hino: {e}")
        sys.exit(1)

    # 3. Carregar MIDI e Extrair Melodia
    try:
        pm = pretty_midi.PrettyMIDI(str(midi_path))
        melody_track = find_melody_track(pm)
        if not melody_track:
            raise ValueError("Não foi possível encontrar uma trilha de melodia válida no MIDI.")
        notes = sorted(melody_track.notes, key=lambda x: x.start)
        print(f"   [midi] Trilha de melodia localizada ({len(notes)} notas).")
    except Exception as e:
        print(f"[erro] Falha ao processar MIDI: {e}")
        sys.exit(1)

    # 4. Detectar Introdução
    intro_notes_count, intro_midi_duration = detectar_introducao(notes)
    print(f"   [midi] Introdução detectada: {intro_notes_count} notas (término em {intro_midi_duration:.2f}s no MIDI).")

    # 5. Estimar Velocidade / Alinhar Áudio
    midi_onsets = np.array(sorted([n.start for n in notes]))
    print("   [audio] Alinhando tempos do MIDI com o MP3 (estimando speed_scale)...")
    alpha = estimar_speed_scale(midi_onsets, mp3_path)
    estimated_speed = 1.0 / alpha
    print(f"   [audio] Speed scale detectado (alpha): {alpha:.4f} (velocidade equivalente: {estimated_speed:.4f}x).")

    # 6. Mapear Frases e Gerar Tempos
    print("   [sync] Distribuindo notas por frases e refinando limites dinamicamente...")
    aligned_lines = mapear_letra_para_notes(letra, notes, intro_notes_count, alpha)
    
    # 7. Salvar JSON Final
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if hino_id:
        hino_id_clean = str(hino_id).strip()
    else:
        is_coro = "coro" in midi_path.name.lower()
        digits = re.search(r"\d+", midi_path.name).group()
        hino_id_clean = f"C{int(digits)}" if is_coro else str(int(digits))
    
    # Obter duração total do MP3
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(mp3_path),
    ]
    mp3_dur = 0.0
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        mp3_dur = float(res.stdout.strip())
    except:
        mp3_dur = notes[-1].end * alpha + 1.0

    output_data = {
        "hino": hino_id_clean,
        "titulo": letra["titulo"],
        "duracao_mp3": round(mp3_dur, 3),
        "speed_scale": round(alpha, 4),
        "intro_duration": round(intro_midi_duration * alpha, 3),
        "letra": aligned_lines
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Sincronização concluída com sucesso! JSON salvo em: {output_path}")

if __name__ == "__main__":
    main()