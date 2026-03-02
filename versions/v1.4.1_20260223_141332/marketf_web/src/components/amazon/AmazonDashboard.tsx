'use client';

import { useState } from 'react';
import ListingStatus from './ListingStatus';
import ProductUpload from './ProductUpload';

interface AmazonStats {
  activeListings: number;
  pendingListings: number;
  suppressedListings: number;
  errorListings: number;
  totalRevenue: number;
  lastSyncAt: string | null;
}

interface AmazonDashboardProps {
  storeId: string;
  stats?: AmazonStats;
}

type Tab = 'overview' | 'listings' | 'upload';

export default function AmazonDashboard({ storeId, stats }: AmazonDashboardProps) {
  const [activeTab, setActiveTab] = useState<Tab>('overview');

  const defaultStats: AmazonStats = {
    activeListings: 0,
    pendingListings: 0,
    suppressedListings: 0,
    errorListings: 0,
    totalRevenue: 0,
    lastSyncAt: null,
    ...stats,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
            <span className="text-orange-600 font-bold text-sm">AMZ</span>
          </div>
          <div>
            <h2 className="text-xl font-bold">Amazon Marketplace</h2>
            <p className="text-sm text-gray-500">via MarketF Professional Seller Account</p>
          </div>
        </div>
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
          <span className="w-1.5 h-1.5 rounded-full bg-yellow-500" />
          Coming Soon
        </span>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Active" value={defaultStats.activeListings} color="green" />
        <StatCard label="Pending" value={defaultStats.pendingListings} color="yellow" />
        <StatCard label="Suppressed" value={defaultStats.suppressedListings} color="orange" />
        <StatCard label="Errors" value={defaultStats.errorListings} color="red" />
      </div>

      {/* Last sync */}
      {defaultStats.lastSyncAt && (
        <p className="text-xs text-gray-400">
          Last synced: {new Date(defaultStats.lastSyncAt).toLocaleString()}
        </p>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-6">
          {(['overview', 'listings', 'upload'] as Tab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-3 text-sm font-medium border-b-2 capitalize transition-colors ${
                activeTab === tab
                  ? 'border-orange-500 text-orange-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab === 'upload' ? 'Upload Product' : tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      {activeTab === 'overview' && <OverviewTab stats={defaultStats} />}
      {activeTab === 'listings' && <ListingStatus storeId={storeId} />}
      {activeTab === 'upload' && <ProductUpload storeId={storeId} />}
    </div>
  );
}

function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: 'green' | 'yellow' | 'orange' | 'red';
}) {
  const colorClasses = {
    green: 'bg-green-50 text-green-700',
    yellow: 'bg-yellow-50 text-yellow-700',
    orange: 'bg-orange-50 text-orange-700',
    red: 'bg-red-50 text-red-700',
  };

  return (
    <div className={`rounded-lg p-4 ${colorClasses[color]}`}>
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-xs font-medium mt-1">{label}</p>
    </div>
  );
}

function OverviewTab({ stats }: { stats: AmazonStats }) {
  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-orange-200 bg-orange-50 p-4">
        <h3 className="font-semibold text-orange-800 mb-1">Amazon Integration Setup Required</h3>
        <p className="text-sm text-orange-700">
          Connect your Amazon Professional Seller account to start listing products on Amazon
          through MarketF. See the{' '}
          <a
            href="/docs/MARKETF_AMAZON_SPEC.md"
            className="underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            setup guide
          </a>{' '}
          for prerequisites.
        </p>
      </div>

      <div className="grid gap-3">
        <SetupStep
          step={1}
          title="Amazon Professional Seller Account"
          description="Create an Amazon Professional Seller account ($39.99/mo) at sellercentral.amazon.com"
          status="pending"
        />
        <SetupStep
          step={2}
          title="SP-API App Registration"
          description="Register a private SP-API app in Seller Central (free for private use)"
          status="pending"
        />
        <SetupStep
          step={3}
          title="Configure Credentials"
          description="Add Amazon SP-API credentials to your environment configuration"
          status="pending"
        />
        <SetupStep
          step={4}
          title="Brand Authorization"
          description="Upload brand authorization documents for any brand-protected products"
          status="pending"
        />
      </div>
    </div>
  );
}

function SetupStep({
  step,
  title,
  description,
  status,
}: {
  step: number;
  title: string;
  description: string;
  status: 'complete' | 'pending';
}) {
  return (
    <div className="flex items-start gap-3 p-3 rounded-lg border border-gray-100 bg-white">
      <div
        className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-sm font-bold ${
          status === 'complete'
            ? 'bg-green-100 text-green-700'
            : 'bg-gray-100 text-gray-500'
        }`}
      >
        {status === 'complete' ? '✓' : step}
      </div>
      <div>
        <p className="text-sm font-medium text-gray-900">{title}</p>
        <p className="text-xs text-gray-500 mt-0.5">{description}</p>
      </div>
    </div>
  );
}
