import { Metadata } from "next";
import LegalPageLayout from "@/components/LegalPageLayout";

export const metadata: Metadata = {
  title: "Privacy Policy | EmpireBox",
  description: "Learn how EmpireBox collects, uses, and protects your personal information.",
  robots: "noindex",
};

const tocItems = [
  { id: "intro", title: "Introduction" },
  { id: "info-collect", title: "Information We Collect" },
  { id: "how-we-use", title: "How We Use Information" },
  { id: "sharing", title: "Information Sharing" },
  { id: "retention", title: "Data Retention" },
  { id: "your-rights", title: "Your Rights" },
  { id: "gdpr", title: "GDPR Compliance" },
  { id: "ccpa", title: "CCPA Compliance" },
  { id: "cookies", title: "Cookie Policy" },
  { id: "children", title: "Children's Privacy" },
  { id: "security", title: "Security" },
  { id: "changes", title: "Changes to Policy" },
  { id: "contact", title: "Contact Us" },
];

export default function PrivacyPage() {
  return (
    <LegalPageLayout
      title="Privacy Policy"
      lastUpdated="February 17, 2026"
      showToc={true}
      tocItems={tocItems}
    >
      <section id="intro" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">1. Introduction</h2>
        <p className="mb-4">
          Welcome to EmpireBox. We are committed to protecting your privacy and ensuring the security 
          of your personal information. This Privacy Policy explains how we collect, use, disclose, 
          and safeguard your information when you use our services.
        </p>
        <p className="mb-4">
          <strong>Company Information:</strong><br />
          EmpireBox<br />
          Email: <a href="mailto:hello@empirebox.com" className="text-primary-700 hover:underline">hello@empirebox.com</a><br />
          Support: <a href="mailto:support@empirebox.com" className="text-primary-700 hover:underline">support@empirebox.com</a>
        </p>
        <p>
          By using EmpireBox, you agree to the collection and use of information in accordance with this policy.
        </p>
      </section>

      <section id="info-collect" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">2. Information We Collect</h2>
        
        <h3 className="text-xl font-semibold text-gray-800 mb-3">2.1 Account Information</h3>
        <p className="mb-4">When you create an account, we collect:</p>
        <ul className="list-disc pl-6 mb-4 space-y-2">
          <li>Name (first and last)</li>
          <li>Email address</li>
          <li>Password (stored as an encrypted hash)</li>
          <li>Account preferences and settings</li>
        </ul>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">2.2 Payment Information</h3>
        <p className="mb-4">
          Payment information is processed securely by Stripe, our payment processor. We do not store 
          your complete credit card information on our servers. We receive and store:
        </p>
        <ul className="list-disc pl-6 mb-4 space-y-2">
          <li>Last 4 digits of your card</li>
          <li>Card brand (Visa, Mastercard, etc.)</li>
          <li>Card expiration date</li>
          <li>Billing address</li>
          <li>Transaction history</li>
        </ul>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">2.3 Usage Data</h3>
        <p className="mb-4">We collect information about how you use our service:</p>
        <ul className="list-disc pl-6 mb-4 space-y-2">
          <li>Marketplace listings you create</li>
          <li>Sales and transaction data</li>
          <li>AI agent interactions and preferences</li>
          <li>App features you use</li>
          <li>Time and frequency of use</li>
        </ul>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">2.4 Device and Technical Information</h3>
        <ul className="list-disc pl-6 mb-4 space-y-2">
          <li>IP address</li>
          <li>Browser type and version</li>
          <li>Device type and operating system</li>
          <li>Unique device identifiers</li>
          <li>Crash reports and performance data</li>
        </ul>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">2.5 Cookies and Tracking Technologies</h3>
        <p className="mb-4">
          We use cookies, web beacons, and similar tracking technologies to collect information 
          about your browsing activity. See Section 9 for details about our Cookie Policy.
        </p>
      </section>

      <section id="how-we-use" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">3. How We Use Information</h2>
        <p className="mb-4">We use the collected information for the following purposes:</p>
        
        <h3 className="text-xl font-semibold text-gray-800 mb-3">3.1 Provide and Improve Services</h3>
        <ul className="list-disc pl-6 mb-4 space-y-2">
          <li>Operate and maintain the EmpireBox platform</li>
          <li>Process your marketplace listings</li>
          <li>Enable AI-powered features and automation</li>
          <li>Improve and optimize our services</li>
          <li>Develop new features</li>
        </ul>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">3.2 Process Payments</h3>
        <ul className="list-disc pl-6 mb-4 space-y-2">
          <li>Process subscription payments</li>
          <li>Calculate and collect commission fees</li>
          <li>Issue refunds when applicable</li>
          <li>Prevent fraud and unauthorized transactions</li>
        </ul>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">3.3 Communications</h3>
        <ul className="list-disc pl-6 mb-4 space-y-2">
          <li>Send transactional emails (receipts, confirmations)</li>
          <li>Provide customer support</li>
          <li>Send important service updates</li>
          <li>Notify you of new features</li>
          <li>Send marketing communications (with opt-out option)</li>
        </ul>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">3.4 Analytics and Research</h3>
        <ul className="list-disc pl-6 mb-4 space-y-2">
          <li>Analyze usage patterns</li>
          <li>Understand user behavior</li>
          <li>Conduct market research</li>
          <li>Generate anonymized statistics</li>
        </ul>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">3.5 Marketing</h3>
        <p className="mb-4">
          With your consent, we may use your information for marketing purposes. You can opt-out 
          at any time by clicking the unsubscribe link in our emails or contacting us.
        </p>
      </section>

      <section id="sharing" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">4. Information Sharing</h2>
        <p className="mb-4">
          We do not sell your personal information. We may share your information with:
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">4.1 Stripe (Payment Processing)</h3>
        <p className="mb-4">
          Payment information is shared with Stripe to process transactions. Stripe's use of your 
          information is governed by their privacy policy.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">4.2 Marketplace Platforms</h3>
        <p className="mb-4">
          When you create listings, we share necessary information with marketplace platforms 
          (eBay, Facebook Marketplace, etc.) to post and manage your listings. Each platform 
          has its own privacy policy.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">4.3 Analytics Providers</h3>
        <p className="mb-4">
          We use third-party analytics services to understand how users interact with our platform. 
          This helps us improve our services.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">4.4 Legal Requirements</h3>
        <p className="mb-4">We may disclose your information if required to:</p>
        <ul className="list-disc pl-6 mb-4 space-y-2">
          <li>Comply with legal obligations</li>
          <li>Respond to valid legal requests</li>
          <li>Protect our rights and safety</li>
          <li>Prevent fraud or illegal activity</li>
          <li>Enforce our Terms of Service</li>
        </ul>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">4.5 Business Transfers</h3>
        <p className="mb-4">
          In the event of a merger, acquisition, or sale of assets, your information may be 
          transferred to the acquiring entity. You will be notified of any such change.
        </p>
      </section>

      <section id="retention" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">5. Data Retention</h2>
        <p className="mb-4">We retain your information for different periods based on the type of data:</p>
        <ul className="list-disc pl-6 mb-4 space-y-2">
          <li><strong>Account Data:</strong> While your account is active plus 3 years after closure</li>
          <li><strong>Transaction Data:</strong> 7 years (legal and tax requirement)</li>
          <li><strong>Usage Logs:</strong> 90 days</li>
          <li><strong>Marketing Data:</strong> Until you opt-out or 3 years of inactivity</li>
        </ul>
        <p>
          You may request deletion of your data at any time, subject to legal retention requirements.
        </p>
      </section>

      <section id="your-rights" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">6. Your Rights</h2>
        <p className="mb-4">You have the following rights regarding your personal information:</p>
        
        <h3 className="text-xl font-semibold text-gray-800 mb-3">6.1 Access Your Data</h3>
        <p className="mb-4">
          You can request a copy of all personal information we hold about you.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">6.2 Correct Inaccurate Data</h3>
        <p className="mb-4">
          You can update your account information at any time through your account settings 
          or by contacting us.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">6.3 Delete Your Data</h3>
        <p className="mb-4">
          You can request deletion of your account and associated data. Some information may 
          be retained for legal compliance.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">6.4 Export Your Data</h3>
        <p className="mb-4">
          You can request a machine-readable copy of your data for portability.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">6.5 Opt-Out of Marketing</h3>
        <p className="mb-4">
          You can unsubscribe from marketing emails at any time by clicking the unsubscribe 
          link or contacting us.
        </p>

        <p className="mt-4">
          To exercise these rights, contact us at{" "}
          <a href="mailto:support@empirebox.com" className="text-primary-700 hover:underline">
            support@empirebox.com
          </a>
        </p>
      </section>

      <section id="gdpr" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">7. GDPR Compliance (EU Users)</h2>
        <p className="mb-4">
          If you are located in the European Economic Area (EEA), you have additional rights under 
          the General Data Protection Regulation (GDPR).
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">7.1 Legal Basis for Processing</h3>
        <p className="mb-4">We process your data based on:</p>
        <ul className="list-disc pl-6 mb-4 space-y-2">
          <li><strong>Contract:</strong> To provide our services to you</li>
          <li><strong>Legitimate Interest:</strong> To improve our services and prevent fraud</li>
          <li><strong>Consent:</strong> For marketing communications</li>
          <li><strong>Legal Obligation:</strong> To comply with laws and regulations</li>
        </ul>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">7.2 Data Transfers</h3>
        <p className="mb-4">
          Your data may be transferred to and processed in countries outside the EEA. We ensure 
          appropriate safeguards are in place to protect your data.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">7.3 Right to Lodge Complaint</h3>
        <p className="mb-4">
          You have the right to lodge a complaint with your local data protection authority if 
          you believe we have not complied with GDPR requirements.
        </p>
      </section>

      <section id="ccpa" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">8. CCPA Compliance (California Users)</h2>
        <p className="mb-4">
          If you are a California resident, you have rights under the California Consumer Privacy 
          Act (CCPA).
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">8.1 Categories of Data Collected</h3>
        <p className="mb-4">We collect the following categories of personal information:</p>
        <ul className="list-disc pl-6 mb-4 space-y-2">
          <li>Identifiers (name, email, IP address)</li>
          <li>Commercial information (transaction history)</li>
          <li>Internet activity (browsing behavior, usage data)</li>
          <li>Financial information (payment details via Stripe)</li>
        </ul>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">8.2 Right to Know</h3>
        <p className="mb-4">
          You have the right to request details about the personal information we collect, 
          use, and disclose.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">8.3 Right to Delete</h3>
        <p className="mb-4">
          You have the right to request deletion of your personal information, subject to 
          certain exceptions.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">8.4 Right to Opt-Out of Sale</h3>
        <p className="mb-4">
          We do not sell your personal information to third parties.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">8.5 Non-Discrimination</h3>
        <p className="mb-4">
          We will not discriminate against you for exercising your CCPA rights.
        </p>
      </section>

      <section id="cookies" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">9. Cookie Policy</h2>
        <p className="mb-4">
          We use cookies and similar tracking technologies to enhance your experience.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">9.1 Essential Cookies</h3>
        <p className="mb-4">
          These cookies are necessary for the website to function properly. They enable core 
          functionality such as security, authentication, and session management.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">9.2 Analytics Cookies</h3>
        <p className="mb-4">
          We use analytics cookies to understand how users interact with our website. This helps 
          us improve our services. These cookies collect anonymized data.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">9.3 Marketing Cookies</h3>
        <p className="mb-4">
          With your consent, we use marketing cookies to deliver relevant advertisements and 
          track campaign performance.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">9.4 Managing Cookies</h3>
        <p className="mb-4">
          You can control and manage cookies through your browser settings. Note that disabling 
          certain cookies may impact website functionality.
        </p>
      </section>

      <section id="children" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">10. Children's Privacy</h2>
        <p className="mb-4">
          Our service is not intended for users under the age of 18. We do not knowingly collect 
          personal information from children under 18. If you are a parent or guardian and believe 
          your child has provided us with personal information, please contact us immediately, 
          and we will delete such information.
        </p>
      </section>

      <section id="security" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">11. Security Measures</h2>
        <p className="mb-4">
          We implement industry-standard security measures to protect your personal information:
        </p>
        <ul className="list-disc pl-6 mb-4 space-y-2">
          <li>Encryption of data in transit (TLS/SSL)</li>
          <li>Encryption of sensitive data at rest</li>
          <li>Regular security audits and assessments</li>
          <li>Access controls and authentication</li>
          <li>Secure payment processing through Stripe</li>
          <li>Regular backups and disaster recovery plans</li>
        </ul>
        <p className="mb-4">
          While we strive to protect your information, no method of transmission over the internet 
          or electronic storage is 100% secure. We cannot guarantee absolute security.
        </p>
      </section>

      <section id="changes" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">12. Changes to This Policy</h2>
        <p className="mb-4">
          We may update this Privacy Policy from time to time to reflect changes in our practices 
          or legal requirements. We will notify you of significant changes by:
        </p>
        <ul className="list-disc pl-6 mb-4 space-y-2">
          <li>Updating the "Last Updated" date at the top of this policy</li>
          <li>Sending an email notification to your registered email address</li>
          <li>Displaying a prominent notice on our website</li>
        </ul>
        <p className="mb-4">
          Your continued use of EmpireBox after changes are posted constitutes acceptance of 
          the updated policy.
        </p>
      </section>

      <section id="contact" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">13. Contact Us</h2>
        <p className="mb-4">
          If you have questions, concerns, or requests regarding this Privacy Policy or our data 
          practices, please contact us:
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
          <p className="mb-2">
            <strong>Address:</strong><br />
            EmpireBox<br />
            [YOUR BUSINESS ADDRESS]<br />
            [CITY, STATE ZIP]
          </p>
          <p>
            <strong>Response Time:</strong> We aim to respond to all inquiries within 24-48 hours.
          </p>
        </div>
      </section>
    </LegalPageLayout>
  );
}
