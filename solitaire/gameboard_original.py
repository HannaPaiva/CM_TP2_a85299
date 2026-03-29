import copy
import random

import flet as ft

try:
    from .card import Card
    from .settings import GAME_MODES, Settings, UNLIMITED_PASSES
    from .slot import Slot
except ImportError:
    from card import Card
    from settings import GAME_MODES, Settings, UNLIMITED_PASSES
    from slot import Slot


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
        self.width = 1000
        self.height = 500
        self.current_top = 0
        self.current_left = 0
        self.card_width = 70
        self.card_height = 100
        self.card_offset = 20
        self.settings = settings
        self.deck_passes_remaining = int(self.settings.deck_passes_allowed)
        self.on_win = on_win
        self.on_change = on_change
        self.current_seed = None
        self.history = []
        self.initial_snapshot = None
        self.score = int(GAME_MODES[self.settings.game_mode]["starting_score"])
        self.elapsed_seconds = 0
        self.status_message = "Pronto para jogar."
        self._game_won = False
        self.is_ready = False
        self.controls = []
        self.cards = []
        self.cards_by_id = {}
        self.foundation = []
        self.tableau = []
        self.all_slots = []

    def can_update(self):
        try:
            return self.page is not None
        except RuntimeError:
            return False

    def notify_change(self, autosave=False):
        if self.on_change is not None:
            self.on_change(autosave=autosave)

    def set_status(self, message, autosave=False, update_board=False):
        self.status_message = message
        if update_board and self.can_update():
            self.update()
        self.notify_change(autosave=autosave)

    def setup(self):
        if self.is_ready:
            return
        self.create_slots()
        self.create_card_deck()
        self.is_ready = True
        self.start_new_game(announce=False)

    def create_slots(self):
        self.stock = Slot(self, "stock", top=0, left=0, border=ft.Border.all(1, self.settings.theme["slot_border"]))
        self.waste = Slot(self, "waste", top=0, left=100, border=None)
        self.foundation = []
        x = 300
        for _ in range(4):
            self.foundation.append(
                Slot(
                    solitaire=self,
                    slot_type="foundation",
                    top=0,
                    left=x,
                    border=ft.Border.all(1, self.settings.theme["slot_border"]),
                )
            )
            x += 100
        self.tableau = []
        x = 0
        for _ in range(7):
            self.tableau.append(
                Slot(
                    solitaire=self,
                    slot_type="tableau",
                    top=150,
                    left=x,
                    border=None,
                )
            )
            x += 100
        self.all_slots = [self.stock, self.waste, *self.foundation, *self.tableau]
        self.controls = list(self.all_slots)
        self.apply_visual_preferences(update=False)

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
                card = Card(solitaire=self, suite=suite, rank=rank)
                self.cards.append(card)
                self.cards_by_id[card.card_id] = card
        self.controls.extend(self.cards)

    def reset_board_state(self):
        for slot in self.all_slots:
            slot.pile.clear()
        for card in self.cards:
            card.slot = None
            card.visible = True
            card.turn_face_down(notify=False)

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
        self.reset_board_state()
        self.deal_cards(deck)
        self.initial_snapshot = self.capture_state(include_initial=False)
        self.apply_visual_preferences(update=False)
        self.display_waste(update=False)
        if self.can_update():
            self.update()
        if announce:
            self.set_status("Nova partida iniciada.", autosave=True)
        else:
            self.notify_change(autosave=False)

    def restart_game(self):
        if self.initial_snapshot is None:
            self.set_status("Nao existe uma partida para reiniciar.")
            return
        self.restore_state(copy.deepcopy(self.initial_snapshot), clear_history=True, set_initial=False, announce=False)
        self.set_status("Partida reiniciada a partir da distribuicao inicial.")

    def deal_cards(self, deck):
        card_index = 0
        first_slot = 0
        while card_index <= 27:
            for slot_index in range(first_slot, len(self.tableau)):
                deck[card_index].place(self.tableau[slot_index])
                card_index += 1
            first_slot += 1
        for number in range(len(self.tableau)):
            self.tableau[number].get_top_card().turn_face_up(notify=False)
        for i in range(28, len(deck)):
            deck[i].place(self.stock)

    def before_action(self):
        self.remember_state_for_undo()

    def after_tableau_reveal(self, notify=False):
        if self.settings.game_mode == "classic":
            self.score += 5
        if notify:
            self.set_status("Carta revelada no tableau.")

    def after_move(self, old_slot, new_slot):
        self.apply_score_for_move(old_slot.type, new_slot.type)
        if self.check_if_you_won():
            self._game_won = True
        self.notify_change(autosave=True)

    def remember_state_for_undo(self):
        self.history.append(self.capture_state(include_initial=False))
        if len(self.history) > 150:
            self.history.pop(0)

    def undo_move(self):
        if not self.history:
            self.set_status("Nao ha jogadas para desfazer.")
            return
        snapshot = self.history.pop()
        self.restore_state(snapshot, clear_history=False, set_initial=False, announce=False)
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
        current_card_back_name = self.settings.card_back_name
        current_theme_name = self.settings.theme_name
        current_board_bg_style = getattr(self.settings, "board_bg_style", "theme_color")
        current_board_bg_target = getattr(self.settings, "board_bg_target", "")
        restored_settings = Settings.from_dict(snapshot.get("settings", {}))
        restored_settings.card_back_name = current_card_back_name
        restored_settings.theme_name = current_theme_name
        restored_settings.board_bg_style = current_board_bg_style
        restored_settings.board_bg_target = current_board_bg_target
        self.settings = restored_settings
        self.deck_passes_remaining = int(snapshot.get("deck_passes_remaining", self.settings.deck_passes_allowed))
        self.score = int(snapshot.get("score", GAME_MODES[self.settings.game_mode]["starting_score"]))
        self.elapsed_seconds = int(snapshot.get("elapsed_seconds", 0))
        self.current_seed = snapshot.get("seed")
        self._game_won = bool(snapshot.get("game_won", False))
        self.reset_board_state()
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
            self.initial_snapshot = copy.deepcopy(initial_state) if initial_state is not None else self.capture_state(include_initial=False)
        self.apply_visual_preferences(update=False)
        self.display_waste(update=False)
        if self.can_update():
            self.update()
        if announce:
            self.set_status("Estado da partida restaurado.")
        else:
            self.notify_change()

    def draw_from_stock(self):
        if len(self.stock.pile) == 0:
            self.set_status("O stock esta vazio.")
            return
        self.before_action()
        for card in self.waste.get_top_cards(self.settings.waste_size):
            card.visible = False
        for _ in range(min(self.settings.waste_size, len(self.stock.pile))):
            top_card = self.stock.pile[-1]
            top_card.place(self.waste)
            top_card.turn_face_up()
        self.display_waste()
        self.notify_change(autosave=True)

    def restart_stock(self):
        self.waste.pile.reverse()
        while len(self.waste.pile) > 0:
            card = self.waste.pile[0]
            card.turn_face_down()
            card.place(self.stock)
        if self.settings.game_mode == "classic":
            self.score -= 20
        self.notify_change(autosave=True)

    def move_on_top(self, cards_to_drag, update=True):
        for card in cards_to_drag:
            if card in self.controls:
                self.controls.remove(card)
                self.controls.append(card)
        if update and self.can_update():
            self.update()

    def bounce_back(self, cards):
        i = 0
        for card in cards:
            card.top = self.current_top
            if card.slot.type == "tableau":
                card.top += i * self.card_offset
            card.left = self.current_left
            i += 1

    def display_waste(self, update=True):
        visible_count = self.settings.waste_size
        if visible_count == 1:
            visible_count = 2

        visible_cards = self.waste.get_top_cards(visible_count)
        first_visible = len(self.waste.pile) - len(visible_cards)

        for index, card in enumerate(self.waste.pile):
            card.top = self.waste.top
            if index >= first_visible:
                card.left = self.waste.left
                if self.settings.waste_size == 3:
                    card.left += self.card_offset * (index - first_visible)
                card.visible = True
            else:
                card.left = self.waste.left
                card.visible = False

        self.move_on_top(visible_cards, update=False)
        if update and self.can_update():
            self.update()

    def auto_move_card_to_foundation(self, card):
        if card.slot is None or not card.face_up:
            return
        if card.slot.type == "tableau" and not card.slot.is_top_card(card):
            return
        self.before_action()
        old_slot = card.slot
        for slot in self.foundation:
            if self.check_foundation_rules(card, slot.get_top_card()):
                self.move_on_top([card])
                card.place(slot)
                if len(old_slot.pile) > 0 and old_slot.type == "tableau":
                    old_slot.get_top_card().turn_face_up()
                    self.after_tableau_reveal()
                elif old_slot.type == "waste":
                    self.display_waste()
                self.after_move(old_slot, slot)
                return
        if self.history:
            self.history.pop()

    def apply_score_for_move(self, source_type, target_type):
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
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    def format_passes(self):
        if self.settings.deck_passes_allowed == UNLIMITED_PASSES:
            return "INF"
        return str(max(1, self.deck_passes_remaining))

    def apply_visual_preferences(self, update=True):
        page_w = max(300, int(self.app_page.width or 700))
        page_h = max(560, int(self.app_page.height or 900))
        avail = max(280, page_w - 48)

        if avail >= 700:
            self.card_width = 70
            self.card_height = 100
            self.card_offset = 20
            col_unit = 100
            tableau_top = 150
            self.width = 1000
            self.height = 500
        else:
            if page_w < 480:
                avail = max(320, page_w - 20)
                width_factor = 0.95
                offset_factor = 0.18
                gap_factor = 0.16
                min_card_width = 38
            else:
                avail = max(300, page_w - 32)
                width_factor = 0.90
                offset_factor = 0.20
                gap_factor = 0.12
                min_card_width = 32
            col_unit = avail / 7
            self.card_width = max(min_card_width, int(col_unit * width_factor))
            self.card_height = int(self.card_width * 10 / 7)
            self.card_offset = max(10, int(self.card_height * offset_factor))
            tableau_top = self.card_height + max(8, int(self.card_height * gap_factor))
            self.width = avail
            self.height = max(
                tableau_top + self.card_height + 14 * self.card_offset + 20,
                page_h - 180 if page_w < 480 else 420,
            )

        self.stock.left = 0
        self.stock.top = 0
        self.waste.left = int(col_unit)
        self.waste.top = 0
        for i, slot in enumerate(self.foundation):
            slot.left = int((3 + i) * col_unit)
            slot.top = 0
        for i, slot in enumerate(self.tableau):
            slot.left = int(i * col_unit)
            slot.top = tableau_top

        for slot in self.all_slots:
            slot.width = self.card_width
            slot.height = self.card_height
            slot.bgcolor = self.settings.theme["slot_bg"]
            if slot.type in ("stock", "foundation"):
                slot.border = ft.Border.all(1, self.settings.theme["slot_border"])
            slot.border_radius = ft.BorderRadius.all(6)

        for card in self.cards:
            card.sync_size()
            if not card.face_up:
                card.turn_face_down(notify=False)
            if card.slot is not None:
                card.left = card.slot.left
                if card.slot.type == "tableau":
                    card.top = card.slot.top + self.card_offset * card.slot.pile.index(card)
                else:
                    card.top = card.slot.top

        if update and self.can_update():
            self.update()

    def refresh_layout(self, update=True):
        self.apply_visual_preferences(update=update)
