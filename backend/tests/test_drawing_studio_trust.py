import asyncio

from app.routers import drawings


def test_bench_drawing_preview_and_pdf_use_current_dimensions():
    small = drawings.BenchRequest(
        name="Trust Bench",
        lf=6,
        seat_depth=20,
        seat_height=18,
        back_height=18,
    )
    large = drawings.BenchRequest(
        name="Trust Bench",
        lf=8,
        seat_depth=20,
        seat_height=18,
        back_height=18,
    )

    small_svg = asyncio.run(drawings.generate_bench_svg(small))["svg"]
    large_svg = asyncio.run(drawings.generate_bench_svg(large))["svg"]

    assert small_svg != large_svg
    assert "72&quot;" in small_svg
    assert "96&quot;" not in small_svg
    assert "96&quot;" in large_svg
    assert "72&quot;" not in large_svg

    small_pdf = asyncio.run(drawings.generate_bench_pdf(small))
    large_pdf = asyncio.run(drawings.generate_bench_pdf(large))

    assert small_pdf.media_type == "application/pdf"
    assert large_pdf.media_type == "application/pdf"
    assert small_pdf.body != large_pdf.body
    assert small_pdf.body.startswith(b"%PDF")
    assert large_pdf.body.startswith(b"%PDF")
