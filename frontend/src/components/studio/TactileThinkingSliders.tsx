'use client';

import React, { useCallback, useMemo, useRef } from 'react';
import { motion, useMotionValue, useSpring } from 'framer-motion';
import {
  useAiStudio,
  KNOB_LABELS,
  CREATIVITY_LEVEL_LABELS,
  DEFAULT_KNOBS,
  type KnobId,
  type CreativityLevel,
} from '@/stores/aiStudioStore';

const KNOB_ORDER: KnobId[] = ['creativity', 'tokenBudget'];
const CREATIVITY_LEVELS: CreativityLevel[] = ['low', 'normal', 'high'];

function knobHue(value: number, active: boolean): number {
  if (active) return 25;
  return 164 + (value / 100) * (199 - 164);
}

function formatLatency(ms: number): string {
  if (!ms) return '—';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function shortenModel(name: string): string {
  if (!name) return 'No model';
  const short = name.split('/').pop() || name;
  return short.length > 22 ? short.slice(0, 22) + '…' : short;
}

interface ThinkingKnobProps {
  id: KnobId;
  label: string;
  value: number;
  active: boolean;
  retrieving: boolean;
  onChange: (value: number) => void;
}

const RADIUS = 20;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
const SWEEP = 270;
const START_DEG = -135;

function ThinkingKnob({ id, label, value, active, retrieving, onChange }: ThinkingKnobProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const rotation = useMotionValue(START_DEG);
  const smoothRotation = useSpring(rotation, { stiffness: 140, damping: 18 });

  const color = useMemo(() => `hsl(${knobHue(value, active)} 85% 50%)`, [value, active]);
  const deg = START_DEG + (value / 100) * SWEEP;

  React.useEffect(() => {
    rotation.set(deg);
  }, [deg, rotation]);

  const valueFromPointer = useCallback(
    (event: React.PointerEvent) => {
      const svg = svgRef.current;
      if (!svg) return;
      const rect = svg.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const dx = event.clientX - cx;
      const dy = event.clientY - cy;
      const angle = (Math.atan2(dy, dx) * 180) / Math.PI;
      let degValue = ((angle - START_DEG + 360) % 360) + START_DEG;
      if (degValue < START_DEG) degValue += 360;
      const next = ((degValue - START_DEG) / SWEEP) * 100;
      onChange(Math.max(0, Math.min(100, next)));
    },
    [onChange],
  );

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'ArrowRight' || event.key === 'ArrowUp') onChange(value + 5);
    else if (event.key === 'ArrowLeft' || event.key === 'ArrowDown') onChange(value - 5);
  };

  return (
    <div className="flex flex-col items-center gap-1 select-none">
      <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      <motion.span
        className="text-sm font-semibold tabular-nums leading-none"
        animate={{ color }}
      >
        {Math.round(value)}
      </motion.span>

      <motion.div
        className="relative h-14 w-14 rounded-full"
        animate={
          retrieving
            ? {
                scale: [1, 1.18, 1],
                boxShadow: [
                  '0 0 0 0 hsl(25 90% 55% / 0.5)',
                  '0 0 0 12px hsl(25 90% 55% / 0)',
                  '0 0 0 0 hsl(25 90% 55% / 0.5)',
                ],
              }
            : active
              ? {
                  scale: 1,
                  boxShadow: [
                    '0 0 24px 2px hsl(25 90% 55% / 0.45)',
                    '0 0 44px 6px hsl(25 90% 55% / 0.25)',
                    '0 0 24px 2px hsl(25 90% 55% / 0.45)',
                  ],
                }
              : { scale: 1, boxShadow: '0 0 0 0 hsl(164 60% 48% / 0)' }
        }
        transition={
          retrieving
            ? { duration: 1.1, repeat: Infinity, ease: 'easeOut' }
            : active
              ? { duration: 1.8, repeat: Infinity, ease: 'easeInOut' }
              : { duration: 0.3 }
        }
      >
        <svg
          ref={svgRef}
          viewBox="0 0 48 48"
          className="h-full w-full touch-none"
          onPointerDown={(e) => {
            (e.currentTarget as SVGElement).setPointerCapture(e.pointerId);
            valueFromPointer(e);
          }}
          onPointerMove={(e) => {
            if (e.currentTarget.hasPointerCapture(e.pointerId)) valueFromPointer(e);
          }}
          role="slider"
          aria-label={label}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={value}
          tabIndex={0}
          onKeyDown={handleKeyDown}
        >
          <circle
            cx="24"
            cy="24"
            r={RADIUS}
            fill="none"
            stroke="hsl(var(--border))"
            strokeWidth="4"
            strokeLinecap="round"
            transform="rotate(135 24 24)"
            strokeDasharray={`${CIRCUMFERENCE * 0.75} ${CIRCUMFERENCE}`}
          />
          <motion.circle
            cx="24"
            cy="24"
            r={RADIUS}
            fill="none"
            strokeWidth="4"
            strokeLinecap="round"
            transform="rotate(135 24 24)"
            initial={false}
            animate={{
              strokeDasharray: `${(CIRCUMFERENCE * 0.75 * value) / 100} ${CIRCUMFERENCE}`,
              stroke: color,
            }}
            transition={{ type: 'spring', stiffness: 140, damping: 18 }}
          />
        </svg>

        <motion.div
          className="pointer-events-none absolute left-1/2 top-1/2 h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full"
          style={{ x: '-50%', y: '-50%' }}
        >
          <motion.span
            className="absolute left-1/2 top-1/2 block h-[22px] w-[3px] origin-top rounded-full"
            style={{ rotate: smoothRotation, backgroundColor: color, x: '-50%' }}
          />
        </motion.div>
      </motion.div>
    </div>
  );
}

