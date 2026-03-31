# `main.py`

## Responsabilidade

`main.py` e a camada de aplicacao. Ele nao implementa as regras do Solitaire,
mas decide como a app arranca, que view aparece, como o board conversa com a
UI e quando o estado deve ser salvo.

## O que este ficheiro faz

- arranca o Flet
- cria `Settings` e `GameStorage`
- cria `GameBoard`
- define rotas e builders de views
- sincroniza score, tempo e mensagens
- gere autosave e load
- integra configuracao visual e temas personalizados
- monta a celebracao de vitoria

## Como faz

### Estado base

`main(page)` cria widgets persistentes e estados temporarios de configuracao.
Isto evita recriar a UI inteira a cada rota.

### Ponte com o board

`refresh_hud()` e o callback que recebe mudancas do `GameBoard`.
`sync_board_visuals()` reaplica tema, dimensoes e waste sem mexer nas regras do jogo.

### Persistencia

O ficheiro usa duas camadas:

- `SharedPreferences` para storage local leve
- `GameStorage` para DuckDB

O snapshot e sempre gerado pelo `GameBoard`.

### Navegacao

`navigate()` trata efeitos secundarios.
`render_route()` escolhe a view.

As views principais sao:

- intro
- jogo
- configuracao
- criacao de tema
- gestao de temas

### Performance relevante

As otimizacoes de UX que passam por aqui sao:

- `run_timer()` atualiza apenas o texto do tempo
- `handle_resize()` evita rerenders pesados desnecessarios
- `sync_board_visuals(update=False)` permite batching antes do redraw final

## Quem chama este ficheiro

- o runtime do Flet, via `ft.run(main, ...)`

## Que ficheiros este ficheiro chama

- `solitaire.gameboard`
- `solitaire.settings`
- `solitaire.storage`
- `solitaire.custom_theme_store`
