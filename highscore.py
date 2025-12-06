import json
import os

HS_FILE = "highscores.json"

def load_scores():
    if os.path.exists(HS_FILE):
        with open(HS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_scores(scores):
    with open(HS_FILE, "w", encoding="utf-8") as f:
        json.dump(scores, f, indent=2)

def add_score(name, score):
    scores = load_scores()
    scores.append({"name": name, "score": score})
    scores = sorted(scores, key=lambda x: x["score"], reverse=True)[:10]  # Top 10
    save_scores(scores)
