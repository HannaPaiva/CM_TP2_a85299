# Solitaire Atelier

Aplicação desenvolvida em Python com Flet para o TP2 de Computação Móvel. O projeto implementa um Klondike Solitaire completo numa única app, com suporte para desktop, tablet e telemóvel, e inclui todos os tópicos pedidos no enunciado para a variante `Solitaire`.

## Funcionalidades obrigatórias implementadas

- Base do jogo Solitaire em Flet, com stock, waste, fundações e tableau.
- Reiniciar a partida atual e criar um novo jogo aleatório.
- Desfazer jogadas (`undo`).
- Guardar e carregar o estado localmente.
- Escolher a imagem traseira das cartas entre 4 opções.
- Sistema de pontuação com cronómetro sempre visível.
- Layout responsivo com redimensionamento automático do tabuleiro.

## Funcionalidade extra 1: Motor de dicas contextual

Escolhi implementar um motor de dicas porque é uma funcionalidade verdadeiramente útil num jogo de Solitaire e, ao mesmo tempo, permite demonstrar raciocínio por cima das regras do jogo, em vez de apenas acrescentar um elemento visual. O objetivo não foi mostrar uma ajuda genérica, mas sim criar um sistema que analisa o estado atual da mesa e escolhe uma jogada concreta com valor estratégico. Para isso, a aplicação avalia possíveis movimentos entre tableau, waste e fundações, atribuindo prioridades diferentes a cada cenário. Jogadas que revelam cartas escondidas recebem mais peso, assim como movimentos para a fundação ou a utilização de colunas vazias com Reis. Desta forma, a dica apresentada não é aleatória: ela tenta favorecer jogadas que aumentam a probabilidade de desbloquear a partida.

Na interface, a funcionalidade foi integrada de forma clara. Quando o utilizador carrega em `Dica`, a aplicação destaca a carta de origem e a área de destino, ao mesmo tempo que apresenta uma pequena explicação textual no painel lateral. Isto torna a ajuda mais pedagógica, porque o jogador percebe não só o que pode fazer, mas também porque essa jogada é relevante. Em termos de usabilidade, esta solução funciona bem tanto em ecrãs grandes como em mobile, já que o painel se adapta ao espaço disponível e o destaque visual mantém-se dentro do tabuleiro. Considerei esta funcionalidade relevante porque melhora a experiência de aprendizagem, reduz frustração em partidas difíceis e dá à aplicação um comportamento mais inteligente, indo além do mínimo exigido.

## Funcionalidade extra 2: Desafio diário com estatísticas persistentes

A segunda funcionalidade escolhida foi o `Desafio diário`, acompanhada por um painel de estatísticas persistentes. A ideia foi aproximar a aplicação de experiências modernas de jogos casuais, onde existe um objetivo renovado todos os dias e uma motivação adicional para regressar. Em vez de gerar apenas jogos aleatórios, a aplicação consegue iniciar uma partida diária com uma seed determinística baseada na data. Isso significa que, num mesmo dia, todos os dispositivos recebem exatamente a mesma distribuição de cartas. Esta abordagem introduz um elemento competitivo e de rotina que não existe num Solitaire básico, e torna a aplicação mais interessante do ponto de vista de produto.

Para complementar o desafio, foram adicionadas estatísticas guardadas localmente: vitórias totais, melhor pontuação, melhor tempo, número total de dicas pedidas e sequência diária concluída. Sempre que o utilizador vence, estes dados são atualizados automaticamente. No caso do desafio diário, a aplicação calcula também a sequência de dias concluídos, incentivando uma utilização continuada. Esta funcionalidade foi incluída porque acrescenta profundidade sem prejudicar a simplicidade do jogo principal. O jogador pode continuar a usar o modo livre normalmente, mas tem também um objetivo diário e métricas concretas de progresso. Em contexto de avaliação, esta escolha mostra iniciativa, persistência de dados e integração de mecânicas adicionais num fluxo único e coerente, tal como é pedido no enunciado.

## Estratégia de responsividade

Em vez de usar dimensões fixas, o tabuleiro recalcula automaticamente a largura das cartas, alturas, espaçamentos e offsets das colunas de acordo com o espaço disponível. Esta abordagem permite manter a mesma lógica de jogo em desktop, tablet e telemóvel, sem criar versões diferentes da interface. O painel de controlo também muda de comportamento: em ecrãs largos fica ao lado do tabuleiro; em ecrãs mais estreitos passa para baixo, preservando legibilidade e área útil para o jogo.

## Como executar

1. Criar o ambiente virtual com `uv venv`.
2. Instalar as dependências do projeto com `uv sync`.
3. Executar com `uv run main.py`.

Em sistemas Unix-like, o `main.py` já inclui shebang compatível com `uv`, pelo que também pode ser executado diretamente depois de marcar o ficheiro como executável.

Para deploy web, o projeto inclui um `fly.toml` base e assets próprios para favicon e loading screen.
