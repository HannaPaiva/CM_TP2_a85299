from dataclasses import dataclass

UNLIMITED_PASSES = 1000

BACK_OPTIONS = {
    "classic": {
        "label": "Classic",
        "asset": "solitaire/assets/backs/classic.svg",
        "suggested_theme": "classic",
    },
    "forest": {
        "label": "Forest",
        "asset": "solitaire/assets/backs/forest.svg",
        "suggested_theme": "forest",
    },
    "ocean": {
        "label": "Ocean",
        "asset": "solitaire/assets/backs/ocean.svg",
        "suggested_theme": "ocean",
    },
    "sunrise": {
        "label": "Sunrise",
        "asset": "solitaire/assets/backs/sunrise.svg",
        "suggested_theme": "sunrise",
    },
}

THEME_OPTIONS = {
    "classic": {
        "label": "Classic Green",
        "page_bg": "#08140E",
        "header_bg": "#10291D",
        "panel_bg": "#153221",
        "panel_bg_alt": "#1C412C",
        "board_bg": "#1E6B42",
        "board_bg_alt": "#175536",
        "chip_bg": "#244F37",
        "slot_bg": "#2F7851",
        "slot_border": "#8ED0A7",
        "text": "#F2F3EA",
        "muted": "#C9D4C8",
        "accent": "#F1CE6E",
    },
    "forest": {
        "label": "Forest Moss",
        "page_bg": "#0A1711",
        "header_bg": "#13271D",
        "panel_bg": "#183126",
        "panel_bg_alt": "#214436",
        "board_bg": "#2D5B43",
        "board_bg_alt": "#224633",
        "chip_bg": "#335A45",
        "slot_bg": "#3A6A51",
        "slot_border": "#B2D39D",
        "text": "#F5F8EF",
        "muted": "#CFD8C6",
        "accent": "#C7D98E",
    },
    "ocean": {
        "label": "Ocean Blue",
        "page_bg": "#081822",
        "header_bg": "#103043",
        "panel_bg": "#123A51",
        "panel_bg_alt": "#184C66",
        "board_bg": "#1F6B8C",
        "board_bg_alt": "#17546D",
        "chip_bg": "#2D5F79",
        "slot_bg": "#3A7B9C",
        "slot_border": "#9FD5EA",
        "text": "#F1F7FA",
        "muted": "#C9DCE5",
        "accent": "#8ED7F4",
    },
    "sunrise": {
        "label": "Sunrise Copper",
        "page_bg": "#26120B",
        "header_bg": "#4A2310",
        "panel_bg": "#5A2E17",
        "panel_bg_alt": "#714124",
        "board_bg": "#A05427",
        "board_bg_alt": "#7F4120",
        "chip_bg": "#8A4D2A",
        "slot_bg": "#B36A3B",
        "slot_border": "#F5C07A",
        "text": "#FFF7ED",
        "muted": "#F3D7B2",
        "accent": "#FFD082",
    },
}

DIFFICULTY_PRESETS = {
    "easy": {
        "label": "Facil",
        "waste_size": 1,
        "deck_passes_allowed": UNLIMITED_PASSES,
        "description": "Compra 1 carta e passagens livres pelo stock.",
    },
    "classic": {
        "label": "Classico",
        "waste_size": 3,
        "deck_passes_allowed": UNLIMITED_PASSES,
        "description": "Compra 3 cartas e passagens livres pelo stock.",
    },
    "hard": {
        "label": "Dificil",
        "waste_size": 3,
        "deck_passes_allowed": 3,
        "description": "Compra 3 cartas e apenas 3 passagens pelo stock.",
    },
}

GAME_MODES = {
    "classic": {
        "label": "Classico",
        "description": "Pontuacao tradicional inspirada no Solitaire do Windows.",
        "starting_score": 0,
    },
    "vegas": {
        "label": "Vegas",
        "description": "Cada fundacao vale dinheiro e a partida comeca em -52.",
        "starting_score": -52,
    },
}


@dataclass
class Settings:
    difficulty: str = "easy"
    game_mode: str = "classic"
    card_back_name: str = "classic"
    theme_name: str = "classic"
    waste_size: int = 1
    deck_passes_allowed: int = UNLIMITED_PASSES

    def __post_init__(self):
        self.apply_difficulty(self.difficulty)

    def apply_difficulty(self, difficulty):
        preset = DIFFICULTY_PRESETS.get(difficulty, DIFFICULTY_PRESETS["classic"])
        self.difficulty = difficulty if difficulty in DIFFICULTY_PRESETS else "classic"
        self.waste_size = int(preset["waste_size"])
        self.deck_passes_allowed = int(preset["deck_passes_allowed"])

    @property
    def card_back(self):
        return BACK_OPTIONS[self.card_back_name]["asset"]

    @property
    def theme(self):
        return THEME_OPTIONS[self.theme_name]

    @property
    def difficulty_label(self):
        return DIFFICULTY_PRESETS[self.difficulty]["label"]

    @property
    def mode_label(self):
        return GAME_MODES[self.game_mode]["label"]

    def to_dict(self):
        return {
            "difficulty": self.difficulty,
            "game_mode": self.game_mode,
            "card_back_name": self.card_back_name,
            "theme_name": self.theme_name,
            "waste_size": self.waste_size,
            "deck_passes_allowed": self.deck_passes_allowed,
        }

    @classmethod
    def from_dict(cls, data):
        settings = cls(
            difficulty=str(data.get("difficulty", "classic")),
            game_mode=str(data.get("game_mode", "classic")),
            card_back_name=str(
                data.get("card_back_name", data.get("card_back", "classic"))
            ),
            theme_name=str(data.get("theme_name", "classic")),
        )

        if settings.card_back_name not in BACK_OPTIONS:
            settings.card_back_name = "classic"
        if settings.theme_name not in THEME_OPTIONS:
            settings.theme_name = "classic"
        if settings.game_mode not in GAME_MODES:
            settings.game_mode = "classic"

        return settings
