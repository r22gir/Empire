// Maps product types to their SVG diagram file paths
export const DIAGRAM_MAP: Record<string, { svg: string; label: string; category: string }> = {
  // Furniture
  'sofa_3cushion': { svg: '/diagrams/furniture/sofa_3cushion.svg', label: '3-Cushion Sofa', category: 'upholstery' },
  'sofa_chesterfield': { svg: '/diagrams/furniture/sofa_chesterfield.svg', label: 'Chesterfield Sofa', category: 'upholstery' },
  'sofa_tuxedo': { svg: '/diagrams/furniture/sofa_tuxedo.svg', label: 'Tuxedo Sofa', category: 'upholstery' },
  'chair_wingback': { svg: '/diagrams/furniture/chair_wingback.svg', label: 'Wingback Chair', category: 'upholstery' },
  'chair_club': { svg: '/diagrams/furniture/chair_club.svg', label: 'Club Chair', category: 'upholstery' },
  'chair_dining': { svg: '/diagrams/furniture/chair_dining.svg', label: 'Dining Chair', category: 'upholstery' },
  'bench_straight': { svg: '/diagrams/furniture/bench_straight.svg', label: 'Straight Bench', category: 'upholstery' },
  'bench_banquette': { svg: '/diagrams/furniture/bench_banquette.svg', label: 'Banquette/Booth', category: 'upholstery' },
  'ottoman_rectangular': { svg: '/diagrams/furniture/ottoman_rectangular.svg', label: 'Ottoman', category: 'upholstery' },
  'headboard_tufted': { svg: '/diagrams/furniture/headboard_tufted.svg', label: 'Tufted Headboard', category: 'upholstery' },
  // Wall Panels
  'wall_panel_flat': { svg: '/diagrams/wall-panels/wall_panel_flat.svg', label: 'Flat Wall Panel', category: 'upholstery' },
  'wall_panel_diamond_tufted': { svg: '/diagrams/wall-panels/wall_panel_diamond_tufted.svg', label: 'Diamond Tufted Panel', category: 'upholstery' },
  'wall_panel_channel': { svg: '/diagrams/wall-panels/wall_panel_channel.svg', label: 'Channel Wall Panel', category: 'upholstery' },
  // Window Treatments
  'drapery_pinch_pleat': { svg: '/diagrams/window-treatments/drapery_pinch_pleat.svg', label: 'Pinch Pleat Drapery', category: 'drapery' },
  'drapery_ripplefold': { svg: '/diagrams/window-treatments/drapery_ripplefold.svg', label: 'Ripplefold Drapery', category: 'drapery' },
  'drapery_grommet': { svg: '/diagrams/window-treatments/drapery_grommet.svg', label: 'Grommet Drapery', category: 'drapery' },
  'roman_flat': { svg: '/diagrams/window-treatments/roman_flat.svg', label: 'Flat Roman Shade', category: 'drapery' },
  'roman_hobbled': { svg: '/diagrams/window-treatments/roman_hobbled.svg', label: 'Hobbled Roman Shade', category: 'drapery' },
  'roman_balloon': { svg: '/diagrams/window-treatments/roman_balloon.svg', label: 'Balloon Shade', category: 'drapery' },
  'valance_swag_jabot': { svg: '/diagrams/window-treatments/valance_swag_jabot.svg', label: 'Swag & Jabot', category: 'drapery' },
  'valance_box_pleat': { svg: '/diagrams/window-treatments/valance_box_pleat.svg', label: 'Box Pleat Valance', category: 'drapery' },
  'cornice_straight': { svg: '/diagrams/window-treatments/cornice_straight.svg', label: 'Straight Cornice', category: 'drapery' },
  'cornice_serpentine': { svg: '/diagrams/window-treatments/cornice_serpentine.svg', label: 'Serpentine Cornice', category: 'drapery' },
  // Cushions
  'cushion_box_edge': { svg: '/diagrams/cushions/cushion_box_edge.svg', label: 'Box Edge Cushion', category: 'upholstery' },
  'cushion_bolster': { svg: '/diagrams/cushions/cushion_bolster.svg', label: 'Bolster Cushion', category: 'upholstery' },
};

// Category filters for the catalog
export const CATALOG_CATEGORIES = [
  { id: 'all', label: 'All Items' },
  { id: 'upholstery', label: 'Furniture & Upholstery' },
  { id: 'drapery', label: 'Window Treatments' },
  { id: 'wall_panel', label: 'Wall Panels' },
  { id: 'cushion', label: 'Cushions' },
];

// Find best diagram match for an AI-detected item type
export function findDiagramMatch(aiLabel: string): string | null {
  const label = aiLabel.toLowerCase();
  // Direct matches
  for (const [key, val] of Object.entries(DIAGRAM_MAP)) {
    if (label.includes(key.replace(/_/g, ' '))) return key;
    if (label.includes(val.label.toLowerCase())) return key;
  }
  // Fuzzy matches
  if (label.includes('sofa') || label.includes('couch')) return 'sofa_3cushion';
  if (label.includes('wingback')) return 'chair_wingback';
  if (label.includes('club')) return 'chair_club';
  if (label.includes('dining') && label.includes('chair')) return 'chair_dining';
  if (label.includes('chair')) return 'chair_club';
  if (label.includes('banquette') || label.includes('booth')) return 'bench_banquette';
  if (label.includes('bench')) return 'bench_straight';
  if (label.includes('ottoman')) return 'ottoman_rectangular';
  if (label.includes('headboard')) return 'headboard_tufted';
  if (label.includes('wall panel') || label.includes('wall pad')) return 'wall_panel_flat';
  if (label.includes('pinch')) return 'drapery_pinch_pleat';
  if (label.includes('ripple')) return 'drapery_ripplefold';
  if (label.includes('grommet')) return 'drapery_grommet';
  if (label.includes('roman') && label.includes('hobble')) return 'roman_hobbled';
  if (label.includes('roman') && label.includes('balloon')) return 'roman_balloon';
  if (label.includes('roman')) return 'roman_flat';
  if (label.includes('swag') || label.includes('jabot')) return 'valance_swag_jabot';
  if (label.includes('valance')) return 'valance_box_pleat';
  if (label.includes('serpentine')) return 'cornice_serpentine';
  if (label.includes('cornice')) return 'cornice_straight';
  if (label.includes('bolster')) return 'cushion_bolster';
  if (label.includes('cushion')) return 'cushion_box_edge';
  if (label.includes('drapery') || label.includes('drape') || label.includes('curtain')) return 'drapery_pinch_pleat';
  return null;
}
