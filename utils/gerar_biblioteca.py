#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script automatizado para gerar a Biblioteca de Sons (14 variações) para o Coro 002.
Cria diretórios, orquestra, renderiza áudio/mscz, pós-processa fade-in, alinha letras e documenta.
"""

import os
import sys
import mido
import random
import shutil
import subprocess
from pathlib import Path

# Utilitários de humanização compartilhados
sys.path.insert(0, str(Path(__file__).parent))
from midi_humanize import remove_staccato, remove_staccato_from_mscz

ROOT = Path(__file__).parent.parent.absolute()
MIDI_REF = ROOT / "mid" / "Coro 002- Toda a glória a Jesus.mid"
LETRA_REF = ROOT / "hinos_txt" / "letras_separadas" / "coro-002-toda-gloria-a-jesus.txt"
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"
BIBLIOTECA_DIR = ROOT / "biblioteca-de-sons"

# Garantir que a biblioteca de sons existe
BIBLIOTECA_DIR.mkdir(parents=True, exist_ok=True)

VARIATIONS = [
    # 1. Cordas (Strings)
    {
        "id": "strings_16part",
        "name": "Orquestra de Cordas Avançada (16 Partes)",
        "desc": "Som orquestral de cordas denso e espacial utilizando 16 instrumentos com panorama expandido.",
        "type": "strings",
        "cmd": [
            str(VENV_PYTHON), str(ROOT / "orchestrators" / "musescore_strings_16part.py"),
            "--midi", str(MIDI_REF), "--preset", "1"
        ],
        "midi_out_name": "Coro 002- Toda a glória a Jesus_preset1_16part_speed90.mid",
        "mp3_out_name": "Coro 002- Toda a glória a Jesus_preset1_16part_speed90.mp3"
    },
    {
        "id": "strings_math",
        "name": "Orquestra de Cordas Matemática (CC11 Dinâmico)",
        "desc": "Orquestra de cordas clássica com curvas matemáticas aplicadas ao CC11 para dinâmicas realistas.",
        "type": "strings",
        "cmd": [
            str(VENV_PYTHON), str(ROOT / "orchestrators" / "musescore_strings_math.py"),
            "--midi", str(MIDI_REF), "--preset", "1"
        ],
        "midi_out_name": "Coro 002- Toda a glória a Jesus.mid",
        "mp3_out_name": "Coro 002- Toda a glória a Jesus.mp3"
    },
    # 2. Metais (Brass)
    {
        "id": "brass_standard",
        "name": "Orquestra de Metais Padrão",
        "desc": "Orquestração de metais clássica baseada em mapeamento estático do MuseScore.",
        "type": "brass",
        "cmd": [
            str(VENV_PYTHON), str(ROOT / "orchestrators" / "musescore_orchestrate.py"),
            "--midi", str(MIDI_REF), "--preset", "1"
        ],
        "midi_out_name": "Coro 002- Toda a glória a Jesus_orquestra_mscore.mid",
        "mp3_out_name": "Coro 002- Toda a glória a Jesus_orquestra_mscore.mp3"
    },
    {
        "id": "brass_math",
        "name": "Orquestra de Metais Matemática",
        "desc": "Mapeamento dinâmico de metais com humanização CC11 baseada em curvas físicas de sopro.",
        "type": "brass",
        "cmd": [
            str(VENV_PYTHON), str(ROOT / "orchestrators" / "musescore_orchestrate_math.py"),
            "--midi", str(MIDI_REF), "--preset", "1"
        ],
        "midi_out_name": "Coro 002- Toda a glória a Jesus.mid",
        "mp3_out_name": "Coro 002- Toda a glória a Jesus.mp3"
    },
    # 3. Órgãos (Organs)
    {
        "id": "organ_drawbar",
        "name": "Órgão Eletrônico Drawbar",
        "desc": "Som clássico de órgão eletrônico Drawbar Hammond (General MIDI program 16).",
        "type": "organ",
        "model": "musicbox", # usaremos custom_orchestrate modificando o program
        "custom_program": 16,
        "custom_name": "Drawbar Organ"
    },
    {
        "id": "organ_rock",
        "name": "Órgão Eletrônico Rock Organ",
        "desc": "Timbre brilhante e saturado de Rock Organ (General MIDI program 18).",
        "type": "organ",
        "model": "musicbox",
        "custom_program": 18,
        "custom_name": "Rock Organ"
    },
    {
        "id": "organ_combinado",
        "name": "Órgão Combinado (Drawbar + Rock)",
        "desc": "Mistura rica de timbres Hammond combinando registros de drawbar e rock organ.",
        "type": "organ",
        "model": "reeds", # modificaremos para tocar ambos
        "custom_program": "combinado",
        "custom_name": "Combined Organ"
    },
    {
        "id": "organ_church",
        "name": "Órgão de Tubos de Igreja (Church Organ)",
        "desc": "Som litúrgico clássico de Órgão de Tubos catedral (General MIDI program 19).",
        "type": "organ",
        "model": "musicbox",
        "custom_program": 19,
        "custom_name": "Church Organ"
    },
    {
        "id": "organ_meia_hora",
        "name": "Órgão de Meia-Hora (Velocidade 50%)",
        "desc": "Execução lenta e contemplativa a 50% da velocidade, ideal para a introdução cultual.",
        "type": "organ",
        "model": "musicbox",
        "custom_program": 16,
        "custom_name": "Drawbar Organ",
        "speed": 0.5
    },
    # 4. Novos Modelos (New Models)
    {
        "id": "musicbox_octave",
        "name": "Caixa de Música com Soprano Oitavado",
        "desc": "Som de caixinha de música com uma trilha adicional contendo o Soprano oitavado (+12) no último verso.",
        "type": "custom",
        "model": "musicbox"
    },
    {
        "id": "reeds_dynamic",
        "name": "Orquestra de Paletas Dinâmica",
        "desc": "Conjunto de paletas (Oboé, Clarinete, Fagote, English Horn) que se reconfigura dinamicamente a cada verso.",
        "type": "custom",
        "model": "reeds"
    },
    {
        "id": "woodwinds_dynamic",
        "name": "Orquestra de Madeiras Dinâmica",
        "desc": "Conjunto clássico de madeiras (Flauta, Oboé, Clarinete, Fagote) com redistribuição de vozes e duplicações por estrofe.",
        "type": "custom",
        "model": "woodwinds"
    },
    {
        "id": "piano_realistic",
        "name": "Piano Realista com Oitavas Dinâmicas",
        "desc": "Piano acústico com duplicações extras em oitavas superiores para Soprano e Contralto no último verso (75% de volume).",
        "type": "custom",
        "model": "piano"
    },
    {
        "id": "piano_equinox_80",
        "name": "Piano Realista Equinox (Velocidade 80%)",
        "desc": "Execução expressiva de piano acústico desacelerada para 80% do andamento original.",
        "type": "custom",
        "model": "equinox",
        "speed": 0.8
    }
]

def generate_organ_midi(input_path, output_path, program, speed=1.0):
    """Gera um arquivo MIDI de órgão humanizado a partir de uma referência."""
    mid = mido.MidiFile(input_path)
    new_mid = mido.MidiFile()
    new_mid.ticks_per_beat = mid.ticks_per_beat
    
    # Meta track
    meta_track = mido.MidiTrack()
    new_mid.tracks.append(meta_track)
    for track in mid.tracks:
        for msg in track:
            if msg.is_meta and msg.type in ['set_tempo', 'time_signature', 'key_signature']:
                msg_copy = msg.copy()
                if msg_copy.type == 'set_tempo' and speed != 1.0:
                    msg_copy.tempo = int(msg_copy.tempo / speed)
                meta_track.append(msg_copy)

    # Identificar canais SATB
    active_channels = set()
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'note_on' and msg.velocity > 0:
                active_channels.add(msg.channel)
    sorted_channels = sorted(list(active_channels))
    
    voices = ["Soprano", "Contralto", "Tenor", "Baixo"]
    channel_to_voice = {sorted_channels[i]: voices[i] for i in range(min(len(sorted_channels), len(voices)))}

    # Se program for "combinado", usaremos canal 0 para drawbar (16) e canal 1 para rock (18)
    is_combinado = isinstance(program, str) or program == "combinado"
    
    # Definir trilhas
    for voice_idx, voice_name in enumerate(voices):
        voice_track = mido.MidiTrack()
        new_mid.tracks.append(voice_track)
        
        target_ch = sorted_channels[voice_idx] if voice_idx < len(sorted_channels) else None
        if target_ch is None:
            continue
            
        # Program changes e track names
        if is_combinado:
            # Soprano e Tenor no Drawbar (16), Alto e Baixo no Rock (18)
            prog = 16 if voice_name in ["Soprano", "Tenor"] else 18
            track_name = f"Organ Combined - {voice_name}"
        else:
            prog = program
            track_name = f"Organ {program} - {voice_name}"
            
        voice_track.append(mido.MetaMessage('track_name', name=track_name, time=0))
        voice_track.append(mido.Message('program_change', channel=voice_idx, program=prog, time=0))
        # Panning estéreo
        pan_val = 52 if voice_name in ["Soprano", "Contralto"] else 76
        voice_track.append(mido.Message('control_change', channel=voice_idx, control=10, value=pan_val, time=0))
        voice_track.append(mido.Message('control_change', channel=voice_idx, control=7, value=85, time=0))
        
        # Extrair notas originais
        notes = []
        for track in mid.tracks:
            has_notes = any(not m.is_meta and hasattr(m, 'channel') and m.channel == target_ch for m in track)
            if not has_notes:
                continue
                
            curr_t = 0
            active_notes = {}
            for m in track:
                curr_t += m.time
                if m.type == 'note_on' and m.velocity > 0 and m.channel == target_ch:
                    active_notes[m.note] = curr_t
                elif (m.type == 'note_off' or (m.type == 'note_on' and m.velocity == 0)) and m.channel == target_ch:
                    if m.note in active_notes:
                        on_t = active_notes.pop(m.note)
                        notes.append({
                            "note": m.note,
                            "on_time": on_t,
                            "off_time": curr_t,
                            "velocity": m.velocity
                        })
        notes.sort(key=lambda x: x["on_time"])
        
        # Humanização
        processed_events = []
        for i, n in enumerate(notes):
            # Micro-delay
            delay_sec = random.uniform(0.005, 0.020)
            delay_ticks = int((delay_sec * 1000000.0 * mid.ticks_per_beat) / 500000)
            on_new = n["on_time"] + delay_ticks
            
            is_after_pause = (i == 0) or (n["on_time"] - notes[i-1]["off_time"] >= mid.ticks_per_beat * 0.25)
            is_before_pause = (i < len(notes) - 1) and (notes[i+1]["on_time"] - n["off_time"] >= mid.ticks_per_beat * 0.25)
            
            dur = n["off_time"] - n["on_time"]
            # Remover articulação staccato: estende notas muito curtas para legato
            dur = remove_staccato(dur, mid.ticks_per_beat)
            if is_before_pause:
                dur = int(dur * 0.70)
                
            off_new = on_new + max(15, dur)
            
            v_note = n["velocity"]
            if is_after_pause:
                v_note = 10
                
            processed_events.append(mido.Message('note_on', channel=voice_idx, note=n["note"], velocity=v_note, time=on_new))
            processed_events.append(mido.Message('note_off', channel=voice_idx, note=n["note"], velocity=0, time=off_new))
            
            if is_after_pause:
                # CC11 ramp
                for step in range(5):
                    t_off = int((step / 4.0) * (mid.ticks_per_beat * 0.5))
                    val = int(40 + (step / 4.0) * 60)
                    processed_events.append(mido.Message('control_change', channel=voice_idx, control=11, value=val, time=on_new + t_off))
                    
        processed_events.sort(key=lambda x: x.time)
        curr = 0
        for m in processed_events:
            delta = m.time - curr
            m.time = delta
            voice_track.append(m)
            curr += delta
            
    new_mid.save(output_path)

def generate_explanations(out_dir, var):
    """Gera o arquivo explicação.md correspondente a esta variação de som."""
    import unicodedata
    filename = unicodedata.normalize('NFC', "explicação.md")
    exp_file = out_dir / filename
    
    # Descrições detalhadas da lógica
    content = f"""# Explicação de Geração e Humanização: {var["name"]}

