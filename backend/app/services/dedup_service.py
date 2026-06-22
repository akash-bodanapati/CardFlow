import re


def normalize_phone(phone: str) -> str:
    """Strip formatting and handle country code variants.
    e.g. '+91 98765-43210' -> '919876543210'
         '9876543210'      -> '9876543210' (if no country code, just digits)
    """
    if not phone:
        return ""
    # Remove all non-numeric characters except +
    digits = re.sub(r"[^\d+]", "", phone)
    if digits.startswith("+"):
        digits = digits[1:]
    return digits


def normalize_email(email: str) -> str:
    if not email:
        return ""
    return email.strip().lower()


def is_duplicate(
    new_phone: str, new_email: str, existing_rows: list[dict]
) -> dict | None:
    """Checks if a contact is a duplicate. Returns the matched row if found."""
    norm_phone = normalize_phone(new_phone)
    norm_email = normalize_email(new_email)

    for row in existing_rows:
        row_phone = normalize_phone(row.get("Phone", ""))
        row_email = normalize_email(row.get("Email", ""))

        if norm_email and norm_email == row_email:
            return row
        # Match if phone digits match (sometimes country code is missing, so we can check suffix match)
        if norm_phone and row_phone:
            if (
                norm_phone == row_phone
                or norm_phone.endswith(row_phone)
                or row_phone.endswith(norm_phone)
            ):
                # Basic check to avoid matching empty or short
                if len(norm_phone) >= 7 and len(row_phone) >= 7:
                    return row

    return None
