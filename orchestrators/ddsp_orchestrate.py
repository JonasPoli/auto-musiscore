"""
DDSP Orchestrate
================
Converte MIDI SATB em áudio orquestral via DDSP Timbre Transfer.

Pipeline:
  MIDI canal 0-3 → onda senoidal → DDSP model → mix estéreo → MP3

Uso:
  python ddsp_orchestrate.py --midi 'mid/241- A Justiça divina.mid'
  python ddsp_orchestrate.py   # todos em mid/
"""

import os, sys, types, glob, argparse, pickle
import numpy as np
import mido

# ─── Mock tensorflow_datasets (arm64 binário, incompatível em x86_64) ────────
def _mock_tfds():
    mod = types.ModuleType("tensorflow_datasets")
    for sub in ["core", "core.community", "core.dataset_builder",
                "core.dataset_info", "core.file_adapters", "core.logging",
                "features", "split_lib"]:
        sys.modules["tensorflow_datasets." + sub] = types.ModuleType("tensorflow_datasets." + sub)
    sys.modules["tensorflow_datasets"] = mod

if "tensorflow_datasets" not in sys.modules:
    _mock_tfds()

# ─── Limitar threads ANTES de importar TF (evita EXC_RESOURCE no macOS) ──────
# O i9-13900KF tem 32 threads; sem limite o TF trava o scheduler do macOS.
# 4 threads é suficiente para DDSP e evita o kill do kernel.
os.environ["TF_CPP_MIN_LOG_LEVEL"]   = "3"
os.environ["OMP_NUM_THREADS"]        = "4"
os.environ["MKL_NUM_THREADS"]        = "4"
os.environ["OPENBLAS_NUM_THREADS"]   = "4"
os.environ["TF_NUM_INTEROP_THREADS"] = "4"
os.environ["TF_NUM_INTRAOP_THREADS"] = "4"

import tensorflow as tf
tf.get_logger().setLevel("ERROR")

# Limitar paralelismo do TF em runtime também
tf.config.threading.set_inter_op_parallelism_threads(4)
tf.config.threading.set_intra_op_parallelism_threads(4)

# Habilitar crescimento incremental de memória (evita alocação massiva)
gpus = tf.config.list_physical_devices('GPU')
for gpu in gpus:
    tf.config.experimental.set_memory_growth(gpu, True)

import ddsp
import ddsp.training
import ddsp.spectral_ops
import gin
import librosa
import soundfile as sf

# ─── Configuração ────────────────────────────────────────────────────────────
SAMPLE_RATE = 16000
FRAME_RATE  = 250          # frames/s para F0 e loudness
TIME_STEPS  = 1000         # tamanho do chunk (4 s @ 250 fps)
CHUNK_SAMP  = TIME_STEPS * SAMPLE_RATE // FRAME_RATE  # = 64000 samples = 4s

# Canais MIDI → instrumento + posição no mix
# Os MIDIs SATB usam canais 4-7 (Soprano=4, Contralto=5, Tenor=6, Baixo=7)
# harmonic_profile: lista de amplitudes por harmônico (1=fundamental, 2=oitava, ...)
#   violin/viola: rico em harmônicos ímpares e pares, brilhante
#   flute:        fundamental forte, harmônicos decaem rapidamente
#   trumpet:      harmônicos pares fortes, brilhante e denso
# Mapeamento de vozes para instrumentos e mixagem.
# Os canais são detectados dinamicamente nos MIDIs SATB de acordo com a ordem crescente:
# Soprano (menor canal), Contralto, Tenor, Baixo (maior canal).
VOICE_CONFIG = {
    "Soprano":   {"model": "violin",  "gain": 1.0,  "pan": -0.4, "pitch_shift":  0,
                  "harmonics": [1.0, 0.7, 0.5, 0.4, 0.3, 0.25, 0.2, 0.15, 0.1],
                  "vibrato_rate": 5.5, "vibrato_depth": 0.012, "attack": 0.06, "release": 0.12},
    "Contralto": {"model": "violin",  "gain": 0.9,  "pan":  0.4, "pitch_shift":  0,
                  "harmonics": [1.0, 0.65, 0.45, 0.35, 0.25, 0.2, 0.15, 0.1, 0.08],
                  "vibrato_rate": 5.2, "vibrato_depth": 0.010, "attack": 0.07, "release": 0.14},
    "Tenor":     {"model": "flute",   "gain": 0.85, "pan": -0.2, "pitch_shift":  0,
                  "harmonics": [1.0, 0.4, 0.15, 0.08, 0.04, 0.02],
                  "vibrato_rate": 5.8, "vibrato_depth": 0.014, "attack": 0.04, "release": 0.10},
    "Baixo":     {"model": "trumpet", "gain": 1.1,  "pan":  0.2, "pitch_shift": 12,
                  "harmonics": [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.15, 0.1],
                  "vibrato_rate": 4.8, "vibrato_depth": 0.008, "attack": 0.03, "release": 0.08},
}

