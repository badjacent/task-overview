"""Data-quality checks for resettable convertible bonds.

Focus: risk client explainability and actionable diagnostics.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Issue:
    code: str
    severity: str  # "error" | "warn"
    message: str
    params: List[str]
    ui: Dict[str, Any]
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        if payload["details"] is None:
            payload.pop("details")
        return payload


def _get(d: Dict[str, Any], path: str, default: Any = None) -> Any:
    cur: Any = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def _ratio(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None or b == 0:
        return None
    return a / b


def _date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    return date.fromisoformat(s)


def _add(
    issues: List[Issue],
    code: str,
    severity: str,
    message: str,
    params: List[str],
    ui_label: str,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    issues.append(
        Issue(
            code=code,
            severity=severity,
            message=message,
            params=params,
            ui={"label": ui_label, "paths": params, "highlight": True},
            details=details,
        )
    )


def validate(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return a list of issues with UI metadata."""
    inst = data.get("instrument", {})
    mkt = data.get("market", {})
    reset = inst.get("reset", {})
    issues: List[Issue] = []

    # Core dates
    val_date = _date(mkt.get("valuation_date"))
    issue_date = _date(inst.get("issue_date"))
    maturity = _date(inst.get("maturity_date"))

    if val_date and maturity and val_date >= maturity:
        _add(
            issues,
            code="date.maturity_in_past",
            severity="error",
            message=(
                "Valuation date must be before maturity; the bond appears expired."
            ),
            params=["market.valuation_date", "instrument.maturity_date"],
            ui_label="Dates",
            details={"valuation_date": str(val_date), "maturity_date": str(maturity)},
        )

    if issue_date and maturity and issue_date >= maturity:
        _add(
            issues,
            code="date.issue_after_maturity",
            severity="error",
            message="Issue date must be before maturity.",
            params=["instrument.issue_date", "instrument.maturity_date"],
            ui_label="Dates",
        )

    # Percent bounds for reset parameters
    floor_pct = reset.get("floor_pct")
    cap_pct = reset.get("cap_pct")
    reset_to_parity = reset.get("reset_to_parity_pct")

    def _pct_check(value: Optional[float], path: str, label: str) -> None:
        if value is None:
            return
        if value < 0.25 or value > 4.0:
            _add(
                issues,
                code="bounds.percent",
                severity="error",
                message=(
                    f"{label} must be between 0.25 and 4.0; got {value}. "
                    "Values outside this range often indicate a 100x scaling error."
                ),
                params=[path],
                ui_label="Reset terms",
                details={"value": value, "min": 0.25, "max": 4.0},
            )

    _pct_check(floor_pct, "instrument.reset.floor_pct", "Reset floor percent")
    _pct_check(cap_pct, "instrument.reset.cap_pct", "Reset cap percent")
    _pct_check(
        reset_to_parity,
        "instrument.reset.reset_to_parity_pct",
        "Reset-to-parity percent",
    )

    if floor_pct is not None and cap_pct is not None and floor_pct > cap_pct:
        _add(
            issues,
            code="bounds.floor_gt_cap",
            severity="error",
            message="Reset floor percent must be less than or equal to reset cap percent.",
            params=["instrument.reset.floor_pct", "instrument.reset.cap_pct"],
            ui_label="Reset terms",
        )

    # Equity vs reset reference checks
    spot = mkt.get("equity_spot")
    conv_price = inst.get("conversion_price")
    reset_ref = mkt.get("reset_reference_price", conv_price)

    spot_to_reset = _ratio(spot, reset_ref)
    if spot_to_reset is not None and (spot_to_reset < 0.1 or spot_to_reset > 10.0):
        _add(
            issues,
            code="bounds.spot_vs_reset",
            severity="warn",
            message=(
                "Equity spot is more than 10x away from reset reference price. "
                "Check scaling or currency mismatches."
            ),
            params=["market.equity_spot", "market.reset_reference_price"],
            ui_label="Equity vs reset",
            details={"spot": spot, "reset_reference": reset_ref},
        )

    spot_to_conv = _ratio(spot, conv_price)
    if spot_to_conv is not None and (spot_to_conv < 0.1 or spot_to_conv > 10.0):
        _add(
            issues,
            code="bounds.spot_vs_conversion",
            severity="warn",
            message=(
                "Equity spot is more than 10x away from conversion price. "
                "Verify the conversion price or equity spot input."
            ),
            params=["market.equity_spot", "instrument.conversion_price"],
            ui_label="Equity vs conversion",
            details={"spot": spot, "conversion_price": conv_price},
        )

    # Basic numeric sanity
    if inst.get("conversion_ratio", 0) <= 0:
        _add(
            issues,
            code="bounds.conversion_ratio",
            severity="error",
            message="Conversion ratio must be positive.",
            params=["instrument.conversion_ratio"],
            ui_label="Conversion terms",
        )

    if inst.get("coupon_rate", 0) < 0 or inst.get("coupon_rate", 0) > 0.5:
        _add(
            issues,
            code="bounds.coupon_rate",
            severity="warn",
            message="Coupon rate looks unusual; expected 0 to 0.5 (50%).",
            params=["instrument.coupon_rate"],
            ui_label="Cashflows",
            details={"coupon_rate": inst.get("coupon_rate")},
        )

    # Cross-currency requirements
    bond_ccy = inst.get("bond_currency")
    und_ccy = inst.get("underlying_currency")
    if bond_ccy and und_ccy and bond_ccy != und_ccy:
        fx_spot = _get(mkt, "fx.fx_spot")
        fx_vol = _get(mkt, "fx.fx_vol")
        if fx_spot is None:
            _add(
                issues,
                code="missing.fx_spot",
                severity="error",
                message="Cross-currency conversion requires fx_spot.",
                params=["market.fx.fx_spot"],
                ui_label="FX",
            )
        if fx_vol is None:
            _add(
                issues,
                code="missing.fx_vol",
                severity="warn",
                message="Cross-currency conversion should include fx_vol for convexity risk.",
                params=["market.fx.fx_vol"],
                ui_label="FX",
            )

    # Reset schedule checks
    reset_dates = reset.get("reset_dates")
    if isinstance(reset_dates, list) and maturity:
        for i, d in enumerate(reset_dates):
            rd = _date(d)
            if rd and rd >= maturity:
                _add(
                    issues,
                    code="date.reset_after_maturity",
                    severity="error",
                    message="Reset date must be before maturity.",
                    params=[f"instrument.reset.reset_dates[{i}]"],
                    ui_label="Reset schedule",
                    details={"reset_date": d, "maturity": str(maturity)},
                )

    # Volatility sanity
    eq_vol = mkt.get("equity_vol")
    if eq_vol is not None and (eq_vol < 0.05 or eq_vol > 2.0):
        _add(
            issues,
            code="bounds.equity_vol",
            severity="warn",
            message="Equity volatility looks unusual; expected 5% to 200%.",
            params=["market.equity_vol"],
            ui_label="Volatility",
            details={"equity_vol": eq_vol},
        )

    return [i.to_dict() for i in issues]


if __name__ == "__main__":
    EXAMPLE = {
        "instrument": {
            "issue_date": "2024-06-15",
            "maturity_date": "2031-06-15",
            "bond_currency": "JPY",
            "underlying_currency": "JPY",
            "coupon_rate": 0.005,
            "conversion_price": 1000.0,
            "conversion_ratio": 100000.0,
            "reset": {
                "reset_to_parity_pct": 90.0,
                "floor_pct": 70.0,
                "cap_pct": 110.0,
                "reset_dates": ["2025-06-15", "2026-06-15"],
            },
        },
        "market": {
            "valuation_date": "2026-02-06",
            "equity_spot": 15000.0,
            "reset_reference_price": 1200.0,
            "equity_vol": 0.25,
        },
    }

    for issue in validate(EXAMPLE):
        print(issue)
