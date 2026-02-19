import { Metadata } from 'next';
import ProductPageLayout from '@/components/ProductPageLayout';

export const metadata: Metadata = {
  title: 'EMPIRE License NFT - EmpireBox',
  description: 'NFT-based software license granting premium EmpireBox access. Transferable and resellable.',
};

export default function EmpireNFTPage() {
  return (
    <ProductPageLayout
      icon="🏆"
      name="EMPIRE License NFT"
      tagline="Your Digital Business License on the Blockchain"
      description="An NFT-based software license that grants access to premium EmpireBox features. Unlike traditional licenses, it lives on the blockchain and can be transferred or resold."
      features={[
        'On-chain license verification',
        'Full premium feature access',
        'Transferable to new owners',
        'Revenue sharing from platform fees',
        'Lifetime updates included',
        'Governance voting rights',
        'Exclusive NFT holder community',
        'Priority support',
      ]}
      pricingTiers={[
        {
          name: 'EMPIRE License NFT',
          price: 'One-time',
          period: 'purchase',
          featured: true,
          features: [
            'Lifetime premium access',
            'Transferable license',
            'Revenue sharing',
            'On-chain verification',
            'Exclusive holder perks',
            'Price set at mint (see details)',
          ],
        },
      ]}
      ctaText="Mint Your License"
      ctaHref="/setup"
    />
  );
}
