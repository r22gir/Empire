import { useMemo } from 'react';
import { TreatmentType, FabricGrade, FABRIC_GRADES, BASE_PRICES } from '@/lib/deskData';

export interface QuoteCalc {
  yardagePerWindow: number;
  totalYardage: number;
  panelsNeeded: number;
  wasteYardage: number;
  materialsTotal: number;
  laborTotal: number;
  hardwareTotal: number;
  subtotal: number;
  tax: number;
  total: number;
}

const TAX_RATE = 0.0825;

export function useQuoteCalc(opts: {
  windowCount: number;
  treatment: TreatmentType;
  fabricGrade: FabricGrade;
  laborRate: number;
  windowWidth: number;
  windowHeight: number;
  fullness: number;
}): QuoteCalc {
  const { windowCount, treatment, fabricGrade, laborRate, windowWidth, windowHeight, fullness } = opts;

  return useMemo(() => {
    const base = BASE_PRICES[treatment];
    const gradeInfo = FABRIC_GRADES.find(g => g.grade === fabricGrade)!;

    const widthInches = windowWidth * fullness;
    const heightInches = windowHeight + 16;
    const panelWidthYds = widthInches / 54;
    const panelsNeeded = Math.ceil(panelWidthYds);
    const yardagePerWindow = (heightInches / 36) * panelsNeeded;
    const wastePercent = 0.15;
    const totalYardage = yardagePerWindow * windowCount * (1 + wastePercent);

    const materialPerWindow = base.material * gradeInfo.multiplier;
    const laborPerWindow = base.labor * (laborRate / 65);
    const hardwarePerWindow = base.hardware;

    const materialsTotal = materialPerWindow * windowCount;
    const laborTotal = laborPerWindow * windowCount;
    const hardwareTotal = hardwarePerWindow * windowCount;
    const subtotal = materialsTotal + laborTotal + hardwareTotal;
    const tax = subtotal * TAX_RATE;
    const total = subtotal + tax;

    return {
      yardagePerWindow: Math.ceil(yardagePerWindow * 10) / 10,
      totalYardage: Math.ceil(totalYardage * 10) / 10,
      panelsNeeded,
      wasteYardage: Math.ceil(yardagePerWindow * windowCount * wastePercent * 10) / 10,
      materialsTotal, laborTotal, hardwareTotal, subtotal, tax, total,
    };
  }, [windowCount, treatment, fabricGrade, laborRate, windowWidth, windowHeight, fullness]);
}
