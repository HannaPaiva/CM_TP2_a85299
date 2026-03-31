# `solitaire/card.py`

## Responsabilidade

Este ficheiro representa cada carta visivel e interativa do jogo.

## O que este ficheiro faz

- guarda rank, naipe, slot e estado da face
- muda imagem conforme o verso/tema
- responde a drag, drop, click e double click
- resolve que subpilha deve acompanhar a carta
- move cartas entre slots

## Como faz

### Interacao

`Card` herda de `ft.GestureDetector`.
Os handlers principais sao:

- `start_drag()`
- `drag()`
- `drop()`
- `click()`
- `doubleclick()`

### Drag otimizado

O fluxo novo de performance vive sobretudo aqui:

1. `start_drag()` guarda a subpilha arrastada
2. `drag()` acumula deltas
3. `_flush_drag_delta()` descarrega os deltas em lote
4. quando ha varias cartas, o update e pedido em grupo

### Drop

`drop()` valida o alvo e move as cartas com `update=False`, deixando o redraw
para o fim da jogada.

## Quem chama este ficheiro

- `GameBoard.create_card_deck()`
- testes de drag/performance

## Que ficheiros este ficheiro chama

- metodos de `GameBoard`
- catalogo `BACK_OPTIONS` em `solitaire.settings`
