"""Build the guided notebook from the latest saved pipeline outputs."""
from __future__ import annotations

import json
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
summary = json.loads((ROOT / "data" / "outputs" / "run_summary.json").read_text(encoding="utf-8"))

nb = nbf.v4.new_notebook()
nb.metadata = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.12"},
}
cells = []
cells.append(nbf.v4.new_markdown_cell(f"""# Live TSX Portfolio Market Data Pipeline

Guided walkthrough of the latest completed run.

- Latest daily session: **{summary['latest_daily_date']}**
- Daily rows: **{summary['daily_raw_rows']:,}**
- Intraday rows: **{summary['intraday_raw_rows']:,}**
- Corporate actions: **{summary['corporate_actions']}**
- Outliers flagged: **{summary['outliers_flagged']}**

The feed is a production-style near-live polling feed from Yahoo Finance, not a direct exchange tick feed."""))
cells.append(nbf.v4.new_markdown_cell("""## 1. Load the run evidence

The notebook starts from saved outputs. It does not need to download the full history again."""))
cells.append(nbf.v4.new_code_cell("""from pathlib import Path
import json
import pandas as pd

ROOT = Path.cwd()
if (ROOT / 'data' / 'outputs').exists():
    BASE = ROOT
else:
    BASE = ROOT.parent

OUT = BASE / 'data' / 'outputs'
summary = json.loads((OUT / 'run_summary.json').read_text())
quality = pd.read_csv(OUT / 'data_quality_summary.csv')
snapshot = pd.read_csv(OUT / 'latest_risk_snapshot.csv')
weights = pd.read_csv(OUT / 'strategy_weights_latest.csv')
metrics = pd.read_csv(OUT / 'strategy_metrics_latest_window.csv')
summary"""))
cells.append(nbf.v4.new_markdown_cell("""## 2. Check data quality

Coverage is measured against benchmark sessions. A warning status means review flags remain, usually outliers. It does not by itself mean ingestion failed."""))
cells.append(nbf.v4.new_code_cell("""quality.sort_values(['coverage_pct', 'symbol'])"""))
cells.append(nbf.v4.new_markdown_cell("""## 3. Read the latest risk snapshot

Volatility and drawdown use adjusted daily prices. Beta and correlation use the latest 252 daily sessions."""))
cells.append(nbf.v4.new_code_cell("""snapshot.sort_values('realized_vol_60d', ascending=False)"""))
cells.append(nbf.v4.new_markdown_cell("""## 4. Compare refreshed weights

Weights sum to 100 percent for each method, with a 20 percent position cap and a 40 percent sector cap."""))
cells.append(nbf.v4.new_code_cell("""weights.pivot(index='short', columns='strategy', values='weight').round(4)"""))
cells.append(nbf.v4.new_markdown_cell("""## 5. Read the window diagnostics carefully

These results are calculated on the same 104-week window used to select the weights. They check the optimisation. They are not forecasts and they do not revise the earlier V2 backtest."""))
cells.append(nbf.v4.new_code_cell("""metrics"""))
cells.append(nbf.v4.new_markdown_cell("""## 6. Run a new pipeline update

Run these commands from the project root:

```bash
python run_pipeline.py
python scripts/build_deliverables.py
```

A failed daily symbol stops the run before strategy outputs are refreshed."""))
nb.cells = cells
path = ROOT / "notebooks" / "live_pipeline_walkthrough.ipynb"
nbf.write(nb, path)
print(path)
