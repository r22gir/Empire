'use client';

import { useState } from 'react';
import { Check, Loader2 } from 'lucide-react';
import { licenseApi } from '@/lib/api';

interface LicenseActivationProps {
  licenseKey: string;
  onActivated: (details: any) => void;
}

export default function LicenseActivation({ licenseKey, onActivated }: LicenseActivationProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [licenseInfo, setLicenseInfo] = useState<any>(null);

  const handleActivate = async () => {
    setLoading(true);
    setError(null);

    try {
      // In production, get user_id from authenticated session
      const userId = 'demo_user_' + Date.now();
      
      const response = await licenseApi.activate(licenseKey, userId);
      
      if (response.success) {
        setLicenseInfo(response.subscription_details);
        onActivated(response.subscription_details);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to activate license');
    } finally {
      setLoading(false);
    }
  };

  if (licenseInfo) {
    return (
      <div className="text-center space-y-6">
        <div className="bg-green-50 border-2 border-green-300 rounded-lg p-8">
          <div className="flex justify-center mb-4">
            <div className="bg-green-500 rounded-full p-3">
              <Check size={48} className="text-white" />
            </div>
          </div>
          <h2 className="text-2xl font-bold text-green-900 mb-2">Subscription Activated!</h2>
          <p className="text-green-800">Your license has been successfully activated.</p>
        </div>

        <div className="bg-white border-2 border-gray-200 rounded-lg p-6 text-left">
          <h3 className="font-semibold text-lg mb-4">Your Subscription Details:</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Plan:</span>
              <span className="font-semibold uppercase">{licenseInfo.plan}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Duration:</span>
              <span className="font-semibold">{licenseInfo.duration_months} months</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Expires:</span>
              <span className="font-semibold">
                {new Date(licenseInfo.expires_at).toLocaleDateString()}
              </span>
            </div>
            {licenseInfo.hardware_bundle && (
              <div className="flex justify-between">
                <span className="text-gray-600">Hardware Bundle:</span>
                <span className="font-semibold">{licenseInfo.hardware_bundle}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold mb-2">Activate Your Subscription</h2>
        <p className="text-gray-600">
          Ready to unlock your MarketForge subscription? Let's get started!
        </p>
      </div>

      <div className="bg-white border-2 border-gray-200 rounded-lg p-6">
        <h3 className="font-semibold mb-4">What's included:</h3>
        <ul className="space-y-2 text-sm">
          <li className="flex items-start gap-2">
            <Check size={20} className="text-green-500 flex-shrink-0 mt-0.5" />
            <span>Full access to MarketForge Pro features</span>
          </li>
          <li className="flex items-start gap-2">
            <Check size={20} className="text-green-500 flex-shrink-0 mt-0.5" />
            <span>AI-powered listing optimization</span>
          </li>
          <li className="flex items-start gap-2">
            <Check size={20} className="text-green-500 flex-shrink-0 mt-0.5" />
            <span>Multi-marketplace integration</span>
          </li>
          <li className="flex items-start gap-2">
            <Check size={20} className="text-green-500 flex-shrink-0 mt-0.5" />
            <span>Advanced analytics and insights</span>
          </li>
          <li className="flex items-start gap-2">
            <Check size={20} className="text-green-500 flex-shrink-0 mt-0.5" />
            <span>Priority customer support</span>
          </li>
        </ul>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-300 text-red-800 rounded-lg p-4">
          <p className="font-semibold">Activation Failed</p>
          <p className="text-sm">{error}</p>
        </div>
      )}

      <button
        onClick={handleActivate}
        disabled={loading}
        className="w-full bg-empire-orange hover:bg-orange-600 text-white font-bold py-4 px-6 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
      >
        {loading ? (
          <>
            <Loader2 size={24} className="animate-spin" />
            <span>Activating...</span>
          </>
        ) : (
          <span>Activate License</span>
        )}
      </button>

      <p className="text-xs text-gray-500 text-center">
        By activating, you agree to the EmpireBox Terms of Service and Privacy Policy
      </p>
    </div>
  );
}
