"""
Testes de regressao para as otimizações de drag/drop.

O objetivo aqui e proteger os pontos que mais facilmente voltariam a ficar
caros: updates por carta, redraws prematuros em `place()` e refreshes em
cascata ao comprar do stock.
"""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from solitaire.card import Card
from solitaire.gameboard import GameBoard
from solitaire.settings import Settings


class FakeSlot:
    """
    Double minimo de slot para cenarios isolados de performance.
    """

    def __init__(self, slot_type="tableau", top=0, left=0):
        self.type = slot_type
        self.top = top
        self.left = left
        self.pile = []

    def is_top_card(self, card):
        return bool(self.pile) and self.pile[-1] is card


class FakeSolitaire:
    """
    Double minimo do tabuleiro para contar pedidos de update.
    """

    def __init__(self):
        self.settings = Settings()
        self.card_offset = 20
        self.current_top = 0
        self.current_left = 0
        self.update_calls = 0
        self.last_moved_cards = []
        self.waste = FakeSlot(slot_type="waste")

    def can_update(self):
        return True

    def update(self):
        self.update_calls += 1

    def move_on_top(self, cards_to_drag, update=True):
        self.last_moved_cards = list(cards_to_drag)
        if update and self.can_update():
            self.update()

    def check_if_you_won(self):
        return False

    def on_win(self):
        return None


class CountingGameBoard(GameBoard):
    """
    Variante de `GameBoard` que conta quantos redraws foram pedidos.
    """

    def __init__(self):
        super().__init__(
            page=SimpleNamespace(width=1000, height=700),
            settings=Settings(),
            on_win=None,
            on_change=None,
        )
        self.update_calls = 0

    def can_update(self):
        return True

    def update(self):
        self.update_calls += 1


class DragPerformanceRegressionTests(unittest.TestCase):
    """
    Agrupa cenarios que nao podem regredir sem reintroduzir lag.
    """

    @staticmethod
    def make_card(solitaire, suite_name, rank_name, rank_value):
        """
        Cria uma carta simples para testes controlados.
        """
        suite = SimpleNamespace(name=suite_name, color="RED")
        rank = SimpleNamespace(name=rank_name, value=rank_value)
        return Card(solitaire=solitaire, suite=suite, rank=rank)

    def test_drag_batches_visual_update_for_tableau_stack(self):
        """
        Arrastar uma subpilha deve evitar update individual por carta.
        """
        solitaire = FakeSolitaire()
        slot = FakeSlot(slot_type="tableau", top=30, left=40)
        cards = [
            self.make_card(solitaire, "hearts", "5", 5),
            self.make_card(solitaire, "clubs", "4", 4),
            self.make_card(solitaire, "diamonds", "3", 3),
        ]

        for index, card in enumerate(cards):
            card.face_up = True
            card.slot = slot
            card.top = slot.top + solitaire.card_offset * index
            card.left = slot.left
            card.update = Mock()
        slot.pile = list(cards)

        dragged = cards[0]
        dragged.start_drag(SimpleNamespace(control=dragged))
        dragged.drag(SimpleNamespace(local_delta=SimpleNamespace(x=7, y=11)))

        self.assertEqual(solitaire.update_calls, 1)
        for card in cards:
            card.update.assert_not_called()

        self.assertEqual(cards[0].top, 41)
        self.assertEqual(cards[1].top, 61)
        self.assertEqual(cards[2].top, 81)
        self.assertEqual(cards[0].left, 47)
        self.assertEqual(cards[1].left, 47)
        self.assertEqual(cards[2].left, 47)

    def test_place_can_skip_immediate_update_when_batching(self):
        """
        `place(update=False)` deve permitir batching sem redraw imediato.
        """
        solitaire = FakeSolitaire()
        old_slot = FakeSlot(slot_type="tableau", top=10, left=15)
        new_slot = FakeSlot(slot_type="tableau", top=120, left=220)
        card = self.make_card(solitaire, "spades", "King", 13)

        card.face_up = True
        card.slot = old_slot
        card.top = old_slot.top
        card.left = old_slot.left
        old_slot.pile.append(card)

        card.place(new_slot, update=False)

        self.assertEqual(solitaire.update_calls, 0)
        self.assertEqual(old_slot.pile, [])
        self.assertEqual(new_slot.pile, [card])
        self.assertIs(card.slot, new_slot)
        self.assertEqual(card.top, 120)
        self.assertEqual(card.left, 220)
        self.assertEqual(solitaire.last_moved_cards, [card])

    def test_draw_from_stock_updates_board_once(self):
        """
        Comprar do stock deve terminar com apenas um redraw do board.
        """
        board = CountingGameBoard()
        board.setup()
        board.update_calls = 0

        waste_size = board.settings.waste_size
        stock_before = len(board.stock.pile)

        board.draw_from_stock()

        self.assertEqual(board.update_calls, 1)
        self.assertEqual(len(board.stock.pile), stock_before - waste_size)
        self.assertEqual(len(board.waste.pile), waste_size)
        self.assertTrue(all(card.face_up for card in board.waste.pile))


if __name__ == "__main__":
    unittest.main()
