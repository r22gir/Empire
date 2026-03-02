'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { licenseApi } from '@/lib/api';
import DeviceDetector, { DeviceType } from '@/components/setup/DeviceDetector';
import SetupProgress from '@/components/setup/SetupProgress';
import AppDownloadButtons from '@/components/setup/AppDownloadButtons';
import WalletSetupGuide from '@/components/setup/WalletSetupGuide';
import LicenseActivation from '@/components/setup/LicenseActivation';
import { Loader2, AlertCircle, PartyPopper, ExternalLink } from 'lucide-react';

const SETUP_STEPS = [
  { id: 1, title: 'Download', description: 'Get MarketForge App' },
  { id: 2, title: 'Wallet', description: 'Create Secure Wallet' },
  { id: 3, title: 'Activate', description: 'Activate Subscription' },
  { id: 4, title: 'Ready!', description: 'Start Selling' },
];

export default function LicenseSetupPage() {
  const params = useParams();
  const router = useRouter();
  const licenseKey = params.licenseKey as string;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [licenseData, setLicenseData] = useState<any>(null);
  const [device, setDevice] = useState<DeviceType>('desktop');
  const [currentStep, setCurrentStep] = useState(0);
  const [subscriptionDetails, setSubscriptionDetails] = useState<any>(null);

  useEffect(() => {
    validateLicense();
  }, [licenseKey]);

  const validateLicense = async () => {
    try {
      const data = await licenseApi.validate(licenseKey);
      
      if (!data.valid) {
        setError(data.message || 'Invalid license key');
      } else {
        setLicenseData(data);
      }
    } catch (err: any) {
      setError('Failed to validate license key');
    } finally {
      setLoading(false);
    }
  };

  const handleDeviceDetect = (detectedDevice: DeviceType) => {
    setDevice(detectedDevice);
  };

  const handleStepComplete = (step: number) => {
    setCurrentStep(step + 1);
  };

  const handleActivated = (details: any) => {
    setSubscriptionDetails(details);
    setCurrentStep(3);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <Loader2 size={48} className="animate-spin text-empire-blue mx-auto mb-4" />
          <p className="text-gray-600">Validating your license key...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8 text-center">
          <div className="flex justify-center mb-4">
            <div className="bg-red-100 rounded-full p-3">
              <AlertCircle size={48} className="text-red-600" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Invalid License Key</h1>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={() => router.push('/setup')}
            className="bg-empire-blue hover:bg-empire-darkBlue text-white font-semibold py-3 px-6 rounded-lg transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      <DeviceDetector onDetect={handleDeviceDetect} />
      
      <div className="min-h-screen bg-gray-50 py-8 px-4">
        <div className="container mx-auto max-w-4xl">
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">
              EmpireBox Setup
            </h1>
            <p className="text-gray-600">
              License Key: <span className="font-mono font-semibold">{licenseKey}</span>
            </p>
          </div>

          {/* Progress Stepper */}
          <SetupProgress currentStep={currentStep} steps={SETUP_STEPS} />

          {/* Step Content */}
          <div className="bg-white rounded-lg shadow-lg p-8 mb-8">
            {/* Step 0: Download App */}
            {currentStep === 0 && (
              <div>
                <AppDownloadButtons device={device} />
                <div className="text-center mt-8">
                  <button
                    onClick={() => handleStepComplete(0)}
                    className="bg-empire-blue hover:bg-empire-darkBlue text-white font-semibold py-3 px-8 rounded-lg transition-colors"
                  >
                    I've Downloaded the App
                  </button>
                </div>
              </div>
            )}

            {/* Step 1: Wallet Setup */}
            {currentStep === 1 && (
              <div>
                <WalletSetupGuide />
                <div className="flex gap-4 mt-8">
                  <button
                    onClick={() => handleStepComplete(1)}
                    className="flex-1 bg-empire-blue hover:bg-empire-darkBlue text-white font-semibold py-3 px-8 rounded-lg transition-colors"
                  >
                    Wallet Created
                  </button>
                  <button
                    onClick={() => handleStepComplete(1)}
                    className="flex-1 bg-gray-300 hover:bg-gray-400 text-gray-700 font-semibold py-3 px-8 rounded-lg transition-colors"
                  >
                    Skip (No Crypto Phone)
                  </button>
                </div>
              </div>
            )}

            {/* Step 2: Activate License */}
            {currentStep === 2 && (
              <LicenseActivation
                licenseKey={licenseKey}
                onActivated={handleActivated}
              />
            )}

            {/* Step 3: Complete! */}
            {currentStep === 3 && (
              <div className="text-center space-y-6">
                <div className="flex justify-center mb-4">
                  <div className="bg-green-100 rounded-full p-4">
                    <PartyPopper size={64} className="text-green-600" />
                  </div>
                </div>
                <h2 className="text-3xl font-bold text-gray-900">
                  You're All Set! 🎉
                </h2>
                <p className="text-gray-600 text-lg">
                  Your EmpireBox is ready to start making you money!
                </p>

                <div className="bg-gradient-to-r from-empire-blue to-empire-lightBlue text-white rounded-lg p-6 my-8">
                  <h3 className="font-bold text-xl mb-4">Next Steps:</h3>
                  <ul className="text-left space-y-2 max-w-md mx-auto">
                    <li>✅ Open MarketForge app on your phone</li>
                    <li>✅ Complete the quick tutorial</li>
                    <li>✅ Connect your first marketplace</li>
                    <li>✅ Create your first listing</li>
                  </ul>
                </div>

                <div className="space-y-3">
                  <a
                    href="marketforge://app/home"
                    className="inline-flex items-center gap-2 bg-empire-orange hover:bg-orange-600 text-white font-bold py-4 px-8 rounded-lg transition-colors"
                  >
                    <span>Open MarketForge</span>
                    <ExternalLink size={20} />
                  </a>
                  
                  <div className="text-sm text-gray-600">
                    <a href="/tutorials" className="hover:underline">
                      Watch tutorial videos
                    </a>
                    {' · '}
                    <a href="/support" className="hover:underline">
                      Get support
                    </a>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Help Footer */}
          <div className="text-center text-sm text-gray-600">
            Need assistance? Contact us at{' '}
            <a href="mailto:support@empirebox.store" className="text-empire-blue hover:underline">
              support@empirebox.store
            </a>
          </div>
        </div>
      </div>
    </>
  );
}
