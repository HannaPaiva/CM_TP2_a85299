"""
Testes do fluxo completo de temas personalizados.

Este modulo protege o caminho de criacao, atualizacao e remocao de temas para
garantir que assets, JSON e registry em memoria continuam coerentes.
"""

import base64
import copy
import json
import tempfile
import unittest
from pathlib import Path

import flet as ft

from solitaire import custom_theme_store as store
from solitaire import settings as settings_module


TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wn8n5sAAAAASUVORK5CYII="
)
ORIGINAL_BACK_OPTIONS = copy.deepcopy(settings_module.BACK_OPTIONS)
ORIGINAL_THEME_OPTIONS = copy.deepcopy(settings_module.THEME_OPTIONS)
BUILTIN_BACK_OPTIONS = {
    name: copy.deepcopy(data)
    for name, data in ORIGINAL_BACK_OPTIONS.items()
    if not data.get("custom")
}
BUILTIN_THEME_OPTIONS = {
    name: copy.deepcopy(data)
    for name, data in ORIGINAL_THEME_OPTIONS.items()
    if not data.get("custom")
}


class ThemeCreationFlowTests(unittest.TestCase):
    """
    Valida o ciclo de vida dos temas personalizados ponta a ponta.
    """

    def setUp(self):
        """
        Prepara um projeto temporario isolado para os testes de tema.
        """
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "assets" / "backs" / "custom").mkdir(parents=True, exist_ok=True)
        (self.root / "assets" / "boards").mkdir(parents=True, exist_ok=True)
        (self.root / "solitaire").mkdir(parents=True, exist_ok=True)

        self.original_paths = {
            "PROJECT_ROOT": store.PROJECT_ROOT,
            "CUSTOM_THEMES_FILE": store.CUSTOM_THEMES_FILE,
            "CUSTOM_BACKS_DIR": store.CUSTOM_BACKS_DIR,
            "CUSTOM_BOARDS_DIR": store.CUSTOM_BOARDS_DIR,
        }
        store.PROJECT_ROOT = self.root
        store.CUSTOM_THEMES_FILE = self.root / "solitaire" / "custom_themes.json"
        store.CUSTOM_BACKS_DIR = self.root / "assets" / "backs" / "custom"
        store.CUSTOM_BOARDS_DIR = self.root / "assets" / "boards"

        settings_module.BACK_OPTIONS.clear()
        settings_module.BACK_OPTIONS.update(copy.deepcopy(BUILTIN_BACK_OPTIONS))
        settings_module.THEME_OPTIONS.clear()
        settings_module.THEME_OPTIONS.update(copy.deepcopy(BUILTIN_THEME_OPTIONS))

    def tearDown(self):
        """
        Restaura o estado global dos modulos alterados pelo teste.
        """
        settings_module.BACK_OPTIONS.clear()
        settings_module.BACK_OPTIONS.update(copy.deepcopy(ORIGINAL_BACK_OPTIONS))
        settings_module.THEME_OPTIONS.clear()
        settings_module.THEME_OPTIONS.update(copy.deepcopy(ORIGINAL_THEME_OPTIONS))

        for name, value in self.original_paths.items():
            setattr(store, name, value)

        self.tempdir.cleanup()

    def test_flet_image_controls_accept_bytes_sources(self):
        """
        Confirma que o Flet aceita bytes diretamente em imagens usadas no fluxo.
        """
        image = ft.Image(src=TINY_PNG, width=32, height=32)
        decoration = ft.DecorationImage(src=TINY_PNG, fit=ft.BoxFit.COVER)

        self.assertEqual(image.src, TINY_PNG)
        self.assertEqual(decoration.src, TINY_PNG)

    def test_create_theme_refresh_registry_and_apply_settings(self):
        """
        Criar um tema deve persistir assets e torna-lo utilizavel no `Settings`.
        """
        created = store.save_custom_theme_bundle(
            label="Tema QA",
            base_color="#123456",
            surface_color="#234567",
            accent_color="#345678",
            use_light_text=True,
            image_bytes=TINY_PNG,
            original_filename="back.png",
            image_scale=1.2,
            board_bg_bytes=TINY_PNG,
            board_bg_filename="board.png",
        )

        settings_module.refresh_custom_theme_registry()

        self.assertIn(created["theme_name"], settings_module.THEME_OPTIONS)
        self.assertIn(created["back_name"], settings_module.BACK_OPTIONS)
        self.assertTrue((self.root / "assets" / created["back"]["asset"]).exists())
        self.assertTrue((self.root / "assets" / created["back"]["board_bg"]).exists())

        saved_payload = json.loads(store.CUSTOM_THEMES_FILE.read_text(encoding="utf-8"))
        self.assertEqual(
            saved_payload["themes"][created["theme_name"]]["label"],
            "Tema QA",
        )
        self.assertEqual(
            saved_payload["backs"][created["back_name"]]["asset"],
            created["back"]["asset"],
        )

        restored_settings = settings_module.Settings.from_dict(
            {
                "difficulty": "classic",
                "card_back_name": created["back_name"],
                "theme_name": created["theme_name"],
                "board_bg_style": "image",
                "board_bg_target": created["back_name"],
            }
        )
        self.assertEqual(restored_settings.card_back_name, created["back_name"])
        self.assertEqual(restored_settings.theme_name, created["theme_name"])
        self.assertEqual(restored_settings.card_back, created["back"]["asset"])
        self.assertEqual(restored_settings.theme["label"], "Tema QA")

    def test_update_and_delete_theme_assets_cleanup_files(self):
        """
        Atualizar e apagar temas deve limpar os ficheiros antigos corretamente.
        """
        created = store.save_custom_theme_bundle(
            label="Tema Cleanup",
            base_color="#654321",
            surface_color="#543210",
            accent_color="#C0FFEE",
            use_light_text=False,
            image_bytes=TINY_PNG,
            original_filename="cleanup.png",
            image_scale=1.0,
            board_bg_bytes=TINY_PNG,
            board_bg_filename="cleanup-board.png",
        )
        original_board_bg = created["back"]["board_bg"]
        original_board_bg_path = self.root / "assets" / original_board_bg

        updated_board_bg = store.update_custom_theme_board_bg(
            created["theme_name"],
            TINY_PNG,
            "cleanup-board.jpg",
        )
        updated_board_bg_path = self.root / "assets" / updated_board_bg

        self.assertFalse(original_board_bg_path.exists())
        self.assertTrue(updated_board_bg_path.exists())

        removed_board_bg = store.update_custom_theme_board_bg(
            created["theme_name"],
            None,
            None,
        )
        self.assertIsNone(removed_board_bg)
        self.assertFalse(updated_board_bg_path.exists())

        back_asset_path = self.root / "assets" / created["back"]["asset"]
        self.assertTrue(back_asset_path.exists())
        store.delete_custom_theme(created["theme_name"])
        self.assertFalse(back_asset_path.exists())

        saved_payload = json.loads(store.CUSTOM_THEMES_FILE.read_text(encoding="utf-8"))
        self.assertNotIn(created["theme_name"], saved_payload["themes"])
        self.assertNotIn(created["back_name"], saved_payload["backs"])


if __name__ == "__main__":
    unittest.main()
