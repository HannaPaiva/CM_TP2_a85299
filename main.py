"""
Aplicacao Flet principal do projeto de Paciencia.

Este ficheiro concentra a composicao da interface, o roteamento interno e a
orquestracao entre as camadas de dominio do jogo. Em termos práticos, ele e
responsavel por:

1. arrancar a app e preparar servicos Flet;
2. construir e alternar entre as views (`/intro`, `/game`, `/config`, etc.);
3. sincronizar preferencias visuais com o tabuleiro;
4. guardar/carregar estado local e em DuckDB;
5. ligar callbacks de jogo a elementos visuais, incluindo a tela de vitoria.

O motor do jogo em si continua encapsulado no pacote `solitaire`; aqui vive
sobretudo a camada de apresentacao e de fluxo.
"""

import asyncio
import colorsys
import json
import math
import random
from pathlib import Path

import flet as ft

from solitaire.custom_theme_store import (
    build_theme_palette,
    delete_custom_theme,
    load_custom_board_background_assets,
    rename_custom_theme,
    save_custom_theme_bundle,
    update_custom_theme_board_bg,
    update_custom_theme_palette,
)
from solitaire.gameboard import GameBoard
from solitaire.settings import (
    BACK_OPTIONS,
    Settings,
    THEME_OPTIONS,
    refresh_custom_theme_registry,
)
from solitaire.storage import GameStorage

LOCAL_GAME_STATE_KEY = "solitaire.game_state.v2"
VISUAL_SETTINGS_KEY = "solitaire.visual_settings.v1"

# Presets that pair a card back with its matching table theme
VISUAL_PRESETS = [
    {
        "label": "Classic Green",
        "back": "classic",
        "theme": "classic",
        "board_bg_style": "theme_color",
        "board_bg_target": "",
        "icon": ft.Icons.GRASS,
    },
    {
        "label": "Forest Moss",
        "back": "forest",
        "theme": "forest",
        "board_bg_style": "theme_color",
        "board_bg_target": "",
        "icon": ft.Icons.PARK,
    },
    {
        "label": "Ocean Blue",
        "back": "ocean",
        "theme": "ocean",
        "board_bg_style": "theme_color",
        "board_bg_target": "",
        "icon": ft.Icons.WAVES,
    },
    {
        "label": "Sunrise Copper",
        "back": "sunrise",
        "theme": "sunrise",
        "board_bg_style": "theme_color",
        "board_bg_target": "",
        "icon": ft.Icons.WB_SUNNY,
    },
]


