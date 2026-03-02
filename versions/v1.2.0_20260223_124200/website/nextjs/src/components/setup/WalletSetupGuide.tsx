'use client';

import { Shield, Key, AlertTriangle, CheckCircle } from 'lucide-react';

export default function WalletSetupGuide() {
  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold mb-2">Create Your Solana Wallet</h2>
        <p className="text-gray-600">
          Your Solana Seeker phone has built-in Seed Vault for ultimate security
        </p>
      </div>

      <div className="space-y-4">
        {/* Step 1 */}
        <div className="bg-white border-2 border-gray-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <div className="bg-empire-blue text-white rounded-full w-8 h-8 flex items-center justify-center font-bold flex-shrink-0">
              1
            </div>
            <div>
              <h3 className="font-semibold mb-2">Open Seed Vault</h3>
              <p className="text-sm text-gray-600">
                Launch the Seed Vault app on your Solana Seeker phone. It's pre-installed and ready to use.
              </p>
            </div>
          </div>
        </div>

        {/* Step 2 */}
        <div className="bg-white border-2 border-gray-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <div className="bg-empire-blue text-white rounded-full w-8 h-8 flex items-center justify-center font-bold flex-shrink-0">
              2
            </div>
            <div>
              <h3 className="font-semibold mb-2">Create New Wallet</h3>
              <p className="text-sm text-gray-600">
                Tap "Create New Wallet" and follow the on-screen instructions. Your seed phrase will be generated using the phone's secure hardware.
              </p>
            </div>
          </div>
        </div>

        {/* Step 3 - Important Warning */}
        <div className="bg-red-50 border-2 border-red-300 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="text-red-600 flex-shrink-0" size={24} />
            <div>
              <h3 className="font-semibold mb-2 text-red-900">Write Down Your Seed Phrase!</h3>
              <p className="text-sm text-red-800 mb-2">
                <strong>CRITICAL:</strong> Write down your 12-word seed phrase on paper and store it safely. This is the ONLY way to recover your wallet if you lose your phone.
              </p>
              <ul className="text-xs text-red-700 space-y-1 ml-4 list-disc">
                <li>Never share your seed phrase with anyone</li>
                <li>Never store it digitally (screenshots, cloud, etc.)</li>
                <li>Keep it in a secure location (safe, safety deposit box)</li>
                <li>If someone gets your seed phrase, they can steal all your funds</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Step 4 */}
        <div className="bg-white border-2 border-gray-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <div className="bg-empire-blue text-white rounded-full w-8 h-8 flex items-center justify-center font-bold flex-shrink-0">
              3
            </div>
            <div>
              <h3 className="font-semibold mb-2">Verify Your Seed Phrase</h3>
              <p className="text-sm text-gray-600">
                You'll be asked to confirm your seed phrase by selecting words in the correct order. This ensures you wrote it down correctly.
              </p>
            </div>
          </div>
        </div>

        {/* Step 5 */}
        <div className="bg-green-50 border-2 border-green-300 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <CheckCircle className="text-green-600 flex-shrink-0" size={24} />
            <div>
              <h3 className="font-semibold mb-2 text-green-900">Wallet Created!</h3>
              <p className="text-sm text-green-800">
                Your Solana wallet is now secured in Seed Vault. Your private keys never leave the secure hardware chip.
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mt-6">
        <div className="flex items-start gap-3">
          <Shield className="text-blue-600 flex-shrink-0" size={20} />
          <div className="text-sm">
            <p className="font-semibold text-blue-900 mb-1">Why Seed Vault is Secure:</p>
            <p className="text-blue-800">
              Unlike software wallets, Seed Vault uses dedicated hardware to store your private keys. This means even if your phone is compromised, your crypto remains safe.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
