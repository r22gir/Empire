'use client';

import { Download, Smartphone, Globe } from 'lucide-react';
import { DeviceType } from './DeviceDetector';

interface AppDownloadButtonsProps {
  device: DeviceType;
}

export default function AppDownloadButtons({ device }: AppDownloadButtonsProps) {
  const playStoreUrl = 'https://play.google.com/store/apps/details?id=com.empirebox.marketforge';
  const appStoreUrl = 'https://apps.apple.com/app/marketforge';
  const webAppUrl = 'https://app.empirebox.store';

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold text-center mb-6">Download MarketForge</h2>

      <div className="space-y-3">
        {/* Android Button */}
        {(device === 'android' || device === 'desktop') && (
          <a
            href={playStoreUrl}
            className="flex items-center justify-center gap-3 bg-green-600 hover:bg-green-700 text-white font-semibold py-4 px-6 rounded-lg transition-colors w-full"
          >
            <Download size={24} />
            <span>Download from Play Store</span>
          </a>
        )}

        {/* iOS Button */}
        {(device === 'ios' || device === 'desktop') && (
          <a
            href={appStoreUrl}
            className="flex items-center justify-center gap-3 bg-black hover:bg-gray-800 text-white font-semibold py-4 px-6 rounded-lg transition-colors w-full"
          >
            <Smartphone size={24} />
            <span>Download from App Store</span>
          </a>
        )}

        {/* Web App Button */}
        <a
          href={webAppUrl}
          className="flex items-center justify-center gap-3 bg-empire-blue hover:bg-empire-darkBlue text-white font-semibold py-4 px-6 rounded-lg transition-colors w-full"
        >
          <Globe size={24} />
          <span>Open Web App</span>
        </a>
      </div>

      <p className="text-sm text-gray-600 text-center mt-4">
        Choose your preferred platform to get started
      </p>
    </div>
  );
}
