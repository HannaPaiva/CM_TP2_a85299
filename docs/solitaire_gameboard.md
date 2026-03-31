# `solitaire/gameboard.py`

## Responsabilidade

Este e o motor do jogo. O `GameBoard` conhece o estado completo da partida e
aplica as regras do Klondike.

## O que este ficheiro faz

- cria stock, waste, fundacoes e tableau
- cria as 52 cartas
- distribui a ronda inicial
- valida movimentos
- gere score e undo
- serializa e restaura snapshots
- recalcula layout responsivo
- consolida updates visuais durante drag/drop

## Como faz

### Estrutura base

`GameBoard` herda de `ft.Stack`, o que permite controlar manualmente `top` e
`left` de slots e cartas.

### Montagem do jogo

- `create_slots()` monta as pilhas
- `create_card_deck()` instancia as cartas
- `start_new_game()` embaralha, distribui e reseta progresso

### Regras

- `check_tableau_rules()` valida alternancia de cor e descida de rank
- `check_foundation_rules()` valida subida por naipe
- `finish_move()` fecha uma jogada, aplica score, reveal e vitoria

### Persistencia

- `capture_state()` produz o snapshot completo
- `restore_state()` recompõe o board a partir do snapshot
- `save_undo_state()` guarda um snapshot reduzido para desfazer

### Performance

As melhorias mais importantes ficaram aqui:

- `update_controls()` tenta atualizar um conjunto de cartas numa chamada
- varios metodos aceitam `update=False` para adiar redraw
- `display_waste()` e `finish_move()` podem preparar estado sem redesenhar imediatamente

## Quem chama este ficheiro

- `main.py`
- testes de performance

## Que ficheiros este ficheiro chama

- `solitaire.card`
- `solitaire.slot`
- `solitaire.settings`
