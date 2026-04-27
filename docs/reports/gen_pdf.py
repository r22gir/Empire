from fpdf import FPDF

MD_PATH = "/home/rg/empire-repo/docs/reports/EMPIRE_ECOSYSTEM_STRUCTURE_STATUS_2026-04-26.md"
OUT_PATH = "/home/rg/empire-repo/docs/reports/EMPIRE_ECOSYSTEM_STRUCTURE_STATUS_2026-04-26.pdf"

FONT_DIR = "/usr/share/fonts/truetype/dejavu/"

with open(MD_PATH, "r") as f:
    content = f.read()
lines = content.split('\n')

class PDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font('DejaVu', '', 7)
            self.set_text_color(130, 130, 150)
            self.cell(0, 7, f'Empire Ecosystem Report  |  2026-04-26  |  commit f535d53  |  page {self.page_no()}', align='C')
            self.ln(4)
    def footer(self):
        pass

pdf = PDF()
pdf.set_auto_page_break(auto=True, margin=18)
pdf.add_page()

pdf.add_font('DejaVu', '', FONT_DIR + 'DejaVuSans.ttf')
pdf.add_font('DejaVu', 'B', FONT_DIR + 'DejaVuSans-Bold.ttf')

# Title page
pdf.set_font('DejaVu', 'B', 26)
pdf.set_text_color(25, 25, 55)
pdf.ln(25)
pdf.multi_cell(0, 14, "Empire Ecosystem\nStructure and Status Report", align='C')
pdf.ln(6)
pdf.set_font('DejaVu', '', 13)
pdf.set_text_color(70, 70, 100)
pdf.cell(0, 8, "Repo-backed evolution review from inception to current HEAD", align='C')
pdf.ln(12)
pdf.set_font('DejaVu', '', 10)
pdf.set_text_color(90, 90, 120)
pdf.cell(0, 7, "Generated: 2026-04-26   |   Commit: f535d53   |   816 commits   |   70 days   |   main branch", align='C')
pdf.ln(35)

pdf.set_font('DejaVu', 'B', 11)
pdf.set_text_color(25, 25, 55)
pdf.cell(0, 8, "Live System Status", align='L')
pdf.ln(8)
pdf.set_font('DejaVu', '', 10)
pdf.set_text_color(40, 40, 40)
for line in [
    "Backend:        ACTIVE   (port 8000) at commit f535d53",
    "Frontend:       ACTIVE   (port 3005) Next.js 16",
    "OpenClaw:       HEALTHY  (port 7878)",
    "MAX AI:         18 desks operational",
    "MiniMax:        routed via f535d53, Grok fallback preserved",
    "Token tracking: 1,049+ AI calls logged",
    "Memory bank:    ~3,000+ memories, 99 conversation summaries",
]:
    pdf.set_x(25)
    pdf.cell(0, 6, line)
    pdf.ln(1)
pdf.ln(8)

pdf.set_font('DejaVu', 'B', 12)
pdf.set_text_color(25, 25, 55)
pdf.ln(5)
pdf.cell(0, 8, "Report Sections", align='L')
pdf.ln(8)
pdf.set_font('DejaVu', '', 11)
pdf.set_text_color(40, 40, 60)
for item in ["1. Repo Truth Snapshot", "2. File Structure", "3. Current Ecosystem Status",
             "4. Project Evolution Since Inception", "5. Current Verdict"]:
    pdf.set_x(30)
    pdf.cell(0, 6, item)
    pdf.ln(1)

def add_h(pdf, text, level):
    if level == 2:
        pdf.set_font('DejaVu', 'B', 16)
        pdf.set_text_color(25, 25, 55)
        pdf.add_page()
        pdf.ln(3)
        pdf.cell(0, 11, text)
        pdf.ln(9)
    elif level == 3:
        pdf.set_font('DejaVu', 'B', 13)
        pdf.set_text_color(30, 30, 75)
        pdf.ln(5)
        pdf.cell(0, 9, text)
        pdf.ln(7)
    elif level == 4:
        pdf.set_font('DejaVu', 'B', 11)
        pdf.set_text_color(40, 40, 90)
        pdf.ln(3)
        pdf.cell(0, 8, text)
        pdf.ln(6)

