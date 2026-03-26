#!/usr/bin/env python3
"""Convert SVG to PDF using cairosvg or svglib."""
import subprocess, sys, os

svg_path = '/home/rg/empire-repo/uploads/bench_upholstery_drawing.svg'
pdf_path = '/home/rg/empire-repo/uploads/bench_upholstery_drawing.pdf'

# Try cairosvg first
try:
    import cairosvg
    cairosvg.svg2pdf(url=svg_path, write_to=pdf_path)
    print(f'PDF created with cairosvg: {pdf_path}')
    print(f'Size: {os.path.getsize(pdf_path)} bytes')
    sys.exit(0)
except ImportError:
    print('cairosvg not available, trying svglib...')
except Exception as e:
    print(f'cairosvg failed: {e}, trying svglib...')

# Try svglib + reportlab
try:
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPDF
    drawing = svg2rlg(svg_path)
    if drawing:
        renderPDF.drawToFile(drawing, pdf_path, fmt='PDF')
        print(f'PDF created with svglib: {pdf_path}')
        print(f'Size: {os.path.getsize(pdf_path)} bytes')
        sys.exit(0)
    else:
        print('svglib returned None drawing')
except ImportError:
    print('svglib not available, trying inkscape...')
except Exception as e:
    print(f'svglib failed: {e}, trying inkscape...')

# Try inkscape CLI
try:
    result = subprocess.run(
        ['inkscape', svg_path, '--export-type=pdf', f'--export-filename={pdf_path}'],
        capture_output=True, text=True, timeout=30
    )
    if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
        print(f'PDF created with inkscape: {pdf_path}')
        print(f'Size: {os.path.getsize(pdf_path)} bytes')
        sys.exit(0)
    else:
        print(f'inkscape failed: {result.stderr}')
except FileNotFoundError:
    print('inkscape not installed, trying rsvg-convert...')
except Exception as e:
    print(f'inkscape failed: {e}, trying rsvg-convert...')

# Try rsvg-convert (librsvg)
try:
    result = subprocess.run(
        ['rsvg-convert', '-f', 'pdf', '-o', pdf_path, svg_path],
        capture_output=True, text=True, timeout=30
    )
    if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
        print(f'PDF created with rsvg-convert: {pdf_path}')
        print(f'Size: {os.path.getsize(pdf_path)} bytes')
        sys.exit(0)
    else:
        print(f'rsvg-convert failed: {result.stderr}')
except FileNotFoundError:
    print('rsvg-convert not installed')
except Exception as e:
    print(f'rsvg-convert failed: {e}')

# Last resort: wkhtmltopdf with HTML wrapper
try:
    html_wrapper = f'''<!DOCTYPE html>
<html><head><style>
body {{ margin: 0; padding: 0; }}
img {{ width: 100%; height: auto; }}
</style></head><body>
<img src="file://{svg_path}" />
</body></html>'''
    html_path = svg_path.replace('.svg', '_temp.html')
    with open(html_path, 'w') as f:
        f.write(html_wrapper)
    result = subprocess.run(
        ['wkhtmltopdf', '--enable-local-file-access', html_path, pdf_path],
        capture_output=True, text=True, timeout=30
    )
    os.remove(html_path)
    if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
        print(f'PDF created with wkhtmltopdf: {pdf_path}')
        print(f'Size: {os.path.getsize(pdf_path)} bytes')
        sys.exit(0)
    else:
        print(f'wkhtmltopdf failed: {result.stderr}')
except FileNotFoundError:
    print('wkhtmltopdf not installed')
except Exception as e:
    print(f'wkhtmltopdf failed: {e}')

print('\nAll conversion methods failed.')
print('Install one of: pip install cairosvg | pip install svglib reportlab | apt install inkscape | apt install librsvg2-bin | apt install wkhtmltopdf')
sys.exit(1)
