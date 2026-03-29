import asyncio
import json
from pathlib import Path

import flet as ft

from solitaire.gameboard_original import GameBoard
from solitaire.settings import BACK_OPTIONS, GAME_MODES, Settings, THEME_OPTIONS
from solitaire.storage import GameStorage

LOCAL_GAME_STATE_KEY = "solitaire.game_state.v2"

# Presets that pair a card back with its matching table theme
VISUAL_PRESETS = [
    {"label": "Classic Green", "back": "classic", "theme": "classic", "icon": ft.Icons.GRASS},
    {"label": "Forest Moss",   "back": "forest",  "theme": "forest",  "icon": ft.Icons.PARK},
    {"label": "Ocean Blue",    "back": "ocean",   "theme": "ocean",   "icon": ft.Icons.WAVES},
    {"label": "Sunrise Copper","back": "sunrise", "theme": "sunrise", "icon": ft.Icons.WB_SUNNY},
]


def main(page: ft.Page):
    settings = Settings()
    storage = GameStorage()
    selected_game_mode = settings.game_mode
    config_return_route = "/intro"
    draft_card_back_name = settings.card_back_name
    draft_theme_name = settings.theme_name

    page.title = "Paciência"
    page.scroll = ft.ScrollMode.AUTO

    score_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
    timer_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
    passes_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
    status_text = ft.Text(size=14)
    intro_status = ft.Text(size=13)

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

    # --- widget helpers ---

    def compact_info(label, value, icon, on_click=None, hint=None):
        theme = settings.theme
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

    def action_chip(label, icon, on_click, tone="soft"):
        theme = settings.theme
        filled = tone == "filled"
        return ft.Container(
            on_click=on_click,
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
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
                        size=18,
                        color=theme["page_bg"] if filled else theme["accent"],
                    ),
                    ft.Text(
                        label,
                        size=14,
                        weight=ft.FontWeight.W_600,
                        color=theme["page_bg"] if filled else theme["text"],
                    ),
                ],
                spacing=8,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def small_banner(text_control, icon):
        theme = settings.theme
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

    def surface_card(title, subtitle, content, icon):
        theme = settings.theme
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
        theme = settings.theme
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

    def on_win():
        dialog = ft.AlertDialog(
            title=ft.Text("Vitoria!"),
            content=ft.Text("Completaste as quatro fundacoes."),
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    def refresh_hud(autosave=False):
        score_text.value = f"Score: {board.score}"
        timer_text.value = f"Tempo: {board.format_elapsed()}"
        passes_text.value = f"Passes: {board.format_passes()}"
        status_text.value = board.status_message
        intro_status.value = board.status_message
        try:
            score_text.update()
            timer_text.update()
            passes_text.update()
            status_text.update()
            intro_status.update()
        except Exception:
            pass
        if autosave:
            page.run_task(save_game)

    board = GameBoard(page=page, settings=settings, on_win=on_win, on_change=refresh_hud)
    board.setup()

    board_frame = ft.Container(content=board, bgcolor=settings.theme["board_bg"], padding=12)

    def navigate(route: str):
        page.route = route
        render_route(route)

    def show_intro(e=None):
        navigate("/intro")

    def show_game(e=None):
        navigate("/game")

    def open_config_from_intro(e=None):
        nonlocal config_return_route, draft_card_back_name, draft_theme_name
        config_return_route = "/intro"
        draft_card_back_name = settings.card_back_name
        draft_theme_name = settings.theme_name
        navigate("/config")

    def open_config_from_game(e=None):
        nonlocal config_return_route, draft_card_back_name, draft_theme_name
        config_return_route = "/game"
        draft_card_back_name = settings.card_back_name
        draft_theme_name = settings.theme_name
        navigate("/config")

    def open_mode_picker(e=None):
        navigate("/mode")

    def select_mode(e):
        nonlocal selected_game_mode
        if e.control.data in GAME_MODES:
            selected_game_mode = e.control.data
            navigate("/intro")

    def select_draft_back(e):
        nonlocal draft_card_back_name
        if e.control.data in BACK_OPTIONS:
            draft_card_back_name = e.control.data
            render_route("/config")

    def select_draft_theme(e):
        nonlocal draft_theme_name
        if e.control.data in THEME_OPTIONS:
            draft_theme_name = e.control.data
            render_route("/config")

    def apply_preset(e):
        nonlocal draft_card_back_name, draft_theme_name
        preset = e.control.data
        draft_card_back_name = preset["back"]
        draft_theme_name = preset["theme"]
        render_route("/config")

    async def save_game():
        snapshot = board.capture_state(include_initial=True)
        local_error = None
        duck_error = None
        try:
            preferences = ft.SharedPreferences()
            await preferences.set(LOCAL_GAME_STATE_KEY, json.dumps(snapshot))
        except Exception as exc:
            local_error = str(exc)
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
        nonlocal settings, selected_game_mode, draft_card_back_name, draft_theme_name
        snapshot = None
        try:
            snapshot = storage.load_game()
        except Exception:
            snapshot = None
        if snapshot is None:
            try:
                preferences = ft.SharedPreferences()
                raw_state = await preferences.get(LOCAL_GAME_STATE_KEY)
                if raw_state:
                    snapshot = json.loads(raw_state)
            except Exception:
                snapshot = None
        if snapshot is None:
            board.set_status("Nao existe uma partida guardada.")
            if page.route == "/intro":
                render_route("/intro")
            return False

        board.restore_state(snapshot, clear_history=True, set_initial=True, announce=False)
        settings = board.settings
        selected_game_mode = settings.game_mode
        draft_card_back_name = settings.card_back_name
        draft_theme_name = settings.theme_name
        apply_page_theme()
        page.update()
        board.set_status("Partida carregada.")
        return True

    async def load_game_from_intro():
        loaded = await load_game()
        if loaded:
            show_game()

    async def auto_load_on_start():
        nonlocal settings, selected_game_mode, draft_card_back_name, draft_theme_name
        snapshot = None
        try:
            snapshot = storage.load_game()
        except Exception:
            pass
        if snapshot is None:
            try:
                preferences = ft.SharedPreferences()
                raw_state = await preferences.get(LOCAL_GAME_STATE_KEY)
                if raw_state:
                    snapshot = json.loads(raw_state)
            except Exception:
                pass
        if snapshot is None:
            return
        board.restore_state(snapshot, clear_history=True, set_initial=True, announce=False)
        settings = board.settings
        selected_game_mode = settings.game_mode
        draft_card_back_name = settings.card_back_name
        draft_theme_name = settings.theme_name
        apply_page_theme()
        board.set_status("Partida anterior carregada.")
        render_route(page.route or "/intro")

    def start_new_game_from_intro(e):
        nonlocal settings
        settings.game_mode = (
            selected_game_mode if selected_game_mode in GAME_MODES else "classic"
        )
        board.settings = settings
        board.start_new_game()
        show_game()

    def continue_current_game(e):
        show_game()

    def new_game(e):
        board.start_new_game()

    def restart(e):
        board.restart_game()

    def undo(e):
        board.undo_move()

    def save_clicked(e):
        page.run_task(save_game)

    def load_clicked(e):
        page.run_task(load_game)

    def apply_config(e=None):
        settings.card_back_name = draft_card_back_name
        settings.theme_name = draft_theme_name
        board.settings = settings
        board.apply_visual_preferences(update=True)
        apply_page_theme()
        navigate(config_return_route)
        board.set_status("Visual atualizado.")

    def apply_page_theme():
        theme = settings.theme
        page.padding = page_padding()
        page.bgcolor = theme["page_bg"]
        board_frame.bgcolor = theme["board_bg"]
        status_text.color = theme["text"]
        intro_status.color = theme["text"]

        for text in (score_text, timer_text, passes_text):
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
        theme = settings.theme
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
                            "Jogo rápido, pensado para telemóvel",
                            size=11,
                            color=theme["text"],
                        ),
                    ),
                    ft.Text(
                        "Paciência",
                        size=34 if is_narrow() else 40,
                        weight=ft.FontWeight.BOLD,
                        color=theme["text"],
                    ),
                    ft.Text(
                        "Escolhe o modo da próxima partida, ajusta o visual e entra logo na mesa.",
                        size=14,
                        color=theme["muted"],
                    ),
                    small_banner(intro_status, ft.Icons.INFO_OUTLINE),
                    ft.Row(
                        controls=[
                            compact_info(
                                "Modo",
                                GAME_MODES[selected_game_mode]["label"],
                                ft.Icons.SPORTS_ESPORTS,
                                on_click=open_mode_picker,
                                hint="Toque para alterar",
                            ),
                            compact_info(
                                "Visual",
                                THEME_OPTIONS[settings.theme_name]["label"],
                                ft.Icons.PALETTE,
                                on_click=open_config_from_intro,
                                hint="Toque para personalizar",
                            ),
                        ],
                        wrap=True,
                        spacing=12,
                        run_spacing=12,
                    ),
                    ft.Row(
                        controls=[
                            action_chip(
                                "Continuar",
                                ft.Icons.PLAY_ARROW,
                                continue_current_game,
                                tone="filled",
                            ),
                            action_chip(
                                "Nova partida",
                                ft.Icons.CASINO,
                                start_new_game_from_intro,
                            ),
                        ],
                        wrap=True,
                        spacing=12,
                        run_spacing=12,
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

    def build_mode_view():
        mode_cards = ft.Row(
            controls=[
                option_tile(
                    GAME_MODES["classic"]["label"],
                    GAME_MODES["classic"]["description"],
                    selected_game_mode == "classic",
                    ft.Icons.STARS,
                    select_mode,
                    data="classic",
                ),
                option_tile(
                    GAME_MODES["vegas"]["label"],
                    GAME_MODES["vegas"]["description"],
                    selected_game_mode == "vegas",
                    ft.Icons.PAID,
                    select_mode,
                    data="vegas",
                ),
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
                            "Modo da partida",
                            "Escolhe como queres contar os pontos na próxima partida.",
                            mode_cards,
                            ft.Icons.SPORTS_ESPORTS,
                        ),
                        ft.Container(
                            width=panel_width(),
                            content=ft.Row(
                                controls=[
                                    action_chip(
                                        "Voltar",
                                        ft.Icons.ARROW_BACK,
                                        lambda e: navigate("/intro"),
                                    ),
                                ],
                                wrap=True,
                                spacing=12,
                                run_spacing=12,
                            ),
                        ),
                    ],
                )
            ],
        )

    def build_card_back_tile(back_name, data):
        selected = back_name == draft_card_back_name
        theme = settings.theme
        border_color = theme["accent"] if selected else theme["slot_border"]
        bg_color = theme["panel_bg_alt"]
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
                fit=ft.BoxFit.COVER,
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
        theme = settings.theme
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
        cur_theme = settings.theme
        selected = (
            draft_card_back_name == preset["back"]
            and draft_theme_name == preset["theme"]
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
                                "Carta + Mesa combinados",
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
        theme = settings.theme

        back_tiles = ft.Column(
            controls=[
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
            controls=[build_preset_tile(p) for p in VISUAL_PRESETS],
            spacing=10,
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
                    "Aplicar visual",
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
            f"{THEME_OPTIONS[draft_theme_name]['label']}"
        )
        preview_bar = ft.Container(
            width=panel_width(),
            padding=14,
            border_radius=ft.BorderRadius.all(20),
            bgcolor=theme["panel_bg_alt"],
            border=ft.Border.all(1.2, theme["slot_border"]),
            content=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.TUNE, size=16, color=theme["accent"]),
                    ft.Text(
                        f"A pré-visualizar: {preview_label}",
                        size=13,
                        color=theme["text"],
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        return ft.Column(
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Column(
                    spacing=16,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        preview_bar,
                        surface_card(
                            "Combinações prontas",
                            "Aplica carta e mesa de uma vez.",
                            preset_tiles,
                            ft.Icons.AUTO_AWESOME,
                        ),
                        surface_card(
                            "Costas das cartas",
                            "Escolhe o padrão que aparece no baralho.",
                            back_tiles,
                            ft.Icons.STYLE,
                        ),
                        surface_card(
                            "Tema da mesa",
                            "Muda a paleta de cores sem alterar o jogo.",
                            theme_tiles,
                            ft.Icons.PALETTE,
                        ),
                        surface_card(
                            "Guardar escolha",
                            "Confirma as alterações.",
                            actions,
                            ft.Icons.CHECK_CIRCLE_OUTLINE,
                        ),
                    ],
                )
            ],
        )

    def safe_page(content):
        return ft.SafeArea(
            content=ft.Container(
                padding=ft.Padding.only(bottom=12),
                content=content,
            ),
            maintain_bottom_view_padding=True,
            minimum_padding=ft.Padding.only(bottom=12),
            expand=True,
        )

    def render_route(route: str):
        page.controls.clear()

        if route == "/config":
            page.appbar = ft.AppBar(
                leading=ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda e: navigate(config_return_route),
                ),
                title=ft.Text("Visual da mesa"),
            )
            page.add(safe_page(build_config_view()))
        elif route == "/mode":
            page.appbar = ft.AppBar(
                leading=ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda e: navigate("/intro"),
                ),
                title=ft.Text("Modo da partida"),
            )
            page.add(safe_page(build_mode_view()))
        elif route == "/game":
            page.appbar = ft.AppBar(
                title=ft.Text("Solitaire Atelier"),
                actions=[
                    score_text,
                    timer_text,
                    passes_text,
                    ft.IconButton(
                        icon=ft.Icons.HOME,
                        tooltip="Intro",
                        on_click=show_intro,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.SETTINGS,
                        tooltip="Configuracao",
                        on_click=open_config_from_game,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.CASINO,
                        tooltip="Novo jogo",
                        on_click=new_game,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.RESTART_ALT,
                        tooltip="Reiniciar",
                        on_click=restart,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.UNDO,
                        tooltip="Desfazer",
                        on_click=undo,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.SAVE_ALT,
                        tooltip="Guardar",
                        on_click=save_clicked,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DOWNLOAD,
                        tooltip="Carregar",
                        on_click=load_clicked,
                    ),
                ],
            )
            page.add(board_frame, status_text)
        else:
            page.appbar = None
            page.add(safe_page(build_intro_view()))

        apply_page_theme()
        page.update()

    refresh_hud()

    async def run_timer():
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
        page.padding = page_padding()
        board.apply_visual_preferences(update=False)
        board.display_waste(update=False)
        render_route(page.route or "/intro")

    page.on_resize = handle_resize
    page.run_task(run_timer)
    navigate("/intro")
    page.run_task(auto_load_on_start)


if __name__ == "__main__":
    ft.run(main, assets_dir=str(Path(__file__).resolve().parent / "assets"))
