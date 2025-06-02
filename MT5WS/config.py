import json

with open("settings.json", "r", encoding="utf-8") as f:
    settings = json.load(f)

moving_average_periods = settings.get("moving_average_periods", [20, 75, 200])