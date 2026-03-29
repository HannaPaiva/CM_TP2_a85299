# Fluxo do Codigo

Este ficheiro existe para te ajudar a explicar o projeto revisao ou manutencao. A ideia e responder a duas perguntas:

1. por onde o codigo comeca;
2. que parte do projeto faz o que.

## 1. Ponto de entrada

O programa comeca em `main.py`, no bloco final:

```python
if __name__ == "__main__":
    ft.run(main, assets_dir=str(Path(__file__).resolve().parent / "assets"))
```

Isto significa:

1. o Python executa `main.py`;
2. o Flet arranca a aplicacao;
3. o Flet chama a funcao `main(page)`;
4. tudo o resto acontece dentro dessa funcao.

## 2. O que acontece dentro de `main(page)`

Dentro de `main(page)`, o codigo faz varias preparacoes antes de mostrar qualquer ecran.

## 2.1 Estado inicial

Logo no inicio sao criados:

- `settings = Settings()`
- `storage = GameStorage()`
- varias variaveis de draft para configuracao visual;
- varios `ft.Text`, `ft.Switch`, `ft.Slider` e outros controlos persistentes.

Objetivo desta fase:

- preparar o estado em memoria;
- preparar os widgets reutilizados entre rotas;
- evitar recriar controlos importantes do zero a toda a hora.

## 2.2 Helpers utilitarios

Depois aparecem varios helpers pequenos, por exemplo:

- conversao de cor (`_hex_to_hsv`, `_hsv_to_hex`);
- calculo de largura/padding (`page_width`, `page_padding`, `is_narrow`);
- resolucao de tema/fundo (`effective_theme`, `effective_board_state`);
- validacao de cor e combinacao de presets.

Esta parte existe para centralizar pequenas regras reutilizadas em muitas views.

## 2.3 Componentes reutilizaveis de interface

A seguir, o `main.py` define varios construtores de UI:

- `compact_info`
- `action_chip`
- `small_banner`
- `game_metric_chip`
- `game_action_button`
- `surface_card`
- `option_tile`

Eles nao sao views completas. Sao blocos reutilizaveis que aparecem em varias rotas.

## 2.4 Picker de cor e uploads

Ainda dentro de `main(page)`, ha uma zona grande dedicada a:

- picker de cor;
- upload de imagens;
- criacao/edicao de temas personalizados.

Aqui entram funcoes como:

- `_ensure_picker_ready`
- `_open_color_picker`
- `pick_single_image`
- `save_theme_studio`
- `_choose_board_bg_for_theme`

Responsabilidade desta secao:

- abrir o file picker;
- ler imagens;
- validar cores;
- atualizar temas personalizados e respetivos assets.

## 3. Onde o motor do jogo entra

Depois da fase de helpers, o `main.py` cria o tabuleiro:

```python
board = GameBoard(page=page, settings=settings, on_win=on_win, on_change=refresh_hud)
board.setup()
```

Isto e o momento em que a logica principal do jogo entra de facto em cena.

### `board.setup()` faz:

1. criar slots;
2. criar as 52 cartas;
3. distribuir uma nova partida.

## 4. O que faz cada modulo do pacote `solitaire`

## `solitaire/gameboard.py`

E o coracao do jogo.

Responsabilidades:

- criar tableau, stock, waste e fundacoes;
- distribuir cartas;
- validar regras do Klondike;
- aplicar score;
- manter historico de undo;
- serializar/restaurar estado;
- adaptar layout ao tamanho da janela;
- detetar vitoria.

Funcoes/metodos importantes:

- `setup()`: prepara o tabuleiro.
- `start_new_game()`: cria uma partida nova.
- `restart_game()`: volta ao estado inicial da ronda atual.
- `finish_move()`: fecha um movimento valido e trata efeitos secundarios.
- `capture_state()`: gera snapshot completo.
- `restore_state()`: repoe snapshot salvo.
- `auto_win()`: leva o jogo diretamente ao estado final de vitoria.
- `apply_visual_preferences()`: recalcula tamanho e posicoes do tabuleiro.

## `solitaire/card.py`

Cada carta e um `ft.GestureDetector`.

Responsabilidades:

- saber em que slot esta;
- saber se esta virada para cima ou para baixo;
- responder a drag, click e double click;
- mudar imagem conforme o tema/verso selecionado.

Funcoes/metodos importantes:

- `can_be_moved()`
- `start_drag()`
- `drag()`
- `drop()`
- `click()`
- `doubleclick()`
- `place()`

## `solitaire/slot.py`

Representa uma pilha do jogo.

Responsabilidades:

- guardar a lista de cartas daquele slot;
- devolver topo e subconjuntos visiveis;
- calcular coordenadas relevantes para drop;
- tratar o clique no stock para reciclagem.

## `solitaire/settings.py`

Centraliza configuracao e catalogos.

Responsabilidades:

- versos predefinidos;
- temas predefinidos;
- dificuldades;
- objeto `Settings` que viaja nos snapshots.

## `solitaire/storage.py`

Camada de persistencia DuckDB.

Responsabilidades:

- abrir ligacao;
- garantir schema;
- guardar/ler estado do jogo;
- guardar/ler preferencias visuais.

## `solitaire/custom_theme_store.py`

Camada de persistencia e utilitarios dos temas personalizados.

Responsabilidades:

- gerar paletas;
- validar cores;
- gravar assets de versos e boards;
- guardar/ler `custom_themes.json`;
- renomear, editar e apagar temas.

