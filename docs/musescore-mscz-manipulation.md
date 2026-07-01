# Manipulação Programática de Arquivos `.mscz` — MuseScore 4

> **Resumo:** Um `.mscz` é um arquivo ZIP contendo principalmente `score.mscx` (XML da partitura)
> e `audiosettings.json` (configurações de mixer/playback). Manipular esses dois arquivos
> permite controlar **tempo (BPM)** e **balanço estéreo (pan)** sem abrir o MuseScore.

---

## Estrutura interna de um `.mscz`

```
meu-hino.mscz
├── meu-hino.mscx          ← Partitura em XML (notas, compassos, tempo)
├── audiosettings.json     ← Mixer: volume, pan, efeitos por instrumento
├── automation.json        ← Automação (geralmente vazio)
├── viewsettings.json      ← Configurações de visualização
├── score_style.mss        ← Estilos de formatação
├── META-INF/
│   └── container.xml      ← Manifesto do ZIP
└── Thumbnails/
    └── thumbnail.png
```

Para inspecionar ou modificar:

```python
import zipfile

with zipfile.ZipFile("meu-hino.mscz", "r") as z:
    print(z.namelist())
    mscx = z.read("meu-hino.mscx").decode("utf-8")
    audio = z.read("audiosettings.json").decode("utf-8")
```

---

## 1. Controlando o Tempo (BPM) — via `score.mscx`

### Como o MuseScore armazena o BPM

O tempo é armazenado como um elemento `<Tempo>` dentro da `<voice>` do **primeiro compasso**,
logo após o `<TimeSig>`. O valor `<tempo>` está em **BPS (beats per second)**:

```
BPS = BPM ÷ 60
```

| BPM desejado | Valor `<tempo>` |
|---|---|
| 60 BPM | `1` |
| 120 BPM | `2` |
| 90 BPM | `1.5` |
| 72 BPM | `1.2` |

### Estrutura do elemento `<Tempo>` no MSCX

```xml
<voice>
  <KeySig>...</KeySig>
  <TimeSig>
    <sigN>2</sigN>
    <sigD>4</sigD>
  </TimeSig>

  <!-- Inserir aqui, antes do primeiro <Chord> -->
  <Tempo>
    <tempo>1</tempo>        <!-- BPS: 1 = 60 BPM, 2 = 120 BPM -->
    <followText>1</followText>
    <eid>qualquer_id_unico</eid>
    <text><sym>metNoteQuarterUp</sym><font face="Edwin"/> = 60</text>
  </Tempo>

  <Chord>...</Chord>   ← primeira nota
</voice>
```

> **Atenção:** O elemento correto é `<Tempo>` (não `<TempoText>`).

### Código Python para injetar o BPM

```python
import zipfile, io, xml.etree.ElementTree as ET
from pathlib import Path


def set_tempo_in_mscz(mscz_path: Path, bpm: float) -> bool:
    bps = bpm / 60.0
    bps_str = str(int(bps)) if bps == int(bps) else str(round(bps, 6))

    with zipfile.ZipFile(mscz_path, "r") as zin:
        names = zin.namelist()
        mscx_name = next(n for n in names if n.endswith(".mscx"))
        mscx_data = zin.read(mscx_name)
        other = {n: zin.read(n) for n in names if n != mscx_name}

    root = ET.fromstring(mscx_data)
    first_voice = root.find(".//Measure/voice")
    if first_voice is None:
        return False

    # Remove Tempo existente
    for t in list(first_voice.findall("Tempo")):
        first_voice.remove(t)

    # Posição: depois de KeySig/TimeSig, antes do primeiro Chord
    insert_idx = 0
    for i, child in enumerate(first_voice):
        if child.tag in ("KeySig", "TimeSig"):
            insert_idx = i + 1

    # Cria <Tempo>
    tempo_el = ET.Element("Tempo")
    ET.SubElement(tempo_el, "tempo").text = bps_str
    ET.SubElement(tempo_el, "followText").text = "1"
    ET.SubElement(tempo_el, "eid").text = "tempo_auto_generated"
    text_el = ET.SubElement(tempo_el, "text")
    text_el.text = f'<sym>metNoteQuarterUp</sym><font face="Edwin"/> = {int(round(bpm))}'

    first_voice.insert(insert_idx, tempo_el)

    buf = io.BytesIO()
    ET.ElementTree(root).write(buf, encoding="utf-8", xml_declaration=True)

    tmp = str(mscz_path) + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        zout.writestr(mscx_name, buf.getvalue())
        for name, data in other.items():
            zout.writestr(name, data)
    Path(tmp).replace(mscz_path)
    return True
```

---

## 2. Controlando o Pan (Balanço Estéreo) — via `audiosettings.json`

### Como o MuseScore 4 armazena o pan

O balanço é armazenado em `audiosettings.json` no campo `out.balance` de cada track:

| Valor de `balance` | Significado |
|---|---|
| `-1` | Som totalmente à **esquerda** |
| `0` | Som **centralizado** |
| `1` | Som totalmente à **direita** |

> **Importante:** O MuseScore 4 **ignora** o `balance` se o `audiosettings.json` tiver
> `"tracks": []`. O arquivo precisa ter sido aberto e salvo no MuseScore ao menos
> uma vez para o `audiosettings.json` ser populado com os metadados MuseSounds.

### Estrutura do `audiosettings.json`

