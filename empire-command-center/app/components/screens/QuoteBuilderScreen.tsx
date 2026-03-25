'use client';
import { useState, useRef, useCallback, useEffect } from 'react';
import { API } from '../../lib/api';
import {
  ArrowLeft, ArrowRight, User, Camera, Layers, Settings, FileText,
  Plus, Trash2, Upload, X, Check, Loader2, ChevronDown, ChevronUp, GripVertical, Search,
  Eye, Download, Sparkles, ImageIcon, FolderOpen, CheckSquare, Edit3, Box, Ruler, CheckCircle, BookOpen, Printer
} from 'lucide-react';
import MeasurementDiagram from '../business/quotes/MeasurementDiagram';
import dynamic from 'next/dynamic';
import { DiagramCatalog, DiagramViewer, findDiagramMatch, DIAGRAM_MAP } from '../business/catalog';

const CushionBuilder = dynamic(() => import('../business/upholstery/CushionBuilder'), { ssr: false });
const CustomShapeBuilder = dynamic(() => import('../tools/CustomShapeBuilder'), { ssr: false });
const DraperyHardwareModule = dynamic(() => import('../business/drapery/DraperyHardwareModule'), { ssr: false });
const ThreeViewer = dynamic(() => import('../business/vision/ThreeViewer'), { ssr: false });
import PanelConfigurator, { DEFAULT_PANEL_CONFIG, type PanelConfig } from '../tools/PanelConfigurator';
import FabricSelector, { type Fabric } from '../FabricSelector';
import YardageCalculator from '../YardageCalculator';

interface CustomerInfo {
  name: string;
  email: string;
  phone: string;
  address: string;
}

interface PhotoFile {
  file?: File;
  preview: string;
  uploadedFilename?: string;
  serverUrl?: string;
  originalName?: string;
  fromIntake?: boolean;
  assignedRoomId?: string;
  assignedItemId?: string;
}

interface AnalysisItem {
  type: string;
  description: string;
  width?: string;
  height?: string;
  depth?: string;
  condition?: string;
  checked?: boolean;
}

interface RoomItem {
  id: string;
  type: string;
  width: string;
  height: string;
  depth: string;
  quantity: number;
  notes: string;
  panelConfig?: PanelConfig;
  _uploadPath?: string;
  _3dUrl?: string;
  _3dFilename?: string;
  // Fabric selections
  fabric?: Fabric | null;
  fabricYards?: number;
  fabricYardsOverride?: number | null;
  backingFabric?: Fabric | null;
  backingYards?: number;
  backingYardsOverride?: number | null;
}

interface Scan3DFile {
  url: string;
  filename: string;
  originalName: string;
  assignedRoomId?: string;
  assignedItemId?: string;
}

interface Room {
  id: string;
  name: string;
  items: RoomItem[];
}

type ItemCategory = 'upholstery' | 'drapery';

interface QuoteOptions {
  fabricGrade: 'A' | 'B' | 'C' | 'D';
  // Drapery options
  liningType: string;  // unlined, standard_poly_cotton, blackout, interlining_bump, interlining_domette, interlining_flannel, thermal, sheer, privacy
  pleatType: string;   // matches drapery subcategory
  fullness: string;    // 2x, 2.5x, 3x, custom
  hardwareType: string; // traverse_rod, decorative_rod_wood, motorized_somfy, etc.
  finialStyle: string; // ball, spear, fleur_de_lis, crystal, etc.
  leadingEdge: string; // plain, contrast_banding, gimp, braid, fringe, tassel_fringe, beaded, brush_fringe
  bottomHem: string;   // double_fold_4in, double_fold_6in, double_fold_8in, weighted, chain_weighted, horsehair
  returnSize: string;  // standard_3_5in, extended_6in, extended_8in, custom
  stacking: string;    // left, right, split, one_way_left, one_way_right
  tieback: string;     // none, fabric, rope, tassel, medallion, magnetic, holdback
  contrastPiping: boolean;
  patternMatch: boolean;
  // Roman shade options
  liftSystem: string;  // cord_lock, continuous_cord_loop, cordless, motorized_somfy, motorized_lutron, top_down_bottom_up, day_night_dual
  valanceOption: string; // self_valance, separate_valance, no_valance
  // Cornice options
  corniceConstruction: string; // foam_core, wood_frame, padded, upholstered
  corniceFace: string;  // flat_fabric, tufted, nailhead_outline, contrast_welt, double_welt, gimp
  dustCover: string;    // none, self_fabric, lining
  // Upholstery options
  foamType: string;     // high_density, medium_density, down_wrap, down_blend, spring_down, memory_foam, latex, reuse
  foamThickness: number; // 1-6 inches
  tufting: string;      // none, diamond, biscuit, channel_vertical, channel_horizontal, button, blind_button, deep_button
  welting: string;      // self_welt, contrast_welt, double_welt, cord, micro_welt, none
  nailheadFinish: string; // none, standard, french_natural, antique_brass, nickel, pewter, black, gunmetal, gold
  nailheadSpacing: string; // standard, close, every_other, custom_pattern
  skirtStyle: string;   // none, kick_pleat, box_pleat, gathered, tailored, bullion_fringe, waterfall
  springs: string;      // eight_way_hand_tied, sinuous_zigzag, no_sag, pocket_coil
  armStyle: string;     // track, english, rolled, flared, slope, pad, recessed
  backStyle: string;    // tight, loose_cushion, tufted, channeled, pillow_back
  legStyle: string;     // exposed_wood, exposed_metal, exposed_acrylic, skirted, bun_feet, turned, tapered, cabriole
  // Wall panel options
  panelMounting: string; // french_cleat, z_clip, velcro, direct_mount
  // Bedding options
  bedSkirtStyle: string; // box_pleat, kick_pleat, gathered, tailored, split_corner
  shamSize: string;      // standard, euro, king, boudoir, neckroll
  quiltingPattern: string; // diamond, channel, vermicelli, stipple, custom
  monogram: boolean;
  // Shared
  rushOrder: boolean;
  delivery: boolean;
  installationIncluded: boolean;
}

const UPHOLSTERY_GROUPS = [
  { label: 'Sofas & Loveseats', items: [
    'sofa_3cushion', 'sofa_2cushion', 'sofa_chesterfield', 'sofa_tuxedo', 'sofa_camelback',
    'sofa_lawson', 'sofa_english_arm', 'sofa_track_arm', 'sofa_mid_century',
    'loveseat', 'settee', 'sectional', 'sectional_l', 'sectional_u',
  ]},
  { label: 'Chairs', items: [
    'chair_wingback', 'chair_club', 'chair_barrel', 'chair_accent', 'chair_slipper',
    'chair_bergere', 'chair_fauteuil', 'chair_parsons',
    'dining_chair_seat', 'dining_chair_full', 'dining_chair_arm',
    'bar_stool', 'chaise', 'daybed',
  ]},
  { label: 'Ottomans & Benches', items: [
    'ottoman_round', 'ottoman_square', 'ottoman_rectangular', 'ottoman_tufted_cube', 'ottoman_storage',
    'bench_straight', 'bench_l_shaped', 'bench_u_booth', 'bench_curved_banquette',
    'bench_semicircle', 'bench_mixed', 'bench_window_seat', 'bench_storage', 'banquette',
  ]},
  { label: 'Headboards', items: [
    'headboard_rectangular', 'headboard_arched', 'headboard_wingback', 'headboard_tufted',
    'headboard_camelback', 'headboard_custom',
  ]},
  { label: 'Wall Panels', items: [
    'wall_panel_flat', 'wall_panel_tufted_diamond', 'wall_panel_tufted_biscuit',
    'wall_panel_channel_vertical', 'wall_panel_channel_horizontal',
    'wall_panel_padded', 'wall_panel_wrapped', 'wall_panel_acoustic', 'wall_panel_cornice_topped',
  ]},
  { label: 'Cushions', items: [
    'cushion_seat', 'cushion_back', 'cushion_throw', 'cushion_bolster',
    'cushion_box_edge', 'cushion_waterfall', 'cushion_t_cushion', 'cushion_bullnose', 'cushion_knife_edge',
  ]},
  { label: 'Bedding', items: [
    'duvet_cover', 'coverlet', 'quilt', 'bed_skirt', 'pillow_sham',
    'decorative_pillow', 'bolster', 'bed_scarf',
  ]},
  { label: 'Table Linens', items: [
    'tablecloth', 'table_runner', 'placemat', 'napkin', 'table_skirt',
  ]},
];

const UPHOLSTERY_TYPES = UPHOLSTERY_GROUPS.flatMap(g => g.items);

const DRAPERY_GROUPS = [
  { label: 'Drapery', items: [
    'drapery_pinch_pleat', 'drapery_french_pleat', 'drapery_euro_pleat',
    'drapery_cartridge', 'drapery_box_pleat', 'drapery_inverted_box',
    'drapery_goblet', 'drapery_butterfly', 'drapery_ripplefold',
    'drapery_rod_pocket', 'drapery_tab_top', 'drapery_grommet',
    'drapery_pencil_pleat', 'drapery_smocked', 'drapery_fan_pleat',
    'drapery',
  ]},
  { label: 'Roman Shades', items: [
    'roman_flat', 'roman_hobbled', 'roman_european_relaxed', 'roman_balloon',
    'roman_austrian', 'roman_london', 'roman_cascade', 'roman_waterfall', 'roman_tulip',
    'roman_shade',
  ]},
  { label: 'Valances', items: [
    'valance_box_pleat', 'valance_inverted_box', 'valance_kingston', 'valance_cambridge',
    'valance_scalloped', 'valance_arched', 'valance_serpentine', 'valance_balloon',
    'valance_austrian', 'valance_london', 'valance_flat_board', 'valance_shaped',
    'valance_pleated', 'valance_gathered', 'valance_swag_jabot', 'valance_cascades',
    'valance_empire', 'valance_tab', 'valance_rod_pocket', 'valance_cornice_fabric',
    'valance',
  ]},
  { label: 'Cornices', items: [
    'cornice_straight', 'cornice_arched', 'cornice_scalloped', 'cornice_serpentine',
    'cornice_double_serpentine', 'cornice_pagoda', 'cornice_stepped', 'cornice_custom',
    'cornice',
  ]},
  { label: 'Sheers', items: ['sheer'] },
];

const DRAPERY_TYPES = DRAPERY_GROUPS.flatMap(g => g.items);

const ITEM_TYPES = [...UPHOLSTERY_TYPES, ...DRAPERY_TYPES];

// Map bench types in Quote Builder → Custom Shape Builder presets
const BENCH_SHAPE_MAP: Record<string, string> = {
  bench_straight: 'straight_bench',
  bench_l_shaped: 'l_bench',
  bench_u_booth: 'u_booth',
  bench_curved_banquette: 'curved_banquette',
  bench_semicircle: 'semicircle',
  bench_mixed: 'l_bench',  // closest available preset — mixed shapes use L-bench as starting point
  banquette: 'curved_banquette',
};

function isBenchType(type: string): boolean {
  return type in BENCH_SHAPE_MAP;
}

// Human-friendly display names for item types that don't format well from slug
const DISPLAY_NAMES: Record<string, string> = {
  sofa_3cushion: 'Sofa 3-Cushion',
  sofa_2cushion: 'Sofa 2-Cushion',
  sectional_l: 'Sectional (L-Shape)',
  sectional_u: 'Sectional (U-Shape)',
  bench_straight: 'Restaurant Bench (Straight)',
  bench_l_shaped: 'Restaurant Bench (L-Shape)',
  bench_u_booth: 'Restaurant Bench (U-Booth)',
  bench_curved_banquette: 'Curved Banquette',
  bench_semicircle: 'Semicircle Bench',
  bench_mixed: 'Custom Bench (Mixed)',
  bench_window_seat: 'Window Seat',
  bench_storage: 'Storage Bench',
  dining_chair_seat: 'Dining Chair (Seat Only)',
  dining_chair_full: 'Dining Chair (Full)',
  dining_chair_arm: 'Dining Chair (with Arms)',
  ottoman_tufted_cube: 'Tufted Cube Ottoman',
  headboard_custom: 'Headboard (Custom Shape)',
  wall_panel_tufted_diamond: 'Wall Panel — Diamond Tuft',
  wall_panel_tufted_biscuit: 'Wall Panel — Biscuit Tuft',
  wall_panel_channel_vertical: 'Wall Panel — Vertical Channel',
  wall_panel_channel_horizontal: 'Wall Panel — Horizontal Channel',
  wall_panel_cornice_topped: 'Wall Panel — Cornice Topped',
  cushion_box_edge: 'Cushion — Box Edge',
  cushion_t_cushion: 'T-Cushion',
  cushion_knife_edge: 'Cushion — Knife Edge',
  drapery_pinch_pleat: 'Drapery — Pinch Pleat',
  drapery_french_pleat: 'Drapery — French Pleat',
  drapery_euro_pleat: 'Drapery — Euro Pleat',
  drapery_inverted_box: 'Drapery — Inverted Box Pleat',
  drapery_ripplefold: 'Drapery — Ripplefold',
  drapery_rod_pocket: 'Drapery — Rod Pocket',
  drapery_tab_top: 'Drapery — Tab Top',
  drapery_pencil_pleat: 'Drapery — Pencil Pleat',
  drapery_fan_pleat: 'Drapery — Fan Pleat',
  roman_european_relaxed: 'Roman Shade — European Relaxed',
  cornice_double_serpentine: 'Cornice — Double Serpentine',
};

