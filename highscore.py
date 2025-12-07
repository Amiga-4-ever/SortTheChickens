import json
import os
import sys
import tempfile

def get_data_dir():
    """Gibt einen Plattform-spezifischen, beschreibbaren Ordner zurück."""
    if sys.platform == "win32":
        base = os.getenv("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "SortTheChickens")
    elif sys.platform == "darwin":  # macOS
        base = os.path.expanduser("~/Library/Application Support")
        return os.path.join(base, "SaveTheChickens")
    else:  # Linux und andere Unixes
        base = os.path.expanduser("~/.local/share")
        return os.path.join(base, "SaveTheChickens")

DATA_DIR = get_data_dir()
SCORE_FILE = os.path.join(DATA_DIR, "highscores.json")

def load_scores():
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(SCORE_FILE):
        return []

    try:
        with open(SCORE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            else:
                # Falls Datei korrupt / nicht erwartet, überschreiben wir später
                return []
    except Exception as e:
        # Im Entwicklermodus kann man hier ein Logging ergänzen; für die exe unterdrücken wir die Exception-Ausgabe.
        # Wir geben eine leere Liste zurück, damit das Spiel weiterläuft.
        return []


def save_scores(scores):
    """Schreibt die komplette Scores-Liste atomar (Tempfile + replace)."""
    os.makedirs(DATA_DIR, exist_ok=True)
    # Validierung: scores sollte eine Liste von dicts sein
    try:
        cleaned = []
        for item in scores:
            if isinstance(item, dict) and "name" in item and "score" in item:
                cleaned.append({"name": str(item["name"]), "score": int(item["score"])})
    except Exception:
        cleaned = []

    # Sortieren & Top 10
    cleaned = sorted(cleaned, key=lambda x: x["score"], reverse=True)[:10]

    # Atomares Schreiben: zuerst in Tempfile, dann ersetzen
    try:
        fd, tmp_path = tempfile.mkstemp(prefix="hs_", dir=DATA_DIR, text=True)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cleaned, f, indent=4, ensure_ascii=False)
        os.replace(tmp_path, SCORE_FILE)
    except Exception:
        # Falls Schreiben fehlschlägt, ignorieren wir, damit das Spiel nicht abstürzt.
        pass


def add_score(name, score):
    """Bequeme Funktion: lädt, fügt hinzu, speichert (Top 10)."""
    try:
        scores = load_scores()
        scores.append({"name": str(name), "score": int(score)})
        save_scores(scores)
    except Exception:
        # defensiv: niemals einen Fehler hier hochwerfen
        pass
