# `solitaire/custom_theme_store.py`

## Responsabilidade

Gerir o ciclo de vida dos temas personalizados.

## O que este ficheiro faz

- valida cores e payloads
- deriva paletas completas
- guarda assets de versos e boards
- grava e le `custom_themes.json`
- renomeia, atualiza e remove temas

## Como faz

### Saneamento

Os helpers `_sanitize_back_entry()` e `_sanitize_theme_entry()` protegem a app
contra JSON editado manualmente ou assets em falta.

### Criacao

`save_custom_theme_bundle()`:

1. cria um nome interno seguro
2. grava o verso personalizado
3. opcionalmente grava o board background
4. gera a paleta derivada
5. persiste tudo no JSON

### Atualizacao e remocao

- `rename_custom_theme()`
- `update_custom_theme_palette()`
- `update_custom_theme_board_bg()`
- `delete_custom_theme()`

## Quem chama este ficheiro

- `main.py`
- `solitaire.settings`
- testes de tema

## Que ficheiros este ficheiro chama

- sistema de ficheiros do projeto
