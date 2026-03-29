import flet as ft

class Card(ft.GestureDetector):
    def __init__(self, solitaire, suite, rank):
        super().__init__()
        self.solitaire = solitaire
        self.suite = suite
        self.rank = rank
        self.card_id = f"{self.rank.name}_{self.suite.name}"
        self.face_up = False
        self.slot = None
        self._dragging_cards = []
        self.mouse_cursor = ft.MouseCursor.MOVE
        self.drag_interval = 16
        self.on_pan_update = self.drag
        self.on_pan_start = self.start_drag
        self.on_pan_end = self.drop
        self.on_tap = self.click
        self.on_double_tap = self.doubleclick
        self.content = ft.Container(
            width=70,
            height=100,
            border_radius=ft.BorderRadius.all(6),
            content=ft.Image(src=self.solitaire.settings.card_back),
        )

    def sync_size(self):
        self.content.width = self.solitaire.card_width
        self.content.height = self.solitaire.card_height
        self.content.border_radius = ft.BorderRadius.all(6)
        self.content.content.width = self.solitaire.card_width
        self.content.content.height = self.solitaire.card_height
        self.content.content.fit = None

    def set_face(self, face_up, notify=True):
        self.face_up = bool(face_up)
        if self.face_up:
            self.content.content.src = f"images/{self.card_id}.svg"
        else:
            self.content.content.src = self.solitaire.settings.card_back
        if notify and self.solitaire.can_update():
            self.solitaire.update()

    def turn_face_up(self, notify=True):
        self.set_face(True, notify=notify)

    def turn_face_down(self, notify=True):
        self.set_face(False, notify=notify)

    def can_be_moved(self):
        if self.slot is None:
            return False
        if self.face_up and self.slot.type != "waste":
            return True
        if self.slot.type == "waste" and len(self.solitaire.waste.pile) - 1 == self.solitaire.waste.pile.index(self):
            return True
        return False

    def start_drag(self, e: ft.DragStartEvent):
        if self.can_be_moved():
            self._dragging_cards = self.get_cards_to_move()
            self.solitaire.current_top = e.control.top
            self.solitaire.current_left = e.control.left

    def drag(self, e: ft.DragUpdateEvent):
        if self.can_be_moved():
            for card in self._dragging_cards:
                card.top = max(0, card.top + e.local_delta.y)
                card.left = max(0, card.left + e.local_delta.x)
                card.update()

    def drop(self, e: ft.DragEndEvent):
        if self.can_be_moved():
            cards_to_drag = self._dragging_cards
            self.solitaire.move_on_top(cards_to_drag)
            slots = self.solitaire.tableau + self.solitaire.foundation
            for slot in slots:
                if abs(self.top - slot.upper_card_top()) < 40 and abs(self.left - slot.left) < 40:
                    if (
                        slot.type == "tableau"
                        and self.solitaire.check_tableau_rules(self, slot.get_top_card())
                    ) or (
                        slot.type == "foundation"
                        and len(cards_to_drag) == 1
                        and self.solitaire.check_foundation_rules(self, slot.get_top_card())
                    ):
                        self.solitaire.before_action()
                        old_slot = self.slot
                        for card in cards_to_drag:
                            card.place(slot)
                        if len(old_slot.pile) > 0 and old_slot.type == "tableau":
                            old_slot.get_top_card().turn_face_up()
                            self.solitaire.after_tableau_reveal()
                        elif old_slot.type == "waste":
                            self.solitaire.display_waste()
                        self.solitaire.after_move(old_slot, slot)
                        self._dragging_cards = []
                        return

            self.solitaire.bounce_back(cards_to_drag)
            self.solitaire.update()
            self._dragging_cards = []

    def doubleclick(self, e):
        if self.slot is not None and self.slot.type in ("waste", "tableau"):
            if self.face_up:
                self.solitaire.before_action()
                self.solitaire.move_on_top([self])
                old_slot = self.slot
                for slot in self.solitaire.foundation:
                    if self.solitaire.check_foundation_rules(self, slot.get_top_card()):
                        self.place(slot)
                        if len(old_slot.pile) > 0 and old_slot.type == "tableau":
                            old_slot.get_top_card().turn_face_up()
                            self.solitaire.after_tableau_reveal()
                        elif old_slot.type == "waste":
                            self.solitaire.display_waste()
                        self.solitaire.after_move(old_slot, slot)
                        return
                self.solitaire.history.pop() if self.solitaire.history else None

    def click(self, e):
        if self.slot is None:
            return
        if self.slot.type == "stock":
            self.solitaire.draw_from_stock()
        if self.slot.type == "tableau":
            if self.face_up is False and len(self.slot.pile) - 1 == self.slot.pile.index(self):
                self.solitaire.before_action()
                self.turn_face_up()
                self.solitaire.after_tableau_reveal()

    def place(self, slot):
        self.top = slot.top
        self.left = slot.left
        if slot.type == "tableau":
            self.top += self.solitaire.card_offset * len(slot.pile)

        if self.slot is not None:
            self.slot.pile.remove(self)

        self.slot = slot
        slot.pile.append(self)
        self.solitaire.move_on_top([self])
        if self.solitaire.check_if_you_won():
            self.solitaire.on_win()
        if self.solitaire.can_update():
            self.solitaire.update()

    def get_cards_to_move(self):
        if self.slot is not None:
            return self.slot.pile[self.slot.pile.index(self) :]
        return [self]
