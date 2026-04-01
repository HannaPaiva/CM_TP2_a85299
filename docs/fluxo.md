# Fluxo do Projeto

## 1. Arranque

O ponto de entrada e `main.py`.

Fluxo:

1. o Python executa `main.py`;
2. `ft.run(main, assets_dir=...)` arranca o runtime do Flet;
3. o Flet chama `main(page)`;
4. `main(page)` cria estado, servicos, board e views.

## 2. Relacao entre ficheiros

Mapa de chamadas principais:

- `main.py` -> `solitaire.settings.Settings`
- `main.py` -> `solitaire.storage.GameStorage`
- `main.py` -> `solitaire.gameboard.GameBoard`
- `main.py` -> `solitaire.sound.ClientSoundPlayer`
- `main.py` -> helpers de `solitaire.custom_theme_store`
- `solitaire.gameboard.GameBoard` -> `solitaire.slot.Slot`
- `solitaire.gameboard.GameBoard` -> `solitaire.card.Card`
- `solitaire.card.Card` -> metodos de `GameBoard`
- `solitaire.slot.Slot` -> metodos de `GameBoard`
- `solitaire.settings` -> `solitaire.custom_theme_store.load_custom_theme_bundle`
- `tests/*` -> modulos de dominio para validar fluxo e regressao

## 3. Fluxo normal de jogo

### 3.1 Criacao do board

`main.py` chama:

```python
board = GameBoard(page=page, settings=settings, on_win=on_win, on_change=refresh_hud)
board.setup()
```

`GameBoard.setup()` chama:

1. `create_slots()`
2. `create_card_deck()`
3. `start_new_game()`

### 3.2 Jogada por drag/drop

Fluxo de chamadas:

1. `Card.start_drag()`
2. `Card.drag()`
3. `Card._flush_drag_delta()`
4. `GameBoard.update_controls()` quando ha varias cartas arrastadas
5. `Card.drop()`
6. `Card.place(..., update=False)` para cada carta
7. `GameBoard.finish_move(..., update_board=False)`
8. `GameBoard.update()` uma unica vez no fim

### 3.3 Jogada por clique

Fluxo de chamadas:

- clique no stock: `Card.click()` -> `GameBoard.draw_from_stock()`
- clique numa carta tapada no tableau: `Card.click()` -> `Card.turn_face_up()` -> `GameBoard.handle_tableau_reveal()`
- duplo clique: `Card.doubleclick()` -> validacao de fundacao -> `GameBoard.finish_move()`

### 3.4 Persistencia

Fluxo de save:

1. `main.py` pede `board.capture_state()`;
2. `main.py` grava em `SharedPreferences`;
3. `main.py` tenta gravar em `GameStorage`.

Fluxo de load:

1. `main.py` tenta `storage.load_game()` ou `storage.load_visual_settings()`;
2. se falhar, tenta `SharedPreferences`;
3. `GameBoard.restore_state()` recompõe o tabuleiro;
4. `sync_board_visuals()` reaplica visual e dimensoes.

## 4. Fluxo das otimizacoes de performance

### 4.1 Batching visual no drag

Responsaveis:

- `solitaire/card.py`
- `solitaire/gameboard.py`

Como funciona:

1. o drag acumula deltas em vez de atualizar a tela em todo evento;
2. os deltas sao descarregados em janelas pequenas;
3. se ha varias cartas, `GameBoard.update_controls()` tenta atualizar o grupo inteiro numa chamada;
4. so se isso falhar e que existe fallback para `board.update()`.

### 4.2 Fecho de jogada com um refresh final

Responsaveis:

- `Card.place(update=False)`
- `GameBoard.finish_move(update_board=False)`
- `GameBoard.display_waste(update=False)`

Como funciona:

1. a logica interna termina primeiro;
2. o redraw fica para o fim;
3. a jogada fecha com uma atualizacao consolidada.

### 4.3 Cronometro desacoplado do board

Responsavel:

- `main.py::run_timer()`

Como funciona:

1. o tempo real e calculado em background;
2. so o `timer_text` recebe update;
3. o tabuleiro nao e redesenhado a cada tick.

### 4.4 Resize protegido durante drag

Responsavel:

- `main.py::handle_resize()`

Como funciona:

1. o handler monta uma assinatura do layout atual;
2. se nao houver mudanca material, ele ignora o evento;
3. se houver drag ativo sem mudanca de largura real, evita rerender pesado.

## 5. Ordem pratica para estudar

1. `docs/main.md`
2. `docs/solitaire_gameboard.md`
3. `docs/solitaire_card.md`
4. `docs/solitaire_slot.md`
5. `docs/solitaire_settings.md`
6. `docs/solitaire_storage.md`
7. `docs/solitaire_custom_theme_store.md`
