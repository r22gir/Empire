// WizardContext.tsx — ArchiveForge V1.1 wizard state management
import React, { createContext, useContext, useReducer, useEffect, ReactNode } from 'react';
import { CompsResult, LifeReferenceIssue } from '../lib/types';

export type WizardStep = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;

export interface ArchiveData {
  id?: number;
  google_books_id?: string;
  suggested_retail_min?: number;
  suggested_retail_max?: number;
  condition_score?: number;
  tier?: 'A' | 'B' | 'C';
  comps?: CompsResult | null;
  [key: string]: any;
}

interface WizardState {
  step: WizardStep;
  searchParams: { date: string; keyword: string };
  searchResults: LifeReferenceIssue[];
  selectedRef: LifeReferenceIssue | null;
  archiveId: number | null;
  archiveData: ArchiveData;
  photos: any[];
  isDirty: boolean;
  isSearching: boolean;
  comps: CompsResult | null;
  error: string | null;
}

type WizardAction =
  | { type: 'SET_STEP'; payload: WizardStep }
  | { type: 'SET_SEARCH_PARAMS'; payload: Partial<WizardState['searchParams']> }
  | { type: 'SET_SEARCH_RESULTS'; payload: LifeReferenceIssue[] }
  | { type: 'SET_SELECTED_REF'; payload: LifeReferenceIssue | null }
  | { type: 'SET_ARCHIVE_ID'; payload: number | null }
  | { type: 'UPDATE_ARCHIVE_DATA'; payload: Partial<ArchiveData> }
  | { type: 'SET_PHOTOS'; payload: any[] }
  | { type: 'SET_COMPS'; payload: CompsResult | null }
  | { type: 'SET_DIRTY'; payload: boolean }
  | { type: 'SET_SEARCHING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'RESET_WIZARD' };

const initialState: WizardState = {
  step: 1,
  searchParams: { date: '', keyword: '' },
  searchResults: [],
  selectedRef: null,
  archiveId: null,
  archiveData: {},
  photos: [],
  isDirty: false,
  isSearching: false,
  comps: null,
  error: null,
};

const wizardReducer = (state: WizardState, action: WizardAction): WizardState => {
  switch (action.type) {
    case 'SET_STEP': return { ...state, step: action.payload, isDirty: true };
    case 'SET_SEARCH_PARAMS': return { ...state, searchParams: { ...state.searchParams, ...action.payload } };
    case 'SET_SEARCH_RESULTS': return { ...state, searchResults: action.payload, isSearching: false };
    case 'SET_SELECTED_REF': return { ...state, selectedRef: action.payload };
    case 'SET_ARCHIVE_ID': return { ...state, archiveId: action.payload };
    case 'UPDATE_ARCHIVE_DATA': return { ...state, archiveData: { ...state.archiveData, ...action.payload }, isDirty: true };
    case 'SET_COMPS': return { ...state, comps: action.payload };
    case 'SET_PHOTOS': return { ...state, photos: action.payload, isDirty: true };
    case 'SET_DIRTY': return { ...state, isDirty: action.payload };
    case 'SET_SEARCHING': return { ...state, isSearching: action.payload };
    case 'SET_ERROR': return { ...state, error: action.payload };
    case 'RESET_WIZARD': return initialState;
    default: return state;
  }
};

interface WizardContextValue {
  state: WizardState;
  dispatch: React.Dispatch<WizardAction>;
  selectIssue: (issue: LifeReferenceIssue) => Promise<void>;
  saveCurrentStep: () => Promise<void>;
  fetchComps: (googleBooksId: string, conditionScore?: number) => Promise<void>;
  fetchLiveComps: (googleBooksId: string) => Promise<void>;
}

const WizardContext = createContext<WizardContextValue | null>(null);

export const WizardProvider = ({ children }: { children: ReactNode }) => {
  const [state, dispatch] = useReducer(wizardReducer, initialState);

  // Restore from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('archiveforge_wizard');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        dispatch({ type: 'UPDATE_ARCHIVE_DATA', payload: parsed.archiveData || {} });
        if (parsed.step) dispatch({ type: 'SET_STEP', payload: parsed.step });
      } catch {}
    }
  }, []);

  // Persist to localStorage on dirty changes
  useEffect(() => {
    if (state.isDirty) {
      localStorage.setItem('archiveforge_wizard', JSON.stringify({
        step: state.step,
        archiveData: state.archiveData,
      }));
    }
  }, [state.step, state.archiveData, state.isDirty]);

  const fetchComps = async (googleBooksId: string, conditionScore = 3) => {
    try {
      const res = await fetch(`/api/v1/archiveforge/reference/comps?google_books_id=${googleBooksId}&condition_score=${conditionScore}`);
      const data = await res.json();
      if (data.status === 'success') {
        dispatch({ type: 'SET_COMPS', payload: data.comps });
        dispatch({ type: 'UPDATE_ARCHIVE_DATA', payload: {
          suggested_retail_min: data.comps.suggested_min,
          suggested_retail_max: data.comps.suggested_max,
          comps: data.comps,
        }});
      }
    } catch (err) {
      console.warn('Comps fetch failed', err);
    }
  };

  const fetchLiveComps = async (googleBooksId: string) => {
    try {
      const res = await fetch(`/api/v1/archiveforge/reference/live-comps`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ google_books_id: googleBooksId }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        dispatch({ type: 'SET_COMPS', payload: data.comps });
      }
    } catch (err) {
      console.warn('Live comps failed, falling back to fixture/generic', err);
    }
  };

  const selectIssue = async (issue: LifeReferenceIssue) => {
    dispatch({ type: 'SET_SELECTED_REF', payload: issue });
    try {
      const res = await fetch('/api/v1/archiveforge/archives', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...issue }),
      });
      const archive = await res.json();
      dispatch({ type: 'SET_ARCHIVE_ID', payload: archive.id });
      await fetchComps(issue.google_books_id);
      await fetchLiveComps(issue.google_books_id);
    } catch (err) {
      dispatch({ type: 'SET_ERROR', payload: 'Failed to create archive entry' });
    }
  };

  const saveCurrentStep = async () => {
    if (!state.archiveId) return;
    try {
      await fetch(`/api/v1/archiveforge/archives/${state.archiveId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(state.archiveData),
      });
      dispatch({ type: 'SET_DIRTY', payload: false });
    } catch (err) {
      console.warn('Save failed', err);
    }
  };

  return (
    <WizardContext.Provider value={{ state, dispatch, selectIssue, saveCurrentStep, fetchComps, fetchLiveComps }}>
      {children}
    </WizardContext.Provider>
  );
};

export const useWizard = () => {
  const context = useContext(WizardContext);
  if (!context) throw new Error('useWizard must be used within WizardProvider');
  return context;
};