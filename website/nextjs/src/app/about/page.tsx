import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';

export default function AboutPage() {
  return (
    <main>
      <Navbar />
      <section className="py-20">
        <div className="container mx-auto px-4 max-w-4xl">
          <h1 className="mb-8 text-center">About EmpireBox</h1>
          
          <div className="prose prose-lg mx-auto">
            <h2 className="text-primary">Our Mission</h2>
            <p>
              EmpireBox was built by resellers, for resellers. We know the pain of spending 
              2 hours creating a single listing, manually copying and pasting to multiple platforms, 
              and losing sales because you couldn&apos;t keep up with demand.
            </p>

            <h2 className="text-primary mt-8">The Story</h2>
            <p>
              In 2025, our founder was running a side hustle reselling thrifted items. Despite 
              finding great inventory, growth was impossible — listing items took too long. 
              After months of frustration, EmpireBox was born.
            </p>
            <p>
              What started as a simple crosslisting tool evolved into a complete operating 
              system for resellers. Today, over 50 sellers use EmpireBox to run their businesses, 
              averaging $3,500 in monthly revenue.
            </p>

            <h2 className="text-primary mt-8">Our Platform</h2>
            <p>
              EmpireBox is more than software — it&apos;s a complete business in a box:
            </p>
            <ul className="space-y-2">
              <li><strong>MarketForge</strong>: AI-powered listing creation in 30 seconds</li>
              <li><strong>MarketF</strong>: Your own branded marketplace with 8% fees</li>
              <li><strong>AI Agents</strong>: 24/7 automation for pricing, messages, and more</li>
              <li><strong>RelistApp</strong>: Automated relisting to bump sold-out items</li>
              <li><strong>LLCFactory</strong>: Business formation and compliance</li>
              <li><strong>SocialForge</strong>: Auto-post to Instagram, TikTok, Pinterest</li>
            </ul>

            <h2 className="text-primary mt-8">Join the Movement</h2>
            <p>
              Stop wasting time on manual tasks. Start building a real business that can 
              scale to $10K/month and beyond. Try EmpireBox free for 7 days.
            </p>
          </div>
        </div>
      </section>
      <Footer />
    </main>
  );
}