## 5. Como a interface e organizada no `main.py`

Depois de criar o tabuleiro, o `main.py` passa a definir fluxo de aplicacao.

As responsabilidades principais ficam em blocos.

## 5.1 Sincronizacao entre board e UI

Funcoes importantes:

- `refresh_hud()`
- `sync_board_visuals()`
- `sync_draft_visuals_from_settings()`
- `sync_settings_from_board()`

Estas funcoes fazem a ponte entre o estado real do jogo e o que aparece na interface.

## 5.2 Persistencia

Funcoes importantes:

- `load_saved_snapshot()`
- `load_saved_visual_settings()`
- `autosave_current_state()`
- `autosave_current_state_sync()`
- `save_game()`
- `load_game()`

Fluxo:

1. o board gera snapshot;
2. o `main.py` envia o snapshot para local storage e DuckDB;
3. no carregamento, a app tenta restaurar primeiro o que encontrar;
4. depois reaplica tema e board.

## 5.3 Navegacao

A app usa rotas internas simples:

- `/intro`
- `/game`
- `/config`
- `/theme-studio`
- `/manage-themes`

As funcoes centrais aqui sao:

- `navigate(route)`
- `render_route(route)`

### `navigate(route)` faz:

- decidir efeitos secundarios de navegacao;
- disparar autosave ao sair do jogo;
- fechar overlay de vitoria quando necessario;
- chamar `render_route(route)`.

### `render_route(route)` faz:

- limpar `page.controls`;
- configurar `appbar` da rota;
- chamar o builder correto;
- aplicar o tema final;
- atualizar a pagina.

## 6. Builders de views

As views principais sao construidas por estas funcoes:

- `build_intro_view()`
- `build_theme_studio_view()`
- `build_manage_themes_view()`
- `build_config_view()`
- `build_game_view()`

### `build_intro_view()`

Mostra a pagina inicial:

- continuar partida;
- nova partida;
- acesso a visual;
- estado atual da app.

### `build_theme_studio_view()`

Mostra o ecran de criacao de tema:

- nome;
- cores;
- upload do verso;
- upload do fundo do board;
- preview e guardar.

### `build_manage_themes_view()`

Mostra os temas personalizados existentes e permite:

- editar cores;
- mudar fundo;
- renomear;
- apagar.

### `build_config_view()`

Mostra o configurador visual geral:

- presets;
- versos de cartas;
- paletas;
- fundo do board.

### `build_game_view()`

Mostra a rota do jogo propriamente dita:

- header com score e tempo;
- acoes do jogo;
- tabuleiro;
- overlay de vitoria.

## 7. Como a vitoria funciona

Existe uma cadeia de eventos clara.

### Vitoria normal

1. a carta e movida;
2. `GameBoard.finish_move()` e chamado;
3. `check_if_you_won()` verifica as fundacoes;
4. se o jogo acabou, `on_win()` e disparado;
5. em `main.py`, o callback real chama `play_victory_celebration()`.

### Vitoria por shake

1. o `ShakeDetector` fica registado em `page.services`;
2. com 4 shakes na rota `/game`, chama `board.auto_win()`;
3. `auto_win()` monta o snapshot final vencedor;
4. `on_win()` e chamado;
5. a mesma tela de celebracao aparece.

## 8. Como a celebracao e montada

O overlay de vitoria e criado no `main.py` com varios controlos persistentes:

- painel central;
- switchers de titulo/subtitulo;
- brilhos;
- flash;
- slots de fogos de artificio;
- botoes de nova partida e fechar.

Funcoes mais importantes:

- `sync_victory_layout()`
- `hide_victory_celebration()`
- `launch_firework()`
- `play_victory_celebration()`

## 9. Tarefas de fundo da pagina

No final de `main(page)` sao ligados alguns handlers globais:

- `page.on_resize = handle_resize`
- `page.on_close = handle_close`
- `page.run_task(run_timer)`
- `page.run_task(lock_portrait_mode)`
- `navigate("/intro")`
- `page.run_task(auto_load_on_start)`

### O que cada um faz

- `handle_resize`: recalcula tabuleiro e views.
- `handle_close`: faz autosave ao sair.
- `run_timer`: incrementa o cronometro.
- `lock_portrait_mode`: tenta fixar a app em vertical.
- `auto_load_on_start`: restaura visual e/ou partida guardada ao arrancar.

## 10. Resumo rapido para explicar oralmente

Se quiseres explicar o projeto de forma curta, podes seguir esta ordem:

1. `main.py` arranca a app e gere rotas/UI.
2. `GameBoard` e o motor do jogo.
3. `Card` e `Slot` modelam as pecas do tabuleiro.
4. `Settings` centraliza visual e dificuldade.
5. `storage.py` guarda jogo e visual em DuckDB.
6. `custom_theme_store.py` trata dos temas personalizados.
7. `render_route()` decide qual ecran aparece.
8. `build_game_view()` monta o jogo.
9. `finish_move()` e `auto_win()` podem terminar a partida.
10. `play_victory_celebration()` mostra a tela final animada.

## 11. Onde olhar primeiro quando quiseres mexer no projeto

Se a tua duvida for sobre...

- regras do jogo: `solitaire/gameboard.py`
- comportamento das cartas: `solitaire/card.py`
- temas e cores: `solitaire/settings.py` e `solitaire/custom_theme_store.py`
- persistencia: `solitaire/storage.py`
- interface e rotas: `main.py`
- ordem geral de execucao: este `fluxo.md`
