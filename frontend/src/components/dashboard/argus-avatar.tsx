'use client';

import { motion } from 'framer-motion';
import { useAiStudio } from '@/stores/aiStudioStore';

const ACCENT = 'hsl(25 90% 55%)';

export function ArgusAvatar({ size = 32 }: { size?: number }) {
  const isRetrieving = useAiStudio((s) => s.isRetrieving);
  const isActive = useAiStudio((s) => s.isActive);

  const thinking = isRetrieving || isActive;

  return (
    <motion.div
      className="relative flex items-center justify-center"
      style={{ width: size, height: size }}
      animate={
        thinking
          ? { scale: [1, 1.08, 1] }
          : { scale: 1 }
      }
      transition={thinking ? { duration: 1.4, repeat: Infinity, ease: 'easeInOut' } : { duration: 0.3 }}
    >
      <svg
        viewBox="0 0 64 64"
        width={size}
        height={size}
        className="overflow-visible"
        aria-hidden="true"
      >
        <defs>
          <radialGradient id="argus-jagan" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#ffffff" />
            <stop offset="40%" stopColor={ACCENT} />
            <stop offset="100%" stopColor="#7a2a06" />
          </radialGradient>
          <linearGradient id="argus-hair" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#1a1a2e" />
            <stop offset="100%" stopColor="#0a0a16" />
          </linearGradient>
        </defs>

        <g>
          <motion.path
            d="M14 26 L18 6 L24 16 L32 4 L40 16 L46 6 L50 26 C50 44 42 54 32 56 C22 54 14 44 14 26 Z"
            fill="url(#argus-hair)"
            stroke="hsl(var(--border))"
            strokeWidth="0.5"
          />

          <ellipse cx="32" cy="34" rx="13" ry="14" fill="#f4e4c1" stroke="#3a2a1a" strokeWidth="0.6" />

          <motion.path
            d="M12 28 L18 10 L24 18 L32 8 L40 18 L46 10 L52 28 L48 18 L40 24 L32 16 L24 24 L16 18 Z"
            fill="#0a0a16"
            stroke="#1a1a2e"
            strokeWidth="0.4"
            animate={thinking ? { opacity: [1, 0.85, 1] } : { opacity: 1 }}
            transition={thinking ? { duration: 1.2, repeat: Infinity } : { duration: 0.2 }}
          />

          <path d="M32 6 L34 0 L30 -2" fill="#0a0a16" transform="translate(0 6)" />
          <path d="M22 8 L18 0 L26 2" fill="#0a0a16" transform="translate(0 6)" />
          <path d="M42 8 L46 0 L38 2" fill="#0a0a16" transform="translate(0 6)" />

          <path
            d="M18 26 Q21 27 24 31"
            fill="none"
            stroke="hsl(210 10% 20%)"
            strokeWidth="1.4"
            strokeLinecap="round"
          />
          <path
            d="M40 31 Q43 27 46 26"
            fill="none"
            stroke="hsl(210 10% 20%)"
            strokeWidth="1.4"
            strokeLinecap="round"
          />

          <ellipse cx="21" cy="32" rx="2.4" ry="3" fill="#1a1a2e" />
          <ellipse cx="43" cy="32" rx="2.4" ry="3" fill="#1a1a2e" />
          <circle cx="21.6" cy="31.4" r="0.8" fill="#ffffff" />
          <circle cx="43.6" cy="31.4" r="0.8" fill="#ffffff" />

          <motion.g
            animate={
              thinking
                ? { opacity: [1, 0.6, 1] }
                : { opacity: [1, 0, 1] }
            }
            transition={
              thinking
                ? { duration: 0.7, repeat: Infinity, ease: 'easeInOut' }
                : { duration: 4, repeat: Infinity, times: [0, 0.95, 1] }
            }
          >
            <motion.circle
              cx="32"
              cy="28"
              r="2.6"
              fill="url(#argus-jagan)"
              animate={
                thinking
                  ? {
                      r: [2.6, 3.6, 2.6],
                      filter: [
                        'drop-shadow(0 0 1px hsl(25 90% 55% / 0.6))',
                        'drop-shadow(0 0 5px hsl(25 100% 65% / 0.95))',
                        'drop-shadow(0 0 1px hsl(25 90% 55% / 0.6))',
                      ],
                    }
                  : {
                      r: 2.6,
                      filter: 'drop-shadow(0 0 1px hsl(25 90% 55% / 0.2))',
                    }
              }
              transition={
                thinking
                  ? { duration: 0.8, repeat: Infinity, ease: 'easeInOut' }
                  : { duration: 0.3 }
              }
            />
            <circle cx="32" cy="28" r="0.9" fill="#0a0a16" />
          </motion.g>

          <path
            d="M27 42 Q32 45 37 42"
            fill="none"
            stroke="#9a3a2a"
            strokeWidth="1.2"
            strokeLinecap="round"
          />

          <motion.rect
            x="20"
            y="20"
            width="24"
            height="3"
            rx="1.5"
            fill="#0a0a16"
            stroke="#c9a227"
            strokeWidth="0.5"
            transform="rotate(-8 32 21.5)"
            animate={thinking ? { y: [20, 19.5, 20] } : { y: 20 }}
            transition={thinking ? { duration: 1.2, repeat: Infinity } : { duration: 0.2 }}
          />
        </g>
      </svg>
    </motion.div>
  );
}

export { ACCENT as ARGUS_ACCENT };