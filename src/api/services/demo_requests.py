"""demo_requests — persists demo/contact-sales/talk-to-an-expert leads.

Backs ``POST /demo-request``. The ``demo_requests`` table is a recent,
optional addition (see ``scripts/sql/003_demo_requests.sql``) — if it hasn't
been created yet, submissions fail with a specific, catchable error instead
of a raw Postgres/PostgREST error leaking into the API response.
"""

from typing import Any

try:
    from ...infrastructure.database.supabase import get_client
except ImportError:  # pragma: no cover - supports package execution
    from src.infrastructure.database.supabase import get_client


class DemoRequestTableMissingError(RuntimeError):
    """Raised when the ``demo_requests`` table doesn't exist yet."""


def submit_demo_request(
    *,
    name: str,
    email: str,
    company: str | None = None,
    use_case: str | None = None,
    product: str | None = None,
) -> dict[str, Any]:
    """Insert a demo/contact-sales request and return the stored row.

    Args:
        name: The requester's name.
        email: The requester's email address.
        company: The requester's company, if given.
        use_case: Free-text description of what they need, if given.
        product: The solution this request relates to (e.g. ``"SPIDIFY"``),
            if the request originated from a specific solution card.

    Returns:
        The inserted row as returned by Supabase (includes ``id`` and
        ``created_at``), or the submitted payload if Supabase didn't echo
        the row back.

    Raises:
        DemoRequestTableMissingError: The ``demo_requests`` table hasn't
            been created yet (see ``scripts/sql/003_demo_requests.sql``).
    """
    sb_client = get_client()
    payload = {
        "name": name,
        "email": email,
        "company": company,
        "use_case": use_case,
        "product": product,
    }

    try:
        response = sb_client.table("demo_requests").insert(payload).execute()
    except Exception as exc:
        message = str(exc)
        if "Could not find the table" in message or "PGRST205" in message:
            raise DemoRequestTableMissingError(
                "The demo_requests table does not exist yet. "
                "Run scripts/sql/003_demo_requests.sql in Supabase."
            ) from exc
        raise

    rows = response.data or []
    return rows[0] if rows else payload
