import yaml

with open("settings.yaml", "r", encoding="utf-8") as f:
    settings = yaml.safe_load(f)

moving_average_periods = settings.get("moving_average_periods", [20, 75, 200])
auto_update_interval = settings.get("auto_update_interval", 60)