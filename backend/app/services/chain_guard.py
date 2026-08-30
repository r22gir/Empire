"""D48 STEP 2 — chain-link guard for the customer→quote→job→invoice→payment chain.

Trust-mode writers used to pass whatever customer_id they were handed
straight into an INSERT. After STEP 1 declared `invoices.customer_id`,
`jobs.customer_id` and `payments.invoice_id` NOT NULL, those writers stopped
corrupting the chain and started raising bare `sqlite3.IntegrityError`
instead — which surfaces to the caller as an HTTP 500 naming an internal
SQLite constraint.

This guard converts that into an explicit, typed refusal raised *before* the
INSERT is attempted, so no partial work (audit rows, number allocation) is
done on a request that cannot succeed.

Deliberately **rejects rather than repairs**: it never looks up or creates a
customer. Writers that legitimately resolve a customer from supplied details
do that themselves, before calling this; the guard only asserts the outcome.

`MissingCustomerLink` subclasses `ValueError` so that callers already mapping
`ValueError` to HTTP 400 — `routers/lifecycle.py` does — need no change.
"""


class MissingCustomerLink(ValueError):
    """A chain writer was asked to create a record with no customer link."""


def require_customer(customer_id, *, writer: str, source: str) -> str:
    """Return `customer_id`, or raise if it is absent.

    Args:
        customer_id: the resolved customer id, or a falsy value.
        writer: the writer refusing, for the operator-facing message.
        source: where the customer link was expected to come from.

    Raises:
        MissingCustomerLink: if `customer_id` is None or empty.
    """
    if not customer_id or not str(customer_id).strip():
        raise MissingCustomerLink(
            f"{writer}: refusing to create a chain record with no customer. "
            f"Expected a customer link from {source}. "
            f"Link a customer to that record first."
        )
    return customer_id


def require_invoice(invoice_id, *, writer: str, source: str) -> str:
    """Return `invoice_id`, or raise if it is absent.

    `payments.invoice_id` is NOT NULL for the same reason; a payment with no
    invoice is unattributable money.
    """
    if not invoice_id or not str(invoice_id).strip():
        raise MissingCustomerLink(
            f"{writer}: refusing to create a payment with no invoice. "
            f"Expected an invoice link from {source}."
        )
    return invoice_id
