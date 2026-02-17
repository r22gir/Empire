import Link from 'next/link';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-empire-blue to-empire-lightBlue text-white">
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-6xl font-bold mb-6">EmpireBox</h1>
          <p className="text-2xl mb-12 opacity-90">
            Your Complete Reselling Business in a Box
          </p>

          <div className="grid md:grid-cols-2 gap-6 mb-12">
            <Link
              href="/setup"
              className="bg-white text-empire-blue font-bold py-8 px-6 rounded-xl hover:shadow-2xl transition-shadow"
            >
              <h2 className="text-2xl mb-2">Setup Portal</h2>
              <p className="text-sm opacity-75">
                Activate your hardware bundle with a license key
              </p>
            </Link>

            <Link
              href="/bundles"
              className="bg-empire-orange text-white font-bold py-8 px-6 rounded-xl hover:shadow-2xl transition-shadow"
            >
              <h2 className="text-2xl mb-2">Hardware Bundles</h2>
              <p className="text-sm opacity-90">
                Pre-order complete bundles shipping March 2026
              </p>
            </Link>
          </div>

          <div className="bg-white bg-opacity-10 backdrop-blur-sm rounded-xl p-8">
            <h3 className="text-xl font-semibold mb-4">What's Included:</h3>
            <ul className="text-left max-w-2xl mx-auto space-y-2">
              <li>✅ Professional reselling phone (factory sealed)</li>
              <li>✅ MarketForge Pro subscription (12 months)</li>
              <li>✅ QR code instant setup</li>
              <li>✅ Secure crypto wallet (Seeker models)</li>
              <li>✅ AI-powered listing tools</li>
              <li>✅ Multi-marketplace integration</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
