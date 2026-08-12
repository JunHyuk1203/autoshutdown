import json

with open("database.rules.json", "r", encoding="utf-8") as f:
    rules = json.load(f)

rules["rules"]["update_info"] = {
    ".read": "true",
    ".write": "true"
}

with open("database.rules.json", "w", encoding="utf-8") as f:
    json.dump(rules, f, indent=2)

print("Updated database.rules.json")
