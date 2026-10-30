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

export type UnsortedProduct = FabricProduct & {
  vendor_name?: string;
  sku_range?: string;
  is_unsorted?: boolean;
};

export type ShippingRule = {
  vendor_id: number;
  slug: string;
  name: string;
  ship_per_yard: number;
  ship_per_sample: number;
  ship_minimum: number;
  handling_fee: number;
};

export type ShippingLedgerKind = 'order' | 'sample';

export type ShippingLedgerRow = {
  id: number;
  customer_name?: string | null;
  customer_email?: string | null;
  shipping_total?: number | null;
  actual_vendor_shipping?: number | null;
  shipping_shortfall?: number | null;
  shipping_flag?: string | null;
  status?: string | null;
  created_at?: string | null;
  quote_id?: string | null;
};

export type ShippingLedgerItem = ShippingLedgerRow & {
  kind: ShippingLedgerKind;
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
