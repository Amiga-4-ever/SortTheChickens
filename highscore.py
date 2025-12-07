import json
import os
import sys

def get_data_dir():
    """Gibt einen Plattform-spezifischen, beschreibbaren Ordner zurück."""
    if sys.platform == "win32":
        base = os.getenv("APPDATA")  
        return os.path.join(base, "SortTheChickens")
    elif sys.platform == "darwin":  # macOS
        base = os.path.expanduser("~/Library/Application Support")
        return os.path.join(base, "SaveTheChickens")
    else:  # Linux
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
            return json.load(f)
    except Exception as e:
        print("Fehler beim Laden der Highscores:", e)
        return []


def save_score(name, score):
    os.makedirs(DATA_DIR, exist_ok=True)

    data = load_scores()
    data.append({"name": name, "score": score})

    # sortieren & auf die Top 10 begrenzen
    data = sorted(data, key=lambda x: x["score"], reverse=True)[:10]

    try:
        with open(SCORE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print("Fehler beim Speichern der Highscores:", e)


def add_score(name, score):
    scores = load_scores()
    scores.append({"name": name, "score": score})
    scores = sorted(scores, key=lambda x: x["score"], reverse=True)[:10]  # Top 10
    save_score(scores)
