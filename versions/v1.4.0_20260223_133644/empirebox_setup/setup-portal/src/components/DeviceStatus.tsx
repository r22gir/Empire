'use client';

import { useEffect, useState } from 'react';
import { Wifi, Bluetooth, Usb, Globe } from 'lucide-react';

interface DeviceInfo {
  serial: string;
  deviceId: string;
  firmware: string;
  online: boolean;
  discoveredVia: 'mdns' | 'ble' | 'usb' | 'qr' | 'unknown';
}

interface Props {
  deviceId: string;
}

export default function DeviceStatus({ deviceId }: Props) {
  const [device, setDevice] = useState<DeviceInfo | null>(null);

  useEffect(() => {
    // In production, poll the real device API
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/device/${deviceId}/status`);
        if (res.ok) {
          const data: DeviceInfo = await res.json();
          setDevice(data);
        }
      } catch {
        // Device not yet reachable
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [deviceId]);

  if (!device) {
    return (
      <div className="flex items-center gap-2 text-gray-500 text-sm">
        <div className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse" />
        Searching for device…
      </div>
    );
  }

  const icons: Record<DeviceInfo['discoveredVia'], React.ReactNode> = {
    mdns:    <Wifi size={14} />,
    ble:     <Bluetooth size={14} />,
    usb:     <Usb size={14} />,
    qr:      <Globe size={14} />,
    unknown: <Globe size={14} />,
  };

  return (
    <div className="flex items-center gap-3 p-3 rounded-lg bg-white/5 text-sm">
      <div className={`w-2 h-2 rounded-full ${device.online ? 'bg-green-500' : 'bg-red-500'}`} />
      <span className="text-white font-medium">EmpireBox-{device.serial}</span>
      <span className="text-gray-500">{device.firmware}</span>
      <span className="flex items-center gap-1 text-gray-400">
        {icons[device.discoveredVia]}
        {device.discoveredVia}
      </span>
    </div>
  );
}
