"""
Branded HTML email templates for Empire workroom communications.

All templates use inline styles (email-client safe), mobile-responsive layout,
and Empire brand colors: off-white #f5f3ef, gold #b8960c, text #333.
"""

from app.config.business_config import biz


def _fmt_money(value) -> str:
    """Format a numeric value as $X,XXX.XX."""
    try:
        v = float(value)
        return f"${v:,.2f}"
    except (ValueError, TypeError):
        return str(value)


def _base_wrapper(content: str, preheader: str = "") -> str:
    """Wrap email content in the branded outer shell."""
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{biz.business_name}</title>
</head>
<body style="margin:0;padding:0;background-color:#f5f3ef;font-family:Georgia,'Times New Roman',serif;">
<!-- Preheader (hidden preview text) -->
<span style="display:none;font-size:1px;color:#f5f3ef;line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;">
{preheader}
</span>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f5f3ef;">
<tr><td align="center" style="padding:24px 16px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;background-color:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
<!-- Gold header bar -->
<tr><td style="background-color:#b8960c;padding:24px 32px;text-align:center;">
<h1 style="margin:0;font-size:24px;font-weight:700;color:#ffffff;letter-spacing:0.5px;">{biz.business_name}</h1>
<p style="margin:4px 0 0;font-size:13px;color:rgba(255,255,255,0.85);font-style:italic;">RG's Drapery &amp; Upholstery</p>
</td></tr>
<!-- Content area -->
<tr><td style="padding:32px;">
{content}
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""


def _cta_button(label: str, url: str) -> str:
    """Render a gold call-to-action button."""
    return f"""\
<table role="presentation" cellpadding="0" cellspacing="0" style="margin:28px auto;">
<tr><td align="center" style="background-color:#b8960c;border-radius:6px;">
<a href="{url}" target="_blank" style="display:inline-block;padding:14px 36px;color:#ffffff;font-size:16px;font-weight:700;text-decoration:none;font-family:Georgia,'Times New Roman',serif;">
{label}
</a>
</td></tr>
</table>"""


def _line_items_table(items: list) -> str:
    """Render a line-items table from a list of dicts with 'description', 'qty', 'unit_price', 'total'."""
    rows = ""
    for item in items:
        desc = item.get("description", "")
        qty = item.get("qty", item.get("quantity", 1))
        unit = _fmt_money(item.get("unit_price", item.get("rate", 0)))
        total = _fmt_money(item.get("total", item.get("amount", 0)))
        rows += f"""\
<tr>
<td style="padding:10px 12px;border-bottom:1px solid #e8e4de;color:#333;font-size:14px;">{desc}</td>
<td style="padding:10px 12px;border-bottom:1px solid #e8e4de;color:#333;font-size:14px;text-align:center;">{qty}</td>
<td style="padding:10px 12px;border-bottom:1px solid #e8e4de;color:#333;font-size:14px;text-align:right;">{unit}</td>
<td style="padding:10px 12px;border-bottom:1px solid #e8e4de;color:#333;font-size:14px;text-align:right;">{total}</td>
</tr>"""

    return f"""\
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e8e4de;border-radius:6px;overflow:hidden;margin:20px 0;">
<tr style="background-color:#f9f7f3;">
<th style="padding:10px 12px;text-align:left;font-size:13px;color:#666;font-weight:600;border-bottom:2px solid #b8960c;">Description</th>
<th style="padding:10px 12px;text-align:center;font-size:13px;color:#666;font-weight:600;border-bottom:2px solid #b8960c;">Qty</th>
<th style="padding:10px 12px;text-align:right;font-size:13px;color:#666;font-weight:600;border-bottom:2px solid #b8960c;">Unit Price</th>
<th style="padding:10px 12px;text-align:right;font-size:13px;color:#666;font-weight:600;border-bottom:2px solid #b8960c;">Total</th>
</tr>
{rows}
</table>"""


