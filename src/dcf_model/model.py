"""Core cash-flow forecast, WACC, DCF, and sensitivity calculations."""

from __future__ import annotations

from dataclasses import dataclass

from dcf_model.assumptions import ModelConfig, OperatingCase


@dataclass(frozen=True)
class ForecastYear:
    year: int
    revenue: float
    revenue_growth: float
    ebitda: float
    ebitda_margin: float
    depreciation_amortization: float
    ebit: float
    cash_taxes: float
    nopat: float
    capex: float
    change_in_nwc: float
    free_cash_flow: float
    present_value_of_fcf: float


@dataclass(frozen=True)
class Valuation:
    scenario: str
    cost_of_equity: float
    after_tax_cost_of_debt: float
    wacc: float
    present_value_of_forecast_fcf: float
    terminal_value: float
    present_value_of_terminal_value: float
    enterprise_value: float
    equity_value: float
    implied_value_per_share: float
    terminal_value_share_of_ev: float | None
    forecast: tuple[ForecastYear, ...]


def calculate_wacc(config: ModelConfig) -> tuple[float, float, float]:
    """Return cost of equity, after-tax cost of debt, and WACC."""
    cost_of_equity = (
        config.risk_free_rate + config.beta * config.equity_risk_premium
    )
    after_tax_cost_of_debt = config.pre_tax_cost_of_debt * (1 - config.tax_rate)
    debt_weight = 1 - config.equity_weight
    wacc = (
        config.equity_weight * cost_of_equity
        + debt_weight * after_tax_cost_of_debt
    )
    return cost_of_equity, after_tax_cost_of_debt, wacc


def build_forecast(
    config: ModelConfig,
    case: OperatingCase,
    wacc: float,
) -> tuple[ForecastYear, ...]:
    """Project unlevered free cash flow for each explicit forecast year."""
    forecast: list[ForecastYear] = []
    prior_revenue = config.starting_revenue

    for index in range(config.forecast_years):
        revenue_growth = case.revenue_growth[index]
        revenue = prior_revenue * (1 + revenue_growth)
        ebitda_margin = case.ebitda_margin[index]
        ebitda = revenue * ebitda_margin
        depreciation = revenue * case.da_pct_revenue[index]
        ebit = ebitda - depreciation

        # This simple model does not recognize tax benefits for loss-making years.
        cash_taxes = max(ebit, 0.0) * config.tax_rate
        nopat = ebit - cash_taxes
        capex = revenue * case.capex_pct_revenue[index]
        change_in_nwc = (
            revenue - prior_revenue
        ) * case.nwc_pct_revenue[index]
        free_cash_flow = nopat + depreciation - capex - change_in_nwc

        year_number = index + 1
        present_value_of_fcf = free_cash_flow / (1 + wacc) ** year_number
        forecast.append(
            ForecastYear(
                year=year_number,
                revenue=revenue,
                revenue_growth=revenue_growth,
                ebitda=ebitda,
                ebitda_margin=ebitda_margin,
                depreciation_amortization=depreciation,
                ebit=ebit,
                cash_taxes=cash_taxes,
                nopat=nopat,
                capex=capex,
                change_in_nwc=change_in_nwc,
                free_cash_flow=free_cash_flow,
                present_value_of_fcf=present_value_of_fcf,
            )
        )
        prior_revenue = revenue

    return tuple(forecast)


def discounted_enterprise_value(
    forecast: tuple[ForecastYear, ...],
    wacc: float,
    terminal_growth_rate: float,
) -> tuple[float, float, float, float]:
    """Return PV of forecast cash flows, terminal value, PV of terminal value, and EV."""
    if wacc <= terminal_growth_rate:
        raise ValueError(
            f"WACC ({wacc:.2%}) must exceed terminal growth "
            f"({terminal_growth_rate:.2%})."
        )
    if wacc <= -1:
        raise ValueError("WACC must be greater than -100%.")

    present_value_of_forecast = sum(
        row.free_cash_flow / (1 + wacc) ** row.year for row in forecast
    )
    final_fcf = forecast[-1].free_cash_flow
    terminal_value = (
        final_fcf * (1 + terminal_growth_rate) / (wacc - terminal_growth_rate)
    )
    present_value_of_terminal = terminal_value / (1 + wacc) ** len(forecast)
    enterprise_value = present_value_of_forecast + present_value_of_terminal
    return (
        present_value_of_forecast,
        terminal_value,
        present_value_of_terminal,
        enterprise_value,
    )


def value_case(
    config: ModelConfig,
    scenario_name: str,
    case: OperatingCase,
) -> Valuation:
    cost_of_equity, after_tax_cost_of_debt, wacc = calculate_wacc(config)
    forecast = build_forecast(config, case, wacc)
    (
        present_value_of_forecast,
        terminal_value,
        present_value_of_terminal,
        enterprise_value,
    ) = discounted_enterprise_value(forecast, wacc, config.terminal_growth_rate)

    equity_value = enterprise_value - config.debt + config.cash
    implied_value_per_share = equity_value / config.shares_outstanding
    terminal_share = (
        present_value_of_terminal / enterprise_value
        if enterprise_value != 0
        else None
    )
    return Valuation(
        scenario=scenario_name,
        cost_of_equity=cost_of_equity,
        after_tax_cost_of_debt=after_tax_cost_of_debt,
        wacc=wacc,
        present_value_of_forecast_fcf=present_value_of_forecast,
        terminal_value=terminal_value,
        present_value_of_terminal_value=present_value_of_terminal,
        enterprise_value=enterprise_value,
        equity_value=equity_value,
        implied_value_per_share=implied_value_per_share,
        terminal_value_share_of_ev=terminal_share,
        forecast=forecast,
    )


def sensitivity_grid(
    config: ModelConfig,
    valuation: Valuation,
) -> tuple[tuple[float, tuple[float, ...]], ...]:
    """Calculate implied share value across WACC and terminal-growth changes."""
    steps = config.sensitivity_steps_each_side
    offsets = tuple(
        step * config.sensitivity_step for step in range(-steps, steps + 1)
    )
    growth_rates = tuple(config.terminal_growth_rate + offset for offset in offsets)
    wacc_rates = tuple(valuation.wacc + offset for offset in offsets)

    rows: list[tuple[float, tuple[float, ...]]] = []
    for wacc in wacc_rates:
        values: list[float] = []
        for growth in growth_rates:
            (
                _,
                _,
                _,
                enterprise_value,
            ) = discounted_enterprise_value(valuation.forecast, wacc, growth)
            equity_value = enterprise_value - config.debt + config.cash
            values.append(equity_value / config.shares_outstanding)
        rows.append((wacc, tuple(values)))
    return tuple(rows)
