'use client';

import { Check } from 'lucide-react';

interface Step {
  id: number;
  title: string;
  description: string;
}

interface SetupProgressProps {
  currentStep: number;
  steps: Step[];
}

export default function SetupProgress({ currentStep, steps }: SetupProgressProps) {
  return (
    <div className="w-full max-w-3xl mx-auto mb-8">
      <div className="flex items-center justify-between">
        {steps.map((step, index) => (
          <div key={step.id} className="flex items-center flex-1">
            {/* Step Circle */}
            <div className="flex flex-col items-center">
              <div
                className={`w-12 h-12 rounded-full flex items-center justify-center font-bold text-lg transition-colors ${
                  index < currentStep
                    ? 'bg-green-500 text-white'
                    : index === currentStep
                    ? 'bg-empire-blue text-white'
                    : 'bg-gray-200 text-gray-500'
                }`}
              >
                {index < currentStep ? <Check size={24} /> : step.id}
              </div>
              <p
                className={`mt-2 text-sm font-medium text-center ${
                  index <= currentStep ? 'text-gray-900' : 'text-gray-400'
                }`}
              >
                {step.title}
              </p>
            </div>

            {/* Connecting Line */}
            {index < steps.length - 1 && (
              <div
                className={`flex-1 h-1 mx-2 transition-colors ${
                  index < currentStep ? 'bg-green-500' : 'bg-gray-200'
                }`}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