def main(page: ft.Page):
    """
    Ponto de entrada da aplicacao Flet.

    O corpo desta funcao cria o estado compartilhado da sessao, declara
    helpers internos, monta as views e liga eventos da pagina a funcoes de
    alto nivel como navegacao, autosave e redimensionamento.

    Args:
        page:
            Objeto `ft.Page` entregue pelo runtime do Flet.
    """
    refresh_custom_theme_registry()
    settings = Settings()
    storage = GameStorage()
    config_return_route = "/intro"
    draft_card_back_name = settings.card_back_name
    draft_theme_name = settings.theme_name
    draft_board_bg_style = settings.board_bg_style
    draft_board_bg_target = settings.board_bg_target
    config_theme_tab = "combo"

    page.title = "Paciência"
    page.scroll = ft.ScrollMode.AUTO

    score_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
    timer_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
    status_text = ft.Text(size=14, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS, expand=True)
    intro_status = ft.Text(size=13)
    theme_studio_status = ft.Text(size=13)

    studio_image_bytes = None
    studio_image_name = None
    studio_board_bg_bytes = None
    studio_board_bg_name = None

    studio_name_field = ft.TextField(
        label="Nome do tema",
        value="Tema Personalizado",
        hint_text="Ex.: Horizonte Neon",
        capitalization=ft.TextCapitalization.WORDS,
    )
    studio_base_field = ft.TextField(
        label="Cor base da mesa",
        value=settings.theme["board_bg"],
        hint_text="#1E6B42",
    )
    studio_surface_field = ft.TextField(
        label="Cor dos paineis",
        value=settings.theme["panel_bg"],
        hint_text="#153221",
    )
    studio_accent_field = ft.TextField(
        label="Cor de destaque",
        value=settings.theme["accent"],
        hint_text="#F1CE6E",
    )
    studio_light_text_switch = ft.Switch(
        label="Texto claro",
        value=True,
    )
    studio_zoom_slider = ft.Slider(
        min=0.85,
        max=1.75,
        divisions=18,
        value=1.0,
        label="{value}x",
    )

    file_picker = ft.FilePicker()
    page.services.append(file_picker)
    file_picker_busy = False

    # Color picker state
    picker_target = None   # "base"|"surface"|"accent"|("edit", theme_name, color_key)
    picker_hue = 0.0       # 0–360
    picker_sat = 1.0       # 0–1
    picker_val = 0.6       # 0–1

    PICKER_W = 260
    PICKER_H = 180
    HUE_H = 28

    def _hex_to_hsv(hex_str):
        raw = str(hex_str or "").strip().lstrip("#")
        if len(raw) == 3:
            raw = "".join(c * 2 for c in raw)
        if len(raw) != 6:
            return 0.0, 0.8, 0.6
        try:
            r = int(raw[0:2], 16) / 255
            g = int(raw[2:4], 16) / 255
            b = int(raw[4:6], 16) / 255
            h, s, v = colorsys.rgb_to_hsv(r, g, b)
            return h * 360, s, v
        except Exception:
            return 0.0, 0.8, 0.6

    def _hsv_to_hex(h, s, v):
        r, g, b = colorsys.hsv_to_rgb(h / 360.0, s, v)
        return "#{:02X}{:02X}{:02X}".format(
            int(r * 255 + 0.5), int(g * 255 + 0.5), int(b * 255 + 0.5)
        )

    # --- layout helpers ---

    def page_width():
        return max(360, int(page.width or 390))

    def page_padding():
        width = page_width()
        if width < 420:
            return 10
        if width < 760:
            return 14
        return 20

    def is_narrow():
        return page_width() < 760

    def panel_width(max_width=880):
        return None if is_narrow() else min(max_width, page_width() - 40)

    def make_shadow():
        return ft.BoxShadow(
            spread_radius=0,
            blur_radius=26,
            color="#33000000",
            offset=ft.Offset(0, 10),
        )

    def effective_theme_name():
        route = page.route or "/intro"
        if route == "/config" and draft_theme_name in THEME_OPTIONS:
            return draft_theme_name
        if settings.theme_name in THEME_OPTIONS:
            return settings.theme_name
        return "classic"

    def effective_theme():
        return THEME_OPTIONS[effective_theme_name()]

    def normalize_board_bg_state(style, target):
        style = str(style or "theme_color")
        target = str(target or "")
        if style == "image":
            if target in BACK_OPTIONS and BACK_OPTIONS[target].get("board_bg"):
                return style, target
            asset_target = target.replace("\\", "/").lstrip("/")
            if asset_target:
                asset_path = Path(__file__).resolve().parent / "assets" / asset_target
                if asset_path.exists():
                    return style, asset_target
            return "theme_color", ""
        if style == "preset_color":
            if target in THEME_OPTIONS:
                return style, target
            return "theme_color", ""
        return "theme_color", ""

    def effective_board_state(use_draft=None):
        if use_draft is None:
            use_draft = (page.route or "/intro") == "/config"
        theme_name = draft_theme_name if use_draft else settings.theme_name
        board_style = draft_board_bg_style if use_draft else settings.board_bg_style
        board_target = draft_board_bg_target if use_draft else settings.board_bg_target
        board_style, board_target = normalize_board_bg_state(board_style, board_target)

        theme_name = theme_name if theme_name in THEME_OPTIONS else "classic"
        theme_data = THEME_OPTIONS[theme_name]

        if board_style == "image":
            back_data = BACK_OPTIONS.get(board_target, {})
            image_path = back_data.get("board_bg")
            if image_path:
                return {
                    "style": board_style,
                    "target": board_target,
                    "color": theme_data["board_bg"],
                    "image": image_path,
                    "label": back_data.get("label", board_target),
                    "description": "Imagem de fundo do board",
                }
            asset_target = board_target.replace("\\", "/").lstrip("/")
            asset_path = Path(__file__).resolve().parent / "assets" / asset_target
            if asset_target and asset_path.exists():
                label = "Board personalizado"
                for option in load_custom_board_background_assets():
                    if option["id"] == asset_target:
                        label = option["label"]
                        break
                return {
                    "style": board_style,
                    "target": asset_target,
                    "color": theme_data["board_bg"],
                    "image": asset_target,
                    "label": label,
                    "description": "Imagem independente do board",
                }

        if board_style == "preset_color":
            preset_theme = THEME_OPTIONS.get(board_target)
            if preset_theme is not None:
                return {
                    "style": board_style,
                    "target": board_target,
                    "color": preset_theme["board_bg"],
                    "image": None,
                    "label": preset_theme["label"],
                    "description": "Cor fixa do board",
                }

        return {
            "style": "theme_color",
            "target": "",
            "color": theme_data["board_bg"],
            "image": None,
            "label": theme_data["label"],
            "description": "Cor do tema atual",
        }

    def is_hex_color(value):
        value = str(value or "").strip().lstrip("#")
        return len(value) in (3, 6) and all(ch in "0123456789abcdefABCDEF" for ch in value)

    def is_light_color(value):
        raw = str(value or "").strip().lstrip("#")
        if len(raw) == 3:
            raw = "".join(ch * 2 for ch in raw)
        if len(raw) != 6 or not all(ch in "0123456789abcdefABCDEF" for ch in raw):
            return True
        red = int(raw[0:2], 16)
        green = int(raw[2:4], 16)
        blue = int(raw[4:6], 16)
        return (0.2126 * red) + (0.7152 * green) + (0.0722 * blue) >= 150

    def theme_studio_palette():
        return build_theme_palette(
            label=studio_name_field.value or "Tema Personalizado",
            base_color=studio_base_field.value,
            surface_color=studio_surface_field.value,
            accent_color=studio_accent_field.value,
            use_light_text=bool(studio_light_text_switch.value),
        )

    def available_visual_presets():
        presets = list(VISUAL_PRESETS)
        for back_name, back_data in BACK_OPTIONS.items():
            if not back_data.get("custom"):
                continue
            theme_name = back_data.get("suggested_theme")
            if theme_name not in THEME_OPTIONS:
                continue
            presets.append(
                {
                    "label": THEME_OPTIONS[theme_name]["label"],
                    "back": back_name,
                    "theme": theme_name,
                    "board_bg_style": "image" if back_data.get("board_bg") else "theme_color",
                    "board_bg_target": back_name if back_data.get("board_bg") else "",
                    "icon": ft.Icons.AUTO_FIX_HIGH,
                }
            )
        return presets

    def available_board_color_themes():
        return [
            name
            for name, data in THEME_OPTIONS.items()
            if not data.get("custom")
        ]

    def available_board_image_backs():
        options = [
            {
                "id": name,
                "label": data.get("label", name),
                "asset": data.get("board_bg"),
                "source": "back",
            }
            for name, data in BACK_OPTIONS.items()
            if data.get("board_bg")
        ]
        options.extend(
            [
                {
                    "id": data["id"],
                    "label": data["label"],
                    "asset": data["asset"],
                    "source": "asset",
                }
                for data in load_custom_board_background_assets()
            ]
        )
        return options

    def build_visual_settings_payload():
        """
        Consolida as preferencias visuais ativas num payload persistivel.

        Returns:
            Dicionario completo com verso, tema e configuracao do fundo do
            tabuleiro, incluindo metadados uteis para futuras restauracoes.
        """
        board_state = effective_board_state(use_draft=False)
        back_data = BACK_OPTIONS.get(settings.card_back_name, {})
        return {
            "version": 2,
            "card_back_name": settings.card_back_name,
            "theme_name": settings.theme_name,
            "board_bg_style": settings.board_bg_style,
            "board_bg_target": settings.board_bg_target,
            "card_back": {
                "label": back_data.get("label", settings.card_back_name),
                "asset": back_data.get("asset"),
                "fit": back_data.get("fit", "cover"),
                "scale": back_data.get("scale", 1.0),
            },
            "theme_palette": dict(settings.theme),
            "board_background": {
                "style": board_state["style"],
                "target": board_state["target"],
                "label": board_state["label"],
                "color": board_state["color"],
                "image": board_state["image"],
                "description": board_state["description"],
            },
        }

    def restore_visual_settings_payload(data):
        """
        Restaura preferencias visuais persistidas para o estado em memoria.

        Args:
            data:
                Dicionario previamente guardado em storage local ou DuckDB.
        """
        nonlocal draft_card_back_name, draft_theme_name, draft_board_bg_style, draft_board_bg_target
        back_name = str(data.get("card_back_name", "classic"))
        theme_name = str(data.get("theme_name", "classic"))
        board_bg_block = data.get("board_background", {}) if isinstance(data.get("board_background"), dict) else {}
        board_style = data.get("board_bg_style", board_bg_block.get("style", "theme_color"))
        board_target = data.get("board_bg_target", board_bg_block.get("target", ""))
        board_style, board_target = normalize_board_bg_state(board_style, board_target)

        if back_name in BACK_OPTIONS:
            settings.card_back_name = back_name
            draft_card_back_name = back_name
        else:
            settings.card_back_name = "classic"
            draft_card_back_name = "classic"

        if theme_name in THEME_OPTIONS:
            settings.theme_name = theme_name
            draft_theme_name = theme_name
        else:
            settings.theme_name = "classic"
            draft_theme_name = "classic"

        settings.board_bg_style = board_style
        settings.board_bg_target = board_target
        draft_board_bg_style = board_style
        draft_board_bg_target = board_target

    def should_show_intro_status():
        """
        Decide se a intro precisa de mostrar um banner de estado.

        Returns:
            `True` quando a mensagem atual nao e apenas um texto neutro.
        """
        return intro_status.value not in {"", "Pronto para jogar.", "Partida anterior carregada."}

    async def pick_single_image(dialog_title, on_error=None):
        nonlocal file_picker_busy
        if file_picker_busy:
            return None

        file_picker_busy = True
        try:
            files = await file_picker.pick_files(
                dialog_title=dialog_title,
                file_type=ft.FilePickerFileType.IMAGE,
                allow_multiple=False,
                with_data=True,
            )
        except RuntimeError as exc:
            if on_error is not None:
                error_text = str(exc).lower()
                if "timeout" in error_text:
                    on_error("O seletor de ficheiros expirou. Tenta novamente.")
                else:
                    on_error("Nao foi possivel abrir o seletor de ficheiros.")
            return None
        finally:
            file_picker_busy = False

        if not files:
            return None

        selected_file = files[0]
        selected_bytes = selected_file.bytes
        if selected_bytes is None and selected_file.path:
            selected_bytes = Path(selected_file.path).read_bytes()
        if not selected_bytes:
            if on_error is not None:
                on_error("Nao foi possivel ler a imagem escolhida.")
            return None

        return {
            "name": selected_file.name,
            "bytes": selected_bytes,
        }

    # --- widget helpers ---

    def compact_info(label, value, icon, on_click=None, hint=None):
        theme = effective_theme()
        return ft.Container(
            on_click=on_click,
            padding=14,
            border_radius=ft.BorderRadius.all(20),
            bgcolor=theme["panel_bg_alt"] if on_click else "#22FFFFFF",
            border=(
                ft.Border.all(1.2, theme["slot_border"])
                if on_click
                else None
            ),
            content=ft.Row(
                controls=[
                    ft.Icon(icon, size=18, color=theme["text"]),
                    ft.Column(
                        controls=[
                            ft.Text(label, size=11, color=theme["muted"]),
                            ft.Text(
                                value,
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color=theme["text"],
                            ),
                            *(
                                [ft.Text(hint, size=11, color=theme["muted"])]
                                if hint
                                else []
                            ),
                        ],
                        spacing=2,
                        tight=True,
                    ),
                    *(
                        [ft.Icon(ft.Icons.CHEVRON_RIGHT, size=18, color=theme["accent"])]
                        if on_click
                        else []
                    ),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def action_chip(label, icon, on_click, tone="soft", large=False):
        theme = effective_theme()
        filled = tone == "filled"
        horizontal_padding = 24 if large else 16
        vertical_padding = 16 if large else 12
        icon_size = 20 if large else 18
        text_size = 16 if large else 14
        chip_width = 280 if large and not is_narrow() else None
        return ft.Container(
            on_click=on_click,
            width=chip_width,
            padding=ft.Padding.symmetric(horizontal=horizontal_padding, vertical=vertical_padding),
            border_radius=ft.BorderRadius.all(999),
            bgcolor=theme["accent"] if filled else theme["panel_bg_alt"],
            border=ft.Border.all(
                1.2,
                theme["accent"] if filled else theme["slot_border"],
            ),
            content=ft.Row(
                controls=[
                    ft.Icon(
                        icon,
                        size=icon_size,
                        color=theme["page_bg"] if filled else theme["accent"],
                    ),
                    ft.Text(
                        label,
                        size=text_size,
                        weight=ft.FontWeight.W_600,
                        color=theme["page_bg"] if filled else theme["text"],
                    ),
                ],
                spacing=8,
                tight=True,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def small_banner(text_control, icon):
        theme = effective_theme()
        return ft.Container(
            width=panel_width(960),
            padding=16,
            border_radius=ft.BorderRadius.all(22),
            bgcolor=theme["panel_bg"],
            border=ft.Border.all(1.2, theme["slot_border"]),
            content=ft.Row(
                controls=[
                    ft.Icon(icon, size=18, color=theme["accent"]),
                    text_control,
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def game_metric_chip(text_control, icon):
        theme = effective_theme()
        return ft.Row(
            controls=[
                ft.Icon(icon, size=16, color=theme["accent"]),
                text_control,
            ],
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
        )

    def game_action_button(icon, tooltip, on_click):
        theme = effective_theme()
        return ft.Container(
            width=44 if is_narrow() else 48,
            height=44 if is_narrow() else 48,
            border_radius=ft.BorderRadius.all(14),
            bgcolor=theme["panel_bg_alt"],
            border=ft.Border.all(1, theme["slot_border"]),
            content=ft.IconButton(
                icon=icon,
                tooltip=tooltip,
                on_click=on_click,
                icon_color=theme["text"],
                icon_size=19 if is_narrow() else 20,
            ),
        )

    def empty_game_action_slot():
        return ft.Container(
            width=44 if is_narrow() else 48,
            height=44 if is_narrow() else 48,
        )

    def surface_card(title, subtitle, content, icon):
        theme = effective_theme()
        header = ft.Row(
            controls=[
                ft.Container(
                    width=42,
                    height=42,
                    border_radius=ft.BorderRadius.all(14),
                    bgcolor=theme["chip_bg"],
                    alignment=ft.Alignment(0, 0),
                    content=ft.Icon(icon, color=theme["accent"], size=22),
                ),
                ft.Column(
                    controls=[
                        ft.Text(
                            title,
                            size=20,
                            weight=ft.FontWeight.BOLD,
                            color=theme["text"],
                        ),
                        ft.Text(subtitle, size=13, color=theme["muted"]),
                    ],
                    spacing=2,
                    tight=True,
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        return ft.Container(
            width=panel_width(),
            padding=20 if is_narrow() else 24,
            border_radius=ft.BorderRadius.all(28),
            bgcolor=theme["panel_bg"],
            border=ft.Border.all(1.5, theme["slot_border"]),
            shadow=make_shadow(),
            content=ft.Column(controls=[header, content], spacing=18, tight=True),
        )

    def option_tile(title, subtitle, selected, icon, on_click, data=None, media=None):
        theme = effective_theme()
        title_color = theme["page_bg"] if selected else theme["text"]
        subtitle_color = theme["page_bg"] if selected else theme["muted"]
        icon_color = theme["page_bg"] if selected else theme["accent"]
        controls = []
        if media is not None:
            controls.append(media)
        controls.append(
            ft.Row(
                controls=[
                    ft.Container(
                        width=38,
                        height=38,
                        border_radius=ft.BorderRadius.all(12),
                        bgcolor="#22FFFFFF" if selected else theme["chip_bg"],
                        alignment=ft.Alignment(0, 0),
                        content=ft.Icon(icon, size=20, color=icon_color),
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(
                                title,
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=title_color,
                            ),
                            ft.Text(subtitle, size=12, color=subtitle_color),
                        ],
                        spacing=2,
                        tight=True,
                        expand=True,
                    ),
                    ft.Icon(
                        ft.Icons.CHECK_CIRCLE if selected else ft.Icons.RADIO_BUTTON_UNCHECKED,
                        size=20,
                        color=icon_color,
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )
        return ft.Container(
            data=data,
            on_click=on_click,
            padding=16,
            width=None if is_narrow() else 260,
            border_radius=ft.BorderRadius.all(24),
            bgcolor=theme["accent"] if selected else theme["panel_bg_alt"],
            border=ft.Border.all(1.5, theme["accent"] if selected else theme["slot_border"]),
            content=ft.Column(controls=controls, spacing=14, tight=True),
        )

    # ── Color picker (Flet 0.82 compatible) ──────────────────────────────────

    # Persistent controls — created lazily on first use
    _pc: dict = {}  # sv_bg, cursor, hue_thumb, result_swatch, hex_text
    _picker_dialog_ref: list = [None]  # [dialog] or [None]

    def _update_picker_visuals():
        if not _pc:
            return
        h, s, v = picker_hue, picker_sat, picker_val
        hue_hex = _hsv_to_hex(h, 1.0, 1.0)
        result_hex = _hsv_to_hex(h, s, v)

        _pc["sv_bg"].bgcolor = hue_hex
        _pc["cursor"].left = max(0, s * PICKER_W - 10)
        _pc["cursor"].top = max(0, (1 - v) * PICKER_H - 10)
        _pc["hue_thumb"].left = max(0, (h / 360.0) * PICKER_W - 11)
        _pc["result_swatch"].bgcolor = result_hex
        _pc["hex_text"].value = result_hex
        try:
            page.update()
        except Exception:
            pass

    def _on_sv_event(e):
        nonlocal picker_sat, picker_val
        lp = getattr(e, "local_position", None)
        x = max(0.0, min(float(PICKER_W), float(lp.x if lp else 0)))
        y = max(0.0, min(float(PICKER_H), float(lp.y if lp else 0)))
        picker_sat = x / PICKER_W
        picker_val = 1.0 - y / PICKER_H
        _update_picker_visuals()

    def _on_hue_event(e):
        nonlocal picker_hue
        lp = getattr(e, "local_position", None)
        x = max(0.0, min(float(PICKER_W), float(lp.x if lp else 0)))
        picker_hue = (x / PICKER_W) * 360.0
        _update_picker_visuals()

    def _close_picker():
        page.pop_dialog()

    def _apply_picker_color(e=None):
        nonlocal picker_target
        hex_val = _hsv_to_hex(picker_hue, picker_sat, picker_val)
        target = picker_target
        _close_picker()
        if target == "base":
            studio_base_field.value = hex_val
            render_route("/theme-studio")
        elif target == "surface":
            studio_surface_field.value = hex_val
            render_route("/theme-studio")
        elif target == "accent":
            studio_accent_field.value = hex_val
            render_route("/theme-studio")
        elif isinstance(target, tuple) and target[0] == "edit":
            _, theme_name, color_key = target
            _apply_theme_color_edit(theme_name, color_key, hex_val)

    def _ensure_picker_ready():
        if _picker_dialog_ref[0] is not None:
            return
        sv_bg = ft.Container(width=PICKER_W, height=PICKER_H, bgcolor="#FF0000")
        cursor = ft.Container(
            width=20, height=20,
            border_radius=ft.BorderRadius.all(10),
            border=ft.Border.all(2.5, "white"),
            shadow=ft.BoxShadow(blur_radius=6, color="#66000000"),
            left=PICKER_W - 10, top=10,
        )
        hue_thumb = ft.Container(
            width=22, height=22,
            border_radius=ft.BorderRadius.all(11),
            bgcolor="white",
            border=ft.Border.all(2, "#888888"),
            shadow=ft.BoxShadow(blur_radius=4, color="#44000000"),
            left=0, top=-1,
        )
        result_swatch = ft.Container(
            width=44, height=44,
            border_radius=ft.BorderRadius.all(10),
            bgcolor="#FF0000",
            border=ft.Border.all(1.5, "#44FFFFFF"),
        )
        hex_text = ft.Text("#FF0000", size=15, weight=ft.FontWeight.BOLD, color="#F0F0F0")

        _pc["sv_bg"] = sv_bg
        _pc["cursor"] = cursor
        _pc["hue_thumb"] = hue_thumb
        _pc["result_swatch"] = result_swatch
        _pc["hex_text"] = hex_text

        sv_canvas = ft.GestureDetector(
            on_tap=_on_sv_event,
            on_pan_start=_on_sv_event,
            on_pan_update=_on_sv_event,
            content=ft.Stack(
                width=PICKER_W, height=PICKER_H,
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                controls=[
                    sv_bg,
                    ft.Container(
                        width=PICKER_W, height=PICKER_H,
                        gradient=ft.LinearGradient(
                            begin=ft.Alignment(-1, 0), end=ft.Alignment(1, 0),
                            colors=["#FFFFFFFF", "#00FFFFFF"],
                        ),
                    ),
                    ft.Container(
                        width=PICKER_W, height=PICKER_H,
                        gradient=ft.LinearGradient(
                            begin=ft.Alignment(0, -1), end=ft.Alignment(0, 1),
                            colors=["#00000000", "#FF000000"],
                        ),
                    ),
                    cursor,
                ],
            ),
        )
        hue_strip = ft.GestureDetector(
            on_tap=_on_hue_event,
            on_pan_start=_on_hue_event,
            on_pan_update=_on_hue_event,
            content=ft.Stack(
                width=PICKER_W, height=HUE_H,
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                controls=[
                    ft.Container(
                        width=PICKER_W, height=HUE_H,
                        border_radius=ft.BorderRadius.all(HUE_H // 2),
                        gradient=ft.LinearGradient(
                            begin=ft.Alignment(-1, 0), end=ft.Alignment(1, 0),
                            colors=["#FF0000", "#FFFF00", "#00FF00",
                                    "#00FFFF", "#0000FF", "#FF00FF", "#FF0000"],
                        ),
                    ),
                    hue_thumb,
                ],
            ),
        )
        _picker_dialog_ref[0] = ft.AlertDialog(
            title=ft.Text("Escolher cor", weight=ft.FontWeight.BOLD),
            bgcolor="#1A2820",
            content=ft.Column(
                controls=[
                    sv_canvas,
                    ft.Container(height=14),
                    hue_strip,
                    ft.Container(height=14),
                    ft.Row(
                        controls=[result_swatch, hex_text],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=0, tight=True, width=PICKER_W,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: _close_picker()),
                ft.FilledButton("Aplicar", on_click=_apply_picker_color),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def _open_color_picker(target_id, current_hex):
        nonlocal picker_target, picker_hue, picker_sat, picker_val
        picker_target = target_id
        picker_hue, picker_sat, picker_val = _hex_to_hsv(current_hex)
        _ensure_picker_ready()
        _update_picker_visuals()
        page.show_dialog(_picker_dialog_ref[0])

    def color_swatch_button(field, target_id):
        """Tappable colour swatch — opens the visual picker for that field."""
        cur_hex = field.value or "#000000"
        bg = cur_hex if is_hex_color(cur_hex) else "#888888"
        return ft.GestureDetector(
            on_tap=lambda e, t=target_id, f=field: _open_color_picker(t, f.value),
            content=ft.Container(
                width=40, height=40,
                border_radius=ft.BorderRadius.all(8),
                bgcolor=bg,
                border=ft.Border.all(1.5, effective_theme()["slot_border"]),
                tooltip="Escolher cor com selector visual",
            ),
        )

    # ── Theme management helpers ──────────────────────────────────────────────

    def _apply_theme_color_edit(theme_name, color_key, new_hex):
        current = THEME_OPTIONS.get(theme_name, {})
        base = current.get("board_bg", "#1E6B42")
        surface = current.get("panel_bg", "#153221")
        accent = current.get("accent", "#F1CE6E")
        light_text = is_light_color(current.get("text", "#F0F0F0"))
        if color_key == "base":
            base = new_hex
        elif color_key == "surface":
            surface = new_hex
        elif color_key == "accent":
            accent = new_hex
        try:
            update_custom_theme_palette(theme_name, base, surface, accent, light_text)
            refresh_custom_theme_registry()
            if settings.theme_name == theme_name:
                apply_visual_draft(refresh_route=False)
        except Exception:
            pass
        render_route("/manage-themes")

    def _open_rename_dialog(theme_name):
        name_field = ft.TextField(
            value=THEME_OPTIONS[theme_name]["label"],
            label="Nome do tema",
            autofocus=True,
        )

        def _do_rename(e):
            new_label = (name_field.value or "").strip()
            if len(new_label) < 2:
                return
            rename_custom_theme(theme_name, new_label)
            refresh_custom_theme_registry()
            page.pop_dialog()
            render_route("/manage-themes")

        page.show_dialog(ft.AlertDialog(
            title=ft.Text("Renomear tema"),
            content=name_field,
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                ft.FilledButton("Guardar", on_click=_do_rename),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        ))

    def _open_delete_confirm(theme_name):
        label = THEME_OPTIONS.get(theme_name, {}).get("label", theme_name)

        def _do_delete(e):
            nonlocal draft_card_back_name, draft_theme_name, draft_board_bg_style, draft_board_bg_target
            delete_custom_theme(theme_name)
            refresh_custom_theme_registry()
            visuals_changed = False
            if settings.theme_name == theme_name:
                settings.theme_name = "classic"
                settings.card_back_name = "classic"
                draft_card_back_name = "classic"
                draft_theme_name = "classic"
                visuals_changed = True
            if settings.card_back_name == theme_name:
                settings.card_back_name = "classic"
                draft_card_back_name = "classic"
                visuals_changed = True
            if settings.board_bg_style == "image" and settings.board_bg_target == theme_name:
                settings.board_bg_style = "theme_color"
                settings.board_bg_target = ""
                draft_board_bg_style = "theme_color"
                draft_board_bg_target = ""
                visuals_changed = True
            if visuals_changed:
                sync_board_visuals(update=False)
                page.run_task(save_visual_settings_async)
            page.pop_dialog()
            render_route("/manage-themes")

        page.show_dialog(ft.AlertDialog(
            title=ft.Text("Eliminar tema"),
            content=ft.Text(
                f"Tens a certeza que queres eliminar '{label}'? Esta ação não pode ser desfeita."
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                ft.FilledButton(
                    "Eliminar",
                    on_click=_do_delete,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        ))

    # ── Board background helpers (per-theme) ─────────────────────────────────

    # Studio board bg (picked while creating a new theme)
    async def _pick_studio_board_bg_async():
        nonlocal studio_board_bg_bytes, studio_board_bg_name
        selected = await pick_single_image(
            "Escolhe o fundo do tabuleiro",
            on_error=lambda message: (
                setattr(theme_studio_status, "value", message),
                render_route("/theme-studio"),
            ),
        )
        if selected is None:
            return
        studio_board_bg_bytes = selected["bytes"]
        studio_board_bg_name = selected["name"]
        theme_studio_status.value = f"Fundo '{studio_board_bg_name}' carregado."
        render_route("/theme-studio")

    def _choose_studio_board_bg(e=None):
        page.run_task(_pick_studio_board_bg_async)

    def _clear_studio_board_bg(e=None):
        nonlocal studio_board_bg_bytes, studio_board_bg_name
        studio_board_bg_bytes = None
        studio_board_bg_name = None
        render_route("/theme-studio")

    # Per-theme board bg management (from manage-themes view)
    def _choose_board_bg_for_theme(theme_name):
        async def _pick():
            selected = await pick_single_image("Fundo do tabuleiro para este tema")
            if selected is None:
                return
            update_custom_theme_board_bg(theme_name, selected["bytes"], selected["name"])
            refresh_custom_theme_registry()
            apply_page_theme()
            render_route("/manage-themes")
        page.run_task(_pick)

    def _clear_board_bg_for_theme(theme_name):
        nonlocal draft_board_bg_style, draft_board_bg_target
        update_custom_theme_board_bg(theme_name, None, None)
        refresh_custom_theme_registry()
        if settings.board_bg_style == "image" and settings.board_bg_target == theme_name:
            settings.board_bg_style = "theme_color"
            settings.board_bg_target = ""
            draft_board_bg_style = "theme_color"
            draft_board_bg_target = ""
            page.run_task(save_visual_settings_async)
        apply_page_theme()
        render_route("/manage-themes")

    # ── End new helpers ───────────────────────────────────────────────────────

    def on_win():
        page.show_dialog(ft.AlertDialog(
            title=ft.Text("Vitória!"),
            content=ft.Text("Completaste as quatro fundações."),
            actions=[ft.FilledButton("OK", on_click=lambda e: page.pop_dialog())],
            actions_alignment=ft.MainAxisAlignment.END,
        ))

    def refresh_hud(autosave=False):
        """
        Sincroniza score, tempo e mensagens entre o tabuleiro e a UI.

        Args:
            autosave:
                Mantido na assinatura para compatibilidade com o callback
                `on_change` do tabuleiro.
        """
        score_text.value = f"Score: {board.score}"
        timer_text.value = f"Tempo: {board.format_elapsed()}"
        status_text.value = board.status_message
        intro_status.value = board.status_message
        try:
            score_text.update()
            timer_text.update()
            status_text.update()
            intro_status.update()
        except Exception:
            pass

    board = GameBoard(page=page, settings=settings, on_win=on_win, on_change=refresh_hud)
    board.setup()

    page.services.append(
        ft.ShakeDetector(
            minimum_shake_count=4,
            shake_slop_time_ms=300,
            shake_count_reset_time_ms=1000,
            on_shake=lambda _: board.auto_win() if (page.route or "/intro") == "/game" else None,
        )
    )

    board_frame = ft.Container(
        content=board,
        bgcolor=effective_board_state(use_draft=False)["color"],
        padding=ft.Padding.symmetric(horizontal=2, vertical=4),
        alignment=ft.Alignment.TOP_CENTER,
        expand=True,
    )
    game_status_banner = ft.Container(
        padding=ft.Padding.symmetric(horizontal=14, vertical=10),
        border_radius=ft.BorderRadius.all(18),
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.INFO_OUTLINE, size=16),
                status_text,
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    def sync_board_visuals(update=True):
        """
        Reaplica no tabuleiro a configuracao visual atualmente efetiva.

        Args:
            update:
                Se `True`, o controlo do tabuleiro e atualizado no final.
        """
        board.settings = settings
        board.apply_visual_preferences(update=False)
        board.display_waste(update=False)
        if update and board.can_update():
            board.update()

    def sync_draft_visuals_from_settings():
        """
        Copia a configuracao efetiva para o estado temporario de edicao.
        """
        nonlocal draft_card_back_name, draft_theme_name, draft_board_bg_style, draft_board_bg_target
        draft_card_back_name = settings.card_back_name
        draft_theme_name = settings.theme_name
        draft_board_bg_style = settings.board_bg_style
        draft_board_bg_target = settings.board_bg_target

    def sync_settings_from_board():
        """
        Faz o caminho inverso: traz do tabuleiro para `settings` o estado atual.
        """
        nonlocal settings
        settings = board.settings
        sync_draft_visuals_from_settings()

    async def load_preferences_json(key):
        try:
            preferences = ft.SharedPreferences()
            raw_value = await preferences.get(key)
        except Exception:
            return None
        if not raw_value:
            return None
        try:
            return json.loads(raw_value)
        except json.JSONDecodeError:
            return None

    async def save_preferences_json(key, payload):
        try:
            preferences = ft.SharedPreferences()
            await preferences.set(key, json.dumps(payload))
            return None
        except Exception as exc:
            return str(exc)

    def load_storage_payload(loader):
        """
        Executa um loader de persistencia com tolerancia a falhas.

        Args:
            loader:
                Callable que tenta ler um payload de storage.

        Returns:
            O payload carregado, ou `None` se a origem falhar.
        """
        try:
            return loader()
        except Exception:
            return None

    async def load_saved_snapshot():
        snapshot = load_storage_payload(storage.load_game)
        if snapshot is not None:
            return snapshot
        return await load_preferences_json(LOCAL_GAME_STATE_KEY)

    async def load_saved_visual_settings():
        visual_payload = load_storage_payload(storage.load_visual_settings)
        if visual_payload is not None:
            return visual_payload
        return await load_preferences_json(VISUAL_SETTINGS_KEY)

    async def autosave_current_state():
        snapshot = board.capture_state(include_initial=True)
        await save_preferences_json(LOCAL_GAME_STATE_KEY, snapshot)
        try:
            storage.save_game(snapshot)
        except Exception:
            pass

    def autosave_current_state_sync():
        """
        Dispara a gravacao da partida em modo sincrono e assincro.

        A copia DuckDB e tentada imediatamente e a copia em preferencias
        locais e delegada para `page.run_task`.
        """
        snapshot = board.capture_state(include_initial=True)
        try:
            storage.save_game(snapshot)
        except Exception:
            pass
        page.run_task(autosave_current_state)

    async def save_visual_settings_async():
        data = build_visual_settings_payload()
        await save_preferences_json(VISUAL_SETTINGS_KEY, data)
        try:
            storage.save_visual_settings(data)
        except Exception:
            pass

    def navigate(route: str):
        """
        Muda a rota interna da app e trata efeitos secundarios do fluxo.

        Args:
            route:
                Nova rota logica a apresentar.
        """
        current_route = page.route or "/intro"
        if current_route == "/game" and route == "/intro":
            autosave_current_state_sync()
        if route != "/game":
            hide_victory_celebration(immediate=True)
        page.route = route
        render_route(route)

    def show_intro(e=None):
        navigate("/intro")

    def show_game(e=None):
        navigate("/game")

    def open_config_from_intro(e=None):
        nonlocal config_return_route, config_theme_tab
        config_return_route = "/intro"
        sync_draft_visuals_from_settings()
        config_theme_tab = "combo"
        navigate("/config")

    def open_config_from_game(e=None):
        nonlocal config_return_route, config_theme_tab
        config_return_route = "/game"
        sync_draft_visuals_from_settings()
        config_theme_tab = "combo"
        navigate("/config")

    def open_theme_studio(e=None):
        nonlocal studio_image_bytes, studio_image_name, studio_board_bg_bytes, studio_board_bg_name
        current_theme = settings.theme
        studio_name_field.value = f"{current_theme['label']} Remix"
        studio_base_field.value = current_theme["board_bg"]
        studio_surface_field.value = current_theme["panel_bg"]
        studio_accent_field.value = current_theme["accent"]
        studio_light_text_switch.value = is_light_color(current_theme["text"])
        studio_zoom_slider.value = 1.0
        studio_image_bytes = None
        studio_image_name = None
        studio_board_bg_bytes = None
        studio_board_bg_name = None
        theme_studio_status.value = "Cria uma paleta, faz upload do verso, etc."
        navigate("/theme-studio")

    def preview_theme_studio(e=None):
        theme_studio_status.value = "Preview atualizado."
        render_route("/theme-studio")

    async def pick_theme_studio_image_async():
        nonlocal studio_image_bytes, studio_image_name
        selected = await pick_single_image(
            "Escolhe a imagem do verso da carta",
            on_error=lambda message: (
                setattr(theme_studio_status, "value", message),
                render_route("/theme-studio"),
            ),
        )
        if selected is None:
            return

        studio_image_bytes = selected["bytes"]
        studio_image_name = selected["name"]
        theme_studio_status.value = f"Imagem '{studio_image_name}' pronta para o tema."
        render_route("/theme-studio")

    def choose_theme_studio_image(e=None):
        page.run_task(pick_theme_studio_image_async)

    studio_zoom_slider.on_change = preview_theme_studio
    studio_light_text_switch.on_change = preview_theme_studio

    def save_theme_studio(e=None):
        nonlocal draft_card_back_name, draft_theme_name, draft_board_bg_style, draft_board_bg_target
        name_value = (studio_name_field.value or "").strip()
        if len(name_value) < 3:
            theme_studio_status.value = "Dá um nome ao tema."
            render_route("/theme-studio")
            return

        invalid_fields = []
        if not is_hex_color(studio_base_field.value):
            invalid_fields.append("cor base")
        if not is_hex_color(studio_surface_field.value):
            invalid_fields.append("cor dos paineis")
        if not is_hex_color(studio_accent_field.value):
            invalid_fields.append("cor de destaque")
        if invalid_fields:
            theme_studio_status.value = (
                "Revê os hexadecimais: " + ", ".join(invalid_fields) + "."
            )
            render_route("/theme-studio")
            return

        try:
            created = save_custom_theme_bundle(
                label=name_value,
                base_color=studio_base_field.value,
                surface_color=studio_surface_field.value,
                accent_color=studio_accent_field.value,
                use_light_text=bool(studio_light_text_switch.value),
                image_bytes=studio_image_bytes,
                original_filename=studio_image_name,
                image_scale=studio_zoom_slider.value or 1.0,
                board_bg_bytes=studio_board_bg_bytes,
                board_bg_filename=studio_board_bg_name,
            )
        except ValueError as exc:
            theme_studio_status.value = str(exc)
            render_route("/theme-studio")
            return

        refresh_custom_theme_registry()
        draft_card_back_name = created["back_name"]
        draft_theme_name = created["theme_name"]
        draft_board_bg_style = "image" if created["back"].get("board_bg") else "theme_color"
        draft_board_bg_target = created["back_name"] if created["back"].get("board_bg") else ""
        apply_visual_draft(refresh_route=False)
        theme_studio_status.value = f"Tema '{created['theme']['label']}' criado e aplicado."
        navigate("/intro")
        board.set_status(f"Tema '{created['theme']['label']}' criado.")

    def apply_visual_draft(refresh_route=True):
        """
        Confirma as escolhas do configurador visual para o estado efetivo.

        Args:
            refresh_route:
                Se `True`, redesenha a rota atual para refletir o novo visual.
        """
        nonlocal draft_board_bg_style, draft_board_bg_target
        settings.card_back_name = draft_card_back_name
        settings.theme_name = draft_theme_name
        settings.board_bg_style, settings.board_bg_target = normalize_board_bg_state(
            draft_board_bg_style,
            draft_board_bg_target,
        )
        draft_board_bg_style = settings.board_bg_style
        draft_board_bg_target = settings.board_bg_target
        board.settings = settings
        sync_board_visuals(update=False)
        page.run_task(save_visual_settings_async)
        if refresh_route:
            render_route(page.route or "/config")

    def select_draft_back(e):
        nonlocal draft_card_back_name
        if e.control.data in BACK_OPTIONS:
            draft_card_back_name = e.control.data
            apply_visual_draft()

    def select_draft_theme(e):
        nonlocal draft_theme_name
        if e.control.data in THEME_OPTIONS:
            draft_theme_name = e.control.data
            apply_visual_draft()

    def apply_preset(e):
        nonlocal draft_card_back_name, draft_theme_name, draft_board_bg_style, draft_board_bg_target
        preset = e.control.data
        draft_card_back_name = preset["back"]
        draft_theme_name = preset["theme"]
        draft_board_bg_style = preset.get("board_bg_style", "theme_color")
        draft_board_bg_target = preset.get("board_bg_target", "")
        apply_visual_draft()

    async def save_game():
        snapshot = board.capture_state(include_initial=True)
        local_error = await save_preferences_json(LOCAL_GAME_STATE_KEY, snapshot)
        duck_error = None
        try:
            storage.save_game(snapshot)
        except Exception as exc:
            duck_error = str(exc)

        if local_error is None and duck_error is None:
            board.set_status("Partida guardada.")
        elif local_error is None:
            board.set_status(f"Guardado local. DuckDB indisponivel: {duck_error}")
        elif duck_error is None:
            board.set_status(f"Guardado em DuckDB. Local storage indisponivel: {local_error}")
        else:
            board.set_status("Nao foi possivel guardar a partida.")

    async def load_game():
        snapshot = await load_saved_snapshot()
        if snapshot is None:
            board.set_status("Nao existe uma partida guardada.")
            if page.route == "/intro":
                render_route("/intro")
            return False

        hide_victory_celebration(immediate=True)
        board.restore_state(snapshot, clear_history=True, set_initial=True, announce=False)
        sync_settings_from_board()
        sync_board_visuals(update=False)
        render_route(page.route or "/intro")
        board.set_status("Partida carregada.")
        return True

    async def auto_load_on_start():
        visual = await load_saved_visual_settings()
        if visual is not None:
            restore_visual_settings_payload(visual)
        snapshot = await load_saved_snapshot()
        if snapshot is not None:
            board.restore_state(snapshot, clear_history=True, set_initial=True, announce=False)
            sync_settings_from_board()
            sync_board_visuals(update=False)
            render_route(page.route or "/intro")
            return

        # No game saved — try to restore the last visual settings
        if visual is None:
            return
        restore_visual_settings_payload(visual)
        sync_board_visuals(update=False)
        render_route(page.route or "/intro")

    def start_new_game_from_intro(e):
        hide_victory_celebration(immediate=True)
        board.settings = settings
        board.start_new_game()
        show_game()

    def continue_current_game(e):
        show_game()

    def new_game(e):
        hide_victory_celebration(immediate=True)
        board.start_new_game()

    def restart(e):
        hide_victory_celebration(immediate=True)
        board.restart_game()

    def undo(e):
        board.undo_move()

    def save_clicked(e):
        page.run_task(save_game)

    def load_clicked(e):
        page.run_task(load_game)

    FIREWORK_SLOT_COUNT = 4
    FIREWORK_PARTICLE_COUNT = 12
    FIREWORK_PALETTE = [
        "#FFD166",
        "#FF7A45",
        "#FF4FA3",
        "#7CF7FF",
        "#8DF26A",
        "#F8F4E3",
    ]

    victory_visible = False
    victory_sequence = 0

    def make_victory_title_card(text, eyebrow):
        return ft.Container(
            key=f"title:{text}",
            content=ft.Column(
                controls=[
                    ft.Text(
                        eyebrow,
                        size=12,
                        weight=ft.FontWeight.W_600,
                        color="#FFD166",
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        text,
                        size=36 if is_narrow() else 42,
                        weight=ft.FontWeight.W_700,
                        color="#F8F4E3",
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                spacing=4,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def make_victory_subtitle_card(text):
        return ft.Container(
            key=f"subtitle:{text}",
            width=420 if not is_narrow() else None,
            content=ft.Text(
                text,
                size=14 if is_narrow() else 15,
                color="#E8DED0",
                text_align=ft.TextAlign.CENTER,
            ),
        )

    def make_victory_action_button(label, icon, filled):
        background = "#FFD166" if filled else "#22161F33"
        border_color = "#FFD166" if filled else "#55FFD166"
        text_color = "#120F16" if filled else "#F8F4E3"
        icon_color = "#120F16" if filled else "#FFD166"
        return ft.Container(
            ink=True,
            width=230 if not is_narrow() else None,
            padding=ft.Padding.symmetric(horizontal=22, vertical=16),
            border_radius=ft.BorderRadius.all(999),
            bgcolor=background,
            border=ft.Border.all(1.3, border_color),
            shadow=ft.BoxShadow(
                blur_radius=24 if filled else 18,
                color="#55FFD166" if filled else "#22000000",
                offset=ft.Offset(0, 8),
            ),
            content=ft.Row(
                controls=[
                    ft.Icon(icon, size=20, color=icon_color),
                    ft.Text(
                        label,
                        size=15,
                        weight=ft.FontWeight.W_600,
                        color=text_color,
                    ),
                ],
                spacing=10,
                tight=True,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def make_victory_glow(color, size, **position):
        return ft.Container(
            width=size,
            height=size,
            shape=ft.BoxShape.CIRCLE,
            bgcolor=color,
            opacity=0,
            scale=0.65,
            shadow=ft.BoxShadow(
                blur_radius=180,
                spread_radius=30,
                color=color,
                offset=ft.Offset(0, 0),
            ),
            animate_opacity=ft.Animation(380, ft.AnimationCurve.EASE_OUT),
            animate_scale=ft.Animation(1600, ft.AnimationCurve.EASE_OUT_CUBIC),
            animate_offset=ft.Animation(2600, ft.AnimationCurve.EASE_IN_OUT_SINE),
            **position,
        )

    def make_firework_particle(color):
        return ft.Container(
            width=10,
            height=10,
            left=-80,
            top=-80,
            opacity=0,
            scale=0.15,
            shape=ft.BoxShape.CIRCLE,
            bgcolor=color,
            shadow=ft.BoxShadow(
                blur_radius=18,
                spread_radius=1,
                color=color,
                offset=ft.Offset(0, 0),
            ),
            animate_position=ft.Animation(760, ft.AnimationCurve.EASE_OUT_CUBIC),
            animate_scale=ft.Animation(760, ft.AnimationCurve.EASE_OUT),
            animate_opacity=ft.Animation(760, ft.AnimationCurve.EASE_OUT),
        )

    victory_badge_text = ft.Text(
        "QUATRO FUNDACOES FECHADAS",
        size=12,
        weight=ft.FontWeight.W_600,
        color="#120F16",
    )
    victory_score_value = ft.Text(
        "0",
        size=22,
        weight=ft.FontWeight.W_700,
        color="#F8F4E3",
    )
    victory_time_value = ft.Text(
        "00:00",
        size=22,
        weight=ft.FontWeight.W_700,
        color="#F8F4E3",
    )
    victory_hint_text = ft.Text(
        "Toca fora do painel para voltar a ver a mesa.",
        size=12,
        color="#BFAE95",
        text_align=ft.TextAlign.CENTER,
    )
    victory_title_switcher = ft.AnimatedSwitcher(
        content=make_victory_title_card("VITORIA TOTAL", "FINAL CINEMATICO"),
        transition=ft.AnimatedSwitcherTransition.SCALE,
        duration=520,
        reverse_duration=180,
        switch_in_curve=ft.AnimationCurve.BOUNCE_OUT,
        switch_out_curve=ft.AnimationCurve.EASE_IN,
    )
    victory_subtitle_switcher = ft.AnimatedSwitcher(
        content=make_victory_subtitle_card("As quatro fundacoes foram tomadas."),
        transition=ft.AnimatedSwitcherTransition.FADE,
        duration=420,
        reverse_duration=140,
        switch_in_curve=ft.AnimationCurve.EASE_OUT,
        switch_out_curve=ft.AnimationCurve.EASE_IN,
    )
    victory_new_game_button = make_victory_action_button("Nova partida", ft.Icons.CASINO, True)
    victory_close_button = make_victory_action_button("Ver mesa", ft.Icons.VISIBILITY, False)
    victory_buttons = ft.Row(
        wrap=True,
        spacing=12,
        run_spacing=12,
        alignment=ft.MainAxisAlignment.CENTER,
        controls=[victory_new_game_button, victory_close_button],
    )

    def make_victory_stat_card(icon, label, value_control):
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=16, vertical=14),
            border_radius=ft.BorderRadius.all(22),
            bgcolor="#2218232E",
            border=ft.Border.all(1.1, "#44FFD166"),
            content=ft.Row(
                controls=[
                    ft.Container(
                        width=38,
                        height=38,
                        border_radius=ft.BorderRadius.all(14),
                        bgcolor="#33FFD166",
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(icon, size=20, color="#FFD166"),
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(label, size=11, color="#BFAE95"),
                            value_control,
                        ],
                        spacing=2,
                        tight=True,
                    ),
                ],
                spacing=10,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    victory_stats = ft.Row(
        wrap=True,
        spacing=12,
        run_spacing=12,
        alignment=ft.MainAxisAlignment.CENTER,
        controls=[
            make_victory_stat_card(ft.Icons.STARS, "Score final", victory_score_value),
            make_victory_stat_card(ft.Icons.SCHEDULE, "Tempo final", victory_time_value),
        ],
    )

    victory_panel = ft.Container(
        width=560,
        opacity=0,
        scale=0.82,
        offset=ft.Offset(0, 0.08),
        padding=ft.Padding.symmetric(horizontal=24, vertical=24),
        border_radius=ft.BorderRadius.all(34),
        gradient=ft.LinearGradient(
            colors=["#FF120F16", "#FF1D1322", "#FF090A10"],
            begin=ft.Alignment(-1, -1),
            end=ft.Alignment(1, 1),
        ),
        border=ft.Border.all(1.4, "#55FFD166"),
        shadow=ft.BoxShadow(
            blur_radius=36,
            spread_radius=2,
            color="#77000000",
            offset=ft.Offset(0, 14),
        ),
        animate_opacity=ft.Animation(260, ft.AnimationCurve.EASE_OUT),
        animate_scale=ft.Animation(720, ft.AnimationCurve.BOUNCE_OUT),
        animate_offset=ft.Animation(720, ft.AnimationCurve.EASE_OUT_CUBIC),
        content=ft.Column(
            spacing=18,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=16, vertical=10),
                    border_radius=ft.BorderRadius.all(999),
                    bgcolor="#FFD166",
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.LOCAL_FIRE_DEPARTMENT, size=18, color="#120F16"),
                            victory_badge_text,
                        ],
                        spacing=8,
                        tight=True,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ),
                victory_title_switcher,
                victory_subtitle_switcher,
                victory_stats,
                victory_buttons,
                victory_hint_text,
            ],
        ),
    )

    victory_backdrop = ft.Container(
        left=0,
        right=0,
        top=0,
        bottom=0,
        blur=8,
        bgcolor="#B8060910",
        gradient=ft.LinearGradient(
            colors=["#F505060B", "#E5110E1C", "#FF04050A"],
            begin=ft.Alignment(-0.2, -1),
            end=ft.Alignment(0.2, 1),
        ),
        on_click=lambda e: hide_victory_celebration(),
    )
    victory_flash = ft.Container(
        left=0,
        right=0,
        top=0,
        bottom=0,
        opacity=0,
        gradient=ft.LinearGradient(
            colors=["#00FFF1D0", "#55FFD166", "#00FF7A45"],
            begin=ft.Alignment(0, -1),
            end=ft.Alignment(0, 1),
        ),
        animate_opacity=ft.Animation(220, ft.AnimationCurve.EASE_OUT),
    )
    victory_glow_left = make_victory_glow("#44FF7A45", 280, left=-80, top=-40)
    victory_glow_right = make_victory_glow("#447CF7FF", 320, right=-120, top=80)
    victory_glow_bottom = make_victory_glow("#33FFD166", 340, left=40, bottom=-150)

    firework_slots = []
    firework_controls = []
    for slot_index in range(FIREWORK_SLOT_COUNT):
        ring = ft.Container(
            width=26,
            height=26,
            left=-120,
            top=-120,
            opacity=0,
            scale=0.2,
            shape=ft.BoxShape.CIRCLE,
            border=ft.Border.all(2.4, FIREWORK_PALETTE[slot_index % len(FIREWORK_PALETTE)]),
            animate_position=ft.Animation(720, ft.AnimationCurve.EASE_OUT_CUBIC),
            animate_scale=ft.Animation(720, ft.AnimationCurve.EASE_OUT),
            animate_opacity=ft.Animation(720, ft.AnimationCurve.EASE_OUT),
        )
        flare = ft.Container(
            width=36,
            height=36,
            left=-140,
            top=-140,
            opacity=0,
            scale=0.35,
            shape=ft.BoxShape.CIRCLE,
            bgcolor="#88FFF1D0",
            shadow=ft.BoxShadow(
                blur_radius=38,
                spread_radius=8,
                color="#66FFD166",
                offset=ft.Offset(0, 0),
            ),
            animate_position=ft.Animation(260, ft.AnimationCurve.EASE_OUT),
            animate_scale=ft.Animation(260, ft.AnimationCurve.EASE_OUT),
            animate_opacity=ft.Animation(260, ft.AnimationCurve.EASE_OUT),
        )
        particles = [
            make_firework_particle(
                FIREWORK_PALETTE[(slot_index + particle_index) % len(FIREWORK_PALETTE)]
            )
            for particle_index in range(FIREWORK_PARTICLE_COUNT)
        ]
        firework_slots.append(
            {
                "ring": ring,
                "flare": flare,
                "particles": particles,
            }
        )
        firework_controls.extend([ring, flare, *particles])

    victory_overlay = ft.Container(
        left=0,
        right=0,
        top=0,
        bottom=0,
        opacity=0,
        ignore_interactions=True,
        animate_opacity=ft.Animation(280, ft.AnimationCurve.EASE_OUT),
        content=ft.Stack(
            expand=True,
            controls=[
                victory_backdrop,
                victory_glow_left,
                victory_glow_right,
                victory_glow_bottom,
                *firework_controls,
                victory_flash,
                ft.Container(
                    expand=True,
                    alignment=ft.Alignment.CENTER,
                    padding=ft.Padding.symmetric(horizontal=12, vertical=18),
                    content=victory_panel,
                ),
            ],
        ),
    )

    def sync_victory_layout():
        """
        Ajusta dimensoes do overlay de vitoria ao tamanho atual da janela.
        """
        available_width = max(300, page_width() - 28)
        victory_panel.width = min(560, available_width)
        button_width = None if not is_narrow() else max(220, available_width - 36)
        victory_new_game_button.width = button_width
        victory_close_button.width = button_width

    def reset_fireworks():
        for glow in (victory_glow_left, victory_glow_right, victory_glow_bottom):
            glow.opacity = 0
            glow.scale = 0.65
            glow.offset = ft.Offset(0, 0)
        victory_flash.opacity = 0
        for slot in firework_slots:
            slot["ring"].left = -120
            slot["ring"].top = -120
            slot["ring"].opacity = 0
            slot["ring"].scale = 0.2
            slot["flare"].left = -140
            slot["flare"].top = -140
            slot["flare"].opacity = 0
            slot["flare"].scale = 0.35
            for particle in slot["particles"]:
                particle.left = -120
                particle.top = -120
                particle.opacity = 0
                particle.scale = 0.15

    def victory_sequence_active(sequence_id):
        return sequence_id == victory_sequence and (page.route or "/intro") == "/game"

    def hide_victory_celebration(e=None, immediate=False):
        """
        Fecha a tela de vitoria e invalida qualquer animacao em curso.

        Args:
            e:
                Evento opcional do Flet.
            immediate:
                Parametro semantico usado pelos chamadores para indicar fecho
                sem transicao de fluxo.
        """
        nonlocal victory_visible, victory_sequence
        victory_sequence += 1
        victory_visible = False
        victory_overlay.ignore_interactions = True
        victory_overlay.opacity = 0
        victory_panel.opacity = 0
        victory_panel.scale = 0.82
        victory_panel.offset = ft.Offset(0, 0.08)
        reset_fireworks()
        try:
            page.update()
        except Exception:
            pass

    async def launch_firework(slot_index, center_x, center_y, delay, sequence_id):
        """
        Dispara uma explosao individual de fogos no overlay de vitoria.

        Args:
            slot_index:
                Slot de particulas reutilizado nesta explosao.
            center_x:
                Coordenada horizontal do centro do burst.
            center_y:
                Coordenada vertical do centro do burst.
            delay:
                Tempo de espera antes da animacao.
            sequence_id:
                Token da celebracao ativa para impedir animacoes obsoletas.
        """
        await asyncio.sleep(delay)
        if not victory_sequence_active(sequence_id):
            return

        slot = firework_slots[slot_index % len(firework_slots)]
        burst_color = FIREWORK_PALETTE[
            (slot_index + random.randrange(len(FIREWORK_PALETTE))) % len(FIREWORK_PALETTE)
        ]
        ring = slot["ring"]
        flare = slot["flare"]
        ring.border = ft.Border.all(2.4, burst_color)
        ring.left = center_x - 13
        ring.top = center_y - 13
        ring.opacity = 0.95
        ring.scale = 0.22

        flare.bgcolor = burst_color
        flare.shadow = ft.BoxShadow(
            blur_radius=42,
            spread_radius=8,
            color=burst_color,
            offset=ft.Offset(0, 0),
        )
        flare.left = center_x - 18
        flare.top = center_y - 18
        flare.opacity = 0.9
        flare.scale = 0.4

        for particle_index, particle in enumerate(slot["particles"]):
            particle.bgcolor = FIREWORK_PALETTE[
                (slot_index + particle_index) % len(FIREWORK_PALETTE)
            ]
            particle.shadow = ft.BoxShadow(
                blur_radius=22,
                spread_radius=1,
                color=particle.bgcolor,
                offset=ft.Offset(0, 0),
            )
            particle.left = center_x - 5
            particle.top = center_y - 5
            particle.opacity = 1
            particle.scale = 1

        try:
            page.update()
        except Exception:
            return

        await asyncio.sleep(0.04)
        if not victory_sequence_active(sequence_id):
            return

        ring.scale = 6.2
        ring.opacity = 0
        flare.scale = 1.5
        flare.opacity = 0

        for particle_index, particle in enumerate(slot["particles"]):
            angle = (math.tau / FIREWORK_PARTICLE_COUNT) * particle_index
            angle += random.uniform(-0.12, 0.12)
            distance = random.randint(80, 170)
            particle.left = center_x + math.cos(angle) * distance - 5
            particle.top = center_y + math.sin(angle) * distance - 5
            particle.opacity = 0
            particle.scale = 0.2

        try:
            page.update()
        except Exception:
            return

    async def play_victory_celebration():
        """
        Encena a tela de vitoria cinematica por cima do jogo.

        O fluxo faz:
        - preparar score e tempo final;
        - revelar o painel com `AnimatedSwitcher`;
        - disparar varios bursts de fogos;
        - trocar mensagens do titulo para dar sensacao de cena final.
        """
        nonlocal victory_visible, victory_sequence
        if (page.route or "/intro") != "/game" or victory_visible:
            return

        victory_visible = True
        victory_sequence += 1
        sequence_id = victory_sequence

        sync_victory_layout()
        reset_fireworks()
        victory_score_value.value = str(board.score)
        victory_time_value.value = board.format_elapsed()
        victory_title_switcher.transition = ft.AnimatedSwitcherTransition.SCALE
        victory_title_switcher.content = make_victory_title_card("VITORIA TOTAL", "FINAL CINEMATICO")
        victory_subtitle_switcher.transition = ft.AnimatedSwitcherTransition.FADE
        victory_subtitle_switcher.content = make_victory_subtitle_card(
            "As quatro fundacoes fecharam como o ultimo ato de um filme de acao."
        )
        victory_badge_text.value = "QUATRO FUNDACOES FECHADAS"
        victory_overlay.ignore_interactions = False
        victory_overlay.opacity = 0
        victory_panel.opacity = 0
        victory_panel.scale = 0.82
        victory_panel.offset = ft.Offset(0, 0.08)

        try:
            page.update()
        except Exception:
            return

        await asyncio.sleep(0.03)
        if not victory_sequence_active(sequence_id):
            return

        victory_overlay.opacity = 1
        victory_panel.opacity = 1
        victory_panel.scale = 1
        victory_panel.offset = ft.Offset(0, 0)
        victory_flash.opacity = 0.16
        victory_glow_left.opacity = 0.42
        victory_glow_left.scale = 1.15
        victory_glow_left.offset = ft.Offset(0.14, -0.06)
        victory_glow_right.opacity = 0.36
        victory_glow_right.scale = 1.08
        victory_glow_right.offset = ft.Offset(-0.1, 0.04)
        victory_glow_bottom.opacity = 0.26
        victory_glow_bottom.scale = 1.05
        victory_glow_bottom.offset = ft.Offset(0.08, -0.08)
        try:
            page.update()
        except Exception:
            return

        await asyncio.sleep(0.18)
        if not victory_sequence_active(sequence_id):
            return

        victory_flash.opacity = 0
        try:
            page.update()
        except Exception:
            return

        width = max(320, page_width() - 20)
        height = max(520, int(page.height or 820) - 32)
        bursts = [
            (0, width * 0.18, height * 0.2, 0.0),
            (1, width * 0.82, height * 0.22, 0.14),
            (2, width * 0.26, height * 0.56, 0.32),
            (3, width * 0.74, height * 0.58, 0.5),
        ]
        for slot_index, x_pos, y_pos, delay in bursts:
            asyncio.create_task(
                launch_firework(slot_index, int(x_pos), int(y_pos), delay, sequence_id)
            )

        await asyncio.sleep(0.48)
        if not victory_sequence_active(sequence_id):
            return

        victory_title_switcher.transition = ft.AnimatedSwitcherTransition.ROTATION
        victory_title_switcher.content = make_victory_title_card(
            "MISSAO COMPLETA",
            "SEM SOBREVIVENTES NO TABULEIRO",
        )
        victory_subtitle_switcher.content = make_victory_subtitle_card(
            "Explosao de pontos, cronometro parado e uma mesa completamente dominada."
        )
        try:
            page.update()
        except Exception:
            return

        await asyncio.sleep(0.8)
        if not victory_sequence_active(sequence_id):
            return

        victory_title_switcher.transition = ft.AnimatedSwitcherTransition.SCALE
        victory_title_switcher.content = make_victory_title_card("TABULEIRO DOMINADO", "CORTE FINAL")
        victory_subtitle_switcher.content = make_victory_subtitle_card(
            "Respira, aprecia a cena e decide se quer fechar a mesa ou entrar noutra ronda."
        )
        try:
            page.update()
        except Exception:
            return

    def start_new_game_after_victory(e=None):
        hide_victory_celebration(immediate=True)
        board.start_new_game()

    def trigger_victory_celebration():
        """
        Reencaminha o callback de vitoria do tabuleiro para a cena animada.
        """
        page.run_task(play_victory_celebration)

    board.on_win = trigger_victory_celebration
    victory_new_game_button.on_click = start_new_game_after_victory
    victory_close_button.on_click = hide_victory_celebration

    def handle_close(e):
        current_route = page.route or "/intro"
        if current_route == "/game":
            autosave_current_state_sync()

    def apply_config(e=None):
        apply_visual_draft(refresh_route=False)
        navigate(config_return_route)
        board.set_status("Visual atualizado.")

    def apply_page_theme():
        """
        Propaga o tema efetivo para a pagina, appbar e moldura do tabuleiro.
        """
        theme = effective_theme()
        board_state = effective_board_state()
        page.padding = 0 if page.route == "/game" else page_padding()
        page.bgcolor = theme["page_bg"]
        board_frame.bgcolor = board_state["color"]
        # Board background image — per-theme, behind the game
        bg = board_state["image"]
        board_frame.image = ft.DecorationImage(src=bg, fit=ft.BoxFit.COVER, opacity=0.75) if bg else None
        board_frame.padding = ft.Padding.symmetric(
            horizontal=2 if is_narrow() else 12,
            vertical=4 if is_narrow() else 12,
        )
        status_text.color = theme["text"]
        game_status_banner.bgcolor = theme["panel_bg"]
        game_status_banner.border = ft.Border.all(1.2, theme["slot_border"])
        if isinstance(game_status_banner.content, ft.Row):
            for control in game_status_banner.content.controls:
                if isinstance(control, ft.Icon):
                    control.color = theme["accent"]
        intro_status.color = theme["text"]
        theme_studio_status.color = theme["text"]

        for text in (score_text, timer_text):
            text.color = theme["text"]

        if page.appbar is not None:
            page.appbar.bgcolor = theme["header_bg"]
            if isinstance(page.appbar.title, ft.Text):
                page.appbar.title.color = theme["text"]
            if page.appbar.leading is not None and hasattr(page.appbar.leading, "icon_color"):
                page.appbar.leading.icon_color = theme["text"]
            for action in page.appbar.actions or []:
                if hasattr(action, "icon_color"):
                    action.icon_color = theme["text"]

    # --- view builders ---

    def build_intro_view():
        """
        Monta a home da aplicacao com acessos a continuar, novo jogo e visual.
        """
        theme = effective_theme()
        hero = ft.Container(
            width=panel_width(),
            padding=24 if is_narrow() else 30,
            border_radius=ft.BorderRadius.all(32),
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1),
                colors=[theme["panel_bg_alt"], theme["board_bg"]],
            ),
            shadow=make_shadow(),
            content=ft.Column(
                controls=[
                    ft.Container(
                        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                        border_radius=ft.BorderRadius.all(999),
                        bgcolor="#22FFFFFF",
                        content=ft.Text(
                            "Bem-vindo ao",
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color=theme["text"],
                        ),
                    ),
                    ft.Text(
                        "Paciência Online xTREME",
                        size=34 if is_narrow() else 40,
                        weight=ft.FontWeight.BOLD,
                        color=theme["text"],
                    ),
                    ft.Text(
'''Ajusta o visual do ecrã,
Retoma a partida atual,
Ou começa um jogo novo!''',
                        size=14,
                        color=theme["muted"],
                    ),
                    *([small_banner(intro_status, ft.Icons.INFO_OUTLINE)] if should_show_intro_status() else []),
                    ft.Row(
                        controls=[
                            action_chip(
                                "Continuar jogo em andamento",
                                ft.Icons.PLAY_ARROW,
                                continue_current_game,
                                tone="filled",
                                large=True,
                            ),
                            action_chip(
                                "        Começar nova partida      ",
                                ft.Icons.CASINO,
                                start_new_game_from_intro,
                                large=True,
                            ),
                        ],
                        wrap=True,
                        spacing=12,
                        run_spacing=12,
                    ),
                    ft.Container(
                        width=panel_width(),
                        content=compact_info(
                            "Visual e temas",
                            f"",
                            ft.Icons.PALETTE,
                            on_click=open_config_from_intro,
                            hint="Verso, paleta e fundo da mesa",
                        ),
                    ),
                ],
                spacing=16,
                tight=True,
            ),
        )
        return ft.Column(
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Column(
                    expand=True,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[hero],
                    spacing=16,
                )
            ],
        )

    def build_theme_studio_view():
        """
        Monta a view de criacao de um novo tema personalizado.
        """
        theme = effective_theme()
        palette = theme_studio_palette()
        preview_src = studio_image_bytes if studio_image_bytes else settings.card_back
        preview_scale = studio_zoom_slider.value or 1.0
        image_caption = (
            f"Imagem atual: {studio_image_name}"
            if studio_image_name
            else "Faz upload de uma imagem para gravar um verso novo no projeto."
        )

        board_slots = ft.Row(
            controls=[
                ft.Container(
                    width=64,
                    height=92,
                    border_radius=ft.BorderRadius.all(12),
                    bgcolor=palette["slot_bg"],
                    border=ft.Border.all(1.2, palette["slot_border"]),
                )
                for _ in range(3)
            ]
            + [
                ft.Container(
                    width=64,
                    height=92,
                    border_radius=ft.BorderRadius.all(12),
                    bgcolor=palette["panel_bg_alt"],
                    border=ft.Border.all(1.2, palette["slot_border"]),
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    content=ft.Image(
                        src=preview_src,
                        fit=ft.BoxFit.COVER,
                        scale=preview_scale,
                        width=64,
                        height=92,
                    ),
                )
            ],
            spacing=10,
            wrap=True,
            run_spacing=10,
        )

        live_preview = ft.Container(
            width=panel_width(),
            padding=20,
            border_radius=ft.BorderRadius.all(28),
            bgcolor=palette["page_bg"],
            border=ft.Border.all(1.5, palette["slot_border"]),
            shadow=make_shadow(),
            content=ft.Column(
                controls=[
                    ft.Container(
                        padding=ft.Padding.symmetric(horizontal=16, vertical=12),
                        border_radius=ft.BorderRadius.all(18),
                        bgcolor=palette["header_bg"],
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.AUTO_AWESOME, color=palette["accent"], size=18),
                                ft.Text(
                                    palette["label"],
                                    size=16,
                                    weight=ft.FontWeight.BOLD,
                                    color=palette["text"],
                                ),
                            ],
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ),
                    ft.Container(
                        padding=18,
                        border_radius=ft.BorderRadius.all(22),
                        bgcolor=palette["panel_bg"],
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Container(
                                            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                                            border_radius=ft.BorderRadius.all(999),
                                            bgcolor=palette["chip_bg"],
                                            content=ft.Text(
                                                "page",
                                                size=11,
                                                weight=ft.FontWeight.BOLD,
                                                color=palette["text"],
                                            ),
                                        ),
                                        ft.Container(
                                            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                                            border_radius=ft.BorderRadius.all(999),
                                            bgcolor=palette["accent"],
                                            content=ft.Text(
                                                "accent",
                                                size=11,
                                                weight=ft.FontWeight.BOLD,
                                                color=palette["page_bg"],
                                            ),
                                        ),
                                    ],
                                    spacing=10,
                                    wrap=True,
                                ),
                                ft.Container(
                                    padding=16,
                                    border_radius=ft.BorderRadius.all(20),
                                    bgcolor=palette["board_bg"],
                                    image=ft.DecorationImage(
                                        src=studio_board_bg_bytes,
                                        fit=ft.BoxFit.COVER,
                                        opacity=0.75,
                                    ) if studio_board_bg_bytes else None,
                                    content=ft.Column(
                                        controls=[
                                            ft.Text(
                                                "Preview do board",
                                                size=13,
                                                weight=ft.FontWeight.BOLD,
                                                color=palette["text"],
                                            ),
                                            board_slots,
                                        ],
                                        spacing=12,
                                    ),
                                ),
                            ],
                            spacing=14,
                        ),
                    ),
                ],
                spacing=14,
            ),
        )

        def _color_row(field, target_id):
            return ft.Row(
                controls=[
                    color_swatch_button(field, target_id),
                    ft.Container(expand=True, content=field),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )

        creation_form = ft.Column(
            controls=[
                studio_name_field,
                _color_row(studio_base_field, "base"),
                _color_row(studio_surface_field, "surface"),
                _color_row(studio_accent_field, "accent"),
                studio_light_text_switch,
            ],
            spacing=12,
        )

        # Board bg preview for the studio
        board_bg_caption = (
            f"Fundo: {studio_board_bg_name}"
            if studio_board_bg_name
            else "Sem fundo de tabuleiro (opcional)"
        )
        board_bg_preview_widget = ft.Container(
            width=120, height=76,
            border_radius=ft.BorderRadius.all(10),
            border=ft.Border.all(1.2, palette["slot_border"]),
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            bgcolor=palette["board_bg"],
            alignment=ft.Alignment(0, 0),
            content=ft.Image(
                src=studio_board_bg_bytes,
                fit=ft.BoxFit.COVER,
                width=120, height=76,
            ) if studio_board_bg_bytes else ft.Icon(
                ft.Icons.WALLPAPER, color=palette["muted"], size=28
            ),
        )

        image_controls = ft.Column(
            controls=[
                ft.Text(image_caption, size=13, color=theme["muted"]),
                ft.Text(f"Zoom do verso: {preview_scale:.2f}x", size=12, color=theme["text"]),
                studio_zoom_slider,
                action_chip("Escolher verso", ft.Icons.UPLOAD_FILE, choose_theme_studio_image),
                ft.Divider(height=1, color=theme["slot_border"]),
                ft.Text(board_bg_caption, size=13, color=theme["muted"]),
                board_bg_preview_widget,
                ft.Row(
                    controls=[
                        action_chip("Escolher fundo", ft.Icons.WALLPAPER, _choose_studio_board_bg),
                        *(
                            [action_chip("Remover fundo", ft.Icons.CLOSE, _clear_studio_board_bg)]
                            if studio_board_bg_bytes else []
                        ),
                    ],
                    wrap=True, spacing=10, run_spacing=10,
                ),
            ],
            spacing=12,
        )

        footer_actions = ft.Row(
            controls=[
                action_chip("Voltar", ft.Icons.ARROW_BACK, lambda e: navigate("/intro")),
                action_chip("Guardar tema", ft.Icons.SAVE, save_theme_studio, tone="filled"),
            ],
            wrap=True,
            spacing=12,
            run_spacing=12,
        )

        return ft.Column(
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Column(
                    spacing=16,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        small_banner(theme_studio_status, ft.Icons.BRUSH),
                        surface_card(
                            "Estudio de tema",
                            "Cria uma nova identidade visual e guarda-a no projeto.",
                            creation_form,
                            ft.Icons.PALETTE,
                        ),
                        surface_card(
                            "Verso da carta",
                            "A imagem fica persistente no projeto e o slider controla o zoom do verso.",
                            image_controls,
                            ft.Icons.STYLE,
                        ),
                        surface_card(
                            "Preview ao vivo",
                            "O resultado passa a estar disponivel depois na intro, configuracao e jogo.",
                            live_preview,
                            ft.Icons.AUTO_FIX_HIGH,
                        ),
                        ft.Container(width=panel_width(), content=footer_actions),
                    ],
                )
            ],
        )

    def build_manage_themes_view():
        """
        Monta a view de gestao dos temas personalizados ja existentes.
        """
        theme = effective_theme()
        custom_themes = {
            name: data
            for name, data in THEME_OPTIONS.items()
            if data.get("custom")
        }

        def _edit_swatch(theme_name, color_key, hex_val):
            return ft.GestureDetector(
                on_tap=lambda e, tn=theme_name, ck=color_key, hv=hex_val: _open_color_picker(("edit", tn, ck), hv),
                content=ft.Container(
                    width=36, height=36,
                    border_radius=ft.BorderRadius.all(8),
                    bgcolor=hex_val,
                    border=ft.Border.all(1.2, theme["slot_border"]),
                    tooltip=f"Editar cor ({color_key})",
                ),
            )

        theme_rows = []
        for tname, tdata in custom_themes.items():
            label_text = ft.Text(
                tdata["label"],
                size=15,
                weight=ft.FontWeight.BOLD,
                color=theme["text"],
                expand=True,
            )
            swatches = ft.Row(
                controls=[
                    _edit_swatch(tname, "base", tdata["board_bg"]),
                    _edit_swatch(tname, "surface", tdata["panel_bg"]),
                    _edit_swatch(tname, "accent", tdata["accent"]),
                ],
                spacing=8,
                tight=True,
            )
            row = ft.Container(
                padding=14,
                border_radius=ft.BorderRadius.all(18),
                bgcolor=theme["panel_bg_alt"],
                border=ft.Border.all(1.2, theme["slot_border"]),
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                label_text,
                                ft.IconButton(
                                    icon=ft.Icons.DRIVE_FILE_RENAME_OUTLINE,
                                    icon_color=theme["accent"],
                                    icon_size=20,
                                    tooltip="Renomear",
                                    on_click=lambda e, tn=tname: _open_rename_dialog(tn),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    icon_color=ft.Colors.RED_400,
                                    icon_size=20,
                                    tooltip="Eliminar",
                                    on_click=lambda e, tn=tname: _open_delete_confirm(tn),
                                ),
                            ],
                            spacing=4,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Text(
                            "Toca numa cor para editar",
                            size=11,
                            color=theme["muted"],
                        ),
                        swatches,
                    ],
                    spacing=8,
                    tight=True,
                ),
            )
            theme_rows.append(row)

        if not theme_rows:
            theme_rows.append(
                ft.Text(
                    "Ainda não criaste nenhum tema personalizado.",
                    size=13,
                    color=theme["muted"],
                )
            )

        # Append per-theme board bg editor row to each existing theme row
        for i, tname in enumerate(custom_themes):
            tback = BACK_OPTIONS.get(tname, {})
            t_board_bg = tback.get("board_bg")
            t_theme_data = custom_themes[tname]

            bg_preview = ft.Container(
                width=100, height=64,
                border_radius=ft.BorderRadius.all(10),
                border=ft.Border.all(1.2, theme["slot_border"]),
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                bgcolor=t_theme_data["board_bg"],
                alignment=ft.Alignment(0, 0),
                content=ft.Image(
                    src=t_board_bg, fit=ft.BoxFit.COVER, width=100, height=64
                ) if t_board_bg else ft.Icon(ft.Icons.WALLPAPER, color=theme["muted"], size=22),
            )
            bg_actions = ft.Row(
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.ADD_PHOTO_ALTERNATE,
                        icon_color=theme["accent"],
                        icon_size=20,
                        tooltip="Escolher fundo",
                        on_click=lambda e, tn=tname: _choose_board_bg_for_theme(tn),
                    ),
                    *(
                        [ft.IconButton(
                            icon=ft.Icons.CLOSE,
                            icon_color=ft.Colors.RED_400,
                            icon_size=20,
                            tooltip="Remover fundo",
                            on_click=lambda e, tn=tname: _clear_board_bg_for_theme(tn),
                        )]
                        if t_board_bg else []
                    ),
                ],
                spacing=0,
                tight=True,
            )
            bg_row = ft.Row(
                controls=[
                    bg_preview,
                    ft.Column(
                        controls=[
                            ft.Text("Fundo do tabuleiro", size=11, color=theme["muted"]),
                            bg_actions,
                        ],
                        spacing=4, tight=True,
                    ),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            # Append to the existing theme container's column
            if i < len(theme_rows):
                theme_rows[i].content.controls.append(ft.Divider(height=1, color=theme["slot_border"]))
                theme_rows[i].content.controls.append(bg_row)

        themes_content = ft.Column(controls=theme_rows, spacing=10, tight=True)

        actions = ft.Row(
            controls=[
                action_chip("Voltar", ft.Icons.ARROW_BACK, lambda e: navigate("/config")),
                action_chip("Criar novo tema", ft.Icons.ADD, open_theme_studio),
            ],
            wrap=True,
            spacing=12,
            run_spacing=12,
        )

        return ft.Column(
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Column(
                    spacing=16,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        surface_card(
                            "Temas personalizados",
                            "Edita cores, fundo, renomeia ou elimina os teus temas.",
                            themes_content,
                            ft.Icons.PALETTE,
                        ),
                        ft.Container(width=panel_width(), content=actions),
                    ],
                )
            ],
        )

    def build_card_back_tile(back_name, data):
        selected = back_name == draft_card_back_name
        theme = effective_theme()
        border_color = theme["accent"] if selected else theme["slot_border"]
        bg_color = theme["panel_bg_alt"]
        fit_lookup = {
            "cover": ft.BoxFit.COVER,
            "contain": ft.BoxFit.CONTAIN,
            "fill": ft.BoxFit.FILL,
        }
        preview = ft.Container(
            width=52,
            height=74,
            border_radius=ft.BorderRadius.all(8),
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            border=ft.Border.all(2, border_color),
            content=ft.Image(
                src=data["asset"],
                width=52,
                height=74,
                fit=fit_lookup.get(str(data.get("fit", "cover")).lower(), ft.BoxFit.COVER),
                scale=float(data.get("scale", 1.0)),
            ),
        )
        return ft.Container(
            data=back_name,
            on_click=select_draft_back,
            padding=14,
            border_radius=ft.BorderRadius.all(20),
            bgcolor=bg_color,
            border=ft.Border.all(2 if selected else 1.2, border_color),
            shadow=make_shadow() if selected else None,
            content=ft.Row(
                controls=[
                    preview,
                    ft.Column(
                        controls=[
                            ft.Text(
                                data["label"],
                                size=15,
                                weight=ft.FontWeight.BOLD,
                                color=theme["text"],
                            ),
                            ft.Text(
                                "Selecionado" if selected else "Toque para escolher",
                                size=11,
                                color=theme["accent"] if selected else theme["muted"],
                            ),
                        ],
                        spacing=4,
                        tight=True,
                        expand=True,
                    ),
                    ft.Icon(
                        ft.Icons.CHECK_CIRCLE if selected else ft.Icons.RADIO_BUTTON_UNCHECKED,
                        size=20,
                        color=theme["accent"] if selected else theme["muted"],
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def build_theme_tile(theme_name, data):
        selected = theme_name == draft_theme_name
        theme = effective_theme()
        border_color = theme["accent"] if selected else theme["slot_border"]
        swatch = ft.Container(
            width=52,
            height=74,
            border_radius=ft.BorderRadius.all(8),
            border=ft.Border.all(2, border_color),
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            content=ft.Column(
                controls=[
                    ft.Container(expand=2, bgcolor=data["board_bg"]),
                    ft.Container(expand=1, bgcolor=data["panel_bg_alt"]),
                    ft.Container(expand=1, bgcolor=data["accent"]),
                ],
                spacing=0,
                tight=True,
            ),
        )
        return ft.Container(
            data=theme_name,
            on_click=select_draft_theme,
            padding=14,
            border_radius=ft.BorderRadius.all(20),
            bgcolor=theme["panel_bg_alt"],
            border=ft.Border.all(2 if selected else 1.2, border_color),
            shadow=make_shadow() if selected else None,
            content=ft.Row(
                controls=[
                    swatch,
                    ft.Column(
                        controls=[
                            ft.Text(
                                data["label"],
                                size=15,
                                weight=ft.FontWeight.BOLD,
                                color=theme["text"],
                            ),
                            ft.Text(
                                "Selecionado" if selected else "Toque para escolher",
                                size=11,
                                color=theme["accent"] if selected else theme["muted"],
                            ),
                        ],
                        spacing=4,
                        tight=True,
                        expand=True,
                    ),
                    ft.Icon(
                        ft.Icons.CHECK_CIRCLE if selected else ft.Icons.RADIO_BUTTON_UNCHECKED,
                        size=20,
                        color=theme["accent"] if selected else theme["muted"],
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def build_preset_tile(preset):
        theme_data = THEME_OPTIONS[preset["theme"]]
        cur_theme = effective_theme()
        selected = (
            draft_card_back_name == preset["back"]
            and draft_theme_name == preset["theme"]
            and draft_board_bg_style == preset.get("board_bg_style", "theme_color")
            and draft_board_bg_target == preset.get("board_bg_target", "")
        )
        border_color = cur_theme["accent"] if selected else cur_theme["slot_border"]
        swatch = ft.Container(
            width=38,
            height=38,
            border_radius=ft.BorderRadius.all(10),
            border=ft.Border.all(1.5, border_color),
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            content=ft.Column(
                controls=[
                    ft.Container(expand=2, bgcolor=theme_data["board_bg"]),
                    ft.Container(expand=1, bgcolor=theme_data["accent"]),
                ],
                spacing=0,
                tight=True,
            ),
        )
        return ft.Container(
            data=preset,
            on_click=apply_preset,
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            border_radius=ft.BorderRadius.all(18),
            bgcolor=cur_theme["accent"] if selected else cur_theme["panel_bg_alt"],
            border=ft.Border.all(1.5, border_color),
            shadow=make_shadow() if selected else None,
            content=ft.Row(
                controls=[
                    swatch,
                    ft.Column(
                        controls=[
                            ft.Text(
                                preset["label"],
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color=cur_theme["page_bg"] if selected else cur_theme["text"],
                            ),
                            ft.Text(
                                "Carta + paleta + board",
                                size=11,
                                color=cur_theme["page_bg"] if selected else cur_theme["muted"],
                            ),
                        ],
                        spacing=2,
                        tight=True,
                        expand=True,
                    ),
                    ft.Icon(
                        preset["icon"],
                        size=18,
                        color=cur_theme["page_bg"] if selected else cur_theme["accent"],
                    ),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def build_config_view():
        """
        Monta o configurador visual com presets, versos e fundo do board.
        """
        theme = effective_theme()
        board_state = effective_board_state(use_draft=True)

        def set_theme_tab(tab_name):
            nonlocal config_theme_tab
            if config_theme_tab == tab_name:
                return
            config_theme_tab = tab_name
            render_route("/config")

        def reset_back_to_default(_e):
            nonlocal draft_card_back_name
            draft_card_back_name = draft_theme_name
            apply_visual_draft()

        def use_theme_board_color(_e=None):
            nonlocal draft_board_bg_style, draft_board_bg_target
            draft_board_bg_style = "theme_color"
            draft_board_bg_target = ""
            apply_visual_draft()

        def select_board_color(theme_name):
            nonlocal draft_board_bg_style, draft_board_bg_target
            draft_board_bg_style = "preset_color"
            draft_board_bg_target = theme_name
            apply_visual_draft()

        def select_board_image(back_name):
            nonlocal draft_board_bg_style, draft_board_bg_target
            draft_board_bg_style = "image"
            draft_board_bg_target = back_name
            apply_visual_draft()

        def config_tab_button(label, icon, tab_name):
            active = config_theme_tab == tab_name
            return ft.Container(
                on_click=lambda e, tn=tab_name: set_theme_tab(tn),
                padding=ft.Padding.symmetric(horizontal=16, vertical=10),
                border_radius=ft.BorderRadius.all(999),
                bgcolor=theme["accent"] if active else theme["panel_bg_alt"],
                border=ft.Border.all(1.2, theme["accent"] if active else theme["slot_border"]),
                content=ft.Row(
                    controls=[
                        ft.Icon(
                            icon,
                            size=16,
                            color=theme["page_bg"] if active else theme["accent"],
                        ),
                        ft.Text(
                            label,
                            size=13,
                            weight=ft.FontWeight.W_600,
                            color=theme["page_bg"] if active else theme["text"],
                        ),
                    ],
                    spacing=8,
                    tight=True,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )

        def build_board_color_tile(title, subtitle, color, selected, on_click):
            swatch = ft.Container(
                width=72,
                height=56,
                border_radius=ft.BorderRadius.all(12),
                bgcolor=color,
                border=ft.Border.all(1.5, theme["accent"] if selected else theme["slot_border"]),
            )
            return option_tile(
                title=title,
                subtitle=subtitle,
                selected=selected,
                icon=ft.Icons.PALETTE,
                on_click=on_click,
                media=swatch,
            )

        def build_board_image_tile(option):
            selected = (
                board_state["style"] == "image"
                and board_state["target"] == option["id"]
            )
            preview = ft.Container(
                height=92,
                border_radius=ft.BorderRadius.all(16),
                border=ft.Border.all(1.2, theme["accent"] if selected else theme["slot_border"]),
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                bgcolor=theme["panel_bg_alt"],
                image=ft.DecorationImage(
                    src=option["asset"],
                    fit=ft.BoxFit.COVER,
                    opacity=0.9,
                ),
            )
            return option_tile(
                title=option["label"],
                subtitle="Usa apenas a imagem do board",
                selected=selected,
                icon=ft.Icons.WALLPAPER,
                on_click=lambda e, oid=option["id"]: select_board_image(oid),
                media=preview,
            )

        default_back_available = draft_theme_name in BACK_OPTIONS
        back_mismatch = draft_card_back_name != draft_theme_name and default_back_available
        default_back_label = BACK_OPTIONS[draft_theme_name]["label"] if default_back_available else ""

        reset_chip = ft.Container(
            on_click=reset_back_to_default,
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            border_radius=ft.BorderRadius.all(999),
            bgcolor=theme["chip_bg"],
            border=ft.Border.all(1.2, theme["slot_border"]),
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.REFRESH, size=15, color=theme["accent"]),
                    ft.Text(
                        f"Restaurar verso padrao ({default_back_label})",
                        size=12,
                        color=theme["text"],
                    ),
                ],
                spacing=6,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ) if back_mismatch else None

        back_tiles = ft.Column(
            controls=(
                [reset_chip] if reset_chip else []
            ) + [
                build_card_back_tile(name, data)
                for name, data in BACK_OPTIONS.items()
            ],
            spacing=10,
            tight=True,
        )

        theme_tiles = ft.Column(
            controls=[
                build_theme_tile(name, data)
                for name, data in THEME_OPTIONS.items()
            ],
            spacing=10,
            tight=True,
        )

        preset_tiles = ft.Column(
            controls=[build_preset_tile(p) for p in available_visual_presets()],
            spacing=10,
            tight=True,
        )

        theme_tabs = ft.Row(
            controls=[
                config_tab_button("Mudar tudo", ft.Icons.AUTO_AWESOME, "combo"),
                config_tab_button("So paleta", ft.Icons.PALETTE, "palette"),
            ],
            wrap=True,
            spacing=10,
            run_spacing=10,
        )

        theme_block = ft.Column(
            controls=[
                theme_tabs,
                preset_tiles if config_theme_tab == "combo" else theme_tiles,
            ],
            spacing=14,
            tight=True,
        )

        current_theme_data = THEME_OPTIONS.get(draft_theme_name, THEME_OPTIONS["classic"])
        board_preview = ft.Container(
            width=panel_width(),
            padding=18,
            border_radius=ft.BorderRadius.all(24),
            bgcolor=board_state["color"],
            border=ft.Border.all(1.2, theme["slot_border"]),
            image=ft.DecorationImage(
                src=board_state["image"],
                fit=ft.BoxFit.COVER,
                opacity=0.82,
            ) if board_state["image"] else None,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.WALLPAPER, size=16, color=current_theme_data["accent"]),
                            ft.Text(
                                board_state["label"],
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color=current_theme_data["text"],
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Text(
                        board_state["description"],
                        size=12,
                        color=current_theme_data["muted"],
                    ),
                    ft.Row(
                        controls=[
                            ft.Container(
                                width=54,
                                height=78,
                                border_radius=ft.BorderRadius.all(12),
                                bgcolor=current_theme_data["slot_bg"],
                                border=ft.Border.all(1.2, current_theme_data["slot_border"]),
                            )
                            for _ in range(3)
                        ],
                        spacing=10,
                        wrap=True,
                    ),
                ],
                spacing=12,
                tight=True,
            ),
        )

        board_color_tiles = [
            build_board_color_tile(
                "Cor do tema atual",
                current_theme_data["label"],
                current_theme_data["board_bg"],
                board_state["style"] == "theme_color",
                use_theme_board_color,
            )
        ] + [
            build_board_color_tile(
                THEME_OPTIONS[name]["label"],
                "Cor padrao do board",
                THEME_OPTIONS[name]["board_bg"],
                board_state["style"] == "preset_color" and board_state["target"] == name,
                lambda e, tn=name: select_board_color(tn),
            )
            for name in available_board_color_themes()
        ]

        board_image_names = available_board_image_backs()
        board_images_content = (
            ft.Column(
                controls=[build_board_image_tile(option) for option in board_image_names],
                spacing=10,
                tight=True,
            )
            if board_image_names
            else ft.Text(
                "Ainda nao existem imagens de board personalizadas guardadas.",
                size=12,
                color=theme["muted"],
            )
        )

        board_content = ft.Column(
            controls=[
                board_preview,
                ft.Text("Cores do board", size=13, weight=ft.FontWeight.BOLD, color=theme["text"]),
                ft.Row(
                    controls=board_color_tiles,
                    wrap=True,
                    spacing=10,
                    run_spacing=10,
                ),
                ft.Text("Imagens do board", size=13, weight=ft.FontWeight.BOLD, color=theme["text"]),
                board_images_content,
            ],
            spacing=14,
            tight=True,
        )

        actions = ft.Row(
            controls=[
                action_chip(
                    "Voltar",
                    ft.Icons.ARROW_BACK,
                    lambda e: navigate(config_return_route),
                ),
                action_chip(
                    "Gerir temas",
                    ft.Icons.TUNE,
                    lambda e: navigate("/manage-themes"),
                ),
                action_chip(
                    "Concluir",
                    ft.Icons.CHECK,
                    apply_config,
                    tone="filled",
                ),
            ],
            wrap=True,
            spacing=12,
            run_spacing=12,
        )

        preview_label = (
            f"{BACK_OPTIONS[draft_card_back_name]['label']} + "
            f"{THEME_OPTIONS[draft_theme_name]['label']} + "
            f"{board_state['label']}"
        )
        return ft.Column(
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Column(
                    spacing=16,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        surface_card(
                            "Temas pre feitos",
                            "Muda tudo ou só a paleta",
                            theme_block,
                            ft.Icons.AUTO_AWESOME,
                        ),
                        surface_card(
                            "Costas das cartas",
                            "Escolhe o padrao que aparece no baralho.",
                            back_tiles,
                            ft.Icons.STYLE,
                        ),
                        surface_card(
                            "Fundo do board",
                            "Cor do board ou uma imagem de fundo.",
                            board_content,
                            ft.Icons.WALLPAPER,
                        ),
                        surface_card(
                            "Guardar escolha",
                            "Confirma as alteracoes.",
                            actions,
                            ft.Icons.CHECK_CIRCLE_OUTLINE,
                        ),
                    ],
                )
            ],
        )

    def safe_page(content):
        """
        Envolve uma view em `SafeArea` com padding padrao da app.

        Args:
            content:
                Conteudo principal da rota.

        Returns:
            Estrutura Flet pronta para ser adicionada a `page`.
        """
        return ft.SafeArea(
            content=ft.Container(
                padding=ft.Padding.only(bottom=12),
                content=content,
            ),
            maintain_bottom_view_padding=True,
            minimum_padding=ft.Padding.only(bottom=12),
            expand=True,
        )

    def build_game_view():
        """
        Constroi a rota principal do jogo.

        A view agrega:
        - cabecalho com score, tempo e acoes;
        - tabuleiro responsivo;
        - overlay de celebracao de vitoria.
        """
        bottom_padding = 8 if is_narrow() else 14
        side_padding = 6 if is_narrow() else page_padding()
        sync_victory_layout()
        header = ft.Column(
            spacing=6,
            tight=True,
            controls=[
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=2, vertical=2),
                    content=ft.Row(
                        controls=[
                            game_metric_chip(score_text, ft.Icons.STARS),
                            ft.Container(expand=True),
                            game_metric_chip(timer_text, ft.Icons.SCHEDULE),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
                ft.Row(
                    wrap=True,
                    spacing=8,
                    run_spacing=8,
                    controls=[
                        game_action_button(ft.Icons.HOME, "Intro", show_intro),
                        game_action_button(ft.Icons.SETTINGS, "Configuracao", open_config_from_game),
                        game_action_button(ft.Icons.CASINO, "Novo jogo", new_game),
                        game_action_button(ft.Icons.RESTART_ALT, "Reiniciar", restart),
                        game_action_button(ft.Icons.UNDO, "Desfazer", undo),
                        empty_game_action_slot(),
                        game_action_button(ft.Icons.DOWNLOAD, "Carregar", load_clicked),
                    ],
                ),
            ],
        )
        return ft.SafeArea(
            expand=True,
            maintain_bottom_view_padding=True,
            minimum_padding=ft.Padding.only(bottom=bottom_padding),
            content=ft.Stack(
                expand=True,
                controls=[
                    ft.Container(
                        expand=True,
                        padding=ft.Padding.only(
                            left=side_padding,
                            right=side_padding,
                            top=6,
                            bottom=bottom_padding,
                        ),
                        content=ft.Column(
                            expand=True,
                            spacing=6,
                            controls=[
                                header,
                                ft.Container(
                                    expand=True,
                                    content=board_frame,
                                ),
                            ],
                        ),
                    ),
                    victory_overlay,
                ],
            ),
        )

    def render_route(route: str):
        """
        Reconstroi a pagina conforme a rota interna selecionada.

        Args:
            route:
                Rota logica a apresentar.
        """
        page.controls.clear()
        page.scroll = None if route == "/game" else ft.ScrollMode.AUTO

        if route == "/manage-themes":
            page.appbar = ft.AppBar(
                leading=ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda e: navigate("/config"),
                ),
                title=ft.Text("Gerir temas"),
            )
            page.add(safe_page(build_manage_themes_view()))
        elif route == "/config":
            page.appbar = ft.AppBar(
                leading=ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda e: navigate(config_return_route),
                ),
                title=ft.Text("Visual da mesa"),
            )
            page.add(safe_page(build_config_view()))
        elif route == "/theme-studio":
            page.appbar = ft.AppBar(
                leading=ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda e: navigate("/intro"),
                ),
                title=ft.Text("Criar tema"),
            )
            page.add(safe_page(build_theme_studio_view()))
        elif route == "/game":
            page.appbar = None
            page.add(build_game_view())
            board.apply_visual_preferences(update=False)
            board.display_waste(update=False)
        else:
            page.appbar = None
            page.add(safe_page(build_intro_view()))

        apply_page_theme()
        page.update()

    refresh_hud()

    async def run_timer():
        """
        Atualiza o cronometro da partida em segundo plano.

        O contador pausa automaticamente quando o tabuleiro entra em estado
        de vitoria.
        """
        while True:
            await asyncio.sleep(1)
            if board._game_won:
                continue
            board.elapsed_seconds += 1
            timer_text.value = f"Tempo: {board.format_elapsed()}"
            try:
                timer_text.update()
            except Exception:
                pass

    def handle_resize(e):
        """
        Recalcula layout, tabuleiro e overlays quando a janela muda.
        """
        page.padding = page_padding()
        sync_victory_layout()
        board.apply_visual_preferences(update=False)
        board.display_waste(update=False)
        render_route(page.route or "/intro")

    async def lock_portrait_mode():
        """
        Tenta fixar a app em orientacao vertical no dispositivo movel.
        """
        try:
            await page.set_allowed_device_orientations([ft.DeviceOrientation.PORTRAIT_UP])
        except Exception:
            pass

    page.on_resize = handle_resize
    page.on_close = handle_close
    page.run_task(run_timer)
    page.run_task(lock_portrait_mode)
    navigate("/intro")
    page.run_task(auto_load_on_start)


if __name__ == "__main__":
    ft.run(main, assets_dir=str(Path(__file__).resolve().parent / "assets"))
