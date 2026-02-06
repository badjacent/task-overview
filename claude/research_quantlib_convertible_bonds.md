# Research: QuantLib Convertible Bond Pricing

## QuantLib Classes

### Instrument Classes
- **`ConvertibleFixedCouponBond`** — Fixed periodic coupons
- **`ConvertibleZeroCouponBond`** — Zero-coupon (discount)
- **`ConvertibleFloatingRateBond`** — Floating-rate (IBOR-linked)

All inherit from `ConvertibleBond` base class.

### Pricing Engine
- **`BinomialConvertibleEngine<T>`** — Tsiveriotis-Fernandes method, splits value into "bond component" (credit-risky) and "equity component" (credit-risk-free).

Seven supported tree types: Jarrow-Rudd, Cox-Ross-Rubinstein, Additive Equiprobabilities, Trigeorgis, Tian, Leisen-Reimer, Joshi.

### Supporting Classes
- `BlackScholesMertonProcess` — equity dynamics
- `CallabilitySchedule` / `Callability` — call/put provisions
- `SoftCallability` — simple price trigger (NOT m-over-n)
- `DividendSchedule` — discrete dividends
- `CallabilityPrice` — clean or dirty

## Critical: What QuantLib Does NOT Support

| Feature | Support | Workaround |
|---------|---------|------------|
| Fixed conversion ratio | Yes | — |
| Hard call/put schedules | Yes | — |
| Simple soft call trigger | Partial (no m/n counting) | Manual per-day entries |
| **Reset/ratchet on conversion price** | **No** | Custom engine or Monte Carlo |
| **Mandatory conversion** | **No** | Custom engine |
| **Path-dependent m/n soft call** | **No** | Custom engine, or consider ORE |

## Critical Pitfalls

### 1. Face Value Hard-Coded to 100
QuantLib assumes face=100. Most vendors (Bloomberg) use face=1000. **You must divide vendor conversion ratios by 10.** This is the #1 source of pricing errors.

### 2. Dividend Double-Counting
BSM process takes continuous yield; bond constructor takes discrete `DividendSchedule`. Using both double-counts. Use one or the other.

### 3. Yield Curve Flattening
The binomial engine extracts only the zero rate at maturity. It treats the curve as flat at that rate. Key rate duration analysis is meaningless.

### 4. No m-over-n Soft Call
`SoftCallability` models a simple price trigger on specific dates, not "20 out of 30 days." QuantLib maintainer confirmed this won't be implemented (GitHub #1741).

### 5. No Resettable Conversion Price
Conversion ratio is fixed at construction. No mechanism for market-driven resets.

### 6. Time Step Sensitivity
Use at least 800-1000 steps. Test suite uses 1001-2001 steps, tolerates 1-2% errors.

## Python Usage Pattern

```python
import QuantLib as ql

# Key: conversion_ratio must be for face=100
# If Bloomberg says 38.4615, use 3.84615
conversion_ratio = face_value_100 / conversion_price

bond = ql.ConvertibleFixedCouponBond(
    exercise, conversion_ratio, dividend_schedule,
    callability_schedule, credit_spread_handle,
    issue_date, settlement_days, [coupon_rate],
    day_count, schedule, 100.0
)

engine = ql.BinomialConvertibleEngine(bsm_process, "crr", 1000)
bond.setPricingEngine(engine)
price = bond.NPV()
```

## Greeks (All Numerical via Bump-and-Revalue)

The engine provides NO analytical greeks. Must compute via:
- **Delta**: bump spot ±h, central difference
- **Gamma**: second-order from same bumps
- **Vega**: bump vol +1%
- **Rho**: bump risk-free rate +1bp
- **Theta**: advance evaluation date +1 day
- **CS01**: bump credit spread +1bp

Key: use `ql.SimpleQuote` objects so bumps propagate without rebuilding.

## Required Pricing Inputs

| Input | Notes |
|-------|-------|
| Stock spot price | Current equity price |
| Risk-free yield curve | For discounting equity component |
| Dividend yield OR discrete dividends | **Not both** |
| Equity volatility | Flat or surface |
| Credit spread | For bond component discount |
| Coupon rate(s) | Annual rate |
| Conversion ratio | **Scaled for face=100** |
| Call/put schedule | `Callability` and `SoftCallability` objects |
| Time steps | 800-2000 for production |
