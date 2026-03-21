import asyncio
import copy
import json
import random

import flet as ft

try:
    from .card import Card
    from .gameboard_original import GameBoard as LegacyGameBoard
    from .settings import (
        BACK_OPTIONS,
        DIFFICULTY_PRESETS,
        GAME_MODES,
        THEME_OPTIONS,
        UNLIMITED_PASSES,
        Settings,
    )
    from .slot import Slot
    from .storage import GameStorage
except ImportError:
    from card import Card
    from gameboard_original import GameBoard as LegacyGameBoard
    from settings import (
        BACK_OPTIONS,
        DIFFICULTY_PRESETS,
        GAME_MODES,
        THEME_OPTIONS,
        UNLIMITED_PASSES,
        Settings,
    )
    from slot import Slot
    from storage import GameStorage

LOCAL_GAME_STATE_KEY = "solitaire.game_state.v2"


class Suite:
    def __init__(self, suite_name, suite_color, label):
        self.name = suite_name
        self.color = suite_color
        self.label = label


class Rank:
    def __init__(self, card_name, card_value):
        self.name = card_name
        self.value = card_value


class GameBoard(ft.Stack):
    def __init__(self, page, settings, on_win, on_change):
        super().__init__()
        self.app_page = page
        self.settings = settings
        self.on_win = on_win
        self.on_change = on_change
        self.current_seed = None
        self.current_top = 0
        self.current_left = 0
        self.card_width = 70
        self.card_height = 100
        self.card_offset = 20
        self.column_gap = 10
        self.board_padding = 16
        self.vertical_gap = 28
        self.waste_fan_offset = 16
        self.deck_passes_remaining = int(self.settings.deck_passes_allowed)
        self.score = int(GAME_MODES[self.settings.game_mode]["starting_score"])
        self.elapsed_seconds = 0
        self.status_message = "Pronto para jogar."
        self.history = []
        self.initial_snapshot = None
        self._game_won = False
        self.is_ready = False
        self.cards = []
        self.cards_by_id = {}
        self.foundation = []
        self.tableau = []
        self.all_slots = []

    def setup(self):
        if self.is_ready:
            return
        self.create_slots()
        self.create_card_deck()
        self.is_ready = True
        self.start_new_game(announce=False)

    def create_slots(self):
        self.stock = Slot(self, "stock", top=0, left=0)
        self.waste = Slot(self, "waste", top=0, left=0)
        self.foundation = [Slot(self, "foundation", top=0, left=0) for _ in range(4)]
        self.tableau = [Slot(self, "tableau", top=0, left=0) for _ in range(7)]
        self.all_slots = [self.stock, self.waste, *self.foundation, *self.tableau]
        self.controls = list(self.all_slots)

    def create_card_deck(self):
        suites = [
            Suite("hearts", "RED", "Copas"),
            Suite("diamonds", "RED", "Ouros"),
            Suite("clubs", "BLACK", "Paus"),
            Suite("spades", "BLACK", "Espadas"),
        ]
        ranks = [
            Rank("Ace", 1),
            Rank("2", 2),
            Rank("3", 3),
            Rank("4", 4),
            Rank("5", 5),
            Rank("6", 6),
            Rank("7", 7),
            Rank("8", 8),
            Rank("9", 9),
            Rank("10", 10),
            Rank("Jack", 11),
            Rank("Queen", 12),
            Rank("King", 13),
        ]
        self.cards = []
        self.cards_by_id = {}
        for suite in suites:
            for rank in ranks:
                card = Card(self, suite, rank)
                self.cards.append(card)
                self.cards_by_id[card.card_id] = card
        self.controls.extend(self.cards)

    def can_update(self):
        try:
            return self.page is not None
        except RuntimeError:
            return False

    def notify_change(self, autosave=False, update_board=False):
        if update_board and self.is_ready and self.can_update():
            self.update()
        if self.on_change is not None:
            self.on_change(autosave=autosave)

    def set_status(self, message, autosave=False, update_board=False):
        self.status_message = message
        self.notify_change(autosave=autosave, update_board=update_board)

    def start_new_game(self, announce=True):
        self.settings.apply_difficulty(self.settings.difficulty)
        self.deck_passes_remaining = int(self.settings.deck_passes_allowed)
        self.score = int(GAME_MODES[self.settings.game_mode]["starting_score"])
        self.elapsed_seconds = 0
        self.history.clear()
        self._game_won = False
        self.current_seed = random.SystemRandom().randrange(1, 10_000_000)
        deck = list(self.cards)
        random.Random(self.current_seed).shuffle(deck)
        self.deal_cards(deck)
        self.initial_snapshot = self.capture_state(include_initial=False)
        self.apply_visual_preferences(update=False)
        self.refresh_layout(update=True)
        if announce:
            self.set_status("Nova partida iniciada.", autosave=True)
        else:
            self.notify_change(autosave=False)

    def restart_game(self):
        if self.initial_snapshot is None:
            self.set_status("Nao existe uma partida para reiniciar.")
            return
        self.restore_state(copy.deepcopy(self.initial_snapshot), True, False, False)
        self.set_status("Partida reiniciada a partir da distribuicao inicial.", autosave=True)

    def deal_cards(self, deck):
        for slot in self.all_slots:
            slot.pile.clear()
        for card in self.cards:
            card.slot = None
            card.visible = True
            card.turn_face_down(notify=False)
        deck_index = 0
        for column_index, slot in enumerate(self.tableau):
            for _ in range(column_index + 1):
                deck[deck_index].place(slot)
                deck_index += 1
            slot.get_top_card().turn_face_up(notify=False)
        for card in deck[deck_index:]:
            card.place(self.stock)
        self.display_waste(update=False)

    def remember_state_for_undo(self):
        self.history.append(self.capture_state(include_initial=False))
        if len(self.history) > 150:
            self.history.pop(0)

    def undo_move(self):
        if not self.history:
            self.set_status("Nao ha jogadas para desfazer.")
            return
        snapshot = self.history.pop()
        self.restore_state(snapshot, False, False, False)
        self.set_status("Ultima jogada desfeita.", autosave=True)

    def capture_state(self, include_initial=True):
        state = {
            "version": 2,
            "settings": self.settings.to_dict(),
            "seed": self.current_seed,
            "score": self.score,
            "elapsed_seconds": self.elapsed_seconds,
            "deck_passes_remaining": self.deck_passes_remaining,
            "game_won": self._game_won,
            "stock": [card.card_id for card in self.stock.pile],
            "waste": [card.card_id for card in self.waste.pile],
            "foundation": [[card.card_id for card in slot.pile] for slot in self.foundation],
            "tableau": [[card.card_id for card in slot.pile] for slot in self.tableau],
            "face_up": {card.card_id: card.face_up for card in self.cards},
        }
        if include_initial and self.initial_snapshot is not None:
            state["initial_state"] = copy.deepcopy(self.initial_snapshot)
        return state

    def restore_state(self, snapshot, clear_history=False, set_initial=False, announce=True):
        self.settings = Settings.from_dict(snapshot.get("settings", {}))
        self.score = int(snapshot.get("score", GAME_MODES[self.settings.game_mode]["starting_score"]))
        self.elapsed_seconds = int(snapshot.get("elapsed_seconds", 0))
        self.deck_passes_remaining = int(snapshot.get("deck_passes_remaining", self.settings.deck_passes_allowed))
        self.current_seed = snapshot.get("seed")
        self._game_won = bool(snapshot.get("game_won", False))
        for slot in self.all_slots:
            slot.pile.clear()
        for card in self.cards:
            card.slot = None
            card.visible = True
        for card_id in snapshot.get("stock", []):
            self.cards_by_id[card_id].place(self.stock)
        for card_id in snapshot.get("waste", []):
            self.cards_by_id[card_id].place(self.waste)
        for slot, pile_ids in zip(self.foundation, snapshot.get("foundation", [])):
            for card_id in pile_ids:
                self.cards_by_id[card_id].place(slot)
        for slot, pile_ids in zip(self.tableau, snapshot.get("tableau", [])):
            for card_id in pile_ids:
                self.cards_by_id[card_id].place(slot)
        face_map = snapshot.get("face_up", {})
        for card in self.cards:
            card.set_face(face_map.get(card.card_id, False), notify=False)
        if clear_history:
            self.history.clear()
        if set_initial:
            initial_state = snapshot.get("initial_state")
            self.initial_snapshot = copy.deepcopy(initial_state) if initial_state is not None else self.capture_state(False)
        self.apply_visual_preferences(update=False)
        self.refresh_layout(update=True)
        if announce:
            self.set_status("Estado da partida restaurado.")
        else:
            self.notify_change(autosave=False)

    def move_on_top(self, cards_to_drag, update=True):
        for card in cards_to_drag:
            if card in self.controls:
                self.controls.remove(card)
                self.controls.append(card)
        if update and self.is_ready and self.can_update():
            self.update()

    def bounce_back(self, cards):
        for index, card in enumerate(cards):
            card.top = self.current_top
            if card.slot.type == "tableau":
                card.top += index * self.card_offset
            card.left = self.current_left

    def draw_from_stock(self):
        if len(self.stock.pile) == 0:
            self.set_status("O stock esta vazio. Toca no espaco vazio para reciclar a waste.")
            return
        self.remember_state_for_undo()
        for card in self.waste.get_top_cards(self.settings.waste_size):
            card.visible = False
        draw_count = min(self.settings.waste_size, len(self.stock.pile))
        for _ in range(draw_count):
            top_card = self.stock.pile[-1]
            top_card.place(self.waste)
            top_card.turn_face_up(notify=False)
        self.display_waste(update=False)
        self.status_message = f"Foram compradas {draw_count} carta(s) do stock."
        self.notify_change(autosave=True, update_board=True)

    def recycle_waste_to_stock(self):
        if len(self.stock.pile) > 0:
            return
        if len(self.waste.pile) == 0:
            self.set_status("Nao ha cartas para reciclar.")
            return
        if self.settings.deck_passes_allowed != UNLIMITED_PASSES and self.deck_passes_remaining <= 1:
            self.set_status("Ja nao existem mais passagens pelo stock nesta partida.")
            return
        self.remember_state_for_undo()
        if self.settings.deck_passes_allowed != UNLIMITED_PASSES:
            self.deck_passes_remaining -= 1
        for card in list(reversed(self.waste.pile)):
            card.turn_face_down(notify=False)
            card.place(self.stock)
        if self.settings.game_mode == "classic":
            self.score -= 20
        self.display_waste(update=False)
        self.status_message = "Waste reciclada para o stock."
        self.notify_change(autosave=True, update_board=True)

    def reveal_tableau_card(self, card):
        if card.slot is None or card.slot.type != "tableau" or card.face_up:
            return
        if not card.slot.is_top_card(card):
            return
        self.remember_state_for_undo()
        card.turn_face_up(notify=False)
        if self.settings.game_mode == "classic":
            self.score += 5
        self.status_message = "Carta revelada no tableau."
        self.notify_change(autosave=True, update_board=True)

    def get_drop_targets(self):
        return self.tableau + self.foundation

    def card_is_near_slot(self, card, slot):
        threshold = max(28, int(self.card_width * 0.5))
        return abs(card.top - slot.upper_card_top()) < threshold and abs(card.left - slot.left) < threshold

    def try_move_cards(self, cards_to_drag, target_slot):
        if not cards_to_drag:
            return False
        current_card = cards_to_drag[0]
        source_slot = current_card.slot
        if source_slot is None or source_slot == target_slot:
            return False
        if target_slot.type == "tableau":
            if not self.check_tableau_rules(current_card, target_slot.get_top_card()):
                return False
        elif target_slot.type == "foundation":
            if len(cards_to_drag) != 1 or not self.check_foundation_rules(current_card, target_slot.get_top_card()):
                return False
        else:
            return False
        self.remember_state_for_undo()
        for card in cards_to_drag:
            card.place(target_slot)
        revealed = False
        if source_slot.type == "tableau" and len(source_slot.pile) > 0:
            top_card = source_slot.get_top_card()
            if top_card is not None and not top_card.face_up:
                top_card.turn_face_up(notify=False)
                revealed = True
        elif source_slot.type == "waste":
            self.display_waste(update=False)
        self.apply_score_for_move(source_slot.type, target_slot.type, revealed)
        if self.check_if_you_won():
            self._game_won = True
            self.status_message = "Vitoria! Todas as fundacoes foram preenchidas."
            self.notify_change(autosave=True, update_board=True)
            self.on_win()
        else:
            self.status_message = "Jogada concluida."
            self.notify_change(autosave=True, update_board=True)
        return True

    def auto_move_card_to_foundation(self, card):
        if card.slot is None or not card.face_up:
            return
        if card.slot.type in ("waste", "tableau") and not card.slot.is_top_card(card):
            self.set_status("So a carta exposta no topo pode subir para a fundacao.")
            return
        for slot in self.foundation:
            if self.try_move_cards([card], slot):
                return
        self.set_status("Esta carta nao pode ser movida para a fundacao.")

    def apply_score_for_move(self, source_type, target_type, revealed):
        if self.settings.game_mode == "vegas":
            if target_type == "foundation":
                self.score += 5
            elif source_type == "foundation" and target_type == "tableau":
                self.score -= 15
            return
        if target_type == "foundation" and source_type in ("waste", "tableau"):
            self.score += 10
        elif target_type == "tableau" and source_type == "waste":
            self.score += 5
        elif source_type == "foundation" and target_type == "tableau":
            self.score -= 15
        if revealed:
            self.score += 5

    def check_foundation_rules(self, current_card, top_card=None):
        if top_card is not None:
            return current_card.suite.name == top_card.suite.name and current_card.rank.value - top_card.rank.value == 1
        return current_card.rank.name == "Ace"

    def check_tableau_rules(self, current_card, top_card=None):
        if top_card is not None:
            return current_card.suite.color != top_card.suite.color and top_card.rank.value - current_card.rank.value == 1
        return current_card.rank.name == "King"

    def check_if_you_won(self):
        return sum(len(slot.pile) for slot in self.foundation) == 52

    def format_elapsed(self):
        minutes, seconds = divmod(self.elapsed_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours > 0 else f"{minutes:02d}:{seconds:02d}"

    def format_passes(self):
        if self.settings.deck_passes_allowed == UNLIMITED_PASSES:
            return "INF"
        return str(max(1, self.deck_passes_remaining))

    def apply_visual_preferences(self, update=True):
        for card in self.cards:
            if not card.face_up:
                card.turn_face_down(notify=False)
        self.refresh_layout(update=update)

    def refresh_layout(self, update=True):
        page_width = max(360, int(self.app_page.width or 1200))
        page_height = max(620, int(self.app_page.height or 900))
        if page_width < 480:
            self.board_padding = 12
            self.column_gap = 6
        elif page_width < 720:
            self.board_padding = 16
            self.column_gap = 8
        else:
            self.board_padding = 20
            self.column_gap = 12
        available_width = page_width - 80
        self.card_width = int((available_width - (2 * self.board_padding) - (6 * self.column_gap)) / 7)
        self.card_width = max(42, min(104, self.card_width))
        self.card_height = int(self.card_width * 1.43)
        self.card_offset = max(14, min(30, int(self.card_height * 0.24)))
        self.waste_fan_offset = max(10, int(self.card_width * 0.34))
        self.vertical_gap = max(20, int(self.card_height * 0.4))
        top_y = self.board_padding
        tableau_y = self.board_padding + self.card_height + self.vertical_gap
        positions = [self.board_padding + index * (self.card_width + self.column_gap) for index in range(7)]
        self.stock.top = top_y
        self.stock.left = positions[0]
        self.waste.top = top_y
        self.waste.left = positions[1]
        for index, slot in enumerate(self.foundation):
            slot.top = top_y
            slot.left = positions[index + 3]
        for index, slot in enumerate(self.tableau):
            slot.top = tableau_y
            slot.left = positions[index]
        max_tableau_len = max([len(slot.pile) for slot in self.tableau] or [1])
        tableau_height = self.card_height + max(0, max_tableau_len - 1) * self.card_offset
        self.width = 2 * self.board_padding + 7 * self.card_width + 6 * self.column_gap
        self.height = max(460, page_height - 260, tableau_y + tableau_height + self.board_padding)
        for slot in self.all_slots:
            slot.width = self.card_width
            slot.height = self.card_height
            slot.border_radius = ft.BorderRadius.all(0)
            slot.bgcolor = self.settings.theme["slot_bg"]
            slot.border = ft.Border.all(1.5, self.settings.theme["slot_border"])
        for card in self.cards:
            card.sync_size()
        for card in self.stock.pile:
            card.left = self.stock.left
            card.top = self.stock.top
            card.visible = True
        self.display_waste(update=False)
        for slot in self.foundation:
            for card in slot.pile:
                card.left = slot.left
                card.top = slot.top
                card.visible = True
        for slot in self.tableau:
            for index, card in enumerate(slot.pile):
                card.left = slot.left
                card.top = slot.top + index * self.card_offset
                card.visible = True
        if update and self.is_ready and self.can_update():
            self.update()

    def display_waste(self, update=True):
        visible_cards = self.waste.pile[-self.settings.waste_size :]
        first_visible = len(self.waste.pile) - len(visible_cards)
        for index, card in enumerate(self.waste.pile):
            card.top = self.waste.top
            if index >= first_visible:
                card.left = self.waste.left + self.waste_fan_offset * (index - first_visible)
                card.visible = True
            else:
                card.left = self.waste.left
                card.visible = False
        if update and self.is_ready and self.can_update():
            self.update()


class Solitaire(ft.Column):
    def __init__(self, page, settings, on_win):
        super().__init__(expand=True, spacing=16)
        self.app_page = page
        self.settings = settings
        self.on_win = on_win
        self.storage = GameStorage()
        self.menu_open = False
        self._timer_running = False
        self.is_ready = False
        self.back_previews = {}
        self.theme_swatches = {}
        self.board = LegacyGameBoard(self.app_page, self.settings, self.on_win, self.handle_board_change)
        self._build_shell()

    def _build_shell(self):
        self.menu_button = ft.IconButton(icon=ft.Icons.MENU, icon_size=28, tooltip="Abrir menu", on_click=self.toggle_menu)
        self.title_text = ft.Text("Solitaire Atelier", size=28, weight=ft.FontWeight.BOLD)
        self.subtitle_text = ft.Text("Klondike com extras, mas sem sacrificar o drag and drop.", size=13)
        self.mode_value = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.difficulty_value = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.score_value = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.timer_value = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.passes_value = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.mode_chip = self._build_stat_chip("Modo", self.mode_value)
        self.difficulty_chip = self._build_stat_chip("Dificuldade", self.difficulty_value)
        self.score_chip = self._build_stat_chip("Pontuacao", self.score_value)
        self.timer_chip = self._build_stat_chip("Tempo", self.timer_value)
        self.passes_chip = self._build_stat_chip("Passes", self.passes_value)
        self.stat_chips = [self.mode_chip, self.difficulty_chip, self.score_chip, self.timer_chip, self.passes_chip]
        self.header = ft.Container(
            border_radius=ft.BorderRadius.all(0),
            padding=18,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            self.menu_button,
                            ft.Column(controls=[self.title_text, self.subtitle_text], spacing=2, tight=True),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Row(controls=self.stat_chips, wrap=True, spacing=12, run_spacing=12),
                ],
                spacing=14,
            ),
        )
        self.board_shell = ft.Container(
            expand=True,
            border_radius=ft.BorderRadius.all(0),
            padding=ft.Padding.all(16),
            content=ft.Container(expand=True, content=self.board),
        )
        self.menu_panel = self._build_menu_panel()
        self.body = ft.Column(expand=True, spacing=16)
        self.status_text = ft.Text(size=14)
        self.controls = [self.header, self.body, self.status_text]
        self.refresh_layout(update=False)
        self.refresh_hud(update=False)

    def _build_stat_chip(self, label, value_control):
        return ft.Container(
            border_radius=ft.BorderRadius.all(0),
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            content=ft.Column(controls=[ft.Text(label, size=11), value_control], spacing=2, tight=True),
        )

    def _build_menu_panel(self):
        self.difficulty_group = ft.RadioGroup(
            value=self.settings.difficulty,
            on_change=self.change_difficulty,
            content=ft.Column(
                controls=[
                    ft.Radio(value="easy", label="Facil"),
                    ft.Radio(value="classic", label="Classico"),
                    ft.Radio(value="hard", label="Dificil"),
                ],
                spacing=4,
                tight=True,
            ),
        )
        self.mode_group = ft.RadioGroup(
            value=self.settings.game_mode,
            on_change=self.change_game_mode,
            content=ft.Column(
                controls=[ft.Radio(value="classic", label="Classico"), ft.Radio(value="vegas", label="Vegas")],
                spacing=4,
                tight=True,
            ),
        )
        back_controls = []
        for back_name, back_data in BACK_OPTIONS.items():
            preview = ft.Container(
                width=72,
                height=102,
                border_radius=ft.BorderRadius.all(0),
                border=ft.Border.all(2, "#00000000"),
                padding=4,
                data=back_name,
                on_click=self.change_card_back,
                content=ft.Image(src=back_data["asset"], fit=ft.BoxFit.COVER),
            )
            self.back_previews[back_name] = preview
            back_controls.append(
                ft.Column(
                    controls=[preview, ft.Text(back_data["label"], size=12)],
                    spacing=6,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    tight=True,
                )
            )
        theme_controls = []
        for theme_name, theme_data in THEME_OPTIONS.items():
            swatch = ft.Container(
                width=72,
                height=72,
                border_radius=ft.BorderRadius.all(0),
                border=ft.Border.all(2, "#00000000"),
                bgcolor=theme_data["board_bg"],
                data=theme_name,
                on_click=self.change_theme,
            )
            self.theme_swatches[theme_name] = swatch
            theme_controls.append(
                ft.Column(
                    controls=[swatch, ft.Text(theme_data["label"], size=12, width=72)],
                    spacing=6,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    tight=True,
                )
            )
        return ft.Container(
            width=320,
            border_radius=ft.BorderRadius.all(0),
            padding=20,
            content=ft.Column(
                controls=[
                    ft.Text("Menu da partida", size=24, weight=ft.FontWeight.BOLD),
                    ft.Text("As opcoes ficam aqui, mas o tabuleiro segue o fluxo classico do jogo.", size=13),
                    ft.Row(
                        controls=[
                            ft.FilledButton("Novo jogo", icon=ft.Icons.CASINO, on_click=self.new_game),
                            ft.OutlinedButton("Reiniciar", icon=ft.Icons.RESTART_ALT, on_click=self.restart_game),
                        ],
                        wrap=True,
                        spacing=10,
                    ),
                    ft.Row(
                        controls=[
                            ft.OutlinedButton("Desfazer", icon=ft.Icons.UNDO, on_click=self.undo_move),
                            ft.OutlinedButton("Guardar", icon=ft.Icons.SAVE_ALT, on_click=self.save_game),
                            ft.OutlinedButton("Carregar", icon=ft.Icons.DOWNLOAD, on_click=self.load_game),
                        ],
                        wrap=True,
                        spacing=10,
                    ),
                    ft.Divider(),
                    ft.Text("Dificuldade", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(DIFFICULTY_PRESETS[self.settings.difficulty]["description"], size=12),
                    self.difficulty_group,
                    ft.Divider(),
                    ft.Text("Modo de jogo", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(GAME_MODES[self.settings.game_mode]["description"], size=12),
                    self.mode_group,
                    ft.Divider(),
                    ft.Text("Costas das cartas", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text("Podes trocar apenas o back, sem mexer no tema.", size=12),
                    ft.Row(controls=back_controls, wrap=True, spacing=10, run_spacing=12),
                    ft.Divider(),
                    ft.Text("Tema do tabuleiro", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text("O tema muda a janela e o board separadamente do back.", size=12),
                    ft.Row(controls=theme_controls, wrap=True, spacing=10, run_spacing=12),
                ],
                spacing=12,
                scroll=ft.ScrollMode.AUTO,
            ),
        )

    def did_mount(self):
        self.app_page.padding = 20
        self.app_page.scroll = ft.ScrollMode.AUTO
        self.app_page.on_resize = self.handle_resize
        self.board.setup()
        self.settings = self.board.settings
        self.sync_menu_state()
        self.apply_theme(update=False)
        self.refresh_layout(update=False)
        self.refresh_hud(update=False)
        self.is_ready = True
        self._timer_running = True
        self.app_page.run_task(self.run_timer)
        self.update()

    def will_unmount(self):
        self._timer_running = False

    def handle_resize(self, e):
        if not self.board.is_ready:
            return
        self.refresh_layout(update=False)
        self.board.refresh_layout(update=False)
        self.update()

    def toggle_menu(self, e):
        self.menu_open = not self.menu_open
        self.refresh_layout()

    def refresh_layout(self, update=True):
        page_width = int(self.app_page.width or 1200)
        narrow = page_width < 980
        self.menu_panel.width = None if narrow else 320
        self.body.controls.clear()
        if self.menu_open:
            if narrow:
                self.body.controls.extend([self.menu_panel, self.board_shell])
            else:
                self.body.controls.append(
                    ft.Row(
                        controls=[self.menu_panel, self.board_shell],
                        spacing=16,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    )
                )
        else:
            self.body.controls.append(self.board_shell)
        if update and self.is_ready:
            self.update()

    def refresh_hud(self, update=True):
        self.mode_value.value = self.settings.mode_label
        self.difficulty_value.value = self.settings.difficulty_label
        self.score_value.value = str(self.board.score)
        self.timer_value.value = self.board.format_elapsed()
        self.passes_value.value = self.board.format_passes()
        self.status_text.value = self.board.status_message
        if update and self.is_ready:
            self.update()

    def handle_board_change(self, autosave=False):
        self.settings = self.board.settings
        self.refresh_hud(update=False)
        if self.is_ready:
            self._update_hud_controls()

    def _update_hud_controls(self):
        for control in (
            self.mode_value,
            self.difficulty_value,
            self.score_value,
            self.timer_value,
            self.passes_value,
            self.status_text,
        ):
            try:
                control.update()
            except Exception:
                pass

    def sync_menu_state(self):
        self.difficulty_group.value = self.settings.difficulty
        self.mode_group.value = self.settings.game_mode
        accent = self.settings.theme["accent"]
        panel_bg_alt = self.settings.theme["panel_bg_alt"]
        for back_name, preview in self.back_previews.items():
            preview.border = ft.Border.all(3, accent) if back_name == self.settings.card_back_name else ft.Border.all(2, "#00000000")
            preview.bgcolor = panel_bg_alt
        for theme_name, swatch in self.theme_swatches.items():
            swatch.border = ft.Border.all(3, accent) if theme_name == self.settings.theme_name else ft.Border.all(2, "#00000000")

    def apply_theme(self, update=True):
        theme = self.settings.theme
        self.app_page.bgcolor = theme["page_bg"]
        self.header.bgcolor = theme["header_bg"]
        self.menu_panel.bgcolor = theme["panel_bg"]
        self.board_shell.bgcolor = theme["board_bg_alt"]
        self.title_text.color = theme["text"]
        self.subtitle_text.color = theme["muted"]
        self.status_text.color = theme["muted"]
        self.menu_button.icon_color = theme["text"]
        for chip in self.stat_chips:
            chip.bgcolor = theme["chip_bg"]
            chip.border = ft.Border.all(1, theme["slot_border"])
            chip.content.controls[0].color = theme["muted"]
            chip.content.controls[1].color = theme["text"]
        if update and self.is_ready:
            self.update()

    def new_game(self, e):
        self.board.start_new_game(announce=True)

    def restart_game(self, e):
        self.board.restart_game()

    def undo_move(self, e):
        self.board.undo_move()

    def change_difficulty(self, e):
        new_difficulty = e.control.value
        if new_difficulty == self.settings.difficulty:
            return
        self.settings.apply_difficulty(new_difficulty)
        self.board.settings = self.settings
        self.board.start_new_game(announce=False)
        self.sync_menu_state()
        self.refresh_hud(update=False)
        if self.is_ready:
            self.update()
        self.board.set_status(f"Dificuldade alterada para {DIFFICULTY_PRESETS[new_difficulty]['label']}.", autosave=True)

    def change_game_mode(self, e):
        new_mode = e.control.value
        if new_mode == self.settings.game_mode:
            return
        self.settings.game_mode = new_mode if new_mode in GAME_MODES else "classic"
        self.board.settings = self.settings
        self.board.start_new_game(announce=False)
        self.sync_menu_state()
        self.refresh_hud(update=False)
        if self.is_ready:
            self.update()
        self.board.set_status(f"Modo alterado para {GAME_MODES[self.settings.game_mode]['label']}.", autosave=True)

    def change_card_back(self, e):
        back_name = e.control.data
        if back_name not in BACK_OPTIONS:
            return
        self.settings.card_back_name = back_name
        self.board.settings = self.settings
        self.board.apply_visual_preferences(update=True)
        self.sync_menu_state()
        if self.is_ready:
            self.update()
        self.board.set_status(f"Back alterado para {BACK_OPTIONS[back_name]['label']}.", autosave=True)

    def change_theme(self, e):
        theme_name = e.control.data
        if theme_name not in THEME_OPTIONS:
            return
        self.settings.theme_name = theme_name
        self.board.settings = self.settings
        self.board.refresh_layout(update=True)
        self.sync_menu_state()
        self.apply_theme(update=False)
        if self.is_ready:
            self.update()
        self.board.set_status(f"Tema alterado para {THEME_OPTIONS[theme_name]['label']}.", autosave=True)

    def save_game(self, e):
        self.app_page.run_task(self.save_game_async, True)

    async def save_game_async(self, manual=False):
        snapshot = self.board.capture_state(include_initial=True)
        local_error = None
        duck_error = None
        try:
            preferences = ft.SharedPreferences()
            await preferences.set(LOCAL_GAME_STATE_KEY, json.dumps(snapshot))
        except Exception as exc:
            local_error = str(exc)
        try:
            await asyncio.to_thread(self.storage.save_game, snapshot)
        except Exception as exc:
            duck_error = str(exc)
        if manual:
            if local_error is None and duck_error is None:
                self.board.set_status("Partida guardada em DuckDB e local storage.")
            elif local_error is None:
                self.board.set_status(f"Partida guardada localmente. DuckDB indisponivel: {duck_error}")
            elif duck_error is None:
                self.board.set_status(f"Partida guardada em DuckDB. Local storage indisponivel: {local_error}")
            else:
                self.board.set_status("Nao foi possivel guardar a partida.")

    def load_game(self, e):
        self.app_page.run_task(self.load_game_async)

    async def load_game_async(self):
        snapshot = None
        source = None
        try:
            duck_snapshot = await asyncio.to_thread(self.storage.load_game)
            if duck_snapshot is not None:
                snapshot = duck_snapshot
                source = "DuckDB"
        except Exception:
            snapshot = None
        if snapshot is None:
            try:
                preferences = ft.SharedPreferences()
                raw_state = await preferences.get(LOCAL_GAME_STATE_KEY)
                if raw_state:
                    snapshot = json.loads(raw_state)
                    source = "local storage"
            except Exception:
                snapshot = None
        if snapshot is None:
            self.board.set_status("Nao existe uma partida guardada.")
            return
        self.board.restore_state(snapshot, clear_history=True, set_initial=True, announce=False)
        self.settings = self.board.settings
        self.sync_menu_state()
        self.apply_theme(update=False)
        self.refresh_hud(update=False)
        self.update()
        self.board.set_status(f"Partida carregada a partir de {source}.")

    async def run_timer(self):
        while self._timer_running:
            await asyncio.sleep(1)
            if not self.board.is_ready or self.board._game_won:
                continue
            self.board.elapsed_seconds += 1
            self.timer_value.value = self.board.format_elapsed()
            try:
                self.timer_value.update()
            except Exception:
                pass
