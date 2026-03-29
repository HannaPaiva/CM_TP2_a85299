"""
Motor principal do tabuleiro de Solitaire.

Este modulo contem a modelacao do estado do jogo, regras de movimento,
pontuacao, historico de undo, restauracao de snapshots e adaptacao responsiva
do tabuleiro. O `GameBoard` e o centro da logica do projeto: as cartas e os
slots vivem aqui e a interface apenas orquestra o que deve ser mostrado.
"""

import copy
import random
from dataclasses import dataclass

import flet as ft

try:
    from .card import Card
    from .settings import Settings
    from .slot import Slot
except ImportError:
    from card import Card
    from settings import Settings
    from slot import Slot

STARTING_SCORE = 0
UNDO_LIMIT = 150


@dataclass(frozen=True)
class Suite:
    """
    Descreve um naipe do baralho.

    Attributes:
        name:
            Nome tecnico usado em IDs e assets.
        color:
            Cor logica do naipe para validacao de regras.
        label:
            Nome amigavel apresentado na documentacao.
    """

    name: str
    color: str
    label: str


@dataclass(frozen=True)
class Rank:
    """
    Descreve o valor de uma carta.

    Attributes:
        name:
            Nome textual do rank.
        value:
            Valor numerico usado nas comparacoes do jogo.
    """

    name: str
    value: int


SUITES = (
    Suite("hearts", "RED", "Copas"),
    Suite("diamonds", "RED", "Ouros"),
    Suite("clubs", "BLACK", "Paus"),
    Suite("spades", "BLACK", "Espadas"),
)

RANKS = (
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
)


