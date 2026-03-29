import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CUSTOM_THEMES_FILE = PROJECT_ROOT / "solitaire" / "custom_themes.json"
CUSTOM_BACKS_DIR = PROJECT_ROOT / "assets" / "backs" / "custom"
CUSTOM_BOARDS_DIR = PROJECT_ROOT / "assets" / "boards"
RESERVED_THEME_NAMES = {"classic", "forest", "ocean", "sunrise"}
SUPPORTED_BACK_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def _clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def _normalize_hex(value, fallback):
    raw = str(value or "").strip().lstrip("#")
    if len(raw) == 3 and all(ch in "0123456789abcdefABCDEF" for ch in raw):
        raw = "".join(ch * 2 for ch in raw)
    if len(raw) != 6 or not all(ch in "0123456789abcdefABCDEF" for ch in raw):
        return fallback.upper()
    return f"#{raw.upper()}"


def _hex_to_rgb(value):
    value = _normalize_hex(value, "#000000").lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def _rgb_to_hex(red, green, blue):
    return "#{:02X}{:02X}{:02X}".format(
        _clamp(int(round(red)), 0, 255),
        _clamp(int(round(green)), 0, 255),
        _clamp(int(round(blue)), 0, 255),
    )


def mix_colors(primary, secondary, ratio):
    ratio = _clamp(float(ratio), 0.0, 1.0)
    p_red, p_green, p_blue = _hex_to_rgb(primary)
    s_red, s_green, s_blue = _hex_to_rgb(secondary)
    return _rgb_to_hex(
        p_red * (1 - ratio) + s_red * ratio,
        p_green * (1 - ratio) + s_green * ratio,
        p_blue * (1 - ratio) + s_blue * ratio,
    )


def lighten(color, amount):
    return mix_colors(color, "#FFFFFF", amount)


def darken(color, amount):
    return mix_colors(color, "#000000", amount)


def build_theme_palette(label, base_color, surface_color, accent_color, use_light_text=True):
    base_color = _normalize_hex(base_color, "#1E6B42")
    surface_color = _normalize_hex(surface_color, "#153221")
    accent_color = _normalize_hex(accent_color, "#F1CE6E")
    text_color = "#F7F7F2" if use_light_text else "#152016"
    muted_mix = 0.28 if use_light_text else 0.36
    return {
        "label": str(label or "Tema Personalizado").strip() or "Tema Personalizado",
        "page_bg": darken(base_color, 0.78),
        "header_bg": darken(surface_color, 0.24),
        "panel_bg": darken(surface_color, 0.08),
        "panel_bg_alt": lighten(surface_color, 0.08),
        "board_bg": base_color,
        "board_bg_alt": darken(base_color, 0.18),
        "chip_bg": mix_colors(surface_color, base_color, 0.42),
        "slot_bg": lighten(base_color, 0.12),
        "slot_border": lighten(accent_color, 0.18),
        "text": text_color,
        "muted": mix_colors(text_color, base_color, muted_mix),
        "accent": accent_color,
        "custom": True,
    }


def _sanitize_back_entry(name, payload):
    asset = str(payload.get("asset", "")).replace("\\", "/").lstrip("/")
    if not asset:
        return None
    asset_path = PROJECT_ROOT / "assets" / asset
    if not asset_path.exists():
        return None
    fit = str(payload.get("fit", "cover")).lower()
    if fit not in {"cover", "contain", "fill"}:
        fit = "cover"
    try:
        scale = float(payload.get("scale", 1.0))
    except (TypeError, ValueError):
        scale = 1.0

    # Optional per-theme board background image
    board_bg = None
    raw_board_bg = str(payload.get("board_bg", "") or "").replace("\\", "/").lstrip("/")
    if raw_board_bg:
        board_bg_path = PROJECT_ROOT / "assets" / raw_board_bg
        if board_bg_path.exists():
            board_bg = raw_board_bg

    return {
        "label": str(payload.get("label", name)).strip() or str(name),
        "asset": asset,
        "suggested_theme": str(payload.get("suggested_theme", name)),
        "fit": fit,
        "scale": round(_clamp(scale, 0.85, 1.75), 2),
        "board_bg": board_bg,
        "custom": True,
    }


