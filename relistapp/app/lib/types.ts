export type ListingStatus = 'draft' | 'active' | 'sold' | 'archived' | 'delisted';
export type Platform = 'ebay' | 'etsy' | 'shopify' | 'poshmark' | 'mercari' | 'facebook' | 'amazon' | 'depop' | 'internal';
export type Condition = 'new' | 'like_new' | 'good' | 'fair' | 'poor';

export interface Listing {
  id: string;
  title: string;
  description: string;
  price: number;
  purchase_price?: number;
  category: string;
  condition: Condition;
  photos: string[];
  status: ListingStatus;
  platforms: PlatformListing[];
  tags: string[];
  sku?: string;
  quantity: number;
  weight_oz?: number;
  created_at: string;
  updated_at?: string;
  sold_at?: string;
  sold_price?: number;
  sold_platform?: Platform;
  views?: number;
  favorites?: number;
}

export interface PlatformListing {
  platform: Platform;
  listing_id?: string;
  url?: string;
  status: 'listed' | 'pending' | 'error' | 'sold' | 'delisted';
  listed_at?: string;
  price?: number;
  error?: string;
}

export interface PlatformConnection {
  platform: Platform;
  account_name: string;
  status: 'active' | 'disconnected' | 'error';
  listings_count: number;
  last_sync?: string;
  connected_at: string;
}

export interface RelistSchedule {
  id: string;
  listing_id: string;
  listing_title?: string;
  platforms: Platform[];
  frequency: 'daily' | 'weekly' | 'biweekly' | 'monthly';
  next_run?: string;
  enabled: boolean;
}

export interface DashboardStats {
  total_listings: number;
  active_listings: number;
  sold_this_month: number;
  revenue_this_month: number;
  avg_days_to_sell: number;
  total_platforms: number;
  pending_crossposts: number;
  total_value: number;
}

export interface PricingComp {
  title: string;
  platform: Platform;
  sold_price: number;
  sold_date: string;
  condition: string;
  url?: string;
}
