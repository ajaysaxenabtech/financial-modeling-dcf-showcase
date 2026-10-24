# Financial Modeling Showcase: Scenario-Driven DCF

A compact, auditable discounted cash flow (DCF) model for valuing an illustrative
software company. It forecasts unlevered free cash flow, derives WACC using CAPM
and the after-tax cost of debt, calculates terminal value, and shows how the
implied share value changes across operating and valuation scenarios.

All sample inputs describe a fictional company. They are included to demonstrate
the model mechanics and are not market data or investment guidance.

## Use case

An analyst needs a repeatable way to connect operating assumptions to intrinsic
value, compare bear, base, and bull outcomes, and explain which assumptions drive
the result. This project makes the calculation path visible from revenue growth
through implied value per share.

## What it includes

- Five-year revenue and EBITDA forecasts for bear, base, and bull cases
- Unlevered free cash flow based on NOPAT, D&A, capital expenditure, and changes
  in net working capital
- CAPM cost of equity and after-tax cost of debt to calculate WACC
- Gordon growth terminal value and bridge from enterprise value to equity value
- WACC versus terminal growth sensitivity table for each operating case
- CSV outputs suitable for review in Excel or another spreadsheet
- Input validation for missing assumptions, invalid rates, and mismatched forecast
  periods

## Project structure

~~~text
financial-modeling-dcf-showcase/
├── data/
│   └── assumptions.json
├── src/
│   └── dcf_model/
│       ├── assumptions.py
│       ├── cli.py
│       ├── model.py
│       └── reporting.py
├── .gitignore
├── LICENSE
├── pyproject.toml
└── README.md
~~~

## Run it

Requires Python 3.10 or newer. The model has no third-party runtime dependencies.

~~~bash
python -m venv .venv
~~~

Activate the environment, then install the project:

~~~bash
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1

python -m pip install -e .
~~~

Run all operating scenarios:

~~~bash
dcf-model --scenario all
~~~

Or run one scenario, choose an alternate assumptions file, and/or change the
output directory:

~~~bash
dcf-model --scenario base
dcf-model --scenario bear --assumptions data/assumptions.json --output-dir outputs
~~~

Generated files are written under outputs/ (which is ignored by Git):

~~~text
outputs/
├── bear/
│   ├── forecast.csv
│   ├── sensitivity.csv
│   └── summary.csv
├── base/
│   └── ...
├── bull/
│   └── ...
└── scenario_comparison.csv
~~~

scenario_comparison.csv is produced when --scenario all is selected.

## Model methodology

For forecast year *t*:

1. **Revenue** = prior-year revenue × (1 + revenue growth)
2. **EBITDA** = revenue × EBITDA margin
3. **EBIT** = EBITDA − D&A
4. **Cash taxes** = max(EBIT, 0) × tax rate
5. **NOPAT** = EBIT − cash taxes
6. **Change in NWC** = change in revenue × NWC as a percentage of revenue
7. **Unlevered FCF** = NOPAT + D&A − capex − change in NWC

Cost of equity is calculated as risk-free rate + beta × equity risk premium.
WACC weights the cost of equity and after-tax cost of debt using the assumed
equity share of total capital.

Terminal value uses the Gordon growth formula:

~~~text
Terminal value = final forecast-year FCF × (1 + terminal growth) / (WACC − terminal growth)
Enterprise value = PV of forecast FCF + PV of terminal value
Equity value = enterprise value − debt + cash
Implied value per share = equity value / shares outstanding
~~~

## Assumptions and units

Edit data/assumptions.json to change the model. The three operating cases vary
annual revenue growth and EBITDA margin. D&A, capex, and NWC assumptions are
shared across cases. Financial amounts (including debt and cash) are in the
specified monetary unit; the sample uses USD millions. Shares outstanding are
in millions, so the resulting per-share value is in USD.

Rates are stored as decimals: 0.10 means 10%. The model checks that WACC is
greater than terminal growth before calculating terminal value.

## Limitations

This is an educational, annual-period DCF with simplified assumptions. It does
not model working capital line items, net operating losses, tax shields beyond
the WACC debt adjustment, stock-based compensation, leases, debt repayment,
mid-year discounting, or dilution changes. Results are sensitive to the
assumptions, especially terminal growth and WACC.

## License

MIT. See [LICENSE](LICENSE).
