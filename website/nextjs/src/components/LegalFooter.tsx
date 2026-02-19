import Link from 'next/link';

export default function LegalFooter() {
  return (
    <div className="mt-12 pt-8 border-t border-gray-200 text-center">
      <p className="text-sm text-gray-600 mb-3">
        By purchasing, you agree to our{' '}
        <Link href="/terms" className="text-primary-700 hover:underline">Terms of Service</Link>
        ,{' '}
        <Link href="/privacy" className="text-primary-700 hover:underline">Privacy Policy</Link>
        , and{' '}
        <Link href="/refund-policy" className="text-primary-700 hover:underline">Refund Policy</Link>.
      </p>
      <p className="text-xs text-gray-500">
        EMPIREBOX &bull; www.empirebox.store &bull;{' '}
        <a href="mailto:support@empirebox.store" className="hover:underline">support@empirebox.store</a>
        {' '}&bull;{' '}
        <Link href="/contact" className="hover:underline">Contact Us</Link>
      </p>
    </div>
  );
}
