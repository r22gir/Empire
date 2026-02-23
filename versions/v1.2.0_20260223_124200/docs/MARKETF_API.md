# MarketF API Documentation

Base URL: `http://localhost:8000` (Development) | `https://api.marketf.com` (Production)

## Authentication

Most endpoints require authentication via JWT token:
```
Authorization: Bearer <your_jwt_token>
```

## Products

### List Products
```http
GET /marketplace/products
```

**Query Parameters:**
- `category` (string, optional) - Filter by category ID
- `condition` (string, optional) - Filter by condition (new, like_new, good, fair, poor)
- `min_price` (float, optional) - Minimum price
- `max_price` (float, optional) - Maximum price
- `sort` (string, optional) - Sort order (newest, price_asc, price_desc)
- `page` (int, optional) - Page number (default: 1)
- `per_page` (int, optional) - Items per page (default: 24, max: 100)

**Response:**
```json
{
  "products": [...],
  "total": 156,
  "page": 1,
  "pages": 7
}
```

### Get Product
```http
GET /marketplace/products/{id}
```

**Response:**
```json
{
  "id": "uuid",
  "title": "Nike Air Max 90",
  "description": "...",
  "price": 85.00,
  "condition": "like_new",
  "images": ["url1", "url2"],
  "seller_id": "uuid",
  ...
}
```

### Create Product
```http
POST /marketplace/products
```

**Headers:** `Authorization: Bearer <token>`

**Body:**
```json
{
  "title": "Product Title",
  "description": "Product description",
  "category_id": "uuid",
  "condition": "like_new",
  "price": 85.00,
  "shipping_price": 8.45,
  "images": ["url1", "url2"],
  "package_weight_oz": 16,
  "package_length_in": 12,
  "package_width_in": 8,
  "package_height_in": 4,
  "ships_from_zip": "90210"
}
```

**Response:** `201 Created` with product object

### Update Product
```http
PUT /marketplace/products/{id}
```

**Headers:** `Authorization: Bearer <token>`

**Body:** Same as create (all fields optional)

**Response:** `200 OK` with updated product object

### Delete Product
```http
DELETE /marketplace/products/{id}
```

**Headers:** `Authorization: Bearer <token>`

**Response:** `204 No Content`

## Orders

### Create Order
```http
POST /marketplace/orders
```

**Headers:** `Authorization: Bearer <token>`

**Body:**
```json
{
  "product_id": "uuid",
  "shipping_address": {
    "name": "John Doe",
    "street": "123 Main St",
    "city": "Los Angeles",
    "state": "CA",
    "zip": "90210",
    "country": "US"
  },
  "payment_method_id": "pm_..."
}
```

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "order_number": "MF-123456",
  "total": 93.45,
  "status": "pending_payment",
  ...
}
```

### List Orders (Buyer)
```http
GET /marketplace/orders
```

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `page` (int, optional)
- `per_page` (int, optional)

**Response:**
```json
{
  "orders": [...],
  "total": 12,
  "page": 1,
  "pages": 1
}
```

### Get Order
```http
GET /marketplace/orders/{id}
```

**Headers:** `Authorization: Bearer <token>`

**Response:** Order object with full details

### Ship Order
```http
POST /marketplace/orders/{id}/ship
```

**Headers:** `Authorization: Bearer <token>` (Seller only)

**Body:**
```json
{
  "tracking_number": "1Z999AA10123456784",
  "carrier": "UPS"
}
```

**Response:** `200 OK` with updated order

## Seller

### List Seller Orders
```http
GET /marketplace/seller/orders
```

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `status` (string, optional) - Filter by status (paid, shipped, delivered, etc.)
- `page` (int, optional)
- `per_page` (int, optional)

**Response:**
```json
{
  "orders": [...],
  "total": 5,
  "page": 1,
  "pages": 1
}
```

## Reviews

### Create Review
```http
POST /marketplace/orders/{order_id}/review
```

**Headers:** `Authorization: Bearer <token>`

**Body:**
```json
{
  "rating": 5,
  "title": "Great seller!",
  "comment": "Fast shipping, exactly as described."
}
```

**Response:** `201 Created` with review object

### Get User Reviews
```http
GET /marketplace/users/{user_id}/reviews
```

**Response:**
```json
{
  "reviews": [...],
  "average_rating": 4.9,
  "total_reviews": 127
}
```

## Error Responses

All errors return appropriate HTTP status codes with JSON body:
```json
{
  "detail": "Error message"
}
```

Common status codes:
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `500` - Internal Server Error
