"""
Testes do player de efeitos sonoros no cliente.

Estes cenarios protegem o fluxo novo de audio: um pool fixo de canais `Audio`
pre-registados na pagina, volume configuravel e possibilidade de sobrepor
efeitos usando slots diferentes.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from solitaire.settings import Settings
from solitaire.sound import ClientSoundPlayer


class FakePage:
    """
    Double minimo de `ft.Page` para testar servicos de audio.
    """

    def __init__(self):
        self.services = []
        self.update_calls = 0

    def update(self):
        self.update_calls += 1


class FakeAudio:
    """
    Double simples de `flet_audio.Audio`.

    Ele regista as propriedades recebidas e conta quantas vezes `play()` foi
    pedido para cada canal do pool.
    """

    def __init__(self, **kwargs):
        self.src = kwargs.get("src")
        self.autoplay = kwargs.get("autoplay", False)
        self.volume = kwargs.get("volume", 1.0)
        self.balance = kwargs.get("balance", 0.0)
        self.release_mode = kwargs.get("release_mode")
        self.on_loaded = kwargs.get("on_loaded")
        self.on_state_change = kwargs.get("on_state_change")
        self.on_position_change = kwargs.get("on_position_change")
        self.on_duration_change = kwargs.get("on_duration_change")
        self.on_seek_complete = kwargs.get("on_seek_complete")
        self.update_calls = 0
        self.play_calls = 0

    def update(self):
        self.update_calls += 1

    async def play(self, position=0):
        self.play_calls += 1


class ClientSoundPlayerTests(unittest.TestCase):
    """
    Garante que o player cliente continua apto para Android e overlap.
    """

    def make_project_root(self, temp_dir: str) -> Path:
        """
        Cria uma arvore minima de assets para os testes do player.
        """
        root = Path(temp_dir)
        (root / "assets" / "sounds" / "bad").mkdir(parents=True, exist_ok=True)
        (root / "assets" / "sounds" / "good").mkdir(parents=True, exist_ok=True)
        (root / "assets" / "sounds" / "bad" / "bad-a.mp3").write_bytes(b"bad-a")
        (root / "assets" / "sounds" / "bad" / "bad-b.mp3").write_bytes(b"bad-b")
        (root / "assets" / "sounds" / "good" / "good-a.mp3").write_bytes(b"good-a")
        return root

    @patch("solitaire.sound.fta.Audio", new=FakeAudio)
    def test_registers_audio_pool_on_page_startup(self):
        """
        O pool de canais deve ser registado logo na criacao do player.
        """
        with TemporaryDirectory() as temp_dir:
            player = ClientSoundPlayer(
                page=FakePage(),
                project_root=self.make_project_root(temp_dir),
                max_simultaneous_players=3,
            )

        self.assertEqual(len(player.page.services), 3)
        self.assertEqual(len(player._players), 3)
        self.assertTrue(all(service in player.page.services for service in player._players))

    @patch("solitaire.sound.fta.Audio", new=FakeAudio)
    def test_play_random_updates_reserved_channel_and_calls_play(self):
        """
        Tocar um efeito deve configurar `src`, aplicar o volume e chamar `play()`.
        """
        with TemporaryDirectory() as temp_dir:
            project_root = self.make_project_root(temp_dir)
            page = FakePage()
            player = ClientSoundPlayer(
                page=page,
                project_root=project_root,
                max_simultaneous_players=2,
            )
            player.set_volume(0.35)
            expected_sound = project_root / "assets" / "sounds" / "bad" / "bad-a.mp3"

            with patch("solitaire.sound.random.choice", return_value=expected_sound):
                result = asyncio.run(player.play_random("bad"))

        self.assertTrue(result)
        self.assertEqual(page.update_calls, 1)
        self.assertEqual(player._players[0].src, "sounds/bad/bad-a.mp3")
        self.assertEqual(player._players[0].volume, 0.35)
        self.assertEqual(player._players[0].play_calls, 1)
        self.assertEqual(player._players[0].update_calls, 1)

    @patch("solitaire.sound.fta.Audio", new=FakeAudio)
    def test_play_random_rotates_slots_to_allow_overlap(self):
        """
        Disparos consecutivos devem usar slots diferentes antes de reciclar o pool.
        """
        with TemporaryDirectory() as temp_dir:
            project_root = self.make_project_root(temp_dir)
            player = ClientSoundPlayer(
                page=FakePage(),
                project_root=project_root,
                max_simultaneous_players=2,
            )
            expected_sound = project_root / "assets" / "sounds" / "bad" / "bad-a.mp3"

            with patch("solitaire.sound.random.choice", return_value=expected_sound):
                asyncio.run(player.play_random("bad"))
                asyncio.run(player.play_random("bad"))

        self.assertEqual(player._players[0].play_calls, 1)
        self.assertEqual(player._players[1].play_calls, 1)
        self.assertEqual(player._next_player_index, 0)

    def test_settings_roundtrip_preserves_effects_volume(self):
        """
        O volume de efeitos deve continuar a sobreviver a serializacao.
        """
        settings = Settings()
        settings.effects_volume = 0.6

        restored = Settings.from_dict(settings.to_dict())

        self.assertEqual(restored.effects_volume, 0.6)


if __name__ == "__main__":
    unittest.main()
