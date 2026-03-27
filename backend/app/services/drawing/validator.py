"""Validate AI draftsman output before rendering. Strip bad refs, reject bad geometry."""
import logging

log = logging.getLogger("drawing_validator")


def validate_drawing(drawing: dict) -> tuple[bool, list[str]]:
    """Returns (is_valid, errors). Strips invalid edges/dims rather than rejecting."""
    errors = []

    if not drawing:
        return False, ["Empty drawing data"]

    geom = drawing.get("geometry", {})
    points = geom.get("points", {})
    edges = geom.get("edges", [])
    dimensions = drawing.get("dimensions", [])

    if not points:
        return False, ["No geometry points defined"]

    # Strip edges that reference undefined points (AI sometimes adds channel edges)
    valid_edges = []
    for edge in edges:
        p_from = edge.get("from")
        p_to = edge.get("to")
        if p_from in points and p_to in points:
            valid_edges.append(edge)
        else:
            log.debug(f"Stripping edge with undefined ref: {p_from} -> {p_to}")
    geom["edges"] = valid_edges

    # Strip dimensions that reference undefined points
    valid_dims = []
    for dim in dimensions:
        p_from = dim.get("from")
        p_to = dim.get("to")
        if p_from in points and p_to in points:
            valid_dims.append(dim)
        else:
            log.debug(f"Stripping dimension with undefined ref: {p_from} -> {p_to}")
    drawing["dimensions"] = valid_dims

    # Minimum geometry — hard fail only on truly broken output
    if len(points) < 8:
        errors.append(f"Too few points ({len(points)}) — need at least 8 for a box")

    if len(valid_dims) < 2:
        errors.append(f"Too few dimensions ({len(valid_dims)}) — need at least width + height")

    if errors:
        log.warning(f"Validation errors: {errors}")

    return len(errors) == 0, errors


def inject_defaults(drawing: dict) -> dict:
    """Fill in missing style/construction defaults."""
    if "channels" not in drawing:
        # Estimate channel count from geometry width
        points = drawing.get("geometry", {}).get("points", {})
        max_x = max((p[0] for p in points.values()), default=100)
        drawing["channels"] = {
            "face": "back_front",
            "count": max(int(max_x / 10), 4),
            "style": "vertical",
        }

    # Ensure all edges have a weight
    for edge in drawing.get("geometry", {}).get("edges", []):
        if "weight" not in edge:
            edge["weight"] = "outline"

    # Ensure all dimensions have offset and placement
    for dim in drawing.get("dimensions", []):
        dim.setdefault("placement", "bottom")
        dim.setdefault("offset", 25)

    return drawing
