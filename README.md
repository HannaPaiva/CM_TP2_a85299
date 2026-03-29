# Solitaire

Aplicacao de Paciencia/Klondike desenvolvida em Python com Flet para o TP2 de Computacao Movel.


Autora: Hanna Paiva

## O que e este programa

O `Solitaire` e uma aplicacao interativa de Paciencia inspirada no Klondike classico. O objetivo do jogo e mover todas as 52 cartas para as quatro fundacoes, respeitando as regras tradicionais:

1. no tableau, as cartas descem de valor e alternam cor;
2. nas fundacoes, as cartas sobem do As ao Rei dentro do mesmo naipe;
3. o stock alimenta a waste, e a waste serve como apoio para novas jogadas.

Para alem da logica base, o programa foi pensado como um produto completo:

- tem ecras dedicados para intro, jogo, configuracao visual e gestao de temas;
- guarda e restaura progresso;
- permite mudar o visual da mesa;
- funciona com layout responsivo;
- inclui uma celebracao animada de vitoria.

## Tecnologias usadas

- Python 3.14+
- Flet
- DuckDB
- uv para gestao de ambiente e dependencias

## Features do projeto

## Jogabilidade

- Klondike/Paciencia com tableau, stock, waste e quatro fundacoes.
- Novo jogo com seed aleatoria.
- Reiniciar a mesma distribuicao inicial da ronda atual.
- Undo com historico de snapshots completos.
- Clique no stock para comprar cartas.
- Reciclagem da waste para o stock segundo a dificuldade.
- Duplo clique para tentar enviar cartas automaticamente para a fundacao.

## Dificuldade

- `easy`: compra 1 carta e passagens livres pelo stock.
- `classic`: compra 3 cartas e passagens livres pelo stock.
- `hard`: compra 3 cartas e limita as passagens pelo stock.

## Score e tempo

- Score atualizado por tipo de jogada.
- Cronometro sempre visivel durante a partida.
- Paragem automatica do cronometro quando o jogo entra em vitoria.

## Persistencia

- Guardado e carregamento do estado da partida.
- Persistencia redundante em:
  - local storage do Flet;
  - DuckDB (`solitaire_state.duckdb`).
- Persistencia separada das preferencias visuais.
- Autosave ao sair da rota de jogo.

## Personalizacao visual

- Versos de carta predefinidos.
- Temas predefinidos de mesa.
- Escolha independente entre verso, tema e fundo do board.
- Fundo do board por cor do tema, por cor de outro tema ou por imagem.
- Criacao de novos temas personalizados.
- Edicao de cores dos temas personalizados.
- Upload de verso da carta para novos temas.
- Upload de fundo do board para novos temas.
- Renomear e apagar temas personalizados.

## UX e interface

- Intro com continuar partida, nova partida e acesso ao visual.
- Rota propria para criar temas.
- Rota propria para gerir temas.
- Scroll bloqueado na rota de jogo para nao atrapalhar o arrastar das cartas.
- App bloqueada em orientacao vertical no telemovel.
- Layout responsivo para diferentes larguras.

## Vitoria e extras

- Tela de vitoria animada com painel, transicoes e fogos.
- A celebracao funciona tanto para vitoria normal como para autowin.
- `ShakeDetector`: 4 shakes no jogo ativam autowin.
- O autowin leva imediatamente as cartas para o estado final de vitoria.

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

## O que cada ficheiro principal faz

- `main.py`: ponto de entrada, rotas, construcao da UI, ligacao entre interface e motor do jogo.
- `solitaire/gameboard.py`: motor principal da partida, regras, score, undo, snapshots e layout responsivo do tabuleiro.
- `solitaire/card.py`: comportamento individual de cada carta, incluindo drag, click e double click.
- `solitaire/slot.py`: representacao das pilhas do jogo.
- `solitaire/settings.py`: catalogo de temas, versos, dificuldades e estrutura de configuracao serializavel.
- `solitaire/storage.py`: persistencia em DuckDB.
- `solitaire/custom_theme_store.py`: criacao, leitura e manutencao de temas personalizados e respetivos assets.

## Setup com uv

## 1. Instalar o uv

Se ainda nao tiveres o `uv`, instala-o primeiro.

No Windows PowerShell:

```powershell
pip install uv
```

## 2. Sincronizar o ambiente

Na raiz do projeto, corre:

```powershell
uv sync
```

Este comando:

- cria/atualiza o ambiente virtual;
- instala as dependencias declaradas no `pyproject.toml`;
- usa o `uv.lock` para manter a instalacao reprodutivel.

## 3. Executar a aplicacao

Opcao mais direta:

```powershell
uv run python main.py
```

Opcao equivalente usando o runner do Flet:

```powershell
uv run flet run .\main.py
```

## 4. Abrir no browser ou no dispositivo

Dependendo do fluxo do Flet, a app pode abrir localmente no browser ou mostrar QR code para abrir no telemovel.

## Fluxo de utilizacao

1. Abrir a app.
2. Entrar na intro.
3. Escolher `Continuar` ou `Nova partida`.
4. Jogar normalmente no tabuleiro.
5. Abrir `Visual` para mudar tema, verso e fundo do board.
6. Abrir `Criar tema` para gerar um tema personalizado.
7. Abrir `Gerir temas` para editar ou apagar temas personalizados.
8. Guardar/carregar partida quando necessario.
9. Ganhar normalmente ou ativar autowin com 4 shakes.

## Como correr para apresentacao

Sugestao de demonstracao:

1. Mostrar a intro.
2. Entrar numa partida guardada.
3. Mostrar `Undo`, `Reiniciar` e `Carregar`.
4. Abrir o configurador visual.
5. Criar ou editar um tema.
6. Voltar ao jogo e mostrar o novo visual aplicado.
7. Fazer 4 shakes para disparar autowin.
8. Mostrar a tela animada de vitoria.

## Persistencia e ficheiros gerados

- `solitaire_state.duckdb`: base de dados local com estado do jogo e preferencias visuais.
- `solitaire/custom_themes.json`: catalogo dos temas personalizados.
- `assets/backs/custom/`: versos carregados pela utilizadora.
- `assets/boards/`: fundos personalizados de board.

## Comandos uteis

Sincronizar dependencias:

```powershell
uv sync
```

Executar a app:

```powershell
uv run python main.py
```

Validar sintaxe:

```powershell
uv run python -m compileall main.py solitaire
```

## Estado atual do projeto

- modo de jogo removido para simplificar o fluxo;
- foco em um unico modelo de score e de partida;
- documentacao interna em portugues adicionada nos modulos ativos;
- README e `fluxo.md` alinhados com a implementacao atual.

## Nota final

O projeto foi organizado para ser mais facil de manter, explicar e evoluir. O motor do jogo esta concentrado no pacote `solitaire`, enquanto `main.py` ficou como camada de apresentacao e fluxo.
