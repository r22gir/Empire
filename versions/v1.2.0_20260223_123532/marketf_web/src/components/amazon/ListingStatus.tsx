'use client';

import { useEffect, useState } from 'react';

export type ListingStatusValue = 'active' | 'pending' | 'suppressed' | 'error';

interface AmazonListing {
  id: string;
  productTitle: string;
  amazonSku: string;
  amazonAsin: string | null;
  listingStatus: ListingStatusValue;
  lastSyncAt: string | null;
  errorMessage?: string;
}

interface ListingStatusProps {
  storeId: string;
}

const STATUS_CONFIG: Record<
  ListingStatusValue,
  { label: string; bgClass: string; textClass: string; dotClass: string }
> = {
  active: {
    label: 'Active',
    bgClass: 'bg-green-100',
    textClass: 'text-green-800',
    dotClass: 'bg-green-500',
  },
  pending: {
    label: 'Pending',
    bgClass: 'bg-yellow-100',
    textClass: 'text-yellow-800',
    dotClass: 'bg-yellow-500',
  },
  suppressed: {
    label: 'Suppressed',
    bgClass: 'bg-orange-100',
    textClass: 'text-orange-800',
    dotClass: 'bg-orange-500',
  },
  error: {
    label: 'Error',
    bgClass: 'bg-red-100',
    textClass: 'text-red-800',
    dotClass: 'bg-red-500',
  },
};

export default function ListingStatus({ storeId }: ListingStatusProps) {
  const [listings, setListings] = useState<AmazonListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function fetchListings() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`/api/amazon/listings?storeId=${storeId}`, {
          signal: controller.signal,
        });
        if (!res.ok) {
          throw new Error(`Failed to load listings (${res.status})`);
        }
        const data = await res.json();
        setListings(data.listings ?? []);
      } catch (err) {
        if ((err as Error).name !== 'AbortError') {
          setError((err as Error).message);
        }
      } finally {
        setLoading(false);
      }
    }

    fetchListings();
    return () => controller.abort();
  }, [storeId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12 text-gray-400">
        <span className="animate-spin mr-2">⟳</span> Loading listings…
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-sm text-red-700">
        {error}
      </div>
    );
  }

  if (listings.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400 text-sm">
        No Amazon listings yet. Upload a product to get started.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {listings.map((listing) => (
        <ListingRow key={listing.id} listing={listing} />
      ))}
    </div>
  );
}

function ListingRow({ listing }: { listing: AmazonListing }) {
  const config = STATUS_CONFIG[listing.listingStatus];

  return (
    <div className="flex items-center justify-between rounded-lg border border-gray-100 bg-white p-4 hover:shadow-sm transition-shadow">
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-gray-900 truncate">{listing.productTitle}</p>
        <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
          <span>SKU: {listing.amazonSku}</span>
          {listing.amazonAsin && <span>ASIN: {listing.amazonAsin}</span>}
          {listing.lastSyncAt && (
            <span>Synced: {new Date(listing.lastSyncAt).toLocaleDateString()}</span>
          )}
        </div>
        {listing.listingStatus === 'error' && listing.errorMessage && (
          <p className="mt-1 text-xs text-red-600">{listing.errorMessage}</p>
        )}
      </div>

      <span
        className={`ml-4 inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${config.bgClass} ${config.textClass}`}
      >
        <span className={`w-1.5 h-1.5 rounded-full ${config.dotClass}`} />
        {config.label}
      </span>
    </div>
  );
}