def _footer(extra_line: str = "") -> str:
    """Branded footer with business info."""
    extra = f'<p style="margin:8px 0 0;font-size:12px;color:#999;">{extra_line}</p>' if extra_line else ""
    return f"""\
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">
<tr><td style="padding:24px 32px;background-color:#f9f7f3;border-top:1px solid #e8e4de;text-align:center;">
<p style="margin:0;font-size:14px;font-weight:600;color:#b8960c;">RG's Drapery &amp; Upholstery</p>
<p style="margin:6px 0 0;font-size:12px;color:#999;">Washington, DC Metro Area</p>
<p style="margin:4px 0 0;font-size:12px;color:#999;">Powered by {biz.business_name}</p>
{extra}
</td></tr>
</table>"""


# ── Public template functions ──────────────────────────────────────


def render_quote_sent(quote_data: dict) -> str:
    """
    Render a 'Your quote is ready' email.

    Expected quote_data keys:
        customer_name, quote_number, project_description, line_items (list),
        total, quote_url
    Optional: phone, address
    """
    name = quote_data.get("customer_name", "Valued Customer")
    quote_num = quote_data.get("quote_number", "")
    project = quote_data.get("project_description", "")
    items = quote_data.get("line_items", [])
    total = _fmt_money(quote_data.get("total", 0))
    quote_url = quote_data.get("quote_url", "#")

    content = f"""\
<p style="margin:0 0 16px;font-size:16px;color:#333;line-height:1.6;">
Dear {name},
</p>
<p style="margin:0 0 16px;font-size:16px;color:#333;line-height:1.6;">
Thank you for your interest in our services. Your quote is ready for review.
</p>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:16px 0;background-color:#f9f7f3;border-radius:6px;border-left:4px solid #b8960c;">
<tr><td style="padding:16px 20px;">
<p style="margin:0;font-size:14px;color:#666;">Quote Number</p>
<p style="margin:4px 0 0;font-size:18px;font-weight:700;color:#333;">#{quote_num}</p>
{"<p style='margin:12px 0 0;font-size:14px;color:#666;'>Project</p><p style='margin:4px 0 0;font-size:15px;color:#333;'>" + project + "</p>" if project else ""}
</td></tr>
</table>
{_line_items_table(items) if items else ""}
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 8px;">
<tr>
<td style="padding:12px 0;font-size:18px;font-weight:700;color:#333;">Total</td>
<td style="padding:12px 0;font-size:18px;font-weight:700;color:#b8960c;text-align:right;">{total}</td>
</tr>
</table>
{_cta_button("View Full Quote", quote_url)}
<p style="margin:16px 0 0;font-size:14px;color:#666;line-height:1.5;text-align:center;">
If you have any questions, please don't hesitate to reach out. We look forward to working with you.
</p>"""

    footer = _footer("Phone &amp; address provided upon booking confirmation")
    html = _base_wrapper(content, preheader=f"Quote #{quote_num} is ready for your review")
    # Insert footer before closing wrapper table
    html = html.replace("</table>\n</td></tr>\n</table>\n</body>",
                         f"{footer}</table>\n</td></tr>\n</table>\n</body>")
    return html


