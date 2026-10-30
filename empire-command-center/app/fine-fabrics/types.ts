export type FabricProduct = {
  id: number;
  pattern: string;
  color: string;
  sku?: string;
  display_title?: string;
  empire_code: string;
  category: string;
  width: string;
  content: string;
  repeat: string;
  durability: string;
  care: string;
  price_per_yard: number;
  price_per_unit?: number;
  unit?: string;
  unit_label?: string;
  product_type?: string;
  image_url: string | null;
  has_owner_photo: boolean;
  has_vendor_image?: boolean;
  placeholder: boolean;
  brand?: string;
  collection?: string;
  description?: string;
  seo?: {
    title: string;
    description: string;
    canonical: string;
    json_ld: Record<string, unknown>;
  };
};

export type CartLine = {
  product_id: number;
  yards: number;
  pattern: string;
  color: string;
  sku?: string;
  display_title?: string;
  empire_code: string;
  price_per_yard: number;
  unit?: string;
  unit_label?: string;
  image_url: string | null;
};

export type ShippingEstimate = {
  pass_through: boolean;
  never_free: boolean;
  free_shipping: boolean;
  freight: number;
  handling_total: number;
  shipping_total: number;
  floor_applied: boolean;
  shipments?: Array<{
    label: string;
    yards: number;
    samples: number;
    freight: number;
    handling_fee: number;
    total: number;
  }>;
  note: string;
};
