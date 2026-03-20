import json
from pathlib import Path


class GameStorage:
    def __init__(self, db_path=None):
        default_path = Path(__file__).resolve().parent.parent / "solitaire_state.duckdb"
        self.db_path = Path(db_path or default_path)

    def _connect(self):
        try:
            import duckdb
        except ImportError as exc:
            raise RuntimeError("duckdb nao esta instalado no ambiente atual.") from exc

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return duckdb.connect(str(self.db_path))

    def _ensure_schema(self, connection):
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS game_state (
                save_key VARCHAR PRIMARY KEY,
                payload JSON,
                saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def save_game(self, snapshot):
        connection = self._connect()
        try:
            self._ensure_schema(connection)
            connection.execute("DELETE FROM game_state WHERE save_key = ?", ["latest"])
            connection.execute(
                "INSERT INTO game_state (save_key, payload) VALUES (?, ?)",
                ["latest", json.dumps(snapshot)],
            )
        finally:
            connection.close()

    def load_game(self):
        connection = self._connect()
        try:
            self._ensure_schema(connection)
            row = connection.execute(
                "SELECT payload FROM game_state WHERE save_key = ?",
                ["latest"],
            ).fetchone()
            if row is None:
                return None
            return json.loads(row[0])
        finally:
            connection.close()