```json
{
  "activeSoundProfile": "MuseSounds",
  "tracks": [
    {
      "in": {
        "resourceMeta": {
          "attributes": {
            "museCategory": "Muse Strings",
            "museName": "Violin 1 (Solo)",
            "museUID": "103",
            "playbackSetupData": "strings.violin.orchestral:primary"
          },
          "id": "103",
          "type": "muse_sampler_sound_pack",
          "vendor": "MuseSounds"
        },
        "unitConfiguration": {}
      },
      "instrumentId": "violin",
      "out": {
        "balance": 1,        ← -1 = esq · 0 = centro · 1 = dir
        "fxChain": {},
        "volumeDb": 0
      },
      "partId": "1"          ← id do <Part> correspondente no MSCX
    }
  ]
}
```

### Código Python para ajustar o balance

```python
import zipfile, json
from pathlib import Path


def set_balance_in_mscz(mscz_path: Path, part_balance: dict) -> int:
    """
    part_balance = {"1": 1, "2": -1, "3": -1, "4": 1, "5": -1}
    Requer audiosettings.json populado (tracks != []).
    Retorna número de tracks modificadas.
    """
    with zipfile.ZipFile(mscz_path, "r") as zin:
        names = zin.namelist()
        if "audiosettings.json" not in names:
            return 0
        audio = json.loads(zin.read("audiosettings.json"))
        other = {n: zin.read(n) for n in names if n != "audiosettings.json"}

    tracks = audio.get("tracks", [])
    if not tracks:
        return 0   # não populado — precisa abrir no MuseScore primeiro

    n = 0
    for track in tracks:
        pid = str(track.get("partId", ""))
        if pid in part_balance and "out" in track:
            track["out"]["balance"] = part_balance[pid]
            n += 1

    if n == 0:
        return 0

    tmp = str(mscz_path) + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        zout.writestr("audiosettings.json", json.dumps(audio, indent=2).encode())
        for name, data in other.items():
            zout.writestr(name, data)
    Path(tmp).replace(mscz_path)
    return n
```

---

## 3. Pipeline Completo recomendado

O `audiosettings.json` só é populado quando o MuseScore abre o arquivo.
Para popular via CLI, são necessários **2 passes**:

```
MIDI  ──[mscore]──►  MSCZ₁  ──[mscore]──►  MSCZ₂  (audiosettings populado)
                                                │
                                         [set_tempo_in_mscz]
                                         [set_balance_in_mscz]
                                                │
                                         MSCZ final  ──[mscore]──►  MP3
```

```python
MSCORE = "/Applications/MuseScore 4.app/Contents/MacOS/mscore"

def gerar_mscz_com_ajustes(midi_in, mscz_out, bpm, part_balance):
    tmp1 = Path(str(mscz_out) + ".pass1.mscz")
    tmp2 = Path(str(mscz_out) + ".pass2.mscz")

    # Passo 1: MIDI → MSCZ (audiosettings.json vazio)
    subprocess.run([MSCORE, "-o", str(tmp1), str(midi_in)])

    # Passo 2: MSCZ → MSCZ (MuseScore popula audiosettings.json)
    subprocess.run([MSCORE, "-o", str(tmp2), str(tmp1)])
    tmp1.unlink(missing_ok=True)

    # Passo 3: injeta BPM no MSCX
    set_tempo_in_mscz(tmp2, bpm)

    # Passo 4: ajusta balance no audiosettings.json
    set_balance_in_mscz(tmp2, part_balance)

    # Passo 5: finaliza
    tmp2.replace(mscz_out)

    # Passo 6: exporta MP3
    mp3 = Path(str(mscz_out).replace(".mscz", ".mp3"))
    subprocess.run([MSCORE, "-o", str(mp3), str(mscz_out)])
    return mp3.exists()
```

---

## 4. Regras de Balance para o Projeto ia-music

| Voz | Balance padrão |
|---|---|
| Soprano | `1` (direita) |
| Contralto | `-1` (esquerda) |
| Tenor | `1` (direita) |
| Baixo | `-1` (esquerda) |
| Metrônomo (`partId=999`) | `0` (centro — fixo) |

---

## 5. IDs MuseSounds — Cordas

| Instrumento | `instrumentId` | `museUID` | `playbackSetupData` |
|---|---|---|---|
| Violino 1 | `violin` | `103` | `strings.violin.orchestral:primary` |
| Violino 2 | `violin` | `104` | `strings.violin.orchestral:secondary` |
| Viola | `viola` | `105` | `strings.viola.orchestral` |
| Violoncelo | `violoncello` | `106` | `strings.violoncello.orchestral` |
| Contrabaixo | `contrabass` | MS Basic | `last.last.last` |

---

## 6. Diagnóstico Rápido

```python
def diagnosticar_mscz(mscz_path):
    with zipfile.ZipFile(mscz_path) as z:
        audio = json.loads(z.read("audiosettings.json"))
    tracks = audio.get("tracks", [])
    if not tracks:
        print("⚠️  tracks vazio — abra e salve no MuseScore primeiro.")
        return
    for t in tracks:
        pid = t.get("partId")
        bal = t.get("out", {}).get("balance", "?")
        iid = t.get("instrumentId", "?")
        side = "← esq" if bal == -1 else ("→ dir" if bal == 1 else "● centro")
        print(f"  Part {pid}  {iid:<20}  balance={bal:>4}  {side}")
```