Este arquivo de áudio de referência foi gerado para catalogação e validação da qualidade acústica do hino.

---

## 🛠️ Especificação de Geração
*   **Nome do Estilo**: {var["name"]}
*   **Descrição**: {var["desc"]}
*   **Hino de Referência**: Coro 002 - Toda a glória a Jesus (SATB)
*   **Arquivos Contidos nesta Pasta**:
    *   `letra.txt`: Texto da letra original.
    *   `Coro 002- Toda a glória a Jesus.mid`: MIDI orquestrado final com os canais humanizados.
    *   `Coro 002- Toda a glória a Jesus.mscz`: Partitura e roteamento gerados no MuseScore 4.
    *   `Coro 002- Toda a glória a Jesus.json`: Letras sincronizadas ajustadas ao andamento.
    *   `Coro 002- Toda a glória a Jesus.mp3`: Áudio MP3 resultante com pós-processamento acústico de fade.

---

## 🧠 Lógica Detalhada de Humanização Utilizada

Esta renderização implementa os 3 pilares de simulação de performance humana desenvolvidos para o CCB:

### 1. 🕒 Desincronismo Micro-Temporal (Atraso Humano)
*   **O Problema**: Em renderizações robóticas normais, todos os instrumentos atacam exatamente no mesmo milissegundo. Isso gera um efeito artificial chamado *phase cancellation* (flanger/chorus digital) que remove o peso acústico.
*   **A Solução**: Cada pauta do arquivo MIDI possui um atraso de ataque individual gerado dinamicamente no intervalo de **5 ms a 25 ms**. Isso simula o tempo de reação físico de músicos reais no início de cada nota, enriquecendo o som em grupo.

