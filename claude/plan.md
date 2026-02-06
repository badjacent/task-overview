# Plan: Resettable Convertible Bond Explainer System

## Context

A prior Codex session created prototype files: `resettable_cb_checks.py` (validation), `resettable_cb_test_suite.py` (scenarios), `resettable_cb_universe.json` (4 synthetic bonds), and `resettable_cb_explainer.md` (documentation). These are solid starting points but have gaps:

- **Data model is implicit** — everything is raw dicts, no typed schema
- **Percent convention bug** — the validator checks `[0.25, 4.0]` (ratio convention) but the universe JSON uses `70.0`/`90.0`/`110.0` (human-percent convention). Every bond in the universe would fail validation.
- **No narrative code** — explanations exist only as prose in the markdown file
- **No face-value scaling check** — the #1 QuantLib data error (100 vs 1000 face value)
- **Universe missing market data** — bonds have no paired market scenarios
- **No bad-data test cases** — nothing to validate that the validator catches errors
- **No pricer integration contract** — no abstract interface for the client's QuantLib pricer

Research confirmed: QuantLib does NOT natively support resettable conversion prices (fixed at construction). The client's pricer handles resets externally. Our system is an explainer layer on top, not a pricer.

## Deliverables

### 1. `cb_explainer/` Python package

```
cb_explainer/
    __init__.py
    models.py                  # Typed dataclasses: CBInstrument, ResetTerms, MarketData, PricerOutput
    validation/
        __init__.py
        engine.py              # validate() dispatcher, Issue dataclass, registry
        checks_dates.py        # Date sanity (maturity, issue, reset dates)
        checks_reset.py        # Reset floor/cap ordering, direction consistency
        checks_market.py       # Spot vs conversion price, vol range, credit spread
        checks_scaling.py      # Face 100-vs-1000, percent-vs-ratio detection
        checks_cross_ccy.py    # FX completeness for cross-currency bonds
    narrative/
        __init__.py
        engine.py              # generate() → Narrative with summary + greeks explanation
        regimes.py             # Regime enum + classify() based on moneyness, reset proximity
        templates.py           # Text templates per regime (bond-floor, reset-optionality, ITM, etc.)
        decomposition.py       # bond_floor + option_value arithmetic
    universe/
        __init__.py
        loader.py              # load_universe(), get_with_market()
        bonds.json             # 7 bonds (4 existing + 3 new)
        market_scenarios.json  # 3-4 market states per bond
    scenarios/
        __init__.py
        definitions.py         # Ported from resettable_cb_test_suite.py
        runner.py              # Execute scenarios against a PricerAdapter
        adapter.py             # Abstract PricerAdapter ABC + MockAdapter for testing
tests/
    test_validation.py         # Validate all universe bonds + bad-data examples
    test_narrative.py          # Generate narratives for each bond × scenario
    test_scenarios.py          # Run scenario suite against mock adapter
```

### 2. Key design decisions

- **Percent convention**: All `_pct` fields use human-readable percentages (`70.0` = 70%). Fix the validator's `[0.25, 4.0]` range — the detection of ratio-vs-percent encoding becomes a check itself (if value < 1.0, likely a ratio; if > 200, likely basis points).
- **Explicit `face_value` field**: Store it on the instrument. Cross-check `face_value / conversion_price ≈ conversion_ratio`.
- **Registry pattern for checks**: Each check is a decorated function. Easy to add/remove without touching the engine.
- **Regime-based narratives**: Classify into regimes (bond-floor-dominated, reset-optionality, in-the-money, soft-call-capped, cross-currency, distressed), then generate from templates. Framework: "compare to straight bond + stock option".
- **PricerAdapter ABC**: The explainer does NOT import QuantLib. The client implements `PricerAdapter.price(instrument, market) → PricerOutput`.

### 3. Universe expansion (4 → 7 bonds)

| ID | Description | Tests |
|----|-------------|-------|
| `JP_BANK_RESET_STEPDOWN` | (existing) Monthly reset, 70% floor | Standard MSCB |
| `JP_BANK_RESET_ANNUAL_FLOOR` | (existing) Annual reset, zero coupon, 60% floor | Deep floor |
| `CROSS_CCY_RESET` | (existing) USD/JPY cross-currency | FX sensitivity |
| `VANILLA_CB_SOFT_CALL` | (existing) No reset, soft call only | Baseline |
| `JP_STEEL_LARGE_ISSUE` | New: Modeled on Nippon Steel pattern, 80% floor, 5d avg close | High-floor, short maturity |
| `JP_ZERO_COUPON_DEEP_FLOOR` | New: Zero coupon, 50% floor, monthly | Extreme dilution protection |
| `BAD_DATA_EXAMPLE` | New: Intentionally broken (floor_pct=0.70, face=1000, spread=0) | Validates that checks catch errors |

Each bond gets 3-4 market scenarios: `base`, `deep_otm`, `itm`, `pre_reset_stressed`.

### 4. Validation checks (expanded from existing)

**Keep from existing**: date sanity, floor≤cap, spot-vs-conversion, spot-vs-reset, conversion ratio positive, coupon range, cross-currency FX, reset dates before maturity, vol range.

**Add new**:
- `checks_scaling.face_value_consistency` — `face / conversion_price ≈ conversion_ratio` (catches 100-vs-1000)
- `checks_scaling.percent_vs_ratio_encoding` — detects `0.70` (should be `70.0`) or `7000` (basis points)
- `checks_market.credit_spread_staleness` — warns on exactly-zero or suspiciously round spreads
- `checks_reset.direction_consistency` — downward-only + cap>100 is redundant (warn)
- `checks_reset.reset_to_parity_range` — must be between 50% and 150%

### 5. Narrative regimes

| Regime | Trigger | Core message |
|--------|---------|--------------|
| BOND_FLOOR_DOMINATED | bond_floor > 90% of price, moneyness < 0.7 | "Conversion unlikely, value is mostly straight bond + default risk" |
| RESET_OPTIONALITY | Next reset < 60 days, spot < conversion_price | "Reset can lower strike, adding option value even when OTM" |
| IN_THE_MONEY | moneyness > 1.3 | "CB behaves like shares + credit floor, delta near conversion ratio" |
| SOFT_CALL_CAPPED | parity > soft_call threshold | "Issuer can call, capping upside — delta and gamma flatten" |
| CROSS_CURRENCY | bond_ccy ≠ equity_ccy | "FX shifts change parity; equity delta mixes with FX delta" |
| DISTRESSED | credit_spread > 1000bps or near-default | "Credit risk dominates; bond floor itself is uncertain" |

Each narrative includes: summary text, value decomposition (bond floor % + option value %), greeks explanation, and data warnings from validation.

## Implementation sequence

1. **`models.py`** — All dataclasses. This is the contract everything depends on.
2. **`universe/`** — Migrate JSON, add 3 new bonds, add market scenarios, write loader.
3. **`validation/`** — Registry + engine + all check modules. Port and fix existing checks.
4. **`narrative/`** — Regimes, decomposition, templates, engine.
5. **`scenarios/`** — PricerAdapter ABC, mock adapter, port definitions, runner.
6. **`tests/`** — Validation tests, narrative tests, scenario tests.

## Verification

- `python -m pytest tests/` passes all tests
- `python -c "from cb_explainer.validation.engine import validate"` imports cleanly
- Run validation on `BAD_DATA_EXAMPLE` → catches all intentional errors
- Run narrative on each bond × base scenario → produces non-empty text
- Run scenario suite against mock adapter → all qualitative expectations pass
