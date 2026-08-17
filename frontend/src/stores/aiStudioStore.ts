import { create } from 'zustand';

export type KnobId = 'creativity' | 'contextDepth' | 'tokenBudget';
export type CreativityLevel = 'low' | 'normal' | 'high';

export interface KnobValues {
  creativity: number;
  contextDepth: number;
  tokenBudget: number;
}

export const CREATIVITY_LEVEL_VALUES: Record<CreativityLevel, number> = {
  low: 20,
  normal: 50,
  high: 85,
};

export const CREATIVITY_LEVEL_LABELS: Record<CreativityLevel, string> = {
  low: 'Low',
  normal: 'Normal',
  high: 'High',
};

export const DEFAULT_KNOBS: KnobValues = {
  creativity: CREATIVITY_LEVEL_VALUES.normal,
  contextDepth: 55,
  tokenBudget: 70,
};

export const KNOB_LABELS: Record<KnobId, string> = {
  creativity: 'Creativity Weight',
  contextDepth: 'Context Depth',
  tokenBudget: 'Token Budget',
};

const TOKEN_RESTORE_TICK_MS = 1500;
const TOKEN_RESTORE_STEP = 4;

function levelFromValue(value: number): CreativityLevel {
  if (value <= 33) return 'low';
  if (value <= 66) return 'normal';
  return 'high';
}

interface AiStudioState {
  isActive: boolean;
  isRetrieving: boolean;
  knobs: KnobValues;
  creativityLevel: CreativityLevel;
  lastModel: string;
  lastLatencyMs: number;
  tokensConsumed: number;
  streamingText: string;
  committedText: string;

  beginResponse: () => void;
  endResponse: () => void;
  retrieveStarted: () => void;
  retrieveDone: () => void;
  reset: () => void;
  setKnob: (id: KnobId, value: number) => void;
  setCreativityLevel: (level: CreativityLevel) => void;
  setLastLlmMetrics: (model: string, latencyMs: number, completionTokens?: number) => void;
  consumeTokens: (n: number) => void;
  setStreamingText: (text: string) => void;
  commitStream: () => void;
}

let restoreTimer: ReturnType<typeof setInterval> | null = null;

function ensureRestoreTimer(set: (partial: Partial<AiStudioState>) => void, get: () => AiStudioState) {
  if (restoreTimer) return;
  restoreTimer = setInterval(() => {
    const { tokensConsumed } = get();
    if (tokensConsumed <= 0) {
      if (restoreTimer) {
        clearInterval(restoreTimer);
        restoreTimer = null;
      }
      return;
    }
    set({ tokensConsumed: Math.max(0, tokensConsumed - TOKEN_RESTORE_STEP) });
  }, TOKEN_RESTORE_TICK_MS);
}

export const useAiStudio = create<AiStudioState>((set, get) => ({
  isActive: false,
  isRetrieving: false,
  knobs: { ...DEFAULT_KNOBS },
  creativityLevel: 'normal',
  lastModel: '',
  lastLatencyMs: 0,
  tokensConsumed: 0,
  streamingText: '',
  committedText: '',

  beginResponse: () => set({ isActive: true }),
  endResponse: () => set({ isActive: false }),
  retrieveStarted: () => set({ isRetrieving: true }),
  retrieveDone: () => set({ isRetrieving: false }),

  reset: () =>
    set({
      isActive: false,
      isRetrieving: false,
      streamingText: '',
    }),

  setKnob: (id, value) =>
    set((state) => {
      const next = Math.max(0, Math.min(100, Math.round(value)));
      const knobs = { ...state.knobs, [id]: next };
      if (id === 'creativity') {
        return { knobs, creativityLevel: levelFromValue(next) };
      }
      return { knobs };
    }),

  setCreativityLevel: (level) =>
    set((state) => ({
      creativityLevel: level,
      knobs: { ...state.knobs, creativity: CREATIVITY_LEVEL_VALUES[level] },
    })),

  setLastLlmMetrics: (model, latencyMs, completionTokens) =>
    set({
      lastModel: model || '',
      lastLatencyMs: Math.round(latencyMs || 0),
    }),

  consumeTokens: (n) => {
    const drain = Math.max(0, Math.round(n || 0));
    if (drain <= 0) return;
    set((state) => ({ tokensConsumed: Math.min(100, state.tokensConsumed + drain) }));
    ensureRestoreTimer(set as any, get);
  },

  setStreamingText: (text) => set({ streamingText: text }),

  commitStream: () =>
    set((state) => {
      if (!state.streamingText.trim()) return state;
      return {
        streamingText: '',
        committedText: state.committedText
          ? `${state.committedText} ${state.streamingText}`.trim()
          : state.streamingText,
      };
    }),
}));