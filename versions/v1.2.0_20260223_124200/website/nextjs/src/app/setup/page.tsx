import Link from 'next/link';
import { QrCode, Package, Shield } from 'lucide-react';

export default function SetupPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-empire-blue to-empire-lightBlue text-white">
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-2xl mx-auto text-center">
          {/* Logo/Brand */}
          <h1 className="text-5xl font-bold mb-4">EmpireBox Setup</h1>
          <p className="text-xl mb-12 opacity-90">
            Welcome! Let's get your hardware bundle set up
          </p>

          {/* Main Card */}
          <div className="bg-white text-gray-900 rounded-2xl shadow-2xl p-8 mb-8">
            <div className="flex justify-center mb-6">
              <div className="bg-empire-orange rounded-full p-4">
                <QrCode size={48} className="text-white" />
              </div>
            </div>

            <h2 className="text-2xl font-bold mb-4">
              Scan Your QR Code to Get Started
            </h2>
            <p className="text-gray-600 mb-6">
              Find the QR code on your Quick Start Card included in your EmpireBox bundle.
              Scan it with your phone to begin the setup process.
            </p>

            <div className="border-t border-gray-200 pt-6 mt-6">
              <h3 className="font-semibold mb-4">Or enter your license key manually:</h3>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const formData = new FormData(e.currentTarget);
                  const key = formData.get('key') as string;
                  if (key) {
                    window.location.href = `/setup/${key}`;
                  }
                }}
                className="space-y-4"
              >
                <input
                  type="text"
                  name="key"
                  placeholder="EMPIRE-XXXX-XXXX-XXXX"
                  className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg text-center font-mono uppercase focus:border-empire-blue focus:outline-none"
                  pattern="EMPIRE-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}"
                  required
                />
                <button
                  type="submit"
                  className="w-full bg-empire-orange hover:bg-orange-600 text-white font-bold py-3 px-6 rounded-lg transition-colors"
                >
                  Continue Setup
                </button>
              </form>
            </div>
          </div>

          {/* Features */}
          <div className="grid md:grid-cols-3 gap-4 text-left">
            <div className="bg-white bg-opacity-10 backdrop-blur-sm rounded-lg p-4">
              <Package className="mb-2" size={24} />
              <h3 className="font-semibold mb-1">Complete Bundle</h3>
              <p className="text-sm opacity-90">
                Everything you need to start reselling
              </p>
            </div>
            <div className="bg-white bg-opacity-10 backdrop-blur-sm rounded-lg p-4">
              <Shield className="mb-2" size={24} />
              <h3 className="font-semibold mb-1">Secure Setup</h3>
              <p className="text-sm opacity-90">
                Your device ships sealed and untouched
              </p>
            </div>
            <div className="bg-white bg-opacity-10 backdrop-blur-sm rounded-lg p-4">
              <QrCode className="mb-2" size={24} />
              <h3 className="font-semibold mb-1">Easy Activation</h3>
              <p className="text-sm opacity-90">
                Scan QR code for instant setup
              </p>
            </div>
          </div>

          {/* Help Link */}
          <div className="mt-8">
            <Link href="/help" className="text-white hover:underline">
              Need help? Visit our support center
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
