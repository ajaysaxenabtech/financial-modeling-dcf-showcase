"""CSV output helpers for model results."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from dcf_model.assumptions import ModelConfig
from dcf_model.model import Valuation, sensitivity_grid


def _write_rows(
    path: Path,
    header: Iterable[str],
    rows: Iterable[Iterable[object]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)


def write_forecast(path: Path, valuation: Valuation) -> None:
    columns = (
        "forecast_year",
        "revenue",
        "revenue_growth",
        "ebitda",
        "ebitda_margin",
        "depreciation_amortization",
        "ebit",
        "cash_taxes",
        "nopat",
        "capex",
        "change_in_nwc",
        "free_cash_flow",
        "present_value_of_fcf",
    )
    rows = []
    for item in valuation.forecast:
        rows.append(
            (
                item.year,
                round(item.revenue, 4),
                round(item.revenue_growth, 6),
                round(item.ebitda, 4),
                round(item.ebitda_margin, 6),
                round(item.depreciation_amortization, 4),
                round(item.ebit, 4),
                round(item.cash_taxes, 4),
                round(item.nopat, 4),
                round(item.capex, 4),
                round(item.change_in_nwc, 4),
                round(item.free_cash_flow, 4),
                round(item.present_value_of_fcf, 4),
            )
        )
    _write_rows(path, columns, rows)


def write_summary(path: Path, config: ModelConfig, valuation: Valuation) -> None:
    terminal_share = valuation.terminal_value_share_of_ev
    rows = [
        ("company", config.company, ""),
        ("scenario", valuation.scenario, ""),
        ("currency", config.currency, ""),
        ("monetary_unit", config.monetary_unit, ""),
        ("starting_revenue", round(config.starting_revenue, 4), config.monetary_unit),
        ("forecast_years", config.forecast_years, "years"),
        ("risk_free_rate", round(config.risk_free_rate, 6), "decimal"),
        ("beta", round(config.beta, 6), "x"),
        ("equity_risk_premium", round(config.equity_risk_premium, 6), "decimal"),
        ("cost_of_equity", round(valuation.cost_of_equity, 6), "decimal"),
        ("after_tax_cost_of_debt", round(valuation.after_tax_cost_of_debt, 6), "decimal"),
        ("wacc", round(valuation.wacc, 6), "decimal"),
        ("terminal_growth_rate", round(config.terminal_growth_rate, 6), "decimal"),
        (
            "present_value_of_forecast_fcf",
            round(valuation.present_value_of_forecast_fcf, 4),
            config.monetary_unit,
        ),
        ("terminal_value", round(valuation.terminal_value, 4), config.monetary_unit),
        (
            "present_value_of_terminal_value",
            round(valuation.present_value_of_terminal_value, 4),
            config.monetary_unit,
        ),
        ("enterprise_value", round(valuation.enterprise_value, 4), config.monetary_unit),
        ("debt", round(config.debt, 4), config.monetary_unit),
        ("cash", round(config.cash, 4), config.monetary_unit),
        ("equity_value", round(valuation.equity_value, 4), config.monetary_unit),
        ("shares_outstanding", round(config.shares_outstanding, 4), "millions"),
        (
            "implied_value_per_share",
            round(valuation.implied_value_per_share, 4),
            config.currency,
        ),
        (
            "terminal_value_share_of_ev",
            round(terminal_share, 6) if terminal_share is not None else "",
            "decimal",
        ),
    ]
    _write_rows(path, ("metric", "value", "units"), rows)


def write_sensitivity(path: Path, config: ModelConfig, valuation: Valuation) -> None:
    grid = sensitivity_grid(config, valuation)
    steps = config.sensitivity_steps_each_side
    growth_rates = [
        config.terminal_growth_rate + (step * config.sensitivity_step)
        for step in range(-steps, steps + 1)
    ]
    header = ["wacc / terminal growth"] + [
        f"{growth:.2%}" for growth in growth_rates
    ]
    rows = [
        (f"{wacc:.2%}", *(round(value, 4) for value in share_values))
        for wacc, share_values in grid
    ]
    _write_rows(path, header, rows)


def write_scenario_comparison(
    path: Path,
    config: ModelConfig,
    valuations: Iterable[Valuation],
) -> None:
    rows = []
    for valuation in valuations:
        share = valuation.terminal_value_share_of_ev
        rows.append(
            (
                valuation.scenario,
                round(valuation.wacc, 6),
                round(config.terminal_growth_rate, 6),
                round(valuation.enterprise_value, 4),
                round(valuation.equity_value, 4),
                round(valuation.implied_value_per_share, 4),
                round(share, 6) if share is not None else "",
            )
        )
    _write_rows(
        path,
        (
            "scenario",
            "wacc",
            "terminal_growth_rate",
            "enterprise_value",
            "equity_value",
            "implied_value_per_share",
            "terminal_value_share_of_ev",
        ),
        rows,
    )
