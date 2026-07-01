#!/usr/bin/env python3
"""
gerar_hino_completo.py  (v9 – interleaved sem trim entre exports)
=================================================================
Descoberta sobre o macOS + MuseScore:
  O MSCZ de cada frase Fn deve ser gerado APÓS o export MP3 da frase F(n-1).
  Se Fn for gerado antes, rc=40 durante o export de MP3.

Pipeline correto (validado por Teste 2):
  Para cada frase N:
    1. Gera MSCZ(N)            ← MuseScore atualiza estado global
    2. Exporta MP3 raw(N)      ← imediatamente, sem delay
  Após TODOS os exports:
    3. Trim de silêncio (ffmpeg) para cada MP3
    4. Concatena com gaps do MIDI original
"""
import sys, subprocess, shutil, argparse, random
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / 'utils'))
sys.path.insert(0, str(ROOT / 'orchestrators'))

import mido
from gerar_testes_timbre import (
    get_tempo, detect_phrases, extract_phrase_notes,
    combo_to_instruments, build_combo_midi, short_name,
    PREDEFINED, SOPRANO_POOL, CONTRALTO_POOL, TENOR_POOL, BAIXO_POOL,
    MSCORE_BIN,
)
from midi_humanize import (
    remove_staccato_from_mscz, set_tempo_in_mscz, set_pan_in_mscz,
    build_and_inject_audiosettings_pan, ajustar_ultimo_compasso_mscz,
)

SILENCE_THRESHOLD_DB = -45
DECAY_TAIL_S = 0.40


def _cleanup(directory: Path):
    for f in ['automation.json', 'audiosettings.json', 'viewsettings.json']:
        p = directory / f
        if p.exists(): p.unlink()
    for d in ['META-INF', 'Thumbnails']:
        p = directory / d
        if p.exists(): shutil.rmtree(p)


def count_instruments(combo) -> int:
    return sum(len(x) for x in combo)


def ticks_to_sec(ticks: int, tempo_new: int, tpb: int) -> float:
    return ticks * tempo_new / (tpb * 1_000_000)