def render_invoice_sent(invoice_data: dict) -> str:
    """
    Render an 'Invoice from {business}' email.

    Expected invoice_data keys:
        customer_name, invoice_number, due_date, line_items (list),
        total, balance_due, payment_url
    Optional: payment_methods
    """
    name = invoice_data.get("customer_name", "Valued Customer")
    inv_num = invoice_data.get("invoice_number", "")
    due_date = invoice_data.get("due_date", "")
    items = invoice_data.get("line_items", [])
    total = _fmt_money(invoice_data.get("total", 0))
    balance = _fmt_money(invoice_data.get("balance_due", invoice_data.get("total", 0)))
    payment_url = invoice_data.get("payment_url", "#")
    methods = invoice_data.get("payment_methods", "Check, Zelle, Cash, Credit Card")

    content = f"""\
<p style="margin:0 0 16px;font-size:16px;color:#333;line-height:1.6;">
Dear {name},
</p>
<p style="margin:0 0 16px;font-size:16px;color:#333;line-height:1.6;">
Please find your invoice below. We appreciate your business and look forward to continuing to serve you.
</p>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:16px 0;background-color:#f9f7f3;border-radius:6px;border-left:4px solid #b8960c;">
<tr><td style="padding:16px 20px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">
<tr>
<td style="width:50%;">
<p style="margin:0;font-size:14px;color:#666;">Invoice Number</p>
<p style="margin:4px 0 0;font-size:18px;font-weight:700;color:#333;">#{inv_num}</p>
</td>
<td style="width:50%;text-align:right;">
<p style="margin:0;font-size:14px;color:#666;">Due Date</p>
<p style="margin:4px 0 0;font-size:18px;font-weight:700;color:#333;">{due_date}</p>
</td>
</tr>
</table>
</td></tr>
</table>
{_line_items_table(items) if items else ""}
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">
<tr>
<td style="padding:8px 0;font-size:15px;color:#666;">Subtotal</td>
<td style="padding:8px 0;font-size:15px;color:#333;text-align:right;">{total}</td>
</tr>
<tr>
<td style="padding:12px 0;font-size:18px;font-weight:700;color:#333;border-top:2px solid #b8960c;">Balance Due</td>
<td style="padding:12px 0;font-size:18px;font-weight:700;color:#b8960c;text-align:right;border-top:2px solid #b8960c;">{balance}</td>
</tr>
</table>
{_cta_button("Pay Now", payment_url)}
<p style="margin:16px 0 0;font-size:14px;color:#666;line-height:1.5;text-align:center;">
Thank you for your prompt payment.
</p>"""

    footer = _footer(f"Accepted payment methods: {methods}")
    html = _base_wrapper(content, preheader=f"Invoice #{inv_num} — {balance} due {due_date}")
    html = html.replace("</table>\n</td></tr>\n</table>\n</body>",
                         f"{footer}</table>\n</td></tr>\n</table>\n</body>")
    return html


def render_payment_received(payment_data: dict) -> str:
    """
    Render a 'Payment Received' confirmation email.

    Expected payment_data keys:
        customer_name, reference_number (invoice or quote #),
        amount_paid, payment_method, payment_date, receipt_url
    """
    name = payment_data.get("customer_name", "Valued Customer")
    ref = payment_data.get("reference_number", "")
    amount = _fmt_money(payment_data.get("amount_paid", 0))
    method = payment_data.get("payment_method", "")
    date = payment_data.get("payment_date", "")
    receipt_url = payment_data.get("receipt_url", "#")

    content = f"""\
<p style="margin:0 0 16px;font-size:16px;color:#333;line-height:1.6;">
Dear {name},
</p>
<p style="margin:0 0 16px;font-size:16px;color:#333;line-height:1.6;">
We have received your payment. Thank you for your business!
</p>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:16px 0;background-color:#f9f7f3;border-radius:6px;border-left:4px solid #b8960c;">
<tr><td style="padding:20px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">
<tr>
<td style="padding:6px 0;">
<p style="margin:0;font-size:14px;color:#666;">Reference</p>
<p style="margin:4px 0 0;font-size:16px;font-weight:600;color:#333;">#{ref}</p>
</td>
</tr>
<tr>
<td style="padding:6px 0;">
<p style="margin:0;font-size:14px;color:#666;">Amount Paid</p>
<p style="margin:4px 0 0;font-size:22px;font-weight:700;color:#b8960c;">{amount}</p>
</td>
</tr>
<tr>
<td style="padding:6px 0;">
<p style="margin:0;font-size:14px;color:#666;">Payment Method</p>
<p style="margin:4px 0 0;font-size:16px;color:#333;">{method}</p>
</td>
</tr>
<tr>
<td style="padding:6px 0;">
<p style="margin:0;font-size:14px;color:#666;">Date</p>
<p style="margin:4px 0 0;font-size:16px;color:#333;">{date}</p>
</td>
</tr>
</table>
</td></tr>
</table>
{_cta_button("View Receipt", receipt_url)}
<p style="margin:16px 0 0;font-size:14px;color:#666;line-height:1.5;text-align:center;">
We appreciate your trust in our work. If you need anything else, we're just a call away.
</p>"""

    footer = _footer("RG's Drapery &amp; Upholstery &mdash; Quality craftsmanship since day one")
    html = _base_wrapper(content, preheader=f"Payment of {amount} received — thank you!")
    html = html.replace("</table>\n</td></tr>\n</table>\n</body>",
                         f"{footer}</table>\n</td></tr>\n</table>\n</body>")
    return html
