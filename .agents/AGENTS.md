# Regras do Agente - Repositório `ia-music`

Este arquivo define regras de comportamento e padrões de desenvolvimento para a geração, pós-processamento, sincronização de letras e documentação de novos modelos de som no projeto.

---

## 🎹 1. Regras de Humanização Acústica (Obrigatório para Qualquer Som)

Qualquer script orquestrador ou gerador de som novo deve implementar e documentar estritamente os seguintes processos de humanização:

1.  **Desincronismo Micro-Temporal (Timing Offset)**:
    *   Músicos reais não atacam notas no mesmo instante exato. Cada pauta/voz de um instrumento deve possuir um atraso aleatório independente de **5 ms a 25 ms** para evitar o cancelamento de fase digital (flanger/chorus) e dar densidade acústica.
2.  **Atenuação de Ataque Pós-Pausa (Velocity & CC11 Ramp)**:
    *   A primeira nota tocada por uma voz após um silêncio (pausa >= 0.25 tempos) deve ter a velocidade inicial limitada a **Velocity = 10**.
    *   Deve ser programado um crescendo dinâmico via controlador MIDI **CC11 (Expression)** subindo de 40 a 100 ao longo de 200 ms a 250 ms.
    *   No nível do áudio renderizado final, deve ser aplicado um pós-processamento de fade-in de **200 ms** usando uma curva Hermitiana (Smoothstep) para amortecer o atrito inicial de arcos de cordas ou sopro de paletas.
3.  **Encurtamento Pré-Pausa**:
    *   Notas que precedem uma pausa (silêncio >= 0.25 tempos) devem ser encurtadas em **30%** de sua duração original no arquivo MIDI para limpar a articulação do reverb natural.

---

## 📁 2. Estrutura da Biblioteca de Sons (`biblioteca-de-sons/`)

Para qualquer modelo de som de referência adicionado ao catálogo, crie uma subpasta exclusiva contendo:
1.  `explicação.md`: Detalhando as especificações de instrumentos, o cálculo dos atrasos e as curvas de dinâmica aplicadas.
2.  `letra.txt`: A letra original utilizada.
3.  `[Nome do Hino].mid`: O arquivo MIDI orquestrado e humanizado.
4.  `[Nome do Hino].mscz`: A partitura correspondente gerada pelo MuseScore.
5.  `[Nome do Hino].json`: O alinhamento de letras sincronizado gerado de forma compatível com a velocidade de reprodução.
6.  `[Nome do Hino].mp3`: O áudio humanizado final com fade-in.

---

## 🔧 3. Preservação de Auto-Limpeza do MuseScore

Toda execução de subprocesso do MuseScore CLI (`mscore`) deve ser envolvida em um bloco `try-finally` para remover imediatamente os resíduos criados na pasta de destino, tais como:
*   Arquivos: `automation.json`, `audiosettings.json`, `viewsettings.json`.
*   Diretórios: `META-INF/`, `Thumbnails/`.
