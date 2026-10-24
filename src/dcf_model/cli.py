"""Command-line interface for the DCF showcase."""

from __future__ import annotations

import argparse
from pathlib import Path

from dcf_model.assumptions import ModelConfig, load_config
from dcf_model.model import Valuation, value_case
from dcf_model.reporting import (
    write_forecast,
    write_scenario_comparison,
    write_sensitivity,
    write_summary,
)


def _default_assumptions_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "assumptions.json"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a scenario-based DCF valuation and CSV reports from JSON assumptions."
        )
    )
    parser.add_argument(
        "--scenario",
        default="all",
        help="Operating case name or 'all' (defaults to all available scenarios).",
    )
    parser.add_argument(
        "--assumptions",
        type=Path,
        default=_default_assumptions_path(),
        help="Path to the JSON assumptions file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs"),
        help="Directory for generated CSV files (default: ./outputs).",
    )
    return parser.parse_args()


def _print_valuation(config: ModelConfig, valuation: Valuation) -> None:
    print(f"{valuation.scenario.upper()} CASE — {config.company}")
    print(
        f"  WACC: {valuation.wacc:.2%}\n"
        f"  Enterprise value: {config.currency} "
        f"{valuation.enterprise_value:,.2f} {config.monetary_unit}\n"
        f"  Equity value: {config.currency} "
        f"{valuation.equity_value:,.2f} {config.monetary_unit}\n"
        f"  Implied value per share: {config.currency} "
        f"{valuation.implied_value_per_share:,.2f}"
    )


def main() -> None:
    args = _parse_args()
    try:
        config = load_config(args.assumptions)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Assumption error: {exc}") from exc

    requested = (
        list(config.scenarios)
        if args.scenario == "all"
        else [args.scenario]
    )
    missing = [name for name in requested if name not in config.scenarios]
    if missing:
        available = ", ".join(config.scenarios)
        raise SystemExit(
            f"Scenario(s) not found: {', '.join(missing)}. "
            f"Available scenarios: {available}."
        )

    valuations: list[Valuation] = []
    for scenario_name in requested:
        valuation = value_case(
            config,
            scenario_name,
            config.scenarios[scenario_name],
        )
        valuations.append(valuation)
        scenario_dir = args.output_dir / scenario_name
        write_forecast(scenario_dir / "forecast.csv", valuation)
        write_summary(scenario_dir / "summary.csv", config, valuation)
        write_sensitivity(scenario_dir / "sensitivity.csv", config, valuation)
        _print_valuation(config, valuation)

    if args.scenario == "all":
        write_scenario_comparison(
            args.output_dir / "scenario_comparison.csv",
            config,
            valuations,
        )

    print(f"CSV reports written to: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
