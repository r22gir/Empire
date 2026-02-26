'use client';
import { useState } from 'react';
import { TreatmentType, FabricGrade } from '@/lib/deskData';
import { Calculator, Scissors, DollarSign } from 'lucide-react';
import { StatsBar, TaskList } from './shared';
import QuoteBuilder from './estimating/QuoteBuilder';
import YardageCalculator from './estimating/YardageCalculator';
import PriceBreakdown from './estimating/PriceBreakdown';
import { useQuoteCalc } from './estimating/useQuoteCalc';

const fmt = (n: number) => '$' + n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export default function EstimatingDesk() {
  const [windowCount, setWindowCount] = useState(1);
  const [treatment, setTreatment] = useState<TreatmentType>('drapes');
  const [fabricGrade, setFabricGrade] = useState<FabricGrade>('Standard');
  const [laborRate, setLaborRate] = useState(65);
  const [windowWidth, setWindowWidth] = useState(72);
  const [windowHeight, setWindowHeight] = useState(84);
  const [fullness, setFullness] = useState(2.5);

  const calc = useQuoteCalc({ windowCount, treatment, fabricGrade, laborRate, windowWidth, windowHeight, fullness });

  return (
    <div className="flex flex-col h-full">
      <StatsBar items={[
        { label: 'Windows', value: String(windowCount), icon: Calculator, color: 'var(--gold)' },
        { label: 'Total Yardage', value: calc.totalYardage + ' yd', icon: Scissors, color: 'var(--purple)' },
        { label: 'Quote Total', value: fmt(calc.total), icon: DollarSign, color: '#22c55e' },
      ]} />
      <div className="flex-1 overflow-auto p-4 grid grid-cols-3 gap-4">
        <div className="col-span-1 flex flex-col gap-4">
          <QuoteBuilder
            windowCount={windowCount} setWindowCount={setWindowCount}
            treatment={treatment} setTreatment={setTreatment}
            fabricGrade={fabricGrade} setFabricGrade={setFabricGrade}
            laborRate={laborRate} setLaborRate={setLaborRate}
            windowWidth={windowWidth} setWindowWidth={setWindowWidth}
            windowHeight={windowHeight} setWindowHeight={setWindowHeight}
            fullness={fullness} setFullness={setFullness}
          />
        </div>
        <div className="col-span-1 flex flex-col gap-4">
          <YardageCalculator calc={calc} windowCount={windowCount} windowWidth={windowWidth} windowHeight={windowHeight} fullness={fullness} />
          <TaskList desk="estimating" compact />
        </div>
        <div className="col-span-1">
          <PriceBreakdown calc={calc} windowCount={windowCount} />
        </div>
      </div>
    </div>
  );
}