def _sanitize_theme_entry(name, payload):
    return {
        "label": str(payload.get("label", name)).strip() or str(name),
        "page_bg": _normalize_hex(payload.get("page_bg"), "#08140E"),
        "header_bg": _normalize_hex(payload.get("header_bg"), "#10291D"),
        "panel_bg": _normalize_hex(payload.get("panel_bg"), "#153221"),
        "panel_bg_alt": _normalize_hex(payload.get("panel_bg_alt"), "#1C412C"),
        "board_bg": _normalize_hex(payload.get("board_bg"), "#1E6B42"),
        "board_bg_alt": _normalize_hex(payload.get("board_bg_alt"), "#175536"),
        "chip_bg": _normalize_hex(payload.get("chip_bg"), "#244F37"),
        "slot_bg": _normalize_hex(payload.get("slot_bg"), "#2F7851"),
        "slot_border": _normalize_hex(payload.get("slot_border"), "#8ED0A7"),
        "text": _normalize_hex(payload.get("text"), "#F2F3EA"),
        "muted": _normalize_hex(payload.get("muted"), "#C9D4C8"),
        "accent": _normalize_hex(payload.get("accent"), "#F1CE6E"),
        "custom": True,
    }


def _load_raw_bundle():
    if not CUSTOM_THEMES_FILE.exists():
        return {}
    try:
        return json.loads(CUSTOM_THEMES_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def load_custom_theme_bundle():
    raw_payload = _load_raw_bundle()

    themes = {}
    backs = {}
    raw_themes = raw_payload.get("themes", {})
    raw_backs = raw_payload.get("backs", {})
    if isinstance(raw_themes, dict):
        for name, payload in raw_themes.items():
            sanitized = _sanitize_theme_entry(name, payload or {})
            themes[str(name)] = sanitized
    if isinstance(raw_backs, dict):
        for name, payload in raw_backs.items():
            sanitized = _sanitize_back_entry(name, payload or {})
            if sanitized is not None:
                backs[str(name)] = sanitized
    themes = {name: data for name, data in themes.items() if name in backs}
    backs = {name: data for name, data in backs.items() if name in themes}
    return {"themes": themes, "backs": backs}


def _save_custom_theme_bundle(bundle):
    """Save themes/backs while preserving all other top-level keys."""
    CUSTOM_THEMES_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing = _load_raw_bundle()
    existing["themes"] = bundle.get("themes", {})
    existing["backs"] = bundle.get("backs", {})
    CUSTOM_THEMES_FILE.write_text(
        json.dumps(existing, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )


def _slugify_theme_name(label):
    slug = re.sub(r"[^a-z0-9]+", "_", str(label).strip().lower()).strip("_")
    return slug or "tema_personalizado"


def _save_board_bg_file(theme_name, image_bytes, original_filename):
    """Save a board bg image for a theme. Returns the asset-relative path."""
    if not image_bytes:
        return None
    extension = Path(str(original_filename or "")).suffix.lower()
    if extension not in SUPPORTED_BACK_EXTENSIONS:
        extension = ".jpg"
    CUSTOM_BOARDS_DIR.mkdir(parents=True, exist_ok=True)
    file_name = f"{theme_name}_board{extension}"
    (CUSTOM_BOARDS_DIR / file_name).write_bytes(image_bytes)
    return f"boards/{file_name}"


def save_custom_theme_bundle(
    label,
    base_color,
    surface_color,
    accent_color,
    use_light_text,
    image_bytes,
    original_filename,
    image_scale,
    board_bg_bytes=None,
    board_bg_filename=None,
):
    if not image_bytes:
        raise ValueError("Escolhe uma imagem para o verso da carta.")

    extension = Path(str(original_filename or "")).suffix.lower()
    if extension not in SUPPORTED_BACK_EXTENSIONS:
        extension = ".png"

    bundle = load_custom_theme_bundle()
    theme_name = _slugify_theme_name(label)
    if theme_name in RESERVED_THEME_NAMES:
        theme_name = f"{theme_name}_custom"
    candidate = theme_name
    index = 2
    while candidate in bundle["themes"] or candidate in RESERVED_THEME_NAMES:
        candidate = f"{theme_name}_{index}"
        index += 1
    theme_name = candidate

    file_name = f"{theme_name}{extension}"
    CUSTOM_BACKS_DIR.mkdir(parents=True, exist_ok=True)
    (CUSTOM_BACKS_DIR / file_name).write_bytes(image_bytes)

    board_bg_path = _save_board_bg_file(theme_name, board_bg_bytes, board_bg_filename)

    theme_payload = build_theme_palette(
        label=label,
        base_color=base_color,
        surface_color=surface_color,
        accent_color=accent_color,
        use_light_text=bool(use_light_text),
    )
    back_payload = {
        "label": theme_payload["label"],
        "asset": f"backs/custom/{file_name}",
        "suggested_theme": theme_name,
        "fit": "cover",
        "scale": round(_clamp(float(image_scale), 0.85, 1.75), 2),
        "board_bg": board_bg_path,
        "custom": True,
    }

    bundle["themes"][theme_name] = theme_payload
    bundle["backs"][theme_name] = back_payload
    _save_custom_theme_bundle(bundle)

    return {
        "theme_name": theme_name,
        "back_name": theme_name,
        "theme": theme_payload,
        "back": back_payload,
    }


# ── Theme management ──────────────────────────────────────────────────────────

def delete_custom_theme(theme_name):
    """Remove a custom theme from the bundle and delete its image files."""
    bundle = load_custom_theme_bundle()
    back_entry = bundle["backs"].get(theme_name)
    if back_entry:
        for field in ("asset", "board_bg"):
            asset = back_entry.get(field, "")
            if asset:
                try:
                    (PROJECT_ROOT / "assets" / asset).unlink(missing_ok=True)
                except Exception:
                    pass
    bundle["themes"].pop(theme_name, None)
    bundle["backs"].pop(theme_name, None)
    _save_custom_theme_bundle(bundle)


def rename_custom_theme(theme_name, new_label):
    """Update only the display label of a custom theme and its back entry."""
    bundle = load_custom_theme_bundle()
    new_label = str(new_label or "").strip() or theme_name
    if theme_name in bundle["themes"]:
        bundle["themes"][theme_name]["label"] = new_label
    if theme_name in bundle["backs"]:
        bundle["backs"][theme_name]["label"] = new_label
    _save_custom_theme_bundle(bundle)


def update_custom_theme_palette(theme_name, base_color, surface_color, accent_color, use_light_text=True):
    """Rebuild the colour palette for an existing custom theme."""
    bundle = load_custom_theme_bundle()
    if theme_name not in bundle["themes"]:
        raise ValueError(f"Tema '{theme_name}' não encontrado.")
    old_label = bundle["themes"][theme_name].get("label", theme_name)
    new_palette = build_theme_palette(
        label=old_label,
        base_color=base_color,
        surface_color=surface_color,
        accent_color=accent_color,
        use_light_text=use_light_text,
    )
    bundle["themes"][theme_name] = new_palette
    _save_custom_theme_bundle(bundle)
    return new_palette


def update_custom_theme_board_bg(theme_name, image_bytes, original_filename):
    """
    Set or clear the board background for a custom theme.
    Pass image_bytes=None to remove the board background.
    Returns the new asset path or None.
    """
    bundle = load_custom_theme_bundle()
    if theme_name not in bundle["backs"]:
        raise ValueError(f"Tema '{theme_name}' não encontrado.")

    # Remove old board bg file if present
    old_path = bundle["backs"][theme_name].get("board_bg")
    if old_path:
        try:
            (PROJECT_ROOT / "assets" / old_path).unlink(missing_ok=True)
        except Exception:
            pass

    if image_bytes is None:
        bundle["backs"][theme_name]["board_bg"] = None
        _save_custom_theme_bundle(bundle)
        return None

    new_path = _save_board_bg_file(theme_name, image_bytes, original_filename)
    bundle["backs"][theme_name]["board_bg"] = new_path
    _save_custom_theme_bundle(bundle)
    return new_path
