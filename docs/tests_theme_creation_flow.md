# `tests/test_theme_creation_flow.py`

## Responsabilidade

Garantir que o fluxo de criacao e manutencao de temas personalizados continua
integro.

## O que valida

- `ft.Image` e `ft.DecorationImage` aceitam bytes
- criar tema grava assets e atualiza registry
- atualizar board background remove ficheiro antigo
- apagar tema limpa assets e JSON

## Como valida

O teste cria um projeto temporario em disco, redireciona os caminhos do
`custom_theme_store` e executa o fluxo completo sem tocar no projeto real.

## Ficheiros cobertos

- `solitaire/custom_theme_store.py`
- `solitaire/settings.py`
