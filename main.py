import asyncio
import json
from pathlib import Path

import flet as ft

from solitaire.custom_theme_store import build_theme_palette, save_custom_theme_bundle
from solitaire.gameboard_original import GameBoard
from solitaire.settings import (
    BACK_OPTIONS,
    GAME_MODES,
    Settings,
    THEME_OPTIONS,
    refresh_custom_theme_registry,
)
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
    refresh_custom_theme_registry()
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
    status_text = ft.Text(size=14, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS, expand=True)
    intro_status = ft.Text(size=13)
    theme_studio_status = ft.Text(size=13)

    studio_image_bytes = None
    studio_image_name = None

    studio_name_field = ft.TextField(
        label="Nome do tema",
        value="Tema Atelier",
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
            label=studio_name_field.value or "Tema Atelier",
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
                    "icon": ft.Icons.AUTO_FIX_HIGH,
                }
            )
        return presets

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

    def action_chip(label, icon, on_click, tone="soft"):
        theme = effective_theme()
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

    board = GameBoard(page=page, settings=settings, on_win=on_win, on_change=refresh_hud)
    board.setup()

    board_frame = ft.Container(
        content=board,
        bgcolor=effective_theme()["board_bg"],
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
        board.settings = settings
        board.apply_visual_preferences(update=False)
        board.display_waste(update=False)
        if update and board.can_update():
            board.update()

    async def autosave_current_state():
        snapshot = board.capture_state(include_initial=True)
        try:
            preferences = ft.SharedPreferences()
            await preferences.set(LOCAL_GAME_STATE_KEY, json.dumps(snapshot))
        except Exception:
            pass
        try:
            storage.save_game(snapshot)
        except Exception:
            pass

    def autosave_current_state_sync():
        snapshot = board.capture_state(include_initial=True)
        try:
            storage.save_game(snapshot)
        except Exception:
            pass
        page.run_task(autosave_current_state)

    def navigate(route: str):
        current_route = page.route or "/intro"
        if current_route == "/game" and route == "/intro":
            autosave_current_state_sync()
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

    def open_theme_studio(e=None):
        nonlocal studio_image_bytes, studio_image_name
        current_theme = settings.theme
        studio_name_field.value = f"{current_theme['label']} Remix"
        studio_base_field.value = current_theme["board_bg"]
        studio_surface_field.value = current_theme["panel_bg"]
        studio_accent_field.value = current_theme["accent"]
        studio_light_text_switch.value = is_light_color(current_theme["text"])
        studio_zoom_slider.value = 1.0
        studio_image_bytes = None
        studio_image_name = None
        theme_studio_status.value = "Cria uma paleta, faz upload do verso e guarda o tema no projeto."
        navigate("/theme-studio")

    def preview_theme_studio(e=None):
        theme_studio_status.value = "Preview atualizado."
        render_route("/theme-studio")

    async def pick_theme_studio_image_async():
        nonlocal studio_image_bytes, studio_image_name
        files = await file_picker.pick_files(
            dialog_title="Escolhe a imagem do verso da carta",
            file_type=ft.FilePickerFileType.IMAGE,
            allow_multiple=False,
            with_data=True,
        )
        if not files:
            return

        selected_file = files[0]
        selected_bytes = selected_file.bytes
        if selected_bytes is None and selected_file.path:
            selected_bytes = Path(selected_file.path).read_bytes()
        if not selected_bytes:
            theme_studio_status.value = "Nao foi possivel ler a imagem escolhida."
            render_route("/theme-studio")
            return

        studio_image_bytes = selected_bytes
        studio_image_name = selected_file.name
        theme_studio_status.value = f"Imagem '{studio_image_name}' pronta para o tema."
        render_route("/theme-studio")

    def choose_theme_studio_image(e=None):
        page.run_task(pick_theme_studio_image_async)

    studio_zoom_slider.on_change = preview_theme_studio
    studio_light_text_switch.on_change = preview_theme_studio

    def save_theme_studio(e=None):
        nonlocal draft_card_back_name, draft_theme_name
        name_value = (studio_name_field.value or "").strip()
        if len(name_value) < 3:
            theme_studio_status.value = "Dá um nome com pelo menos 3 caracteres ao tema."
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
            )
        except ValueError as exc:
            theme_studio_status.value = str(exc)
            render_route("/theme-studio")
            return

        refresh_custom_theme_registry()
        draft_card_back_name = created["back_name"]
        draft_theme_name = created["theme_name"]
        apply_visual_draft(refresh_route=False)
        theme_studio_status.value = f"Tema '{created['theme']['label']}' criado e aplicado."
        navigate("/intro")
        board.set_status(f"Tema '{created['theme']['label']}' criado.")

    def select_mode(e):
        nonlocal selected_game_mode
        if e.control.data in GAME_MODES:
            selected_game_mode = e.control.data
            navigate("/intro")

    def apply_visual_draft(refresh_route=True):
        settings.card_back_name = draft_card_back_name
        settings.theme_name = draft_theme_name
        board.settings = settings
        sync_board_visuals(update=False)
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
        nonlocal draft_card_back_name, draft_theme_name
        preset = e.control.data
        draft_card_back_name = preset["back"]
        draft_theme_name = preset["theme"]
        apply_visual_draft()

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
        sync_board_visuals(update=False)
        render_route(page.route or "/intro")
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
        sync_board_visuals(update=False)
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

    def handle_close(e):
        current_route = page.route or "/intro"
        if current_route == "/game":
            autosave_current_state_sync()

    def apply_config(e=None):
        apply_visual_draft(refresh_route=False)
        navigate(config_return_route)
        board.set_status("Visual atualizado.")

    def apply_page_theme():
        theme = effective_theme()
        page.padding = 0 if page.route == "/game" else page_padding()
        page.bgcolor = theme["page_bg"]
        board_frame.bgcolor = theme["board_bg"]
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
                        "Paciência Online Extreme",
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
                            action_chip(
                                "Criar tema",
                                ft.Icons.BRUSH,
                                open_theme_studio,
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

    def build_theme_studio_view():
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

        creation_form = ft.Column(
            controls=[
                studio_name_field,
                ft.ResponsiveRow(
                    controls=[
                        ft.Container(col={"xs": 12, "md": 4}, content=studio_base_field),
                        ft.Container(col={"xs": 12, "md": 4}, content=studio_surface_field),
                        ft.Container(col={"xs": 12, "md": 4}, content=studio_accent_field),
                    ],
                    run_spacing=12,
                ),
                studio_light_text_switch,
            ],
            spacing=12,
        )

        image_controls = ft.Column(
            controls=[
                ft.Text(image_caption, size=13, color=theme["muted"]),
                ft.Text(
                    f"Zoom do verso: {preview_scale:.2f}x",
                    size=12,
                    color=theme["text"],
                ),
                studio_zoom_slider,
                ft.Row(
                    controls=[
                        action_chip("Escolher imagem", ft.Icons.UPLOAD_FILE, choose_theme_studio_image),
                        action_chip("Atualizar preview", ft.Icons.VISIBILITY, preview_theme_studio),
                    ],
                    wrap=True,
                    spacing=12,
                    run_spacing=12,
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
        theme = effective_theme()

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
            controls=[build_preset_tile(p) for p in available_visual_presets()],
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

    def build_game_view():
        bottom_padding = 8 if is_narrow() else 14
        side_padding = 6 if is_narrow() else page_padding()
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
                        game_action_button(ft.Icons.DOWNLOAD, "Carregar", load_clicked),
                    ],
                ),
            ],
        )
        return ft.SafeArea(
            expand=True,
            maintain_bottom_view_padding=True,
            minimum_padding=ft.Padding.only(bottom=bottom_padding),
            content=ft.Container(
                expand=True,
                padding=ft.Padding.only(left=side_padding, right=side_padding, top=6, bottom=bottom_padding),
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
        )

    def render_route(route: str):
        page.controls.clear()
        page.scroll = ft.ScrollMode.HIDDEN if route == "/game" else ft.ScrollMode.AUTO

        if route == "/config":
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
    page.on_close = handle_close
    page.run_task(run_timer)
    navigate("/intro")
    page.run_task(auto_load_on_start)


if __name__ == "__main__":
    ft.run(main, assets_dir=str(Path(__file__).resolve().parent / "assets"))