# ─── 1. MIDI → áudio com harmônicos ricos ────────────────────────────────────
def _synth_note(freq: float, n_samples: int, vel: float, cfg: dict) -> np.ndarray:
    """
    Sintetiza uma nota com:
    - harmônicos ricos (perfil espectral por instrumento)
    - vibrato natural (rate + depth por voz)
    - envelope ADSR com attack/release realistas

    O sinal rico em harmônicos dá ao DDSP material espectral real
    para fazer timbre transfer, eliminando o chiado causado por senoides puras.
    """
    t_arr     = np.arange(n_samples) / SAMPLE_RATE
    harmonics = cfg.get("harmonics",     [1.0, 0.5, 0.3, 0.2, 0.1])
    vib_rate  = cfg.get("vibrato_rate",  5.5)
    vib_depth = cfg.get("vibrato_depth", 0.010)
    atk_s     = cfg.get("attack",  0.06)
    rel_s     = cfg.get("release", 0.12)

    # Vibrato: modulação leve de frequência (começa após o attack)
    vib_onset = min(int(0.15 * SAMPLE_RATE), n_samples // 4)
    vib_env   = np.zeros(n_samples)
    if vib_onset < n_samples:
        fade = min(int(0.08 * SAMPLE_RATE), n_samples - vib_onset)
        vib_env[vib_onset:vib_onset + fade] = np.linspace(0, 1, fade)
        vib_env[vib_onset + fade:]          = 1.0
    vib      = vib_depth * vib_env * np.sin(2 * np.pi * vib_rate * t_arr)
    freq_mod = freq * (1.0 + vib)   # frequência com vibrato

    # Fase acumulada (garante continuidade mesmo com freq variável)
    phase = np.cumsum(2 * np.pi * freq_mod / SAMPLE_RATE)

    # Soma de harmônicos (série de Fourier do instrumento)
    wave = np.zeros(n_samples)
    norm = sum(harmonics)
    for k, amp in enumerate(harmonics, start=1):
        if freq * k >= SAMPLE_RATE / 2:   # ignora acima de Nyquist
            break
        wave += (amp / norm) * np.sin(k * phase)

    # Envelope ADSR
    env = np.ones(n_samples)
    a   = min(int(atk_s * SAMPLE_RATE), n_samples // 4)
    r   = min(int(rel_s * SAMPLE_RATE), n_samples // 3)
    if a > 0: env[:a]            = np.linspace(0.0, 1.0, a)
    if r > 0: env[n_samples - r:] = np.linspace(1.0, 0.0, r)

    return (vel / 127.0) * 0.75 * env * wave


def midi_channel_to_audio(midi_path: str, channel: int, cfg: dict) -> np.ndarray:
    """Sintetiza um canal MIDI como áudio monofônico rico em harmônicos (16 kHz)."""
    mid   = mido.MidiFile(midi_path)
    tempo = 500000
    for track in mid.tracks:
        for msg in track:
            if msg.type == "set_tempo":
                tempo = msg.tempo
                break

    events = []
    for track in mid.tracks:
        tick = 0
        for msg in track:
            tick += msg.time
            if not hasattr(msg, "channel") or msg.channel != channel:
                continue
            t = mido.tick2second(tick, mid.ticks_per_beat, tempo)
            if msg.type == "note_on" and msg.velocity > 0:
                events.append(("on",  t, msg.note, msg.velocity))
            elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                events.append(("off", t, msg.note, 0))

    events.sort(key=lambda e: e[1])
    if not events:
        return np.zeros(SAMPLE_RATE, dtype=np.float32)

    total = events[-1][1] + 1.5
    audio = np.zeros(int(total * SAMPLE_RATE), dtype=np.float64)
    active = {}

    for ev, t, note, vel in events:
        s = int(t * SAMPLE_RATE)
        if ev == "on":
            active[note] = (s, vel)
        elif ev == "off" and note in active:
            s0, v = active.pop(note)
            s1 = s
            if s1 <= s0:
                continue
            freq       = 440.0 * (2.0 ** ((note - 69) / 12.0))
            n          = s1 - s0
            note_audio = _synth_note(freq, n, v, cfg)
            audio[s0:s1] += note_audio

    mx = np.abs(audio).max()
    if mx > 0:
        audio = audio / mx * 0.88
    return audio.astype(np.float32)


# ─── 2. Carrega modelo DDSP ──────────────────────────────────────────────────
_model_cache = {}

def load_model(model_dir: str):
    if model_dir in _model_cache:
        return _model_cache[model_dir]

    gin_file = os.path.join(model_dir, "operative_config-0.gin")
    if not os.path.exists(gin_file):
        raise FileNotFoundError(f"Gin não encontrado: {gin_file}\nExecute primeiro: bash setup_ddsp.sh")

    gin.clear_config()
    with gin.unlock_config():
        gin.parse_config_file(gin_file, skip_unknown=True)

    model = ddsp.training.models.Autoencoder()

    # Dummy forward para inicializar pesos
    dummy = {
        "audio":       tf.zeros([1, CHUNK_SAMP]),
        "f0_hz":       tf.zeros([1, TIME_STEPS, 1]),
        "loudness_db": tf.zeros([1, TIME_STEPS, 1]),
    }
    model(dummy, training=False)

    # Restaura checkpoint
    ckpt_path = tf.train.latest_checkpoint(model_dir)
    if not ckpt_path:
        raise FileNotFoundError(f"Checkpoint não encontrado em: {model_dir}")
    tf.train.Checkpoint(model=model).restore(ckpt_path).expect_partial()

    _model_cache[model_dir] = model
    return model


# ─── 3. Timbre Transfer em chunks de 4s ─────────────────────────────────────
def _transfer_chunk(chunk: np.ndarray, model, pitch_shift: int) -> np.ndarray:
    """Aplica DDSP timbre transfer a um chunk de CHUNK_SAMP samples."""
    # compute_f0(audio, frame_rate, viterbi=True)
    f0_hz, _  = ddsp.spectral_ops.compute_f0(chunk, FRAME_RATE, viterbi=True)
    # compute_loudness com use_tf=False → retorna numpy (não EagerTensor)
    loud_db   = ddsp.spectral_ops.compute_loudness(
        chunk, sample_rate=SAMPLE_RATE, frame_rate=FRAME_RATE, use_tf=False
    )

    # Ajuste de pitch
    if pitch_shift != 0:
        f0_hz = f0_hz * (2.0 ** (pitch_shift / 12.0))

    n    = min(len(f0_hz), len(loud_db), TIME_STEPS)
    f0   = np.array(f0_hz[:n], dtype=np.float32)[np.newaxis, :, np.newaxis]
    loud = np.array(loud_db[:n], dtype=np.float32)[np.newaxis, :, np.newaxis]
    aud  = chunk[:n * SAMPLE_RATE // FRAME_RATE].astype(np.float32)[np.newaxis, :]

    feat = {
        "audio":       tf.constant(aud),
        "f0_hz":       tf.constant(f0),
        "loudness_db": tf.constant(loud),
    }
    out = model(feat, training=False)
    return np.array(out["audio_synth"])[0]


def timbre_transfer(audio: np.ndarray, model, pitch_shift: int = 0) -> np.ndarray:
    """Aplica DDSP timbre transfer ao áudio completo, processando em chunks."""
    # Pad para múltiplo de CHUNK_SAMP
    n_chunks = max(1, int(np.ceil(len(audio) / CHUNK_SAMP)))
    padded   = np.pad(audio, (0, n_chunks * CHUNK_SAMP - len(audio)))

    dur_total = len(audio) / SAMPLE_RATE
    chunks_out = []
    for i in range(n_chunks):
        t_start = i * CHUNK_SAMP / SAMPLE_RATE
        print(f"    chunk {i+1}/{n_chunks}  ({t_start:.1f}s – {min(t_start+4, dur_total):.1f}s)",
              end="", flush=True)
        chunk = padded[i * CHUNK_SAMP:(i + 1) * CHUNK_SAMP]
        out   = _transfer_chunk(chunk, model, pitch_shift)
        chunks_out.append(out)
        print(" ✓")

    return np.concatenate(chunks_out)[:len(audio)]


# ─── 4. Mix estéreo ──────────────────────────────────────────────────────────
def mix_voices(voice_audios: list, configs: list) -> np.ndarray:
    max_len = max(len(a) for a in voice_audios)
    left  = np.zeros(max_len, dtype=np.float32)
    right = np.zeros(max_len, dtype=np.float32)

    for audio, cfg in zip(voice_audios, configs):
        if len(audio) < max_len:
            audio = np.pad(audio, (0, max_len - len(audio)))
        g   = cfg["gain"]
        pan = cfg["pan"]
        left  += g * max(0.0, 1 - pan)  * audio
        right += g * max(0.0, 1 + pan)  * audio

    stereo = np.stack([left, right], axis=-1)
    mx = np.abs(stereo).max()
    if mx > 0:
        stereo = stereo / mx * 0.9
    return stereo.astype(np.float32)


# ─── 5. Processa um arquivo MIDI ─────────────────────────────────────────────
def process_midi(midi_path: str, output_dir: str, models_dir: str):
    name    = os.path.splitext(os.path.basename(midi_path))[0]
    out_mp3 = os.path.join(output_dir, name + "_orquestra.mp3")

    if os.path.exists(out_mp3):
        print(f"  [já existe] {os.path.basename(out_mp3)}")
        return

    print(f"\n{'─'*60}")
    print(f"  {name}")

    # Detectar dinamicamente os canais com notas ativas no MIDI
    active_channels = set()
    mid = mido.MidiFile(midi_path)
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'note_on' and msg.velocity > 0:
                active_channels.add(msg.channel)
    sorted_channels = sorted(list(active_channels))

    if len(sorted_channels) != 4:
        print(f"  AVISO: Esperava 4 canais com notas, encontreu {len(sorted_channels)}: {sorted_channels}")

    voices = ["Soprano", "Contralto", "Tenor", "Baixo"]
    voice_audios, voice_cfgs = [], []

    for idx, voice_name in enumerate(voices):
        if idx >= len(sorted_channels):
            break
        ch = sorted_channels[idx]
        cfg = VOICE_CONFIG[voice_name].copy()
        cfg["name"] = voice_name

        print(f"  [{voice_name} (ch {ch})] MIDI→audio...", end="", flush=True)
        raw = midi_channel_to_audio(midi_path, ch, cfg)

        if np.abs(raw).max() < 0.001:
            print(" (vazio, pulando)")
            continue

        model_dir = os.path.join(models_dir, cfg["model"])
        print(f" DDSP {cfg['model']}...", end="", flush=True)
        model = load_model(model_dir)
        result = timbre_transfer(raw, model, pitch_shift=cfg["pitch_shift"])
        print(" ✓")

        voice_audios.append(result)
        voice_cfgs.append(cfg)

    if not voice_audios:
        print("  AVISO: nenhuma voz encontrada.")
        return

    print("  Mixando...", end="", flush=True)
    stereo = mix_voices(voice_audios, voice_cfgs)

    tmp_wav = out_mp3.replace(".mp3", "_tmp.wav")
    sf.write(tmp_wav, stereo, SAMPLE_RATE)
    ret = os.system(f'ffmpeg -loglevel error -i "{tmp_wav}" -q:a 2 "{out_mp3}" -y')
    os.remove(tmp_wav)

    if ret == 0:
        kb = os.path.getsize(out_mp3) // 1024
        print(f" salvo ({kb} KB)")
    else:
        print(" ERRO ffmpeg")


# ─── 6. Processa áudio direto (MP3/WAV → timbre transfer) ───────────────────
def process_audio(audio_path: str, output_dir: str, models_dir: str,
                  model_name: str = "violin", pitch_shift: int = 0):
    """Aplica timbre transfer em um arquivo de áudio (MP3/WAV) diretamente."""
    name    = os.path.splitext(os.path.basename(audio_path))[0]
    out_mp3 = os.path.join(output_dir, name + f"_{model_name}.mp3")

    print(f"\n{'─'*60}")
    print(f"  {name}  →  modelo: {model_name}")

    # Carrega e converte para mono 16 kHz
    print(f"  Carregando áudio...", end="", flush=True)
    audio, sr = librosa.load(audio_path, sr=SAMPLE_RATE, mono=True)
    print(f" {len(audio)/SAMPLE_RATE:.1f}s @ {SAMPLE_RATE} Hz")

    model_dir = os.path.join(models_dir, model_name)
    print(f"  DDSP {model_name}...", end="", flush=True)
    model  = load_model(model_dir)
    result = timbre_transfer(audio, model, pitch_shift=pitch_shift)
    print(" ✓")

    # Salva como MP3
    tmp_wav = out_mp3.replace(".mp3", "_tmp.wav")
    sf.write(tmp_wav, result, SAMPLE_RATE)
    ret = os.system(f'ffmpeg -loglevel error -i "{tmp_wav}" -q:a 2 "{out_mp3}" -y')
    os.remove(tmp_wav)

    if ret == 0:
        kb = os.path.getsize(out_mp3) // 1024
        print(f"  Salvo: {out_mp3} ({kb} KB)")
    else:
        print("  ERRO ffmpeg")


# ─── 7. Main ─────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="DDSP: MIDI SATB → orquestra / áudio → timbre transfer")
    ap.add_argument("--midi",        default=None,          help="Arquivo MIDI específico")
    ap.add_argument("--audio",       default=None,          help="Arquivo de áudio (MP3/WAV) para timbre transfer direto")
    ap.add_argument("--audio-model", default="violin",      help="Modelo para --audio (violin/flute/trumpet)")
    ap.add_argument("--input",       default="mid",         help="Pasta de MIDIs (batch)")
    ap.add_argument("--output",      default="output/ddsp", help="Pasta de saída")
    ap.add_argument("--models",      default="models",      help="Pasta de modelos")
    args = ap.parse_args()

    os.makedirs(args.output, exist_ok=True)

    # ── Modo áudio direto ──
    if args.audio:
        print(f"Carregando modelo {args.audio_model}...")
        load_model(os.path.join(args.models, args.audio_model))
        print(" ✓")
        process_audio(args.audio, args.output, args.models,
                      model_name=args.audio_model)
        print("\n✓ Concluído!")
        return

    # ── Modo MIDI ──
    needed = set(v["model"] for v in VOICE_CONFIG.values())
    print("Carregando modelos DDSP...")
    for name in needed:
        d = os.path.join(args.models, name)
        print(f"  {name}...", end="", flush=True)
        try:
            load_model(d)
            print(" ✓")
        except Exception as e:
            print(f"\nERRO: {e}")
            sys.exit(1)
    print()

    midi_files = [args.midi] if args.midi else sorted(glob.glob(os.path.join(args.input, "*.mid")))
    print(f"{len(midi_files)} arquivo(s) → {args.output}/")

    for i, path in enumerate(midi_files, 1):
        print(f"[{i}/{len(midi_files)}]", end=" ")
        try:
            process_midi(path, args.output, args.models)
        except Exception as e:
            print(f"ERRO: {e}")

    print(f"\n✓ Concluído!")


if __name__ == "__main__":
    main()
