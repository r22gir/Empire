import { Metadata } from 'next';
import ProductPageLayout from '@/components/ProductPageLayout';

export const metadata: Metadata = {
  title: 'MarketForge - EmpireBox',
  description: 'AI-powered listing tool. Photo → Price → Post in 30 seconds across all major marketplaces.',
};

export default function MarketForgePage() {
  return (
    <ProductPageLayout
      icon="📸"
      name="MarketForge"
      tagline="Photo → Price → Post in 30 seconds"
      description="AI-powered listing tool for resellers. Upload a photo, get instant AI pricing and descriptions, then post to eBay, Poshmark, Facebook Marketplace, Mercari, and more simultaneously."
      features={[
        'AI-powered pricing based on real market data',
        'Auto-generated item descriptions and titles',
        'One-click crosslisting to 6+ marketplaces',
        'Inventory management dashboard',
        'Real-time sales analytics',
        'Mobile app for iOS and Android',
        'Bulk listing tools',
        'Automatic price adjustments',
      ]}
      pricingTiers={[
        {
          name: 'Free Trial',
          price: '$0',
          period: '7 days',
          features: ['10 listings', 'All platforms', 'Basic AI features', 'Email support'],
        },
        {
          name: 'Premium',
          price: '$9.99',
          period: 'month',
          featured: true,
          features: ['Unlimited listings', 'All platforms', 'Full AI features', 'Priority support', 'No commission fees', 'Advanced analytics'],
        },
        {
          name: 'Hybrid',
          price: '$5.99',
          period: 'month',
          features: ['Unlimited listings', 'All platforms', 'Full AI features', 'Priority support', '+ 1.5% commission per sale', 'Best value for growing sellers'],
        },
      ]}
    />
  );
}
