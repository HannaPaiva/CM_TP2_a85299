# `tests/test_drag_performance_regressions.py`

## Responsabilidade

Evitar regressao nas otimizações de drag/drop e batching visual.

## O que valida

- arrastar uma subpilha nao dispara update por carta
- `place(update=False)` permite agrupar mudancas
- `draw_from_stock()` faz apenas um redraw do board

## Como valida

O teste usa doubles pequenos de `Slot` e `GameBoard` para isolar os cenarios
de performance e contar atualizacoes com precisao.

## Ficheiros cobertos

- `solitaire/card.py`
- `solitaire/gameboard.py`