def cell_widths(pdf, rows, min_w=20):
    cols = max((len(r) for r in rows), default=1)
    avail = pdf.w - 36
    widths = []
    for i in range(cols):
        mx = max((pdf.get_string_width(str(r[i]) if i < len(r) else '') + 4 for r in rows), default=min_w)
        widths.append(max(min_w, mx))
    total = sum(widths)
    if total > avail:
        widths = [w * avail / total for w in widths]
    return widths

def flush_table(pdf, rows, widths):
    if not rows:
        return
    pdf.set_font('DejaVu', 'B', 8)
    pdf.set_fill_color(25, 25, 55)
    pdf.set_text_color(255, 255, 255)
    for cell in rows[0][:len(widths)]:
        pdf.cell(widths[0], 7, str(cell)[:42], border=1, fill=True)
        widths = widths[1:]
    pdf.ln()
    pdf.set_font('DejaVu', '', 8)
    pdf.set_text_color(30, 30, 30)
    for row in rows[1:]:
        for cell in row[:len(widths)]:
            pdf.cell(widths[0], 6, str(cell)[:42], border=1)
            widths = widths[1:]
        pdf.ln()
    pdf.ln(3)

in_table = False
table_rows = []

i = 0
while i < len(lines):
    line = lines[i].strip()
    i += 1

    if line.startswith('<!--') or line.startswith('<!') or line.startswith('</'):
        continue

    if '|' in line and line.startswith('|'):
        cells = [c.strip() for c in line.split('|') if c.strip() != '']
        if line.startswith('|---') or all(c in ('---', '') for c in cells):
            continue
        table_rows.append(cells)
        in_table = True
        continue
    else:
        if in_table:
            cw = cell_widths(pdf, table_rows)
            flush_table(pdf, table_rows, cw)
            table_rows = []
            in_table = False

    if line.startswith('#### '):
        add_h(pdf, line[5:], 4)
    elif line.startswith('### '):
        add_h(pdf, line[4:], 3)
    elif line.startswith('## '):
        add_h(pdf, line[3:], 2)
    elif line.startswith('# '):
        continue

    elif line == '```' or line.startswith('```'):
        continue
    elif line == '---':
        pdf.ln(2)
        pdf.set_draw_color(160, 160, 190)
        pdf.line(18, pdf.get_y(), pdf.w - 18, pdf.get_y())
        pdf.ln(2)
    elif line.startswith('- '):
        pdf.set_font('DejaVu', '', 9)
        pdf.set_text_color(35, 35, 35)
        pdf.set_x(22)
        pdf.multi_cell(pdf.w - 36, 5.5, line[2:], align='L')
    elif line.startswith('  - '):
        pdf.set_font('DejaVu', '', 8)
        pdf.set_text_color(65, 65, 65)
        pdf.set_x(32)
        pdf.multi_cell(pdf.w - 46, 5, line[4:], align='L')
    elif line.startswith('**') and ':' in line:
        pdf.set_font('DejaVu', 'B', 9)
        pdf.set_text_color(25, 25, 55)
        pdf.set_x(22)
        pdf.multi_cell(pdf.w - 36, 5.5, line.replace('**',''), align='L')
    elif line and line[0].isdigit() and '. ' in line[:5]:
        pdf.set_font('DejaVu', '', 9)
        pdf.set_text_color(35, 35, 35)
        pdf.set_x(22)
        pdf.multi_cell(pdf.w - 36, 5.5, line, align='L')
    elif line.startswith('>'):
        pdf.set_font('DejaVu', '', 9)
        pdf.set_text_color(90, 90, 130)
        pdf.set_x(28)
        pdf.multi_cell(pdf.w - 42, 5, line[2:], align='L')
    elif line == '':
        pdf.ln(2)
    else:
        pdf.set_font('DejaVu', '', 9)
        pdf.set_text_color(35, 35, 35)
        pdf.set_x(22)
        pdf.multi_cell(pdf.w - 36, 5.5, line, align='L')

if in_table:
    cw = cell_widths(pdf, table_rows)
    flush_table(pdf, table_rows, cw)

pdf.output(OUT_PATH)
import os
sz = os.path.getsize(OUT_PATH)
print(f"PDF written: {OUT_PATH}")
print(f"Size: {sz:,} bytes ({sz/1024:.1f} KB)")
