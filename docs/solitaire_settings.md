# `solitaire/settings.py`

## Responsabilidade

Centralizar a configuracao serializavel da partida e os catalogos visuais.

## O que este ficheiro faz

- define versos predefinidos
- define temas predefinidos
- define presets de dificuldade
- expone o dataclass `Settings`
- recarrega temas personalizados no catalogo global

## Como faz

### Catalogos

`BACK_OPTIONS` e `THEME_OPTIONS` funcionam como fonte de verdade para a UI e
para o board.

### Configuracao serializavel

`Settings` guarda:

- dificuldade
- verso selecionado
- tema selecionado
- estrategia de fundo do board
- quantidade de cartas por compra
- numero de passagens do stock

### Integracao com temas personalizados

`refresh_custom_theme_registry()` limpa entradas custom antigas e volta a
carregar o bundle vindo de `custom_theme_store`.

## Quem chama este ficheiro

- `main.py`
- `GameBoard`
- testes de tema e de performance

## Que ficheiros este ficheiro chama

- `solitaire.custom_theme_store`
