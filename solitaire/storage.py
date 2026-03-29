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

    def _save_payload(self, save_key, payload):
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
        self._save_payload("latest", snapshot)

    def load_game(self):
        return self._load_payload("latest")

    def save_visual_settings(self, data):
        self._save_payload("visual_settings", data)

    def load_visual_settings(self):
        return self._load_payload("visual_settings")
