"""
Componente visual e interativo de cada carta do jogo.

O objeto `Card` acumula duas responsabilidades principais:

1. representar a carta no ecra como um `GestureDetector`;
2. servir de ponte entre os gestos do utilizador e a logica do `GameBoard`.

Cada carta conhece o naipe, o rank, o slot em que se encontra e o seu estado
de face para cima/baixo, o que permite tratar drag-and-drop, clique simples,
duplo clique e restauracao a partir de snapshots.
"""

import flet as ft
import time

try:
    from .settings import BACK_OPTIONS
except ImportError:
    from settings import BACK_OPTIONS


class Card(ft.GestureDetector):
    """
    Representa uma carta individual do baralho no tabuleiro.

    A carta e simultaneamente um elemento visual e uma unidade de estado.
    Quando arrastada, clicada ou restaurada a partir de persistencia, a carta
    atualiza a propria imagem e notifica o tabuleiro atraves dos metodos de
    apoio.
    """

    def __init__(self, solitaire, suite, rank):
        """
        Constroi a carta e liga os handlers de gesto.

        Args:
            solitaire:
                Referencia ao `GameBoard` que gere a partida.
            suite:
                Objeto `Suite` que identifica o naipe da carta.
            rank:
                Objeto `Rank` que identifica o valor da carta.
        """
        super().__init__()
        self.solitaire = solitaire
        self.suite = suite
        self.rank = rank
        self.card_id = f"{self.rank.name}_{self.suite.name}"
        self.face_up = False
        self.slot = None
        self._dragging_cards = []
        self._pending_drag_dx = 0.0
        self._pending_drag_dy = 0.0
        self._last_drag_flush = 0.0
        self.mouse_cursor = ft.MouseCursor.MOVE
        self.drag_interval = 33
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
        self.apply_image_preferences()

    def apply_image_preferences(self):
        """
        Ajusta `fit` e `scale` da imagem da carta.

        Quando a carta esta virada para cima, a imagem da face usa o tamanho
        natural. Quando esta virada para baixo, o metodo le as preferencias do
        verso selecionado para manter consistencia visual com o tema ativo.
        """
        image = self.content.content
        if self.face_up:
            image.fit = None
            image.scale = 1.0
            return

        back_data = BACK_OPTIONS.get(self.solitaire.settings.card_back_name, {})
        fit_name = str(back_data.get("fit", "cover")).lower()
        fit_lookup = {
            "cover": ft.BoxFit.COVER,
            "contain": ft.BoxFit.CONTAIN,
            "fill": ft.BoxFit.FILL,
        }
        image.fit = fit_lookup.get(fit_name, ft.BoxFit.COVER)
        try:
            scale = float(back_data.get("scale", 1.0))
        except (TypeError, ValueError):
            scale = 1.0
        image.scale = max(0.85, min(1.75, scale))

    def sync_size(self):
        """
        Reajusta dimensoes da carta apos alteracoes de layout responsivo.

        O tabuleiro recalcula `card_width`, `card_height` e `card_offset`
        sempre que a janela muda de tamanho. Este metodo propaga esses novos
        valores para a carta e para a imagem interna.
        """
        self.content.width = self.solitaire.card_width
        self.content.height = self.solitaire.card_height
        self.content.border_radius = ft.BorderRadius.all(6)
        self.content.content.width = self.solitaire.card_width
        self.content.content.height = self.solitaire.card_height
        self.apply_image_preferences()

    def set_face(self, face_up, notify=True):
        """
        Troca explicitamente o estado da face da carta.

        Args:
            face_up:
                `True` para mostrar a frente da carta, `False` para mostrar o
                verso configurado.
            notify:
                Se `True`, o tabuleiro sera atualizado no fim da operacao.
        """
        self.face_up = bool(face_up)
        if self.face_up:
            self.content.content.src = f"images/{self.card_id}.svg"
        else:
            self.content.content.src = self.solitaire.settings.card_back
        self.apply_image_preferences()
        if notify and self.solitaire.can_update():
            self.solitaire.update()

    def turn_face_up(self, notify=True):
        """
        Atalho semantico para virar a carta para cima.

        Args:
            notify:
                Indica se o tabuleiro deve ser atualizado imediatamente.
        """
        self.set_face(True, notify=notify)

    def turn_face_down(self, notify=True):
        """
        Atalho semantico para virar a carta para baixo.

        Args:
            notify:
                Indica se o tabuleiro deve ser atualizado imediatamente.
        """
        self.set_face(False, notify=notify)

    def can_be_moved(self):
        """
        Determina se a carta pode ser movida no estado atual.

        Regras aplicadas:
        - cartas viradas para cima no tableau podem ser movidas;
        - na waste, apenas a carta do topo e movivel;
        - cartas sem slot nao participam em interacao.

        Returns:
            `True` se a carta puder iniciar movimento; caso contrario `False`.
        """
        if self.slot is None:
            return False
        if self.face_up and self.slot.type != "waste":
            return True
        if self.slot.type == "waste" and self.slot.is_top_card(self):
            return True
        return False

    def start_drag(self, e: ft.DragStartEvent):
        """
        Inicia o arrasto da carta e do bloco associado.

        Para cartas do tableau, o arrasto pode incluir a carta selecionada e
        todas as cartas abaixo dela. O metodo memoriza tambem a posicao inicial
        para permitir o efeito de `bounce back` caso o drop seja invalido.
        """
        if self.can_be_moved():
            self._dragging_cards = self.get_cards_to_move()
            self._pending_drag_dx = 0.0
            self._pending_drag_dy = 0.0
            self._last_drag_flush = 0.0
            self.solitaire.is_dragging = True
            self.solitaire.current_top = e.control.top
            self.solitaire.current_left = e.control.left

    def _flush_drag_delta(self, force=False):
        """
        Aplica o delta acumulado do arrasto numa unica atualizacao visual.

        Durante o gesto, o Flet pode emitir varios eventos muito proximos entre
        si. Agrupar pequenos deltas reduz o numero de redraws sem alterar a
        logica do drop.
        """
        if not self._dragging_cards:
            return

        dx = self._pending_drag_dx
        dy = self._pending_drag_dy
        if not force:
            if abs(dx) < 1 and abs(dy) < 1:
                return
            now = time.monotonic()
            flush_interval = 0.03 if len(self._dragging_cards) == 1 else 0.045
            distance = abs(dx) + abs(dy)
            if self._last_drag_flush and now - self._last_drag_flush < flush_interval and distance < 6:
                return
            self._last_drag_flush = now
        elif dx == 0 and dy == 0:
            return

        self._pending_drag_dx = 0.0
        self._pending_drag_dy = 0.0
        for card in self._dragging_cards:
            card.top = max(0, card.top + dy)
            card.left = max(0, card.left + dx)

        if len(self._dragging_cards) == 1:
            self._dragging_cards[0].update()
        elif self.solitaire.can_update():
            update_controls = getattr(self.solitaire, "update_controls", None)
            if callable(update_controls):
                update_controls(*self._dragging_cards)
            else:
                self.solitaire.update()

    def drag(self, e: ft.DragUpdateEvent):
        """
        Atualiza a posicao das cartas durante o arrasto.

        Args:
            e:
                Evento de arrasto emitido pelo Flet, contendo o delta local.
        """
        if self.can_be_moved() and self._dragging_cards:
            self._pending_drag_dx += e.local_delta.x
            self._pending_drag_dy += e.local_delta.y
            self._flush_drag_delta(force=False)

    def drop(self, e: ft.DragEndEvent):
        """
        Finaliza o arrasto e tenta aplicar um movimento valido.

        O metodo percorre tableau e fundacoes, verifica proximidade visual e
        valida as regras de colocacao. Quando encontra um alvo valido, guarda o
        estado para `undo`, move as cartas e delega o fecho do movimento ao
        tabuleiro. Se nenhum alvo servir, devolve as cartas a posicao inicial.
        """
        try:
            if self.can_be_moved():
                self._flush_drag_delta(force=True)
                cards_to_drag = self._dragging_cards
                self.solitaire.move_on_top(cards_to_drag, update=False)
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
                            self.solitaire.save_undo_state()
                            old_slot = self.slot
                            for card in cards_to_drag:
                                card.place(slot, update=False, bring_to_front=False)
                            self.solitaire.move_on_top(cards_to_drag, update=False)
                            self.solitaire.finish_move(old_slot, slot, update_board=False)
                            if self.solitaire.can_update():
                                self.solitaire.update()
                            return

                self.solitaire.bounce_back(cards_to_drag)
                if self.solitaire.can_update():
                    self.solitaire.update()
        finally:
            self.solitaire.is_dragging = False
            self._pending_drag_dx = 0.0
            self._pending_drag_dy = 0.0
            self._last_drag_flush = 0.0
            self._dragging_cards = []

    def doubleclick(self, e):
        """
        Tenta mover automaticamente a carta para uma fundacao.

        O duplo clique e suportado para cartas viradas para cima vindas da
        waste ou do tableau. Se nenhuma fundacao aceitar a carta, o estado de
        undo que tinha sido criado e removido para nao poluir o historico.
        """
        if self.slot is not None and self.slot.type in ("waste", "tableau"):
            if self.face_up:
                self.solitaire.save_undo_state()
                self.solitaire.move_on_top([self], update=False)
                old_slot = self.slot
                for slot in self.solitaire.foundation:
                    if self.solitaire.check_foundation_rules(self, slot.get_top_card()):
                        self.place(slot, update=False, bring_to_front=False)
                        self.solitaire.move_on_top([self], update=False)
                        self.solitaire.finish_move(old_slot, slot, update_board=False)
                        if self.solitaire.can_update():
                            self.solitaire.update()
                        return
                self.solitaire.history.pop() if self.solitaire.history else None

    def click(self, e):
        """
        Trata o clique simples sobre a carta.

        Comportamentos suportados:
        - clique na carta do stock compra cartas;
        - clique na ultima carta tapada do tableau revela-a.
        """
        if self.slot is None:
            return
        if self.slot.type == "stock":
            self.solitaire.draw_from_stock()
        if self.slot.type == "tableau":
            if self.face_up is False and self.slot.is_top_card(self):
                self.solitaire.save_undo_state()
                self.turn_face_up()
                self.solitaire.handle_tableau_reveal()

    def place(self, slot, update=True, bring_to_front=True):
        """
        Coloca a carta num novo slot e atualiza coordenadas.

        Este metodo e usado tanto em movimentos interativos quanto em
        restauracao de snapshots. A logica inclui reposicionamento no tableau,
        remocao do slot anterior, insercao no novo slot e reordenacao no topo
        visual do `Stack`.

        Args:
            slot:
                Novo slot de destino.
            update:
                Se `True`, atualiza imediatamente o tabuleiro; caso contrario,
                o chamador pode agrupar varias mudancas numa unica renderizacao.
            bring_to_front:
                Se `True`, reordena a carta para o topo visual do stack.
        """
        self.top = slot.top
        self.left = slot.left
        if slot.type == "tableau":
            self.top += self.solitaire.card_offset * len(slot.pile)

        if self.slot is not None:
            self.slot.pile.remove(self)

        self.slot = slot
        slot.pile.append(self)
        if bring_to_front:
            self.solitaire.move_on_top([self], update=False)
        if update and self.solitaire.can_update():
            self.solitaire.update()

    def get_cards_to_move(self):
        """
        Resolve o conjunto de cartas que acompanha esta carta num arrasto.

        Returns:
            Se a carta estiver no tableau, devolve a subpilha a partir dela.
            Caso contrario, devolve apenas a propria carta.
        """
        if self.slot is not None:
            return self.slot.pile[self.slot.pile.index(self) :]
        return [self]
