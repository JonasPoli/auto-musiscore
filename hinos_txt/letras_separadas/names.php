<?php
array_shift($argv);
$arquivos = $argv;

if (empty($arquivos)) {
    echo "Nenhum arquivo foi informado.\n";
    exit;
}

foreach ($arquivos as $arquivo) {
    if (!file_exists($arquivo)) {
        continue;
    }

    $conteudo = file_get_contents($arquivo);

    // Normaliza as quebras de linha para evitar problemas de leitura
    $conteudo = str_replace("\r\n", "\n", $conteudo);

    $blocos = explode("\n\n", trim($conteudo));
    $contagem_linhas = array();

    foreach ($blocos as $bloco) {
        $bloco_limpo = trim($bloco);

        // Verifica se o parágrafo começa com um número
        if (preg_match('/^\d+/', $bloco_limpo)) {
            // Conta quantas linhas existem neste parágrafo
            $linhas = explode("\n", $bloco_limpo);
            $contagem_linhas[] = count($linhas);
        }
    }

    // Se houver parágrafos numerados, verifica se os tamanhos são diferentes
    if (count($contagem_linhas) > 1) {
        $valores_unicos = array_unique($contagem_linhas);

        if (count($valores_unicos) > 1) {
            echo $arquivo . "\n";
        }
    }
}
?>