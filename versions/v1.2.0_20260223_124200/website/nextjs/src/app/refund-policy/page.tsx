import { Metadata } from "next";
import LegalPageLayout from "@/components/LegalPageLayout";

export const metadata: Metadata = {
  title: "Refund Policy | EmpireBox",
  description: "EmpireBox refund and cancellation policy for subscriptions and services.",
  robots: "noindex",
};

const tocItems = [
  { id: "overview", title: "Policy Overview" },
  { id: "free-trial", title: "Free Trial" },
  { id: "cancellation", title: "Subscription Cancellation" },
  { id: "refund-eligibility", title: "Refund Eligibility" },
  { id: "non-refundable", title: "Non-Refundable Items" },
  { id: "request", title: "How to Request Refund" },
  { id: "processing", title: "Refund Processing" },
  { id: "chargebacks", title: "Chargebacks" },
  { id: "contact", title: "Contact" },
];

export default function RefundPolicyPage() {
  return (
    <LegalPageLayout
      title="Refund & Cancellation Policy"
      lastUpdated="February 17, 2026"
      showToc={true}
      tocItems={tocItems}
    >
      <section id="overview" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">1. Policy Overview</h2>
        <p className="mb-4">
          At EmpireBox, we want you to be completely satisfied with our service. This Refund & 
          Cancellation Policy explains your rights regarding subscription cancellations and refunds.
        </p>
        <p className="mb-4">
          Please read this policy carefully before subscribing to understand when refunds are and 
          are not available.
        </p>
      </section>

      <section id="free-trial" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">2. Free Trial</h2>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">2.1 7-Day Free Trial</h3>
        <p className="mb-4">
          EmpireBox offers a 7-day free trial for new users. During the trial period:
        </p>
        <ul className="list-disc pl-6 mb-4 space-y-2">
          <li>You have full access to all features of your selected plan</li>
          <li>You will not be charged if you cancel before the trial ends</li>
          <li>No credit card is required to start the trial</li>
        </ul>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">2.2 How to Cancel During Trial</h3>
        <p className="mb-4">
          To cancel your trial and avoid being charged:
        </p>
        <ol className="list-decimal pl-6 mb-4 space-y-2">
          <li>Log into your EmpireBox account</li>
          <li>Go to Settings → Subscription</li>
          <li>Click "Cancel Trial" or "Cancel Subscription"</li>
          <li>Confirm cancellation</li>
        </ol>
        <p className="mb-4">
          Alternatively, you can email{" "}
          <a href="mailto:support@empirebox.com" className="text-primary-700 hover:underline">
            support@empirebox.com
          </a>{" "}
          with your account email to cancel.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">2.3 After Trial Ends</h3>
        <p className="mb-4">
          If you do not cancel before your trial ends, your payment method will be charged the 
          subscription fee for your selected plan, and your subscription will begin.
        </p>
      </section>

      <section id="cancellation" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">3. Subscription Cancellation</h2>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">3.1 Cancel Anytime</h3>
        <p className="mb-4 font-semibold">
          You can cancel your EmpireBox subscription at any time. There are no cancellation fees 
          or penalties.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">3.2 Access Until End of Billing Period</h3>
        <p className="mb-4">
          When you cancel your subscription:
        </p>
        <ul className="list-disc pl-6 mb-4 space-y-2">
          <li>You will continue to have access until the end of your current billing period</li>
          <li>You will not be charged again after your current billing period ends</li>
          <li>Your account will be downgraded to a free tier (if available) or deactivated</li>
        </ul>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">3.3 No Partial Refunds</h3>
        <p className="mb-4">
          Canceling your subscription does not entitle you to a refund for the unused portion of 
          your billing period. You have paid for access through the end of the period, and that 
          access will be maintained.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">3.4 How to Cancel</h3>
        <p className="mb-4">
          <strong>Option 1: Through Account Settings</strong>
        </p>
        <ol className="list-decimal pl-6 mb-4 space-y-2">
          <li>Log into your EmpireBox account</li>
          <li>Navigate to Settings → Subscription</li>
          <li>Click "Cancel Subscription"</li>
          <li>Follow the prompts to confirm cancellation</li>
        </ol>
        <p className="mb-4">
          <strong>Option 2: Email Support</strong>
        </p>
        <p className="mb-4">
          Email{" "}
          <a href="mailto:support@empirebox.com" className="text-primary-700 hover:underline">
            support@empirebox.com
          </a>{" "}
          with your account email and request to cancel your subscription.
        </p>
      </section>

      <section id="refund-eligibility" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">4. Refund Eligibility</h2>
        <p className="mb-4">
          Refunds are available in the following circumstances:
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">4.1 14-Day Satisfaction Guarantee</h3>
        <p className="mb-4">
          If you are not satisfied with EmpireBox, you may request a full refund within 14 days 
          of your first paid subscription charge (not including the free trial period).
        </p>
        <p className="mb-4">
          This guarantee applies only to your first payment. Subsequent renewals are not eligible 
          for this guarantee.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">4.2 Technical Issues</h3>
        <p className="mb-4">
          If you experienced significant technical issues that prevented you from using the Service, 
          and we were unable to resolve them within a reasonable timeframe, you may be eligible 
          for a prorated refund.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">4.3 Duplicate Charges</h3>
        <p className="mb-4">
          If you were accidentally charged twice or charged in error, we will issue a full refund 
          for the duplicate or erroneous charge.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">4.4 Billing Errors</h3>
        <p className="mb-4">
          If we made a billing error (e.g., charged wrong amount, charged after cancellation), 
          we will correct it and refund the difference.
        </p>
      </section>

      <section id="non-refundable" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">5. Non-Refundable Items</h2>
        <p className="mb-4">
          The following are NOT eligible for refunds:
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">5.1 Commission Fees</h3>
        <p className="mb-4 font-semibold">
          Commission fees charged on completed sales are non-refundable, even if:
        </p>
        <ul className="list-disc pl-6 mb-4 space-y-2">
          <li>The buyer returns the item</li>
          <li>The transaction is later cancelled</li>
          <li>You have a dispute with the buyer</li>
          <li>The marketplace charges you fees or holds your payment</li>
        </ul>
        <p className="mb-4">
          Commission is earned when the sale completes, regardless of post-sale issues.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">5.2 Partial Month Subscriptions</h3>
        <p className="mb-4">
          If you cancel mid-billing period, you will not receive a refund for the unused time. 
          You will retain access until the end of the period you paid for.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">5.3 After 14-Day Window</h3>
        <p className="mb-4">
          Subscription fees paid more than 14 days ago (except your first payment) are not eligible 
          for refunds, except in cases of technical issues or billing errors.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">5.4 Account Termination for Violations</h3>
        <p className="mb-4">
          If your account is terminated due to violations of our Terms of Service, you are not 
          entitled to a refund of any fees paid.
        </p>
      </section>

      <section id="request" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">6. How to Request a Refund</h2>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">6.1 Submit Request</h3>
        <p className="mb-4">
          To request a refund, email{" "}
          <a href="mailto:support@empirebox.com" className="text-primary-700 hover:underline">
            support@empirebox.com
          </a>{" "}
          with the following information:
        </p>
        <ul className="list-disc pl-6 mb-4 space-y-2">
          <li>Your account email address</li>
          <li>Reason for refund request</li>
          <li>Date of charge(s) in question</li>
          <li>Any relevant details or screenshots</li>
        </ul>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">6.2 Response Time</h3>
        <p className="mb-4">
          We will review your refund request and respond within 48 business hours (Monday-Friday, 
          9am-6pm EST, excluding holidays).
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">6.3 Approval Process</h3>
        <p className="mb-4">
          We review each refund request on a case-by-case basis. We may ask for additional 
          information to process your request. We reserve the right to approve or deny refund 
          requests at our discretion, in accordance with this policy.
        </p>
      </section>

      <section id="processing" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">7. Refund Processing</h2>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">7.1 Processing Time</h3>
        <p className="mb-4">
          Once a refund is approved:
        </p>
        <ul className="list-disc pl-6 mb-4 space-y-2">
          <li>We will process the refund within 5-10 business days</li>
          <li>Refunds are issued to the original payment method</li>
          <li>You will receive an email confirmation when the refund is processed</li>
        </ul>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">7.2 Payment Processor Time</h3>
        <p className="mb-4">
          After we process the refund, it may take additional time for your bank or credit card 
          company to post the refund to your account. This is typically:
        </p>
        <ul className="list-disc pl-6 mb-4 space-y-2">
          <li>Credit cards: 5-10 business days</li>
          <li>Debit cards: 5-10 business days</li>
          <li>Bank accounts: 5-10 business days</li>
        </ul>
        <p className="mb-4">
          If you don't see the refund after this timeframe, please contact your bank or card issuer.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">7.3 Stripe Processing</h3>
        <p className="mb-4">
          All refunds are processed through Stripe, our payment processor. You will see the refund 
          as a credit from "EmpireBox" or "Stripe" on your statement.
        </p>
      </section>

      <section id="chargebacks" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">8. Chargebacks</h2>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">8.1 Contact Us First</h3>
        <p className="mb-4 font-semibold">
          Before filing a chargeback or payment dispute with your bank, please contact us first 
          at{" "}
          <a href="mailto:support@empirebox.com" className="text-primary-700 hover:underline">
            support@empirebox.com
          </a>
        </p>
        <p className="mb-4">
          We are committed to resolving billing issues quickly and fairly. Chargebacks are costly 
          and time-consuming for both parties.
        </p>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">8.2 Chargeback Consequences</h3>
        <p className="mb-4">
          If you file a chargeback without first attempting to resolve the issue with us:
        </p>
        <ul className="list-disc pl-6 mb-4 space-y-2">
          <li>Your account will be immediately suspended</li>
          <li>We may charge a chargeback processing fee (typically $15-25)</li>
          <li>You may be permanently banned from using EmpireBox</li>
          <li>We will dispute the chargeback if it is not valid</li>
        </ul>

        <h3 className="text-xl font-semibold text-gray-800 mb-3">8.3 Valid Chargebacks</h3>
        <p className="mb-4">
          If you file a chargeback for a valid reason (fraud, unauthorized charge, etc.), we will 
          not penalize you. However, we still prefer you contact us first so we can resolve the 
          issue quickly.
        </p>
      </section>

      <section id="contact" className="mb-8">
        <h2 className="text-2xl font-heading font-bold text-gray-900 mb-4">9. Contact for Questions</h2>
        <p className="mb-4">
          If you have questions about our refund policy, cancellation process, or a specific charge, 
          please contact us:
        </p>
        <div className="bg-gray-50 p-4 rounded-lg">
          <p className="mb-2">
            <strong>Support Email:</strong>{" "}
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
            <strong>Business Hours:</strong> Monday-Friday, 9am-6pm EST
          </p>
          <p>
            <strong>Response Time:</strong> Within 24-48 hours
          </p>
        </div>
        <p className="mt-4">
          We're here to help and want to ensure you have a positive experience with EmpireBox.
        </p>
      </section>
    </LegalPageLayout>
  );
}