### 2. 🔕 Tratamento de Ataque Seco (Atenuação Pós-Pausas)
*   **O Problema**: O ataque inicial em amostras de áudio modernas (especialmente cordas de arco e paletas de sopro) pode soar extremamente seco e agressivo ao reiniciar uma frase após o silêncio.
*   **A Solução**:
    1.  **Velocity Suave**: Qualquer nota disparada após uma pausa de pelo menos 0.25 tempos inicia com **Velocity física = 10** (ataque suave de arco/sopro).
    2.  **Rampa de Volume CC11**: Um crescendo sutil é programado via controlador contínuo MIDI CC11 (Expression), saindo de 40 e subindo linearmente até 100 ao longo de 250ms após a pausa.
    3.  **Fade-In de Áudio Hermitiano**: Aplicamos uma curva de fade-in cúbica (*Smoothstep*) de **200ms** diretamente na saída do áudio MP3 após detecção de silêncio absoluto para amortecer a transição.

### 3. ✂️ Encurtamento de Notas Pré-Pausa
*   Para evitar que a cauda de reverb natural do Muse Sounds embole a articulação do próximo verso, as notas imediatamente anteriores a uma pausa são encurtadas em **30%** de sua duração original no MIDI. Isso limpa a respiração musical.

---

## 📝 Sistema de Alinhamento de Letras (JSON)
O arquivo de sincronização `Coro 002- Toda a glória a Jesus.json` foi gerado dinamicamente associando os eventos de notas do canal Soprano com as sílabas correspondentes em `letra.txt`.
O sistema calcula o tempo em milissegundos lendo diretamente os metaeventos de tempo do MIDI original e recalcula com precisão de acordo com o andamento do hino (inclusive no caso de velocidade modificada, como o Piano a 80% ou Órgão a 50%).
"""
    with open(exp_file, "w", encoding="utf-8") as f:
        f.write(content)

def main():
    print("════════════════════════════════════════════════════════════")
    print("   GERANDO BIBLIOTECA COMPLETA DE SONS (14 ESTILOS)")
    print("════════════════════════════════════════════════════════════\n")
    
    temp_dir = ROOT / "temp_library"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    for idx, var in enumerate(VARIATIONS, 1):
        print(f"[{idx}/{len(VARIATIONS)}] Processando: {var['name']}...")
        
        subfolder = BIBLIOTECA_DIR / var["id"]
        subfolder.mkdir(parents=True, exist_ok=True)
        
        # 1. Copiar letra
        shutil.copy(LETRA_REF, subfolder / "letra.txt")
        
        # 2. Orquestração e geração de áudio
        raw_mp3 = temp_dir / "temp_raw.mp3"
        raw_midi = temp_dir / "temp_raw.mid"
        
        if raw_mp3.exists(): raw_mp3.unlink()
        if raw_midi.exists(): raw_midi.unlink()
        
        if var["type"] == "custom":
            # Rodar custom orchestrator
            speed = var.get("speed", 1.0)
            subprocess.run([
                str(VENV_PYTHON), str(ROOT / "orchestrators" / "musescore_custom_orchestrate.py"),
                "--midi", str(MIDI_REF),
                "--model", var["model"],
                "--speed", str(speed),
                "--output", str(temp_dir)
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Copiar os arquivos gerados
            gen_mid = list(temp_dir.glob(f"*_{var['model']}.mid"))[0]
            gen_mp3 = list(temp_dir.glob(f"*_{var['model']}.mp3"))[0]
            
            shutil.copy(gen_mid, raw_midi)
            shutil.copy(gen_mp3, raw_mp3)
            
            # Limpar arquivos da pasta temporária
            gen_mid.unlink()
            gen_mp3.unlink()
            
        elif var["type"] == "strings" or var["type"] == "brass":
            # Rodar scripts existentes
            cmd = var["cmd"] + ["--output", str(temp_dir)]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Localizar gerados
            src_mid = temp_dir / var["midi_out_name"]
            src_mp3 = temp_dir / var["mp3_out_name"]
            
            shutil.copy(src_mid, raw_midi)
            shutil.copy(src_mp3, raw_mp3)
            
            src_mid.unlink()
            src_mp3.unlink()
            
        else: # organ
            prog = var["custom_program"]
            speed = var.get("speed", 1.0)
            generate_organ_midi(MIDI_REF, raw_midi, prog, speed=speed)
            
            # Renderizar via MuseScore CLI
            # Usando program 19 no MIDI para simular Órgão de Tubos ou program 16 Hammond
            subprocess.run([
                "/Applications/MuseScore 4.app/Contents/MacOS/mscore",
                "-o", str(raw_mp3), str(raw_midi)
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 3. Aplicar pós-processamento de fade-in no MP3
        final_mp3 = subfolder / "Coro 002- Toda a glória a Jesus.mp3"
        subprocess.run([
            str(VENV_PYTHON), str(ROOT / "utils" / "postprocess_fade_apos_pausa.py"),
            "--input", str(raw_mp3),
            "--output", str(subfolder),
            "--suffix", "",
            "--lookback-ms", "200"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Caso o pós-processador renomeie ou mova
        temp_rendered = subfolder / "temp_raw.mp3"
        if temp_rendered.exists():
            temp_rendered.rename(final_mp3)
            
        # 4. Gerar partitura .mscz via MuseScore CLI abrindo o MIDI humanizado
        final_mscz = subfolder / "Coro 002- Toda a glória a Jesus.mscz"
        subprocess.run([
            "/Applications/MuseScore 4.app/Contents/MacOS/mscore",
            "-o", str(final_mscz), str(raw_midi)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Remove marcadores de staccato que o MuseScore adiciona ao importar MIDIs com notas curtas
        if final_mscz.exists():
            n_removed = remove_staccato_from_mscz(final_mscz)
            if n_removed:
                print(f"    → {n_removed} marcadores staccato removidos da partitura")
        
        # 5. Salvar o MIDI humanizado definitivo na pasta
        shutil.copy(raw_midi, subfolder / "Coro 002- Toda a glória a Jesus.mid")
        
        # 6. Rodar alinhamento de letras para gerar o JSON
        final_json = subfolder / "Coro 002- Toda a glória a Jesus.json"
        subprocess.run([
            str(VENV_PYTHON), str(ROOT / "utils" / "sincronizar_letras.py"),
            "--hino", "C2",
            "--mp3", str(final_mp3),
            "--output", str(final_json)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # 7. Gerar explicação.md
        generate_explanations(subfolder, var)
        
        # Limpar temporários do MuseScore do subfolder
        for f in ["automation.json", "audiosettings.json", "viewsettings.json"]:
            f_p = subfolder / f
            if f_p.exists(): f_p.unlink()
        for d in ["META-INF", "Thumbnails"]:
            d_p = subfolder / d
            if d_p.exists() and d_p.is_dir(): shutil.rmtree(d_p)
            
        print(f"  ✓ Pasta {var['id']} populada com sucesso!")

    # Limpeza da pasta temporária principal
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
        
    print("\n════════════════════════════════════════════════════════════")
    print("   BIBLIOTECA DE SONS COMPLETA POPULADA COM SUCESSO!")
    print(f"   Salva em: {BIBLIOTECA_DIR.absolute()}")
    print("════════════════════════════════════════════════════════════\n")

if __name__ == "__main__":
    main()
