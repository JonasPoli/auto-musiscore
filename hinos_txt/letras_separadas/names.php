<?php
array_shift($argv);
$arquivos = $argv;

if (empty($arquivos)) {
    echo "Nenhum arquivo foi informado.\n";
    exit;
}

$total_alterado = 0;

foreach ($arquivos as $arquivo) {
    if (!file_exists($arquivo)) {
        continue;
    }

    $conteudo = file_get_contents($arquivo);

    if (stripos($conteudo, "Coro") !== false) {
        $blocos = explode("\n\n", $conteudo);
        $contador = 1;

        foreach ($blocos as $indice => $bloco) {
            $bloco_limpo = trim($bloco);

            if ($indice === 0 || $bloco_limpo === "") {
                continue;
            }

            if (!preg_match('/^(\d+|Coro)/i', $bloco_limpo)) {
                $blocos[$indice] = $contador . ". " . $bloco;
                $contador++;
            }
        }

        $novo_conteudo = implode("\n\n", $blocos);
        file_put_contents($arquivo, $novo_conteudo);
        $total_alterado++;
    }
}

echo "Processo finalizado com sucesso.\n";
echo "Total de arquivos alterados: " . $total_alterado . "\n";