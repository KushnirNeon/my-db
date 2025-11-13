import json
from models import Database

def save_to_file(db: Database, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(db.to_dict(), f, ensure_ascii=False, indent=2)

def load_from_file(path: str) -> Database:
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    return Database.from_dict(d)