/** Format item type for display — use DISPLAY_NAMES if available, else auto-format */
function formatItemType(t: string): string {
  return DISPLAY_NAMES[t] || t.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function getItemCategory(type: string): ItemCategory {
  if (DRAPERY_TYPES.includes(type)) return 'drapery';
  if (type.startsWith('drapery') || type.startsWith('roman') || type.startsWith('valance') || type.startsWith('cornice') || type.startsWith('sheer')) return 'drapery';
  return 'upholstery';
}

// Map AI-detected furniture names to ITEM_TYPES keys
function mapFurnitureType(aiType: string): string {
  const t = (aiType || '').toLowerCase();
  // Specific furniture matches
  if (t.includes('chesterfield')) return 'sofa_chesterfield';
  if (t.includes('tuxedo')) return 'sofa_tuxedo';
  if (t.includes('camelback') && t.includes('sofa')) return 'sofa_camelback';
  if (t.includes('lawson')) return 'sofa_lawson';
  if (t.includes('mid century') || t.includes('mid-century')) return 'sofa_mid_century';
  if (t.includes('track arm')) return 'sofa_track_arm';
  if (t.includes('english arm')) return 'sofa_english_arm';
  if (t.includes('sectional') && t.includes('u')) return 'sectional_u';
  if (t.includes('sectional') && t.includes('l')) return 'sectional_l';
  if (t.includes('sectional')) return 'sectional';
  if (t.includes('settee')) return 'settee';
  if (t.includes('loveseat') || t.includes('love seat')) return 'loveseat';
  if (t.includes('wingback') && t.includes('chair')) return 'chair_wingback';
  if (t.includes('wingback') && t.includes('head')) return 'headboard_wingback';
  if (t.includes('club chair')) return 'chair_club';
  if (t.includes('barrel chair')) return 'chair_barrel';
  if (t.includes('slipper')) return 'chair_slipper';
  if (t.includes('bergere')) return 'chair_bergere';
  if (t.includes('fauteuil')) return 'chair_fauteuil';
  if (t.includes('parsons')) return 'chair_parsons';
  if (t.includes('bar stool')) return 'bar_stool';
  if (t.includes('chaise')) return 'chaise';
  if (t.includes('daybed')) return 'daybed';
  if (t.includes('dining chair') && t.includes('arm')) return 'dining_chair_arm';
  if (t.includes('dining chair') && t.includes('seat')) return 'dining_chair_seat';
  if (t.includes('dining chair')) return 'dining_chair_full';
  if (t.includes('accent chair') || t.includes('arm chair') || t.includes('armchair')) return 'chair_accent';
  if (t.includes('banquette') || t.includes('booth')) return 'bench_u_booth';
  if (t.includes('window seat')) return 'bench_window_seat';
  if (t.includes('bench') && t.includes('curved')) return 'bench_curved_banquette';
  if (t.includes('bench') && t.includes('l')) return 'bench_l_shaped';
  if (t.includes('bench') && t.includes('storage')) return 'bench_storage';
  if (t.includes('bench')) return 'bench_straight';
  if (t.includes('ottoman') && t.includes('round')) return 'ottoman_round';
  if (t.includes('ottoman') && t.includes('tufted')) return 'ottoman_tufted_cube';
  if (t.includes('ottoman') && t.includes('storage')) return 'ottoman_storage';
  if (t.includes('ottoman')) return 'ottoman_rectangular';
  if (t.includes('headboard') && t.includes('tufted')) return 'headboard_tufted';
  if (t.includes('headboard') && t.includes('arch')) return 'headboard_arched';
  if (t.includes('headboard')) return 'headboard_rectangular';
  if (t.includes('wall panel') && t.includes('diamond')) return 'wall_panel_tufted_diamond';
  if (t.includes('wall panel') && t.includes('channel')) return 'wall_panel_channel_vertical';
  if (t.includes('wall panel') && t.includes('tufted')) return 'wall_panel_tufted_biscuit';
  if (t.includes('wall panel') && t.includes('acoustic')) return 'wall_panel_acoustic';
  if (t.includes('wall panel')) return 'wall_panel_flat';
  if (t.includes('sofa') || t.includes('couch')) return 'sofa_3cushion';
  if (t.includes('bolster')) return 'cushion_bolster';
  if (t.includes('cushion') && t.includes('back')) return 'cushion_back';
  if (t.includes('cushion') && t.includes('box')) return 'cushion_box_edge';
  if (t.includes('cushion') || t.includes('seat pad')) return 'cushion_seat';
  if (t.includes('pillow') || t.includes('throw')) return 'cushion_throw';
  if (t.includes('duvet')) return 'duvet_cover';
  if (t.includes('coverlet')) return 'coverlet';
  if (t.includes('bed skirt') || t.includes('bedskirt')) return 'bed_skirt';
  if (t.includes('sham')) return 'pillow_sham';
  if (t.includes('chair')) return 'chair_accent';
  // Window treatments
  if (t.includes('pinch pleat')) return 'drapery_pinch_pleat';
  if (t.includes('french pleat')) return 'drapery_french_pleat';
  if (t.includes('euro pleat')) return 'drapery_euro_pleat';
  if (t.includes('ripple')) return 'drapery_ripplefold';
  if (t.includes('grommet')) return 'drapery_grommet';
  if (t.includes('rod pocket')) return 'drapery_rod_pocket';
  if (t.includes('goblet')) return 'drapery_goblet';
  if (t.includes('drapery') || t.includes('drape') || t.includes('curtain')) return 'drapery';
  if (t.includes('roman') && t.includes('hobble')) return 'roman_hobbled';
  if (t.includes('roman') && t.includes('balloon')) return 'roman_balloon';
  if (t.includes('roman') && t.includes('london')) return 'roman_london';
  if (t.includes('roman') && t.includes('austrian')) return 'roman_austrian';
  if (t.includes('roman shade') || t.includes('roman')) return 'roman_flat';
  if (t.includes('swag') && t.includes('jabot')) return 'valance_swag_jabot';
  if (t.includes('valance')) return 'valance';
  if (t.includes('serpentine') && t.includes('cornice')) return 'cornice_serpentine';
  if (t.includes('cornice')) return 'cornice_straight';
  if (t.includes('sheer')) return 'sheer';
  if (ITEM_TYPES.includes(t)) return t;
  return 'sofa_3cushion'; // safe default
}

type QuoteInputMethod = 'photos' | '3dscan' | 'manual' | 'intake';

type ManualItemType = string;

interface ManualItemDef { key: ManualItemType; label: string; icon: string }
interface ManualItemGroup { group: string; color: string; items: ManualItemDef[] }

const MANUAL_ITEM_GROUPS: ManualItemGroup[] = [
  {
    group: 'Drapery', color: '#2563eb',
    items: [
      { key: 'drapery_pinch_pleat', label: 'Pinch Pleat', icon: '🪟' },
      { key: 'drapery_french_pleat', label: 'French Pleat', icon: '🪟' },
      { key: 'drapery_euro_pleat', label: 'Euro Pleat', icon: '🪟' },
      { key: 'drapery_goblet', label: 'Goblet', icon: '🪟' },
      { key: 'drapery_cartridge', label: 'Cartridge', icon: '🪟' },
      { key: 'drapery_ripplefold', label: 'Ripplefold', icon: '🪟' },
      { key: 'drapery_rod_pocket', label: 'Rod Pocket', icon: '🪟' },
      { key: 'drapery_grommet', label: 'Grommet', icon: '🪟' },
      { key: 'drapery_tab_top', label: 'Tab Top', icon: '🪟' },
      { key: 'drapery_box_pleat', label: 'Box Pleat', icon: '🪟' },
      { key: 'drapery_inverted_box', label: 'Inverted Box', icon: '🪟' },
      { key: 'drapery_butterfly', label: 'Butterfly', icon: '🪟' },
      { key: 'drapery_pencil_pleat', label: 'Pencil Pleat', icon: '🪟' },
      { key: 'drapery_smocked', label: 'Smocked', icon: '🪟' },
      { key: 'sheer', label: 'Sheer', icon: '🪟' },
    ],
  },
  {
    group: 'Roman Shades', color: '#0891b2',
    items: [
      { key: 'roman_flat', label: 'Flat Fold', icon: '🪟' },
      { key: 'roman_hobbled', label: 'Hobbled/Teardrop', icon: '🪟' },
      { key: 'roman_european_relaxed', label: 'European Relaxed', icon: '🪟' },
      { key: 'roman_balloon', label: 'Balloon', icon: '🪟' },
      { key: 'roman_austrian', label: 'Austrian', icon: '🪟' },
      { key: 'roman_london', label: 'London', icon: '🪟' },
      { key: 'roman_cascade', label: 'Cascade', icon: '🪟' },
      { key: 'roman_waterfall', label: 'Waterfall', icon: '🪟' },
      { key: 'roman_tulip', label: 'Tulip', icon: '🪟' },
    ],
  },
  {
    group: 'Valances & Cornices', color: '#7c3aed',
    items: [
      { key: 'valance_box_pleat', label: 'Box Pleat Valance', icon: '🎪' },
      { key: 'valance_kingston', label: 'Kingston', icon: '🎪' },
      { key: 'valance_scalloped', label: 'Scalloped', icon: '🎪' },
      { key: 'valance_serpentine', label: 'Serpentine', icon: '🎪' },
      { key: 'valance_swag_jabot', label: 'Swag & Jabot', icon: '🎪' },
      { key: 'valance_balloon', label: 'Balloon Valance', icon: '🎪' },
      { key: 'valance_empire', label: 'Empire', icon: '🎪' },
      { key: 'cornice_straight', label: 'Straight Cornice', icon: '📐' },
      { key: 'cornice_arched', label: 'Arched Cornice', icon: '📐' },
      { key: 'cornice_serpentine', label: 'Serpentine Cornice', icon: '📐' },
      { key: 'cornice_pagoda', label: 'Pagoda Cornice', icon: '📐' },
    ],
  },
  {
    group: 'Sofas & Seating', color: '#b8960c',
    items: [
      { key: 'sofa_3cushion', label: '3-Cushion Sofa', icon: '🛋' },
      { key: 'sofa_2cushion', label: '2-Cushion Sofa', icon: '🛋' },
      { key: 'sofa_chesterfield', label: 'Chesterfield', icon: '🛋' },
      { key: 'sofa_tuxedo', label: 'Tuxedo', icon: '🛋' },
      { key: 'sofa_camelback', label: 'Camelback', icon: '🛋' },
      { key: 'loveseat', label: 'Loveseat', icon: '🛋' },
      { key: 'settee', label: 'Settee', icon: '🛋' },
      { key: 'sectional', label: 'Sectional', icon: '🛋' },
      { key: 'chaise', label: 'Chaise Lounge', icon: '🛋' },
      { key: 'daybed', label: 'Daybed', icon: '🛏' },
    ],
  },
  {
    group: 'Chairs', color: '#16a34a',
    items: [
      { key: 'chair_wingback', label: 'Wingback', icon: '💺' },
      { key: 'chair_club', label: 'Club Chair', icon: '💺' },
      { key: 'chair_barrel', label: 'Barrel Chair', icon: '💺' },
      { key: 'chair_accent', label: 'Accent Chair', icon: '💺' },
      { key: 'chair_slipper', label: 'Slipper Chair', icon: '💺' },
      { key: 'chair_bergere', label: 'Bergere', icon: '💺' },
      { key: 'chair_parsons', label: 'Parsons Chair', icon: '💺' },
      { key: 'dining_chair_full', label: 'Dining Chair', icon: '💺' },
      { key: 'bar_stool', label: 'Bar Stool', icon: '💺' },
    ],
  },
  {
    group: 'Benches & Ottomans', color: '#d97706',
    items: [
      { key: 'bench_straight', label: 'Straight Bench', icon: '🪑' },
      { key: 'bench_l_shaped', label: 'L-Shaped Bench', icon: '🪑' },
      { key: 'bench_u_booth', label: 'U-Booth/Banquette', icon: '🪑' },
      { key: 'bench_curved_banquette', label: 'Curved Banquette', icon: '🪑' },
      { key: 'bench_window_seat', label: 'Window Seat', icon: '🪑' },
      { key: 'ottoman_rectangular', label: 'Ottoman', icon: '🪑' },
      { key: 'ottoman_tufted_cube', label: 'Tufted Cube Ottoman', icon: '🪑' },
      { key: 'ottoman_storage', label: 'Storage Ottoman', icon: '🪑' },
    ],
  },
  {
    group: 'Headboards & Wall Panels', color: '#dc2626',
    items: [
      { key: 'headboard_tufted', label: 'Tufted Headboard', icon: '🛏' },
      { key: 'headboard_rectangular', label: 'Rectangular Headboard', icon: '🛏' },
      { key: 'headboard_arched', label: 'Arched Headboard', icon: '🛏' },
      { key: 'headboard_wingback', label: 'Wingback Headboard', icon: '🛏' },
      { key: 'wall_panel_flat', label: 'Flat Wall Panel', icon: '🧱' },
      { key: 'wall_panel_tufted_diamond', label: 'Diamond Tufted Panel', icon: '🧱' },
      { key: 'wall_panel_tufted_biscuit', label: 'Biscuit Tufted Panel', icon: '🧱' },
      { key: 'wall_panel_channel_vertical', label: 'Channel Panel (Vert)', icon: '🧱' },
      { key: 'wall_panel_channel_horizontal', label: 'Channel Panel (Horiz)', icon: '🧱' },
      { key: 'wall_panel_padded', label: 'Padded Panel', icon: '🧱' },
      { key: 'wall_panel_acoustic', label: 'Acoustic Panel', icon: '🧱' },
    ],
  },
  {
    group: 'Cushions & Pillows', color: '#7c3aed',
    items: [
      { key: 'cushion_seat', label: 'Seat Cushion', icon: '🛏' },
      { key: 'cushion_back', label: 'Back Cushion', icon: '🛏' },
      { key: 'cushion_box_edge', label: 'Box Edge Cushion', icon: '🛏' },
      { key: 'cushion_t_cushion', label: 'T-Cushion', icon: '🛏' },
      { key: 'cushion_bolster', label: 'Bolster', icon: '🛏' },
      { key: 'cushion_throw', label: 'Throw Pillow', icon: '🛌' },
      { key: 'decorative_pillow', label: 'Decorative Pillow', icon: '🛌' },
    ],
  },
  {
    group: 'Bedding', color: '#ec4899',
    items: [
      { key: 'duvet_cover', label: 'Duvet Cover', icon: '🛏' },
      { key: 'coverlet', label: 'Coverlet', icon: '🛏' },
      { key: 'quilt', label: 'Quilt', icon: '🛏' },
      { key: 'bed_skirt', label: 'Bed Skirt', icon: '🛏' },
      { key: 'pillow_sham', label: 'Pillow Sham', icon: '🛌' },
      { key: 'bed_scarf', label: 'Bed Scarf', icon: '🛏' },
    ],
  },
  {
    group: 'Table Linens', color: '#0284c7',
    items: [
      { key: 'tablecloth', label: 'Tablecloth', icon: '🍽' },
      { key: 'table_runner', label: 'Table Runner', icon: '🍽' },
      { key: 'placemat', label: 'Placemat', icon: '🍽' },
      { key: 'table_skirt', label: 'Table Skirt', icon: '🍽' },
    ],
  },
];

const MANUAL_ITEM_TYPES = MANUAL_ITEM_GROUPS.flatMap(g => g.items);

const STEPS = [
  { id: 1, label: 'Customer', icon: User },
  { id: 2, label: 'Photos', icon: Camera },
  { id: 3, label: 'Rooms & Items', icon: Layers },
  { id: 4, label: 'Options', icon: Settings },
  { id: 5, label: 'Review', icon: FileText },
];

const TIERS = [
  { label: 'Essential', key: 'A', color: '#16a34a', bg: '#f0fdf4', border: '#bbf7d0' },
  { label: 'Designer', key: 'B', color: '#b8960c', bg: '#fdf8eb', border: '#f5ecd0' },
  { label: 'Premium', key: 'C', color: '#7c3aed', bg: '#faf5ff', border: '#e9d5ff' },
];

interface Props {
  onBack: () => void;
  editQuoteId?: string;
}

export default function QuoteBuilderScreen({ onBack, editQuoteId }: Props) {
  const [step, setStep] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const [customer, setCustomer] = useState<CustomerInfo>({ name: '', email: '', phone: '', address: '' });
  const [photos, setPhotos] = useState<PhotoFile[]>([]);
  const [scan3DFiles, setScan3DFiles] = useState<Scan3DFile[]>([]);
  const [rooms, setRooms] = useState<Room[]>([{ id: crypto.randomUUID(), name: 'Living Room', items: [] }]);
  const [options, setOptions] = useState<QuoteOptions>({
    fabricGrade: 'B',
    // Drapery
    liningType: 'standard_poly_cotton', pleatType: '', fullness: '2.5x',
    hardwareType: '', finialStyle: '', leadingEdge: 'plain', bottomHem: 'double_fold_4in',
    returnSize: 'standard_3_5in', stacking: 'split', tieback: 'none',
    contrastPiping: false, patternMatch: false,
    // Roman shade
    liftSystem: 'cordless', valanceOption: 'self_valance',
    // Cornice
    corniceConstruction: 'foam_core', corniceFace: 'flat_fabric', dustCover: 'none',
    // Upholstery
    foamType: 'high_density', foamThickness: 4,
    tufting: 'none', welting: 'self_welt', nailheadFinish: 'none', nailheadSpacing: 'standard',
    skirtStyle: 'none', springs: 'eight_way_hand_tied', armStyle: 'track', backStyle: 'tight', legStyle: 'exposed_wood',
    // Wall panel
    panelMounting: 'french_cleat',
    // Bedding
    bedSkirtStyle: 'tailored', shamSize: 'standard', quiltingPattern: 'diamond', monogram: false,
    // Shared
    rushOrder: false, delivery: false, installationIncluded: false,
  });

  // Intake project loading
  const [intakeProjects, setIntakeProjects] = useState<any[]>([]);
  const [loadingIntake, setLoadingIntake] = useState(false);
  const [selectedIntakeId, setSelectedIntakeId] = useState<string | null>(null);

  // Catalog browser
  const [showCatalog, setShowCatalog] = useState(false);
  const [catalogTargetRoom, setCatalogTargetRoom] = useState<string | null>(null);

  // Custom Shape Builder modal for bench items
  const [showShapeBuilder, setShowShapeBuilder] = useState(false);
  const [shapeBuilderTarget, setShapeBuilderTarget] = useState<{ roomId: string; itemId: string; preset: string } | null>(null);

  // Drapery hardware config
  const [hardwareConfig, setHardwareConfig] = useState<Record<string, any>>({});

  // 3D Viewer modal
  const [viewer3DItem, setViewer3DItem] = useState<{ itemId: string; roomId: string; url: string } | null>(null);

  // Fabric selector modal
  const [fabricSelectorOpen, setFabricSelectorOpen] = useState<{
    roomId: string; itemId: string; mode: 'primary' | 'backing';
  } | null>(null);

  // Photo analysis
  const [analyzingPhoto, setAnalyzingPhoto] = useState<number | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalysisItem[] | null>(null);
  const [analysisRaw, setAnalysisRaw] = useState<any>(null); // raw AI response for wizard
  const [showAnalysis, setShowAnalysis] = useState(false);
  const [analysisPhotoIdx, setAnalysisPhotoIdx] = useState<number | null>(null);

  const API_BASE = API.replace(/\/api\/v1$/, '');

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load existing quote data when editQuoteId is provided
  useEffect(() => {
    if (!editQuoteId) return;
    fetch(`${API}/quotes/${editQuoteId}`)
      .then(r => r.json())
      .then(q => {
        // Pre-fill customer
        if (q.customer_name || q.customer_email) {
          setCustomer({
            name: q.customer_name || '',
            email: q.customer_email || '',
            phone: q.customer_phone || '',
            address: q.customer_address || '',
          });
        }
        // Pre-fill photos from quote (handles both string URLs and {url,path} objects)
        if (q.photos?.length) {
          const quotePhotos: PhotoFile[] = q.photos.map((p: any) => {
            const photoPath = typeof p === 'string' ? p : (p.url || p.path || '');
            const absUrl = photoPath.startsWith('http') ? photoPath : `${API_BASE}${photoPath}`;
            return {
              preview: absUrl,
              serverUrl: absUrl,
              originalName: typeof p === 'string' ? photoPath.split('/').pop() || 'photo' : (p.original_name || p.filename || 'photo'),
              fromIntake: true,
              assignedRoomId: typeof p === 'object' ? (p.assigned_room_id || undefined) : undefined,
              assignedItemId: typeof p === 'object' ? (p.assigned_item_id || undefined) : undefined,
            };
          });
          setPhotos(quotePhotos);
        }
        // Also load photos from photo store for this quote — match room assignments from saved quote photos
        fetch(`${API}/photos/quote/${q.id}`)
          .then(r => r.json())
          .then(data => {
            if (data.photos?.length) {
              // Build lookup from saved quote photos by filename/url for room assignments
              const savedAssignments = new Map<string, { roomId?: string; itemId?: string }>();
              (q.photos || []).forEach((sp: any) => {
                if (typeof sp === 'object') {
                  const key = sp.original_name || sp.url?.split('/').pop() || '';
                  if (key && (sp.assigned_room_id || sp.assigned_item_id)) {
                    savedAssignments.set(key, { roomId: sp.assigned_room_id, itemId: sp.assigned_item_id });
                  }
                }
              });
              setPhotos(prev => {
                const existing = new Set(prev.map(p => p.originalName).filter(Boolean));
                // Also include original_name variants in dedup check
                prev.forEach(p => { if (p.serverUrl) existing.add(p.serverUrl.split('/').pop() || ''); });
                const newPhotos = data.photos
                  .filter((p: any) => !existing.has(p.filename) && !existing.has(p.original_name))
                  .map((p: any) => {
                    const assign = savedAssignments.get(p.original_name || p.filename) || {};
                    return {
                      preview: `${API_BASE}${p.path}`,
                      serverUrl: `${API_BASE}${p.path}`,
                      originalName: p.original_name || p.filename,
                      fromIntake: true,
                      assignedRoomId: assign.roomId || undefined,
                      assignedItemId: assign.itemId || undefined,
                    };
                  });
                return [...prev, ...newPhotos];
              });
            }
          })
          .catch(() => {});
        // Pre-fill rooms if they exist (handles both items and windows format)
        if (q.rooms?.length) {
          setRooms(q.rooms.map((r: any) => ({
            id: r.id || crypto.randomUUID(),
            name: r.name || 'Room',
            items: (r.items || r.windows || []).map((w: any) => ({
              id: w.id || crypto.randomUUID(),
              type: w.type || w.treatmentType || 'sofa_3cushion',
              width: w.dimensions?.width || w.width || '',
              height: w.dimensions?.height || w.height || '',
              depth: w.dimensions?.depth || w.depth || '',
              quantity: w.quantity || 1,
              notes: w.notes || w.description || '',
              ...(w.panel_config ? { panelConfig: w.panel_config } : {}),
              ...(w.fabric_id ? { fabric: { id: w.fabric_id, code: w.fabric_code || '', name: w.fabric_name || '', color_pattern: null, material_type: null, supplier: null, cost_per_yard: w.fabric_cost_at_quote || 0, margin_percent: w.fabric_margin_at_quote || 0, width_inches: 54, pattern_repeat_v: 0, pattern_repeat_h: 0, backing_fabric_id: null, swatch_photo_path: null, notes: null } as Fabric } : {}),
              ...(w.fabric_yards_needed ? { fabricYards: w.fabric_yards_needed } : {}),
              ...(w.fabric_yards_override ? { fabricYardsOverride: w.fabric_yards_override } : {}),
              ...(w.backing_fabric_id ? { backingFabric: { id: w.backing_fabric_id, code: w.backing_fabric_code || '', name: w.backing_fabric_name || '', color_pattern: null, material_type: 'Backing', supplier: null, cost_per_yard: 0, margin_percent: 0, width_inches: 54, pattern_repeat_v: 0, pattern_repeat_h: 0, backing_fabric_id: null, swatch_photo_path: null, notes: null } as Fabric } : {}),
              ...(w.backing_yards_needed ? { backingYards: w.backing_yards_needed } : {}),
            })),
          })));
        }
        // Pre-fill options if they exist
        if (q.options) {
          setOptions(prev => ({
            ...prev,
            fabricGrade: q.options.fabric_grade || prev.fabricGrade,
            liningType: q.options.lining_type || prev.liningType,
            tufting: q.options.tufting || prev.tufting,
            welting: q.options.welting || prev.welting,
          }));
        }
      })
      .catch(() => {});
  }, [editQuoteId]);

  // Auto-save photo assignments when they change (debounced) — prevents lost room assignments
  const photoSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (!editQuoteId || photos.length === 0) return;
    // Skip initial load (first 2 seconds)
    if (photoSaveTimerRef.current === undefined) {
      photoSaveTimerRef.current = null;
      return;
    }
    if (photoSaveTimerRef.current) clearTimeout(photoSaveTimerRef.current);
    photoSaveTimerRef.current = setTimeout(() => {
      // Deduplicate by original_name before saving
      const seen = new Set<string>();
      const savedPhotos = photos
        .map(p => ({
          url: p.uploadedFilename || p.serverUrl || p.preview,
          original_name: p.originalName || p.preview.split('/').pop() || 'photo',
          from_intake: p.fromIntake || false,
          assigned_room_id: p.assignedRoomId || null,
          assigned_item_id: p.assignedItemId || null,
        }))
        .filter(p => {
          if (seen.has(p.original_name)) return false;
          seen.add(p.original_name);
          return true;
        });
      fetch(`${API}/quotes/${editQuoteId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ photos: savedPhotos }),
      }).catch(() => {});
    }, 1500);
    return () => { if (photoSaveTimerRef.current) clearTimeout(photoSaveTimerRef.current); };
  }, [photos, editQuoteId]);

  // Auto-save 3D scan assignments when they change (debounced)
  const scanSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (!editQuoteId || scan3DFiles.length === 0) return;
    if (scanSaveTimerRef.current) clearTimeout(scanSaveTimerRef.current);
    scanSaveTimerRef.current = setTimeout(() => {
      const savedScans = scan3DFiles.map(f => ({
        url: f.url,
        filename: f.filename,
        original_name: f.originalName,
        assigned_room_id: f.assignedRoomId || null,
        assigned_item_id: f.assignedItemId || null,
      }));
      fetch(`${API}/quotes/${editQuoteId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scan_3d_files: savedScans }),
      }).catch(() => {});
    }, 1500);
    return () => { if (scanSaveTimerRef.current) clearTimeout(scanSaveTimerRef.current); };
  }, [scan3DFiles, editQuoteId]);

  // Load previously uploaded 3D scans on mount
  useEffect(() => {
    // First try to load from quote JSON (has room assignments)
    if (editQuoteId) {
      fetch(`${API}/quotes/${editQuoteId}`)
        .then(r => r.json())
        .then(q => {
          if (q.scan_3d_files?.length) {
            const loaded: Scan3DFile[] = q.scan_3d_files.map((f: any) => ({
              url: f.url,
              filename: f.filename,
              originalName: f.original_name || f.filename,
              assignedRoomId: f.assigned_room_id || undefined,
              assignedItemId: f.assigned_item_id || undefined,
            }));
            setScan3DFiles(loaded);
            return; // Don't load from photo store if quote has scan data
          }
        })
        .catch(() => {});
    }
    // Fallback: load from photo store (no room assignments)
    fetch(`${API}/photos/quote/3d_scans`)
      .then(r => r.json())
      .then(data => {
        if (data.photos?.length) {
          const modelExts = ['.glb', '.gltf', '.obj', '.ply', '.usdz', '.stl', '.fbx'];
          const models = data.photos.filter((p: any) => modelExts.some(e => p.filename?.toLowerCase().endsWith(e)));
          setScan3DFiles(prev => {
            const existing = new Set(prev.map(f => f.url));
            const newFiles = models.filter((p: any) => !existing.has(`${API_BASE}${p.path}`)).map((p: any, i: number) => ({
              url: `${API_BASE}${p.path}`,
              filename: p.filename,
              originalName: p.display_name || p.original_name || `#${String(i + 1).padStart(3, '0')} — ${p.filename}`,
            }));
            return [...prev, ...newFiles];
          });
        }
      })
      .catch(() => {});
  }, [editQuoteId]);

  // Fetch intake projects when entering Photos step
  useEffect(() => {
    if (step === 2) {
      setLoadingIntake(true);
      fetch(`${API}/intake/admin/projects-with-photos`)
        .then(r => r.json())
        .then(data => setIntakeProjects(data.projects || data || []))
        .catch(() => {})
        .finally(() => setLoadingIntake(false));
    }
  }, [step]);

  // Track deleted photo filenames so intake reload doesn't re-add them
  const deletedPhotosRef = useRef<Set<string>>(new Set());

  // Load intake project photos and customer info
  const loadIntakeProject = (project: any) => {
    setSelectedIntakeId(project.id);
    const intakePhotos: PhotoFile[] = (project.photos || []).map((p: any) => ({
      preview: `${API_BASE}${p.url || p.path}`,
      serverUrl: `${API_BASE}${p.url || p.path}`,
      originalName: p.original_name || p.filename,
      fromIntake: true,
    }));
    setPhotos(prev => {
      // Keep non-intake photos as-is; merge intake photos but skip deleted ones
      const nonIntake = prev.filter(p => !p.fromIntake);
      const existing = new Set(prev.map(p => p.originalName).filter(Boolean));
      const filtered = intakePhotos.filter(p =>
        !deletedPhotosRef.current.has(p.originalName || '') && !existing.has(p.originalName)
      );
      return [...prev.filter(p => p.fromIntake), ...filtered, ...nonIntake];
    });
    // Auto-fill customer info
    if (project.customer_name) {
      setCustomer({
        name: project.customer_name || '',
        email: project.customer_email || '',
        phone: project.customer_phone || '',
        address: project.address || '',
      });
    }
  };

  // Analyze a photo via vision API
  const analyzePhoto = async (idx: number) => {
    setAnalyzingPhoto(idx);
    setAnalysisResult(null);
    setAnalysisRaw(null);
    setShowAnalysis(true);
    setAnalysisPhotoIdx(idx);

    try {
      const photo = photos[idx];
      let base64: string;

      if (photo.serverUrl) {
        // Fetch server photo and convert to base64
        const res = await fetch(photo.serverUrl);
        const blob = await res.blob();
        base64 = await new Promise<string>((resolve) => {
          const reader = new FileReader();
          reader.onloadend = () => resolve((reader.result as string).split(',')[1]);
          reader.readAsDataURL(blob);
        });
      } else if (photo.file) {
        base64 = await new Promise<string>((resolve) => {
          const reader = new FileReader();
          reader.onloadend = () => resolve((reader.result as string).split(',')[1]);
          reader.readAsDataURL(photo.file!);
        });
      } else {
        throw new Error('No photo source available');
      }

      // Call upholstery endpoint for furniture detection + measurements
      const res = await fetch(`${API}/vision/upholstery`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: base64 }),
      });

      if (res.ok) {
        const data = await res.json();
        const items: AnalysisItem[] = [];

        // Primary detected furniture piece
        if (data.furniture_type) {
          const dims = data.estimated_dimensions || {};
          items.push({
            type: mapFurnitureType(data.furniture_type),
            description: [data.furniture_type, data.style].filter(Boolean).join(' — '),
            width: dims.width ? `${dims.width}` : '',
            height: dims.height ? `${dims.height}` : '',
            depth: dims.depth ? `${dims.depth}` : '',
            condition: data.questions?.join('; ') || '',
            checked: true,
          });
        }

        // Additional furniture from all_furniture array
        if (data.all_furniture && Array.isArray(data.all_furniture)) {
          for (const f of data.all_furniture) {
            // Skip if it's the same as the primary piece
            if (items.length === 1 && f.type?.toLowerCase() === data.furniture_type?.toLowerCase()) continue;
            items.push({
              type: mapFurnitureType(f.type || 'sofa'),
              description: [f.type, f.condition].filter(Boolean).join(' — '),
              width: '', height: '', depth: '',
              condition: f.recommendation || '',
              checked: true,
            });
          }
        }

        setAnalysisRaw(data); // store raw for wizard
        setAnalysisResult(items);
      } else {
        setAnalysisResult([]);
      }
    } catch {
      setAnalysisResult([]);
    }
    setAnalyzingPhoto(null);
  };

  // Add analyzed items to rooms
  const addAnalyzedItems = () => {
    if (!analysisResult) return;
    const selected = analysisResult.filter(it => it.checked);
    if (selected.length === 0) return;

    const newItems: RoomItem[] = selected.map(it => ({
      id: crypto.randomUUID(),
      type: ITEM_TYPES.includes(it.type) ? it.type : 'sofa_3cushion',
      width: it.width || '',
      height: it.height || '',
      depth: it.depth || '',
      quantity: 1,
      notes: [it.description, it.condition].filter(Boolean).join(' - '),
    }));

    setRooms(prev => {
      const copy = [...prev];
      copy[0] = { ...copy[0], items: [...copy[0].items, ...newItems] };
      return copy;
    });

    setShowAnalysis(false);
    setAnalysisResult(null);
    setAnalysisPhotoIdx(null);
  };

  // Add a manually entered item to Room 1
  const addManualItem = (item: any) => {
    const newItem: RoomItem = {
      id: crypto.randomUUID(),
      type: ITEM_TYPES.includes(item.type) ? item.type : 'sofa_3cushion',
      width: item.width || '',
      height: item.height || '',
      depth: item.depth || '',
      quantity: 1,
      notes: item.description || '',
      _uploadPath: item._uploadPath,
    };
    setRooms(prev => {
      const copy = [...prev];
      copy[0] = { ...copy[0], items: [...copy[0].items, newItem] };
      return copy;
    });
  };

  const canAdvance = () => {
    if (step === 1) return customer.name.trim().length > 0;
    if (step === 2) return true; // photos optional
    if (step === 3) return rooms.some(r => r.items.length > 0);
    return true;
  };

  // -- Photo handling --
  const handleFiles = useCallback((files: FileList | File[]) => {
    const newPhotos: PhotoFile[] = Array.from(files)
      .filter(f => f.type.startsWith('image/'))
      .map(f => ({ file: f, preview: URL.createObjectURL(f) }));
    setPhotos(prev => [...prev, ...newPhotos]);
  }, []);

  const removePhoto = async (idx: number) => {
    const photo = photos[idx];
    // Track deletion so intake reload won't re-add this photo
    const photoName = photo?.originalName || photo?.uploadedFilename?.split('/').pop() || photo?.preview.split('/').pop() || '';
    if (photoName) deletedPhotosRef.current.add(photoName);

    // Delete from backend if this photo has been uploaded/stored
    if (editQuoteId && photo) {
      if (photoName) {
        try {
          await fetch(`${API}/photos/quote/${editQuoteId}/${encodeURIComponent(photoName)}`, { method: 'DELETE' });
        } catch { /* best effort — still remove from UI */ }
      }
    }
    setPhotos(prev => {
      const copy = [...prev];
      if (!copy[idx].fromIntake && copy[idx].file) {
        URL.revokeObjectURL(copy[idx].preview);
      }
      copy.splice(idx, 1);
      return copy;
    });
  };

  const uploadPhoto = async (photo: PhotoFile): Promise<string | null> => {
    if (photo.uploadedFilename) return photo.uploadedFilename;
    if (photo.fromIntake && photo.serverUrl) {
      // Return the server-relative URL so the quote can reference the intake photo
      const url = new URL(photo.serverUrl, window.location.origin);
      return url.pathname; // e.g. /intake_uploads/{project_id}/photo.jpg
    }
    if (!photo.file) return null;
    const form = new FormData();
    form.append('file', photo.file);
    form.append('entity_type', 'quote');
    form.append('entity_id', 'pending');
    form.append('source', 'web');
    try {
      const res = await fetch(API + '/photos/upload', { method: 'POST', body: form });
      if (res.ok) {
        const data = await res.json();
        const uploaded = data.photos?.[0];
        if (uploaded?.path) return uploaded.path;
        return data.filename || data.file_id || null;
      }
      console.warn('Photo upload failed:', res.status, res.statusText);
    } catch (err) {
      console.warn('Photo upload error:', err);
    }
    return null;
  };

  // -- Room / Item management --
  const addRoom = () => {
    setRooms(prev => [...prev, { id: crypto.randomUUID(), name: `Room ${prev.length + 1}`, items: [] }]);
  };

  const removeRoom = (roomId: string) => {
    setRooms(prev => prev.filter(r => r.id !== roomId));
  };

  const updateRoomName = (roomId: string, name: string) => {
    setRooms(prev => prev.map(r => r.id === roomId ? { ...r, name } : r));
  };

  const moveRoom = (roomId: string, direction: 'up' | 'down') => {
    setRooms(prev => {
      const idx = prev.findIndex(r => r.id === roomId);
      if (idx < 0) return prev;
      const target = direction === 'up' ? idx - 1 : idx + 1;
      if (target < 0 || target >= prev.length) return prev;
      const next = [...prev];
      [next[idx], next[target]] = [next[target], next[idx]];
      return next;
    });
  };

  const moveItem = (roomId: string, itemId: string, direction: 'up' | 'down') => {
    setRooms(prev => prev.map(r => {
      if (r.id !== roomId) return r;
      const idx = r.items.findIndex(it => it.id === itemId);
      if (idx < 0) return r;
      const target = direction === 'up' ? idx - 1 : idx + 1;
      if (target < 0 || target >= r.items.length) return r;
      const items = [...r.items];
      [items[idx], items[target]] = [items[target], items[idx]];
      return { ...r, items };
    }));
  };

  const addItem = (roomId: string, category: ItemCategory = 'upholstery') => {
    const defaultType = category === 'drapery' ? 'drapery' : 'sofa_3cushion';
    setRooms(prev => prev.map(r => r.id === roomId ? {
      ...r, items: [...r.items, {
        id: crypto.randomUUID(), type: defaultType, width: '', height: '', depth: '', quantity: 1, notes: '',
      }]
    } : r));
  };

  const removeItem = (roomId: string, itemId: string) => {
    setRooms(prev => prev.map(r => r.id === roomId ? { ...r, items: r.items.filter(it => it.id !== itemId) } : r));
  };

  const updateItem = (roomId: string, itemId: string, field: keyof RoomItem, value: any) => {
    setRooms(prev => prev.map(r => r.id === roomId ? {
      ...r, items: r.items.map(it => it.id === itemId ? { ...it, [field]: value } : it)
    } : r));
  };

  // Add item from catalog diagram selection
  const addItemFromCatalog = (diagramKey: string) => {
    const roomId = catalogTargetRoom || rooms[0]?.id;
    if (!roomId) return;
    const category: ItemCategory = DIAGRAM_MAP[diagramKey]?.category === 'drapery' ? 'drapery' : 'upholstery';
    // Map diagram key to closest ITEM_TYPES entry
    const itemType = ITEM_TYPES.includes(diagramKey) ? diagramKey : (category === 'drapery' ? 'drapery' : 'sofa_3cushion');
    setRooms(prev => prev.map(r => r.id === roomId ? {
      ...r, items: [...r.items, {
        id: crypto.randomUUID(), type: itemType, width: '', height: '', depth: '', quantity: 1,
        notes: DIAGRAM_MAP[diagramKey]?.label || '',
      }]
    } : r));
    setShowCatalog(false);
    setCatalogTargetRoom(null);
  };

  // -- Submit --
  const handleSubmit = async () => {
    setSubmitting(true);
    setError('');
    try {
      // Upload photos first, preserving index alignment with photos array
      const savedPhotos: { url: string; original_name: string; from_intake?: boolean; assigned_room_id?: string | null; assigned_item_id?: string | null }[] = [];
      for (let i = 0; i < photos.length; i++) {
        const photo = photos[i];
        const fn = await uploadPhoto(photo);
        // Even if upload returns null, keep the photo with its serverUrl so assignments persist
        const url = fn || (photo.serverUrl ? new URL(photo.serverUrl, window.location.origin).pathname : null);
        if (url) {
          savedPhotos.push({
            url,
            original_name: photo.originalName || photo.file?.name || url.split('/').pop() || 'photo',
            from_intake: photo.fromIntake || false,
            assigned_room_id: photo.assignedRoomId || null,
            assigned_item_id: photo.assignedItemId || null,
          });
        }
      }

      const payload = {
        customer_name: customer.name,
        customer_email: customer.email,
        customer_phone: customer.phone,
        customer_address: customer.address,
        photos: savedPhotos,
        rooms: rooms.map(r => ({
          id: r.id,
          name: r.name,
          items: r.items.map(it => ({
            id: it.id,
            type: it.type,
            dimensions: { width: it.width, height: it.height, depth: it.depth },
            quantity: it.quantity,
            notes: it.notes,
            ...(it.panelConfig && it.panelConfig.style !== 'flat' ? { panel_config: it.panelConfig } : {}),
            ...(it.fabric ? {
              fabric_id: it.fabric.id,
              fabric_code: it.fabric.code,
              fabric_name: `${it.fabric.name}${it.fabric.color_pattern ? ' — ' + it.fabric.color_pattern : ''}`,
              fabric_yards_needed: it.fabricYardsOverride || it.fabricYards || 0,
              fabric_yards_override: it.fabricYardsOverride || null,
              fabric_cost_at_quote: it.fabric.cost_per_yard,
              fabric_margin_at_quote: it.fabric.margin_percent,
            } : {}),
            ...(it.backingFabric ? {
              backing_fabric_id: it.backingFabric.id,
              backing_fabric_code: it.backingFabric.code,
              backing_fabric_name: `${it.backingFabric.name}${it.backingFabric.color_pattern ? ' — ' + it.backingFabric.color_pattern : ''}`,
              backing_yards_needed: it.backingYardsOverride || it.backingYards || 0,
            } : {}),
          })),
        })),
        options: {
          fabric_grade: options.fabricGrade,
          // Drapery
          lining_type: options.liningType,
          pleat_type: options.pleatType,
          fullness: options.fullness,
          hardware_type: options.hardwareType,
          finial_style: options.finialStyle,
          leading_edge: options.leadingEdge,
          bottom_hem: options.bottomHem,
          return_size: options.returnSize,
          stacking: options.stacking,
          tieback: options.tieback,
          contrast_piping: options.contrastPiping,
          pattern_match: options.patternMatch,
          // Roman shade
          lift_system: options.liftSystem,
          valance_option: options.valanceOption,
          // Cornice
          cornice_construction: options.corniceConstruction,
          cornice_face: options.corniceFace,
          dust_cover: options.dustCover,
          // Upholstery
          foam_type: options.foamType,
          foam_thickness: options.foamThickness,
          tufting: options.tufting,
          welting: options.welting,
          nailhead_finish: options.nailheadFinish,
          nailhead_spacing: options.nailheadSpacing,
          skirt_style: options.skirtStyle,
          springs: options.springs,
          arm_style: options.armStyle,
          back_style: options.backStyle,
          leg_style: options.legStyle,
          // Wall panel
          panel_mounting: options.panelMounting,
          // Bedding
          bed_skirt_style: options.bedSkirtStyle,
          sham_size: options.shamSize,
          quilting_pattern: options.quiltingPattern,
          monogram: options.monogram,
          // Shared
          rush_order: options.rushOrder,
          delivery: options.delivery,
          installation_included: options.installationIncluded,
        },
      };

      // If editing, include the existing quote ID so backend updates instead of creating new
      if (editQuoteId) {
        (payload as any).quote_id = editQuoteId;
      }
      // Use from-rooms endpoint which runs full pricing pipeline (yardage + tiers)
      const res = await fetch(API + '/quotes/from-rooms', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        const data = await res.json();
        // Unwrap: endpoint returns {status, quote} — use the quote object
        const quote = data.quote || data;
        // Convert tiers object {A:{...}, B:{...}, C:{...}} to array for ResultView
        if (quote.tiers && !Array.isArray(quote.tiers)) {
          const tierKeys = ['A', 'B', 'C'];
          quote.tiers = tierKeys.map(k => quote.tiers[k]).filter(Boolean);
        }
        setResult(quote);
      } else {
        const errData = await res.json().catch(() => null);
        setError(errData?.detail || `Server error ${res.status}`);
      }
    } catch (e: any) {
      const msg = e.message || 'Network error';
      if (msg.toLowerCase().includes('network') || msg.toLowerCase().includes('fetch')) {
        setError(`Cannot reach the server (${API}). Check your connection or try again.`);
      } else {
        setError(msg);
      }
      console.error('Quote submit error:', e);
    }
    setSubmitting(false);
  };

  const totalItems = rooms.reduce((s, r) => s + r.items.reduce((s2, it) => s2 + it.quantity, 0), 0);

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '24px 36px' }}>
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <button onClick={onBack}
          className="flex items-center gap-1.5 cursor-pointer transition-colors hover:text-[#b8960c]"
          style={{ background: 'none', border: 'none', fontSize: 13, fontWeight: 600, color: '#777', padding: 0 }}>
          <ArrowLeft size={16} /> Back
        </button>
        <div className="flex-1" />
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-[#fdf8eb] flex items-center justify-center">
            <FileText size={18} className="text-[#b8960c]" />
          </div>
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>Quote Builder</h1>
            <p style={{ fontSize: 11, color: '#999', margin: 0 }}>Create a new workroom quote</p>
          </div>
        </div>
        <div className="flex-1" />
      </div>

      {/* Step indicators */}
      <div className="flex items-center justify-center gap-1 mb-8">
        {STEPS.map((s, i) => {
          const Icon = s.icon;
          const isActive = step === s.id;
          const isDone = step > s.id;
          return (
            <div key={s.id} className="flex items-center gap-1">
              <button
                onClick={() => { if (isDone || isActive) setStep(s.id); }}
                className="flex items-center gap-1.5 cursor-pointer transition-all"
                style={{
                  padding: '8px 14px', borderRadius: 10, border: 'none', fontSize: 12, fontWeight: 600,
                  background: isActive ? '#fdf8eb' : isDone ? '#f0fdf4' : '#f5f3ef',
                  color: isActive ? '#b8960c' : isDone ? '#16a34a' : '#aaa',
                  outline: isActive ? '2px solid #b8960c' : 'none',
                }}>
                {isDone ? <Check size={14} /> : <Icon size={14} />}
                <span className="hidden sm:inline">{s.label}</span>
              </button>
              {i < STEPS.length - 1 && (
                <div style={{ width: 20, height: 2, background: isDone ? '#bbf7d0' : '#ece8e0', borderRadius: 1 }} />
              )}
            </div>
          );
        })}
      </div>

      {/* Step Content */}
      <div className="empire-card" style={{ padding: 28, minHeight: 340 }}>
        {step === 1 && <StepCustomer customer={customer} setCustomer={setCustomer} />}
        {step === 2 && (
          <>
            <StepPhotos
              photos={photos} onAdd={handleFiles} onRemove={removePhoto} fileInputRef={fileInputRef}
              onAddServerPhotos={(newPhotos) => setPhotos(prev => [...prev, ...newPhotos])}
              apiBase={API_BASE}
              intakeProjects={intakeProjects} loadingIntake={loadingIntake}
              selectedIntakeId={selectedIntakeId} onLoadIntake={loadIntakeProject}
              onAnalyze={analyzePhoto} analyzingPhoto={analyzingPhoto}
              onManualItem={addManualItem}
              rooms={rooms}
              onAssignPhotoRoom={(photoIdx, roomId) => {
                setPhotos(prev => prev.map((p, i) => i === photoIdx ? { ...p, assignedRoomId: roomId || undefined, assignedItemId: roomId ? p.assignedItemId : undefined } : p));
              }}
              onAddRoom={() => {
                const name = prompt('Room name:');
                if (!name) return;
                const newRoom: Room = { id: crypto.randomUUID(), name, items: [] };
                setRooms(prev => [...prev, newRoom]);
                return newRoom.id;
              }}
              scan3DFiles={scan3DFiles}
              onAdd3DFile={(file) => setScan3DFiles(prev => [...prev, file])}
              onAssign3DToRoom={(scanIdx, roomId) => {
                setScan3DFiles(prev => prev.map((f, i) => i === scanIdx ? { ...f, assignedRoomId: roomId || undefined } : f));
              }}
              onPreview3D={(url) => setViewer3DItem({ itemId: '', roomId: '', url })}
              onRemove3D={async (idx) => {
                const scan = scan3DFiles[idx];
                if (scan?.filename) {
                  try {
                    await fetch(`${API}/photos/quote/3d_scans/${encodeURIComponent(scan.filename)}`, { method: 'DELETE' });
                  } catch { /* best effort */ }
                }
                setScan3DFiles(prev => prev.filter((_, i) => i !== idx));
              }}
            />
            {showAnalysis && (
              <AnalysisWizard
                photo={analysisPhotoIdx !== null ? photos[analysisPhotoIdx] : null}
                items={analysisResult}
                rawResponse={analysisRaw}
                analyzing={analyzingPhoto !== null}
                onUpdateItems={setAnalysisResult}
                onAddItems={(enrichedItems) => {
                  if (!enrichedItems || enrichedItems.length === 0) return;
                  const selected = enrichedItems.filter(it => it.checked);
                  const newItems: RoomItem[] = selected.map(it => ({
                    id: crypto.randomUUID(),
                    type: ITEM_TYPES.includes(it.type) ? it.type : 'sofa_3cushion',
                    width: it.width || '',
                    height: it.height || '',
                    depth: it.depth || '',
                    quantity: 1,
                    notes: [it.description, it.condition].filter(Boolean).join(' - '),
                  }));
                  setRooms(prev => {
                    const copy = [...prev];
                    copy[0] = { ...copy[0], items: [...copy[0].items, ...newItems] };
                    return copy;
                  });
                  setShowAnalysis(false);
                  setAnalysisResult(null);
                  setAnalysisPhotoIdx(null);
                }}
                onClose={() => { setShowAnalysis(false); setAnalysisResult(null); setAnalysisRaw(null); setAnalysisPhotoIdx(null); }}
              />
            )}
          </>
        )}
        {step === 3 && (
          <>
            <StepRooms
              rooms={rooms} photos={photos} scan3DFiles={scan3DFiles} apiBase={API_BASE}
              addRoom={addRoom} removeRoom={removeRoom} moveRoom={moveRoom} updateRoomName={updateRoomName}
              addItem={addItem} moveItem={moveItem} removeItem={removeItem} updateItem={updateItem}
              onBrowseCatalog={(roomId) => { setCatalogTargetRoom(roomId); setShowCatalog(true); }}
              onSelectFabric={(roomId, itemId, mode) => setFabricSelectorOpen({ roomId, itemId, mode })}
              onAssignPhotoToItem={(photoIndex, itemId, type) => {
                if (type === 'photo') {
                  setPhotos(prev => prev.map((p, i) => i === photoIndex ? { ...p, assignedItemId: itemId } : p));
                } else {
                  setScan3DFiles(prev => prev.map((f, i) => i === photoIndex ? { ...f, assignedItemId: itemId } : f));
                }
              }}
              onOpenShapeBuilder={(roomId, itemId, itemType) => {
                const preset = BENCH_SHAPE_MAP[itemType];
                if (preset) {
                  setShapeBuilderTarget({ roomId, itemId, preset });
                  setShowShapeBuilder(true);
                }
              }}
              onView3D={(roomId, itemId) => {
                const room = rooms.find(r => r.id === roomId);
                const item = room?.items.find(i => i.id === itemId);
                if (item?.notes?.startsWith('3D Scan:')) {
                  const filename = item.notes.replace('3D Scan: ', '');
                  if (item._uploadPath) {
                    setViewer3DItem({ itemId, roomId, url: API_BASE + item._uploadPath });
                  } else {
                    // Fallback: search photos API for the file
                    fetch(`${API}/photos/quote/3d_scans`)
                      .then(r => r.json())
                      .then(data => {
                        const photos = data.photos || [];
                        const match = photos.find((p: any) => p.original_name === filename || p.filename?.includes(filename.split('.')[0]));
                        const url = match?.path || photos[photos.length - 1]?.path;
                        if (url) setViewer3DItem({ itemId, roomId, url: API_BASE + url });
                      })
                      .catch(err => console.error('Failed to find 3D file:', err));
                  }
                }
              }}
            />
            {showCatalog && (
              <div style={{ position: 'fixed', inset: 0, zIndex: 50, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.4)' }} onClick={() => setShowCatalog(false)} />
                <div style={{ position: 'relative', width: '90%', maxWidth: 900, maxHeight: '85vh', overflow: 'auto', background: '#fff', borderRadius: 16, boxShadow: '0 8px 40px rgba(0,0,0,0.2)', padding: 0 }}>
                  <div style={{ position: 'sticky', top: 0, zIndex: 2, background: '#fff', padding: '16px 24px', borderBottom: '1px solid #ece8e0', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: '#1a1a1a' }}>Product Catalog</div>
                      <div style={{ fontSize: 12, color: '#888' }}>Select a product to add to your quote</div>
                    </div>
                    <button onClick={() => setShowCatalog(false)} style={{ width: 32, height: 32, borderRadius: 8, border: '1px solid #ece8e0', background: '#faf9f7', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
                      <X size={16} />
                    </button>
                  </div>
                  <div style={{ padding: 24 }}>
                    <DiagramCatalog
                      onSelect={(key) => addItemFromCatalog(key)}
                      onQuickAdd={(key) => addItemFromCatalog(key)}
                    />
                  </div>
                </div>
              </div>
            )}
            {/* Fabric Selector modal */}
            {fabricSelectorOpen && (
              <FabricSelector
                mode="owner"
                filterType={fabricSelectorOpen.mode === 'backing' ? 'Backing' : undefined}
                suggestedBackingId={(() => {
                  if (fabricSelectorOpen.mode !== 'backing') return null;
                  const room = rooms.find(r => r.id === fabricSelectorOpen.roomId);
                  const item = room?.items.find(i => i.id === fabricSelectorOpen.itemId);
                  return item?.fabric?.backing_fabric_id || null;
                })()}
                onSelect={(fabric) => {
                  const { roomId, itemId, mode } = fabricSelectorOpen;
                  if (mode === 'primary') {
                    updateItem(roomId, itemId, 'fabric', fabric);
                  } else {
                    updateItem(roomId, itemId, 'backingFabric', fabric);
                  }
                  setFabricSelectorOpen(null);
                }}
                onClose={() => setFabricSelectorOpen(null)}
              />
            )}
            {/* Custom Shape Builder modal for bench items */}
            {showShapeBuilder && shapeBuilderTarget && (
              <div style={{ position: 'fixed', inset: 0, zIndex: 50, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.4)' }} onClick={() => setShowShapeBuilder(false)} />
                <div style={{ position: 'relative', width: '95%', maxWidth: 1100, maxHeight: '90vh', overflow: 'auto', background: '#fff', borderRadius: 16, boxShadow: '0 8px 40px rgba(0,0,0,0.2)', padding: 0 }}>
                  <div style={{ position: 'sticky', top: 0, zIndex: 2, background: '#fff', padding: '16px 24px', borderBottom: '1px solid #ece8e0', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: '#1a1a1a' }}>Custom Shape Builder</div>
                      <div style={{ fontSize: 12, color: '#888' }}>Configure dimensions, seatbacks, and cushion layout for this bench</div>
                    </div>
                    <button onClick={() => setShowShapeBuilder(false)} style={{ width: 32, height: 32, borderRadius: 8, border: '1px solid #ece8e0', background: '#faf9f7', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
                      <X size={16} />
                    </button>
                  </div>
                  <div style={{ padding: 24 }}>
                    <CustomShapeBuilder
                      initialPreset={shapeBuilderTarget.preset}
                      onSave={(shapeType, dims, result) => {
                        // Update the bench item's notes with shape builder results
                        const { roomId, itemId } = shapeBuilderTarget;
                        const summary = [
                          `Shape: ${shapeType.replace(/_/g, ' ')}`,
                          dims.length ? `L: ${dims.length}"` : '',
                          dims.length_a ? `A: ${dims.length_a}" B: ${dims.length_b}"` : '',
                          dims.length_c ? `C: ${dims.length_c}"` : '',
                          dims.depth ? `D: ${dims.depth}"` : '',
                          dims.radius ? `R: ${dims.radius}" Arc: ${dims.arc_degrees}°` : '',
                          result?.linear_feet ? `${result.linear_feet.toFixed(1)} lin ft` : '',
                          result?.square_footage ? `${result.square_footage.toFixed(1)} sq ft` : '',
                          result?.fabric_yardage_54 ? `${result.fabric_yardage_54.toFixed(2)} yd fabric` : '',
                        ].filter(Boolean).join(' | ');
                        updateItem(roomId, itemId, 'notes', summary);
                        // Update dimensions from shape builder
                        if (dims.length) updateItem(roomId, itemId, 'width', String(dims.length));
                        if (dims.length_a) updateItem(roomId, itemId, 'width', String(dims.length_a));
                        if (dims.depth) updateItem(roomId, itemId, 'depth', String(dims.depth));
                        if (dims.height) updateItem(roomId, itemId, 'height', String(dims.height));
                        setShowShapeBuilder(false);
                        setShapeBuilderTarget(null);
                      }}
                    />
                  </div>
                </div>
              </div>
            )}
          </>
        )}
        {step === 4 && <StepOptions options={options} setOptions={setOptions} rooms={rooms} hardwareConfig={hardwareConfig} setHardwareConfig={setHardwareConfig} />}
        {step === 5 && !result && (
          <StepReview customer={customer} photos={photos} rooms={rooms} options={options} totalItems={totalItems} />
        )}
        {step === 5 && result && <ResultView result={result} />}
        {error && <div style={{ marginTop: 16, padding: '12px 16px', borderRadius: 10, background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626', fontSize: 13 }}>{error}</div>}
      </div>

      {/* 3D Viewer Modal — global, works from any step */}
      {viewer3DItem && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 50, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.5)' }} onClick={() => setViewer3DItem(null)} />
          <div style={{ position: 'relative', width: '95%', maxWidth: 1200, height: '85vh', background: '#fff', borderRadius: 16, boxShadow: '0 8px 40px rgba(0,0,0,0.25)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <div style={{ padding: '16px 24px', borderBottom: '1px solid #ece8e0', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: '#f0fdf4', color: '#16a34a' }}>
                  <Box size={16} />
                </div>
                <div>
                  <div style={{ fontSize: 16, fontWeight: 700, color: '#1a1a1a' }}>3D Scan Viewer</div>
                  <div style={{ fontSize: 12, color: '#888' }}>Measure, calibrate, and define treatment areas</div>
                </div>
              </div>
              <button onClick={() => setViewer3DItem(null)} style={{ width: 32, height: 32, borderRadius: 8, border: '1px solid #ece8e0', background: '#faf9f7', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
                <X size={16} />
              </button>
            </div>
            <div style={{ flex: 1, padding: 16, overflow: 'hidden' }}>
              <ThreeViewer
                modelUrl={viewer3DItem.url}
                width={1160}
                height={600}
                onExportData={viewer3DItem.itemId ? (data) => {
                  const { roomId, itemId } = viewer3DItem;
                  if (data.measurements?.length > 0) {
                    const m = data.measurements;
                    if (m[0]?.value_inches) updateItem(roomId, itemId, 'width', String(Math.round(m[0].value_inches)));
                    if (m[1]?.value_inches) updateItem(roomId, itemId, 'height', String(Math.round(m[1].value_inches)));
                    if (m[2]?.value_inches) updateItem(roomId, itemId, 'depth', String(Math.round(m[2].value_inches)));
                  }
                  setViewer3DItem(null);
                } : undefined}
              />
            </div>
          </div>
        </div>
      )}

      {/* Navigation buttons */}
      <div className="flex items-center justify-between mt-5">
        <button onClick={() => setStep(s => Math.max(1, s - 1))} disabled={step === 1}
          className="flex items-center gap-1.5 cursor-pointer disabled:opacity-30 transition-all hover:text-[#b8960c]"
          style={{ height: 40, padding: '0 18px', borderRadius: 10, border: '1.5px solid #ece8e0', background: '#faf9f7', fontSize: 13, fontWeight: 600, color: '#555' }}>
          <ArrowLeft size={16} /> Previous
        </button>
        <div style={{ fontSize: 12, color: '#aaa' }}>Step {step} of 5</div>
        {step < 5 ? (
          <button onClick={() => setStep(s => Math.min(5, s + 1))} disabled={!canAdvance()}
            className="flex items-center gap-1.5 cursor-pointer disabled:opacity-40 transition-all hover:bg-[#a08509]"
            style={{ height: 40, padding: '0 18px', borderRadius: 10, border: 'none', background: '#b8960c', color: '#fff', fontSize: 13, fontWeight: 700 }}>
            Next <ArrowRight size={16} />
          </button>
        ) : !result ? (
          <button onClick={handleSubmit} disabled={submitting}
            className="flex items-center gap-1.5 cursor-pointer disabled:opacity-60 transition-all hover:bg-[#a08509]"
            style={{ height: 44, padding: '0 24px', borderRadius: 12, border: 'none', background: '#b8960c', color: '#fff', fontSize: 14, fontWeight: 700, boxShadow: '0 2px 10px rgba(184,150,12,0.3)' }}>
            {submitting ? <><Loader2 size={18} className="animate-spin" /> Generating...</> : <><FileText size={18} /> Generate Quote</>}
          </button>
        ) : (
          <button onClick={onBack}
            className="flex items-center gap-1.5 cursor-pointer transition-all hover:bg-[#15803d]"
            style={{ height: 40, padding: '0 18px', borderRadius: 10, border: 'none', background: '#16a34a', color: '#fff', fontSize: 13, fontWeight: 700 }}>
            <Check size={16} /> Done
          </button>
        )}
      </div>

    </div>
  );
}

// ============ Step Components ============

function StepCustomer({ customer, setCustomer }: { customer: CustomerInfo; setCustomer: (c: CustomerInfo) => void }) {
  const update = (field: keyof CustomerInfo, value: string) => setCustomer({ ...customer, [field]: value });
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [allCustomers, setAllCustomers] = useState<any[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const nameRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetch(`${API}/crm/customers`).then(r => r.json())
      .then(data => setAllCustomers(data.customers || data || []))
      .catch(() => {});
  }, []);

  const handleNameChange = (value: string) => {
    update('name', value);
    setSelectedId(null);
    if (value.length >= 2 && allCustomers.length > 0) {
      const q = value.toLowerCase();
      const matches = allCustomers.filter((c: any) => c.name?.toLowerCase().includes(q)).slice(0, 6);
      setSuggestions(matches);
      setShowSuggestions(matches.length > 0);
    } else {
      setShowSuggestions(false);
    }
  };

  const selectCustomer = (c: any) => {
    setCustomer({ name: c.name || '', email: c.email || '', phone: c.phone || '', address: c.address || '' });
    setSelectedId(c.id);
    setShowSuggestions(false);
  };

  return (
    <div>
      <div style={{ fontSize: 10, fontWeight: 700, color: '#b8960c', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 16 }}>
        Customer Information
      </div>
      {selectedId && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, padding: '8px 12px', background: '#f0fdf4', borderRadius: 8, border: '1px solid #bbf7d0' }}>
          <Check size={14} className="text-green-600" />
          <span style={{ fontSize: 12, color: '#15803d', fontWeight: 500 }}>Loaded from CRM</span>
          <button onClick={() => { setSelectedId(null); setCustomer({ name: '', email: '', phone: '', address: '' }); }} style={{ marginLeft: 'auto', fontSize: 11, color: '#999', cursor: 'pointer', background: 'none', border: 'none' }}>Clear</button>
        </div>
      )}
      <div className="grid grid-cols-2 gap-4">
        <div style={{ position: 'relative' }}>
          <label style={{ fontSize: 11, fontWeight: 600, color: '#555', display: 'block', marginBottom: 4 }}>Full Name *</label>
          <div style={{ position: 'relative' }}>
            <input ref={nameRef} value={customer.name} onChange={e => handleNameChange(e.target.value)}
              onFocus={() => { if (suggestions.length > 0 && !selectedId) setShowSuggestions(true); }}
              onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
              placeholder="Start typing to search CRM..."
              className="form-input" style={{ width: '100%', paddingRight: 30 }} />
            <Search size={14} style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', color: '#ccc', pointerEvents: 'none' }} />
          </div>
          {showSuggestions && (
            <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 50, background: '#fff', border: '1px solid #e5e0d8', borderRadius: 10, boxShadow: '0 8px 24px rgba(0,0,0,0.12)', marginTop: 4, maxHeight: 220, overflowY: 'auto' }}>
              {suggestions.map(c => (
                <div key={c.id} onMouseDown={() => selectCustomer(c)}
                  style={{ padding: '10px 14px', cursor: 'pointer', borderBottom: '1px solid #f5f3ef', display: 'flex', alignItems: 'center', gap: 10 }}
                  className="hover:bg-[#fdf8eb]">
                  <div style={{ width: 32, height: 32, borderRadius: '50%', background: '#f5f0e6', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 700, color: '#b8960c', flexShrink: 0 }}>
                    {(c.name || '?')[0].toUpperCase()}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>{c.name}</div>
                    <div style={{ fontSize: 11, color: '#999', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {[c.email, c.phone, c.company].filter(Boolean).join(' · ') || 'No contact info'}
                    </div>
                  </div>
                  {c.total_revenue > 0 && (
                    <div style={{ fontSize: 11, fontWeight: 600, color: '#b8960c' }}>${c.total_revenue.toLocaleString()}</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
        <div>
          <label style={{ fontSize: 11, fontWeight: 600, color: '#555', display: 'block', marginBottom: 4 }}>Email</label>
          <input value={customer.email} onChange={e => update('email', e.target.value)} placeholder="jane@example.com" type="email"
            className="form-input" style={{ width: '100%' }} />
        </div>
        <div>
          <label style={{ fontSize: 11, fontWeight: 600, color: '#555', display: 'block', marginBottom: 4 }}>Phone</label>
          <input value={customer.phone} onChange={e => update('phone', e.target.value)} placeholder="(555) 123-4567"
            className="form-input" style={{ width: '100%' }} />
        </div>
        <div>
          <label style={{ fontSize: 11, fontWeight: 600, color: '#555', display: 'block', marginBottom: 4 }}>Address</label>
          <input value={customer.address} onChange={e => update('address', e.target.value)} placeholder="123 Main St, City, ST"
            className="form-input" style={{ width: '100%' }} />
        </div>
      </div>
    </div>
  );
}

function StepPhotos({ photos, onAdd, onAddServerPhotos, onRemove, fileInputRef, intakeProjects, loadingIntake, selectedIntakeId, onLoadIntake, onAnalyze, analyzingPhoto, onManualItem, apiBase, rooms, onAssignPhotoRoom, onAddRoom, scan3DFiles, onAdd3DFile, onAssign3DToRoom, onPreview3D, onRemove3D }: {
  photos: PhotoFile[]; onAdd: (files: FileList | File[]) => void; onAddServerPhotos?: (photos: PhotoFile[]) => void; onRemove: (i: number) => void;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  intakeProjects: any[]; loadingIntake: boolean; selectedIntakeId: string | null;
  onLoadIntake: (project: any) => void; onAnalyze: (idx: number) => void; analyzingPhoto: number | null;
  onManualItem: (item: any) => void;
  apiBase?: string;
  rooms?: Room[];
  onAssignPhotoRoom?: (photoIdx: number, roomId: string) => void;
  onAddRoom?: () => string | undefined;
  scan3DFiles?: Scan3DFile[];
  onAdd3DFile?: (file: Scan3DFile) => void;
  onAssign3DToRoom?: (scanIdx: number, roomId: string) => void;
  onPreview3D?: (url: string) => void;
  onRemove3D?: (scanIdx: number) => void;
}) {
  const API_BASE = apiBase || '';
  const [dragOver, setDragOver] = useState(false);
  const [inputMethod, setInputMethod] = useState<QuoteInputMethod>('photos');
  const [uploading3D, setUploading3D] = useState(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length) onAdd(e.dataTransfer.files);
  };

  const methodTabs: { key: QuoteInputMethod; label: string; icon: React.ReactNode; color: string }[] = [
    { key: 'photos', label: 'Upload Photos', icon: <Camera size={15} />, color: '#2563eb' },
    { key: '3dscan', label: '3D Scan', icon: <Box size={15} />, color: '#16a34a' },
    { key: 'manual', label: 'Manual Entry', icon: <Edit3 size={15} />, color: '#b8960c' },
    { key: 'intake', label: 'Load from Intake', icon: <FolderOpen size={15} />, color: '#7c3aed' },
  ];

  return (
    <div>
      {/* Input method selector */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 20, flexWrap: 'wrap' }}>
        {methodTabs.map(tab => {
          const active = inputMethod === tab.key;
          return (
            <button key={tab.key} onClick={() => setInputMethod(tab.key)}
              className="flex items-center gap-2 cursor-pointer transition-all"
              style={{
                padding: '10px 16px', borderRadius: 10, fontSize: 12, fontWeight: 600,
                border: `2px solid ${active ? tab.color : '#ece8e0'}`,
                background: active ? `${tab.color}10` : '#faf9f7',
                color: active ? tab.color : '#777',
                minHeight: 44,
              }}>
              {tab.icon} {tab.label}
              {tab.key === 'intake' && selectedIntakeId && (
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#16a34a', display: 'inline-block', marginLeft: 4 }} />
              )}
            </button>
          );
        })}
      </div>

      {/* ── Upload Photos ── */}
      {inputMethod === 'photos' && (
        <div>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#b8960c', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 12 }}>
            Photo Gallery
          </div>

          {photos.length > 0 && (
            <div className="flex gap-3 flex-wrap mb-4">
              {photos.map((p, i) => (
                <div key={i} style={{ position: 'relative', width: 120, borderRadius: 12, overflow: 'hidden', border: '2px solid #ece8e0', background: '#f5f3ef' }}>
                  <img src={p.preview} alt="" style={{ width: '100%', height: 100, objectFit: 'cover' }} />
                  {p.fromIntake && (
                    <div style={{ position: 'absolute', top: 4, left: 4, fontSize: 8, fontWeight: 700, color: '#fff', background: '#b8960c', padding: '2px 5px', borderRadius: 4 }}>
                      INTAKE
                    </div>
                  )}
                  <button onClick={(e) => { e.stopPropagation(); onRemove(i); }}
                    className="cursor-pointer transition-all hover:bg-[#dc2626]"
                    style={{
                      position: 'absolute', top: 4, right: 4, width: 22, height: 22, borderRadius: 6,
                      background: 'rgba(0,0,0,0.5)', color: '#fff', border: 'none', display: 'flex',
                      alignItems: 'center', justifyContent: 'center',
                    }}>
                    <X size={12} />
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); onAnalyze(i); }}
                    disabled={analyzingPhoto === i}
                    className="cursor-pointer transition-all hover:bg-[#fdf8eb]"
                    style={{
                      width: '100%', height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4,
                      background: '#faf9f7', border: 'none', borderTop: '1px solid #ece8e0',
                      fontSize: 10, fontWeight: 600, color: analyzingPhoto === i ? '#b8960c' : '#777',
                    }}>
                    {analyzingPhoto === i
                      ? <><Loader2 size={11} className="animate-spin" /> Analyzing...</>
                      : <><Sparkles size={11} /> Analyze</>}
                  </button>
                  {rooms && onAssignPhotoRoom && (
                    <select
                      value={p.assignedRoomId || ''}
                      onChange={(e) => {
                        const val = e.target.value;
                        if (val === '__new__') {
                          const newId = onAddRoom?.();
                          if (newId) onAssignPhotoRoom(i, newId);
                        } else {
                          onAssignPhotoRoom(i, val);
                        }
                      }}
                      onClick={e => e.stopPropagation()}
                      style={{
                        width: '100%', fontSize: 9, padding: '4px 6px', border: 'none',
                        borderTop: '1px solid #ece8e0', background: p.assignedRoomId ? '#f0fdf4' : '#faf9f7',
                        color: p.assignedRoomId ? '#16a34a' : '#999', fontWeight: 600, cursor: 'pointer',
                        borderRadius: '0 0 10px 10px',
                      }}
                    >
                      <option value="">Assign Room...</option>
                      {rooms.map(r => (
                        <option key={r.id} value={r.id}>{r.name}</option>
                      ))}
                      <option value="__new__">+ New Room</option>
                    </select>
                  )}
                </div>
              ))}
            </div>
          )}

          <div
            onDragOver={e => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className="cursor-pointer transition-all"
            style={{
              border: `2px dashed ${dragOver ? '#b8960c' : '#ddd'}`,
              borderRadius: 14,
              padding: photos.length > 0 ? '20px 24px' : '36px 24px',
              textAlign: 'center',
              background: dragOver ? '#fdf8eb' : '#faf9f7',
            }}>
            <Upload size={photos.length > 0 ? 22 : 32} className="mx-auto mb-2" style={{ color: dragOver ? '#b8960c' : '#ccc' }} />
            <div style={{ fontSize: 13, fontWeight: 600, color: '#555' }}>
              {photos.length > 0 ? 'Add more photos' : 'Drop photos here or click to browse'}
            </div>
            <div style={{ fontSize: 11, color: '#aaa', marginTop: 2 }}>JPG, PNG, HEIC accepted</div>
            <input ref={fileInputRef} type="file" accept="image/*" multiple hidden
              onChange={e => { if (e.target.files?.length) onAdd(e.target.files); e.target.value = ''; }} />
          </div>
        </div>
      )}

      {/* ── 3D Scan ── */}
      {inputMethod === '3dscan' && (
        <div>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#16a34a', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 12 }}>
            3D Scan Upload
          </div>
          <div style={{
            border: '2px dashed #bbf7d0', borderRadius: 14, padding: '40px 24px', textAlign: 'center',
            background: '#f0fdf4',
          }}>
            <Box size={36} className="mx-auto mb-3" style={{ color: '#16a34a' }} />
            <div style={{ fontSize: 14, fontWeight: 600, color: '#333', marginBottom: 4 }}>
              Upload a 3D Scan
            </div>
            <div style={{ fontSize: 12, color: '#777', marginBottom: 16 }}>
              Supports GLB, GLTF, OBJ, PLY, USDZ, STL, FBX, or ZIP from Polycam, LiDAR, or RealityScan
            </div>
            <button
              onClick={() => {
                const input = document.createElement('input');
                input.type = 'file';
                input.accept = '.glb,.gltf,.obj,.ply,.usdz,.stl,.fbx,.zip';
                input.onchange = async (e: any) => {
                  const file = e.target?.files?.[0];
                  console.log('[3D Upload] File selected:', file?.name, file?.size, 'bytes');
                  if (!file) return;
                  setUploading3D(true);
                  const fd = new FormData();
                  fd.append('files', file);
                  fd.append('entity_type', 'quote');
                  fd.append('entity_id', '3d_scans');
                  fd.append('source', 'cc');
                  const uploadUrl = `${API}/photos/upload`;
                  console.log('[3D Upload] Uploading to:', uploadUrl);
                  try {
                    const res = await fetch(uploadUrl, { method: 'POST', body: fd });
                    if (!res.ok) throw new Error(`Upload failed (${res.status})`);
                    const data = await res.json();
                    const allFiles = data.photos || [];
                    // Separate 3D models from images
                    const modelExts = ['.glb', '.gltf', '.obj', '.ply', '.usdz', '.stl', '.fbx'];
                    const imageExts = ['.jpg', '.jpeg', '.png', '.webp', '.heic', '.gif', '.bmp'];
                    const models = allFiles.filter((p: any) => modelExts.some(e => p.filename?.toLowerCase().endsWith(e)));
                    const images = allFiles.filter((p: any) => imageExts.some(e => p.filename?.toLowerCase().endsWith(e)));
                    // Add images to photos gallery
                    if (images.length > 0 && onAddServerPhotos) {
                      const newPhotos: PhotoFile[] = images.map((p: any) => ({
                        preview: `${API_BASE}${p.path}`,
                        serverUrl: `${API_BASE}${p.path}`,
                        originalName: p.display_name || p.original_name || p.filename,
                        fromIntake: false,
                      }));
                      onAddServerPhotos(newPhotos);
                    }
                    // Store 3D models in scan list (not as room items)
                    for (const model of models) {
                      onAdd3DFile?.({
                        url: `${API_BASE}${model.path}`,
                        filename: model.filename,
                        originalName: model.display_name || model.original_name || file.name,
                      });
                    }
                    // If zip had no recognized models, add the primary file
                    if (models.length === 0 && allFiles[0]) {
                      onAdd3DFile?.({
                        url: `${API_BASE}${allFiles[0].path}`,
                        filename: allFiles[0].filename,
                        originalName: allFiles[0].display_name || allFiles[0].original_name || file.name,
                      });
                    }
                  } catch (err) {
                    console.error('[3D Upload] FAILED:', err);
                    alert('Failed to upload 3D file. Check your connection and try again.');
                  } finally {
                    setUploading3D(false);
                  }
                };
                input.click();
              }}
              disabled={uploading3D}
              className="flex items-center gap-2 cursor-pointer transition-all hover:brightness-110 mx-auto"
              style={{ padding: '12px 24px', borderRadius: 10, background: uploading3D ? '#86efac' : '#16a34a', color: '#fff', fontSize: 13, fontWeight: 700, border: 'none', minHeight: 48, opacity: uploading3D ? 0.8 : 1 }}>
              {uploading3D ? <><Loader2 size={16} className="animate-spin" /> Uploading...</> : <><Upload size={16} /> Choose 3D File</>}
            </button>
            <div style={{ fontSize: 11, color: '#aaa', marginTop: 12 }}>
              Scan rooms with your phone&apos;s LiDAR sensor, then upload the exported model
            </div>
          </div>

          {/* Uploaded 3D Files List */}
          {scan3DFiles && scan3DFiles.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: '#16a34a', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
                Uploaded 3D Scans ({scan3DFiles.length})
              </div>
              {scan3DFiles.map((f, idx) => (
                <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px', marginBottom: 6, borderRadius: 10, border: '1px solid #d1fae5', background: '#f0fdf4' }}>
                  <Box size={16} style={{ color: '#16a34a', flexShrink: 0 }} />
                  <span style={{ fontSize: 12, fontWeight: 600, color: '#333', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {f.originalName}
                  </span>
                  <button
                    onClick={() => onPreview3D?.(f.url)}
                    className="cursor-pointer transition-all hover:bg-[#16a34a] hover:text-white"
                    style={{ fontSize: 10, fontWeight: 700, padding: '4px 10px', borderRadius: 6, border: '1px solid #16a34a', background: '#fff', color: '#16a34a' }}
                  >
                    <Eye size={12} style={{ display: 'inline', marginRight: 3 }} />Preview
                  </button>
                  {rooms && onAssign3DToRoom && (
                    <select
                      value={f.assignedRoomId || ''}
                      onChange={(e) => {
                        const val = e.target.value;
                        if (val === '__new__') {
                          const newId = onAddRoom?.();
                          if (newId) onAssign3DToRoom(idx, newId);
                        } else {
                          onAssign3DToRoom(idx, val);
                        }
                      }}
                      style={{ fontSize: 10, padding: '4px 8px', borderRadius: 6, border: '1px solid #d1fae5', background: f.assignedRoomId ? '#dcfce7' : '#fff', color: f.assignedRoomId ? '#16a34a' : '#999', fontWeight: 600, cursor: 'pointer' }}
                    >
                      <option value="">Assign Room...</option>
                      {rooms.map(r => (
                        <option key={r.id} value={r.id}>{r.name}</option>
                      ))}
                      <option value="__new__">+ New Room</option>
                    </select>
                  )}
                  <button
                    onClick={() => onRemove3D?.(idx)}
                    className="cursor-pointer transition-all hover:bg-[#dc2626] hover:text-white"
                    style={{ width: 24, height: 24, borderRadius: 6, border: '1px solid #fca5a5', background: '#fff', color: '#ef4444', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}
                  >
                    <X size={12} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Manual Entry ── */}
      {inputMethod === 'manual' && (
        <QuoteManualEntry onAddItem={onManualItem} />
      )}

      {/* ── Load from Intake ── */}
      {inputMethod === 'intake' && (
        <div>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#7c3aed', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 12 }}>
            Load from Intake Submission
          </div>
          {selectedIntakeId && (
            <div style={{ marginBottom: 12, padding: '8px 12px', borderRadius: 8, background: '#f0fdf4', border: '1px solid #bbf7d0', fontSize: 12, fontWeight: 600, color: '#16a34a', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Check size={14} /> Intake loaded — photos added to gallery
            </div>
          )}
          <div style={{ border: '1.5px solid #ece8e0', borderRadius: 12, background: '#faf9f7', overflow: 'hidden' }}>
            {loadingIntake ? (
              <div style={{ padding: '20px', textAlign: 'center' }}>
                <Loader2 size={18} className="animate-spin mx-auto" style={{ color: '#b8960c' }} />
                <div style={{ fontSize: 11, color: '#999', marginTop: 6 }}>Loading intake projects...</div>
              </div>
            ) : intakeProjects.length === 0 ? (
              <div style={{ padding: '20px', textAlign: 'center', fontSize: 12, color: '#bbb' }}>
                <ImageIcon size={20} className="mx-auto mb-2" style={{ color: '#ddd' }} />
                No intake projects with photos found
              </div>
            ) : (
              <div style={{ maxHeight: 280, overflowY: 'auto' }}>
                {intakeProjects.map((proj: any) => {
                  const isSelected = selectedIntakeId === proj.id;
                  return (
                    <div
                      key={proj.id}
                      onClick={() => onLoadIntake(proj)}
                      className="cursor-pointer transition-all hover:bg-[#fdf8eb]"
                      style={{
                        padding: '10px 14px',
                        borderBottom: '1px solid #f0ede8',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 10,
                        background: isSelected ? '#fdf8eb' : 'transparent',
                      }}>
                      <div style={{
                        width: 32, height: 32, borderRadius: 8, background: isSelected ? '#b8960c' : '#f5f0e6',
                        display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                      }}>
                        {isSelected
                          ? <Check size={14} style={{ color: '#fff' }} />
                          : <Camera size={14} style={{ color: '#b8960c' }} />}
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>
                          {proj.customer_name || 'Unknown Customer'}
                        </div>
                        <div style={{ fontSize: 11, color: '#999', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {[proj.intake_code, proj.project_type].filter(Boolean).join(' · ')}
                        </div>
                      </div>
                      <div style={{ textAlign: 'right', flexShrink: 0 }}>
                        <div style={{ fontSize: 12, fontWeight: 600, color: '#b8960c' }}>
                          {(proj.photos || []).length} photo{(proj.photos || []).length !== 1 ? 's' : ''}
                        </div>
                        {proj.created_at && (
                          <div style={{ fontSize: 10, color: '#bbb' }}>
                            {new Date(proj.created_at).toLocaleDateString()}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function QuoteManualEntry({ onAddItem }: { onAddItem: (item: any) => void }) {
  const [itemType, setItemType] = useState<ManualItemType>('window');
  const [m, setM] = useState({ width_inches: 0, height_inches: 0, depth_inches: 0, sill_depth: 0, stack_space: 0 });
  const [opts, setOpts] = useState({ mount_type: 'inside', treatment: '', lining: '', notes: '' });
  const [addedCount, setAddedCount] = useState(0);
  const [showCushionBuilder, setShowCushionBuilder] = useState(false);

  const isWindow = ['window', 'drapery', 'cornice', 'valance', 'roman_shade', 'swag'].includes(itemType);
  const isFurniture = ['sofa', 'loveseat', 'chair', 'sectional', 'ottoman', 'bench', 'headboard', 'banquette'].includes(itemType);
  const isCushion = ['cushion', 'pillow'].includes(itemType);

  const updateM = (key: string, val: string) => {
    setM(prev => ({ ...prev, [key]: parseFloat(val) || 0 }));
  };

  const currentItem = {
    type: itemType,
    subtype: opts.treatment || undefined,
    measurements: { width_inches: m.width_inches, height_inches: m.height_inches, depth_inches: m.depth_inches || undefined },
    treatment: opts.treatment || itemType,
    mount_type: opts.mount_type || undefined,
    lining: opts.lining || undefined,
    description: opts.notes || undefined,
  };

  // Map manual entry types to ITEM_TYPES keys
  const manualToItemType = (t: ManualItemType): string => {
    // Keys now directly match ITEM_TYPES — pass through
    if (ITEM_TYPES.includes(t)) return t;
    return 'sofa_3cushion';
  };

  const addItem = () => {
    if (!m.width_inches && !m.height_inches) return;
    onAddItem({
      type: manualToItemType(itemType),
      width: m.width_inches ? `${m.width_inches}"` : '',
      height: m.height_inches ? `${m.height_inches}"` : '',
      depth: m.depth_inches ? `${m.depth_inches}"` : '',
      description: [
        MANUAL_ITEM_TYPES.find(t => t.key === itemType)?.label || itemType,
        opts.treatment ? opts.treatment.replace(/_/g, ' ') : '',
        opts.mount_type === 'outside' ? 'outside mount' : '',
        opts.lining ? `${opts.lining} lining` : '',
        opts.notes,
      ].filter(Boolean).join(' · '),
    });
    setAddedCount(c => c + 1);
    setM({ width_inches: 0, height_inches: 0, depth_inches: 0, sill_depth: 0, stack_space: 0 });
    setOpts({ mount_type: 'inside', treatment: '', lining: '', notes: '' });
  };

  return (
    <div>
      <div style={{ fontSize: 10, fontWeight: 700, color: '#b8960c', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 12 }}>
        Manual Measurement Entry
      </div>

      {addedCount > 0 && (
        <div style={{ marginBottom: 12, padding: '8px 12px', borderRadius: 8, background: '#f0fdf4', border: '1px solid #bbf7d0', fontSize: 12, fontWeight: 600, color: '#16a34a', display: 'flex', alignItems: 'center', gap: 6 }}>
          <CheckCircle size={14} /> {addedCount} item{addedCount !== 1 ? 's' : ''} added to Room 1
        </div>
      )}

      {/* Item type selector — grouped */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 8 }}>
          What are you measuring?
        </label>
        {MANUAL_ITEM_GROUPS.map(group => (
          <div key={group.group} style={{ marginBottom: 10 }}>
            <div style={{ fontSize: 9, fontWeight: 700, color: group.color, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 5 }}>
              {group.group}
            </div>
            <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
              {group.items.map(t => (
                <button key={t.key} onClick={() => setItemType(t.key)}
                  className="cursor-pointer transition-all"
                  style={{
                    padding: '6px 12px', borderRadius: 8, fontSize: 11, fontWeight: 600,
                    border: `1.5px solid ${itemType === t.key ? group.color : '#ece8e0'}`,
                    background: itemType === t.key ? `${group.color}10` : '#faf9f7',
                    color: itemType === t.key ? group.color : '#777',
                    minHeight: 36,
                  }}>
                  {t.icon} {t.label}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Cushion Builder (full wizard) */}
      {isCushion && (
        <div style={{ marginBottom: 16 }}>
          <button
            onClick={() => setShowCushionBuilder(!showCushionBuilder)}
            className="w-full flex items-center justify-center gap-2 cursor-pointer font-bold transition-all hover:brightness-110"
            style={{
              height: 44, fontSize: 12, borderRadius: 10, marginBottom: showCushionBuilder ? 12 : 0,
              background: showCushionBuilder ? '#7c3aed' : 'linear-gradient(135deg, #7c3aed, #a855f7)',
              color: '#fff', border: 'none', boxShadow: '0 2px 8px #7c3aed30',
            }}>
            <Box size={14} /> {showCushionBuilder ? 'Hide Cushion Builder' : 'Open Cushion Builder (Detailed Specs)'}
          </button>
          {showCushionBuilder && (
            <div style={{ border: '1.5px solid #e9d5ff', borderRadius: 12, padding: 16, background: '#faf5ff' }}>
              <CushionBuilder
                onAddToQuote={(data: any) => {
                  onAddItem({
                    type: 'cushion',
                    width: data.dimensions?.width ? `${data.dimensions.width}"` : '',
                    height: data.dimensions?.height ? `${data.dimensions.height}"` : '',
                    depth: data.dimensions?.depth ? `${data.dimensions.depth}"` : '',
                    description: `${data.cushionType || 'Cushion'} — ${data.shape || ''} ${data.fill || ''} ${data.edge || ''}`.trim(),
                    quantity: data.quantity || 1,
                    cushionData: data,
                  });
                  setAddedCount(c => c + 1);
                  setShowCushionBuilder(false);
                }}
              />
            </div>
          )}
        </div>
      )}

      {/* Quick entry heading for cushions */}
      {isCushion && !showCushionBuilder && (
        <div style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
          Or enter dimensions manually
        </div>
      )}

      {/* Form + live diagram side by side */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 16 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            <label style={{ fontSize: 12 }}>
              <span style={{ color: '#888', fontSize: 11, fontWeight: 600 }}>Width (in)</span>
              <input type="number" value={m.width_inches || ''} onChange={e => updateM('width_inches', e.target.value)}
                placeholder="e.g. 72" style={{ width: '100%', padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 14, marginTop: 4, background: '#faf9f7', minHeight: 44 }} />
            </label>
            <label style={{ fontSize: 12 }}>
              <span style={{ color: '#888', fontSize: 11, fontWeight: 600 }}>Height (in)</span>
              <input type="number" value={m.height_inches || ''} onChange={e => updateM('height_inches', e.target.value)}
                placeholder="e.g. 96" style={{ width: '100%', padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 14, marginTop: 4, background: '#faf9f7', minHeight: 44 }} />
            </label>
          </div>

          {(isFurniture || isCushion) && (
            <label style={{ fontSize: 12 }}>
              <span style={{ color: '#888', fontSize: 11, fontWeight: 600 }}>Depth (in)</span>
              <input type="number" value={m.depth_inches || ''} onChange={e => updateM('depth_inches', e.target.value)}
                style={{ width: '100%', padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 14, marginTop: 4, background: '#faf9f7', minHeight: 44 }} />
            </label>
          )}

          {isWindow && (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                <label style={{ fontSize: 12 }}>
                  <span style={{ color: '#888', fontSize: 11, fontWeight: 600 }}>Mount Type</span>
                  <select value={opts.mount_type} onChange={e => setOpts(p => ({...p, mount_type: e.target.value}))}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 13, marginTop: 4, background: '#faf9f7', minHeight: 44 }}>
                    <option value="inside">Inside Mount</option>
                    <option value="outside">Outside Mount</option>
                  </select>
                </label>
                <label style={{ fontSize: 12 }}>
                  <span style={{ color: '#888', fontSize: 11, fontWeight: 600 }}>Pleat / Style</span>
                  <select value={opts.treatment} onChange={e => setOpts(p => ({...p, treatment: e.target.value}))}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 13, marginTop: 4, background: '#faf9f7', minHeight: 44 }}>
                    <option value="">--</option>
                    <option value="pinch_pleat">Pinch Pleat</option>
                    <option value="french_pleat">French Pleat</option>
                    <option value="euro_pleat">Euro Pleat</option>
                    <option value="cartridge_pleat">Cartridge Pleat</option>
                    <option value="ripplefold">Ripplefold</option>
                    <option value="goblet">Goblet Pleat</option>
                    <option value="box_pleat">Box Pleat</option>
                    <option value="inverted_box">Inverted Box Pleat</option>
                    <option value="rod_pocket">Rod Pocket</option>
                    <option value="tab_top">Tab Top</option>
                    <option value="grommet">Grommet</option>
                    <option value="flat">Flat / No Pleat</option>
                  </select>
                </label>
              </div>
              <label style={{ fontSize: 12 }}>
                <span style={{ color: '#888', fontSize: 11, fontWeight: 600 }}>Lining</span>
                <select value={opts.lining} onChange={e => setOpts(p => ({...p, lining: e.target.value}))}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 13, marginTop: 4, background: '#faf9f7', minHeight: 44 }}>
                  <option value="">None</option>
                  <option value="standard">Standard</option>
                  <option value="blackout">Blackout</option>
                  <option value="thermal">Thermal</option>
                </select>
              </label>
            </>
          )}

          <label style={{ fontSize: 12 }}>
            <span style={{ color: '#888', fontSize: 11, fontWeight: 600 }}>Notes</span>
            <input value={opts.notes} onChange={e => setOpts(p => ({...p, notes: e.target.value}))}
              placeholder="Additional notes..."
              style={{ width: '100%', padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 13, marginTop: 4, background: '#faf9f7', minHeight: 44 }} />
          </label>

          <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
            <button onClick={addItem}
              disabled={!m.width_inches && !m.height_inches}
              className="flex items-center gap-2 cursor-pointer transition-all hover:brightness-110 disabled:opacity-50"
              style={{ flex: 1, padding: '12px 20px', borderRadius: 10, background: '#b8960c', color: '#fff', fontSize: 13, fontWeight: 700, border: 'none', minHeight: 48 }}>
              <CheckCircle size={16} /> Add to Room 1
            </button>
            <button onClick={() => { setM({width_inches:0,height_inches:0,depth_inches:0,sill_depth:0,stack_space:0}); setOpts({mount_type:'inside',treatment:'',lining:'',notes:''}); }}
              className="cursor-pointer transition-all hover:bg-[#f0ede8]"
              style={{ padding: '12px 16px', borderRadius: 10, border: '1px solid #ece8e0', background: '#faf9f7', fontSize: 13, fontWeight: 600, color: '#777', minHeight: 48 }}>
              Clear
            </button>
          </div>
        </div>

        {/* Right: live SVG diagram */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
          {(m.width_inches > 0 || m.height_inches > 0) ? (
            <>
              <div style={{ border: '1px solid #ece8e0', borderRadius: 12, overflow: 'hidden', background: '#fff', padding: 8, width: '100%' }}>
                <MeasurementDiagram item={currentItem as any} width={380} height={300} />
              </div>
              <span style={{ fontSize: 11, color: '#888' }}>Live preview — updates as you type</span>
            </>
          ) : (
            <div style={{ width: '100%', height: 300, borderRadius: 12, border: '2px dashed #ece8e0', background: '#faf9f7', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
              <Ruler size={32} style={{ color: '#ddd' }} />
              <span style={{ fontSize: 13, color: '#aaa', fontWeight: 500 }}>Enter measurements to see diagram</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// ANALYSIS WIZARD — 4-step guided AI analysis flow
// ═══════════════════════════════════════════════════════════════
const WIZARD_STEPS = [
  { id: 1, label: 'Identify', desc: 'Confirm detected items' },
  { id: 2, label: 'Measurements', desc: 'Verify dimensions' },
  { id: 3, label: 'Scope', desc: 'Define the work' },
  { id: 4, label: 'Pricing', desc: 'Review line items' },
];

const WORK_TYPES = [
  'full_reupholster', 'cushion_replacement', 'slipcover', 'recover',
  'repair', 'refinish_frame', 'new_foam_only', 'spring_retying',
];

function AnalysisWizard({ photo, items, rawResponse, analyzing, onUpdateItems, onAddItems, onClose }: {
  photo: PhotoFile | null; items: AnalysisItem[] | null; rawResponse: any;
  analyzing: boolean; onUpdateItems: (items: AnalysisItem[]) => void;
  onAddItems: (items: AnalysisItem[]) => void; onClose: () => void;
}) {
  const [wizStep, setWizStep] = useState(1);
  const [workTypes, setWorkTypes] = useState<Record<number, string>>({});
  const [features, setFeatures] = useState<Record<number, string[]>>({});
  const [pricingPreview, setPricingPreview] = useState<any>(null);
  const [loadingPricing, setLoadingPricing] = useState(false);

  const selectedItems = items?.filter(it => it.checked) || [];

  // Toggle item selection (Step 1)
  const toggleItem = (idx: number) => {
    if (!items) return;
    const copy = [...items];
    copy[idx] = { ...copy[idx], checked: !copy[idx].checked };
    onUpdateItems(copy);
  };

  // Update item field (Step 1-3)
  const updateField = (idx: number, field: keyof AnalysisItem, value: any) => {
    if (!items) return;
    const copy = [...items];
    copy[idx] = { ...copy[idx], [field]: value };
    onUpdateItems(copy);
  };

  // Add a manual item
  const addManualItem = () => {
    if (!items) return;
    onUpdateItems([...items, {
      type: 'accent_chair', description: '', width: '', height: '', depth: '',
      condition: '', checked: true,
    }]);
  };

  // Fetch pricing preview (Step 4)
  const fetchPricing = async () => {
    setLoadingPricing(true);
    try {
      const previewItems = selectedItems.map(it => ({
        name: it.type.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase()),
        type: it.type,
        dimensions: {
          width: parseFloat(it.width || '0') || 0,
          height: parseFloat(it.height || '0') || 0,
          depth: parseFloat(it.depth || '0') || 0,
        },
        quantity: 1,
        construction: '',
        condition: it.condition || '',
        special_features: features[items!.indexOf(it)] || [],
      }));
      const res = await fetch(`${API}/quotes/preview-pricing`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: previewItems, lining: 'standard' }),
      });
      if (res.ok) {
        const data = await res.json();
        setPricingPreview(data.tiers);
      }
    } catch { /* */ }
    setLoadingPricing(false);
  };

  // Auto-fetch pricing when entering Step 4
  const goToStep = (s: number) => {
    setWizStep(s);
    if (s === 4 && !pricingPreview) fetchPricing();
  };

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 1000,
      background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: 24,
    }} onClick={onClose}>
      <div onClick={e => e.stopPropagation()} style={{
        background: '#fff', borderRadius: 16, width: '100%', maxWidth: 720,
        maxHeight: '85vh', overflow: 'hidden', display: 'flex', flexDirection: 'column',
        boxShadow: '0 20px 60px rgba(0,0,0,0.2)',
      }}>
        {/* Header with step indicator */}
        <div style={{ padding: '14px 20px', borderBottom: '1px solid #ece8e0' }}>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Sparkles size={16} style={{ color: '#b8960c' }} />
              <span style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>AI-Guided Analysis</span>
            </div>
            <button onClick={onClose} className="cursor-pointer" style={{ background: 'none', border: 'none', color: '#999', display: 'flex' }}>
              <X size={18} />
            </button>
          </div>
          {!analyzing && items && items.length > 0 && (
            <div className="flex gap-1">
              {WIZARD_STEPS.map(s => (
                <div key={s.id} className="flex-1" style={{
                  padding: '6px 0', textAlign: 'center', fontSize: 10, fontWeight: 700,
                  borderBottom: `3px solid ${wizStep === s.id ? '#b8960c' : wizStep > s.id ? '#16a34a' : '#ece8e0'}`,
                  color: wizStep === s.id ? '#b8960c' : wizStep > s.id ? '#16a34a' : '#bbb',
                }}>
                  {wizStep > s.id ? <Check size={10} style={{ display: 'inline' }} /> : null} {s.label}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
          {/* Photo preview (compact) */}
          {photo && (
            <div style={{ marginBottom: 12, borderRadius: 8, overflow: 'hidden', border: '1px solid #ece8e0', maxHeight: 140 }}>
              <img src={photo.preview} alt="" style={{ width: '100%', maxHeight: 140, objectFit: 'contain', background: '#f5f3ef' }} />
            </div>
          )}

          {analyzing ? (
            <div style={{ textAlign: 'center', padding: '30px 0' }}>
              <Loader2 size={28} className="animate-spin mx-auto" style={{ color: '#b8960c' }} />
              <div style={{ fontSize: 13, fontWeight: 600, color: '#555', marginTop: 10 }}>Analyzing photo...</div>
              <div style={{ fontSize: 11, color: '#aaa', marginTop: 4 }}>Detecting items, dimensions, and condition</div>
            </div>
          ) : items && items.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '24px 0' }}>
              <div style={{ color: '#999', fontSize: 13, marginBottom: 12 }}>No items detected. Add manually:</div>
              <button onClick={addManualItem} className="flex items-center gap-1.5 mx-auto cursor-pointer" style={{ padding: '8px 16px', borderRadius: 8, border: '1.5px solid #b8960c', background: '#fdf8eb', color: '#b8960c', fontSize: 12, fontWeight: 700 }}>
                <Plus size={14} /> Add Item Manually
              </button>
            </div>
          ) : items && items.length > 0 ? (
            <>
              {/* ── STEP 1: IDENTIFY ── */}
              {wizStep === 1 && (
                <div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#1a1a1a', marginBottom: 4 }}>Step 1: Confirm Detected Items</div>
                  <div style={{ fontSize: 11, color: '#777', marginBottom: 12 }}>Check each item the AI found. Correct any misidentifications. Add anything missed.</div>
                  <div className="flex flex-col gap-2">
                    {items.map((item, idx) => (
                      <div key={idx} style={{ padding: '10px 14px', borderRadius: 10, border: `1.5px solid ${item.checked ? '#b8960c' : '#ece8e0'}`, background: item.checked ? '#fdf8eb' : '#faf9f7' }}>
                        <div className="flex items-center gap-2 mb-2">
                          <div onClick={() => toggleItem(idx)} className="cursor-pointer" style={{ width: 20, height: 20, borderRadius: 5, border: `2px solid ${item.checked ? '#b8960c' : '#ddd'}`, background: item.checked ? '#b8960c' : '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                            {item.checked && <Check size={12} style={{ color: '#fff' }} />}
                          </div>
                          <select value={item.type} onChange={e => updateField(idx, 'type', e.target.value)} className="form-input" style={{ flex: 1, fontSize: 12, padding: '5px 8px' }}>
                            {[...UPHOLSTERY_GROUPS, ...DRAPERY_GROUPS].map(g => (
                              <optgroup key={g.label} label={g.label}>
                                {g.items.map(t => <option key={t} value={t}>{formatItemType(t)}</option>)}
                              </optgroup>
                            ))}
                          </select>
                        </div>
                        <input value={item.description} onChange={e => updateField(idx, 'description', e.target.value)} placeholder="Description (style, color, material...)" className="form-input" style={{ width: '100%', fontSize: 11, padding: '5px 8px' }} />
                      </div>
                    ))}
                  </div>
                  <button onClick={addManualItem} className="flex items-center gap-1 mt-3 cursor-pointer" style={{ padding: '6px 12px', borderRadius: 7, border: '1px dashed #ccc', background: 'transparent', fontSize: 11, fontWeight: 600, color: '#777' }}>
                    <Plus size={12} /> Add Item AI Missed
                  </button>
                </div>
              )}

              {/* ── STEP 2: MEASUREMENTS ── */}
              {wizStep === 2 && (
                <div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#1a1a1a', marginBottom: 4 }}>Step 2: Verify Measurements</div>
                  <div style={{ fontSize: 11, color: '#777', marginBottom: 12 }}>Override AI estimates with your tape-measure numbers. All dimensions in inches.</div>
                  <div className="flex flex-col gap-3">
                    {selectedItems.map((item, si) => {
                      const idx = items.indexOf(item);
                      const diagKey = findDiagramMatch(item.type);
                      const dims = {
                        width: parseFloat(item.width || '0') || undefined,
                        height: parseFloat(item.height || '0') || undefined,
                        depth: parseFloat(item.depth || '0') || undefined,
                      };
                      const hasDims = dims.width || dims.height || dims.depth;
                      return (
                        <div key={idx} style={{ padding: '12px 14px', borderRadius: 10, border: '1.5px solid #ece8e0', background: '#faf9f7' }}>
                          <div style={{ fontSize: 12, fontWeight: 700, color: '#1a1a1a', marginBottom: 8 }}>
                            {item.type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                          </div>
                          <div style={{ display: 'flex', gap: 16 }}>
                            <div style={{ flex: 1 }}>
                              <div className="grid grid-cols-3 gap-2">
                                <label style={{ fontSize: 10 }}>
                                  <span style={{ color: '#888', fontWeight: 600 }}>Width (in)</span>
                                  <input value={item.width} onChange={e => updateField(idx, 'width', e.target.value)} placeholder="0" className="form-input" style={{ width: '100%', fontSize: 13, padding: '8px', marginTop: 2 }} />
                                </label>
                                <label style={{ fontSize: 10 }}>
                                  <span style={{ color: '#888', fontWeight: 600 }}>Height (in)</span>
                                  <input value={item.height} onChange={e => updateField(idx, 'height', e.target.value)} placeholder="0" className="form-input" style={{ width: '100%', fontSize: 13, padding: '8px', marginTop: 2 }} />
                                </label>
                                <label style={{ fontSize: 10 }}>
                                  <span style={{ color: '#888', fontWeight: 600 }}>Depth (in)</span>
                                  <input value={item.depth} onChange={e => updateField(idx, 'depth', e.target.value)} placeholder="0" className="form-input" style={{ width: '100%', fontSize: 13, padding: '8px', marginTop: 2 }} />
                                </label>
                              </div>
                              {rawResponse?.confidence && (
                                <div style={{ fontSize: 10, color: '#aaa', marginTop: 4 }}>AI confidence: {rawResponse.confidence}%</div>
                              )}
                            </div>
                            {diagKey && (
                              <div style={{ flexShrink: 0, display: 'flex', alignItems: 'center' }}>
                                <DiagramViewer
                                  diagramKey={diagKey}
                                  dimensions={hasDims ? dims : undefined}
                                  showAnnotations={!!hasDims}
                                />
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* ── STEP 3: CONDITION & SCOPE ── */}
              {wizStep === 3 && (
                <div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#1a1a1a', marginBottom: 4 }}>Step 3: Define the Work</div>
                  <div style={{ fontSize: 11, color: '#777', marginBottom: 12 }}>Select work type and any special features for each item.</div>
                  <div className="flex flex-col gap-3">
                    {selectedItems.map((item, si) => {
                      const idx = items.indexOf(item);
                      const itemFeatures = features[idx] || [];
                      return (
                        <div key={idx} style={{ padding: '12px 14px', borderRadius: 10, border: '1.5px solid #ece8e0', background: '#faf9f7' }}>
                          <div style={{ fontSize: 12, fontWeight: 700, color: '#1a1a1a', marginBottom: 8 }}>
                            {item.type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                            {item.width && <span style={{ fontWeight: 400, color: '#888' }}> ({item.width} x {item.height} x {item.depth})</span>}
                          </div>
                          <div style={{ fontSize: 10, fontWeight: 600, color: '#888', marginBottom: 4 }}>Work Type</div>
                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5 mb-3">
                            {WORK_TYPES.map(w => {
                              const isSelected = (workTypes[idx] || 'full_reupholster') === w;
                              return (
                                <button key={w} onClick={() => setWorkTypes(p => ({ ...p, [idx]: w }))} className="cursor-pointer transition-all text-left" style={{
                                  padding: '6px 10px', borderRadius: 8, fontSize: 10, fontWeight: isSelected ? 700 : 500,
                                  border: `1.5px solid ${isSelected ? '#b8960c' : '#ddd'}`, background: isSelected ? '#fdf8eb' : '#fff', color: isSelected ? '#b8960c' : '#666',
                                }}>
                                  {w.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())}
                                </button>
                              );
                            })}
                          </div>
                          <div className="grid grid-cols-2 gap-2 mb-2">
                            <label style={{ fontSize: 10 }}>
                              <span style={{ color: '#888', fontWeight: 600 }}>Condition</span>
                              <select value={item.condition || 'worn'} onChange={e => updateField(idx, 'condition', e.target.value)} className="form-input" style={{ width: '100%', fontSize: 12, padding: '8px', marginTop: 2 }}>
                                <option value="good">Good</option>
                                <option value="worn">Worn</option>
                                <option value="damaged">Damaged</option>
                                <option value="needs_foam">Needs New Foam</option>
                                <option value="needs_springs">Needs Springs</option>
                              </select>
                            </label>
                          </div>
                          <div style={{ fontSize: 10, fontWeight: 600, color: '#888', marginBottom: 4 }}>Special Features</div>
                          <div className="flex flex-wrap gap-1.5">
                            {['tufting', 'welting', 'nailhead', 'skirt', 'channeling', 'new_foam', 'spring_repair', 'webbing'].map(feat => {
                              const isOn = itemFeatures.includes(feat);
                              return (
                                <button key={feat} onClick={() => {
                                  setFeatures(p => {
                                    const cur = p[idx] || [];
                                    return { ...p, [idx]: isOn ? cur.filter(f => f !== feat) : [...cur, feat] };
                                  });
                                }} className="cursor-pointer transition-all" style={{
                                  padding: '4px 10px', borderRadius: 6, fontSize: 10, fontWeight: 600,
                                  border: `1px solid ${isOn ? '#b8960c' : '#ddd'}`, background: isOn ? '#fdf8eb' : '#fff', color: isOn ? '#b8960c' : '#888',
                                }}>
                                  {feat.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* ── STEP 4: PRICING PREVIEW ── */}
              {wizStep === 4 && (
                <div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#1a1a1a', marginBottom: 4 }}>Step 4: Review Pricing</div>
                  <div style={{ fontSize: 11, color: '#777', marginBottom: 12 }}>3-tier pricing preview based on your approved items and measurements.</div>
                  {loadingPricing ? (
                    <div style={{ textAlign: 'center', padding: '20px 0' }}>
                      <Loader2 size={24} className="animate-spin mx-auto" style={{ color: '#b8960c' }} />
                      <div style={{ fontSize: 12, color: '#777', marginTop: 8 }}>Calculating pricing...</div>
                    </div>
                  ) : pricingPreview ? (
                    <div>
                      <div className="flex gap-2 mb-3">
                        {TIERS.map(t => {
                          const tier = pricingPreview[t.key];
                          if (!tier) return null;
                          return (
                            <div key={t.key} className="flex-1 text-center" style={{ padding: '10px 8px', borderRadius: 10, border: `2px solid ${t.color}`, background: t.bg }}>
                              <div style={{ fontSize: 10, fontWeight: 700, color: '#777' }}>{t.key} · {t.label}</div>
                              <div style={{ fontSize: 20, fontWeight: 700, color: t.color }}>${tier.total?.toLocaleString()}</div>
                              <div style={{ fontSize: 9, color: '#888' }}>Deposit: ${tier.deposit?.toLocaleString()}</div>
                            </div>
                          );
                        })}
                      </div>
                      {/* Show line items for Tier A as reference */}
                      <div style={{ fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase', marginBottom: 4 }}>Tier A Breakdown</div>
                      {pricingPreview.A?.items?.map((item: any, i: number) => (
                        <div key={i} style={{ marginBottom: 6, padding: '8px 10px', borderRadius: 8, border: '1px solid #ece8e0', background: '#faf9f7' }}>
                          <div style={{ fontSize: 11, fontWeight: 700, color: '#1a1a1a', marginBottom: 4 }}>{item.name}</div>
                          {item.line_items?.map((li: any, j: number) => (
                            <div key={j} className="flex justify-between" style={{ fontSize: 10, color: '#555', padding: '1px 0' }}>
                              <span>{li.description}</span>
                              <span style={{ fontWeight: 600 }}>${li.amount?.toFixed(2)}</span>
                            </div>
                          ))}
                          <div className="flex justify-between" style={{ fontSize: 11, fontWeight: 700, color: '#1a1a1a', borderTop: '1px solid #ece8e0', marginTop: 3, paddingTop: 3 }}>
                            <span>Subtotal</span><span>${item.subtotal?.toFixed(2)}</span>
                          </div>
                        </div>
                      ))}
                      <button onClick={fetchPricing} className="flex items-center gap-1 mt-2 cursor-pointer" style={{ padding: '6px 12px', borderRadius: 7, border: '1px solid #ece8e0', background: '#fff', fontSize: 10, fontWeight: 600, color: '#777' }}>
                        <Loader2 size={10} /> Recalculate
                      </button>
                    </div>
                  ) : (
                    <div style={{ textAlign: 'center', color: '#999', fontSize: 12 }}>Failed to load pricing. <button onClick={fetchPricing} className="cursor-pointer" style={{ color: '#b8960c', fontWeight: 600, border: 'none', background: 'none' }}>Retry</button></div>
                  )}
                </div>
              )}
            </>
          ) : null}
        </div>

        {/* Footer with navigation */}
        {items && items.length > 0 && !analyzing && (
          <div style={{ padding: '12px 20px', borderTop: '1px solid #ece8e0', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              {wizStep > 1 && (
                <button onClick={() => setWizStep(s => Math.max(1, s - 1) as any)} className="flex items-center gap-1 cursor-pointer" style={{ padding: '8px 14px', borderRadius: 8, border: '1px solid #ece8e0', background: '#fff', fontSize: 12, fontWeight: 600, color: '#555' }}>
                  <ArrowLeft size={14} /> Back
                </button>
              )}
            </div>
            <div style={{ fontSize: 10, color: '#999' }}>Step {wizStep} of 4 · {selectedItems.length} item{selectedItems.length !== 1 ? 's' : ''}</div>
            <div>
              {wizStep < 4 ? (
                <button onClick={() => goToStep(wizStep + 1 as any)} disabled={selectedItems.length === 0}
                  className="flex items-center gap-1.5 cursor-pointer disabled:opacity-40 transition-all hover:brightness-110"
                  style={{ padding: '8px 16px', borderRadius: 8, border: 'none', background: '#b8960c', color: '#fff', fontSize: 12, fontWeight: 700 }}>
                  Approve & Continue <ArrowRight size={14} />
                </button>
              ) : (
                <button onClick={() => onAddItems(items!)} disabled={selectedItems.length === 0}
                  className="flex items-center gap-1.5 cursor-pointer disabled:opacity-40 transition-all hover:brightness-110"
                  style={{ padding: '8px 16px', borderRadius: 8, border: 'none', background: '#16a34a', color: '#fff', fontSize: 12, fontWeight: 700 }}>
                  <Check size={14} /> Add to Quote
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StepRooms({ rooms, photos, scan3DFiles, apiBase, addRoom, removeRoom, moveRoom, updateRoomName, addItem, moveItem, removeItem, updateItem, onBrowseCatalog, onOpenShapeBuilder, onView3D, onSelectFabric, onAssignPhotoToItem }: {
  rooms: Room[]; photos?: PhotoFile[]; scan3DFiles?: Scan3DFile[]; apiBase?: string;
  addRoom: () => void; removeRoom: (id: string) => void; moveRoom: (id: string, dir: 'up' | 'down') => void; updateRoomName: (id: string, name: string) => void;
  addItem: (roomId: string, category?: ItemCategory) => void; moveItem: (roomId: string, itemId: string, dir: 'up' | 'down') => void; removeItem: (roomId: string, itemId: string) => void;
  updateItem: (roomId: string, itemId: string, field: keyof RoomItem, value: any) => void;
  onBrowseCatalog: (roomId: string) => void;
  onOpenShapeBuilder?: (roomId: string, itemId: string, itemType: string) => void;
  onView3D?: (roomId: string, itemId: string) => void;
  onSelectFabric?: (roomId: string, itemId: string, mode: 'primary' | 'backing') => void;
  onAssignPhotoToItem?: (photoIndex: number, itemId: string, type: 'photo' | 'scan') => void;
}) {
  const [addMenuRoom, setAddMenuRoom] = useState<string | null>(null);
  const [dragOverItem, setDragOverItem] = useState<string | null>(null);

  // Print helper: generates a clean printable view for items
  const printItems = (roomName: string, itemsToPrint: RoomItem[], allRooms?: boolean) => {
    const printWindow = window.open('', '_blank', 'width=900,height=700');
    if (!printWindow) return;

    const buildPanelHtml = (pc: typeof DEFAULT_PANEL_CONFIG | undefined, w: string, h: string) => {
      if (!pc || pc.style === 'flat') return '';
      const bw = parseFloat(w) || 0;
      const bh = parseFloat(h) || 0;
      const styleName = pc.style.replace(/_/g, ' ');

      // Calculate per-panel size
      let panelSize = '';
      if ((pc.style === 'vertical_channels' || pc.style === 'spaced_panels') && pc.panelCount > 0 && bw > 0) {
        const pw = pc.equalDivide
          ? ((bw - pc.gap * (pc.panelCount - 1)) / pc.panelCount).toFixed(1)
          : (pc.panelWidth || 0).toFixed(1);
        panelSize = `Each panel: ${pw}" W × ${bh}" H`;
      } else if (pc.style === 'horizontal_channels' && pc.panelCount > 0 && bh > 0) {
        const ph = pc.equalDivide
          ? ((bh - pc.gap * (pc.panelCount - 1)) / pc.panelCount).toFixed(1)
          : (pc.panelHeight || 0).toFixed(1);
        panelSize = `Each panel: ${bw}" W × ${ph}" H`;
      } else if (pc.style === 'tufted' && pc.rows && pc.columns) {
        const dw = pc.diamondW || (bw / pc.columns);
        const dh = pc.diamondH || (bh / pc.rows);
        panelSize = `Diamond: ${dw.toFixed(1)}" W × ${dh.toFixed(1)}" H`;
      }

      // Fabric estimate
      let fabricEst = '';
      if (pc.panelCount > 0 && bw > 0 && bh > 0 && pc.style !== 'tufted') {
        const totalSqFt = (bw * bh) / 144 * 1.1;
        fabricEst = `Est. fabric: ${totalSqFt.toFixed(1)} sq ft → ${(totalSqFt / 9).toFixed(2)} yd`;
      }

      return `
        <div style="margin-top:12px;padding:10px;background:#fdf8eb;border:1px solid #f0e6c0;border-radius:8px;">
          <div style="font-size:11px;font-weight:700;color:#b8960c;margin-bottom:6px;">Back Panel Configuration</div>
          <table style="font-size:11px;color:#555;border-collapse:collapse;width:100%;">
            <tr><td style="padding:2px 8px 2px 0;font-weight:600;color:#888;">Style</td><td>${styleName}</td></tr>
            ${pc.panelCount ? `<tr><td style="padding:2px 8px 2px 0;font-weight:600;color:#888;"># Panels</td><td>${pc.panelCount}</td></tr>` : ''}
            ${pc.panelWidth ? `<tr><td style="padding:2px 8px 2px 0;font-weight:600;color:#888;">Panel Width</td><td>${pc.panelWidth}"</td></tr>` : ''}
            ${pc.panelHeight ? `<tr><td style="padding:2px 8px 2px 0;font-weight:600;color:#888;">Panel Height</td><td>${pc.panelHeight}"</td></tr>` : ''}
            ${pc.gap ? `<tr><td style="padding:2px 8px 2px 0;font-weight:600;color:#888;">Gap</td><td>${pc.gap}"</td></tr>` : ''}
            ${pc.rows ? `<tr><td style="padding:2px 8px 2px 0;font-weight:600;color:#888;">Grid</td><td>${pc.rows} rows × ${pc.columns} columns</td></tr>` : ''}
            ${pc.tuftType && pc.style === 'tufted' ? `<tr><td style="padding:2px 8px 2px 0;font-weight:600;color:#888;">Tuft Type</td><td>${pc.tuftType}</td></tr>` : ''}
            ${pc.equalDivide ? `<tr><td style="padding:2px 8px 2px 0;font-weight:600;color:#888;">Divide</td><td>Equal</td></tr>` : ''}
            ${panelSize ? `<tr><td style="padding:2px 8px 2px 0;font-weight:600;color:#888;">Panel Size</td><td><strong>${panelSize}</strong></td></tr>` : ''}
            ${fabricEst ? `<tr><td style="padding:2px 8px 2px 0;font-weight:600;color:#888;">Fabric</td><td>${fabricEst}</td></tr>` : ''}
          </table>
        </div>`;
    };

    const itemsHtml = itemsToPrint.map(item => {
      const panelInfo = buildPanelHtml(item.panelConfig, item.width, item.height);

      const fabricInfo = item.fabric ? `
        <div style="font-size:11px;color:#555;margin-top:4px;">
          Fabric: <strong>${item.fabric.name || 'Selected'}</strong>
          ${item.fabricYards ? ` &bull; ${item.fabricYards.toFixed(1)} yd` : ''}
        </div>` : '';

      const backingInfo = item.backingFabric ? `
        <div style="font-size:11px;color:#555;">
          Backing: <strong>${item.backingFabric.name || 'Selected'}</strong>
          ${item.backingYards ? ` &bull; ${item.backingYards.toFixed(1)} yd` : ''}
        </div>` : '';

      return `
        <div style="padding:12px;border:1px solid #ece8e0;border-radius:8px;margin-bottom:12px;background:#faf9f7;">
          <div style="font-size:13px;font-weight:700;color:#1a1a1a;margin-bottom:4px;">${formatItemType(item.type)}</div>
          <div style="display:flex;gap:16px;font-size:11px;color:#666;">
            ${item.width ? `<span>W: <strong>${item.width}"</strong></span>` : ''}
            ${item.height ? `<span>H: <strong>${item.height}"</strong></span>` : ''}
            ${item.depth ? `<span>D: <strong>${item.depth}"</strong></span>` : ''}
            <span>Qty: <strong>${item.quantity}</strong></span>
          </div>
          ${item.notes ? `<div style="font-size:11px;color:#888;margin-top:4px;">${item.notes}</div>` : ''}
          ${fabricInfo}${backingInfo}${panelInfo}
        </div>`;
    }).join('');

    const title = allRooms ? 'All Items — Job Summary' : `${roomName} — Item Details`;
    const roomsHtml = allRooms
      ? rooms.map(r => `
          <h2 style="font-size:15px;font-weight:700;color:#b8960c;margin:16px 0 8px;border-bottom:1px solid #ece8e0;padding-bottom:4px;">${r.name} (${r.items.length} items)</h2>
          ${r.items.map(item => {
            const panelInfo = buildPanelHtml(item.panelConfig, item.width, item.height);
            return `
              <div style="padding:10px;border:1px solid #ece8e0;border-radius:8px;margin-bottom:8px;background:#faf9f7;">
                <div style="font-size:12px;font-weight:700;color:#1a1a1a;">${formatItemType(item.type)}</div>
                <div style="font-size:11px;color:#666;">${[item.width && `W:${item.width}"`, item.height && `H:${item.height}"`, item.depth && `D:${item.depth}"`, `Qty:${item.quantity}`].filter(Boolean).join(' &bull; ')}</div>
                ${item.notes ? `<div style="font-size:10px;color:#888;margin-top:2px;">${item.notes}</div>` : ''}
                ${panelInfo}
              </div>`;
          }).join('')}
        `).join('')
      : itemsHtml;

    printWindow.document.write(`<!DOCTYPE html><html><head>
      <title>${title}</title>
      <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Inter', -apple-system, sans-serif; padding: 24px; color: #1a1a1a; max-width: 800px; margin: 0 auto; }
        .header { border-bottom: 2px solid #b8960c; padding-bottom: 8px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: baseline; }
        .header h1 { font-size: 18px; color: #1a1a1a; }
        .header .date { font-size: 11px; color: #888; }
        @media print { body { padding: 12px; } }
      </style>
    </head><body>
      <div class="header">
        <h1>${title}</h1>
        <span class="date">${new Date().toLocaleDateString()}</span>
      </div>
      ${roomsHtml}
    </body></html>`);
    printWindow.document.close();
    setTimeout(() => printWindow.print(), 300);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div style={{ fontSize: 10, fontWeight: 700, color: '#b8960c', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Rooms & Items
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => printItems('All', rooms.flatMap(r => r.items), true)}
            className="flex items-center gap-1.5 cursor-pointer transition-all hover:bg-[#fdf8eb] hover:border-[#b8960c]"
            style={{ padding: '6px 12px', borderRadius: 8, border: '1.5px solid #ece8e0', background: '#faf9f7', fontSize: 11, fontWeight: 600, color: '#555' }}>
            <Printer size={12} /> Print All
          </button>
          <button onClick={addRoom}
            className="flex items-center gap-1.5 cursor-pointer transition-all hover:bg-[#fdf8eb] hover:border-[#b8960c]"
            style={{ padding: '6px 12px', borderRadius: 8, border: '1.5px solid #ece8e0', background: '#faf9f7', fontSize: 11, fontWeight: 600, color: '#555' }}>
            <Plus size={13} /> Add Room
          </button>
        </div>
      </div>

      <div className="flex flex-col gap-5">
        {rooms.map(room => (
          <div key={room.id} style={{ border: '1.5px solid #ece8e0', borderRadius: 14, overflow: 'hidden' }}>
            {/* Room header */}
            <div className="flex items-center gap-2" style={{ padding: '12px 16px', background: '#f5f3ef', borderBottom: '1px solid #ece8e0' }}>
              {/* Move up/down */}
              <div className="flex flex-col gap-0.5" style={{ flexShrink: 0 }}>
                <button onClick={() => moveRoom(room.id, 'up')} disabled={rooms.indexOf(room) === 0}
                  className="cursor-pointer transition-all hover:bg-[#fdf8eb] disabled:opacity-25 disabled:cursor-default"
                  style={{ width: 22, height: 18, borderRadius: 4, border: '1px solid #ddd', background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 0 }}>
                  <ChevronUp size={12} className="text-[#999]" />
                </button>
                <button onClick={() => moveRoom(room.id, 'down')} disabled={rooms.indexOf(room) === rooms.length - 1}
                  className="cursor-pointer transition-all hover:bg-[#fdf8eb] disabled:opacity-25 disabled:cursor-default"
                  style={{ width: 22, height: 18, borderRadius: 4, border: '1px solid #ddd', background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 0 }}>
                  <ChevronDown size={12} className="text-[#999]" />
                </button>
              </div>
              <input value={room.name} onChange={e => updateRoomName(room.id, e.target.value)}
                style={{ flex: 1, background: 'transparent', border: 'none', outline: 'none', fontSize: 14, fontWeight: 600, color: '#1a1a1a' }} />
              <div style={{ position: 'relative' }}>
                <button onClick={() => setAddMenuRoom(addMenuRoom === room.id ? null : room.id)}
                  className="flex items-center gap-1 cursor-pointer transition-all hover:bg-[#fdf8eb]"
                  style={{ padding: '5px 10px', borderRadius: 7, border: '1px solid #ece8e0', background: '#fff', fontSize: 10, fontWeight: 600, color: '#b8960c' }}>
                  <Plus size={12} /> Item
                </button>
                {addMenuRoom === room.id && (
                  <div style={{
                    position: 'absolute', top: '100%', right: 0, marginTop: 4, zIndex: 20,
                    background: '#fff', border: '1.5px solid #ece8e0', borderRadius: 10, boxShadow: '0 4px 16px rgba(0,0,0,0.1)',
                    overflow: 'hidden', minWidth: 180,
                  }}>
                    <button onClick={() => { addItem(room.id, 'upholstery'); setAddMenuRoom(null); }}
                      className="flex items-center gap-2 w-full cursor-pointer transition-all hover:bg-[#fdf8eb]"
                      style={{ padding: '10px 14px', border: 'none', background: 'none', fontSize: 12, fontWeight: 600, color: '#1a1a1a', borderBottom: '1px solid #f0ede8' }}>
                      <Box size={14} style={{ color: '#b8960c' }} /> Furniture / Upholstery
                    </button>
                    <button onClick={() => { addItem(room.id, 'drapery'); setAddMenuRoom(null); }}
                      className="flex items-center gap-2 w-full cursor-pointer transition-all hover:bg-[#eff6ff]"
                      style={{ padding: '10px 14px', border: 'none', background: 'none', fontSize: 12, fontWeight: 600, color: '#1a1a1a', borderBottom: '1px solid #f0ede8' }}>
                      <Layers size={14} style={{ color: '#2563eb' }} /> Drapery / Window Treatment
                    </button>
                    <button onClick={() => { onBrowseCatalog(room.id); setAddMenuRoom(null); }}
                      className="flex items-center gap-2 w-full cursor-pointer transition-all hover:bg-[#fdf8eb]"
                      style={{ padding: '10px 14px', border: 'none', background: 'none', fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>
                      <BookOpen size={14} style={{ color: '#b8960c' }} /> Browse Catalog
                    </button>
                  </div>
                )}
              </div>
              {rooms.length > 1 && (
                <button onClick={() => removeRoom(room.id)}
                  className="cursor-pointer transition-all hover:bg-[#fef2f2] hover:text-[#dc2626]"
                  style={{ width: 28, height: 28, borderRadius: 7, border: '1px solid #ece8e0', background: '#fff', color: '#ccc', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Trash2 size={13} />
                </button>
              )}
            </div>

            {/* Room photos strip */}
            {(() => {
              const roomPhotos = (photos || []).filter(p => p.assignedRoomId === room.id);
              const roomScans = (scan3DFiles || []).filter(f => f.assignedRoomId === room.id);
              if (!roomPhotos.length && !roomScans.length) return null;
              return (
                <div style={{ padding: '8px 16px', borderBottom: '1px solid #f0ede8', background: '#faf9f7' }}>
                  <div style={{ fontSize: 9, fontWeight: 700, color: '#999', textTransform: 'uppercase', marginBottom: 4 }}>
                    <Camera size={10} style={{ display: 'inline', verticalAlign: '-1px', marginRight: 3 }} />
                    {roomPhotos.length + roomScans.length} photo{roomPhotos.length + roomScans.length !== 1 ? 's' : ''} assigned
                    <span style={{ fontWeight: 400, color: '#bbb', marginLeft: 6 }}>drag onto item to assign</span>
                  </div>
                  <div className="flex gap-2 overflow-x-auto" style={{ paddingBottom: 2 }}>
                    {roomPhotos.map((p, pi) => {
                      const globalIdx = (photos || []).indexOf(p);
                      return (
                      <div key={`p-${pi}`} draggable
                        onDragStart={(e) => {
                          e.dataTransfer.setData('text/plain', JSON.stringify({ type: 'photo', index: globalIdx }));
                          e.dataTransfer.effectAllowed = 'link';
                        }}
                        title={p.assignedItemId ? `Assigned to item` : 'Drag onto an item to assign'}
                        style={{
                          width: 52, height: 52, borderRadius: 6, flexShrink: 0, cursor: 'grab',
                          border: p.assignedItemId ? '2px solid #b8960c' : '1px solid #ece8e0',
                          overflow: 'hidden', background: '#f5f3ef', position: 'relative',
                        }}>
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={p.preview || p.serverUrl || ''} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                          onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                        {p.assignedItemId && (
                          <div style={{ position: 'absolute', bottom: 0, right: 0, width: 14, height: 14, borderRadius: '4px 0 0 0', background: '#b8960c', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <Check size={8} className="text-white" />
                          </div>
                        )}
                      </div>
                      );
                    })}
                    {roomScans.map((f, si) => {
                      const globalIdx = (scan3DFiles || []).indexOf(f);
                      return (
                      <div key={`s-${si}`} draggable
                        onDragStart={(e) => {
                          e.dataTransfer.setData('text/plain', JSON.stringify({ type: 'scan', index: globalIdx }));
                          e.dataTransfer.effectAllowed = 'link';
                        }}
                        title={f.assignedItemId ? 'Assigned to item' : 'Drag onto an item to assign'}
                        style={{
                          width: 52, height: 52, borderRadius: 6, flexShrink: 0, cursor: 'grab',
                          border: f.assignedItemId ? '2px solid #16a34a' : '1px solid #bbf7d0',
                          overflow: 'hidden', background: '#f0fdf4',
                          display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative',
                        }}>
                        <Box size={18} className="text-[#16a34a]" />
                        {f.assignedItemId && (
                          <div style={{ position: 'absolute', bottom: 0, right: 0, width: 14, height: 14, borderRadius: '4px 0 0 0', background: '#16a34a', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <Check size={8} className="text-white" />
                          </div>
                        )}
                      </div>
                      );
                    })}
                  </div>
                </div>
              );
            })()}

            {/* Items */}
            <div style={{ padding: room.items.length ? '12px 16px' : '0' }}>
              {room.items.length === 0 && (
                <div style={{ padding: '20px 16px', textAlign: 'center', fontSize: 12, color: '#bbb' }}>
                  No items yet — click "+ Item" to add furniture or drapery
                </div>
              )}
              {room.items.map((item, idx) => {
                const cat = getItemCategory(item.type);
                const typeGroups = cat === 'drapery' ? DRAPERY_GROUPS : UPHOLSTERY_GROUPS;
                const catColor = cat === 'drapery' ? '#2563eb' : '#b8960c';
                const catLabel = cat === 'drapery' ? 'DRAPERY' : 'UPHOLSTERY';
                const diagramMatch = DIAGRAM_MAP[item.type] ? item.type : findDiagramMatch(item.type);
                return (
                <div key={item.id} className="flex items-start gap-2"
                  onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = 'link'; }}
                  onDragEnter={() => setDragOverItem(item.id)}
                  onDragLeave={(e) => { if (!e.currentTarget.contains(e.relatedTarget as Node)) setDragOverItem(null); }}
                  onDrop={(e) => {
                    e.preventDefault();
                    setDragOverItem(null);
                    try {
                      const data = JSON.parse(e.dataTransfer.getData('text/plain'));
                      onAssignPhotoToItem?.(data.index, item.id, data.type);
                    } catch {}
                  }}
                  style={{
                    marginBottom: idx < room.items.length - 1 ? 10 : 0,
                    paddingBottom: idx < room.items.length - 1 ? 10 : 0,
                    borderBottom: idx < room.items.length - 1 ? '1px solid #f0ede8' : 'none',
                    borderRadius: 8, padding: '6px 4px',
                    outline: dragOverItem === item.id ? '2px dashed #b8960c' : 'none',
                    background: dragOverItem === item.id ? '#fdf8eb' : 'transparent',
                    transition: 'outline 0.15s, background 0.15s',
                  }}>
                  {/* Item-assigned photos */}
                  {(() => {
                    const itemPhotos = (photos || []).filter(p => p.assignedItemId === item.id);
                    const itemScans = (scan3DFiles || []).filter(f => f.assignedItemId === item.id);
                    if (!itemPhotos.length && !itemScans.length) return null;
                    return (
                      <div className="flex flex-col gap-1" style={{ flexShrink: 0, marginTop: 10 }}>
                        {itemPhotos.map((p, pi) => (
                          <div key={`ip-${pi}`} style={{
                            width: 36, height: 36, borderRadius: 5, overflow: 'hidden',
                            border: '2px solid #b8960c',
                          }}>
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img src={p.preview || p.serverUrl || ''} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                          </div>
                        ))}
                        {itemScans.map((f, si) => (
                          <div key={`is-${si}`} style={{
                            width: 36, height: 36, borderRadius: 5,
                            border: '2px solid #16a34a', background: '#f0fdf4',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                          }}>
                            <Box size={14} className="text-[#16a34a]" />
                          </div>
                        ))}
                      </div>
                    );
                  })()}
                  {/* Move item up/down */}
                  {room.items.length > 1 && (
                    <div className="flex flex-col gap-0.5" style={{ flexShrink: 0, marginTop: 14 }}>
                      <button onClick={() => moveItem(room.id, item.id, 'up')} disabled={idx === 0}
                        className="cursor-pointer transition-all hover:bg-[#fdf8eb] disabled:opacity-20 disabled:cursor-default"
                        style={{ width: 18, height: 14, borderRadius: 3, border: '1px solid #eee', background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 0 }}>
                        <ChevronUp size={10} className="text-[#aaa]" />
                      </button>
                      <button onClick={() => moveItem(room.id, item.id, 'down')} disabled={idx === room.items.length - 1}
                        className="cursor-pointer transition-all hover:bg-[#fdf8eb] disabled:opacity-20 disabled:cursor-default"
                        style={{ width: 18, height: 14, borderRadius: 3, border: '1px solid #eee', background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 0 }}>
                        <ChevronDown size={10} className="text-[#aaa]" />
                      </button>
                    </div>
                  )}
                  {/* Diagram thumbnail */}
                  {diagramMatch && DIAGRAM_MAP[diagramMatch] && (
                    <div style={{ width: 52, height: 52, borderRadius: 8, border: '1px solid #ece8e0', background: '#faf9f7', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: 12, overflow: 'hidden' }}>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={DIAGRAM_MAP[diagramMatch].svg} alt="" style={{ maxWidth: 44, maxHeight: 44, objectFit: 'contain', opacity: 0.7 }}
                        onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                    </div>
                  )}
                  <div className="flex-1 grid grid-cols-6 gap-2">
                    {/* Category badge + Type */}
                    <div className="col-span-2">
                      <div className="flex items-center gap-1.5" style={{ marginBottom: 2 }}>
                        <span style={{ fontSize: 8, fontWeight: 700, color: catColor, background: `${catColor}12`, padding: '1px 5px', borderRadius: 4 }}>{catLabel}</span>
                        <label style={{ fontSize: 9, fontWeight: 600, color: '#999' }}>TYPE</label>
                      </div>
                      <select value={item.type} onChange={e => updateItem(room.id, item.id, 'type', e.target.value)}
                        className="form-input" style={{ width: '100%', fontSize: 11, padding: '6px 8px' }}>
                        {typeGroups.map(g => (
                          <optgroup key={g.label} label={g.label}>
                            {g.items.map(t => (
                              <option key={t} value={t}>{formatItemType(t)}</option>
                            ))}
                          </optgroup>
                        ))}
                      </select>
                    </div>
                    {/* W */}
                    <div>
                      <label style={{ fontSize: 9, fontWeight: 600, color: '#999', display: 'block', marginBottom: 2 }}>W</label>
                      <input value={item.width} onChange={e => updateItem(room.id, item.id, 'width', e.target.value)}
                        placeholder={cat === 'drapery' ? '48"' : '72"'} className="form-input" style={{ width: '100%', fontSize: 11, padding: '6px 8px' }} />
                    </div>
                    {/* H */}
                    <div>
                      <label style={{ fontSize: 9, fontWeight: 600, color: '#999', display: 'block', marginBottom: 2 }}>H</label>
                      <input value={item.height} onChange={e => updateItem(room.id, item.id, 'height', e.target.value)}
                        placeholder={cat === 'drapery' ? '84"' : '36"'} className="form-input" style={{ width: '100%', fontSize: 11, padding: '6px 8px' }} />
                    </div>
                    {/* D */}
                    <div>
                      <label style={{ fontSize: 9, fontWeight: 600, color: '#999', display: 'block', marginBottom: 2 }}>{cat === 'drapery' ? 'PROJ' : 'D'}</label>
                      <input value={item.depth} onChange={e => updateItem(room.id, item.id, 'depth', e.target.value)}
                        placeholder={cat === 'drapery' ? '6"' : '32"'} className="form-input" style={{ width: '100%', fontSize: 11, padding: '6px 8px' }} />
                    </div>
                    {/* Qty */}
                    <div>
                      <label style={{ fontSize: 9, fontWeight: 600, color: '#999', display: 'block', marginBottom: 2 }}>QTY</label>
                      <input type="number" min={1} value={item.quantity}
                        onChange={e => updateItem(room.id, item.id, 'quantity', Math.max(1, parseInt(e.target.value) || 1))}
                        className="form-input" style={{ width: '100%', fontSize: 11, padding: '6px 8px' }} />
                    </div>
                    {/* Notes row + Shape Builder / 3D Viewer buttons */}
                    <div className={(isBenchType(item.type) || item.notes?.startsWith('3D Scan:')) ? 'col-span-4' : 'col-span-5'}>
                      <input value={item.notes} onChange={e => updateItem(room.id, item.id, 'notes', e.target.value)}
                        placeholder={cat === 'drapery' ? 'Notes (fabric, mount type, motorization...)' : 'Notes (fabric preference, condition, existing foam...)'}
                        className="form-input" style={{ width: '100%', fontSize: 11, padding: '6px 8px' }} />
                    </div>
                    {item.notes?.startsWith('3D Scan:') && (
                      <div className="col-span-1">
                        <button
                          onClick={() => onView3D?.(room.id, item.id)}
                          className="flex items-center gap-1 cursor-pointer transition-all hover:bg-[#f0fdf4] hover:border-[#16a34a] w-full justify-center"
                          style={{ padding: '5px 6px', borderRadius: 7, border: '1.5px solid #bbf7d0', background: '#f0fdf4', fontSize: 9, fontWeight: 700, color: '#16a34a' }}
                          title="Open 3D Viewer with measuring tools"
                        >
                          <Box size={12} /> View 3D
                        </button>
                      </div>
                    )}
                    {isBenchType(item.type) && !item.notes?.startsWith('3D Scan:') && (
                      <div className="col-span-1">
                        <button
                          onClick={() => onOpenShapeBuilder?.(room.id, item.id, item.type)}
                          className="flex items-center gap-1 cursor-pointer transition-all hover:bg-[#fdf8eb] hover:border-[#b8960c] w-full justify-center"
                          style={{ padding: '5px 6px', borderRadius: 7, border: '1.5px solid #ece8e0', background: '#faf9f7', fontSize: 9, fontWeight: 700, color: '#b8960c' }}
                          title="Open Custom Shape Builder — configure multi-segment dimensions, seatbacks, and cushion layout"
                        >
                          <Ruler size={12} /> Shape Builder
                        </button>
                      </div>
                    )}
                    {/* Fabric selection row */}
                    <div className="col-span-6" style={{ marginTop: 4 }}>
                      <div className="flex flex-wrap items-center gap-2">
                        {!item.fabric ? (
                          <button onClick={() => onSelectFabric?.(room.id, item.id, 'primary')}
                            className="cursor-pointer transition-all hover:bg-[#fdf8eb] hover:border-[#b8960c]"
                            style={{
                              padding: '5px 12px', borderRadius: 7,
                              border: '1.5px solid #ece8e0', background: '#faf9f7',
                              fontSize: 10, fontWeight: 700, color: '#b8960c',
                              minHeight: 32,
                            }}>
                            Select Fabric
                          </button>
                        ) : (
                          <>
                            {/* Compact fabric card */}
                            <div style={{
                              display: 'flex', alignItems: 'center', gap: 6,
                              padding: '4px 10px 4px 4px', borderRadius: 8,
                              border: '1.5px solid #d4d0c8', background: '#faf9f7',
                            }}>
                              <div style={{
                                width: 24, height: 24, borderRadius: 5, flexShrink: 0,
                                background: '#ece8e0',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                              }}>
                                <span style={{ fontSize: 10 }}>F</span>
                              </div>
                              <span style={{ fontSize: 11, fontWeight: 600, color: '#1a1a1a' }}>
                                {item.fabric.code} {item.fabric.color_pattern || ''}
                              </span>
                              {item.fabric.cost_per_yard > 0 && (
                                <span style={{ fontSize: 10, color: '#888' }}>
                                  ${item.fabric.cost_per_yard.toFixed(2)}/yd
                                </span>
                              )}
                              <button onClick={() => { updateItem(room.id, item.id, 'fabric', null); updateItem(room.id, item.id, 'fabricYards', undefined); updateItem(room.id, item.id, 'fabricYardsOverride', null); }}
                                className="cursor-pointer transition-all hover:bg-[#fef2f2]"
                                style={{ width: 18, height: 18, borderRadius: 4, border: '1px solid #ece8e0', background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', marginLeft: 2 }}>
                                <X size={10} className="text-[#999]" />
                              </button>
                            </div>
                            {/* Select Backing button */}
                            {!item.backingFabric ? (
                              <button onClick={() => onSelectFabric?.(room.id, item.id, 'backing')}
                                className="cursor-pointer transition-all hover:bg-[#eff6ff] hover:border-[#2563eb]"
                                style={{
                                  padding: '5px 10px', borderRadius: 7,
                                  border: '1.5px solid #dbeafe', background: '#f0f7ff',
                                  fontSize: 10, fontWeight: 600, color: '#2563eb',
                                  minHeight: 32,
                                }}>
                                + Backing
                              </button>
                            ) : (
                              <div style={{
                                display: 'flex', alignItems: 'center', gap: 6,
                                padding: '4px 10px 4px 4px', borderRadius: 8,
                                border: '1.5px solid #c7d2fe', background: '#f0f7ff',
                              }}>
                                <div style={{
                                  width: 24, height: 24, borderRadius: 5, flexShrink: 0,
                                  background: '#dbeafe',
                                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                                }}>
                                  <span style={{ fontSize: 10, color: '#2563eb' }}>B</span>
                                </div>
                                <span style={{ fontSize: 11, fontWeight: 600, color: '#1a1a1a' }}>
                                  {item.backingFabric.code} {item.backingFabric.color_pattern || ''}
                                </span>
                                <button onClick={() => { updateItem(room.id, item.id, 'backingFabric', null); updateItem(room.id, item.id, 'backingYards', undefined); updateItem(room.id, item.id, 'backingYardsOverride', null); }}
                                  className="cursor-pointer transition-all hover:bg-[#fef2f2]"
                                  style={{ width: 18, height: 18, borderRadius: 4, border: '1px solid #c7d2fe', background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', marginLeft: 2 }}>
                                  <X size={10} className="text-[#999]" />
                                </button>
                              </div>
                            )}
                          </>
                        )}
                      </div>
                      {/* Yardage calculators */}
                      {item.fabric && (
                        <YardageCalculator
                          fabric={item.fabric}
                          itemWidth={item.width} itemHeight={item.height} itemDepth={item.depth}
                          quantity={item.quantity}
                          yardsOverride={item.fabricYardsOverride || null}
                          onYardsCalculated={(y) => updateItem(room.id, item.id, 'fabricYards', y)}
                          onYardsOverride={(y) => updateItem(room.id, item.id, 'fabricYardsOverride', y)}
                        />
                      )}
                      {item.backingFabric && (
                        <YardageCalculator
                          fabric={item.backingFabric}
                          itemWidth={item.width} itemHeight={item.height} itemDepth={item.depth}
                          quantity={item.quantity}
                          yardsOverride={item.backingYardsOverride || null}
                          onYardsCalculated={(y) => updateItem(room.id, item.id, 'backingYards', y)}
                          onYardsOverride={(y) => updateItem(room.id, item.id, 'backingYardsOverride', y)}
                        />
                      )}
                    </div>
                  </div>
                  {/* Panel Configurator for items with backs */}
                  {(isBenchType(item.type) || ['sofa', 'loveseat', 'sectional', 'sectional_l', 'sectional_u', 'headboard', 'headboard_custom', 'banquette'].some(t => item.type.startsWith(t) || item.type === t)) && (
                    <div style={{ gridColumn: '1 / -1', marginTop: -4 }}>
                      <PanelConfigurator
                        backWidth={parseFloat(item.width) || 0}
                        backHeight={parseFloat(item.height) || 0}
                        config={item.panelConfig || DEFAULT_PANEL_CONFIG}
                        onChange={(pc) => updateItem(room.id, item.id, 'panelConfig', pc)}
                        itemType={item.type}
                        itemLabel={`${formatItemType(item.type)} — ${room.name}`}
                      />
                    </div>
                  )}
                  <div className="flex flex-col gap-1 mt-4" style={{ flexShrink: 0 }}>
                    <button onClick={() => printItems(room.name, [item])}
                      className="cursor-pointer transition-all hover:bg-[#fdf8eb] hover:text-[#b8960c]"
                      style={{ width: 28, height: 28, borderRadius: 7, border: '1px solid #ece8e0', background: '#fff', color: '#bbb', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                      title="Print this item">
                      <Printer size={12} />
                    </button>
                    <button onClick={() => removeItem(room.id, item.id)}
                      className="cursor-pointer transition-all hover:bg-[#fef2f2] hover:text-[#dc2626]"
                      style={{ width: 28, height: 28, borderRadius: 7, border: '1px solid #ece8e0', background: '#fff', color: '#ccc', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function StepOptions({ options, setOptions, rooms, hardwareConfig, setHardwareConfig }: {
  options: QuoteOptions; setOptions: (o: QuoteOptions) => void; rooms: Room[];
  hardwareConfig?: Record<string, any>; setHardwareConfig?: (c: Record<string, any>) => void;
}) {
  const toggle = (key: keyof QuoteOptions) => setOptions({ ...options, [key]: !options[key] });

  // Determine which categories are present in the quote
  const allItems = rooms.flatMap(r => r.items);
  const hasUpholstery = allItems.some(it => getItemCategory(it.type) === 'upholstery');
  const hasDrapery = allItems.some(it => getItemCategory(it.type) === 'drapery');

  const checkBtn = (key: keyof QuoteOptions, label: string, accent = '#b8960c') => {
    const isChecked = options[key] as boolean;
    return (
      <button key={key} onClick={() => toggle(key)}
        className="flex items-center gap-2 cursor-pointer transition-all text-left"
        style={{
          padding: '10px 12px', borderRadius: 10,
          border: `1.5px solid ${isChecked ? accent : '#ece8e0'}`,
          background: isChecked ? `${accent}10` : '#faf9f7',
          fontSize: 12, fontWeight: isChecked ? 600 : 400,
          color: isChecked ? accent : '#777',
        }}>
        <div style={{
          width: 18, height: 18, borderRadius: 5, flexShrink: 0,
          border: `2px solid ${isChecked ? accent : '#ddd'}`,
          background: isChecked ? accent : '#fff',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          {isChecked && <Check size={12} className="text-white" />}
        </div>
        {label}
      </button>
    );
  };

  const sel = (label: string, key: keyof QuoteOptions, opts: [string, string][], accent = '#b8960c') => (
    <div key={key}>
      <label style={{ fontSize: 11, fontWeight: 600, color: '#555', display: 'block', marginBottom: 4 }}>{label}</label>
      <select value={String(options[key] || '')}
        onChange={e => setOptions({ ...options, [key]: key === 'foamThickness' ? Number(e.target.value) : e.target.value })}
        className="form-input" style={{ width: '100%', fontSize: 12, padding: '8px 10px', borderColor: accent + '40' }}>
        {opts.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
    </div>
  );

  return (
    <div>
      <div style={{ fontSize: 10, fontWeight: 700, color: '#b8960c', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 16 }}>
        Quote Options
      </div>

      {/* Fabric Grade — shared */}
      <div style={{ marginBottom: 20 }}>
        <label style={{ fontSize: 12, fontWeight: 600, color: '#555', display: 'block', marginBottom: 8 }}>Fabric Grade</label>
        <div className="flex gap-2">
          {(['A', 'B', 'C'] as const).map(g => {
            const isActive = options.fabricGrade === g;
            const labels: Record<string, string> = { A: 'Standard', B: 'Designer', C: 'Premium' };
            const colors: Record<string, string> = { A: '#16a34a', B: '#b8960c', C: '#7c3aed' };
            return (
              <button key={g} onClick={() => setOptions({ ...options, fabricGrade: g })}
                className="flex-1 cursor-pointer transition-all"
                style={{
                  padding: '10px 8px', borderRadius: 10, textAlign: 'center', fontSize: 12, fontWeight: 600,
                  border: `2px solid ${isActive ? colors[g] : '#ece8e0'}`,
                  background: isActive ? `${colors[g]}10` : '#faf9f7',
                  color: isActive ? colors[g] : '#777',
                }}>
                Grade {g}<br /><span style={{ fontSize: 10, fontWeight: 400 }}>{labels[g]}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Upholstery Options */}
      {hasUpholstery && (
        <div style={{ marginBottom: 20, padding: 16, borderRadius: 12, border: '1.5px solid #ece8e0', background: '#fdfcfa' }}>
          <div className="flex items-center gap-2 mb-3">
            <Box size={14} style={{ color: '#b8960c' }} />
            <span style={{ fontSize: 11, fontWeight: 700, color: '#b8960c', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Upholstery Options</span>
          </div>
          <div className="grid grid-cols-2 gap-4 mb-3">
            {sel('Foam Type', 'foamType', [['high_density','High Density'],['medium_density','Medium Density'],['down_wrap','Down Wrap'],['down_blend','Down Blend'],['spring_down','Spring Down'],['memory_foam','Memory Foam'],['latex','Latex'],['reuse','Reuse Existing']])}
            {sel('Foam Thickness', 'foamThickness', [['1','1"'],['2','2"'],['3','3"'],['4','4"'],['5','5"'],['6','6"']])}
            {sel('Tufting', 'tufting', [['none','None'],['diamond','Diamond'],['biscuit','Biscuit'],['channel_vertical','Channel (Vertical)'],['channel_horizontal','Channel (Horizontal)'],['button','Button'],['blind_button','Blind Button'],['deep_button','Deep Button']])}
            {sel('Welting', 'welting', [['self_welt','Self Welt'],['contrast_welt','Contrast Welt'],['double_welt','Double Welt'],['cord','Cord'],['micro_welt','Micro Welt'],['none','None']])}
            {sel('Nailhead Finish', 'nailheadFinish', [['none','None'],['standard','Standard'],['french_natural','French Natural'],['antique_brass','Antique Brass'],['nickel','Nickel'],['pewter','Pewter'],['black','Black'],['gunmetal','Gunmetal'],['gold','Gold']])}
            {sel('Nailhead Spacing', 'nailheadSpacing', [['standard','Standard'],['close','Close'],['every_other','Every Other'],['custom_pattern','Custom Pattern']])}
            {sel('Skirt', 'skirtStyle', [['none','None'],['kick_pleat','Kick Pleat'],['box_pleat','Box Pleat'],['gathered','Gathered'],['tailored','Tailored'],['bullion_fringe','Bullion Fringe'],['waterfall','Waterfall']])}
            {sel('Springs', 'springs', [['eight_way_hand_tied','8-Way Hand Tied'],['sinuous_zigzag','Sinuous/Zigzag'],['no_sag','No-Sag'],['pocket_coil','Pocket Coil']])}
            {sel('Arm Style', 'armStyle', [['track','Track'],['english','English'],['rolled','Rolled'],['flared','Flared'],['slope','Slope'],['pad','Pad'],['recessed','Recessed']])}
            {sel('Back Style', 'backStyle', [['tight','Tight'],['loose_cushion','Loose Cushion'],['tufted','Tufted'],['channeled','Channeled'],['pillow_back','Pillow Back']])}
            {sel('Leg Style', 'legStyle', [['exposed_wood','Exposed Wood'],['exposed_metal','Exposed Metal'],['exposed_acrylic','Exposed Acrylic'],['skirted','Skirted'],['bun_feet','Bun Feet'],['turned','Turned'],['tapered','Tapered'],['cabriole','Cabriole']])}
            {sel('Panel Mounting', 'panelMounting', [['french_cleat','French Cleat'],['z_clip','Z-Clip'],['velcro','Velcro'],['direct_mount','Direct Mount']])}
          </div>
        </div>
      )}

      {/* Drapery Options */}
      {hasDrapery && (
        <div style={{ marginBottom: 20, padding: 16, borderRadius: 12, border: '1.5px solid #d6e4f0', background: '#fafcff' }}>
          <div className="flex items-center gap-2 mb-3">
            <Layers size={14} style={{ color: '#2563eb' }} />
            <span style={{ fontSize: 11, fontWeight: 700, color: '#2563eb', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Drapery & Window Treatment Options</span>
          </div>
          <div className="grid grid-cols-2 gap-4 mb-3">
            {sel('Lining', 'liningType', [['unlined','Unlined'],['standard_poly_cotton','Standard Poly-Cotton'],['blackout','Blackout'],['interlining_bump','Interlining (Bump)'],['interlining_domette','Interlining (Domette)'],['interlining_flannel','Interlining (Flannel)'],['thermal','Thermal'],['sheer','Sheer'],['privacy','Privacy']], '#2563eb')}
            {sel('Fullness', 'fullness', [['2x','2x Standard'],['2.5x','2.5x (Recommended)'],['3x','3x Full'],['custom','Custom']], '#2563eb')}
            {sel('Hardware', 'hardwareType', [['','Not Selected'],['traverse_rod','Traverse Rod'],['decorative_rod_wood','Decorative Rod (Wood)'],['decorative_rod_metal','Decorative Rod (Metal)'],['decorative_rod_acrylic','Decorative Rod (Acrylic)'],['ripplefold_track_silent_gliss','Ripplefold Track (Silent Gliss)'],['ripplefold_track_kirsch','Ripplefold Track (Kirsch)'],['motorized_somfy','Motorized (Somfy)'],['motorized_lutron','Motorized (Lutron)'],['motorized_hunter_douglas','Motorized (Hunter Douglas)'],['ceiling_mount','Ceiling Mount'],['double_rod','Double Rod'],['tension_rod','Tension Rod']], '#2563eb')}
            {sel('Finial', 'finialStyle', [['','None'],['ball','Ball'],['spear','Spear'],['fleur_de_lis','Fleur-de-Lis'],['crystal','Crystal'],['urn','Urn'],['cage','Cage'],['leaf','Leaf'],['scroll','Scroll'],['square','Square'],['custom','Custom']], '#2563eb')}
            {sel('Leading Edge', 'leadingEdge', [['plain','Plain'],['contrast_banding','Contrast Banding'],['gimp','Gimp'],['braid','Braid'],['fringe','Fringe'],['tassel_fringe','Tassel Fringe'],['beaded','Beaded'],['brush_fringe','Brush Fringe']], '#2563eb')}
            {sel('Bottom Hem', 'bottomHem', [['double_fold_4in','Double Fold 4"'],['double_fold_6in','Double Fold 6"'],['double_fold_8in','Double Fold 8"'],['weighted','Weighted'],['chain_weighted','Chain Weighted'],['horsehair','Horsehair']], '#2563eb')}
            {sel('Returns', 'returnSize', [['standard_3_5in','Standard 3.5"'],['extended_6in','Extended 6"'],['extended_8in','Extended 8"'],['custom','Custom']], '#2563eb')}
            {sel('Stacking', 'stacking', [['left','Stack Left'],['right','Stack Right'],['split','Split (Center Open)'],['one_way_left','One-Way Left'],['one_way_right','One-Way Right']], '#2563eb')}
            {sel('Tiebacks', 'tieback', [['none','None'],['fabric','Fabric'],['rope','Rope'],['tassel','Tassel'],['medallion','Medallion'],['magnetic','Magnetic'],['holdback','Holdback']], '#2563eb')}
            {sel('Lift System', 'liftSystem', [['cordless','Cordless'],['cord_lock','Cord Lock'],['continuous_cord_loop','Continuous Loop'],['motorized_somfy','Motorized (Somfy)'],['motorized_lutron','Motorized (Lutron)'],['top_down_bottom_up','Top-Down/Bottom-Up'],['day_night_dual','Day/Night Dual']], '#2563eb')}
          </div>
          <div className="grid grid-cols-2 gap-2">
            {checkBtn('contrastPiping', 'Contrast Piping', '#2563eb')}
            {checkBtn('patternMatch', 'Pattern Match', '#2563eb')}
            {checkBtn('installationIncluded', 'Include Installation', '#2563eb')}
          </div>
          {/* Drapery Hardware Configuration Module */}
          {setHardwareConfig && (
            <div style={{ marginTop: 16 }}>
              <DraperyHardwareModule
                config={hardwareConfig || {}}
                onChange={(cfg) => setHardwareConfig(cfg)}
              />
            </div>
          )}
        </div>
      )}

      {/* Rush / Delivery — shared */}
      <div className="flex gap-3">
        <button onClick={() => toggle('rushOrder')}
          className="flex-1 flex items-center gap-2 cursor-pointer transition-all"
          style={{
            padding: '12px 16px', borderRadius: 10,
            border: `1.5px solid ${options.rushOrder ? '#dc2626' : '#ece8e0'}`,
            background: options.rushOrder ? '#fef2f2' : '#faf9f7',
            fontSize: 12, fontWeight: options.rushOrder ? 600 : 400,
            color: options.rushOrder ? '#dc2626' : '#777',
          }}>
          <div style={{
            width: 18, height: 18, borderRadius: 5,
            border: `2px solid ${options.rushOrder ? '#dc2626' : '#ddd'}`,
            background: options.rushOrder ? '#dc2626' : '#fff',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            {options.rushOrder && <Check size={12} className="text-white" />}
          </div>
          Rush Order (+20%)
        </button>
        <button onClick={() => toggle('delivery')}
          className="flex-1 flex items-center gap-2 cursor-pointer transition-all"
          style={{
            padding: '12px 16px', borderRadius: 10,
            border: `1.5px solid ${options.delivery ? '#2563eb' : '#ece8e0'}`,
            background: options.delivery ? '#eff6ff' : '#faf9f7',
            fontSize: 12, fontWeight: options.delivery ? 600 : 400,
            color: options.delivery ? '#2563eb' : '#777',
          }}>
          <div style={{
            width: 18, height: 18, borderRadius: 5,
            border: `2px solid ${options.delivery ? '#2563eb' : '#ddd'}`,
            background: options.delivery ? '#2563eb' : '#fff',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            {options.delivery && <Check size={12} className="text-white" />}
          </div>
          Include Delivery
        </button>
      </div>
    </div>
  );
}

function StepReview({ customer, photos, rooms, options, totalItems }: {
  customer: CustomerInfo; photos: PhotoFile[]; rooms: Room[]; options: QuoteOptions; totalItems: number;
}) {
  const allItems = rooms.flatMap(r => r.items);
  const hasUpholstery = allItems.some(it => getItemCategory(it.type) === 'upholstery');
  const hasDrapery = allItems.some(it => getItemCategory(it.type) === 'drapery');
  const fmt = (v: string) => v.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  const features = [
    hasUpholstery && options.foamType && `Foam: ${fmt(options.foamType)}`,
    hasUpholstery && options.foamThickness && `${options.foamThickness}" thick`,
    hasUpholstery && options.tufting !== 'none' && `Tufting: ${fmt(options.tufting)}`,
    hasUpholstery && options.welting !== 'none' && `Welting: ${fmt(options.welting)}`,
    hasUpholstery && options.nailheadFinish !== 'none' && `Nailhead: ${fmt(options.nailheadFinish)}`,
    hasUpholstery && options.skirtStyle !== 'none' && `Skirt: ${fmt(options.skirtStyle)}`,
    hasDrapery && options.fullness && `Fullness: ${options.fullness}`,
    hasDrapery && options.leadingEdge !== 'plain' && `Edge: ${fmt(options.leadingEdge)}`,
    hasDrapery && options.hardwareType && `Hardware: ${fmt(options.hardwareType)}`,
    options.contrastPiping && 'Contrast Piping',
    options.patternMatch && 'Pattern Match',
    options.installationIncluded && 'Installation',
    options.monogram && 'Monogram',
  ].filter(Boolean);

  return (
    <div>
      <div style={{ fontSize: 10, fontWeight: 700, color: '#b8960c', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 16 }}>
        Review & Generate
      </div>

      <div className="grid grid-cols-2 gap-5">
        {/* Customer */}
        <div style={{ padding: '14px 16px', borderRadius: 12, border: '1px solid #ece8e0', background: '#faf9f7' }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase', marginBottom: 8 }}>Customer</div>
          <div style={{ fontSize: 14, fontWeight: 600, color: '#1a1a1a' }}>{customer.name}</div>
          {customer.email && <div style={{ fontSize: 11, color: '#777' }}>{customer.email}</div>}
          {customer.phone && <div style={{ fontSize: 11, color: '#777' }}>{customer.phone}</div>}
          {customer.address && <div style={{ fontSize: 11, color: '#777', marginTop: 4 }}>{customer.address}</div>}
        </div>

        {/* Summary */}
        <div style={{ padding: '14px 16px', borderRadius: 12, border: '1px solid #ece8e0', background: '#faf9f7' }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase', marginBottom: 8 }}>Summary</div>
          <div className="flex items-center justify-between mb-1">
            <span style={{ fontSize: 12, color: '#555' }}>Rooms</span>
            <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>{rooms.filter(r => r.items.length > 0).length}</span>
          </div>
          <div className="flex items-center justify-between mb-1">
            <span style={{ fontSize: 12, color: '#555' }}>Total Items</span>
            <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>{totalItems}</span>
          </div>
          <div className="flex items-center justify-between mb-1">
            <span style={{ fontSize: 12, color: '#555' }}>Photos</span>
            <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>{photos.length}</span>
          </div>
          <div className="flex items-center justify-between">
            <span style={{ fontSize: 12, color: '#555' }}>Fabric Grade</span>
            <span style={{ fontSize: 13, fontWeight: 700, color: '#b8960c' }}>Grade {options.fabricGrade}</span>
          </div>
        </div>
      </div>

      {/* Items detail */}
      <div style={{ marginTop: 16, padding: '14px 16px', borderRadius: 12, border: '1px solid #ece8e0', background: '#faf9f7' }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase', marginBottom: 8 }}>Items</div>
        {rooms.filter(r => r.items.length > 0).map(room => (
          <div key={room.id} style={{ marginBottom: 8 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#1a1a1a', marginBottom: 4 }}>{room.name}</div>
            {room.items.map(item => (
              <div key={item.id} style={{ padding: '4px 0', fontSize: 12, color: '#555' }}>
                <div className="flex items-center justify-between">
                  <span>{formatItemType(item.type)}
                    {item.width || item.height ? ` (${[item.width, item.height, item.depth].filter(Boolean).join(' x ')})` : ''}
                  </span>
                  <span style={{ fontWeight: 600 }}>x{item.quantity}</span>
                </div>
                {item.fabric && (
                  <div style={{ fontSize: 10, color: '#b8960c', marginTop: 1 }}>
                    Fabric: {item.fabric.code} {item.fabric.name}{item.fabric.color_pattern ? ` — ${item.fabric.color_pattern}` : ''}
                    {(item.fabricYardsOverride || item.fabricYards) ? ` | ${item.fabricYardsOverride || item.fabricYards} yd` : ''}
                  </div>
                )}
                {item.backingFabric && (
                  <div style={{ fontSize: 10, color: '#2563eb', marginTop: 1 }}>
                    Backing: {item.backingFabric.code} {item.backingFabric.name}
                    {(item.backingYardsOverride || item.backingYards) ? ` | ${item.backingYardsOverride || item.backingYards} yd` : ''}
                  </div>
                )}
              </div>
            ))}
          </div>
        ))}
      </div>

      {/* Options */}
      <div className="flex flex-wrap gap-2 mt-4">
        {hasDrapery && (
          <>
            <span style={{ fontSize: 10, padding: '4px 10px', borderRadius: 6, background: '#eff6ff', color: '#2563eb', fontWeight: 600, border: '1px solid #bfdbfe' }}>
              {options.liningType === 'none' ? 'No Lining' : `${options.liningType.charAt(0).toUpperCase() + options.liningType.slice(1)} Lining`}
            </span>
            {options.pleatType !== 'none' && (
              <span style={{ fontSize: 10, padding: '4px 10px', borderRadius: 6, background: '#eff6ff', color: '#2563eb', fontWeight: 600, border: '1px solid #bfdbfe' }}>
                {options.pleatType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
              </span>
            )}
          </>
        )}
        {features.map(f => (
          <span key={f as string} style={{ fontSize: 10, padding: '4px 10px', borderRadius: 6, background: '#f5f3ef', color: '#555', fontWeight: 600, border: '1px solid #ece8e0' }}>
            {f}
          </span>
        ))}
        {options.rushOrder && (
          <span style={{ fontSize: 10, padding: '4px 10px', borderRadius: 6, background: '#fef2f2', color: '#dc2626', fontWeight: 600, border: '1px solid #fecaca' }}>
            Rush Order
          </span>
        )}
        {options.delivery && (
          <span style={{ fontSize: 10, padding: '4px 10px', borderRadius: 6, background: '#eff6ff', color: '#2563eb', fontWeight: 600, border: '1px solid #bfdbfe' }}>
            Delivery Included
          </span>
        )}
      </div>

      {/* Photo previews */}
      {photos.length > 0 && (
        <div className="flex gap-2 mt-4">
          {photos.map((p, i) => (
            <div key={i} style={{ width: 64, height: 64, borderRadius: 8, overflow: 'hidden', border: '1.5px solid #ece8e0' }}>
              <img src={p.preview} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// RESULT VIEW — Transparent pricing with editable line items
// ═══════════════════════════════════════════════════════════════
const CATEGORY_STYLES: Record<string, { color: string; bg: string }> = {
  fabric: { color: '#2563eb', bg: '#eff6ff' },
  lining: { color: '#7c3aed', bg: '#faf5ff' },
  labor: { color: '#b8960c', bg: '#fdf8eb' },
  upgrade: { color: '#059669', bg: '#ecfdf5' },
  foam: { color: '#059669', bg: '#ecfdf5' },
  installation: { color: '#6b7280', bg: '#f3f4f6' },
  surcharge: { color: '#dc2626', bg: '#fef2f2' },
};

function ResultView({ result }: { result: any }) {
  const [selectedTier, setSelectedTier] = useState(0);
  const [expandedItems, setExpandedItems] = useState<Record<string, boolean>>({});
  const [editableTiers, setEditableTiers] = useState<any[]>([]);
  const quoteNumber = result.quote_number || result.id || 'NEW';

  // Initialize editable tiers from result
  useEffect(() => {
    const proposals = result.design_proposals || result.proposals || result.tiers || [];
    if (Array.isArray(proposals)) {
      setEditableTiers(JSON.parse(JSON.stringify(proposals)));
    }
  }, [result]);

  const toggleExpand = (key: string) => setExpandedItems(p => ({ ...p, [key]: !p[key] }));

  // Recalculate when a line item value changes
  const updateLineItem = (tierIdx: number, itemIdx: number, liIdx: number, field: 'quantity' | 'rate', value: number) => {
    setEditableTiers(prev => {
      const tiers = JSON.parse(JSON.stringify(prev));
      const li = tiers[tierIdx].items[itemIdx].line_items[liIdx];
      li[field] = value;
      li.amount = Math.round(li.quantity * li.rate * 100) / 100;
      // Recalculate item subtotal
      const item = tiers[tierIdx].items[itemIdx];
      item.subtotal = Math.round(item.line_items.reduce((s: number, l: any) => s + l.amount, 0) * 100) / 100;
      // Recalculate tier totals
      const tier = tiers[tierIdx];
      tier.subtotal = Math.round(tier.items.reduce((s: number, it: any) => s + it.subtotal, 0) * 100) / 100;
      tier.tax = Math.round(tier.subtotal * (tier.tax_rate || 0.06) * 100) / 100;
      tier.total = Math.round((tier.subtotal + tier.tax) * 100) / 100;
      tier.deposit = Math.round(tier.total * 0.5 * 100) / 100;
      return tiers;
    });
  };

  if (editableTiers.length === 0) {
    return (
      <div style={{ padding: '20px 16px', borderRadius: 12, border: '1px solid #ece8e0', background: '#faf9f7' }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>Quote Created — {quoteNumber}</div>
        {result.total && <div style={{ fontSize: 22, fontWeight: 700, color: '#b8960c' }}>${result.total.toLocaleString()}</div>}
      </div>
    );
  }

  const activeTier = editableTiers[selectedTier];

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <div className="w-8 h-8 rounded-lg bg-[#f0fdf4] flex items-center justify-center">
          <Check size={18} className="text-[#16a34a]" />
        </div>
        <div>
          <div style={{ fontSize: 16, fontWeight: 700, color: '#1a1a1a' }}>Quote Generated</div>
          <div style={{ fontSize: 11, color: '#777' }}>{quoteNumber}</div>
        </div>
      </div>

      {/* 3-tier selector cards */}
      <div className="flex gap-2 mb-4">
        {TIERS.map((t, i) => {
          const tier = editableTiers[i];
          if (!tier) return null;
          const isSelected = selectedTier === i;
          return (
            <div key={t.key} onClick={() => setSelectedTier(i)}
              className="flex-1 cursor-pointer text-center transition-all"
              style={{
                padding: '14px 8px', borderRadius: 12,
                background: isSelected ? t.bg : '#faf9f7',
                border: `2px solid ${isSelected ? t.color : '#ece8e0'}`,
                boxShadow: isSelected ? '0 4px 16px rgba(0,0,0,0.06)' : 'none',
              }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: '#777' }}>{t.key} · {t.label}</div>
              <div style={{ fontSize: 22, fontWeight: 700, color: t.color, margin: '4px 0' }}>${tier.total?.toLocaleString()}</div>
              <div style={{ fontSize: 9, color: '#888' }}>Tax: ${tier.tax?.toFixed(2)} · Deposit: ${tier.deposit?.toLocaleString()}</div>
            </div>
          );
        })}
      </div>

      {/* Expanded line item breakdown */}
      {activeTier && (
        <div>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
            {TIERS[selectedTier]?.label} Tier — Line Item Breakdown
          </div>

          {activeTier.items?.map((item: any, itemIdx: number) => {
            const key = `${selectedTier}-${itemIdx}`;
            const isOpen = expandedItems[key] !== false; // default open
            return (
              <div key={itemIdx} style={{ marginBottom: 8, borderRadius: 10, border: '1px solid #ece8e0', overflow: 'hidden' }}>
                {/* Item header — click to expand/collapse */}
                <div onClick={() => toggleExpand(key)} className="flex items-center justify-between cursor-pointer"
                  style={{ padding: '10px 14px', background: '#f5f3ef' }}>
                  <div className="flex items-center gap-2">
                    <ChevronDown size={14} style={{ color: '#888', transform: isOpen ? 'none' : 'rotate(-90deg)', transition: 'transform 0.2s' }} />
                    <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>{item.name}</span>
                    {item.quantity > 1 && <span style={{ fontSize: 10, color: '#888' }}>x{item.quantity}</span>}
                  </div>
                  <span style={{ fontSize: 13, fontWeight: 700, color: TIERS[selectedTier]?.color || '#1a1a1a' }}>
                    ${item.subtotal?.toFixed(2)}
                  </span>
                </div>

                {/* Line items table */}
                {isOpen && item.line_items && (
                  <div style={{ padding: '8px 14px' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                      <thead>
                        <tr style={{ borderBottom: '1px solid #ece8e0' }}>
                          <th style={{ textAlign: 'left', fontSize: 9, fontWeight: 700, color: '#999', padding: '4px 0', textTransform: 'uppercase' }}>Description</th>
                          <th style={{ textAlign: 'right', fontSize: 9, fontWeight: 700, color: '#999', padding: '4px 0', width: 70, textTransform: 'uppercase' }}>Qty</th>
                          <th style={{ textAlign: 'right', fontSize: 9, fontWeight: 700, color: '#999', padding: '4px 0', width: 80, textTransform: 'uppercase' }}>Rate</th>
                          <th style={{ textAlign: 'right', fontSize: 9, fontWeight: 700, color: '#999', padding: '4px 0', width: 80, textTransform: 'uppercase' }}>Amount</th>
                        </tr>
                      </thead>
                      <tbody>
                        {item.line_items.map((li: any, liIdx: number) => {
                          const catStyle = CATEGORY_STYLES[li.category] || { color: '#555', bg: '#f5f3ef' };
                          return (
                            <tr key={liIdx} style={{ borderBottom: '1px solid #f5f3ef' }}>
                              <td style={{ padding: '6px 0', fontSize: 11, color: '#333' }}>
                                <span style={{ fontSize: 8, fontWeight: 700, color: catStyle.color, background: catStyle.bg, padding: '1px 5px', borderRadius: 3, marginRight: 6, textTransform: 'uppercase' }}>
                                  {li.category}
                                </span>
                                {li.description}
                              </td>
                              <td style={{ textAlign: 'right', padding: '6px 0' }}>
                                <input type="number" step="0.1" value={li.quantity}
                                  onChange={e => updateLineItem(selectedTier, itemIdx, liIdx, 'quantity', parseFloat(e.target.value) || 0)}
                                  style={{ width: 55, textAlign: 'right', fontSize: 11, padding: '3px 4px', border: '1px solid #ece8e0', borderRadius: 4, background: '#faf9f7' }} />
                                <span style={{ fontSize: 9, color: '#888', marginLeft: 2 }}>{li.unit}</span>
                              </td>
                              <td style={{ textAlign: 'right', padding: '6px 0' }}>
                                <span style={{ fontSize: 9, color: '#888', marginRight: 1 }}>$</span>
                                <input type="number" step="0.01" value={li.rate}
                                  onChange={e => updateLineItem(selectedTier, itemIdx, liIdx, 'rate', parseFloat(e.target.value) || 0)}
                                  style={{ width: 60, textAlign: 'right', fontSize: 11, padding: '3px 4px', border: '1px solid #ece8e0', borderRadius: 4, background: '#faf9f7' }} />
                              </td>
                              <td style={{ textAlign: 'right', padding: '6px 0', fontSize: 11, fontWeight: 600, color: '#1a1a1a' }}>
                                ${li.amount?.toFixed(2)}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                    {/* Item subtotal */}
                    <div className="flex justify-between" style={{ padding: '6px 0', borderTop: '1.5px solid #ece8e0', marginTop: 4, fontSize: 12, fontWeight: 700, color: '#1a1a1a' }}>
                      <span>Item Subtotal</span>
                      <span>${item.subtotal?.toFixed(2)}</span>
                    </div>
                  </div>
                )}
              </div>
            );
          })}

          {/* Tier totals */}
          <div style={{ marginTop: 8, padding: '12px 14px', borderRadius: 10, border: '1.5px solid #ece8e0', background: '#f5f3ef' }}>
            <div className="flex justify-between mb-1" style={{ fontSize: 12, color: '#555' }}>
              <span>Subtotal</span><span style={{ fontWeight: 600 }}>${activeTier.subtotal?.toFixed(2)}</span>
            </div>
            <div className="flex justify-between mb-1" style={{ fontSize: 12, color: '#555' }}>
              <span>Tax ({((activeTier.tax_rate || 0.06) * 100).toFixed(1)}%)</span><span style={{ fontWeight: 600 }}>${activeTier.tax?.toFixed(2)}</span>
            </div>
            <div className="flex justify-between mb-1" style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a', borderTop: '1.5px solid #ddd', paddingTop: 6 }}>
              <span>Total</span><span>${activeTier.total?.toFixed(2)}</span>
            </div>
            <div className="flex justify-between" style={{ fontSize: 11, color: '#16a34a', fontWeight: 600 }}>
              <span>50% Deposit Due</span><span>${activeTier.deposit?.toFixed(2)}</span>
            </div>
          </div>

          <div style={{ marginTop: 8, fontSize: 10, color: '#aaa', textAlign: 'center' }}>
            Edit any quantity or rate above — totals recalculate live
          </div>
        </div>
      )}
    </div>
  );
}
