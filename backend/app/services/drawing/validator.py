"""Validate AI draftsman output before rendering. Reject bad geometry."""
import logging

log = logging.getLogger("drawing_validator")


def validate_drawing(drawing: dict) -> tuple[bool, list[str]]:
    """Returns (is_valid, errors). Mutates drawing to inject defaults."""
    errors = []

    if not drawing:
        return False, ["Empty drawing data"]

    geom = drawing.get("geometry", {})
    points = geom.get("points", {})
    edges = geom.get("edges", [])
    dimensions = drawing.get("dimensions", [])

    if not points:
        errors.append("No geometry points defined")

    # Check edge references
    for i, edge in enumerate(edges):
        for key in ("from", "to"):
            ref = edge.get(key)
            if ref and ref not in points:
                errors.append(f"Edge {i} references undefined point '{ref}'")

    # Check dimension references
    for i, dim in enumerate(dimensions):
        for key in ("from", "to"):
            ref = dim.get(key)
            if ref and ref not in points:
                errors.append(f"Dimension {i} references undefined point '{ref}'")

    # Minimum geometry
    if len(points) < 8:
        errors.append(f"Too few points ({len(points)}) — need at least 8 for a box")

    if len(dimensions) < 3:
        errors.append(f"Too few dimensions ({len(dimensions)}) — need at least width, depth, height")

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
