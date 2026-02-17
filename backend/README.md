# EmpireBox Backend API

FastAPI backend for EmpireBox Setup Portal, License Management, and ShipForge shipping integration.

## Features

- **License Key System**: Generate, validate, and activate license keys for hardware bundles
- **Shipping Integration**: EasyPost integration for comparing rates and purchasing labels
- **Pre-order Management**: Handle hardware bundle pre-orders with Stripe payments

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Copy environment variables:
```bash
cp .env.example .env
```

3. Edit `.env` and add your API keys for EasyPost and Stripe

4. Initialize the database:
```bash
python -m app.init_db
```

5. Run the server:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### Licenses
- `POST /licenses/generate` - Generate license keys
- `GET /licenses/{key}/validate` - Validate a license key
- `POST /licenses/{key}/activate` - Activate a license
- `GET /licenses/my-licenses` - Get user's licenses

### Shipping
- `POST /shipping/rates` - Get shipping rates
- `POST /shipping/labels` - Purchase a shipping label
- `GET /shipping/labels/{id}` - Get label details
- `GET /shipping/track/{tracking_number}` - Track shipment
- `GET /shipping/history` - Get shipment history
- `POST /shipping/labels/{id}/email` - Email label PDF

### Pre-orders
- `POST /preorders/` - Create a pre-order
- `GET /preorders/` - List pre-orders
- `GET /preorders/{id}` - Get pre-order details
- `PATCH /preorders/{id}` - Update pre-order
- `POST /preorders/{id}/process-payment` - Process payment

## Development

### Test Mode

The shipping service runs in test mode by default (using simulated data). To use real EasyPost API:
1. Set `EASYPOST_TEST_MODE=false` in `.env`
2. Add your production `EASYPOST_API_KEY`

### Database

Uses SQLite by default. For production, update `DATABASE_URL` in `.env` to use PostgreSQL:
```
DATABASE_URL=postgresql://user:password@localhost/empirebox
```

## License Key Format

License keys use the format: `EMPIRE-XXXX-XXXX-XXXX`
- 16 alphanumeric characters (excluding confusing characters like O, 0, I, 1)
- Always starts with "EMPIRE-"
- Unique and randomly generated
