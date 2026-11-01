from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from tsx_pipeline.config import BENCHMARK_SYMBOL, STOCK_SYMBOLS
from tsx_pipeline.regimes import daily_returns, find_most_extreme_day, regime_report

OUT = ROOT / "data" / "regime_outputs"
OUT.mkdir(parents=True, exist_ok=True)


def save(frame: pd.DataFrame, name: str, index: bool = False) -> None:
    frame.to_csv(OUT / name, index=index)


def state_summary(daily: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    valid = daily[daily["market_state"].ne("Warm-up")].copy()
    valid = valid.assign(spell_id=valid["market_state"].ne(valid["market_state"].shift()).cumsum())
    spells = (valid.groupby(["spell_id", "market_state"], as_index=False)
              .size().rename(columns={"size": "spell_days"}))
    rows = []
    for state, group in valid.groupby("market_state"):
        state_spells = spells[spells["market_state"].eq(state)]["spell_days"]
        rows.append({
            "market_state": state,
            "days": int(len(group)),
            "share_pct": float(len(group) / len(valid) * 100),
            "average_benchmark_return_bp": float(group["benchmark_return"].mean() * 10_000),
            "equal_weight_return_dispersion_pct": float(group["equal_weight_return"].std(ddof=1) * np.sqrt(252) * 100),
            "average_distance_from_center": float(group["distance_from_center"].mean()),
            "average_abs_pc1_score": float(group["PC1"].abs().mean()),
            "average_rank3_residual_share": float(group["rank3_residual_share"].mean()),
            "spells": int(len(state_spells)),
            "average_spell_days": float(state_spells.mean()) if len(state_spells) else np.nan,
            "median_spell_days": float(state_spells.median()) if len(state_spells) else np.nan,
            "longest_spell_days": int(state_spells.max()) if len(state_spells) else 0,
        })
    return pd.DataFrame(rows).sort_values("days", ascending=False), spells


def extreme_days(returns: pd.DataFrame, daily: pd.DataFrame, count: int = 15) -> pd.DataFrame:
    top = daily.sort_values("distance_from_center", ascending=False).head(count).copy()
    rows = []
    for date, row in top.iterrows():
        day = returns.loc[date]
        rows.append({
            "date": date,
            "distance_from_center": row["distance_from_center"],
            "equal_weight_return": row["equal_weight_return"],
            "benchmark_return": row["benchmark_return"],
            "market_state": row["market_state"],
            "largest_gain_stock": day.idxmax(), "largest_gain_return": day.max(),
            "smallest_return_stock": day.idxmin(), "smallest_return": day.min(),
            "pc1_score": row["PC1"], "pc2_score": row["PC2"],
            "rank3_residual_share": row["rank3_residual_share"],
        })
    return pd.DataFrame(rows)


def transition_days(daily: pd.DataFrame, count: int = 15,
                    material_only: bool = False) -> pd.DataFrame:
    ordered = daily.reset_index().rename(columns={"timestamp": "date"})
    ordered["previous_date"] = ordered["date"].shift(1)
    ordered["previous_market_state"] = ordered["market_state"].shift(1)
    ordered["previous_distance_from_center"] = ordered["distance_from_center"].shift(1)
    ordered["previous_equal_weight_return"] = ordered["equal_weight_return"].shift(1)
    if material_only:
        threshold = daily["distance_from_center"].quantile(0.75)
        ordered = ordered[
            (ordered["angle_from_previous_day_degrees"] > 135)
            & (ordered["distance_from_center"] >= threshold)
            & (ordered["previous_distance_from_center"] >= threshold)
        ]
    cols = ["previous_date", "date", "angle_from_previous_day_degrees",
            "previous_distance_from_center", "distance_from_center",
            "previous_market_state", "market_state", "previous_equal_weight_return",
            "equal_weight_return", "benchmark_return"]
    return ordered.sort_values("angle_from_previous_day_degrees", ascending=False).head(count)[cols]


def main() -> int:
    prices = pd.read_csv(ROOT / "data" / "clean" / "adjusted_close_filled_matrix.csv",
                         index_col=0, parse_dates=True)
    stock_prices = prices[STOCK_SYMBOLS]
    returns = daily_returns(stock_prices)
    benchmark = daily_returns(prices[[BENCHMARK_SYMBOL]])[BENCHMARK_SYMBOL]
    tables = regime_report(returns, benchmark)

    save(tables["spectrum"], "spectrum.csv")
    save(tables["standardized_spectrum"], "spectrum_standardized.csv")
    save(tables["loadings"], "dominant_directions.csv", index=True)
    save(tables["standardized_loadings"], "dominant_directions_standardized.csv", index=True)
    save(tables["daily"], "daily_projections.csv", index=True)
    save(tables["reconstruction"], "reconstruction_quality.csv")
    save(tables["annual_structure"], "annual_structure.csv")
    save(tables["rolling_structure"], "rolling_structure.csv")

    summary_by_state, spells = state_summary(tables["daily"])
    save(summary_by_state, "market_state_summary.csv")
    save(spells, "market_state_spells.csv")
    extremes = extreme_days(returns, tables["daily"])
    save(extremes, "extreme_days.csv")
    transitions = transition_days(tables["daily"])
    save(transitions, "largest_transition_days.csv")
    material_transitions = transition_days(tables["daily"], count=50, material_only=True)
    save(material_transitions, "material_transition_days.csv")

    daily = tables["daily"]
    spectrum = tables["spectrum"]
    reconstruction = tables["reconstruction"].set_index("rank")
    angles = daily["angle_from_previous_day_degrees"].dropna()
    most_extreme = find_most_extreme_day(returns)
    summary = {
        "analysis": "Discovering Market Regimes Through Structure",
        "data_start": str(returns.index.min().date()),
        "data_end": str(returns.index.max().date()),
        "days": int(len(returns)),
        "assets": int(len(returns.columns)),
        "pc1_explained_variance_pct": float(spectrum.iloc[0].explained_variance_ratio * 100),
        "top2_explained_variance_pct": float(spectrum.iloc[:2].explained_variance_ratio.sum() * 100),
        "top3_explained_variance_pct": float(spectrum.iloc[:3].explained_variance_ratio.sum() * 100),
        "top5_explained_variance_pct": float(spectrum.iloc[:5].explained_variance_ratio.sum() * 100),
        "standardized_pc1_explained_variance_pct": float(tables["standardized_spectrum"].iloc[0].explained_variance_ratio * 100),
        "standardized_top3_explained_variance_pct": float(tables["standardized_spectrum"].iloc[:3].explained_variance_ratio.sum() * 100),
        "rank3_residual_share_pct": float(reconstruction.loc[3, "residual_share"] * 100),
        "rank3_residual_rms_bp": float(reconstruction.loc[3, "residual_rms_bp"]),
        "most_extreme_day": str(most_extreme["date"].date()),
        "most_extreme_day_distance": float(most_extreme["distance_from_center"]),
        "large_transitions_over_135_degrees": int((angles > 135).sum()),
        "large_transition_share_pct": float((angles > 135).mean() * 100),
        "material_large_transitions": int(len(material_transitions)),
        "material_distance_threshold": float(daily["distance_from_center"].quantile(0.75)),
        "mean_angle_degrees": float(angles.mean()),
        "median_angle_degrees": float(angles.median()),
        "latest_date": str(daily.index.max().date()),
        "latest_market_state": str(daily.iloc[-1]["market_state"]),
        "volatility_threshold_pct": float(daily.iloc[-1]["volatility_threshold"] * 100),
    }
    (OUT / "regime_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
