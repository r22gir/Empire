"""
Generate architectural-style measurement diagrams as SVG.
Used by Notes Extraction, Quote Builder, and Quote PDFs.
"""


class DiagramGenerator:
    """Generate architectural-style measurement diagrams from item data."""

    # Colors
    BLACK = "#1a1a1a"
    DARK_GRAY = "#4a4a4a"
    LIGHT_GRAY = "#e5e5e5"
    GLASS_BLUE = "#d4e8f7"
    GOLD = "#b8960c"
    WHITE = "#ffffff"
    FONT = "Arial, Helvetica, sans-serif"

    def generate(self, item: dict) -> dict:
        """Route to the appropriate diagram type. Returns {svg, summary}."""
        item_type = (item.get("type") or "window").lower()
        measurements = item.get("measurements") or {}

        if item_type in ("window", "drapery", "roman_shade", "valance", "cornices"):
            svg = self.generate_window_diagram(item)
        elif item_type in ("sofa", "chair", "upholstery"):
            svg = self.generate_furniture_diagram(item)
        elif item_type in ("cushion", "cushions", "pillow", "pillows"):
            svg = self.generate_cushion_diagram(item)
        else:
            svg = self.generate_window_diagram(item)

        w = measurements.get("width_inches", "?")
        h = measurements.get("height_inches", "?")
        subtype = item.get("subtype") or item.get("treatment") or item_type
        mount = item.get("mount_type") or ""
        summary = f"{subtype}, {w}×{h}"
        if mount:
            summary += f", {mount} mount"

        return {"svg": svg, "summary": summary}

    def generate_window_diagram(self, item: dict) -> str:
        """Return SVG string for a window measurement diagram."""
        m = item.get("measurements") or {}
        width = m.get("width_inches") or 48
        height = m.get("height_inches") or 72
        sill_depth = m.get("sill_depth") or m.get("depth_inches") or 0
        stack = item.get("stack_space") or m.get("stack_space") or 0
        mount_type = item.get("mount_type") or "inside"
        treatment = item.get("treatment") or item.get("subtype") or ""
        lining = item.get("lining") or ""
        window_type = item.get("window_type") or item.get("subtype") or ""

        # Calculate total rod width
        total_width = width + (stack * 2) if stack else width

        # SVG dimensions and scaling
        svg_w, svg_h = 460, 400
        margin = 60
        label_space = 70  # space for dimension labels

        # Drawing area
        draw_x = margin + label_space
        draw_y = margin
        max_draw_w = svg_w - draw_x - margin - 40
        max_draw_h = svg_h - draw_y - 120  # room for labels below

        # Scale proportionally
        scale = min(max_draw_w / max(width, 1), max_draw_h / max(height, 1))
        win_w = width * scale
        win_h = height * scale

        # Center the window
        win_x = draw_x + (max_draw_w - win_w) / 2
        win_y = draw_y + (max_draw_h - win_h) / 2

        # Stack space in pixels
        stack_px = stack * scale if stack else 0

        parts = []

        # Background
        parts.append(f'<rect width="{svg_w}" height="{svg_h}" fill="{self.WHITE}" rx="6"/>')
        parts.append(f'<rect x="1" y="1" width="{svg_w-2}" height="{svg_h-2}" fill="none" stroke="{self.LIGHT_GRAY}" rx="6"/>')

        # Treatment overlay (gold area where drapes hang)
        if stack and treatment:
            tx = win_x - stack_px
            tw = win_w + stack_px * 2
            parts.append(
                f'<rect x="{tx:.1f}" y="{win_y:.1f}" width="{tw:.1f}" height="{win_h:.1f}" '
                f'fill="{self.GOLD}" fill-opacity="0.12" stroke="{self.GOLD}" stroke-width="1" stroke-dasharray="6,3" rx="2"/>'
            )

        # Window frame (outer)
        parts.append(
            f'<rect x="{win_x:.1f}" y="{win_y:.1f}" width="{win_w:.1f}" height="{win_h:.1f}" '
            f'fill="none" stroke="{self.BLACK}" stroke-width="2" rx="1"/>'
        )

        # Glass area
        glass_pad = 6
        parts.append(
            f'<rect x="{win_x+glass_pad:.1f}" y="{win_y+glass_pad:.1f}" '
            f'width="{max(win_w-glass_pad*2, 4):.1f}" height="{max(win_h-glass_pad*2, 4):.1f}" '
            f'fill="{self.GLASS_BLUE}" fill-opacity="0.4" stroke="{self.DARK_GRAY}" stroke-width="0.5"/>'
        )

        # Window cross-bars (double-hung style)
        mid_y = win_y + win_h / 2
        parts.append(
            f'<line x1="{win_x:.1f}" y1="{mid_y:.1f}" x2="{win_x+win_w:.1f}" y2="{mid_y:.1f}" '
            f'stroke="{self.DARK_GRAY}" stroke-width="1.5"/>'
        )

        # Sill
        if sill_depth:
            sill_w = win_w + 16
            sill_x = win_x - 8
            sill_y = win_y + win_h
            sill_h = min(sill_depth * scale, 14)
            parts.append(
                f'<rect x="{sill_x:.1f}" y="{sill_y:.1f}" width="{sill_w:.1f}" height="{sill_h:.1f}" '
                f'fill="{self.LIGHT_GRAY}" stroke="{self.BLACK}" stroke-width="1"/>'
            )

        # === DIMENSION LINES ===

        # Width dimension (top, outside window)
        dim_y = win_y - 22
        self._add_h_dimension(parts, win_x, win_x + win_w, dim_y, f'{width}"')

        # Height dimension (right side, outside window)
        dim_x = win_x + win_w + 22
        self._add_v_dimension(parts, win_y, win_y + win_h, dim_x, f'{height}"')

        # Stack space dimensions (if applicable)
        if stack:
            stack_y = win_y + win_h + 35
            # Left stack
            self._add_h_dimension(parts, win_x - stack_px, win_x, stack_y, f'{stack}"', small=True)
            # Window width
            self._add_h_dimension(parts, win_x, win_x + win_w, stack_y, f'{width}"', small=True)
            # Right stack
            self._add_h_dimension(parts, win_x + win_w, win_x + win_w + stack_px, stack_y, f'{stack}"', small=True)

            # Total rod width
            total_y = stack_y + 22
            self._add_h_dimension(
                parts,
                win_x - stack_px, win_x + win_w + stack_px,
                total_y, f'{total_width}" total rod'
            )

        # Sill depth label
        if sill_depth:
            sill_label_x = win_x + win_w + 10
            sill_label_y = win_y + win_h + 10
            parts.append(
                f'<text x="{sill_label_x:.1f}" y="{sill_label_y:.1f}" '
                f'font-family="{self.FONT}" font-size="11" fill="{self.DARK_GRAY}">sill: {sill_depth}"</text>'
            )

        # Labels at bottom
        label_y = svg_h - 55
        labels = []
        if mount_type:
            labels.append(f"Mount: {mount_type.title()}")
        if treatment:
            labels.append(treatment.replace("_", " ").title())
        if lining:
            labels.append(f"{lining.title()} lining")

        if labels:
            parts.append(
                f'<text x="{svg_w/2:.1f}" y="{label_y}" text-anchor="middle" '
                f'font-family="{self.FONT}" font-size="13" fill="{self.BLACK}" font-weight="600">'
                f'{" · ".join(labels)}</text>'
            )

        # Window type label
        if window_type and window_type != treatment:
            parts.append(
                f'<text x="{svg_w/2:.1f}" y="{label_y + 18}" text-anchor="middle" '
                f'font-family="{self.FONT}" font-size="11" fill="{self.DARK_GRAY}">'
                f'{window_type.replace("_", " ").title()}</text>'
            )

        return self._wrap_svg(parts, svg_w, svg_h)

    def generate_furniture_diagram(self, item: dict) -> str:
        """Return SVG string for furniture measurement diagram."""
        m = item.get("measurements") or {}
        width = m.get("width_inches") or 72
        height = m.get("height_inches") or 36
        depth = m.get("depth_inches") or 30
        cushion_count = m.get("additional", {}).get("cushion_count") or item.get("quantity") or 3

        svg_w, svg_h = 460, 360
        margin = 60

        # Scale
        max_w = svg_w - margin * 2 - 80
        max_h = svg_h - margin * 2 - 80
        scale = min(max_w / max(width, 1), max_h / max(height, 1))

        fw = width * scale
        fh = height * scale
        fx = (svg_w - fw) / 2
        fy = margin + 20

        parts = []
        parts.append(f'<rect width="{svg_w}" height="{svg_h}" fill="{self.WHITE}" rx="6"/>')
        parts.append(f'<rect x="1" y="1" width="{svg_w-2}" height="{svg_h-2}" fill="none" stroke="{self.LIGHT_GRAY}" rx="6"/>')

        # Sofa body
        parts.append(
            f'<rect x="{fx:.1f}" y="{fy:.1f}" width="{fw:.1f}" height="{fh:.1f}" '
            f'fill="#f0ede8" stroke="{self.BLACK}" stroke-width="2" rx="6"/>'
        )

        # Arms (10% of width each side)
        arm_w = fw * 0.1
        parts.append(
            f'<rect x="{fx:.1f}" y="{fy:.1f}" width="{arm_w:.1f}" height="{fh:.1f}" '
            f'fill="#e8e4de" stroke="{self.BLACK}" stroke-width="1.5" rx="4"/>'
        )
        parts.append(
            f'<rect x="{fx+fw-arm_w:.1f}" y="{fy:.1f}" width="{arm_w:.1f}" height="{fh:.1f}" '
            f'fill="#e8e4de" stroke="{self.BLACK}" stroke-width="1.5" rx="4"/>'
        )

        # Cushions
        cushion_area = fw - arm_w * 2 - 8
        cushion_w = (cushion_area - (cushion_count - 1) * 4) / max(cushion_count, 1)
        cushion_h = fh * 0.55
        cushion_y = fy + fh - cushion_h - 6

        for i in range(cushion_count):
            cx = fx + arm_w + 4 + i * (cushion_w + 4)
            parts.append(
                f'<rect x="{cx:.1f}" y="{cushion_y:.1f}" width="{cushion_w:.1f}" height="{cushion_h:.1f}" '
                f'fill="{self.GOLD}" fill-opacity="0.15" stroke="{self.GOLD}" stroke-width="1" rx="3"/>'
            )

        # Dimensions
        self._add_h_dimension(parts, fx, fx + fw, fy - 18, f'{width}"')
        self._add_v_dimension(parts, fy, fy + fh, fx + fw + 22, f'{height}"')

        # Depth label
        label_y = svg_h - 60
        parts.append(
            f'<text x="{svg_w/2:.1f}" y="{label_y}" text-anchor="middle" '
            f'font-family="{self.FONT}" font-size="13" fill="{self.BLACK}" font-weight="600">'
            f'Depth: {depth}" · {cushion_count} cushions</text>'
        )

        desc = item.get("description") or item.get("type", "Furniture")
        parts.append(
            f'<text x="{svg_w/2:.1f}" y="{label_y + 20}" text-anchor="middle" '
            f'font-family="{self.FONT}" font-size="11" fill="{self.DARK_GRAY}">{desc}</text>'
        )

        return self._wrap_svg(parts, svg_w, svg_h)

    def generate_cushion_diagram(self, item: dict) -> str:
        """Return SVG string for cushion/pillow measurement diagram."""
        m = item.get("measurements") or {}
        width = m.get("width_inches") or 20
        height = m.get("height_inches") or 20
        depth = m.get("depth_inches") or 4

        svg_w, svg_h = 360, 300
        margin = 60

        max_s = min(svg_w, svg_h) - margin * 2 - 60
        scale = min(max_s / max(width, 1), max_s / max(height, 1))

        cw = width * scale
        ch = height * scale
        cx = (svg_w - cw) / 2
        cy = margin + 10

        parts = []
        parts.append(f'<rect width="{svg_w}" height="{svg_h}" fill="{self.WHITE}" rx="6"/>')
        parts.append(f'<rect x="1" y="1" width="{svg_w-2}" height="{svg_h-2}" fill="none" stroke="{self.LIGHT_GRAY}" rx="6"/>')

        # Cushion body
        parts.append(
            f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{cw:.1f}" height="{ch:.1f}" '
            f'fill="{self.GOLD}" fill-opacity="0.12" stroke="{self.BLACK}" stroke-width="2" rx="8"/>'
        )

        # Boxing depth indicator (small side view)
        if depth:
            bx = cx + cw + 20
            by = cy + ch * 0.3
            bh = ch * 0.4
            bw = depth * scale * 0.5
            parts.append(
                f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh:.1f}" '
                f'fill="#f0ede8" stroke="{self.BLACK}" stroke-width="1" rx="2"/>'
            )
            parts.append(
                f'<text x="{bx + bw/2:.1f}" y="{by + bh + 14:.1f}" text-anchor="middle" '
                f'font-family="{self.FONT}" font-size="10" fill="{self.DARK_GRAY}">{depth}"</text>'
            )

        # Dimensions
        self._add_h_dimension(parts, cx, cx + cw, cy - 16, f'{width}"')
        self._add_v_dimension(parts, cy, cy + ch, cx - 22, f'{height}"')

        desc = item.get("description") or "Cushion"
        label_y = svg_h - 40
        parts.append(
            f'<text x="{svg_w/2:.1f}" y="{label_y}" text-anchor="middle" '
            f'font-family="{self.FONT}" font-size="12" fill="{self.BLACK}" font-weight="600">{desc}</text>'
        )

        return self._wrap_svg(parts, svg_w, svg_h)

    # === HELPER METHODS ===

    def _add_h_dimension(self, parts: list, x1: float, x2: float, y: float, label: str, small: bool = False):
        """Add a horizontal dimension line with arrows and label."""
        arrow = 5 if not small else 3
        fs = 12 if not small else 10
        mid = (x1 + x2) / 2

        # Line
        parts.append(
            f'<line x1="{x1:.1f}" y1="{y:.1f}" x2="{x2:.1f}" y2="{y:.1f}" '
            f'stroke="{self.BLACK}" stroke-width="1"/>'
        )
        # Left arrow
        parts.append(
            f'<polygon points="{x1:.1f},{y:.1f} {x1+arrow:.1f},{y-arrow/2:.1f} {x1+arrow:.1f},{y+arrow/2:.1f}" '
            f'fill="{self.BLACK}"/>'
        )
        # Right arrow
        parts.append(
            f'<polygon points="{x2:.1f},{y:.1f} {x2-arrow:.1f},{y-arrow/2:.1f} {x2-arrow:.1f},{y+arrow/2:.1f}" '
            f'fill="{self.BLACK}"/>'
        )
        # Extension lines
        ext = 6
        parts.append(f'<line x1="{x1:.1f}" y1="{y-ext:.1f}" x2="{x1:.1f}" y2="{y+ext:.1f}" stroke="{self.BLACK}" stroke-width="0.5" stroke-dasharray="2,2"/>')
        parts.append(f'<line x1="{x2:.1f}" y1="{y-ext:.1f}" x2="{x2:.1f}" y2="{y+ext:.1f}" stroke="{self.BLACK}" stroke-width="0.5" stroke-dasharray="2,2"/>')

        # Label background + text
        parts.append(
            f'<rect x="{mid-30:.1f}" y="{y-fs-2:.1f}" width="60" height="{fs+4}" '
            f'fill="{self.WHITE}" rx="2"/>'
        )
        parts.append(
            f'<text x="{mid:.1f}" y="{y-3:.1f}" text-anchor="middle" '
            f'font-family="{self.FONT}" font-size="{fs}" fill="{self.BLACK}" font-weight="500">{label}</text>'
        )

    def _add_v_dimension(self, parts: list, y1: float, y2: float, x: float, label: str):
        """Add a vertical dimension line with arrows and label."""
        arrow = 5
        mid = (y1 + y2) / 2

        # Line
        parts.append(
            f'<line x1="{x:.1f}" y1="{y1:.1f}" x2="{x:.1f}" y2="{y2:.1f}" '
            f'stroke="{self.BLACK}" stroke-width="1"/>'
        )
        # Top arrow
        parts.append(
            f'<polygon points="{x:.1f},{y1:.1f} {x-arrow/2:.1f},{y1+arrow:.1f} {x+arrow/2:.1f},{y1+arrow:.1f}" '
            f'fill="{self.BLACK}"/>'
        )
        # Bottom arrow
        parts.append(
            f'<polygon points="{x:.1f},{y2:.1f} {x-arrow/2:.1f},{y2-arrow:.1f} {x+arrow/2:.1f},{y2-arrow:.1f}" '
            f'fill="{self.BLACK}"/>'
        )
        # Extension lines
        ext = 6
        parts.append(f'<line x1="{x-ext:.1f}" y1="{y1:.1f}" x2="{x+ext:.1f}" y2="{y1:.1f}" stroke="{self.BLACK}" stroke-width="0.5" stroke-dasharray="2,2"/>')
        parts.append(f'<line x1="{x-ext:.1f}" y1="{y2:.1f}" x2="{x+ext:.1f}" y2="{y2:.1f}" stroke="{self.BLACK}" stroke-width="0.5" stroke-dasharray="2,2"/>')

        # Rotated label
        parts.append(
            f'<rect x="{x-8:.1f}" y="{mid-22:.1f}" width="16" height="44" fill="{self.WHITE}" rx="2"/>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{mid:.1f}" text-anchor="middle" '
            f'font-family="{self.FONT}" font-size="12" fill="{self.BLACK}" font-weight="500" '
            f'transform="rotate(-90,{x:.1f},{mid:.1f})">{label}</text>'
        )

    def _wrap_svg(self, parts: list, w: int, h: int) -> str:
        """Wrap SVG elements in an SVG tag."""
        body = "\n  ".join(parts)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
            f'width="{w}" height="{h}" style="font-family: {self.FONT};">\n'
            f'  {body}\n</svg>'
        )


# Singleton
diagram_generator = DiagramGenerator()
