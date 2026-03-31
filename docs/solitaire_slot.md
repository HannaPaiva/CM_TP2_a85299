# `solitaire/slot.py`

## Responsabilidade

`Slot` modela uma pilha do tabuleiro.

## O que este ficheiro faz

- guarda a lista `pile`
- devolve a carta do topo
- devolve subconjuntos do topo
- calcula coordenadas relevantes para validar drop
- trata o clique do stock para reciclar a waste

## Como faz

Cada `Slot` e um `ft.Container` posicionado dentro do `GameBoard`.
O tipo do slot define o comportamento:

- `stock`
- `waste`
- `foundation`
- `tableau`

O metodo mais importante para drag/drop e `upper_card_top()`, usado para
comparar a posicao da carta arrastada com a pilha de destino.

## Quem chama este ficheiro

- `GameBoard.create_slots()`

## Que ficheiros este ficheiro chama

- metodos do `GameBoard` quando o stock precisa reciclar a waste
