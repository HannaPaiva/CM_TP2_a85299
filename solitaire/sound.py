"""
Reproducao de efeitos sonoros no cliente Flet (telemovel / web / Android).

Os ficheiros de audio sao servidos diretamente do GitHub via raw URLs,
eliminando a necessidade de assets bundled no APK.
"""

from __future__ import annotations

import random

import flet as ft
import flet_audio as fta
from flet_audio.types import AudioState


SoundCategory = str  # "bad" | "good"

_BASE = "https://raw.githubusercontent.com/HannaPaiva/CM_TP2_a85299/main/assets/sounds"

_SOUNDS: dict[SoundCategory, list[str]] = {
    "bad": [
        f"{_BASE}/bad/error_CDOxCYm.mp3",
        f"{_BASE}/bad/gangnam-style-uaaaa-uaaao.mp3",
        f"{_BASE}/bad/kai-cenat-suspense.mp3",
        f"{_BASE}/bad/som-de-susto-youtuber.mp3",
        f"{_BASE}/bad/sudden-suspense_0jhLorD.mp3",
        f"{_BASE}/bad/the-alien-annihilation.mp3",
        f"{_BASE}/bad/thud_AHM3W06.mp3",
        f"{_BASE}/bad/trollface-smile.mp3",
        f"{_BASE}/bad/violin-suspense.mp3",
        f"{_BASE}/bad/yt1s_FU9XJKS.mp3",
    ],
    "good": [
        f"{_BASE}/good/bass-boost-drop.mp3",
        f"{_BASE}/good/sushi-dont-lie.mp3",
    ],
}


class ClientSoundPlayer:
    """
    Toca efeitos aleatorios a partir de URLs do GitHub.

    Cada chamada cria um Audio no services, toca, e liberta automaticamente.
    Varios sons podem sobrepor-se sem limite.
    """

    def __init__(self, page: ft.Page):
        self.page = page
        self.effects_volume = 1.0

    def set_volume(self, value: float) -> None:
        self.effects_volume = max(0.0, min(1.0, float(value)))

    def _play(self, category: SoundCategory) -> None:
        sounds = _SOUNDS.get(category, [])
        if not sounds:
            return

        src = random.choice(sounds)
        audio: fta.Audio | None = None

        def on_state_change(e):
            if e.state in (AudioState.COMPLETED, AudioState.STOPPED):
                try:
                    self.page.services.remove(audio)
                    self.page.update()
                except Exception:
                    pass

        def on_loaded(_):
            self.page.run_task(audio.play)

        audio = fta.Audio(
            src=src,
            autoplay=False,
            volume=self.effects_volume,
            balance=0.0,
            release_mode=fta.ReleaseMode.RELEASE,
            on_loaded=on_loaded,
            on_state_change=on_state_change,
        )

        self.page.services.append(audio)
        self.page.update()

    async def play_bad(self) -> None:
        self._play("bad")

    async def play_good(self) -> None:
        self._play("good")
