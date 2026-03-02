// Phase 1
export { analyzeContent, shouldReanalyze } from './ContentAnalyzer';
export type { CanvasMode, AnalysisResult, ChartData, MetricData, WebPreview, ImageData, QuoteData, MediaRef } from './ContentAnalyzer';
export { default as AvatarDisplay } from './AvatarDisplay';
export { default as ChartCanvas } from './ChartCanvas';
export { default as MetricCard } from './MetricCard';
export { default as QuoteCallout } from './QuoteCallout';
export { default as ImageCanvas } from './ImageCanvas';
export { default as WebPreviewCanvas } from './WebPreviewCanvas';
export { default as DocumentCanvas } from './DocumentCanvas';
export { default as SplitCanvas } from './SplitCanvas';
export { default as CanvasTransition } from './CanvasTransition';

// Phase 2
export { default as MediaCanvas } from './MediaCanvas';
export { default as PiPOverlay } from './PiPOverlay';
export { default as PresentationCanvas, parseSlides, isPresentationContent } from './PresentationCanvas';
export { useMedia, urlToMediaItem, extractYoutubeId, extractVimeoId, formatTime, MediaContext, DEFAULT_MEDIA_STATE, PLAYBACK_SPEEDS } from './MediaController';
export type { MediaItem, MediaState, MediaActions } from './MediaController';
export { loadHistory, saveSnapshot, deleteSnapshot, clearHistory, searchHistory, getByMode, getRecent, autoLabel, autoTags } from './CanvasHistory';
export type { CanvasSnapshot } from './CanvasHistory';

// Phase 3
export { default as CommsCanvas, parseCommsFromContent } from './CommsCanvas';
export type { CallInfo, ThreadMessage, CommsThread, CommsView } from './CommsCanvas';
export { default as WorkspaceCanvas, isWorkspaceContent } from './WorkspaceCanvas';
export type { WorkspaceTab, CodeBlock as WorkspaceCodeBlock, TerminalOutput, CalendarEvent, QuoteLine, QuotePreview } from './WorkspaceCanvas';
