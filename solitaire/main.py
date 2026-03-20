import asyncio
import json
from pathlib import Path

import flet as ft

from gameboard_original import GameBoard
from settings import BACK_OPTIONS, GAME_MODES, Settings, THEME_OPTIONS
from storage import GameStorage

LOCAL_GAME_STATE_KEY = "solitaire.game_state.v2"


def main(page: ft.Page):
    settings = Settings()
    storage = GameStorage()
    selected_game_mode = settings.game_mode
    config_return_route = "/intro"

    page.title = "Solitaire Atelier"
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO

    score_text = ft.Text(size=14, weight=ft.FontWeight.BOLD)
    timer_text = ft.Text(size=14, weight=ft.FontWeight.BOLD)
    passes_text = ft.Text(size=14, weight=ft.FontWeight.BOLD)
    status_text = ft.Text(size=14)

    intro_title = ft.Text("Solitaire Atelier", size=28, weight=ft.FontWeight.BOLD)
    intro_subtitle = ft.Text(
        "Escolhe o modo da proxima partida e entra no jogo sem mexer na gameplay.",
        size=13,
    )
    intro_mode_note = ft.Text(
        "Waste fixo em 1 carta. O game mode altera apenas a pontuacao da nova partida.",
        size=13,
    )
    intro_mode_description = ft.Text(size=13)
    intro_theme_summary = ft.Text(size=13)
    intro_status = ft.Text(size=13)

    config_title = ft.Text("Configuracao", size=24, weight=ft.FontWeight.BOLD)
    config_subtitle = ft.Text(
        "Aqui mudas apenas o visual da janela e o back das cartas.",
        size=13,
    )

    back_group = ft.RadioGroup(
        content=ft.Column(
            controls=[
                ft.Radio(value=name, label=data["label"])
                for name, data in BACK_OPTIONS.items()
            ],
            spacing=6,
            tight=True,
        )
    )
    theme_group = ft.RadioGroup(
        content=ft.Column(
            controls=[
                ft.Radio(value=name, label=data["label"])
                for name, data in THEME_OPTIONS.items()
            ],
            spacing=6,
            tight=True,
        )
    )
    mode_group = ft.RadioGroup(
        content=ft.Column(
            controls=[
                ft.Radio(value=name, label=data["label"])
                for name, data in GAME_MODES.items()
            ],
            spacing=6,
            tight=True,
        )
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

    board_frame = ft.Container(content=board, bgcolor=settings.theme["board_bg"], padding=12)

    def sync_intro_controls():
        intro_mode = selected_game_mode if selected_game_mode in GAME_MODES else "classic"
        mode_group.value = intro_mode
        intro_mode_description.value = GAME_MODES[intro_mode]["description"]
        intro_theme_summary.value = (
            f"Tema: {THEME_OPTIONS[settings.theme_name]['label']} | "
            f"Back: {BACK_OPTIONS[settings.card_back_name]['label']}"
        )
        intro_status.value = board.status_message

    def sync_config_controls():
        back_group.value = settings.card_back_name
        theme_group.value = settings.theme_name

    def navigate(route: str):
        page.route = route
        render_route(route)

    def show_intro(e=None):
        navigate("/intro")

    def show_game(e=None):
        navigate("/game")

    def open_config_from_intro(e=None):
        nonlocal config_return_route
        config_return_route = "/intro"
        navigate("/config")

    def open_config_from_game(e=None):
        nonlocal config_return_route
        config_return_route = "/game"
        navigate("/config")

    def handle_mode_change(e):
        nonlocal selected_game_mode
        if mode_group.value in GAME_MODES:
            selected_game_mode = mode_group.value
        sync_intro_controls()
        page.update()

    mode_group.on_change = handle_mode_change

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
        nonlocal settings, selected_game_mode
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
            sync_intro_controls()
            if page.route == "/intro":
                render_route("/intro")
            return False

        board.restore_state(snapshot, clear_history=True, set_initial=True, announce=False)
        settings = board.settings
        selected_game_mode = settings.game_mode
        sync_intro_controls()
        sync_config_controls()
        apply_page_theme()
        page.update()
        board.set_status("Partida carregada.")
        return True

    async def load_game_from_intro():
        loaded = await load_game()
        if loaded:
            show_game()

    def start_new_game_from_intro(e):
        nonlocal settings
        settings.game_mode = (
            selected_game_mode if selected_game_mode in GAME_MODES else "classic"
        )
        board.settings = settings
        board.start_new_game()
        sync_intro_controls()
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

    def load_from_intro_clicked(e):
        page.run_task(load_game_from_intro)

    def apply_config():
        settings.card_back_name = back_group.value
        settings.theme_name = theme_group.value
        board.settings = settings
        board.apply_visual_preferences(update=True)
        sync_intro_controls()
        apply_page_theme()
        navigate(config_return_route)
        board.set_status("Visual atualizado.")

    intro_panel = ft.Container(
        width=560,
        padding=24,
        content=ft.Column(
            controls=[
                intro_title,
                intro_subtitle,
                ft.Divider(),
                ft.Text("Game mode", size=18, weight=ft.FontWeight.BOLD),
                intro_mode_note,
                mode_group,
                intro_mode_description,
                ft.Divider(),
                ft.Text("Visual", size=18, weight=ft.FontWeight.BOLD),
                intro_theme_summary,
                ft.OutlinedButton("Tema e back", on_click=open_config_from_intro),
                ft.Divider(),
                intro_status,
                ft.Row(
                    controls=[
                        ft.FilledButton(
                            "Continuar jogo atual", on_click=continue_current_game
                        ),
                        ft.OutlinedButton(
                            "Carregar jogo guardado", on_click=load_from_intro_clicked
                        ),
                    ],
                    wrap=True,
                    spacing=12,
                ),
                ft.FilledButton("Comecar novo jogo", on_click=start_new_game_from_intro),
            ],
            spacing=12,
            tight=True,
        ),
    )

    config_panel = ft.Container(
        padding=20,
        content=ft.Column(
            controls=[
                config_title,
                config_subtitle,
                ft.Divider(),
                ft.Text("Modo principal ativo: 1 carta no waste.", size=14),
                ft.Divider(),
                ft.Text("Back das cartas", size=18, weight=ft.FontWeight.BOLD),
                back_group,
                ft.Divider(),
                ft.Text("Tema", size=18, weight=ft.FontWeight.BOLD),
                theme_group,
                ft.Divider(),
                ft.Row(
                    controls=[
                        ft.OutlinedButton("Voltar", on_click=lambda e: navigate(config_return_route)),
                        ft.FilledButton("Aplicar", on_click=lambda e: apply_config()),
                    ],
                    spacing=12,
                ),
            ],
            spacing=12,
            tight=True,
        ),
    )

    def apply_page_theme():
        theme = settings.theme
        page.bgcolor = theme["page_bg"]
        board_frame.bgcolor = theme["board_bg"]
        intro_panel.bgcolor = theme["panel_bg"]
        config_panel.bgcolor = theme["panel_bg"]

        intro_title.color = theme["text"]
        intro_subtitle.color = theme["muted"]
        intro_mode_note.color = theme["muted"]
        intro_mode_description.color = theme["muted"]
        intro_theme_summary.color = theme["text"]
        intro_status.color = theme["text"]

        config_title.color = theme["text"]
        config_subtitle.color = theme["muted"]
        status_text.color = theme["text"]

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

    def render_route(route: str):
        page.controls.clear()

        if route == "/config":
            sync_config_controls()
            page.appbar = ft.AppBar(
                leading=ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda e: navigate(config_return_route),
                ),
                title=ft.Text("Configuracao"),
            )
            page.add(config_panel)
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
            sync_intro_controls()
            page.appbar = None
            page.add(
                ft.Column(
                    expand=True,
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[intro_panel],
                )
            )

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

    page.run_task(run_timer)
    navigate("/intro")


if __name__ == "__main__":
    ft.run(main, assets_dir=str(Path(__file__).resolve().parent / "assets"))
