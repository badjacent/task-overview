# Research: Japanese Resettable Convertible Bonds

## Key Distinction: Japanese Banks vs. Japanese Corporates

Japanese **megabanks** (MUFG, Mizuho, SMFG) have primarily issued **AT1/CoCo bonds** (Additional Tier 1 contingent convertible bonds) rather than traditional resettable convertible bonds in the 2021-2026 period. These convert to equity or are written down when a bank's capital ratio breaches a regulatory trigger (e.g., CET1 falls below 5.125%).

The classic **resettable convertible bond (MSCB / Moving Strike Convertible Bond)** is more commonly issued by **Japanese corporates**. The megabanks historically issued resettable CBs during the banking crisis of 1995-1998.

## Recent Japanese Corporate CB Issuances (2022-2026)

| Issuer | Year | Amount | Coupon | Maturity | Key Terms |
|---|---|---|---|---|---|
| **Nippon Steel** | Feb 2026 (considering) | JPY 500bn (~$3.2bn) | Zero coupon | TBD | Would be largest-ever Japan CB |
| **INFRONEER Holdings** | Mar 2024 | Undisclosed | Zero coupon | 2029 | Green CB framework |
| **Resonac Holdings** | Apr 2024 | Undisclosed | Zero coupon | 2028 | Standard CB |
| **JFE Holdings** | Sep 2023 | JPY 90bn (~$614M) | Undisclosed | Undisclosed | Most sought-after Asian equity-linked in six years |
| **Daiwa House Industry** | 2023 | JPY 200bn (~$1.38bn) | Undisclosed | Undisclosed | Dual-tranche, offered at 102.5 |
| **Yaoko Co.** | Pre-2022 | Undisclosed | Zero coupon | 2024 | Conversion price adjusted from JPY 6,044.80 to JPY 6,026.20 (anti-dilution from dividend) |

The Japanese CB market experienced a **486.2% rise in deal volume in 2024**. Most recent Japanese CBs are **zero-coupon** structures.

## Typical Japanese MSCB Reset Mechanisms

### Mechanism A: Annual Reset (Classic Bank Style, 1995-1998)
- Frequency: Annually on specified date
- Reference: Closing stock price on reset date
- New CP: Equal to closing price
- Direction: Downward only
- Floor: 50-80% of original CP

### Mechanism B: Monthly MSCB Reset (Modern Corporate Style)
- Determination date: Business day following 2nd Monday of each month
- Reference: Average closing price of 5 consecutive trading days ending on determination date
- New CP: 90% × Reference Price (10% discount)
- Direction: Downward only (typical) or bidirectional (less common)
- Floor: 50-80% of original CP
- Cap: Original CP
- Regulatory: Reset intervals must be >= 6 months if floor allows CP below original reference (TSE 2007)

### Mechanism C: Conditional Reset (Chinese-Style)
- Trigger: Stock < 70% of CP for 20 of 30 consecutive trading days
- Decision: Issuer has the right (not obligation) to propose
- Shareholder approval required (2/3 supermajority)
- New CP: Not lower than higher of (a) 20-day avg or (b) prior day close

## Data Schema for Convertible Bond Risk Valuation

### Core Bond Fields
- issuer_name, isin/cusip, currency, issue_date, maturity_date, par_value
- issue_price, coupon_rate, coupon_frequency, day_count_convention
- redemption_price, credit_rating, seniority

### Conversion / Equity-Linked Fields
- underlying_equity, conversion_price, conversion_ratio
- conversion_premium (25-45% typical in Japan)
- conversion_start_date, conversion_end_date
- stock_reference_price, anti_dilution_adjustments, dividend_protection

### Call Schedule
- hard_call_protection_end, hard_call_price
- soft_call_trigger (e.g., 130% of conversion price)
- soft_call_observation_period (20 of 30 consecutive trading days)
- soft_call_start_date, soft_call_price, make_whole_provision, call_notice_period

### Put Schedule
- put_dates, put_price, change_of_control_put

### Reset-Specific Fields
- reset_type, reset_dates, reset_determination_date
- reset_reference_price_method ("closing price" or "5-day avg close" or "20d VWAP")
- reset_percentage_of_parity (e.g., 90%)
- reset_floor (absolute or % of initial CP)
- reset_cap (may equal initial CP)
- reset_direction (downward only / bidirectional)
- reset_lookback_period, reset_frequency
- reset_trigger_condition, reset_effective_date

### Cross-Currency Fields
- bond_currency, equity_currency, fx_rate_for_conversion
- quanto_feature, settlement_currency, cross_currency_basis, fx_hedge_cost

### Model / Valuation Inputs
- stock_price, stock_volatility, risk_free_rate_curve
- credit_spread, borrow_cost, dividend_forecast
- fx_spot_rate, fx_volatility, stock_fx_correlation

## Valuation Complexity

### Path Dependency
Resettable CBs are path-dependent. The conversion price depends on stock price at prior reset dates. Standard lattice/PDE methods become complex; Monte Carlo is often necessary.

### Non-Monotonic Price Behavior
Near a reset date, if stock is below CP, expected reset increases conversion ratio (more valuable). But if stock is just above CP, no reset occurs. This creates discontinuities.

### Common Data Errors
1. **Confusing anti-dilution adjustments with resets** — price changes from stock splits/dividends vs. market-driven resets
2. **Incorrect reset floor/cap encoding** — percentage vs. absolute price, or ratio vs. percent
3. **Wrong lookback period** — single close vs. 5-day average vs. VWAP
4. **Ignoring direction constraint** — downward-only vs. bidirectional
5. **Date confusion** — determination date vs. reset date vs. effective date
6. **Death spiral / dilution spiral** — falling stock → reset down → more dilution → stock falls further (TSE prohibited most aggressive forms in 2007)
7. **Cross-currency basis neglect** — JPY/USD basis is the most extreme among major currencies
8. **Stale credit spreads** — single spread for whole instrument ignores different credit sensitivities of debt vs. equity components