class GameBoard(ft.Stack):
    """
    Stack Flet que representa o tabuleiro inteiro da partida.

    O tabuleiro gere:
    - criacao de slots e cartas;
    - distribuicao inicial;
    - regras de movimento;
    - historico de undo;
    - score, cronometro e mensagens de estado;
    - serializacao/restauro completo da partida;
    - ajuste responsivo de layout.
    """

    def __init__(self, page, settings, on_win, on_change):
        """
        Inicializa o tabuleiro e regista callbacks externos.

        Args:
            page:
                Pagina Flet dona do tabuleiro.
            settings:
                Configuracao inicial do jogo.
            on_win:
                Callback disparado quando a partida termina em vitoria.
            on_change:
                Callback disparado sempre que o estado observavel muda.
        """
        super().__init__()
        self.app_page = page
        self.settings = settings
        self.on_win = on_win
        self.on_change = on_change
        self.width = 1000
        self.height = 500
        self.current_top = 0
        self.current_left = 0
        self.card_width = 70
        self.card_height = 100
        self.card_offset = 20
        self.current_seed = None
        self.history = []
        self.initial_snapshot = None
        self.deck_passes_remaining = int(self.settings.deck_passes_allowed)
        self.score = STARTING_SCORE
        self.elapsed_seconds = 0
        self.status_message = ""
        self._game_won = False
        self.is_ready = False
        self.controls = []
        self.cards = []
        self.cards_by_id = {}
        self.foundation = []
        self.tableau = []
        self.all_slots = []

    def can_update(self):
        """
        Verifica se o controlo ainda esta ligado a uma pagina valida.

        Returns:
            `True` quando o tabuleiro pode chamar `update()` sem erro.
        """
        try:
            return self.page is not None
        except RuntimeError:
            return False

    def notify_change(self, autosave=False):
        """
        Propaga uma alteracao para a camada exterior.

        Args:
            autosave:
                Indica se a mudanca justifica gravacao automatica do estado.
        """
        if self.on_change is not None:
            self.on_change(autosave=autosave)

    def set_status(self, message, autosave=False, update_board=False):
        """
        Atualiza a mensagem de estado publicada para a interface.

        Args:
            message:
                Texto curto apresentado ao utilizador.
            autosave:
                Se `True`, a camada superior pode persistir a alteracao.
            update_board:
                Se `True`, o controlo atualiza-se imediatamente.
        """
        self.status_message = message
        if update_board and self.can_update():
            self.update()
        self.notify_change(autosave=autosave)

    def setup(self):
        """
        Constroi a estrutura do tabuleiro na primeira utilizacao.

        O metodo e idempotente: se o tabuleiro ja tiver sido preparado,
        chamadas repetidas nao fazem nada.
        """
        if self.is_ready:
            return
        self.create_slots()
        self.create_card_deck()
        self.is_ready = True
        self.start_new_game(announce=False)

    def create_slots(self):
        """
        Cria stock, waste, fundacoes e tableau.

        O conjunto de slots e tambem guardado em `all_slots` para facilitar
        resets e atualizacoes de layout.
        """
        slot_border = ft.Border.all(1, self.settings.theme["slot_border"])
        self.stock = Slot(self, "stock", top=0, left=0, border=slot_border)
        self.waste = Slot(self, "waste", top=0, left=100, border=None)
        self.foundation = [
            Slot(self, "foundation", top=0, left=300 + (index * 100), border=slot_border)
            for index in range(4)
        ]
        self.tableau = [
            Slot(self, "tableau", top=150, left=index * 100, border=None)
            for index in range(7)
        ]
        self.all_slots = [self.stock, self.waste, *self.foundation, *self.tableau]
        self.controls = list(self.all_slots)
        self.apply_visual_preferences(update=False)

    def create_card_deck(self):
        """
        Gera as 52 cartas do baralho e indexa-as por ID.
        """
        self.cards = []
        self.cards_by_id = {}
        for suite in SUITES:
            for rank in RANKS:
                card = Card(solitaire=self, suite=suite, rank=rank)
                self.cards.append(card)
                self.cards_by_id[card.card_id] = card
        self.controls.extend(self.cards)

    def reset_board_state(self):
        """
        Limpa completamente as pilhas e repoe todas as cartas a face para baixo.
        """
        for slot in self.all_slots:
            slot.pile.clear()
        for card in self.cards:
            card.slot = None
            card.visible = True
            card.turn_face_down(notify=False)

    def reset_game_progress(self):
        """
        Repoe score, cronometro, undo e passes de stock.
        """
        self.settings.apply_difficulty(self.settings.difficulty)
        self.deck_passes_remaining = int(self.settings.deck_passes_allowed)
        self.score = STARTING_SCORE
        self.elapsed_seconds = 0
        self.history.clear()
        self._game_won = False

    def start_new_game(self, announce=True):
        """
        Inicia uma nova partida a partir de um baralho embaralhado.

        Args:
            announce:
                Se `True`, publica mensagem de estado visivel ao utilizador.
        """
        self.reset_game_progress()
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
        """
        Reinicia a partida atual para a distribuicao inicial.

        Ao contrario de `start_new_game()`, este metodo nao gera uma nova seed:
        ele restaura exatamente o primeiro estado distribuido desta ronda.
        """
        if self.initial_snapshot is None:
            self.set_status("Nao existe uma partida para reiniciar.")
            return
        self.restore_state(
            copy.deepcopy(self.initial_snapshot),
            clear_history=True,
            set_initial=False,
            announce=False,
        )
        self.set_status("Partida reiniciada a partir da distribuicao inicial.")

    def deal_cards(self, deck):
        """
        Distribui o baralho segundo as regras do Klondike.

        Args:
            deck:
                Lista de cartas ja embaralhada.
        """
        card_index = 0
        first_slot = 0
        while card_index <= 27:
            for slot_index in range(first_slot, len(self.tableau)):
                deck[card_index].place(self.tableau[slot_index])
                card_index += 1
            first_slot += 1
        for slot in self.tableau:
            slot.get_top_card().turn_face_up(notify=False)
        for card in deck[28:]:
            card.place(self.stock)

    def save_undo_state(self):
        """
        Guarda um snapshot para permitir `undo`.

        O historico e truncado a `UNDO_LIMIT` para evitar crescimento sem fim.
        """
        self.history.append(self.capture_state(include_initial=False))
        if len(self.history) > UNDO_LIMIT:
            self.history.pop(0)

    def handle_tableau_reveal(self, notify=False):
        """
        Aplica os efeitos secundarios de revelar uma carta do tableau.

        Args:
            notify:
                Se `True`, publica mensagem de estado imediata.
        """
        self.score += 5
        if notify:
            self.set_status("Carta revelada no tableau.")

    def finish_move(self, old_slot, new_slot):
        """
        Fecha um movimento bem-sucedido entre slots.

        Responsabilidades:
        - revelar nova carta do tableau, quando aplicavel;
        - atualizar waste visivel;
        - aplicar score;
        - verificar vitoria;
        - disparar autosave e callback de vitoria.

        Args:
            old_slot:
                Slot de origem.
            new_slot:
                Slot de destino.
        """
        if old_slot.type == "tableau" and old_slot.pile:
            old_slot.get_top_card().turn_face_up()
            self.handle_tableau_reveal()
        elif old_slot.type == "waste":
            self.display_waste()

        self.apply_score_for_move(old_slot.type, new_slot.type)
        just_won = False
        if self.check_if_you_won():
            just_won = not self._game_won
            self._game_won = True
        self.notify_change(autosave=True)
        if just_won and self.on_win is not None:
            self.on_win()

    def undo_move(self):
        """
        Restaura o ultimo snapshot do historico.
        """
        if not self.history:
            self.set_status("Nao ha jogadas para desfazer.")
            return
        snapshot = self.history.pop()
        self.restore_state(snapshot, clear_history=False, set_initial=False, announce=False)
        self.set_status("Ultima jogada desfeita.", autosave=True)

    def capture_state(self, include_initial=True):
        """
        Serializa o estado completo do tabuleiro.

        Args:
            include_initial:
                Se `True`, inclui tambem a distribuicao inicial da ronda.

        Returns:
            Dicionario pronto para persistencia local ou DuckDB.
        """
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
        """
        Restaura o tabuleiro a partir de um snapshot persistido.

        Args:
            snapshot:
                Dicionario produzido por `capture_state()`.
            clear_history:
                Se `True`, apaga o historico de undo apos o restauro.
            set_initial:
                Se `True`, redefine tambem a snapshot inicial da ronda.
            announce:
                Se `True`, publica mensagem de estado ao utilizador.
        """
        restored_settings = Settings.from_dict(snapshot.get("settings", {}))
        restored_settings.card_back_name = self.settings.card_back_name
        restored_settings.theme_name = self.settings.theme_name
        restored_settings.board_bg_style = getattr(self.settings, "board_bg_style", "theme_color")
        restored_settings.board_bg_target = getattr(self.settings, "board_bg_target", "")
        self.settings = restored_settings
        self.deck_passes_remaining = int(
            snapshot.get("deck_passes_remaining", self.settings.deck_passes_allowed)
        )
        self.score = int(snapshot.get("score", STARTING_SCORE))
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
            if initial_state is not None:
                self.initial_snapshot = copy.deepcopy(initial_state)
            else:
                self.initial_snapshot = self.capture_state(include_initial=False)

        self.apply_visual_preferences(update=False)
        self.display_waste(update=False)
        if self.can_update():
            self.update()
        if announce:
            self.set_status("Estado da partida restaurado.")
        else:
            self.notify_change()

    def draw_from_stock(self):
        """
        Compra cartas do stock para a waste.
        """
        if not self.stock.pile:
            self.set_status("O stock esta vazio.")
            return

        self.save_undo_state()
        for card in self.waste.get_top_cards(self.settings.waste_size):
            card.visible = False
        for _ in range(min(self.settings.waste_size, len(self.stock.pile))):
            top_card = self.stock.pile[-1]
            top_card.place(self.waste)
            top_card.turn_face_up()
        self.display_waste()
        self.notify_change(autosave=True)

    def recycle_waste_to_stock(self):
        """
        Recicla a waste de volta para o stock.
        """
        self.waste.pile.reverse()
        while self.waste.pile:
            card = self.waste.pile[0]
            card.turn_face_down()
            card.place(self.stock)
        self.score -= 20
        self.notify_change(autosave=True)

    def move_on_top(self, cards_to_drag, update=True):
        """
        Move cartas para o topo visual do stack.

        Isto garante que as cartas arrastadas ficam sempre visiveis acima das
        restantes durante a interacao.
        """
        for card in cards_to_drag:
            if card in self.controls:
                self.controls.remove(card)
                self.controls.append(card)
        if update and self.can_update():
            self.update()

    def bounce_back(self, cards):
        """
        Reposiciona cartas arrastadas para a localizacao original.
        """
        for index, card in enumerate(cards):
            card.top = self.current_top
            if card.slot.type == "tableau":
                card.top += index * self.card_offset
            card.left = self.current_left

    def display_waste(self, update=True):
        """
        Atualiza a apresentacao das cartas da waste.

        O numero de cartas visiveis depende da dificuldade. Quando a compra e
        de tres cartas, as cartas visiveis recebem um pequeno deslocamento
        horizontal para simular o leque classico.
        """
        visible_count = 2 if self.settings.waste_size == 1 else self.settings.waste_size
        visible_cards = self.waste.get_top_cards(visible_count)
        first_visible = len(self.waste.pile) - len(visible_cards)

        for index, card in enumerate(self.waste.pile):
            card.top = self.waste.top
            card.left = self.waste.left
            card.visible = index >= first_visible
            if card.visible and self.settings.waste_size == 3:
                card.left += self.card_offset * (index - first_visible)

        self.move_on_top(visible_cards, update=False)
        if update and self.can_update():
            self.update()

    def auto_win(self):
        """
        Forca o tabuleiro para um estado de vitoria.

        A funcionalidade e usada pelo gesto de shake. O metodo guarda undo,
        move logicamente todas as cartas para as fundacoes, marca a partida
        como vencida e dispara o callback de comemoracao.
        """
        if self._game_won:
            return

        self.save_undo_state()
        snapshot = self.capture_state(include_initial=True)
        snapshot["stock"] = []
        snapshot["waste"] = []
        snapshot["tableau"] = [[] for _ in self.tableau]
        snapshot["foundation"] = [
            [f"{rank.name}_{suite.name}" for rank in RANKS]
            for suite in SUITES
        ]
        snapshot["face_up"] = {card.card_id: True for card in self.cards}
        snapshot["game_won"] = True

        self.restore_state(
            snapshot,
            clear_history=False,
            set_initial=False,
            announce=False,
        )
        self._game_won = True
        self.set_status("Vitoria automatica ativada.", autosave=True)
        if self.on_win is not None:
            self.on_win()

    def apply_score_for_move(self, source_type, target_type):
        """
        Aplica as regras de score para um movimento concluido.

        Args:
            source_type:
                Tipo do slot de origem.
            target_type:
                Tipo do slot de destino.
        """
        if target_type == "foundation" and source_type in ("waste", "tableau"):
            self.score += 10
        elif target_type == "tableau" and source_type == "waste":
            self.score += 5
        elif source_type == "foundation" and target_type == "tableau":
            self.score -= 15

    def check_foundation_rules(self, current_card, top_card=None):
        """
        Valida se uma carta pode entrar numa fundacao.

        Returns:
            `True` se a jogada cumprir as regras do Klondike.
        """
        if top_card is not None:
            return (
                current_card.suite.name == top_card.suite.name
                and current_card.rank.value - top_card.rank.value == 1
            )
        return current_card.rank.name == "Ace"

    def check_tableau_rules(self, current_card, top_card=None):
        """
        Valida se uma carta pode ser colocada no tableau.

        Returns:
            `True` se a carta alternar cor e descer exatamente um valor.
        """
        if top_card is not None:
            return (
                current_card.suite.color != top_card.suite.color
                and top_card.rank.value - current_card.rank.value == 1
            )
        return current_card.rank.name == "King"

    def check_if_you_won(self):
        """
        Verifica se as quatro fundacoes ja contem as 52 cartas.

        Returns:
            `True` quando a partida foi concluida.
        """
        return sum(len(slot.pile) for slot in self.foundation) == 52

    def format_elapsed(self):
        """
        Formata o cronometro acumulado para apresentacao.

        Returns:
            String no formato `MM:SS` ou `HH:MM:SS`.
        """
        minutes, seconds = divmod(self.elapsed_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    def apply_visual_preferences(self, update=True):
        """
        Recalcula dimensoes e coordenadas conforme o tamanho da pagina.

        Este metodo torna o tabuleiro responsivo, adaptando:
        - largura/altura das cartas;
        - offset vertical do tableau;
        - distancia entre colunas;
        - dimensao total do stack.
        """
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

        for index, slot in enumerate(self.foundation):
            slot.left = int((3 + index) * col_unit)
            slot.top = 0
        for index, slot in enumerate(self.tableau):
            slot.left = int(index * col_unit)
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
            if card.slot is None:
                continue
            card.left = card.slot.left
            if card.slot.type == "tableau":
                card.top = card.slot.top + self.card_offset * card.slot.pile.index(card)
            else:
                card.top = card.slot.top

        if update and self.can_update():
            self.update()

    def refresh_layout(self, update=True):
        """
        Atalho semantico para reaplicar o layout responsivo.
        """
        self.apply_visual_preferences(update=update)
