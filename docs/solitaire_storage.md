# `solitaire/storage.py`

## Responsabilidade

Guardar e carregar estado persistente em DuckDB.

## O que este ficheiro faz

- abre ligacoes DuckDB
- garante o schema minimo
- grava snapshots de jogo
- grava preferencias visuais
- le os dois tipos de payload

## Como faz

`GameStorage` encapsula a infraestrutura de persistencia e oferece uma API
pequena:

- `save_game()`
- `load_game()`
- `save_visual_settings()`
- `load_visual_settings()`

Internamente usa `_save_payload()` e `_load_payload()` com uma unica tabela
`game_state`.

## Quem chama este ficheiro

- `main.py`

## Que ficheiros este ficheiro chama

- apenas a dependencia `duckdb`