def trim_mp3(src: Path, dst: Path) -> bool:
    thr = f'{SILENCE_THRESHOLD_DB}dB'
    af = (
        f'silenceremove=start_periods=1:start_silence=0.05:start_threshold={thr},'
        f'areverse,'
        f'silenceremove=start_periods=1:start_silence={DECAY_TAIL_S}:start_threshold={thr},'
        f'areverse'
    )
    r = subprocess.run(
        ['ffmpeg', '-y', '-i', str(src), '-af', af,
         '-c:a', 'libmp3lame', '-q:a', '2', str(dst)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return r.returncode == 0 and dst.exists()


def make_silence_mp3(duration_s: float, dst: Path) -> bool:
    if duration_s <= 0.01: return False
    r = subprocess.run(
        ['ffmpeg', '-y', '-f', 'lavfi', '-t', f'{duration_s:.3f}', '-i', 'aevalsrc=0:s=44100:c=stereo',
         '-c:a', 'libmp3lame', '-q:a', '2', str(dst)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return r.returncode == 0 and dst.exists()


def obter_duracao_mp3(path: Path) -> float:
    cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', str(path)
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        try:
            return float(r.stdout.strip())
        except ValueError:
            pass
    return 0.0


def select_progressive_combos(n_phrases: int, seed: int = 42) -> list:
    random.seed(seed)
    ordered = sorted(enumerate(PREDEFINED), key=lambda x: (count_instruments(x[1]), x[0]))
    n_avail = len(ordered)
    step = max(1, (n_avail - 1) / max(1, n_phrases - 1))
    selected = []
    for i in range(n_phrases):
        pos = min(int(round(i * step)), n_avail - 1)
        _, combo = ordered[pos]
        selected.append(combo)
    for i in range(1, len(selected)):
        if count_instruments(selected[i]) < count_instruments(selected[i-1]):
            selected[i] = selected[i-1]
    return selected


def render_phrase(mid, ph_start, ph_end, combo, speed, bpm_target, work_dir, phrase_idx, partes_dir=None):
    """
    Gera MSCZ e exporta MP3 raw (SEM trim).
    Retorna (orig_idx_0based, mp3_raw_path) ou (orig_idx_0based, None).

    CRÍTICO: o trim NÃO é feito aqui — deve ser feito apenas depois de TODOS
    os exports para não criar delay entre exports consecutivos.
    """
    s_idxs, c_idxs, t_idxs, b_idxs = combo
    instruments = combo_to_instruments(s_idxs, c_idxs, t_idxs, b_idxs)
    n = count_instruments(combo)
    sn = short_name(SOPRANO_POOL, s_idxs)
    cn = short_name(CONTRALTO_POOL, c_idxs)
    tn = short_name(TENOR_POOL, t_idxs)
    bn = short_name(BAIXO_POOL, b_idxs)
    print(f'  [F{phrase_idx:02d}] {n} instr | S={sn} | C={cn} | T={tn} | B={bn}', end='  ')

    voice_notes = extract_phrase_notes(mid, ph_start, ph_end)
    if not voice_notes:
        print('VAZIO'); return None

    new_mid, ch_pan_map = build_combo_midi(
        mid, voice_notes, instruments, speed=speed, phrase_start=ph_start,
    )

    pdir = work_dir / f'p{phrase_idx:02d}'
    pdir.mkdir(parents=True, exist_ok=True)
    midi_tmp = pdir / 'input.mid'
    mscz_tmp = pdir / 'score.mscz'
    mp3_raw  = pdir / 'raw.mp3'   # ← retornado sem trim

    # Pass 1: MIDI → MSCZ (MuseScore atualiza estado global — necessário para Pass 2 do próximo)
    new_mid.save(str(midi_tmp))
    subprocess.run([MSCORE_BIN, '-o', str(mscz_tmp), str(midi_tmp)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not mscz_tmp.exists():
        shutil.rmtree(pdir, ignore_errors=True)
        print('ERRO MSCZ'); return None

    n_stacc = remove_staccato_from_mscz(mscz_tmp)
    set_tempo_in_mscz(mscz_tmp, bpm_target)
    set_pan_in_mscz(mscz_tmp, ch_pan_map)
    n_pan = build_and_inject_audiosettings_pan(mscz_tmp, ch_pan_map)
    ajustar_ultimo_compasso_mscz(mscz_tmp)
    midi_tmp.unlink(missing_ok=True)
    
    # Se partes_dir existir, copia o .mscz gerado (orquestrado/humanizado) para análise
    if partes_dir and mscz_tmp.exists():
        partes_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(mscz_tmp, partes_dir / f'F{phrase_idx:02d}.mscz')

    # Pass 2: MSCZ → MP3 raw (IMEDIATAMENTE após Pass1, zero delay)
    r = subprocess.run([MSCORE_BIN, '-o', str(mp3_raw), str(mscz_tmp)],
                       capture_output=True, text=True)
    
    # Se partes_dir existir e exportou com sucesso, copia o raw MP3
    if partes_dir and mp3_raw.exists():
        shutil.copy(mp3_raw, partes_dir / f'F{phrase_idx:02d}_raw.mp3')

    # Só agora limpa — depois que Pass2 terminou
    mscz_tmp.unlink(missing_ok=True)
    # _cleanup(pdir)

    if not mp3_raw.exists():
        shutil.rmtree(pdir, ignore_errors=True)
        print(f'ERRO MP3 (rc={r.returncode} pan={n_pan} stacc={n_stacc})')
        if r.stdout.strip(): print(f'  STDOUT: {r.stdout.strip()}')
        if r.stderr.strip(): print(f'  STDERR: {r.stderr.strip()}')
        return None

    # NÃO faz trim aqui — o caller faz depois de todos os exports
    print(f'RAW OK (pan={n_pan} stacc={n_stacc})')
    return mp3_raw
def escrever_explicacao_md(partes_dir: Path, selected: list, midi_name: str):
    local_muse_lookup = {
        "strings.violin":      {"uid": "103", "setup": "strings.violin.orchestral:primary", "pack": "Muse Strings"},
        "strings.viola":       {"uid": "105", "setup": "strings.viola.orchestral", "pack": "Muse Strings"},
        "strings.cello":       {"uid": "106", "setup": "strings.violoncello.orchestral", "pack": "Muse Strings"},
        "strings.contrabass":  {"uid": "132", "setup": "winds.saxophone.baritone", "pack": "Muse Woodwinds"},
        "brass.trumpet":       {"uid": "110", "setup": "winds.trumpet", "pack": "Muse Brass"},
        "brass.trombone":      {"uid": "111", "setup": "winds.trombone", "pack": "Muse Brass"},
        "brass.french-horn":   {"uid": "96",  "setup": "winds.horn.french:in_a:section", "pack": "Muse Brass"}, # Horns a6
        "brass.tuba":          {"uid": "113", "setup": "winds.tuba", "pack": "Muse Brass"},
        "woodwind.flutes.flute": {"uid": "120", "setup": "winds.flute", "pack": "Muse Woodwinds"},
        "woodwind.flutes.piccolo": {"uid": "125", "setup": "winds.piccolo", "pack": "Muse Woodwinds"},
        "woodwind.reed.oboe":    {"uid": "121", "setup": "winds.oboe", "pack": "Muse Woodwinds"},
        "woodwind.reed.english-horn": {"uid": "96", "setup": "winds.horn.french:in_a:section", "pack": "Muse Brass"}, # Horns a6
        "woodwind.reed.clarinet": {"uid": "127", "setup": "winds.clarinet.soprano:in_b_flat", "pack": "Muse Woodwinds"},
        "woodwind.reed.bassoon":  {"uid": "123", "setup": "winds.bassoon", "pack": "Muse Woodwinds"},
        "woodwind.reed.contrabassoon": {"uid": "134", "setup": "winds.contrabassoon", "pack": "Muse Woodwinds"},
        "sax.soprano":         {"uid": "129", "setup": "winds.saxophone.soprano", "pack": "Muse Woodwinds"},
        "sax.alto":            {"uid": "130", "setup": "winds.saxophone.alto", "pack": "Muse Woodwinds"},
        "sax.tenor":           {"uid": "131", "setup": "winds.saxophone.tenor", "pack": "Muse Woodwinds"},
        "sax.baritone":        {"uid": "132", "setup": "winds.saxophone.baritone", "pack": "Muse Woodwinds"},
        "sax.contrabass":      {"uid": "132", "setup": "winds.saxophone.baritone", "pack": "Muse Woodwinds"},
        "sax.subcontrabass":   {"uid": "132", "setup": "winds.saxophone.baritone", "pack": "Muse Woodwinds"},
        "sax.bass":            {"uid": "132", "setup": "winds.saxophone.baritone", "pack": "Muse Woodwinds"},
        "keyboard.piano":      {"uid": "201", "setup": "keys.piano", "pack": "Muse Keys"}
    }

    name_to_key = {
        "Violino": "strings.violin",
        "Violino 2": "strings.violin",
        "Viola": "strings.viola",
        "Cello": "strings.cello",
        "Contrabaixo": "strings.contrabass",
        "Trompete": "brass.trumpet",
        "Trombone": "brass.trombone",
        "Trombone Baixo": "brass.trombone",
        "Trompa": "brass.french-horn",
        "Tuba": "brass.tuba",
        "Flauta": "woodwind.flutes.flute",
        "Piccolo": "woodwind.flutes.piccolo",
        "Oboé": "woodwind.reed.oboe",
        "Corne Ingles": "woodwind.reed.english-horn",
        "Clarinete": "woodwind.reed.clarinet",
        "Fagote": "woodwind.reed.bassoon",
        "Sax Soprano": "sax.soprano",
        "Sax Alto": "sax.alto",
        "Sax Tenor": "sax.tenor",
        "Sax Baritono": "sax.baritone",
        "Sax Baixo": "sax.bass",
        "Saxofone Baixo": "sax.bass",
        "Bass Saxophone": "sax.bass",
        "Sax Contrabaixo": "sax.contrabass",
        "Sax Subcontrabaixo": "sax.subcontrabass",
        "Piano": "keyboard.piano"
    }

    md_path = partes_dir / "explicação.md"
    lines = [
        f"# 🎹 Explicação dos Timbres e Dinâmicas — {midi_name}",
        "",
        "Este arquivo detalha as especificações técnicas, volumes, UIDs e configurações do MuseSounds aplicadas a cada frase.",
        "",
        "---",
        "",
        "## 🎧 1. Regras de Humanização Acústica",
        "",
        "1. **Timing Offset**: Cada instrumento possui um atraso aleatório independente de **5 ms a 25 ms** para evitar o cancelamento de fase digital.",
        "2. **Dinâmica Pós-Pausa (Velocity & CC11 Ramp)**: A primeira nota tocada pós-silêncio (pausa >= 0.25 tempos) tem a velocidade inicial limitada a **Velocity = 10**. Um crescendo dinâmico via **CC11 (Expression)** sobe de 40 a 100 ao longo de 200 ms a 250 ms.",
        "3. **Encurtamento Pré-Pausa**: Notas que precedem uma pausa (silêncio >= 0.25 tempos) são encurtadas em **30%** para limpar a articulação do reverb natural.",
        "",
        "---",
        "",
        "## 🎼 2. Detalhamento dos Instrumentos por Frase",
        ""
    ]

    for f_idx, combo in enumerate(selected):
        s_idxs, c_idxs, t_idxs, b_idxs = combo
        lines.append(f"### 📯 Frase F{f_idx+1:02d}")
        lines.append("")
        
        voices = [
            ("Soprano",   s_idxs, SOPRANO_POOL),
            ("Contralto", c_idxs, CONTRALTO_POOL),
            ("Tenor",     t_idxs, TENOR_POOL),
            ("Baixo",     b_idxs, BAIXO_POOL)
        ]
        
        for vname, idxs, pool in voices:
            for inst_idx in idxs:
                if inst_idx >= len(pool):
                    continue
                inst = pool[inst_idx]
                iname = inst["name"]
                vol = inst["vol"]
                prog = inst["program"]
                fam = inst["fam"]
                
                mkey = name_to_key.get(iname)
                muse_info = local_muse_lookup.get(mkey) if mkey else None
                
                if muse_info:
                    muse_str = f"MuseSounds (UID: `{muse_info['uid']}`, Setup: `{muse_info['setup']}`, Pack: `{muse_info['pack']}`)"
                else:
                    muse_str = "MS Basic (Fallback SoundFont)"
                
                lines.append(f"* **{vname}**: {iname} (Volume: `{vol}`, Prog GM: `{prog}`, Família: `{fam}`) ➔ {muse_str}")
        lines.append("")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  [OK] Explicação gerada em: {md_path.name}")


def gerar_hino_completo(midi_path: str, output_mp3: str, bpm_target: float = 60.0, speed: float = None) -> bool:
    mid      = mido.MidiFile(midi_path)
    tempo    = get_tempo(mid)
    bpm_orig = 60_000_000 / tempo
    tpb      = mid.ticks_per_beat
    if bpm_target is None:
        if speed is not None:
            bpm_target = bpm_orig * speed
        else:
            bpm_target = bpm_orig
            
    if speed is None:
        speed = bpm_target / bpm_orig
    tempo_new = int(60_000_000 / bpm_target)

    print(f'\n{"="*60}')
    print(f'  HINO COMPLETO: {Path(midi_path).name}')
    print(f'  BPM: {bpm_orig:.0f} -> {bpm_target:.0f}  (speed={speed:.3f})')
    print(f'{"="*60}')

    phrases = detect_phrases(mid, tempo, min_phrase_seconds=6.0, silence_beats=0.4)
    if not phrases:
        print('ERRO: nenhuma frase detectada.'); return False

    print(f'\nFrases ({len(phrases)}):')
    for i, (s, e) in enumerate(phrases):
        dur_tgt = ticks_to_sec(e - s, tempo_new, tpb) / speed
        gap_tgt = ticks_to_sec(phrases[i+1][0] - e, tempo_new, tpb) if i+1 < len(phrases) else 0
        print(f'  Frase {i+1}: {dur_tgt:.1f}s  gap->{gap_tgt:.1f}s')

    selected = select_progressive_combos(len(phrases))
    print(f'\nProgressao:')
    prev_n = 0
    for i, combo in enumerate(selected):
        n = count_instruments(combo)
        arrow = '^' if n > prev_n else '='
        sn = short_name(SOPRANO_POOL, combo[0])
        print(f'  F{i+1}: {n} instr {arrow}  S={sn}')
        prev_n = n

    out_path = Path(output_mp3)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    partes_dir = out_path.parent / (out_path.stem + '_partes')
    shutil.rmtree(partes_dir, ignore_errors=True)
    partes_dir.mkdir(parents=True, exist_ok=True)
    escrever_explicacao_md(partes_dir, selected, Path(midi_path).name)

    work_dir = Path('/tmp/_tmp_hino')
    shutil.rmtree(work_dir, ignore_errors=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    # ── Fase 1+2: MSCZ gerado e MP3 exportado em sequência intercalada ──────────
    # Cada frase gera MSCZ → exporta MP3 raw, SEM trim, antes de passar para próxima.
    print(f'\nRenderizando frases (MSCZ+MP3 por vez, sem trim entre):')
    print(f'  Arquivos temporários das partes salvos em: {partes_dir}')
    raw_results = []   # [(orig_idx_0based, mp3_raw_path)]
    for i, (phrase, combo) in enumerate(zip(phrases, selected), start=1):
        mp3_raw = render_phrase(mid, phrase[0], phrase[1], combo,
                                speed=speed, bpm_target=bpm_target,
                                work_dir=work_dir, phrase_idx=i,
                                partes_dir=partes_dir)
        raw_results.append((i - 1, mp3_raw))

    # ── Fase 3: Trim de silêncio (depois de todos os exports) ───────────────────
    print(f'\nTrimming silêncio:')
    trimmed = {}
    for orig_idx, mp3_raw in raw_results:
        if mp3_raw and mp3_raw.exists():
            trimmed_mp3 = work_dir / f'frase_{orig_idx:02d}.mp3'
            if trim_mp3(mp3_raw, trimmed_mp3):
                # Copia o trimmed MP3 para a pasta de partes
                shutil.copy(trimmed_mp3, partes_dir / f'F{orig_idx+1:02d}_trim.mp3')
                mp3_raw.unlink(missing_ok=True)
                trimmed[orig_idx] = trimmed_mp3
                print(f'  F{orig_idx+1:02d}: OK')
            else:
                mp3_raw.rename(trimmed_mp3)
                shutil.copy(trimmed_mp3, partes_dir / f'F{orig_idx+1:02d}_trim.mp3')
                trimmed[orig_idx] = trimmed_mp3
                print(f'  F{orig_idx+1:02d}: OK-notrim')

    succeeded = sorted(trimmed.keys())
    print(f'\n{len(succeeded)}/{len(phrases)} frases prontas.')
    if not succeeded:
        print('ERRO: nenhuma frase.'); shutil.rmtree(work_dir, ignore_errors=True); return False

    # ── Fase 4: Montagem com gaps auto-ajustados dinamicamente ──────────────────
    sequence = []
    frases_coladas_info = [] # Lista de (tempo_inicio_original_s, duracao_trimada_s)
    
    for k, orig_idx in enumerate(succeeded):
        mp3_trimmed = trimmed[orig_idx]
        dur_s = obter_duracao_mp3(mp3_trimmed)
        inicio_s = ticks_to_sec(phrases[orig_idx][0], tempo_new, tpb)
        
        if k > 0:
            prev_inicio_s, prev_dur_s = frases_coladas_info[-1]
            if orig_idx == succeeded[k-1] + 1:
                gap_s = inicio_s - (prev_inicio_s + prev_dur_s)
            else:
                gap_s = 1.0
            gap_s = max(0.01, gap_s)
            sil = work_dir / f'sil_{k:02d}.mp3'
            if make_silence_mp3(gap_s, sil):
                sequence.append(sil)
                print(f'  gap F{succeeded[k-1]+1}->F{orig_idx+1}: {gap_s:.2f}s (ajustado)')
                frases_coladas_info[-1] = (prev_inicio_s, prev_dur_s + gap_s)
        
        sequence.append(mp3_trimmed)
        frases_coladas_info.append((inicio_s, dur_s))

    print(f'\nConcatenando {len(sequence)} segmentos via filter_complex (precisão perfeita) -> {out_path.name} ...')
    inputs = []
    filter_chunks = []
    for idx, seg in enumerate(sequence):
        inputs += ['-i', str(seg.resolve())]
        filter_chunks.append(f'[{idx}:a]')
    
    # Encadeia a concatenação e o loudnorm no mesmo filter_complex
    filter_str = "".join(filter_chunks) + f"concat=n={len(sequence)}:v=0:a=1[concatout];[concatout]loudnorm=I=-16:TP=-1.5:LRA=11[outa]"
    
    cmd = ['ffmpeg', '-y'] + inputs + [
        '-filter_complex', filter_str,
        '-map', '[outa]',
        '-c:a', 'libmp3lame', '-q:a', '2', str(out_path)
    ]
    r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    shutil.rmtree(work_dir, ignore_errors=True)

    if out_path.exists():
        print(f'\nHino completo: {out_path}  ({out_path.stat().st_size//1024} KB)')
        
        # ── Fase 5: Sincronização automática de letras ───────────────────────────
        import re
        hino_id_match = re.search(r'(\d+)', Path(midi_path).name)
        if hino_id_match:
            hino_id_str = hino_id_match.group(1)
            if 'coro' in Path(midi_path).name.lower():
                hino_id_str = 'C' + hino_id_str
            sinc_script = Path(__file__).parent / 'sincronizar_letras.py'
            json_path = out_path.with_suffix('.json')
            print(f'Sincronizando letras (MIDI+MP3+TXT -> JSON) ...')
            
            r_sinc = subprocess.run([
                sys.executable, str(sinc_script),
                '--hino', hino_id_str,
                '--mp3', str(out_path),
                '--output', str(json_path)
            ], capture_output=True, text=True)
            
            if r_sinc.returncode == 0:
                print(f'  [OK] Letras sincronizadas gravadas em: {json_path.name}')
            else:
                print(f'  [AVISO] Falha ao sincronizar letras (rc={r_sinc.returncode})')
                if r_sinc.stderr.strip():
                    print(f'  STDERR do alinhador:\n{r_sinc.stderr.strip()}')
        
        print(f'{"="*60}\n')
        return True
    else:
        print(f'ERRO concat:\n{r.stderr.decode()}'); return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--midi',  required=True)
    parser.add_argument('--out',   required=True)
    parser.add_argument('--bpm',   type=float, default=60.0)
    parser.add_argument('--speed', type=float, default=None)
    args = parser.parse_args()
    ok = gerar_hino_completo(args.midi, args.out, args.bpm, args.speed)
    sys.exit(0 if ok else 1)
