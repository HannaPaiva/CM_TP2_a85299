"""
Reproducao de efeitos sonoros no cliente Flet (telemóvel / web).

Cada som e tocado criando um fta.Audio temporario no page.overlay.
ReleaseMode.RELEASE liberta o recurso automaticamente no fim da reproducao.
"""

from __future__ import annotations

import random
import shutil
from pathlib import Path

import flet as ft
import flet_audio as fta


SoundCategory = str  # "bad" | "good"


class ClientSoundPlayer:
    """
    Toca efeitos aleatorios a partir de assets/sounds/bad e assets/sounds/good.

    Cada chamada cria um Audio no overlay, toca, e liberta automaticamente.
    Varios sons podem sobrepor-se sem limite.
    """

    def __init__(self, page: ft.Page):
        self.page = page
        self.assets_sound_root = Path("assets/sounds")
        self.source_root = Path("sounds")
        self.effects_volume = 1.0
        self.sync_sound_assets()

    def set_volume(self, value: float) -> None:
        self.effects_volume = max(0.0, min(1.0, float(value)))

    def sync_sound_assets(self) -> None:
        for sound_path in self.source_root.rglob("*"):
            if not sound_path.is_file():
                continue
            relative_path = sound_path.relative_to(self.source_root)
            asset_target = self.assets_sound_root / relative_path
            asset_target.parent.mkdir(parents=True, exist_ok=True)
            if asset_target.exists():
                try:
                    if asset_target.read_bytes() == sound_path.read_bytes():
                        continue
                except Exception:
                    pass
            shutil.copy2(sound_path, asset_target)

    def list_sounds(self, category: SoundCategory) -> list[Path]:
        sound_dir = self.assets_sound_root / category
        if not sound_dir.exists():
            return []
        return sorted(
            p for p in sound_dir.iterdir()
            if p.is_file() and p.suffix.lower() in {".mp3", ".wav", ".ogg", ".m4a"}
        )

    def choose_sound(self, category: SoundCategory) -> Path | None:
        sounds = self.list_sounds(category)
        if not sounds:
            return None
        return random.choice(sounds)

    def _asset_src(self, sound_path: Path) -> str:
        relative = sound_path.relative_to(Path("assets")).as_posix()
        try:
            from urllib.parse import urlparse
            page_url = getattr(self.page, "url", None) or ""
            if page_url.startswith("http://") or page_url.startswith("https://"):
                p = urlparse(page_url)
                base = f"{p.scheme}://{p.netloc}"
                return f"{base}/{relative}"
        except Exception:
            pass
        return relative

    def _play(self, category: SoundCategory) -> None:
        sound_path = self.choose_sound(category)
        if sound_path is None:
            return

        src = self._asset_src(sound_path)

        audio: fta.Audio | None = None

        def on_state_change(e):
            if e.state in ("completed", "stopped"):
                try:
                    self.page.overlay.remove(audio)
                    self.page.update()
                except Exception:
                    pass

        audio = fta.Audio(
            src=src,
            autoplay=True,
            volume=self.effects_volume,
            balance=0.0,
            release_mode=fta.ReleaseMode.RELEASE,
            on_state_change=on_state_change,
        )

        self.page.overlay.append(audio)
        self.page.update()

    async def play_bad(self) -> None:
        self._play("bad")

    async def play_good(self) -> None:
        self._play("good")
