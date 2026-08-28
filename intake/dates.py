from datetime import date, datetime

# ISO first: the columns were DateFields originally, so stored text is almost always ISO.
# The slash formats are belt-and-braces for anything hand-entered; m/d/Y wins ambiguous
# cases deterministically, d/m/Y only ever catches day > 12.
DATE_INPUT_FORMATS = ('%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y')


def parse_date_string(raw: str | None) -> date | None:
    """Parse a legacy free-text date. Returns None for empty or unrecognized input."""
    value = (raw or '').strip()
    for fmt in DATE_INPUT_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None
