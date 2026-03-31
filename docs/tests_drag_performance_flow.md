# `tests/test_drag_performance_flow.py`

## Responsabilidade

Garantir o fluxo feliz das otimizacoes de drag/drop no `GameBoard`.

## O que valida

- um arrasto de pilha faz batching de refresh visual
- um drop valido fecha a jogada com um unico redraw do board

## Como valida

O teste monta um `GameBoard` controlado com `Mock` para `page.update()` e
`board.update()`. Assim fica possivel contar exatamente quantas atualizacoes
acontecem.

## Ficheiros cobertos

- `solitaire/gameboard.py`
- `solitaire/card.py`
