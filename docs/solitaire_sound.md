# `solitaire/sound.py`

## Responsabilidade

`sound.py` gere a reproducao de efeitos sonoros na aplicacao Flet para telemovel, web e Android. Os ficheiros de audio sao servidos diretamente do GitHub via URLs raw, evitando a necessidade de assets bundled no APK.

## O que este ficheiro faz

- Define categorias de sons: "bad" (erros, suspense) e "good" (sucesso, feedback positivo).
- Fornece uma classe `ClientSoundPlayer` para tocar efeitos aleatorios.
- Cada chamada cria um Audio no Flet, toca e liberta automaticamente.
- Permite sobreposicao de varios sons sem limite.

## Como faz

### Estrutura de dados

- `_SOUNDS`: dicionario com listas de URLs do GitHub para cada categoria.
- `SoundCategory`: tipo alias para "bad" | "good".

### Classe ClientSoundPlayer

- `__init__(self, page: ft.Page)`: inicializa com a pagina Flet.
- `play(category: SoundCategory)`: seleciona um som aleatorio da categoria e toca via `fta.Audio`.

### Integracao

- Os sons sao reproduzidos em resposta a eventos do jogo, como jogadas invalidas ("bad") ou vitorias ("good").
- Nao requer bundling de assets, reduzindo o tamanho do APK.

## Quem chama este ficheiro

- `main.py`: integra o `ClientSoundPlayer` na aplicacao.

## Que ficheiros este ficheiro chama

- Nenhum (depende apenas de Flet e flet_audio).

## Refatoracoes recentes

- Refatoracao do sound manager para melhorar a gestao de audio e reduzir dependencias.</content>
<parameter name="filePath">c:\Users\hanna\Desktop\FACULDADE\computacaoMovel\TP2_a85299\docs\solitaire_sound.md