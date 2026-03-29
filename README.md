# Solitaire

Projeto desenvolvido por **Hanna Paiva** no âmbito da unidade curricular de **Computação Móvel**, da **Universidade do Algarve**.

## Enquadramento

Este projeto corresponde à implementação de uma aplicação de **Paciência / Klondike Solitaire** em **Python** com **Flet**, com foco em jogabilidade, persistência de estado, personalização visual e adaptação a dispositivos móveis.

O objetivo principal da aplicação é permitir ao utilizador jogar uma versão completa de Paciência, movendo todas as cartas para as quatro fundações, respeitando as regras clássicas do jogo:

1. no tableau, as cartas devem ser organizadas por ordem decrescente e com alternância de cor;
2. nas fundações, as cartas devem ser colocadas por naipe, do Ás ao Rei;
3. o stock e a waste servem de apoio ao progresso da partida.

Para além da lógica base do jogo, a aplicação foi organizada para oferecer uma experiência mais completa, com persistência, configuração visual e uma apresentação final de vitória mais rica.

## Tecnologias utilizadas

- **Python 3.14+**
- **Flet**
- **DuckDB**
- **uv** para gestão do ambiente e das dependências

## Instalação e execução

## 1. Instalar dependências com `uv`

Na raiz do projeto, executar:

```powershell
uv sync
```

Este comando cria ou atualiza o ambiente virtual e instala todas as dependências definidas no projeto.

## 2. Executar a aplicação

Pode executar a aplicação de uma das seguintes formas:

```powershell
uv run python main.py
```

ou

```powershell
uv run flet run
```

## 3. Validação rápida

Se for necessário validar a sintaxe dos ficheiros principais:

```powershell
uv run python -m compileall main.py solitaire
```

## Conformidade com o enunciado

| Ponto pedido no enunciado | Implementação no projeto | Estado |
|---|---|---|
| Reiniciar o jogo | A aplicação permite reiniciar a ronda atual para a distribuição inicial da mesma partida, através da ação **Reiniciar**. A lógica está implementada no tabuleiro, preservando a seed e o estado inicial da ronda. | Concluído |
| Desfazer jogadas (`undo`) | Foi implementado um sistema de histórico com snapshots completos do tabuleiro, permitindo desfazer a última jogada com consistência. | Concluído |
| Salvar e carregar o estado do jogo | O estado da partida é persistido e restaurado corretamente. A aplicação guarda o progresso em **DuckDB** e em **local storage**, permitindo recuperar a última sessão guardada. O carregamento está disponível na interface e o guardado é assegurado pelo fluxo de persistência da aplicação. | Concluído |
| Escolher a imagem traseira das cartas, entre 4 opções diferentes | Estão disponíveis quatro versos predefinidos para as cartas: **Classic**, **Forest**, **Ocean** e **Sunrise**. | Concluído |
| Sistema de pontuação com cronómetro visível durante toda a partida | O jogo apresenta **pontuação** e **cronómetro** visíveis no ecrã de jogo, atualizados ao longo da partida e interrompidos quando a vitória é alcançada. | Concluído |
| Duas funcionalidades extra à escolha | Foram implementadas duas funcionalidades extra: **autowin por agitação do dispositivo** e **personalização avançada do tabuleiro e da interface através das settings e de temas personalizados**. | Concluído |
| README.md com justificação e descrição das funcionalidades extra | Este ficheiro apresenta a motivação, a descrição detalhada das funcionalidades extra e a verificação do cumprimento dos requisitos do enunciado. | Concluído |

## Conclusão da verificação

Não ficou nenhum requisito obrigatório por cumprir.

## Funcionalidades principais implementadas

## Núcleo do jogo

- Jogo de Paciência / Klondike funcional.
- Tableau, stock, waste e quatro fundações.
- Novo jogo com distribuição aleatória.
- Reinício da ronda atual.
- Undo com histórico de estados.
- Clique no stock para compra de cartas.
- Duplo clique para tentar mover automaticamente cartas para a fundação.

## Pontuação e tempo

- Sistema de pontuação por tipo de jogada.
- Cronómetro visível durante toda a partida.
- Pausa do cronómetro quando a vitória é atingida.

## Persistência

- Gravação do estado do jogo em **DuckDB**.
- Gravação redundante em **local storage**.
- Carregamento da última partida guardada.
- Persistência separada das preferências visuais.

## Personalização visual

- Quatro versos de cartas predefinidos.
- Temas visuais predefinidos para a mesa.
- Escolha independente entre verso, paleta e fundo do board.
- Suporte para criação de temas personalizados.
- Edição de cores dos temas personalizados.
- Upload de imagem para verso de cartas personalizado.
- Upload de imagem para fundo de board personalizado.
- Renomear e apagar temas personalizados.

## Interface e adaptação ao dispositivo

- Ecrã inicial com acesso a continuar jogo, nova partida e configuração visual.
- Rota própria para jogo.
- Rota própria para configuração visual.
- Rota própria para criação de temas.
- Rota própria para gestão de temas personalizados.
- Layout responsivo.
- Scroll desativado durante o jogo para não interferir com o arrastar das cartas.
- Aplicação bloqueada em orientação vertical no dispositivo móvel.

