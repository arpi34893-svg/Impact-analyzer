from utils import calculate_tax, format_currency

def generate_invoice(subtotal: float):
    tax = calculate_tax(subtotal)
    total = subtotal + tax
    return format_currency(total)