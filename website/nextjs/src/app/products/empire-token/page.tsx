import { Metadata } from 'next';
import ProductPageLayout from '@/components/ProductPageLayout';

export const metadata: Metadata = {
  title: 'EMPIRE Token - EmpireBox',
  description: 'The native utility token powering the EmpireBox ecosystem. Earn, stake, and govern.',
};

export default function EmpireTokenPage() {
  return (
    <ProductPageLayout
      icon="🪙"
      name="EMPIRE Token"
      tagline="Earn, Stake, and Govern the EmpireBox Ecosystem"
      description="The native utility token powering the entire EMPIREBOX ecosystem. Earn tokens through platform activity, use them to pay reduced fees, and participate in governance decisions."
      features={[
        'Earn tokens through sales and activity',
        'Reduced platform fees when paying with EMPIRE',
        'Governance voting rights',
        'Staking rewards program',
        'Exclusive member perks and early access',
        'Solana blockchain (fast, low fees)',
        'Transferable and tradeable',
        'Integrated crypto wallet',
      ]}
      pricingTiers={[
        {
          name: 'EMPIRE Token',
          price: 'Free',
          period: 'to earn',
          featured: true,
          features: [
            'Earn tokens through EmpireBox activity',
            'No purchase required to start earning',
            'Available to all EmpireBox subscribers',
            'Token value set by market',
            'Optional: buy tokens directly',
          ],
        },
      ]}
      ctaText="Learn About Tokens"
      ctaHref="/setup"
    />
  );
}
