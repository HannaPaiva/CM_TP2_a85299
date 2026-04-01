"""
Representacao visual e logica das pilhas do tabuleiro.

Um `Slot` e uma area do jogo que pode conter cartas. O mesmo componente e
usado para stock, waste, fundacoes e colunas do tableau. Alem da parte
visual, o objeto conhece o proprio tipo e disponibiliza operacoes utilitarias
que simplificam a logica do tabuleiro.
"""

import flet as ft


class Slot(ft.Container):
    """
    Modela uma pilha/posicao do tabuleiro de Solitaire.

    Cada slot guarda as cartas que lhe pertencem na lista `pile` e tambem
    expone metodos utilitarios para obter topo, subconjuntos visiveis e
    coordenadas relevantes para drag-and-drop.
    """

    def __init__(self, solitaire, slot_type, top, left, border):
        """
        Cria um novo slot visual.

        Args:
            solitaire:
                Referencia ao `GameBoard` dono deste slot.
            slot_type:
                Tipo logico do slot: `stock`, `waste`, `foundation` ou
                `tableau`.
            top:
                Coordenada vertical inicial no stack do tabuleiro.
            left:
                Coordenada horizontal inicial no stack do tabuleiro.
            border:
                Borda opcional usada para destacar slots vazios.
        """
        super().__init__()
        self.solitaire = solitaire
        self.pile = []
        self.type = slot_type
        self.width = 70
        self.height = 100
        self.left = left
        self.top = top
        self.bgcolor = "#2F7851"
        self.border_radius = ft.BorderRadius.all(6)
        self.border = border
        self.on_click = self.click

    def get_top_card(self):
        """
        Devolve a carta no topo da pilha.

        Returns:
            A ultima carta da pilha, ou `None` se o slot estiver vazio.
        """
        if len(self.pile) > 0:
            return self.pile[-1]
        return None

    def get_top_cards(self, count):
        """
        Devolve as `count` cartas mais acima da pilha.

        Args:
            count:
                Numero maximo de cartas a devolver.

        Returns:
            Lista com as cartas mais recentes do slot.
        """
        n = len(self.pile)
        return self.pile[max(0, n - count) :]

    def is_top_card(self, card):
        """
        Verifica se a carta recebida esta no topo do slot.

        Args:
            card:
                Carta a comparar.

        Returns:
            `True` se a carta for a ultima da pilha; caso contrario `False`.
        """
        return len(self.pile) > 0 and self.pile[-1] == card

    def upper_card_top(self):
        """
        Calcula o `top` da carta superior para validacao de drops.

        No tableau, a carta superior pode estar deslocada verticalmente em
        funcao do efeito de cascata. Nos restantes slots, o topo coincide com
        o topo do proprio slot.

        Returns:
            Coordenada `top` relevante para comparar distancia de drop.
        """
        if self.type == "tableau":
            if len(self.pile) > 1:
                return self.top + self.solitaire.card_offset * (len(self.pile) - 1)
        return self.top

    def click(self, e):
        """
        Trata o clique direto sobre o slot.

        Neste projeto, apenas o stock tem comportamento clicavel proprio:
        quando o stock esta vazio mas ainda existem passagens disponiveis, o
        clique recicla a waste de volta para o stock.
        """
        if self.type == "stock" and self.solitaire.deck_passes_remaining > 1:
            self.solitaire.save_undo_state()
            self.solitaire.deck_passes_remaining -= 1
            self.solitaire.recycle_waste_to_stock()
