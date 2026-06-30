# 🎼 Manual do Sistema de Conferência de Sincronismo de Letras

Este documento explica como utilizar a ferramenta interativa de visualização e edição de legendas para auditar, conferir e ajustar o sincronismo de áudio e letras dos hinos.

---

## 🚀 Como Iniciar o Servidor

Para rodar a interface de conferência localmente, execute o seguinte comando no diretório raiz do projeto:

```bash
python visualizador_sincronizacao.py
```

O script irá automaticamente encontrar uma porta disponível (geralmente a `8000`) e abrirá o seu navegador padrão na página:
👉 **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**

---

## 🎨 Visão Geral da Interface

A interface foi desenvolvida em formato SPA (Single Page Application) com um tema escuro e moderno, composta por três seções principais:

1.  **Barra Lateral (Explorador)**:
    *   **Seletor de Pasta**: Lista as pastas do projeto contendo arquivos `.json` e `.mp3` (ex: `output_meia_hora/orgao_eletronico_drawbar`).
    *   **Campo de Busca**: Permite filtrar hinos por número ou nome instantaneamente.
    *   **Lista de Hinos**: Mostra o título e um indicador de status (`Áudio OK` ou `Sem Áudio`).
2.  **Modo Karaoke (Visualizador Superior)**:
    *   Exibe a frase ativa no centro com fonte ampliada e brilho azul.
    *   Identifica explicitamente o estado de **`[ Introdução ]`** (texto em amarelo pulsante) e **`[ Pausa ]`** (texto em itálico fosco) quando o áudio estiver tocando sem cantar.
    *   Exibe a frase anterior e a próxima frase de forma transparente nas extremidades para dar contexto.
3.  **Tabela Editora (Painel Inferior)**:
    *   Lista todas as frases do hino em ordem temporal.
    *   Permite a visualização, digitação direta de tempos ou ajuste com botões interativos.

---

## ⚡ Recursos Principais de Auditoria e Edição

### ⏱️ Ajuste e Detecção da Introdução
Músicas lentas possuem introduções prolongadas. No cabeçalho ao lado do título, há o painel de **⏱️ Introdução**:
*   Você pode ajustar o fim da introdução usando os botões `-0.5s`, `-0.1s`, `+0.1s`, `+0.5s` ou digitando os segundos diretamente.
*   Pode ouvir a música e clicar em **Definir Atual [I]** para capturar o tempo corrente do player como o fim da introdução.

### 🎚️ Controle de Velocidade de Reprodução
Para conferir o tempo exato em que a voz ou instrumento inicia a frase:
*   Selecione uma velocidade reduzida no dropdown (ex: `0.8x - Lento` ou `0.7x - Muito Lento`). O áudio será reproduzido de forma mais lenta sem distorcer o tom da nota.

### ⌨️ Atalhos de Teclado (Para um Trabalho Ultra Rápido)
Você pode fazer toda a conferência e edição usando apenas o teclado:

| Tecla | Ação |
| :--- | :--- |
| **`Espaço`** | Toca / Pausa o áudio do hino. |
| **`←` / `→`** | Volta / Avança **5 segundos** no áudio para reescutar trechos. |
| **`↑` / `↓`** | Navega pelas linhas na tabela de legendas. |
| **`I`** | Define o tempo atual do áudio como o **Fim da Introdução**. |
| **`S`** | Define o tempo atual do áudio como o **Início** da frase selecionada. |
| **`D`** | Define o tempo atual do áudio como o **Fim** da frase selecionada. |
| **`Ctrl + S`** (ou `Cmd + S`) | Salva as alterações feitas no JSON. |

### 🛠️ Ajuste Fino e Navegação na Tabela
*   **▶️ Ouvir**: Cada linha possui um botão "Ouvir" que salta o áudio do player exatamente para o início (`inicio`) daquela frase e inicia o play.
*   **Ajuste Incremental**: Use os botões `-0.1s` / `+0.1s` (ajuste fino de 100ms) ou `-0.5s` / `+0.5s` para deslocamentos rápidos.

### 📦 Ajuste em Lote (Shift/Deslocamento)
Se você perceber que a legenda está perfeitamente sincronizada em ritmo, mas começou a adiantar ou atrasar de forma fixa (por exemplo, 0.5s de atraso em todas as frases subsequentes):
1.  Selecione a linha a partir da qual o problema começou.
2.  Insira o valor em segundos no campo **Ajuste em lote** (ex: `0.5` para somar 500ms, `-0.2` para adiantar 200ms).
3.  Clique em **Desta Linha em Diante** (aplica o deslocamento a partir da linha atual selecionada) ou **Todas as Linhas**.

---

## 💾 Salvamento Seguro e Backups

*   Ao clicar em **💾 Salvar JSON** (ou pressionar `Ctrl+S`), o painel envia as alterações para o servidor local.
*   O servidor lê o arquivo original, atualiza apenas as chaves `letra` e `intro_duration` (preservando todas as outras estruturas originais do JSON) e reescreve o arquivo.
*   **Backup automático**: Um arquivo `.json.bak` idêntico ao estado imediatamente anterior ao salvamento é criado ao lado do original na mesma pasta. Caso queira reverter alguma alteração acidental, basta renomear o arquivo `.bak` apagando a extensão adicional.