function LlmInfoPanel({ active, retrieving }: { active: boolean; retrieving: boolean }) {
  const model = useAiStudio((s) => s.lastModel);
  const latencyMs = useAiStudio((s) => s.lastLatencyMs);

  const glow = retrieving || active;

  return (
    <motion.div
      className="flex w-20 flex-col items-center justify-center gap-0.5 rounded-lg px-1 py-1.5"
      animate={
        glow
          ? {
              boxShadow: [
                '0 0 12px 1px hsl(25 90% 55% / 0.35)',
                '0 0 22px 3px hsl(25 90% 55% / 0.15)',
                '0 0 12px 1px hsl(25 90% 55% / 0.35)',
              ],
            }
          : { boxShadow: '0 0 0 0 hsl(25 90% 55% / 0)' }
      }
      transition={glow ? { duration: 1.6, repeat: Infinity, ease: 'easeInOut' } : { duration: 0.3 }}
    >
      <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
        LLM
      </span>
      <span className="text-[11px] font-semibold leading-tight text-center text-accent-foreground break-words">
        {shortenModel(model)}
      </span>
      <span className="mt-0.5 inline-flex items-center gap-1 rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
        <motion.span
          className="inline-block h-1.5 w-1.5 rounded-full bg-accent"
          animate={retrieving ? { opacity: [1, 0.2, 1] } : { opacity: 1 }}
          transition={retrieving ? { duration: 0.8, repeat: Infinity } : { duration: 0.2 }}
        />
        {formatLatency(latencyMs)}
      </span>
    </motion.div>
  );
}

export function TactileThinkingSliders() {
  const knobs = useAiStudio((s) => s.knobs);
  const setKnob = useAiStudio((s) => s.setKnob);
  const creativityLevel = useAiStudio((s) => s.creativityLevel);
  const setCreativityLevel = useAiStudio((s) => s.setCreativityLevel);
  const isActive = useAiStudio((s) => s.isActive);
  const isRetrieving = useAiStudio((s) => s.isRetrieving);
  const tokensConsumed = useAiStudio((s) => s.tokensConsumed);

  const tokenValue = Math.max(0, knobs.tokenBudget - tokensConsumed);

  return (
    <div className="space-y-2 rounded-xl border border-border/60 bg-background/50 px-3 py-2.5 backdrop-blur">
      <div className="flex items-stretch justify-between gap-2">
        {KNOB_ORDER.map((id) => (
          <ThinkingKnob
            key={id}
            id={id}
            label={KNOB_LABELS[id]}
            value={id === 'tokenBudget' ? tokenValue : knobs[id]}
            active={isActive}
            retrieving={isRetrieving}
            onChange={(value) => setKnob(id, value)}
          />
        ))}
        <LlmInfoPanel active={isActive} retrieving={isRetrieving} />
      </div>
      <div className="flex items-center justify-center gap-1.5">
        <span className="text-[10px] uppercase tracking-wider text-muted-foreground mr-1">
          Creativity
        </span>
        {CREATIVITY_LEVELS.map((level) => (
          <button
            key={level}
            type="button"
            onClick={() => setCreativityLevel(level)}
            className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium transition-colors ${
              creativityLevel === level
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground hover:bg-muted/80'
            }`}
          >
            {CREATIVITY_LEVEL_LABELS[level]}
          </button>
        ))}
      </div>
    </div>
  );
}

export { DEFAULT_KNOBS };