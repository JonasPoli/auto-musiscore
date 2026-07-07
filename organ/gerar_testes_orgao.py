#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
organ/gerar_testes_orgao.py
============================
Gera combinações de timbre de órgão eletrônico para curadoria.
Cada combinação produz um MP3 renderizado via FluidSynth usando programas
GM (Drawbar, Percussive, Rock, Church, Reed Organ, Accordion, Pads).

Estrutura de saída:
    output/testes-orgao/
    ├── 001_drawbar_organ_puro.mp3
    ├── ...
    ├── 030_drawbar_church_church_forte.mp3
    └── catalogo.md

Regras de Humanização (AGENTS.md):
    - Timing Offset = 0 (sem desincronismo)
    - Velocity pós-pausa = 10, CC11 ramp 40→100 em 225ms
    - Encurtamento pré-pausa = 30%
"""

import os
import sys
import argparse
import subprocess
import shutil
from pathlib import Path

import mido

ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT / 'utils'))

from gerar_testes_timbre import get_tempo, detect_phrases
from midi_humanize import remove_staccato

# ─── Canais melódicos (sem canal 9 = percussão) ──────────────────────────────
MELODIC_CHANNELS = [ch for ch in range(16) if ch != 9]


# =============================================================================
#  DEFINIÇÃO DAS 30 COMBINAÇÕES PREDEFINIDAS
# =============================================================================

def _combo(cid, name, layers, desc, vel_scales=None, voice_split=None):
    """Helper para definir uma combinação de timbre.

    Args:
        cid: ID sequencial (str "001")
        name: Nome legível da combinação
        layers: Lista de programas GM [16, 18, ...]
        desc: Descrição do timbre
        vel_scales: Dict {program: fator_volume} (opcional, auto-calculado)
        voice_split: Dict {"Soprano": [progs], "Contralto": [progs], ...} (opcional)
    """
    return {
        "id": cid,
        "name": name,
        "programs": layers,
        "description": desc,
        "vel_scales": vel_scales,
        "voice_split": voice_split,
    }


COMBINATIONS = [
    # ─── 1. Timbres GM Puros (programa único) ─────────────────────────────────
    _combo("001", "Drawbar Organ Puro",    [16],    "Hammond clássico, quente"),
    _combo("003", "Rock Organ",            [18],    "Hammond com drive/distorção"),

    # ─── 2. Combinações Layered (2 camadas) ───────────────────────────────────
    _combo("007", "Drawbar + Rock",        [16, 18], "Hammond quente + drive",
           vel_scales={16: 0.85, 18: 0.60}),
    _combo("008", "Drawbar + Church",      [16, 19], "Hammond + tubos suaves",
           vel_scales={16: 0.80, 19: 0.65}),
    _combo("009", "Drawbar + Reed",        [16, 20], "Hammond + harmonium",
           vel_scales={16: 0.80, 20: 0.65}),
    _combo("010", "Rock + Church",         [18, 19], "Drive + solenidade",
           vel_scales={18: 0.70, 19: 0.75}),
    _combo("011", "Rock + Reed",           [18, 20], "Drive + harmonium",
           vel_scales={18: 0.75, 20: 0.65}),
    _combo("012", "Church + Reed",         [19, 20], "Tubos + harmonium (litúrgico)",
           vel_scales={19: 0.80, 20: 0.70}),

    # ─── 3. Combinações com Pad (corpo + ambiência) ──────────────────────────
    _combo("013", "Drawbar + Warm Pad",    [16, 89], "Hammond + pad quente",
           vel_scales={16: 0.85, 89: 0.50}),
    _combo("015", "Drawbar + Halo Pad",    [16, 94], "Hammond + pad etéreo",
           vel_scales={16: 0.85, 94: 0.45}),

    _combo("018", "Rock + Polysynth",      [18, 90], "Drive + synth organ",
           vel_scales={18: 0.75, 90: 0.55}),

    # ─── 4. Combinações Triplas (3 camadas) ──────────────────────────────────
    _combo("019", "Drawbar + Rock + Warm Pad",    [16, 18, 89], "Triplo layered",
           vel_scales={16: 0.70, 18: 0.50, 89: 0.40}),
    _combo("020", "Drawbar + Church + Warm Pad",  [16, 19, 89], "Corpo completo",
           vel_scales={16: 0.70, 19: 0.55, 89: 0.40}),
    _combo("021", "Drawbar + Reed + Halo Pad",    [16, 20, 94], "Harmonium celestial",
           vel_scales={16: 0.70, 20: 0.55, 94: 0.35}),

    # ─── 5. Vozes Split (timbres diferentes por voz SATB) ────────────────────
    _combo("023", "Split Clássico",        [18, 16, 16, 19], "Rock melodia + Drawbar corpo + Church baixo",
           voice_split={"Soprano": [18], "Contralto": [16], "Tenor": [16], "Baixo": [19]}),
    _combo("024", "Split Litúrgico",       [19, 19, 20, 20], "Church agudo + Reed grave",
           voice_split={"Soprano": [19], "Contralto": [19], "Tenor": [20], "Baixo": [20]}),
    _combo("026", "Split Rock-Church",     [18, 18, 19, 19], "Rock vozes altas + Church graves",
           voice_split={"Soprano": [18], "Contralto": [18], "Tenor": [19], "Baixo": [19]}),
    _combo("027", "Split Drawbar-Reed",    [16, 16, 20, 20], "Hammond vozes + Harmonium graves",
           voice_split={"Soprano": [16], "Contralto": [16], "Tenor": [20], "Baixo": [20]}),
    _combo("028", "Split Full",            [18, 16, 20, 19], "Cada voz um timbre diferente",
           voice_split={"Soprano": [18], "Contralto": [16], "Tenor": [20], "Baixo": [19]}),

    # ─── 6. Variações de Volume ──────────────────────────────────────────────
    _combo("029", "Drawbar+Rock (Rock forte)", [16, 18], "Rock mais presente",
           vel_scales={16: 0.60, 18: 0.85}),
    _combo("030", "Drawbar+Church (Church forte)", [16, 19], "Church mais presente",
           vel_scales={16: 0.55, 19: 0.90}),
]


# =============================================================================
#  DETECÇÃO DE VOZES SATB
# =============================================================================

def detect_satb_channels(mid):
    """Detecta os canais MIDI correspondentes a Soprano/Contralto/Tenor/Baixo
    pela média de pitch de cada canal (mais agudo = Soprano)."""
    pitch_sum, pitch_cnt = {}, {}
    for track in mid.tracks:
        curr = 0
        for msg in track:
            curr += msg.time
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


# =============================================================================
#  EXTRAÇÃO DE NOTAS DA FRASE
# =============================================================================

def extract_phrase_notes(mid, ph_start, ph_end):
    """Extrai as notas de cada voz SATB dentro do intervalo [ph_start, ph_end)."""
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


# =============================================================================
#  CONSTRUÇÃO DO MIDI HUMANIZADO PARA ÓRGÃO
# =============================================================================

def build_organ_midi(mid, voice_notes, combo, speed=0.5, phrase_start=0):
    """Constrói um MIDI humanizado para a combinação de órgão especificada.

    Suporta dois modos:
    1. Layered: todos os programs aplicados a todas as vozes (com vel_scales)
    2. Voice Split: cada voz usa programas específicos

    Retorna o MidiFile pronto para renderização FluidSynth.
    """
    tempo_orig = get_tempo(mid)
    tempo_new = int(tempo_orig / speed)
    tpb = mid.ticks_per_beat

    new_mid = mido.MidiFile()
    new_mid.ticks_per_beat = tpb
    meta = mido.MidiTrack()
    new_mid.tracks.append(meta)

    # Copia time_signature e key_signature
    for track in mid.tracks:
        for msg in track:
            if msg.is_meta and msg.type in ['time_signature', 'key_signature']:
                meta.append(msg.copy())
    meta.append(mido.MetaMessage('set_tempo', tempo=tempo_new, time=0))

    all_events = []
    ch_counter = 0

    voice_split = combo.get("voice_split")
    programs = combo["programs"]
    vel_scales = combo.get("vel_scales") or {}

    # Parâmetros de ataque pós-pausa (AGENTS.md)
    attack_vel = 10
    cc11_start = 40

    voices_order = ["Soprano", "Contralto", "Tenor", "Baixo"]

    for voice in voices_order:
        notes = voice_notes.get(voice, [])
        if not notes:
            continue

        # Determina quais programas esta voz usa
        if voice_split:
            voice_programs = voice_split.get(voice, programs[:1])
        else:
            voice_programs = programs

        for prog in voice_programs:
            midi_ch = MELODIC_CHANNELS[ch_counter % len(MELODIC_CHANNELS)]
            ch_counter += 1

            # Calcula escala de velocity para esta camada
            if vel_scales and prog in vel_scales:
                v_scale = vel_scales[prog]
            elif len(voice_programs) > 1:
                v_scale = 1.0 / len(voice_programs)
            else:
                v_scale = 1.0

            # Volume base (órgão não precisa de atenuação como cordas)
            vol = min(127, max(40, int(100 * v_scale)))

            # Setup do canal
            all_events += [
                mido.Message('program_change', channel=midi_ch, program=prog, time=0),
                mido.Message('control_change', channel=midi_ch, control=10, value=64, time=0),  # Pan center
                mido.Message('control_change', channel=midi_ch, control=7,  value=vol, time=0),
                mido.Message('control_change', channel=midi_ch, control=11, value=127, time=0),
            ]

            for i, (note, on_t, off_t, vel) in enumerate(notes):
                dur = remove_staccato(off_t - on_t, tpb)
                is_after_pause = (i == 0) or (on_t - notes[i - 1][2] >= tpb * 0.25)
                is_before_pause = (i < len(notes) - 1) and (notes[i + 1][1] - off_t >= tpb * 0.25)

                # Encurtamento pré-pausa (30%) — AGENTS.md
                if is_before_pause:
                    dur = int(dur * 0.70)

                on_new = on_t - phrase_start
                off_new = on_new + max(15, dur)

                # Anti-overlap
                next_start = None
                for nj in notes[i + 1:]:
                    if nj[1] > on_t:
                        next_start = nj[1] - phrase_start
                        break
                if next_start is not None and off_new > next_start:
                    off_new = max(on_new + 5, next_start)

                # Velocity pós-pausa atenuada
                v_note = attack_vel if is_after_pause else min(127, max(1, int(vel * v_scale)))

                all_events.append(mido.Message(
                    'note_on', channel=midi_ch, note=note,
                    velocity=v_note, time=on_new))
                all_events.append(mido.Message(
                    'note_off', channel=midi_ch, note=note,
                    velocity=0, time=off_new))

                # Rampa CC11 pós-pausa: 40→100 ao longo de 225ms (AGENTS.md)
                if is_after_pause:
                    ramp = seconds_to_ticks(0.225, tempo_new, tpb)
                    for step in range(5):
                        t_cc = on_new + int((step / 4) * ramp)
                        cc_val = int(cc11_start + (step / 4) * (100 - cc11_start))
                        all_events.append(mido.Message(
                            'control_change', channel=midi_ch,
                            control=11, value=cc_val, time=t_cc))

    # Ordena e escreve os eventos
    setup = [m for m in all_events if m.time == 0]
    music = sorted([m for m in all_events if m.time > 0], key=lambda m: m.time)
    note_track = mido.MidiTrack()
    new_mid.tracks.append(note_track)
    prev = 0
    for msg in setup + music:
        note_track.append(msg.copy(time=msg.time - prev))
        prev = msg.time

    return new_mid

# =============================================================================
#  RENDERIZAÇÃO via MuseScore CLI (MIDI → MSCZ → patch → MP3)
# =============================================================================

MSCORE_BIN = "/Applications/MuseScore 4.app/Contents/MacOS/mscore"


def clean_runtime_files(directory: Path):
    """Limpa resíduos do MuseScore CLI (AGENTS.md §3)."""
    for f in ["automation.json", "audiosettings.json", "viewsettings.json"]:
        fp = directory / f
        if fp.exists():
            try:
                fp.unlink()
            except OSError:
                pass
    for d in ["META-INF", "Thumbnails"]:
        dp = directory / d
        if dp.exists() and dp.is_dir():
            try:
                shutil.rmtree(dp)
            except OSError:
                pass


def render_via_musescore(midi_path: Path, mp3_path: Path, mscz_path: Path,
                         bpm_target: float) -> bool:
    """Pipeline MuseScore: MIDI → MSCZ → remove staccato → set BPM → MP3.

    Segue o mesmo padrão de gerar_testes_timbre.py.
    """
    from midi_humanize import (remove_staccato_from_mscz, set_tempo_in_mscz,
                                ajustar_ultimo_compasso_mscz)

    try:
        # 1. MIDI → MSCZ (MuseScore importa a partitura)
        r = subprocess.run(
            [MSCORE_BIN, "-o", str(mscz_path), str(midi_path)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        if not mscz_path.exists():
            return False

        # 2. Patch: remove staccato + define BPM + ajusta último compasso
        n_stacc = remove_staccato_from_mscz(mscz_path)
        set_tempo_in_mscz(mscz_path, bpm_target)
        ajustar_ultimo_compasso_mscz(mscz_path)

        # 3. MSCZ → MP3 (renderização com MS Basic SoundFont)
        r = subprocess.run(
            [MSCORE_BIN, "-o", str(mp3_path), str(mscz_path)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return mp3_path.exists()

    except Exception as e:
        print(f"EXCEÇÃO: {e}")
        return False
    finally:
        # Limpa resíduos do MuseScore (AGENTS.md §3)
        clean_runtime_files(midi_path.parent)
        clean_runtime_files(mp3_path.parent)


# =============================================================================
#  PÓS-PROCESSAMENTO: Fade-in Hermitiano (Smoothstep 200ms)
# =============================================================================

def apply_postprocess(mp3_path: Path):
    """Aplica fade-in Smoothstep de 200ms pós-pausa (AGENTS.md)."""
    pp_script = ROOT / 'utils' / 'postprocess_fade_apos_pausa.py'
    if pp_script.exists() and mp3_path.exists():
        subprocess.run([
            sys.executable, str(pp_script),
            '--input', str(mp3_path),
            '--output', str(mp3_path),
            '--fade-ms', '200',
            '--lookback-ms', '20',
            '--min-silence-ms', '250',
            '--include-start'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# =============================================================================
#  NORMALIZAÇÃO DE VOLUME (loudnorm EBU R128)
# =============================================================================

def normalize_mp3(mp3_path: Path):
    """Normaliza volume do MP3 final via ffmpeg loudnorm."""
    tmp = mp3_path.with_suffix(".tmp.mp3")
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", str(mp3_path),
         "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
         "-c:a", "libmp3lame", "-q:a", "2", str(tmp)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    if r.returncode == 0 and tmp.exists():
        tmp.replace(mp3_path)
    elif tmp.exists():
        tmp.unlink()


# =============================================================================
#  GERAÇÃO DO CATÁLOGO MARKDOWN
# =============================================================================

def write_catalog(output_dir: Path, results: list, midi_name: str, phrase_idx: int,
                  bpm_orig: float, bpm_target: float, speed: float):
    """Gera catalogo.md com tabela de todas as combinações para curadoria."""
    lines = [
        "# 🎹 Catálogo de Timbres de Órgão Eletrônico — Curadoria\n\n",
        f"**Referência:** `{midi_name}`, frase {phrase_idx + 1}\n",
        f"**BPM:** {bpm_orig:.0f} → {bpm_target:.0f} (speed={speed:.2f})\n",
        f"**Renderização:** MuseScore 4 CLI (MS Basic SoundFont)\n\n",
        "---\n\n",
        "## Combinações\n\n",
        "| # | Nome | Programs GM | Descrição | Status | Aprovado? |\n",
        "|---|------|-------------|-----------|--------|----------|\n",
    ]

    for combo, ok in results:
        progs_str = "+".join(str(p) for p in combo["programs"])
        status = "✓" if ok else "✗"
        lines.append(
            f"| `{combo['id']}` | {combo['name']} | {progs_str} | "
            f"{combo['description']} | {status} | |\n"
        )

    lines += [
        "\n---\n\n",
        "## Legenda de Programs GM\n\n",
        "| Program | Nome GM | Família |\n",
        "|---------|---------|--------|\n",
        "| 16 | Drawbar Organ | Hammond |\n",
        "| 17 | Percussive Organ | Hammond |\n",
        "| 18 | Rock Organ | Hammond |\n",
        "| 19 | Church Organ | Tubos |\n",
        "| 20 | Reed Organ | Harmonium |\n",
        "| 21 | Accordion | Sanfona |\n",
        "| 89 | Warm Synth Pad | Synth |\n",
        "| 90 | Polysynth | Synth |\n",
        "| 94 | Halo Synth Pad | Synth |\n",
    ]

    (output_dir / "catalogo.md").write_text("".join(lines), encoding='utf-8')


# =============================================================================
#  LOOP PRINCIPAL
# =============================================================================

def generate_organ_tests(midi_path: str, output_dir: str, phrase_index: int = 0,
                         speed: float = 0.5, bpm_target: float = None):
    """Gera todas as combinações de timbre de órgão para curadoria."""
    mid = mido.MidiFile(midi_path)
    tempo = get_tempo(mid)
    tpb = mid.ticks_per_beat
    bpm_orig = 60_000_000 / tempo

    if bpm_target is not None:
        speed = bpm_target / bpm_orig
    elif speed is not None:
        bpm_target = bpm_orig * speed
    else:
        speed = 0.5
        bpm_target = bpm_orig * speed

    phrases = detect_phrases(mid, tempo, min_phrase_seconds=6.0, silence_beats=0.4)
    if not phrases:
        print("ERRO: Nenhuma frase detectada no MIDI.")
        sys.exit(1)
    if phrase_index >= len(phrases):
        phrase_index = 0

    ph_start, ph_end = phrases[phrase_index]
    dur_orig = (ph_end - ph_start) * tempo / (tpb * 1_000_000)
    dur_slow = dur_orig / speed

    print(f"\n{'='*60}")
    print(f"  TESTES DE TIMBRE DE ÓRGÃO ELETRÔNICO")
    print(f"{'='*60}")
    print(f"  MIDI: {Path(midi_path).name}")
    print(f"  Frase {phrase_index + 1}/{len(phrases)}: {dur_orig:.1f}s → {dur_slow:.1f}s")
    print(f"  BPM: {bpm_orig:.0f} → {bpm_target:.0f}  (speed={speed:.3f})")
    print(f"  Renderização: MuseScore 4 CLI")
    print(f"  Combinações: {len(COMBINATIONS)}")
    print(f"{'='*60}\n")

    voice_notes = extract_phrase_notes(mid, ph_start, ph_end)
    if not voice_notes:
        print("ERRO: Nenhuma nota detectada na frase selecionada.")
        sys.exit(1)

    for v, notes in voice_notes.items():
        print(f"  {v}: {len(notes)} notas")
    print()

    out = Path(output_dir)
    if out.exists():
        shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)

    work_dir = Path(f'/tmp/_tmp_organ_test_{os.getpid()}')
    shutil.rmtree(work_dir, ignore_errors=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    results = []
    ok_count = 0

    for idx, combo in enumerate(COMBINATIONS, 1):
        cid = combo["id"]
        name_slug = combo["name"].lower().replace(" ", "_").replace("+", "_").replace("(", "").replace(")", "")
        fn = f"{cid}_{name_slug}"
        mp3_out = out / f"{fn}.mp3"
        mscz_out = out / f"{fn}.mscz"

        progs_str = "+".join(str(p) for p in combo["programs"])
        print(f"[{idx:03d}/{len(COMBINATIONS)}] {combo['name']} (GM {progs_str})", end="  ", flush=True)

        # 1. Constrói o MIDI humanizado
        new_mid = build_organ_midi(mid, voice_notes, combo, speed=speed, phrase_start=ph_start)

        # 2. Salva MIDI temporário
        midi_tmp = work_dir / f"{cid}.mid"
        new_mid.save(str(midi_tmp))

        # 3. Renderiza via MuseScore (MIDI → MSCZ → MP3)
        ok = render_via_musescore(midi_tmp, mp3_out, mscz_out, bpm_target)

        # 4. Pós-processamento fade-in + normalização
        if ok:
            apply_postprocess(mp3_out)
            normalize_mp3(mp3_out)
            print(f"OK ({mp3_out.stat().st_size // 1024} KB)")
            ok_count += 1
        else:
            print("ERRO")

        # 5. Limpa MIDI temporário
        if midi_tmp.exists():
            midi_tmp.unlink()

        results.append((combo, ok))

    # Limpa diretório temporário
    shutil.rmtree(work_dir, ignore_errors=True)

    # Gera catálogo
    write_catalog(out, results, Path(midi_path).name, phrase_index,
                  bpm_orig, bpm_target, speed)

    print(f"\n{'='*60}")
    print(f"  {ok_count}/{len(COMBINATIONS)} combinações geradas com sucesso!")
    print(f"  Pasta: {out}")
    print(f"  Catálogo: {out / 'catalogo.md'}")
    print(f"{'='*60}\n")


# =============================================================================
#  CLI
# =============================================================================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Gera testes de timbre de órgão eletrônico para curadoria."
    )
    parser.add_argument("--midi", default="mid/003- Faz-nos ouvir Tua voz.mid",
                        help="Caminho do MIDI de referência")
    parser.add_argument("--output", default="output/testes-orgao",
                        help="Diretório de saída")
    parser.add_argument("--frase", type=int, default=0,
                        help="Índice da frase (0-indexed, default: 0)")
    parser.add_argument("--bpm", type=float, default=None,
                        help="BPM alvo de saída (sobrepõe --speed)")
    parser.add_argument("--speed", type=float, default=0.5,
                        help="Fator de velocidade (default: 0.5 = 50%%)")
    args = parser.parse_args()

    generate_organ_tests(
        midi_path=args.midi,
        output_dir=args.output,
        phrase_index=args.frase,
        speed=args.speed if args.bpm is None else None,
        bpm_target=args.bpm,
    )