## Funcionalidades extra escolhidas

O enunciado pedia duas funcionalidades inovadoras à escolha. As duas funcionalidades extra selecionadas foram as seguintes.

## 1. Autowin por agitação do dispositivo, com fluxo de vitória

Foi implementado um sistema baseado em **ShakeDetector**, em que **quatro agitações do dispositivo** durante a rota de jogo ativam imediatamente o **autowin**. Quando isso acontece, o tabuleiro é levado diretamente para o estado final de vitória e a aplicação apresenta a celebração correspondente.

### Motivo da inclusão

Esta funcionalidade surgiu, numa primeira fase, como um mecanismo de apoio aos testes. Durante o desenvolvimento da sequência final de vitória e das respetivas animações, tornou-se pouco eficiente ter de concluir manualmente várias partidas completas apenas para validar o comportamento do ecrã final. Por essa razão, foi criado um atalho controlado que permitisse forçar rapidamente o estado vencedor.

No entanto, depois de implementada, a funcionalidade revelou utilidade real dentro da própria aplicação. Na prática, acabou por funcionar também como um mecanismo de **encerramento rápido da ronda**, quase como uma forma de **desistência assistida** que conduz imediatamente o baralho ao estado final. Por isso, foi mantida na versão final do projeto.

### O que foi implementado

- Deteção de agitação através de `ShakeDetector`.
- Ativação de autowin apenas durante a rota de jogo.
- Transição automática do tabuleiro para o estado vencedor.
- Integração com o fluxo normal de vitória.

## 2. Personalização avançada do tabuleiro através das settings

A segunda funcionalidade extra consistiu na criação de um sistema de **personalização visual aprofundada**, permitindo ao utilizador configurar vários elementos do tabuleiro e da interface através de settings e de temas personalizados.

### Motivo da inclusão

Durante a implementação da troca de fundos, versos e temas, tornou-se evidente que limitar a aplicação a um pequeno conjunto fixo de escolhas acabava por reduzir bastante o interesse da componente visual. Como havia alguma indecisão sobre que combinações deveriam ficar predefinidas, fez mais sentido evoluir a solução para algo mais flexível e mais interessante para o utilizador final.

Assim, em vez de impor apenas um visual fechado, optei por permitir que o utilizador pudesse **configurar o próprio board ao seu gosto**, escolhendo cores, imagens e combinações visuais de forma mais livre. Esta decisão valorizou a aplicação do ponto de vista da experiência de utilização e tornou a personalização uma parte realmente forte do projeto.

### O que foi implementado

- Escolha independente de verso de carta e tema da mesa.
- Alteração do fundo do board por cor ou imagem.
- Criação de temas personalizados.
- Edição das cores base, superfícies e destaque.
- Gestão de texto claro/escuro.
- Upload de assets personalizados.
- Gestão posterior dos temas criados.

## Ecrã e animação de vitória

Embora o autowin seja uma das funcionalidades extra escolhidas, o projeto passou também a incluir um **ecrã de celebração de vitória** com transições animadas, brilho, mudança de mensagens e efeitos visuais inspirados numa linguagem mais cinematográfica.

Este comportamento funciona:

- quando a vitória é alcançada normalmente;
- quando a vitória é ativada por agitação do dispositivo.

## Estrutura principal do projeto

```text
.
|-- main.py
|-- README.md
|-- fluxo.md
|-- pyproject.toml
|-- uv.lock
|-- assets/
`-- solitaire/
    |-- __init__.py
    |-- card.py
    |-- custom_theme_store.py
    |-- gameboard.py
    |-- settings.py
    |-- slot.py
    `-- storage.py
```

## Organização do código

- `main.py`: ponto de entrada, construção da interface, rotas, integração com persistência e ligação entre UI e motor do jogo.
- `solitaire/gameboard.py`: motor principal do tabuleiro, regras de jogada, score, snapshots, vitória e layout responsivo.
- `solitaire/card.py`: comportamento individual de cada carta.
- `solitaire/slot.py`: representação das pilhas do jogo.
- `solitaire/settings.py`: settings de dificuldade, temas, versos e estados visuais.
- `solitaire/storage.py`: persistência em DuckDB.
- `solitaire/custom_theme_store.py`: criação, leitura, edição e remoção de temas personalizados.
- `fluxo.md`: explicação do fluxo do código, útil para apresentação e manutenção.

## Observação final

Este projeto foi desenvolvido com a preocupação de cumprir integralmente o enunciado e, ao mesmo tempo, apresentar duas funcionalidades extra que fossem realmente relevantes para a aplicação. A opção passou por reforçar não só a componente técnica, mas também a experiência de utilização, a clareza do fluxo e a possibilidade de personalização.

No estado atual, a aplicação cumpre todos os requisitos pedidos e encontra-se organizada de forma a ser fácil de demonstrar, explicar e manter.
