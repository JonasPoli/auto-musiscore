#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
utils/midi_humanize.py
======================
Funções utilitárias compartilhadas de humanização MIDI.
Importado por todos os orquestradores do projeto.
"""
import os
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


def remove_staccato(duration: int, ticks_per_beat: int, threshold: float = 0.5, target: float = 0.85) -> int:
    """
    Corrige notas com articulação staccato, estendendo-as para uma duração mínima.

    Em partituras corais SATB digitalizadas, o MuseScore frequentemente marca
    frações de beat como staccato (duração < 50% do beat). Isso soa mecânico e
    percussivo em qualquer renderização de orquestra de cordas, metais, madeiras
    ou órgão, onde o legato/tenuto é a articulação natural.

    Regra:
        Se duration < threshold * ticks_per_beat
            → duration = target * ticks_per_beat   (estende para articulação legato)
        Caso contrário, mantém a duração original.

    Parâmetros:
        duration       : Duração original da nota em ticks MIDI.
        ticks_per_beat : Resolução do arquivo MIDI (ticks por semínima).
        threshold      : Fração do beat abaixo da qual a nota é considerada staccato.
                         Padrão: 0.5 (metade do beat = colcheia).
        target         : Fração do beat para a qual a nota staccato é estendida.
                         Padrão: 0.85 (ligeiramente legato sem invadir a próxima nota).

    Retorna:
        Duração corrigida em ticks (int).
    """
    staccato_threshold = int(threshold * ticks_per_beat)
    target_duration    = int(target * ticks_per_beat)

    if duration < staccato_threshold:
        return target_duration
    return duration


def remove_staccato_from_mscz(mscz_path) -> int:
    """
    Remove TODAS as marcações de staccato e staccatissimo de um arquivo .mscz
    do MuseScore, editando diretamente o XML interno da partitura.

    O .mscz é um arquivo ZIP contendo um .mscx (XML). O MuseScore adiciona
    automaticamente articulações de staccato ao importar MIDIs com notas curtas.
    Esta função remove esses marcadores do XML para que a reprodução e impressão
    da partitura usem articulação legato/normal.

    Atributos de Articulation removidos:
        name="staccato", name="staccatissimo", name="sforzatoStaccato",
        name="marcatoStaccato"

    Parâmetros:
        mscz_path : Caminho para o arquivo .mscz (str ou Path).

    Retorna:
        Número total de articulações staccato removidas.
    """
    import zipfile
    import os
    import tempfile
    import xml.etree.ElementTree as ET
    from pathlib import Path

    mscz_path = Path(mscz_path)
    if not mscz_path.exists():
        return 0

    # Subtipos de staccato a remover pelo atributo 'name' do elemento Articulation
    STACCATO_NAMES = {
        # MuseScore 4 (atributo name=)
        'staccato', 'staccatissimo',
        'sforzatoStaccato', 'marcatoStaccato',
        # MuseScore 4 (elemento <subtype>)
        'articStaccatoAbove', 'articStaccatoBelow',
        'articStaccatissimoAbove', 'articStaccatissimoBelow',
        'articMarcatoStaccatoAbove', 'articMarcatoStaccatoBelow',
        'articAccentStaccatoAbove', 'articAccentStaccatoBelow',
    }

    removed_count = 0

    with tempfile.TemporaryDirectory() as tmp:
        # 1. Extrai o ZIP do MSCZ
        with zipfile.ZipFile(mscz_path, 'r') as zf:
            namelist = zf.namelist()
            zf.extractall(tmp)

        # 2. Processa cada .mscx encontrado
        for fname in namelist:
            if not fname.endswith('.mscx'):
                continue

            fpath = os.path.join(tmp, fname)

            # Lê o XML preservando encoding
            with open(fpath, 'rb') as f:
                raw_xml = f.read()

            tree = ET.ElementTree(ET.fromstring(raw_xml))
            root_el = tree.getroot()

            # Remove <Articulation name="staccato"> e variantes
            for parent in root_el.iter():
                to_remove = []
                for child in list(parent):
                    if child.tag == 'Articulation':
                        # MuseScore 4: atributo name=""
                        art_name = child.get('name', '')
                        # MuseScore 3: elemento filho <subtype>
                        subtype_el = child.find('subtype')
                        subtype_text = (subtype_el.text or '') if subtype_el is not None else ''

                        if art_name in STACCATO_NAMES or subtype_text in STACCATO_NAMES:
                            to_remove.append(child)

                for child in to_remove:
                    parent.remove(child)
                    removed_count += 1

            # Reescreve o XML
            tree.write(fpath, encoding='unicode', xml_declaration=False)

        # 3. Recompacta o ZIP mantendo a estrutura original
        tmp_out = str(mscz_path) + '.patched'
        with zipfile.ZipFile(tmp_out, 'w', zipfile.ZIP_DEFLATED) as zf_out:
            for fname in namelist:
                fpath = os.path.join(tmp, fname)
                if os.path.exists(fpath):
                    zf_out.write(fpath, fname)

        # 4. Substitui o arquivo original
        os.replace(tmp_out, mscz_path)

    return removed_count


def set_pan_in_mscz(mscz_path, channel_pan_map: dict) -> int:
    """
    Injeta controller MIDI CC10 (pan) em cada <Channel> do MSCX.
    Usado como fallback para exportação MIDI e instrumentos MS Basic.
    MuseScore 4 MuseSounds ignora CC10 — o pan visual no Mixer requer
    que o usuário ajuste manualmente e salve no MuseScore GUI.

    Parâmetros:
        mscz_path       : Path para o arquivo .mscz
        channel_pan_map : dict {midi_channel_int: pan_cc10_value}
                          16 ≈ esquerda total · 64 = centro · 112 ≈ direita total

    Retorna: número de <Channel> modificados
    """
    import io
    mscz_path = Path(mscz_path)
    if not mscz_path.exists() or not channel_pan_map:
        return 0

    with zipfile.ZipFile(mscz_path, 'r') as zin:
        names = zin.namelist()
        mscx_name = next((n for n in names if n.endswith('.mscx')), None)
        if not mscx_name:
            return 0
        mscx_data   = zin.read(mscx_name)
        other_files = {n: zin.read(n) for n in names if n != mscx_name}

    try:
        root = ET.fromstring(mscx_data)
    except ET.ParseError:
        return 0

    n_modified = 0
    for part in root.findall('.//Part'):
        for instrument in part.findall('Instrument'):
            arco = (instrument.find("Channel[@name='arco']") or
                    instrument.find("Channel[@name='normal']") or
                    instrument.find('Channel'))
            if arco is None:
                continue
            midi_ch_el = arco.find('midiChannel')
            if midi_ch_el is None:
                continue
            try:
                midi_ch = int(midi_ch_el.text)
            except (ValueError, TypeError):
                continue

            cc10 = channel_pan_map.get(midi_ch)
            if cc10 is None:
                continue

            for channel in instrument.findall('Channel'):
                for ctrl in list(channel.findall('controller')):
                    if ctrl.get('ctrl') == '10':
                        channel.remove(ctrl)

                # Insere antes do <midiChannel> (mantém legibilidade do XML)
                midi_ch_tag = channel.find('midiChannel')
                insert_pos = (list(channel).index(midi_ch_tag)
                              if midi_ch_tag is not None else 0)

                ctrl_el = ET.Element('controller')
                ctrl_el.set('ctrl', '10')
                ctrl_el.set('value', str(cc10))
                channel.insert(insert_pos, ctrl_el)
                n_modified += 1

    if n_modified == 0:
        return 0

    # Serializa de volta para bytes UTF-8
    buf = io.BytesIO()
    ET.ElementTree(root).write(buf, encoding='utf-8', xml_declaration=True)

    tmp_out = str(mscz_path) + '.pan_tmp'
    with zipfile.ZipFile(tmp_out, 'w', zipfile.ZIP_DEFLATED) as zout:
        zout.writestr(mscx_name, buf.getvalue())
        for name, data in other_files.items():
            zout.writestr(name, data)

    os.replace(tmp_out, str(mscz_path))
    return n_modified


def set_tempo_in_mscz(mscz_path, bpm: float) -> bool:
    """
    Injeta o elemento <Tempo> no primeiro compasso do MSCX para que o
    MuseScore 4 exiba e reproduza o BPM correto (em vez do padrão 120).

    Formato confirmado pelos arquivos de referência do projeto:
        <Tempo>
          <tempo>BPS</tempo>              BPS = BPM / 60
          <followText>1</followText>
          <eid>...</eid>
          <text><sym>metNoteQuarterUp</sym><font face="Edwin"/> = BPM</text>
        </Tempo>

    Usa inserção direta de string (não ElementTree) para preservar as tags
    <sym> e <font> dentro de <text>, que o ElementTree escaparia.

    Posição: logo após </TimeSig> na primeira voz do primeiro compasso.

    Parâmetros:
        mscz_path : Path para o arquivo .mscz
        bpm       : BPM desejado (ex: 60.0)

    Retorna: True se inserido com sucesso.
    """
    import re
    mscz_path = Path(mscz_path)
    if not mscz_path.exists():
        return False

    bps = bpm / 60.0
    bps_str = str(int(bps)) if bps == int(bps) else str(round(bps, 6))
    bpm_int = int(round(bpm))

    tempo_block = (
        f'\n          <Tempo>'
        f'\n            <tempo>{bps_str}</tempo>'
        f'\n            <followText>1</followText>'
        f'\n            <eid>tempo_auto_{bpm_int}</eid>'
        f'\n            <text><sym>metNoteQuarterUp</sym>'
        f'<font face="Edwin"/> = {bpm_int}</text>'
        f'\n          </Tempo>'
    )

    with zipfile.ZipFile(mscz_path, 'r') as zin:
        names = zin.namelist()
        mscx_name = next((n for n in names if n.endswith('.mscx')), None)
        if not mscx_name:
            return False
        mscx_bytes = zin.read(mscx_name)
        other_files = {n: zin.read(n) for n in names if n != mscx_name}

    mscx = mscx_bytes.decode('utf-8')

    # Remove qualquer <Tempo> existente (para evitar duplicatas)
    mscx = re.sub(r'\s*<Tempo>.*?</Tempo>', '', mscx, flags=re.DOTALL)

    # Insere após </TimeSig> na primeira ocorrência (primeiro compasso)
    mscx, n = re.subn(r'(</TimeSig>)', r'\1' + tempo_block, mscx, count=1)
    if n == 0:
        # Fallback: insere após </KeySig>
        mscx, n = re.subn(r'(</KeySig>)', r'\1' + tempo_block, mscx, count=1)

    if n == 0:
        return False

    tmp_out = str(mscz_path) + '.tempo_tmp'
    with zipfile.ZipFile(tmp_out, 'w', zipfile.ZIP_DEFLATED) as zout:
        zout.writestr(mscx_name, mscx.encode('utf-8'))
        for name, data in other_files.items():
            zout.writestr(name, data)

    os.replace(tmp_out, str(mscz_path))
    return True


def build_and_inject_audiosettings_pan(mscz_path, channel_pan_map: dict) -> int:
    """
    Constrói o audiosettings.json completo (formato array MuseSounds) e injeta no MSCZ.

    Descoberta do usuário: o MuseScore 4 CLI respeita `out.balance` no audiosettings.json
    quando o arquivo usa o formato ARRAY com muse_sampler_sound_pack (MuseSounds).
    O formato DICT (templates) e o formato array vazio são ignorados.

    MuseSounds IDs extraídos do arquivo ajustado pelo próprio usuário:
        strings.violin  → uid=103 (Violin 1 Solo, primary) / 104 (Violin 2 Solo, secondary)
        strings.viola   → uid=105 (Viola Solo)
        strings.cello   → uid=106 (Violoncello Solo)
        brass.trumpet   → uid=110 (Trumpet)
        brass.trombone  → uid=111 (Trombone)

    Instrumentos sem UID conhecido → MS Basic (com balance correto igualmente).

    Retorna: número de tracks com balance != 0 (com pan aplicado).
    """
    import json as _json

    mscz_path = Path(mscz_path)
    if not mscz_path.exists():
        return 0

    def cc10_to_balance(cc10: int) -> float:
        return -1.0 if cc10 < 64 else 1.0

    # ── Lookup: instrumentId (MSCX) → MuseSounds metadata ─────────────────────
    # Para multi-ocorrências (violin), fornece lista ordenada por ocorrência.
    _MUSE_LOOKUP = {
        # Cordas (extraídos do arquivo ajustado do usuário)
        'strings.violin': [
            {'uid': '103', 'instr_id': 'violin',     'name': 'Violin 1 (Solo)',      'setup': 'strings.violin.orchestral:primary',   'cat': 'Muse Strings', 'pack': 'Muse Strings'},
            {'uid': '104', 'instr_id': 'violin',     'name': 'Violin 2 (Solo)',      'setup': 'strings.violin.orchestral:secondary', 'cat': 'Muse Strings', 'pack': 'Muse Strings'},
        ],
        'strings.viola':      {'uid': '105', 'instr_id': 'viola',       'name': 'Viola (Solo)',         'setup': 'strings.viola.orchestral',           'cat': 'Muse Strings', 'pack': 'Muse Strings'},
        'strings.cello':      {'uid': '106', 'instr_id': 'violoncello', 'name': 'Violoncello (Solo)',   'setup': 'strings.violoncello.orchestral',     'cat': 'Muse Strings', 'pack': 'Muse Strings'},
        'strings.contrabass': {'uid': '107', 'instr_id': 'contrabass',  'name': 'Contrabasses (Solo)',  'setup': 'strings.contrabass.orchestral',      'cat': 'Muse Strings', 'pack': 'Muse Strings'},
        'strings.double-bass':{'uid': '107', 'instr_id': 'contrabass',  'name': 'Contrabasses (Solo)',  'setup': 'strings.contrabass.orchestral',      'cat': 'Muse Strings', 'pack': 'Muse Strings'},
        # Metais (dos arquivos da biblioteca brass_standard)
        'brass.trumpet':      {'uid': '110', 'instr_id': 'bb-trumpet',  'name': 'Trumpet',             'setup': 'winds.trumpet',                      'cat': 'Muse Brass',   'pack': 'Muse Brass'},
        'brass.trombone':     {'uid': '111', 'instr_id': 'trombone',    'name': 'Trombone',            'setup': 'winds.trombone',                     'cat': 'Muse Brass',   'pack': 'Muse Brass'},
        'brass.french-horn':  {'uid': '112', 'instr_id': 'horn',             'name': 'Horn in F',           'setup': 'winds.horn',                         'cat': 'Muse Brass',     'pack': 'Muse Brass'},
        'brass.tuba':         {'uid': '113', 'instr_id': 'tuba',             'name': 'Tuba',                'setup': 'winds.tuba',                         'cat': 'Muse Brass',     'pack': 'Muse Brass'},
        'brass.flugelhorn':   {'uid': '114', 'instr_id': 'flugelhorn',       'name': 'Flugelhorn',          'setup': 'winds.flugelhorn',                   'cat': 'Muse Brass',     'pack': 'Muse Brass'},
        'brass.cornet':       {'uid': '115', 'instr_id': 'cornet',           'name': 'Cornet',              'setup': 'winds.cornet',                       'cat': 'Muse Brass',     'pack': 'Muse Brass'},
        'brass.tenor-horn':   {'uid': '116', 'instr_id': 'alto-horn',        'name': 'Alto Horn',           'setup': 'winds.alto_horn',                    'cat': 'Muse Brass',     'pack': 'Muse Brass'},
        'brass.baritone-horn':{'uid': '117', 'instr_id': 'baritone',         'name': 'Baritone Horn',       'setup': 'winds.baritone',                     'cat': 'Muse Brass',     'pack': 'Muse Brass'},
        'brass.euphonium':    {'uid': '118', 'instr_id': 'euphonium',        'name': 'Euphonium',           'setup': 'winds.euphonium',                    'cat': 'Muse Brass',     'pack': 'Muse Brass'},

        # Madeiras (Muse Woodwinds)
        'woodwind.flutes.flute':      {'uid': '120', 'instr_id': 'flute',            'name': 'Flute',               'setup': 'winds.flute',                        'cat': 'Muse Woodwinds', 'pack': 'Muse Woodwinds'},
        'woodwind.flutes.piccolo':    {'uid': '125', 'instr_id': 'piccolo',          'name': 'Piccolo',             'setup': 'winds.piccolo',                      'cat': 'Muse Woodwinds', 'pack': 'Muse Woodwinds'},
        'woodwind.reed.oboe':         {'uid': '121', 'instr_id': 'oboe',             'name': 'Oboe',                'setup': 'winds.oboe',                         'cat': 'Muse Woodwinds', 'pack': 'Muse Woodwinds'},
        'wind.reed.oboe':             {'uid': '121', 'instr_id': 'oboe',             'name': 'Oboe',                'setup': 'winds.oboe',                         'cat': 'Muse Woodwinds', 'pack': 'Muse Woodwinds'},
        
        # English Horn mapeado para French Horns a6 (seção) conforme alterado pelo usuário para corpo do som e evitar mudez
        'woodwind.reed.english-horn': {'uid': '96',  'instr_id': 'english-horn',     'name': 'Horns a6',            'setup': 'winds.horn.french:in_a:section',     'cat': 'Muse Brass',     'pack': 'Muse Brass'},
        'wind.reed.english-horn':     {'uid': '96',  'instr_id': 'english-horn',     'name': 'Horns a6',            'setup': 'winds.horn.french:in_a:section',     'cat': 'Muse Brass',     'pack': 'Muse Brass'},
        
        # Clarinetes corrigidos (uid 127, setup específico winds.clarinet.soprano:in_b_flat)
        'woodwind.reed.clarinet':     {'uid': '127', 'instr_id': 'bflat-clarinet',   'name': 'Clarinet in Bb',      'setup': 'winds.clarinet.soprano:in_b_flat',   'cat': 'Muse Woodwinds', 'pack': 'Muse Woodwinds'},
        'wind.reed.clarinet':         {'uid': '127', 'instr_id': 'bflat-clarinet',   'name': 'Clarinet in Bb',      'setup': 'winds.clarinet.soprano:in_b_flat',   'cat': 'Muse Woodwinds', 'pack': 'Muse Woodwinds'},
        'wind.reed.clarinet.bflat':   {'uid': '127', 'instr_id': 'bflat-clarinet',   'name': 'Clarinet in Bb',      'setup': 'winds.clarinet.soprano:in_b_flat',   'cat': 'Muse Woodwinds', 'pack': 'Muse Woodwinds'},
        
        'woodwind.reed.bassoon':      {'uid': '123', 'instr_id': 'bassoon',          'name': 'Bassoon',             'setup': 'winds.bassoon',                      'cat': 'Muse Woodwinds', 'pack': 'Muse Woodwinds'},
        'wind.reed.bassoon':          {'uid': '123', 'instr_id': 'bassoon',          'name': 'Bassoon',             'setup': 'winds.bassoon',                      'cat': 'Muse Woodwinds', 'pack': 'Muse Woodwinds'},
        
        # Contrabassoon corrigido (uid 134 e não 126)
        'woodwind.reed.contrabassoon':{'uid': '134', 'instr_id': 'contrabassoon',    'name': 'Contrabassoon',       'setup': 'winds.contrabassoon',                'cat': 'Muse Woodwinds', 'pack': 'Muse Woodwinds'},
        'wind.reed.contrabassoon':    {'uid': '134', 'instr_id': 'contrabassoon',    'name': 'Contrabassoon',       'setup': 'winds.contrabassoon',                'cat': 'Muse Woodwinds', 'pack': 'Muse Woodwinds'},

        # Saxofones corrigidos (Soprano=129/setup, Alto=130/setup, Tenor=131/setup, Baritone=132/setup)
        'wind.reed.saxophone.soprano':{'uid': '129', 'instr_id': 'soprano-sax',      'name': 'Soprano Sax',         'setup': 'winds.saxophone.soprano',            'cat': 'Muse Woodwinds', 'pack': 'Muse Woodwinds'},
        'wind.reed.saxophone.alto':   {'uid': '130', 'instr_id': 'alto-sax',         'name': 'Alto Sax',            'setup': 'winds.saxophone.alto',               'cat': 'Muse Woodwinds', 'pack': 'Muse Woodwinds'},
        'wind.reed.saxophone.tenor':  {'uid': '131', 'instr_id': 'tenor-sax',        'name': 'Tenor Sax',           'setup': 'winds.saxophone.tenor',              'cat': 'Muse Woodwinds', 'pack': 'Muse Woodwinds'},
        'wind.reed.saxophone.baritone':{'uid': '132','instr_id': 'baritone-sax',     'name': 'Baritone Sax',        'setup': 'winds.saxophone.baritone',           'cat': 'Muse Woodwinds', 'pack': 'Muse Woodwinds'},
        'wind.reed.saxophone.bass':   {'uid': '132','instr_id': 'baritone-sax',     'name': 'Baritone Sax',        'setup': 'winds.saxophone.baritone',           'cat': 'Muse Woodwinds', 'pack': 'Muse Woodwinds'},
        
        'wind.reed.saxophone.contrabass':{'uid':'132','instr_id':'contrabass-saxophone', 'name': 'Baritone Sax',        'setup': 'winds.saxophone.baritone',           'cat': 'Muse Woodwinds', 'pack': 'Muse Woodwinds'},
        'wind.reed.saxophone.subcontrabass':{'uid':'132','instr_id':'subcontrabass-saxophone', 'name': 'Baritone Sax',  'setup': 'winds.saxophone.baritone',           'cat': 'Muse Woodwinds', 'pack': 'Muse Woodwinds'},
        
        'sax.soprano':                {'uid': '129', 'instr_id': 'soprano-sax',      'name': 'Soprano Sax',         'setup': 'winds.saxophone.soprano',            'cat': 'Muse Woodwinds', 'pack': 'Muse Woodwinds'},
        'sax.alto':                   {'uid': '130', 'instr_id': 'alto-sax',         'name': 'Alto Sax',            'setup': 'winds.saxophone.alto',               'cat': 'Muse Woodwinds', 'pack': 'Muse Woodwinds'},
        'sax.tenor':                  {'uid': '131', 'instr_id': 'tenor-sax',        'name': 'Tenor Sax',           'setup': 'winds.saxophone.tenor',              'cat': 'Muse Woodwinds', 'pack': 'Muse Woodwinds'},
        'sax.baritone':               {'uid': '132', 'instr_id': 'baritone-sax',     'name': 'Baritone Sax',        'setup': 'winds.saxophone.baritone',           'cat': 'Muse Woodwinds', 'pack': 'Muse Woodwinds'},
        'sax.bass':                   {'uid': '132', 'instr_id': 'baritone-sax',     'name': 'Baritone Sax',        'setup': 'winds.saxophone.baritone',           'cat': 'Muse Woodwinds', 'pack': 'Muse Woodwinds'},

        # Vozes (dos arquivos mid/)
        'voice.soprano':      {'uid': '19',  'instr_id': 'soprano',     'name': 'Sopranos',            'setup': 'voices.choir.soprano',               'cat': 'Muse Choir',   'pack': 'Muse Choir'},
        'voice.mezzo-soprano':{'uid': '19',  'instr_id': 'soprano',     'name': 'Sopranos',            'setup': 'voices.choir.soprano',               'cat': 'Muse Choir',   'pack': 'Muse Choir'},
        'voice.alto':         {'uid': '20',  'instr_id': 'alto',        'name': 'Altos',               'setup': 'voices.choir.alto',                  'cat': 'Muse Choir',   'pack': 'Muse Choir'},
        'voice.tenor':        {'uid': '21',  'instr_id': 'tenor',       'name': 'Tenors',              'setup': 'voices.choir.tenor',                 'cat': 'Muse Choir',   'pack': 'Muse Choir'},
        'voice.bass':         {'uid': '22',  'instr_id': 'bass',        'name': 'Basses',              'setup': 'voices.choir.bass',                  'cat': 'Muse Choir',   'pack': 'Muse Choir'},
        'strings.contrabass':         {'uid': '132', 'instr_id': 'baritone-sax',     'name': 'Baritone Sax',        'setup': 'winds.saxophone.baritone',           'cat': 'Muse Woodwinds', 'pack': 'Muse Woodwinds'},
        'strings.contrabass.orchestral': {'uid': '132', 'instr_id': 'baritone-sax',     'name': 'Baritone Sax',        'setup': 'winds.saxophone.baritone',           'cat': 'Muse Woodwinds', 'pack': 'Muse Woodwinds'},
        'keyboard.piano':     {'uid': '201', 'instr_id': 'grand-piano', 'name': 'Grand Piano',          'setup': 'keys.piano',                         'cat': 'Muse Keys',    'pack': 'Muse Keys'},
    }

    # ── Lê MSCX ───────────────────────────────────────────────────────────────
    audio_settings = None
    with zipfile.ZipFile(mscz_path, 'r') as zin:
        names     = zin.namelist()
        mscx_name = next((n for n in names if n.endswith('.mscx')), None)
        if not mscx_name:
            return 0
        mscx_data   = zin.read(mscx_name)
        other_files = {n: zin.read(n) for n in names
                       if n not in (mscx_name, 'audiosettings.json')}
        if 'audiosettings.json' in names:
            try:
                audio_settings = _json.loads(zin.read('audiosettings.json').decode('utf-8'))
            except:
                pass

    try:
        root = ET.fromstring(mscx_data)
    except ET.ParseError:
        return 0

    # Extrai parts em ordem: (partId, instrumentId_mscx, midiChannel)
    # Fallback ao índice sequencial quando <midiChannel> não existe (ex: sopros de madeira)
    # pois o MuseScore importa Parts na ordem dos canais MIDI → Part 0 = canal 0, etc.
    parts = []
    part_idx = 0
    for part in root.findall('.//Part'):
        pid = part.get('id', '')
        for inst in part.findall('Instrument'):
            iid_mscx = inst.findtext('instrumentId', '')
            midi_ch_val = part_idx  # fallback: índice da Part
            for ch_selector in ("Channel[@name='arco']", "Channel[@name='normal']", 'Channel'):
                ch = inst.find(ch_selector)
                if ch is not None:
                    el = ch.find('midiChannel')
                    if el is not None:
                        try:
                            midi_ch_val = int(el.text)
                        except (ValueError, TypeError):
                            pass  # mantém fallback por índice
                    break
            parts.append((pid, iid_mscx, midi_ch_val))
            part_idx += 1

    if not parts:
        return 0


    # ── Constrói/Atualiza tracks do audiosettings.json ─────────────────────────
    occurrence: dict = {}
    n_panned = 0

    AUX_SENDS = [
        {'active': True, 'signalAmount': 0.4000000059604645},
        {'active': True, 'signalAmount': 0.30000001192092896},
    ]

    ordered_pans = channel_pan_map.get('ordered_pans', [])
    ordered_vols = channel_pan_map.get('ordered_vols', [])
    import math as _math

    def obter_mixer_id(iid_mscx: str) -> str:
        parts_key = iid_mscx.split('.')
        short = parts_key[-1]
        if 'saxophone' in iid_mscx or 'sax' in iid_mscx:
            if short in ('soprano', 'alto', 'tenor', 'baritone', 'bass', 'contrabass', 'subcontrabass'):
                return f"{short}-saxophone"
        if iid_mscx.endswith('clarinet') or iid_mscx.endswith('clarinet.bflat'):
            return 'bflat-clarinet'
        if iid_mscx.endswith('french-horn'):
            return 'french-horn'
        if short == 'piano':
            return 'grand-piano'
        return short

    # Dicionário de mapeamento partId -> (iid_mscx, midi_ch, idx)
    part_map = {pid: (iid_mscx, midi_ch, idx) for idx, (pid, iid_mscx, midi_ch) in enumerate(parts)}

    # Se já temos o audiosettings.json gerado nativamente pelo MuseScore E ele contém tracks válidas, apenas atualizamos!
    if audio_settings and 'tracks' in audio_settings and len(audio_settings['tracks']) > 0:
        for track in audio_settings['tracks']:
            pid = track.get('partId')
            if pid in part_map:
                iid_mscx, midi_ch, idx = part_map[pid]
                
                # Pan
                pan_val = ordered_pans[idx] if ordered_pans and idx < len(ordered_pans) else channel_pan_map.get(midi_ch, 64)
                balance = cc10_to_balance(pan_val)
                if balance != 0.0:
                    n_panned += 1
                
                # Volume
                vol_midi = 90
                if ordered_vols and idx < len(ordered_vols):
                    vol_midi = ordered_vols[idx]
                vol_db = -60.0 if vol_midi <= 0 else 20 * _math.log10(vol_midi / 90.0)
                vol_db = max(-20.0, min(6.0, vol_db))
                
                # Configura out
                track['out'] = track.get('out', {})
                track['out']['balance'] = balance
                track['out']['volumeDb'] = vol_db
                track['out']['auxSends'] = AUX_SENDS
                track['soloMuteState'] = track.get('soloMuteState', {'mute': False, 'solo': False})
                
                # Injeta Sampler / SoundFont
                occ = occurrence.get(iid_mscx, 0)
                occurrence[iid_mscx] = occ + 1
                
                muse_info = _MUSE_LOOKUP.get(iid_mscx)
                if isinstance(muse_info, list):
                    muse_info = muse_info[min(occ, len(muse_info) - 1)]
                    
                if muse_info:
                    # Track MuseSounds - Mantém o track['instrumentId'] original do MuseScore!
                    track['in'] = {
                        'resourceMeta': {
                            'attributes': {
                                'museCategory':    muse_info['cat'],
                                'museName':        muse_info['name'],
                                'musePack':        muse_info['pack'],
                                'museUID':         muse_info['uid'],
                                'museVendorName':  'Muse',
                                'playbackSetupData': muse_info['setup'],
                            },
                            'hasNativeEditorSupport': False,
                            'id':     muse_info['uid'],
                            'type':   'muse_sampler_sound_pack',
                            'vendor': 'MuseSounds',
                        },
                        'unitConfiguration': {},
                    }
                else:
                    # Track MS Basic (fallback)
                    instr_id_short = track.get('instrumentId')  # Mantém o ID nativo da track!
                    if not instr_id_short:
                        instr_id_short = obter_mixer_id(iid_mscx)
                    track['in'] = {
                        'resourceMeta': {
                            'attributes': {
                                'soundFontName': 'MS Basic',
                            },
                            'hasNativeEditorSupport': False,
                            'id':     'MS Basic',
                            'type':   'fluid_soundfont',
                            'vendor': 'Fluid',
                        },
                        'unitConfiguration': {},
                    }
                    track['instrumentId'] = instr_id_short
    else:
        # Fallback: Se não havia audiosettings.json prévio ou ele estava vazio, reconstrói do zero
        tracks = []
        for idx, (pid, iid_mscx, midi_ch) in enumerate(parts):
            pan_val = ordered_pans[idx] if ordered_pans and idx < len(ordered_pans) else channel_pan_map.get(midi_ch, 64)
            balance = cc10_to_balance(pan_val)
            if balance != 0.0:
                n_panned += 1
                
            vol_midi = 90
            if ordered_vols and idx < len(ordered_vols):
                vol_midi = ordered_vols[idx]
            vol_db = -60.0 if vol_midi <= 0 else 20 * _math.log10(vol_midi / 90.0)
            vol_db = max(-20.0, min(6.0, vol_db))
            
            occ = occurrence.get(iid_mscx, 0)
            occurrence[iid_mscx] = occ + 1
            
            muse_info = _MUSE_LOOKUP.get(iid_mscx)
            if isinstance(muse_info, list):
                muse_info = muse_info[min(occ, len(muse_info) - 1)]
                
            mixer_id = obter_mixer_id(iid_mscx)
            if muse_info:
                track = {
                    'in': {
                        'resourceMeta': {
                            'attributes': {
                                'museCategory':    muse_info['cat'],
                                'museName':        muse_info['name'],
                                'musePack':        muse_info['pack'],
                                'museUID':         muse_info['uid'],
                                'museVendorName':  'Muse',
                                'playbackSetupData': muse_info['setup'],
                            },
                            'hasNativeEditorSupport': False,
                            'id':     muse_info['uid'],
                            'type':   'muse_sampler_sound_pack',
                            'vendor': 'MuseSounds',
                        },
                        'unitConfiguration': {},
                    },
                    'instrumentId': mixer_id,
                    'out': {
                        'auxSends':  AUX_SENDS,
                        'balance':   balance,
                        'fxChain':   {},
                        'volumeDb':  vol_db,
                    },
                    'partId': pid,
                    'soloMuteState': {'mute': False, 'solo': False},
                }
            else:
                track = {
                    'in': {
                        'resourceMeta': {
                            'attributes': {
                                'soundFontName': 'MS Basic',
                            },
                            'hasNativeEditorSupport': False,
                            'id':     'MS Basic',
                            'type':   'fluid_soundfont',
                            'vendor': 'Fluid',
                        },
                        'unitConfiguration': {},
                    },
                    'instrumentId': mixer_id,
                    'out': {
                        'balance':   balance,
                        'fxChain':   {},
                        'volumeDb':  vol_db,
                    },
                    'partId': pid,
                    'soloMuteState': {'mute': False, 'solo': False},
                }
            tracks.append(track)
            
        audio_settings = {
            'activeSoundProfile': 'MuseSounds',
            'aux': [
                {
                    'out': {
                        'balance': 0,
                        'fxChain': {
                            '0': {
                                'active': True,
                                'chainOrder': 0,
                                'resourceMeta': {
                                    'attributes': {},
                                    'hasNativeEditorSupport': True,
                                    'id':     'Muse Reverb',
                                    'type':   'muse_plugin',
                                    'vendor': 'Muse',
                                },
                                'unitConfiguration': {},
                            }
                        },
                        'volumeDb': 0,
                    },
                    'soloMuteState': {'mute': False, 'solo': False},
                },
                {
                    'out': {'balance': 0, 'fxChain': {}, 'volumeDb': 0},
                    'soloMuteState': {'mute': False, 'solo': False},
                },
            ],
            'master': {'balance': 0, 'fxChain': {}, 'volumeDb': 0},
            'tracks': tracks,
        }

    # ── Injeta no MSCZ ────────────────────────────────────────────────────────
    tmp_out = str(mscz_path) + '.audio_tmp'
    with zipfile.ZipFile(tmp_out, 'w', zipfile.ZIP_DEFLATED) as zout:
        zout.writestr(mscx_name, mscx_data)
        zout.writestr('audiosettings.json',
                      _json.dumps(audio_settings, indent=2, ensure_ascii=False).encode('utf-8'))
        for name, data in other_files.items():
            zout.writestr(name, data)

    os.replace(tmp_out, str(mscz_path))
    return n_panned


def ajustar_ultimo_compasso_mscz(mscz_path) -> int:
    """
    Remove pausas extras (silêncio de compasso) no final de cada frase,
    ajustando a duração do último compasso da partitura (.mscz) para coincidir
    exatamente com a nota final.
    """
    import zipfile
    import shutil
    import os
    import xml.etree.ElementTree as ET
    from pathlib import Path
    from fractions import Fraction

    mscz_path = Path(mscz_path)
    if not mscz_path.exists():
        return 0

    # ── Lê MSCX ───────────────────────────────────────────────────────────────
    with zipfile.ZipFile(mscz_path, 'r') as zin:
        names     = zin.namelist()
        mscx_name = next((n for n in names if n.endswith('.mscx')), None)
        if not mscx_name:
            return 0
        mscx_data   = zin.read(mscx_name)
        other_files = {n: zin.read(n) for n in names
                       if n not in (mscx_name, 'audiosettings.json')}

    try:
        root = ET.fromstring(mscx_data)
    except ET.ParseError:
        return 0

    # Mapeamento de duração MuseScore para frações de semibreve
    dur_map = {
        'maxima': Fraction(8, 1),
        'longa': Fraction(4, 1),
        'breve': Fraction(2, 1),
        'whole': Fraction(1, 1),
        'half': Fraction(1, 2),
        'quarter': Fraction(1, 4),
        'eighth': Fraction(1, 8),
        'sixteenth': Fraction(1, 16),
        'thirty-two': Fraction(1, 32),
        '64th': Fraction(1, 64),
        '128th': Fraction(1, 128)
    }

    staves = root.findall('.//Staff')
    if not staves:
        return 0

    # ── Remove compassos 100% silenciosos do final ────────────────────────────
    while True:
        staff1_measures = staves[0].findall('Measure')
        if not staff1_measures:
            break
        last_measure_idx = len(staff1_measures) - 1
        
        has_chords = False
        for staff in staves:
            measures = staff.findall('Measure')
            if len(measures) <= last_measure_idx:
                continue
            last_measure = measures[last_measure_idx]
            voice = last_measure.find('voice')
            if voice is not None:
                if voice.find('Chord') is not None:
                    has_chords = True
                    break
        
        if not has_chords:
            for staff in staves:
                measures = staff.findall('Measure')
                if len(measures) > last_measure_idx:
                    staff.remove(measures[last_measure_idx])
            continue
        else:
            break

    # ── Encurta o compasso final (que agora garantidamente tem notas) ─────────
    staff1_measures = staves[0].findall('Measure')
    if not staff1_measures:
        return 0
    last_measure_idx = len(staff1_measures) - 1
    
    max_duration_semibreve = Fraction(0, 1)
    for staff in staves:
        measures = staff.findall('Measure')
        if len(measures) <= last_measure_idx:
            continue
        last_measure = measures[last_measure_idx]
        
        voice = last_measure.find('voice')
        if voice is None:
            continue
            
        elements = list(voice)
        last_chord_idx = -1
        for idx, child in enumerate(elements):
            if child.tag == 'Chord':
                last_chord_idx = idx
                
        if last_chord_idx == -1:
            continue
            
        duration = Fraction(0, 1)
        for idx in range(last_chord_idx + 1):
            child = elements[idx]
            if child.tag in ('Chord', 'Rest'):
                dtype = child.findtext('durationType', 'quarter')
                dots_el = child.find('dots')
                dots = int(dots_el.text) if dots_el is not None else 0
                
                base_dur = dur_map.get(dtype, Fraction(1, 4))
                multiplier = Fraction(1, 1)
                for i in range(1, dots + 1):
                    multiplier += Fraction(1, 2**i)
                
                duration += base_dur * multiplier
                
        if duration > max_duration_semibreve:
            max_duration_semibreve = duration

    if max_duration_semibreve == Fraction(0, 1):
        return 0
        
    n_modified = 0
    actual_str = f"{max_duration_semibreve.numerator}/{max_duration_semibreve.denominator}"
    
    for staff in staves:
        measures = staff.findall('Measure')
        if len(measures) <= last_measure_idx:
            continue
        last_measure = measures[last_measure_idx]
        
        for old_len in last_measure.findall('len'):
            last_measure.remove(old_len)
            
        len_el = ET.Element('len', actual=actual_str)
        last_measure.insert(0, len_el)
        
        voice = last_measure.find('voice')
        if voice is not None:
            elements = list(voice)
            last_chord_idx = -1
            for idx, child in enumerate(elements):
                if child.tag == 'Chord':
                    last_chord_idx = idx
            
            if last_chord_idx != -1:
                for idx in range(len(elements) - 1, last_chord_idx, -1):
                    child = elements[idx]
                    if child.tag == 'Rest':
                        voice.remove(child)
        n_modified += 1

    new_mscx_data = ET.tostring(root, encoding='utf-8')
    
    import tempfile
    temp_dir = Path(tempfile.mkdtemp())
    try:
        temp_mscz = temp_dir / mscz_path.name
        with zipfile.ZipFile(temp_mscz, 'w', zipfile.ZIP_DEFLATED) as zout:
            zout.writestr(mscx_name, new_mscx_data)
            for n, data in other_files.items():
                zout.writestr(n, data)
        shutil.move(temp_mscz, mscz_path)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return n_modified

