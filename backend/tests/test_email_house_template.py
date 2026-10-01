from app.services.max.email_template import render_house_email


WILLARD_BODY = """Willard InterContinental lobby – Maggie O'Neill

Attached:
- Estimate 838 Addendum
- Photo Reference / presentation sheet

Original items: $4,580.99
Add-ons: $4,707.21
Grand total: $9,288.20"""


def test_willard_example_renders_readable_house_email():
    rendered = render_house_email(WILLARD_BODY, recipient_name="Maggie O'Neill")

    assert rendered.plain_text.startswith("Hi Maggie O'Neill,\n\nWillard InterContinental lobby")
    assert "Attached:\n- Estimate 838 Addendum" in rendered.plain_text
    assert "Original items: $4,580.99\nAdd-ons: $4,707.21\nGrand total: $9,288.20" in rendered.plain_text
    assert "Thanks,\n\nNelma's Workroom\nworkroom@empirebox.store\n+1 703-213-6484" in rendered.plain_text

    assert "<p>Hi Maggie O'Neill,</p>" in rendered.html
    assert "<p>Willard InterContinental lobby – Maggie O'Neill</p>" in rendered.html
    assert "<ul><li>Estimate 838 Addendum</li><li>Photo Reference / presentation sheet</li></ul>" in rendered.html
    assert '<table class="amounts"><tbody>' in rendered.html
    assert '<tr><td class="label">Original items</td><td class="amount">$4,580.99</td></tr>' in rendered.html
    assert '<tr class="grand-total"><td class="label">Grand total</td><td class="amount">$9,288.20</td></tr>' in rendered.html
    assert ".amounts .label { text-align: left; }" in rendered.html
    assert ".amounts .amount { text-align: right;" in rendered.html
    assert ".amounts tr.grand-total td { border-top: 1px solid" in rendered.html
    assert "<p>Thanks,</p>" in rendered.html
    assert ".signature { margin-top: 24px; }" in rendered.html
    assert "mailto:workroom@empirebox.store" in rendered.html
