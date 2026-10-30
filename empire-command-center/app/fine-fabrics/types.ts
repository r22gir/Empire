export type FabricProduct = {
  id: number;
  pattern: string;
  color: string;
  empire_code: string;
  category: string;
  width: string;
  content: string;
  repeat: string;
  durability: string;
  care: string;
  price_per_yard: number;
  image_url: string | null;
  has_owner_photo: boolean;
  placeholder: boolean;
  brand?: string;
};

export type CartLine = {
  product_id: number;
  yards: number;
  pattern: string;
  color: string;
  empire_code: string;
  price_per_yard: number;
  image_url: string | null;
};
