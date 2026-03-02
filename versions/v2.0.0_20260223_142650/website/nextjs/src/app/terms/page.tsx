import { Metadata } from "next";
import LegalPageLayout from "@/components/LegalPageLayout";

export const metadata: Metadata = {
  title: "Terms of Service | EmpireBox",
  description: "Terms and conditions for using the EmpireBox platform and services.",
  robots: "noindex",
};

const tocItems = [
  { id: "agreement", title: "Agreement to Terms" },
  { id: "service-description", title: "Service Description" },
  { id: "account", title: "Account Registration" },
  { id: "payments", title: "Subscription and Payments" },
  { id: "commission", title: "Commission Fees" },
  { id: "acceptable-use", title: "Acceptable Use" },
  { id: "intellectual-property", title: "Intellectual Property" },
  { id: "third-party", title: "Third-Party Services" },
  { id: "disclaimers", title: "Disclaimers" },
  { id: "liability", title: "Limitation of Liability" },
  { id: "indemnification", title: "Indemnification" },
  { id: "disputes", title: "Dispute Resolution" },
  { id: "termination", title: "Termination" },
  { id: "modifications", title: "Modifications" },
  { id: "misc", title: "Miscellaneous" },
  { id: "contact", title: "Contact" },
];

export default function TermsPage() {
  return (
    <LegalPageLayout
      title="Terms of Service"
      lastUpdated="February 17, 2026"
      showToc={true}
      tocItems={tocItems}
    >
      <section id="agreement" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">1. Agreement to Terms</h2>
        <p className="mb-4">
          By accessing or using EmpireBox ("Service", "Platform", "we", "us", or "our"), you agree 
          to be bound by these Terms of Service ("Terms"). If you disagree with any part of these 
          terms, you may not access the Service.
        </p>
        <p className="mb-4">
          These Terms constitute a legally binding agreement between you and EmpireBox. Please read 
          them carefully.
        </p>
      </section>

      <section id="service-description" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">2. Service Description</h2>
        <p className="mb-4">
          EmpireBox provides a comprehensive marketplace automation platform including:
        </p>
        
        <h3 className="text-xl font-semibold text-gray-800 mb-3">2.1 MarketForge</h3>
        <p className="mb-4">
          Multi-platform listing creation and management tool that allows you to create and publish 
          listings across multiple online marketplaces including eBay, Facebook Marketplace, and others.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">2.2 AI Agents and Automation</h3>
        <p className="mb-4">
          AI-powered tools to assist with listing optimization, pricing recommendations, inventory 
          management, and automated responses to buyer inquiries.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">2.3 Marketplace Integrations</h3>
        <p className="mb-4">
          Integrations with third-party marketplace platforms to streamline your selling process.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">2.4 Email/Messaging Services</h3>
        <p className="mb-4">
          Tools to manage customer communications across multiple platforms.
        </p>
      </section>

      <section id="account" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">3. Account Registration</h2>
        
        <h3 className="text-xl font-semibold text-gray-800 mb-3">3.1 Eligibility</h3>
        <p className="mb-4">
          You must be at least 18 years of age to use EmpireBox. By creating an account, you represent 
          and warrant that you meet this age requirement.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">3.2 Account Information</h3>
        <p className="mb-4">
          You agree to provide accurate, current, and complete information during registration and 
          to update such information to keep it accurate, current, and complete.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">3.3 Account Security</h3>
        <p className="mb-4">
          You are responsible for safeguarding your account password and for all activities that 
          occur under your account. You agree to notify us immediately of any unauthorized use of 
          your account.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">3.4 One Account Per Person</h3>
        <p className="mb-4">
          You may only create one account. Creating multiple accounts to circumvent service limits 
          or policies is prohibited.
        </p>
      </section>

      <section id="payments" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">4. Subscription and Payments</h2>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">4.1 Free Trial</h3>
        <p className="mb-4">
          EmpireBox offers a 7-day free trial for new users. No payment information is required to 
          start the trial. If you cancel before the trial ends, you will not be charged.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">4.2 Subscription Tiers and Pricing</h3>
        <p className="mb-4">
          EmpireBox offers multiple subscription tiers with different features and pricing. Current 
          pricing is available on our <a href="/pricing" className="text-primary-700 hover:underline">Pricing page</a>.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">4.3 Auto-Renewal</h3>
        <p className="mb-4 font-semibold">
          YOUR SUBSCRIPTION WILL AUTOMATICALLY RENEW AT THE END OF EACH BILLING PERIOD (MONTHLY OR YEARLY) 
          UNLESS YOU CANCEL BEFORE THE RENEWAL DATE.
        </p>
        <p className="mb-4">
          You will be charged the then-current subscription fee for your tier at the start of each 
          billing period.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">4.4 Payment Processing</h3>
        <p className="mb-4">
          All payments are processed securely through Stripe, a third-party payment processor. 
          You agree to provide valid payment information and authorize us to charge your payment 
          method for all fees incurred.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">4.5 Failed Payments</h3>
        <p className="mb-4">
          If a payment fails, we will attempt to process the payment again. If payment continues 
          to fail, your account may be suspended or terminated. You remain responsible for any 
          unpaid amounts.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">4.6 Price Changes</h3>
        <p className="mb-4">
          We reserve the right to change our pricing. We will provide at least 30 days' notice 
          before any price increase takes effect. Your continued use of the Service after the 
          price change constitutes your agreement to pay the new price.
        </p>
      </section>

      <section id="commission" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">5. Commission Fees</h2>
        
        <h3 className="text-xl font-semibold text-gray-800 mb-3">5.1 Commission Structure</h3>
        <p className="mb-4">
          In addition to subscription fees, EmpireBox charges a commission fee of 3% on completed 
          sales made through listings created with our platform (commission rate may vary by 
          subscription tier).
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">5.2 When Commission is Charged</h3>
        <p className="mb-4">
          Commission is charged when a sale is completed and payment is received by you. Commission 
          is calculated based on the final sale price (excluding shipping).
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">5.3 Non-Refundable Commission</h3>
        <p className="mb-4">
          Commission fees are non-refundable once a sale is completed, even if the buyer later 
          returns the item or the transaction is cancelled. We do not issue refunds for marketplace 
          fees, chargebacks, or other post-sale issues.
        </p>
      </section>

      <section id="acceptable-use" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">6. Acceptable Use Policy</h2>
        <p className="mb-4">You agree to use EmpireBox only for lawful purposes. You agree NOT to:</p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">6.1 Prohibited Items</h3>
        <ul className="list-disc pl-6 mb-4 space-y-2">
          <li>List or sell illegal items</li>
          <li>List weapons, ammunition, or explosives (unless permitted by marketplace)</li>
          <li>List drugs, drug paraphernalia, or controlled substances</li>
          <li>List counterfeit, replica, or unauthorized goods</li>
          <li>List stolen property</li>
          <li>List adult content or services</li>
        </ul>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">6.2 Prohibited Activities</h3>
        <ul className="list-disc pl-6 mb-4 space-y-2">
          <li>Engage in spam or excessive automated posting</li>
          <li>Abuse or harass other users or marketplace buyers</li>
          <li>Manipulate prices or engage in price fixing</li>
          <li>Create fake reviews or ratings</li>
          <li>Attempt to circumvent marketplace fees or policies</li>
        </ul>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">6.3 Marketplace Compliance</h3>
        <p className="mb-4">
          You must comply with the terms of service and policies of all marketplace platforms 
          you use through EmpireBox (eBay, Facebook, etc.). Violations may result in suspension 
          or termination of your EmpireBox account.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">6.4 No Fraudulent Activity</h3>
        <p className="mb-4">
          You may not engage in any fraudulent, deceptive, or misleading practices including 
          false advertising, bait-and-switch tactics, or misrepresentation of items.
        </p>
      </section>

      <section id="intellectual-property" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">7. Intellectual Property</h2>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">7.1 EmpireBox Property</h3>
        <p className="mb-4">
          The Service, including its software, design, text, graphics, logos, and other content 
          (excluding user content), is owned by EmpireBox and is protected by copyright, trademark, 
          and other intellectual property laws.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">7.2 User Content Ownership</h3>
        <p className="mb-4">
          You retain all ownership rights to the content you create and post through EmpireBox, 
          including product descriptions, images, and listings.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">7.3 License Grant</h3>
        <p className="mb-4">
          By using the Service, you grant EmpireBox a non-exclusive, worldwide, royalty-free license 
          to use, display, reproduce, and distribute your content solely for the purpose of operating 
          and improving the Service.
        </p>
      </section>

      <section id="third-party" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">8. Third-Party Services</h2>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">8.1 Marketplace Integration</h3>
        <p className="mb-4">
          EmpireBox integrates with third-party marketplace platforms (eBay, Facebook Marketplace, etc.). 
          These platforms have their own terms of service, privacy policies, and community guidelines 
          that you must comply with.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">8.2 No Responsibility for Third Parties</h3>
        <p className="mb-4">
          We are not responsible for the availability, content, policies, or practices of third-party 
          marketplaces. Issues with marketplace platforms must be resolved directly with those platforms.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">8.3 API Limitations</h3>
        <p className="mb-4">
          Our integrations are subject to the API terms and limitations of third-party platforms. 
          Changes to third-party APIs may affect Service functionality, and we are not liable for 
          such disruptions.
        </p>
      </section>

      <section id="disclaimers" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">9. Disclaimers</h2>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">9.1 Service "As Is"</h3>
        <p className="mb-4 font-semibold">
          THE SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND, EITHER 
          EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO WARRANTIES OF MERCHANTABILITY, FITNESS 
          FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">9.2 No Guarantee of Sales or Income</h3>
        <p className="mb-4">
          We do not guarantee that you will make any sales, earn any income, or achieve any specific 
          results from using EmpireBox. Success depends on many factors beyond our control.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">9.3 Marketplace Availability</h3>
        <p className="mb-4">
          We do not guarantee continuous availability of marketplace integrations. Third-party 
          platforms may change their APIs, policies, or terms at any time.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">9.4 AI Recommendations</h3>
        <p className="mb-4">
          AI-powered recommendations and suggestions are for informational purposes only. We do not 
          guarantee their accuracy or effectiveness. You are responsible for all listing content and 
          pricing decisions.
        </p>
      </section>

      <section id="liability" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">10. Limitation of Liability</h2>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">10.1 Liability Cap</h3>
        <p className="mb-4 font-semibold">
          TO THE MAXIMUM EXTENT PERMITTED BY LAW, EMPIREBOX'S TOTAL LIABILITY TO YOU FOR ANY CLAIMS 
          ARISING FROM OR RELATED TO THE SERVICE SHALL NOT EXCEED THE AMOUNT YOU PAID TO EMPIREBOX 
          IN THE 12 MONTHS PRECEDING THE CLAIM.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">10.2 No Indirect Damages</h3>
        <p className="mb-4 font-semibold">
          WE SHALL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE 
          DAMAGES, INCLUDING LOST PROFITS, LOST REVENUE, LOST SALES, LOST DATA, OR BUSINESS INTERRUPTION.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">10.3 Marketplace Issues</h3>
        <p className="mb-4">
          We are not liable for any issues arising from your use of third-party marketplace platforms, 
          including account suspensions, listing removals, buyer disputes, or payment holds.
        </p>
      </section>

      <section id="indemnification" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">11. Indemnification</h2>
        <p className="mb-4">
          You agree to indemnify, defend, and hold harmless EmpireBox and its officers, directors, 
          employees, and agents from any claims, losses, damages, liabilities, and expenses (including 
          legal fees) arising from:
        </p>
        <ul className="list-disc pl-6 mb-4 space-y-2">
          <li>Your use of the Service</li>
          <li>Your violation of these Terms</li>
          <li>Your violation of any third-party rights</li>
          <li>Your content or listings</li>
          <li>Your sales or transactions</li>
        </ul>
      </section>

      <section id="disputes" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">12. Dispute Resolution</h2>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">12.1 Informal Resolution</h3>
        <p className="mb-4">
          Before filing any legal claim, you agree to first contact us at{" "}
          <a href="mailto:support@empirebox.com" className="text-primary-700 hover:underline">
            support@empirebox.com
          </a>{" "}
          to attempt to resolve the dispute informally.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">12.2 Governing Law</h3>
        <p className="mb-4">
          These Terms shall be governed by and construed in accordance with the laws of [YOUR STATE], 
          United States, without regard to its conflict of law provisions.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">12.3 Arbitration (Optional)</h3>
        <p className="mb-4">
          Any disputes not resolved informally shall be resolved through binding arbitration in 
          accordance with the rules of the American Arbitration Association.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">12.4 Class Action Waiver</h3>
        <p className="mb-4">
          You agree to resolve disputes with us on an individual basis and waive the right to 
          participate in class actions or class arbitrations.
        </p>
      </section>

      <section id="termination" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">13. Termination</h2>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">13.1 Cancellation by You</h3>
        <p className="mb-4">
          You may cancel your subscription at any time through your account settings or by 
          contacting support. Cancellation takes effect at the end of your current billing period.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">13.2 Termination by Us</h3>
        <p className="mb-4">
          We may suspend or terminate your account immediately if you:
        </p>
        <ul className="list-disc pl-6 mb-4 space-y-2">
          <li>Violate these Terms</li>
          <li>Engage in fraudulent activity</li>
          <li>Fail to pay fees owed</li>
          <li>Abuse the Service or harm other users</li>
        </ul>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">13.3 Effect of Termination</h3>
        <p className="mb-4">
          Upon termination, your right to use the Service immediately ceases. We may delete your 
          account data after a reasonable period. You remain responsible for all fees incurred 
          before termination.
        </p>
      </section>

      <section id="modifications" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">14. Modifications to Terms</h2>
        <p className="mb-4">
          We reserve the right to modify these Terms at any time. We will notify you of material 
          changes by email or through the Service. Your continued use after changes are posted 
          constitutes acceptance of the modified Terms.
        </p>
      </section>

      <section id="misc" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">15. Miscellaneous</h2>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">15.1 Severability</h3>
        <p className="mb-4">
          If any provision of these Terms is found to be unenforceable, the remaining provisions 
          will continue in full force and effect.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">15.2 Entire Agreement</h3>
        <p className="mb-4">
          These Terms, together with our Privacy Policy and any other legal notices published by 
          us, constitute the entire agreement between you and EmpireBox.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">15.3 Assignment</h3>
        <p className="mb-4">
          You may not assign or transfer these Terms without our prior written consent. We may 
          assign these Terms at any time without notice.
        </p>
      </section>

      <section id="contact" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">16. Contact Information</h2>
        <p className="mb-4">
          If you have questions about these Terms, please contact us:
        </p>
        <div className="bg-gray-50 p-4 rounded-lg">
          <p className="mb-2">
            <strong>Email:</strong>{" "}
            <a href="mailto:support@empirebox.com" className="text-primary-700 hover:underline">
              support@empirebox.com
            </a>
          </p>
          <p className="mb-2">
            <strong>General Inquiries:</strong>{" "}
            <a href="mailto:hello@empirebox.com" className="text-primary-700 hover:underline">
              hello@empirebox.com
            </a>
          </p>
          <p>
            <strong>Address:</strong><br />
            EmpireBox<br />
            [YOUR BUSINESS ADDRESS]<br />
            [CITY, STATE ZIP]
          </p>
        </div>
      </section>
    </LegalPageLayout>
  );
}
