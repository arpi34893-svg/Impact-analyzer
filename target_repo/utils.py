def calculate_tax(amount: float) -> float:
    """Calculates tax rate - core business logic function."""
    return amount * 0.15

def format_currency(value: float) -> str:
    return f"${value:.2f}"