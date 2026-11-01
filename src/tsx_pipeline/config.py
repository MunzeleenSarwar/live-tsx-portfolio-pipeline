from __future__ import annotations

from pathlib import Path
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config" / "universe.yaml"


def load_config(path: Path = CONFIG_PATH) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


CONFIG = load_config()
SYMBOLS = CONFIG["symbols"]
STOCK_SYMBOLS = list(SYMBOLS)
BENCHMARK_SYMBOL = CONFIG["benchmark"]["symbol"]
ALL_SYMBOLS = STOCK_SYMBOLS + [BENCHMARK_SYMBOL]
SHORT_BY_SYMBOL = {symbol: details["short"] for symbol, details in SYMBOLS.items()}
SHORT_BY_SYMBOL[BENCHMARK_SYMBOL] = CONFIG["benchmark"]["short"]
SECTOR_BY_SHORT = {details["short"]: details["sector"] for details in SYMBOLS.values()}
NAME_BY_SHORT = {details["short"]: details["name"] for details in SYMBOLS.values()}
NAME_BY_SHORT[CONFIG["benchmark"]["short"]] = CONFIG["benchmark"]["name"]
STOCK_SHORTS = [details["short"] for details in SYMBOLS.values()]
TIMEZONE = CONFIG["project"]["timezone"]
