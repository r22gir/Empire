import Link from 'next/link';
import { QrCode, Search, Usb } from 'lucide-react';

export default function LandingPage() {
  return (
    <main className="flex flex-col items-center justify-center min-h-screen px-4 py-12">
      <div className="max-w-lg w-full text-center">
        {/* Logo / Title */}
        <h1 className="text-4xl font-bold mb-2" style={{ color: '#C9A84C' }}>
          EmpireBox
        </h1>
        <p className="text-gray-400 mb-10 text-lg">Mini PC Setup Portal</p>

        {/* Setup options */}
        <div className="space-y-4">
          {/* QR / Serial entry */}
          <Link
            href="/setup"
            className="flex items-center gap-4 p-5 rounded-xl border border-gold hover:bg-white/5 transition-colors"
            style={{ borderColor: '#C9A84C' }}
          >
            <div className="p-3 rounded-lg" style={{ backgroundColor: '#C9A84C22' }}>
              <QrCode size={28} style={{ color: '#C9A84C' }} />
            </div>
            <div className="text-left">
              <div className="font-semibold text-lg">Scan QR Code</div>
              <div className="text-gray-400 text-sm">Scan the sticker on your EmpireBox</div>
            </div>
          </Link>

          <Link
            href="/setup"
            className="flex items-center gap-4 p-5 rounded-xl border border-white/20 hover:bg-white/5 transition-colors"
          >
            <div className="p-3 rounded-lg bg-white/10">
              <Search size={28} className="text-white" />
            </div>
            <div className="text-left">
              <div className="font-semibold text-lg">Enter Serial Number</div>
              <div className="text-gray-400 text-sm">Type the serial number from your device</div>
            </div>
          </Link>

          <div className="flex items-center gap-4 p-5 rounded-xl border border-white/10 bg-white/5">
            <div className="p-3 rounded-lg bg-white/10">
              <Usb size={28} className="text-gray-400" />
            </div>
            <div className="text-left">
              <div className="font-semibold text-lg text-gray-400">USB Auto-Config</div>
              <div className="text-gray-500 text-sm">Drop empirebox-config.json on a USB drive</div>
            </div>
          </div>
        </div>

        <p className="mt-8 text-gray-500 text-sm">
          Need help?{' '}
          <a href="https://docs.empirebox.com" className="underline" style={{ color: '#C9A84C' }}>
            View documentation
          </a>
        </p>
      </div>
    </main>
  );
}
