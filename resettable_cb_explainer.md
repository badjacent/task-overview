# Resettable Convertible Bond Explainer (Risk Client)

## Scope and approach
This document is designed for risk users who need operational explanations of
pricing and greeks rather than a deep dive into model math. It pairs:

- A representative synthetic universe for testing and explainers.
- A data schema template for capture and validation.
- Three evaluation sets: data bounds checks, narrative explainers, and scenario
  sanity tests.

## Real-world anchors (Japan, last five years)
Public examples of conversion-price adjustments provide practical reference
points for reset mechanics. For Japanese financial issuers, SBI Holdings (a
Japanese financial group) disclosed multiple conversion price adjustments to
its zero-coupon convertible bonds due to dividends and a stock split between
2023 and 2025. These are not full refixing mechanisms, but they are real-world
reset-style adjustments that affect conversion price and therefore price and
risk.

- 2023-05-12: Adjustment of conversion price for zero coupon CBs due 2023 and
  2025 (dividend related).
- 2024-11-08: Adjustment of conversion price for zero coupon CBs due 2031.
- 2025-05-09: Adjustment of conversion price for zero coupon CBs due 2031.
- 2025-10-31: Adjustment of conversion price for zero coupon CBs due 2031
  following an extraordinary dividend and a stock split.

These disclosures are used only as operational anchors for how adjustments are
communicated and handled in practice. The synthetic universe below is not a
copy of any real issuance.

## Representative universe
See `resettable_cb_universe.json` for a set of synthetic instruments covering:

- Vanilla CB with soft call.
- Resettable CB with floor/cap and periodic refixing.
- Cross-currency resettable CB with FX inputs.
- Zero-coupon style CB with refixing.

## Data schema template (risk valuation view)
Below is a schema template that emphasizes inputs likely to drive unexpected
valuation differences.

```
Instrument
  issuer_type
  issue_date
  maturity_date
  notional
  bond_currency
  underlying_currency
  coupon_rate
  coupon_freq
  conversion_price
  conversion_ratio
  call_schedule[]
  put_schedule[]
  soft_call { parity_pct, days, window_days }
  reset {
    type
    reset_dates
    reset_lag_days
    reset_ref
    reset_to_parity_pct
    floor_pct
    cap_pct
  }
Market
  valuation_date
  equity_spot
  equity_vol
  credit_spread
  rates_curve
  reset_reference_price
  fx { pair, fx_spot, fx_vol }
Model
  engine
  lattice_steps
  dividend_assumptions
  recovery_rate
```

## Evaluation set 1: data bounds checks (code)
Implemented in `resettable_cb_checks.py`. The checks focus on obvious data
problems and provide UI metadata to point users to the suspect fields.

Highlights:
- Percent bounds for reset inputs (0.25 to 4.0).
- Equity spot vs reset reference / conversion price ratio bounds (0.1x to 10x).
- Reset floor <= reset cap.
- Cross-currency FX input completeness.
- Date sanity: valuation before maturity, reset dates before maturity.

## Evaluation set 2: narrative explainers (risk language)
Use the mental model: bond floor + equity option. The narrative explains why
price and greeks behave a certain way, and calls out data issues if signals are
extreme.

Narrative building blocks (examples):

1) Bond-floor dominated
- "Equity is far below the conversion price and even below the reset floor.
  This makes conversion unlikely in the near term, so value is mostly the
  straight bond plus default risk. Delta should be small."

2) Reset optionality dominates
- "A reset is near and parity is below the current conversion price. The reset
  can reduce the conversion price, which increases the option value and delta
  even if the equity is not yet in-the-money."

3) In-the-money equity option
- "Equity is well above the conversion price. The CB behaves like the shares
  plus a bond floor. Delta should be close to the conversion ratio, with some
  reduction from call features."

4) Soft call constraint
- "Parity has exceeded the soft call threshold. This caps upside because the
  issuer can call, so delta and gamma flatten relative to a plain option."

5) Cross-currency sensitivity
- "Because the bond cashflows and the equity are in different currencies, FX
  shifts change parity and therefore the effective moneyness. The equity delta
  is mixed with FX delta."

## Evaluation set 3: scenario sanity tests
Implemented in `resettable_cb_test_suite.py`. These are qualitative tests for
signs and monotonicity rather than tight price matching.

Included scenarios:
- Default / recovery dominates price, delta near zero.
- Deep OTM pre-reset: delta near zero, value near bond floor.
- Deep ITM: delta approaches conversion ratio.
- Reset step-down: conversion price decreases at reset, delta jumps upward.
- Soft call caps convexity.
- Cross-currency FX sensitivity.
- Higher vol raises value near reset window.

## How to use
1) Load a CB from `resettable_cb_universe.json` and market data.
2) Run `resettable_cb_checks.validate()` to surface data issues.
3) Generate a narrative from the building blocks based on moneyness,
   reset proximity, and call features.
4) Run the scenario suite against your pricer and confirm qualitative behavior.
