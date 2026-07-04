from __future__ import annotations

# USD per million tokens. Unknown models intentionally use a conservative fallback.
_PRICES: dict[str, tuple[float, float]] = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "claude-sonnet-4": (3.00, 15.00),
    "claude-haiku": (0.80, 4.00),
}
_FALLBACK = (3.00, 15.00)


def estimate_cost(model: str | None, input_tokens: int, output_tokens: int) -> float:
    normalized = (model or "").lower()
    prices = next((price for name, price in sorted(_PRICES.items(), key=lambda item: len(item[0]), reverse=True)
                   if name in normalized), _FALLBACK)
    return round((input_tokens * prices[0] + output_tokens * prices[1]) / 1_000_000, 8)
