"""
LuxeForge Measurements API Router.

Endpoints:
  POST /api/luxeforge/measurements/calibrate  - Save reference calibration
  POST /api/luxeforge/measurements/calculate  - Calculate real dimensions
  GET  /api/luxeforge/measurements/{image_id} - Get measurements for an image
  POST /api/luxeforge/measurements/export     - Export measurements to quote/order
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
import math

from app.database import get_db
from app.models.luxeforge_measurement import ImageMeasurement
from app.schemas.luxeforge_measurement import (
    CalibrateRequest,
    CalculateRequest,
    CalculateResponse,
    ExportRequest,
    ExportResponse,
    MeasurementResponse,
)

router = APIRouter()


def _pixels_per_unit(record: ImageMeasurement) -> float:
    """Return the pixels-per-unit ratio for a calibrated record."""
    return record.reference_pixels / record.reference_real


@router.post(
    "/calibrate",
    response_model=MeasurementResponse,
    status_code=status.HTTP_201_CREATED,
)
def calibrate(request: CalibrateRequest, db: Session = Depends(get_db)):
    """
    Save (or replace) reference calibration for an image.

    The caller draws a line over a known object and supplies:
    - reference_pixels: pixel length of that line
    - reference_real:   real-world length of the object
    - reference_unit:   'inches' or 'cm'
    """
    record = (
        db.query(ImageMeasurement)
        .filter(ImageMeasurement.image_id == request.image_id)
        .first()
    )
    if record:
        record.reference_pixels = request.reference_pixels
        record.reference_real = request.reference_real
        record.reference_unit = request.reference_unit
    else:
        record = ImageMeasurement(
            image_id=request.image_id,
            reference_pixels=request.reference_pixels,
            reference_real=request.reference_real,
            reference_unit=request.reference_unit,
            measurements=[],
        )
        db.add(record)

    db.commit()
    db.refresh(record)
    return record


@router.post("/calculate", response_model=CalculateResponse)
def calculate(request: CalculateRequest, db: Session = Depends(get_db)):
    """
    Convert pixel measurements to real-world dimensions.

    Requires a prior calibration for the image.  Each supplied line has its
    ``real_length`` populated and is persisted alongside the calibration record.
    """
    record = (
        db.query(ImageMeasurement)
        .filter(ImageMeasurement.image_id == request.image_id)
        .first()
    )
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No calibration found for this image. Please calibrate first.",
        )

    ppu = _pixels_per_unit(record)
    calculated_lines = []
    for line in request.lines:
        real_length = round(line.pixels / ppu, 3)
        line.real_length = real_length
        calculated_lines.append(line)

    # Persist calculated measurements
    record.measurements = [
        {
            "label": l.label,
            "start": l.start.model_dump(),
            "end": l.end.model_dump(),
            "pixels": l.pixels,
            "real_length": l.real_length,
        }
        for l in calculated_lines
    ]
    db.commit()

    return CalculateResponse(
        image_id=request.image_id,
        reference_unit=record.reference_unit,
        lines=calculated_lines,
    )


@router.get("/{image_id}", response_model=MeasurementResponse)
def get_measurements(image_id: UUID, db: Session = Depends(get_db)):
    """
    Retrieve calibration and all measurements for a given image.
    """
    record = (
        db.query(ImageMeasurement)
        .filter(ImageMeasurement.image_id == image_id)
        .first()
    )
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No measurements found for this image.",
        )
    return record


@router.post("/export", response_model=ExportResponse)
def export_measurements(request: ExportRequest, db: Session = Depends(get_db)):
    """
    Export measurements in the requested format.

    Supported formats:
    - ``quote``  – human-readable string ready for an order form
    - ``json``   – raw JSON array of measurements
    - ``csv``    – CSV-formatted string
    """
    record = (
        db.query(ImageMeasurement)
        .filter(ImageMeasurement.image_id == request.image_id)
        .first()
    )
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No measurements found for this image.",
        )

    unit = record.reference_unit
    measurements = record.measurements or []

    if request.format == "quote":
        lines = []
        for m in measurements:
            label = m.get("label") or "Measurement"
            rl = m.get("real_length")
            if rl is not None:
                lines.append(f'{label}: {rl}"' if unit == "inches" else f"{label}: {rl} {unit}")
        data = "\n".join(lines) if lines else "No measurements recorded."

    elif request.format == "csv":
        rows = ["label,pixels,real_length,unit"]
        for m in measurements:
            rows.append(
                f'{m.get("label","")},{m.get("pixels","")},{m.get("real_length","")},{unit}'
            )
        data = "\n".join(rows)

    else:  # json
        data = measurements

    return ExportResponse(image_id=request.image_id, format=request.format, data=data)
