# Solitaire Atelier

Aplicacao desenvolvida em Python com Flet para o TP2 de Computacao Movel. O projeto parte de uma base de Klondike Solitaire e acrescenta as funcionalidades pedidas nos objetivos 2 e 3 do enunciado: controlo de partida, persistencia, pontuacao, personalizacao visual e niveis de dificuldade. A interface foi reorganizada para seguir a ideia do Solitaire & Casual Games do Windows, com um tabuleiro central, painel de informacao sempre visivel e um menu hamburger no canto superior esquerdo que concentra todas as opcoes principais.

## Funcionalidade 1: controlo de partida e recuperacao de jogadas

Uma das inclusoes mais importantes foi o conjunto de ferramentas de controlo da partida: novo jogo, reinicio da distribuicao atual e desfazer jogadas. Esta decisao foi motivada por duas necessidades muito claras. Em primeiro lugar, estas acoes fazem parte da expectativa normal de quem joga Solitaire em plataformas modernas, sobretudo quando o objetivo e aproximar a experiencia do que existe no ecossistema Windows. Em segundo lugar, permitem demonstrar que a aplicacao nao se limita a animar cartas no ecra, mas possui um modelo de estado consistente, capaz de reconstruir uma jogada anterior com rigor. O sistema de `undo` foi implementado com snapshots completos do tabuleiro antes de cada acao relevante, o que inclui movimentos entre tableau, waste e fundacoes, compra de cartas do stock e reciclagem da waste. Desta forma, o restauro nao depende de inferencias parciais e o comportamento mantem-se previsivel.

O reinicio da partida nao cria um novo baralho aleatorio; em vez disso, repoe a distribuicao inicial da partida corrente. Isto e relevante porque o utilizador pode experimentar estrategias diferentes sem perder o mesmo arranque de jogo. O menu hamburger reune estas opcoes num unico local, reduzindo ruido visual no tabuleiro e favorecendo a utilizacao em telemovel e tablet. A nivel de usabilidade, esta funcionalidade melhora bastante a experiencia porque reduz a frustracao causada por um erro de toque ou por uma jogada precipitada. Em termos de avaliacao, mostra tambem capacidade de gerir historico de estados, de restaurar a interface de forma coerente e de manter a logica do jogo sincronizada com a apresentacao visual.

## Funcionalidade 2: persistencia com DuckDB e local storage

A persistencia da partida foi pensada como uma funcionalidade central do objetivo 2, e nao como um simples extra acessorio. O enunciado pede explicitamente que o estado do jogo possa ser guardado e carregado a partir de DuckDB e local storage, por isso a implementacao foi desenhada para usar ambos os mecanismos em paralelo. Sempre que o utilizador escolhe guardar a partida, o tabuleiro atual e serializado para um snapshot completo com cartas no stock, waste, tableau e fundacoes, cartas viradas para cima ou para baixo, seed da partida, pontuacao, tempo decorrido, dificuldade, back selecionado e tema visual. Esse snapshot e escrito para uma base `DuckDB` local e tambem para o armazenamento persistente do cliente via `SharedPreferences` do Flet. No carregamento, a aplicacao tenta recuperar primeiro a versao em DuckDB e, caso nao exista, utiliza o estado em local storage.

O motivo para incluir os dois mecanismos foi garantir redundancia e demonstrar um fluxo de persistencia mais completo. O `DuckDB` cumpre a exigencia tecnologica do enunciado e oferece um armazenamento estruturado no disco, enquanto o local storage ajuda a manter uma copia leve e imediata das preferencias e do ultimo estado salvo. A vantagem pratica para o utilizador e evidente: uma partida pode ser interrompida e retomada sem perder progresso, mesmo depois de fechar a aplicacao. Esta funcionalidade tambem reforca a percecao de produto acabado, porque o jogo deixa de ser efemero e passa a acompanhar o utilizador entre sessoes. Para efeitos de demonstracao, o menu inclui botoes diretos de guardar e carregar, com mensagens de estado que explicam de onde foi recuperada a partida e se algum dos mecanismos ficou indisponivel.

