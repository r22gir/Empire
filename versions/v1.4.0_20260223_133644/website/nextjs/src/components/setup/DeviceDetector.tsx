'use client';

import { useEffect, useState } from 'react';

export type DeviceType = 'android' | 'ios' | 'desktop';

interface DeviceDetectorProps {
  onDetect: (device: DeviceType) => void;
}

export default function DeviceDetector({ onDetect }: DeviceDetectorProps) {
  const [device, setDevice] = useState<DeviceType | null>(null);

  useEffect(() => {
    const userAgent = navigator.userAgent.toLowerCase();
    let detectedDevice: DeviceType;

    if (/android/.test(userAgent)) {
      detectedDevice = 'android';
    } else if (/iphone|ipad|ipod/.test(userAgent)) {
      detectedDevice = 'ios';
    } else {
      detectedDevice = 'desktop';
    }

    setDevice(detectedDevice);
    onDetect(detectedDevice);
  }, [onDetect]);

  return null; // This component doesn't render anything
}
