"""
Camada de persistencia em DuckDB usada pela aplicacao.

Este modulo concentra toda a logica de leitura e escrita no ficheiro
`solitaire_state.duckdb`. A interface foi mantida pequena de proposito:
o resto da app so precisa de guardar e recuperar dois tipos de payload
JSON:

1. o estado completo da partida;
2. as preferencias visuais persistentes.

Ao isolar esta responsabilidade num unico ponto, o codigo de `main.py`
fica livre para tratar apenas o fluxo da interface, enquanto a estrutura
da base de dados e gerida aqui.
"""

import json
from pathlib import Path


class GameStorage:
    """
    Encapsula o acesso a DuckDB para guardar estado da app.

    A classe cria a base de dados no arranque sob demanda, garante que a
    tabela necessaria existe e oferece metodos de alto nivel para guardar
    a partida atual e as preferencias visuais.

    Attributes:
        db_path:
            Caminho absoluto do ficheiro DuckDB usado pela aplicacao.
    """

    def __init__(self, db_path=None):
        """
        Inicializa o storage apontando para o ficheiro DuckDB.

        Args:
            db_path:
                Caminho opcional para a base de dados. Quando omitido, a
                aplicacao usa `solitaire_state.duckdb` na raiz do projeto.
        """
        default_path = Path(__file__).resolve().parent.parent / "solitaire_state.duckdb"
        self.db_path = Path(db_path or default_path)

    def _connect(self):
        """
        Abre uma ligacao DuckDB pronta a usar.

        Returns:
            Ligacao DuckDB aberta.

        Raises:
            RuntimeError:
                Se a dependencia `duckdb` nao estiver instalada no ambiente.
        """
        try:
            import duckdb
        except ImportError as exc:
            raise RuntimeError("duckdb nao esta instalado no ambiente atual.") from exc

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return duckdb.connect(str(self.db_path))

    def _ensure_schema(self, connection):
        """
        Garante a existencia da tabela usada pela aplicacao.

        Args:
            connection:
                Ligacao DuckDB onde o schema sera verificado/criado.
        """
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS game_state (
                save_key VARCHAR PRIMARY KEY,
                payload JSON,
                saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def _save_payload(self, save_key, payload):
        """
        Guarda um payload JSON associado a uma chave logica.

        O registo anterior com a mesma chave e removido antes da nova
        insercao. Isto simplifica o modelo de dados porque a app so precisa
        do ultimo estado salvo para cada categoria.

        Args:
            save_key:
                Identificador logico do payload, por exemplo `latest`.
            payload:
                Dicionario serializavel em JSON.
        """
        connection = self._connect()
        try:
            self._ensure_schema(connection)
            connection.execute("DELETE FROM game_state WHERE save_key = ?", [save_key])
            connection.execute(
                "INSERT INTO game_state (save_key, payload) VALUES (?, ?)",
                [save_key, json.dumps(payload)],
            )
        finally:
            connection.close()

    def _load_payload(self, save_key):
        """
        Recupera um payload previamente guardado.

        Args:
            save_key:
                Chave logica do registo a procurar.

        Returns:
            O dicionario desserializado, ou `None` se nao existir registo.
        """
        connection = self._connect()
        try:
            self._ensure_schema(connection)
            row = connection.execute(
                "SELECT payload FROM game_state WHERE save_key = ?",
                [save_key],
            ).fetchone()
            if row is None:
                return None
            return json.loads(row[0])
        finally:
            connection.close()

    def save_game(self, snapshot):
        """
        Guarda o snapshot mais recente da partida.

        Args:
            snapshot:
                Estrutura JSON produzida por `GameBoard.capture_state()`.
        """
        self._save_payload("latest", snapshot)

    def load_game(self):
        """
        Carrega o ultimo snapshot de partida guardado.

        Returns:
            Dicionario com o estado da partida, ou `None` caso nao exista.
        """
        return self._load_payload("latest")

    def save_visual_settings(self, data):
        """
        Guarda as preferencias visuais persistentes da app.

        Args:
            data:
                Dicionario com verso, tema e configuracao de fundo.
        """
        self._save_payload("visual_settings", data)

    def load_visual_settings(self):
        """
        Carrega as preferencias visuais persistentes.

        Returns:
            Dicionario com as preferencias visuais, ou `None`.
        """
        return self._load_payload("visual_settings")