## Funcionalidade 3: pontuacao e cronometro

O sistema de pontuacao com cronometro visivel durante toda a partida foi incluido para aproximar a app do comportamento esperado num Solitaire moderno e para dar mais contexto ao progresso do jogador. O cronometro corre continuamente enquanto a partida esta ativa e para de evoluir quando o jogador vence. A pontuacao muda de acordo com o tipo de movimento, privilegiando jogadas uteis como mover cartas para a fundacao, tirar cartas da waste para o tableau e revelar novas cartas no tableau. Isto cria um feedback constante e torna a partida mais legivel, porque cada acao deixa de ser apenas visual e passa a ter peso numerico. Alem disso, o cronometro e a pontuacao ajudam a comparar desempenhos entre partidas, sobretudo quando se experimentam dificuldades diferentes.

Para manter o fluxo da aplicacao mais claro, a pontuacao ficou concentrada num unico conjunto de regras inspirado no Solitaire do Windows. Assim, o jogador recebe pontos por jogadas uteis como mover cartas para a fundacao, tirar cartas da waste para o tableau e revelar novas cartas no tableau, sem ter de escolher variantes de scoring antes de entrar na partida. Esta decisao torna o comportamento da aplicacao mais previsivel, reduz complexidade desnecessaria na interface e deixa a logica central do tabuleiro mais facil de seguir e manter.

## Funcionalidade 4: personalizacao visual com backs e temas independentes

A personalizacao visual foi tratada como a segunda grande funcionalidade nova do objetivo 3. O enunciado pedia a possibilidade de escolher entre quatro imagens traseiras para as cartas e, para alem disso, o utilizador queria poder mudar o tema da janela de jogo como um todo, mantendo a liberdade de alterar apenas o back ou apenas o tema do tabuleiro. Para cumprir esse pedido, o menu hamburger passou a disponibilizar duas secoes independentes: uma para os backs e outra para os temas. Os quatro backs usam diretamente os assets fornecidos em `solitaire/assets/backs`, o que garante coerencia com o material do projeto. Em paralelo, foram criados quatro temas de tabuleiro que combinam com esses backs, mas sem ficarem rigidamente acoplados a eles.

Esta separacao tem uma justificacao clara em termos de experiencia de utilizacao. Se o back e o tema estivessem sempre ligados, a personalizacao seria artificial e limitada. Ao permitir a escolha independente, o utilizador pode criar combinacoes mais classicas, mais contrastadas ou mais ousadas, de acordo com a preferencia pessoal e com as condicoes do dispositivo onde esta a jogar. Para que a alteracao seja realmente percebida como “tema da janela”, a mudanca nao se limita ao tabuleiro: o fundo da pagina, o cabecalho, o painel lateral e os chips de informacao tambem adoptam a nova paleta. O resultado e uma aplicacao visualmente mais rica e mais proxima do que se espera de um jogo casual polido. Esta funcionalidade foi incluida porque melhora a identidade do projeto, responde diretamente ao pedido do cliente e evidencia trabalho de interface para alem da logica base do jogo.

## Como utilizar

1. Criar o ambiente virtual com `uv venv`.
2. Instalar as dependencias com `uv sync`.
3. Executar a app com `uv run main.py` ou `uv run flet run .\main.py`.
4. Abrir o menu hamburger no canto superior esquerdo para:
   - iniciar um novo jogo;
   - reiniciar a distribuicao atual;
   - desfazer a ultima jogada;
   - guardar e carregar o estado do jogo;
   - trocar a dificuldade;
   - escolher um back de cartas;
   - escolher um tema de tabuleiro independentemente do back.

## Nota sobre validacao

Nesta entrega, a logica e a interface foram adaptadas para comportamento responsivo, mas a validacao manual em varios dispositivos e sistemas operativos deve ser concluida durante a fase final de demonstracao do trabalho.
