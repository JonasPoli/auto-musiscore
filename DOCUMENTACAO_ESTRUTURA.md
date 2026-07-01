# 📂 Documentação de Estrutura do Repositório (`ia-music`)

Para manter o repositório limpo e organizado, adote estritamente as regras de estrutura descritas abaixo. **Nenhum arquivo ou script novo deve ser gerado na raiz do projeto.** Todos os scripts foram organizados em subpastas de acordo com a sua finalidade.

---

## 🗺️ Mapa de Diretórios

O projeto está estruturado da seguinte forma:

### 🐍 1. Scripts e Motores Python (Código-Fonte)
Todos os scripts `.py` foram agrupados nas seguintes subpastas:
*   **`orchestrators/`** (Motores de Síntese e Renderização):
    *   `musescore_strings_16part.py`: Orquestrador avançado de cordas (16 vozes panned).
    *   `musescore_strings_math.py`: Orquestrador clássico de cordas com controle CC11 matemático.
    *   `musescore_orchestrate_math.py`: Orquestrador de metais com curvas de física dinâmicas.
    *   `musescore_orchestrate.py`: Orquestração geral simplificada via MuseScore.
    *   `ddsp_orchestrate.py`: Renderização neuronal via DDSP (Differentiable Digital Signal Processing).
    *   `orchestrate.py`: Renderização SoundFont básica via FluidSynth.
*   **`pipelines/`** (Automação e Lotes de Produção):
    *   `run_batch_strings.py`: Execução em lote completa de cordas.
    *   `processar_todos.py`: Geração em lote dos JSONs de sincronização para brass e string.
    *   `processar_lento.py`: Geração em lote de JSONs para a pasta "meia-hora".
    *   `processar_jonas.py`: Processamento em lote para caminhos externos de Jonas.
*   **`organ/`** (Órgãos e Pads para Meia-Hora):
    *   `gerar_meia_hora.py`: Motor básico para desacelerar e renderizar hinos com FluidSynth.
    *   `comparar_orgaos.py`: Utilitário para gerar e comparar 7 variações de órgãos eletrônicos.
    *   `gerar_aprovados.py`: Gera os 3 timbres de órgãos aprovados pelo usuário.
    *   `gerar_blocos_preferidos.py`: Gera blocos de ~30min de execução de meia-hora contínua.
*   **`utils/`** (Ferramentas e Pós-Processadores):
    *   `postprocess_fade_apos_pausa.py`: Envelopamento acústico para eliminar estalos de arco.
    *   `sincronizar_letras.py`: Alinhamento inteligente de letras (MIDI + MP3 + TXT -> JSON).
    *   `visualizador_sincronizacao.py`: Servidor web local para edição e conferência de letras.

---

### 📥 2. Fontes de Entrada (Inputs)
*   **`mid/`**: MIDIs originais dos hinos em formato SATB (ex: `001-Cristo.mid`).
*   **`hinos_txt/`**: Letras estruturadas em TXT.
    *   `hinos_txt/letras_separadas/`: Arquivos individuais das letras.
    *   `hinos_txt/letras_separadas/_indice.csv`: Mapeamento de números de hinos para arquivos.

---

### 🧠 3. Modelos e Configurações (Models & Configs)
*   **`models/`**: Checkpoints locais do DDSP (ex: `violin/`, `trumpet/`, `flute/`).
*   **`config/`**: Arquivos de parametrização estática do MuseScore.
    *   `config/presets.json`: Configurações de metais.
    *   `config/score_style.mss`: Folha de estilo visual das partituras.

---

### 📤 4. Arquivos Gerados (Outputs)
*   **`output/`**: Todas as saídas de produção residem aqui.
    *   `output/string/`: Áudios finais de cordas.
    *   `output/brass/`: Áudios, partituras MSCZ e MIDIs de metais.
    *   `output/meia_hora/`: Áudios de órgãos de meia-hora.
    *   `output/lyrics/`: JSONs de letras alinhadas.

---

## 🚫 Regras Críticas Contra Bagunça

1.  **Auto-Limpeza do MuseScore**:
    Todos os scripts em `orchestrators/` implementam a remoção automática de arquivos e pastas residuais criados pelo MuseScore 4 CLI (`automation.json`, `META-INF`, `Thumbnails`, etc.). Mantenha essa prática em novos scripts.
2.  **Caminhos Absolutos em Scripts**:
    Como os scripts estão em subpastas, sempre use `ROOT = Path(__file__).parent.parent.absolute()` para derivar caminhos confiáveis para pastas irmãs, garantindo robustez independente de onde o terminal foi aberto.
