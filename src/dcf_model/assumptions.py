"""Load and validate the model's JSON assumptions."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class OperatingCase:
    revenue_growth: tuple[float, ...]
    ebitda_margin: tuple[float, ...]
    da_pct_revenue: tuple[float, ...]
    capex_pct_revenue: tuple[float, ...]
    nwc_pct_revenue: tuple[float, ...]


@dataclass(frozen=True)
class ModelConfig:
    company: str
    currency: str
    monetary_unit: str
    starting_revenue: float
    forecast_years: int
    tax_rate: float
    risk_free_rate: float
    equity_risk_premium: float
    beta: float
    pre_tax_cost_of_debt: float
    equity_weight: float
    terminal_growth_rate: float
    debt: float
    cash: float
    shares_outstanding: float
    sensitivity_step: float
    sensitivity_steps_each_side: int
    scenarios: dict[str, OperatingCase]


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"'{label}' must be a JSON object.")
    return value


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"'{label}' must be a number.")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"'{label}' must be finite.")
    return result


def _bounded_rate(
    value: Any,
    label: str,
    *,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    result = _number(value, label)
    if not minimum <= result < maximum:
        raise ValueError(f"'{label}' must be between {minimum} and {maximum}.")
    return result


def _series(
    value: Any,
    label: str,
    forecast_years: int,
    *,
    minimum: float,
    maximum: float = 1.0,
) -> tuple[float, ...]:
    if not isinstance(value, list) or len(value) != forecast_years:
        raise ValueError(
            f"'{label}' must contain exactly {forecast_years} annual values."
        )
    return tuple(
        _bounded_rate(item, f"{label}[{index}]", minimum=minimum, maximum=maximum)
        for index, item in enumerate(value, start=1)
    )


def load_config(path: Path) -> ModelConfig:
    """Read a configuration file and reject incomplete or invalid assumptions."""
    try:
        raw_data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Could not parse JSON in {path}: {exc.msg}.") from exc

    raw = _mapping(raw_data, "root")
    try:
        forecast_years = raw["forecast_years"]
        if isinstance(forecast_years, bool) or not isinstance(forecast_years, int):
            raise ValueError("'forecast_years' must be an integer.")
        if forecast_years < 1 or forecast_years > 20:
            raise ValueError("'forecast_years' must be between 1 and 20.")

        scenarios_raw = _mapping(raw["scenarios"], "scenarios")
        shared = _mapping(
            scenarios_raw.get("shared_operating_assumptions"),
            "scenarios.shared_operating_assumptions",
        )
        scenario_cases: dict[str, OperatingCase] = {}
        for name, values in scenarios_raw.items():
            if name == "shared_operating_assumptions":
                continue
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Scenario names must be non-empty strings.")
            case = _mapping(values, f"scenarios.{name}")
            scenario_cases[name] = OperatingCase(
                revenue_growth=_series(
                    case.get("revenue_growth"),
                    f"scenarios.{name}.revenue_growth",
                    forecast_years,
                    minimum=-0.99,
                ),
                ebitda_margin=_series(
                    case.get("ebitda_margin"),
                    f"scenarios.{name}.ebitda_margin",
                    forecast_years,
                    minimum=0.0,
                ),
                da_pct_revenue=_series(
                    shared.get("da_pct_revenue"),
                    "scenarios.shared_operating_assumptions.da_pct_revenue",
                    forecast_years,
                    minimum=0.0,
                ),
                capex_pct_revenue=_series(
                    shared.get("capex_pct_revenue"),
                    "scenarios.shared_operating_assumptions.capex_pct_revenue",
                    forecast_years,
                    minimum=0.0,
                ),
                nwc_pct_revenue=_series(
                    shared.get("nwc_pct_revenue"),
                    "scenarios.shared_operating_assumptions.nwc_pct_revenue",
                    forecast_years,
                    minimum=0.0,
                ),
            )
        if not scenario_cases:
            raise ValueError("At least one operating scenario is required.")

        company = raw["company"]
        currency = raw["currency"]
        monetary_unit = raw["monetary_unit"]
        for label, value in (
            ("company", company),
            ("currency", currency),
            ("monetary_unit", monetary_unit),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"'{label}' must be a non-empty string.")

        starting_revenue = _number(raw["starting_revenue"], "starting_revenue")
        if starting_revenue <= 0:
            raise ValueError("'starting_revenue' must be greater than zero.")

        debt = _number(raw["debt"], "debt")
        cash = _number(raw["cash"], "cash")
        if debt < 0 or cash < 0:
            raise ValueError("'debt' and 'cash' must be zero or greater.")

        beta = _number(raw["beta"], "beta")
        if beta <= 0:
            raise ValueError("'beta' must be greater than zero.")

        equity_weight = _number(raw["equity_weight"], "equity_weight")
        if not 0 < equity_weight <= 1:
            raise ValueError("'equity_weight' must be greater than zero and at most one.")

        sensitivity_step = _number(raw["sensitivity_step"], "sensitivity_step")
        sensitivity_steps = raw["sensitivity_steps_each_side"]
        if sensitivity_step <= 0:
            raise ValueError("'sensitivity_step' must be greater than zero.")
        if (
            isinstance(sensitivity_steps, bool)
            or not isinstance(sensitivity_steps, int)
            or sensitivity_steps < 1
            or sensitivity_steps > 10
        ):
            raise ValueError(
                "'sensitivity_steps_each_side' must be an integer from 1 to 10."
            )

        shares_outstanding = _number(
            raw["shares_outstanding"], "shares_outstanding"
        )
        if shares_outstanding <= 0:
            raise ValueError("'shares_outstanding' must be greater than zero.")

        return ModelConfig(
            company=company.strip(),
            currency=currency.strip(),
            monetary_unit=monetary_unit.strip(),
            starting_revenue=starting_revenue,
            forecast_years=forecast_years,
            tax_rate=_bounded_rate(raw["tax_rate"], "tax_rate"),
            risk_free_rate=_bounded_rate(raw["risk_free_rate"], "risk_free_rate"),
            equity_risk_premium=_bounded_rate(
                raw["equity_risk_premium"], "equity_risk_premium"
            ),
            beta=beta,
            pre_tax_cost_of_debt=_bounded_rate(
                raw["pre_tax_cost_of_debt"], "pre_tax_cost_of_debt"
            ),
            equity_weight=equity_weight,
            terminal_growth_rate=_bounded_rate(
                raw["terminal_growth_rate"],
                "terminal_growth_rate",
                minimum=-0.99,
            ),
            debt=debt,
            cash=cash,
            shares_outstanding=shares_outstanding,
            sensitivity_step=sensitivity_step,
            sensitivity_steps_each_side=sensitivity_steps,
            scenarios=scenario_cases,
        )
    except KeyError as exc:
        raise ValueError(f"Missing required assumption: '{exc.args[0]}'.") from exc
