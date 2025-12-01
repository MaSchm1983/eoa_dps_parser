import os
import sys
import json
import config


def _get_app_dir() -> str:

    if getattr(sys, "frozen", False):
        # PyInstaller-EXE
        return os.path.dirname(sys.argv[0])
    # python-script
    return os.path.dirname(os.path.abspath(__file__))


SETTINGS_FILE = os.path.join(_get_app_dir(), "settings.json")

DEFAULT_SETTINGS = {
    "cmbt_log_dir": config.CMBT_LOG_DIR,
    "custom_pet_names": [],  # nur nicht-default-Namen
}


def load_settings() -> dict:
    data = {}
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        pass
    except Exception as e:
        if getattr(config, "DEBUG_PARSE", False):
            print("[CFG] Failed to load settings.json:", e)

    merged = DEFAULT_SETTINGS.copy()
    for k, v in data.items():
        if k in merged:
            merged[k] = v

    # Combat-Log-Pfad
    config.CMBT_LOG_DIR = merged["cmbt_log_dir"]

    # Default + Custom-Pets kombinieren
    default_lower = set(config.DEFAULT_PET_NAMES_LOWER)
    custom_lower = [n.lower() for n in merged.get("custom_pet_names", [])]

    # nur echte Custom-Namen behalten (nicht in Defaults enthalten)
    custom_lower = [n for n in custom_lower if n and n not in default_lower]

    combined = list(config.DEFAULT_PET_NAMES_LOWER) + [
        n for n in custom_lower if n not in default_lower
    ]

    if hasattr(config, "PET_NAMES") and isinstance(config.PET_NAMES, list):
        config.PET_NAMES[:] = combined

    # den bereinigten Stand zurück in die Settings spiegeln
    merged["custom_pet_names"] = custom_lower
    return merged


def save_settings(settings: dict) -> None:
    out = {}
    for k in DEFAULT_SETTINGS.keys():
        if k in settings:
            out[k] = settings[k]

    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        if getattr(config, "DEBUG_PARSE", False):
            print(f"[CFG] Saved settings.json to {SETTINGS_FILE}")
    except Exception as e:
        if getattr(config, "DEBUG_PARSE", False):
            print("[CFG] Failed to save settings.json:", e)