from app.services.max.email_template import render_house_email


WILLARD_BODY = """Willard InterContinental lobby – Maggie O'Neill

Attached:
- Estimate 838 Addendum
- Photo Reference / presentation sheet

Original items: $4,580.99
Add-ons: $4,175.30
Grand total: $8,756.29
Optional passway hardware: $531.91
Total with hardware: $9,288.20"""


def test_willard_example_renders_readable_house_email():
    rendered = render_house_email(WILLARD_BODY)

    assert "Attached:\n- Estimate 838 Addendum" in rendered.plain_text
    assert "Original items: $4,580.99\nAdd-ons: $4,175.30" in rendered.plain_text
    assert "Empire Workroom\nRafael Giraldo\nworkroom@empirebox.store\n+1 703-213-6484" in rendered.plain_text

    assert "<p>Willard InterContinental lobby – Maggie O'Neill</p>" in rendered.html
    assert "<ul><li>Estimate 838 Addendum</li><li>Photo Reference / presentation sheet</li></ul>" in rendered.html
    assert '<table class="amounts"><tbody>' in rendered.html
    assert "<th scope=\"row\">Original items</th><td>$4,580.99</td>" in rendered.html
    assert "<th scope=\"row\">Total with hardware</th><td>$9,288.20</td>" in rendered.html
    assert "Empire Workroom" in rendered.html
    assert "mailto:workroom@empirebox.store" in rendered.html
