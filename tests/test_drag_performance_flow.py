"""
Testes do fluxo principal das optimizacoes de drag/drop.

Este modulo garante que o caminho feliz das melhorias de performance continua
ativo: batching de updates durante o arrasto e um unico redraw ao fechar um
drop valido.
"""

from types import SimpleNamespace
from unittest.mock import Mock
import unittest

from solitaire.gameboard import GameBoard
from solitaire.settings import Settings


class DragPerformanceFlowTests(unittest.TestCase):
    """
    Valida o fluxo esperado das optimizacoes de interacao do tabuleiro.
    """

    def make_board(self):
        """
        Cria um `GameBoard` controlado para contar redraws com precisao.
        """
        page = SimpleNamespace(width=1000, height=700, update=Mock(name="page.update"))
        board = GameBoard(
            page=page,
            settings=Settings(),
            on_win=lambda: None,
            on_change=lambda autosave=False: None,
        )
        board.can_update = lambda: True
        board.update = Mock(name="board.update")
        board.create_slots()
        board.create_card_deck()
        return board, page

    def test_drag_batches_stack_updates_into_one_page_refresh(self):
        """
        Um arrasto de pilha deve atualizar as cartas numa chamada agrupada.
        """
        board, page = self.make_board()
        slot = board.tableau[0]
        dragged_cards = board.cards[:3]

        for card in dragged_cards:
            card.turn_face_up(notify=False)
            card.place(slot, update=False)

        anchor = dragged_cards[0]
        anchor.start_drag(SimpleNamespace(control=anchor))
        anchor.drag(SimpleNamespace(local_delta=SimpleNamespace(x=5, y=7)))

        page.update.assert_called_once_with(*dragged_cards)
        board.update.assert_not_called()

        for index, card in enumerate(dragged_cards):
            self.assertEqual(card.left, slot.left + 5)
            self.assertEqual(card.top, slot.top + (board.card_offset * index) + 7)

    def test_valid_drop_redraws_board_once(self):
        """
        Um drop valido deve consolidar a jogada num unico redraw do board.
        """
        board, _page = self.make_board()
        ace = next(
            card
            for card in board.cards
            if card.rank.name == "Ace" and card.suite.name == "clubs"
        )

        ace.turn_face_up(notify=False)
        ace.place(board.tableau[0], update=False)

        ace.start_drag(SimpleNamespace(control=ace))
        ace.top = board.foundation[0].top
        ace.left = board.foundation[0].left
        ace.drop(SimpleNamespace())

        self.assertIs(ace.slot, board.foundation[0])
        self.assertEqual(board.update.call_count, 1)


if __name__ == "__main__":
    unittest.main()
