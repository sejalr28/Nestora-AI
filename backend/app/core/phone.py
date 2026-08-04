def normalize_phone(raw: str) -> str:
    """Strips Twilio's 'whatsapp:' prefix and surrounding whitespace, so a
    number coming from the WhatsApp webhook and one entered via the admin
    dashboard end up identical in the DB."""
    return raw.replace("whatsapp:", "").strip()