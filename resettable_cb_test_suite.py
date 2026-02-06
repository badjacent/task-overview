"""Scenario-driven sanity tests for resettable convertible bond valuation.

These tests are intended for qualitative validation (signs, monotonicity,
regime identification) rather than tight price matching.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List


@dataclass
class Expectation:
    kind: str
    metric: str
    details: Dict[str, Any]


@dataclass
class TestCase:
    id: str
    title: str
    setup: Dict[str, Any]
    expectations: List[Expectation]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "setup": self.setup,
            "expectations": [asdict(e) for e in self.expectations],
        }


def get_suite() -> List[Dict[str, Any]]:
    suite: List[TestCase] = []

    # 1) Default / distressed credit
    suite.append(
        TestCase(
            id="default_recovery",
            title="Price collapses to recovery when default is assumed",
            setup={
                "credit_state": "default",
                "recovery_rate": 0.2,
                "equity_spot": 0.0,
            },
            expectations=[
                Expectation(
                    kind="approx",
                    metric="price",
                    details={"target": "recovery_value", "tolerance_pct": 5.0},
                ),
                Expectation(
                    kind="range",
                    metric="delta",
                    details={"min": -0.05, "max": 0.05},
                ),
            ],
        )
    )

    # 2) Deep out-of-the-money with upcoming reset
    suite.append(
        TestCase(
            id="deep_otm_pre_reset",
            title="Delta near zero when spot is far below conversion and reset floor",
            setup={
                "equity_spot": "very_low",
                "conversion_price": "high",
                "reset_floor_pct": 0.7,
                "time_to_reset_days": 30,
            },
            expectations=[
                Expectation(
                    kind="range",
                    metric="delta",
                    details={"min": 0.0, "max": 0.1},
                ),
                Expectation(
                    kind="dominant_component",
                    metric="price",
                    details={"component": "bond_floor"},
                ),
            ],
        )
    )

    # 3) Deep in-the-money
    suite.append(
        TestCase(
            id="deep_itm",
            title="Delta approaches conversion ratio when equity is very high",
            setup={
                "equity_spot": "very_high",
                "conversion_ratio": "as_input",
                "credit_spread": "normal",
            },
            expectations=[
                Expectation(
                    kind="approx",
                    metric="delta",
                    details={"target": "conversion_ratio", "tolerance_pct": 10.0},
                ),
                Expectation(
                    kind="monotonic",
                    metric="price",
                    details={"wrt": "equity_spot", "direction": "up"},
                ),
            ],
        )
    )

    # 4) Reset event effect on conversion price
    suite.append(
        TestCase(
            id="reset_stepdown",
            title="Conversion price should step down at reset when parity is low",
            setup={
                "equity_spot": "below_conversion",
                "reset_to_parity_pct": 0.9,
                "reset_floor_pct": 0.7,
                "cap_pct": 1.1,
                "time_to_reset_days": 1,
            },
            expectations=[
                Expectation(
                    kind="event",
                    metric="conversion_price",
                    details={"direction": "down", "reason": "reset"},
                ),
                Expectation(
                    kind="jump",
                    metric="delta",
                    details={"direction": "up", "reason": "lowered strike"},
                ),
            ],
        )
    )

    # 5) Soft call reduces upside convexity
    suite.append(
        TestCase(
            id="soft_call_convexity",
            title="Soft call caps upside when parity threshold is sustained",
            setup={
                "equity_spot": "high",
                "soft_call_parity_pct": 1.3,
                "soft_call_days": 20,
                "window_days": 30,
            },
            expectations=[
                Expectation(
                    kind="slope",
                    metric="delta",
                    details={"direction": "flatten"},
                ),
                Expectation(
                    kind="gamma",
                    metric="gamma",
                    details={"direction": "down"},
                ),
            ],
        )
    )

    # 6) Cross-currency sensitivity
    suite.append(
        TestCase(
            id="cross_ccy_fx",
            title="FX moves shift parity and reset reference for cross-currency CB",
            setup={
                "bond_currency": "USD",
                "underlying_currency": "JPY",
                "fx_spot": "move_up",
            },
            expectations=[
                Expectation(
                    kind="monotonic",
                    metric="price",
                    details={"wrt": "fx_spot", "direction": "up_or_down_by_definition"},
                ),
                Expectation(
                    kind="explain",
                    metric="delta",
                    details={"note": "equity delta mixes with FX delta"},
                ),
            ],
        )
    )

    # 7) Volatility sensitivity around reset window
    suite.append(
        TestCase(
            id="volatility_pre_reset",
            title="Higher vol lifts value more when reset window is near",
            setup={
                "equity_vol": "higher",
                "time_to_reset_days": 10,
            },
            expectations=[
                Expectation(
                    kind="monotonic",
                    metric="price",
                    details={"wrt": "equity_vol", "direction": "up"},
                ),
                Expectation(
                    kind="monotonic",
                    metric="vega",
                    details={"wrt": "equity_vol", "direction": "up"},
                ),
            ],
        )
    )

    return [t.to_dict() for t in suite]


if __name__ == "__main__":
    from pprint import pprint

    pprint(get_suite())
