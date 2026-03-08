'use client';
import { Hammer, LayoutDashboard, Ruler, ListTodo, Package, Plus } from 'lucide-react';

const tabs = [
  { id: 'overview', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'designs', label: 'Designs', icon: Ruler },
  { id: 'jobs', label: 'Production', icon: ListTodo },
  { id: 'inventory', label: 'Inventory', icon: Package },
] as const;

type TabId = typeof tabs[number]['id'];

export default function TopNav({
  activeTab,
  setActiveTab,
  onNewDesign,
}: {
  activeTab: TabId;
  setActiveTab: (t: TabId) => void;
  onNewDesign: () => void;
}) {
  return (
    <nav className="bg-white border-b border-[#e5e0d8] sticky top-0 z-50">
      <div className="max-w-[1400px] mx-auto px-6 flex items-center justify-between h-14">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-[#c9a84c] flex items-center justify-center">
              <Hammer size={18} className="text-white" />
            </div>
            <span className="font-bold text-[15px]">CraftForge</span>
            <span className="text-[10px] text-[#aaa] font-medium ml-1">CNC & 3D Print</span>
          </div>

          <div className="flex items-center gap-1 ml-4">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  activeTab === tab.id
                    ? 'bg-[#fdf8eb] text-[#c9a84c] border border-[#c9a84c]/30'
                    : 'text-[#777] hover:text-[#1a1a1a] hover:bg-[#f5f3ef]'
                }`}
              >
                <tab.icon size={14} />
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={onNewDesign}
          className="flex items-center gap-1.5 px-4 py-2 bg-[#c9a84c] text-white text-xs font-semibold rounded-lg hover:bg-[#b8960c] transition-colors"
        >
          <Plus size={14} />
          New Design
        </button>
      </div>
    </nav>
  );
}
