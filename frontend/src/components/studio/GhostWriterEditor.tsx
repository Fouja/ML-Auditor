'use client';

import React, { useCallback, useLayoutEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { useAiStudio } from '@/stores/aiStudioStore';
import { cn } from '@/lib/utils';

interface GhostWriterEditorProps {
  /** Hint shown when there is no text. */
  placeholder?: string;
  className?: string;
}

/**
 * GhostWriterEditor — a borderless composer for AI streaming output.
 *
 * Incoming (uncommitted) text renders faint, italic and translucent like a
 * ghost. Pressing Tab "commits" the ghost into solid ink with a short
 * ghost-to-ink animation. State lives in the AiStudio store, so any component
 * can stream text in (and commit it) without talking to this editor.
 */
export function GhostWriterEditor({ placeholder, className }: GhostWriterEditorProps) {
  const streamingText = useAiStudio((s) => s.streamingText);
  const committedText = useAiStudio((s) => s.committedText);
  const isActive = useAiStudio((s) => s.isActive);
  const commitStream = useAiStudio((s) => s.commitStream);
  const setStreamingText = useAiStudio((s) => s.setStreamingText);

  const prevStreamingRef = useRef('');
  const [commitCount, setCommitCount] = useState(0);

  useLayoutEffect(() => {
    prevStreamingRef.current = streamingText;
  }, [streamingText]);

  // The slice that was just promoted from ghost to committed text.
  const ghost = prevStreamingRef.current.trim();
  const justCommitted =
    streamingText === '' && ghost && committedText.endsWith(ghost) ? ghost : '';

  const solid = justCommitted ? committedText.slice(0, -justCommitted.length) : committedText;

  const commit = useCallback(() => {
    if (!streamingText.trim()) return;
    setCommitCount((c) => c + 1);
    commitStream();
  }, [streamingText, commitStream]);

  const cancel = useCallback(() => setStreamingText(''), [setStreamingText]);

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Tab') {
      event.preventDefault();
      commit();
    } else if (event.key === 'Escape') {
      event.preventDefault();
      cancel();
    }
  };

  const hasText = Boolean(streamingText || committedText);

  return (
    <div
      className={cn(
        'min-h-[72px] w-full cursor-text rounded-xl px-3 py-2.5 text-sm leading-relaxed outline-none transition-colors',
        'focus-visible:ring-1 focus-visible:ring-ring/50',
        isActive && 'ring-1 ring-orange-400/20',
        className,
      )}
      role="textbox"
      aria-multiline="true"
      aria-label="Streaming text composer"
      tabIndex={0}
      onKeyDown={handleKeyDown}
    >
      {!hasText && !isActive && (
        <span className="text-xs text-muted-foreground/60">{placeholder ?? 'Waiting for the AI to write…'}</span>
      )}

      {/* committed ink (solid) */}
      {committedText && (
        <>
          <span className="whitespace-pre-wrap font-normal text-black dark:text-white">{solid}</span>
          {justCommitted && (
            <motion.span
              key={`ink-${commitCount}`}
              className="whitespace-pre-wrap"
              initial={{ color: '#9ca3af', opacity: 0.45, fontStyle: 'italic' }}
              animate={{ color: '#000000', opacity: 1, fontStyle: 'normal' }}
              transition={{ type: 'spring', stiffness: 260, damping: 24 }}
            >
              {justCommitted}
            </motion.span>
          )}
        </>
      )}

      {/* ghost (uncommitted) streaming text */}
      {streamingText && (
        <motion.span
          key="ghost"
          className="whitespace-pre-wrap font-light italic text-gray-400/50"
          initial={{ opacity: 0.2 }}
          animate={{ opacity: 0.7 }}
          transition={{ duration: 0.4 }}
        >
          {streamingText}
        </motion.span>
      )}

      {/* blinking caret while the AI is writing */}
      {isActive && (
        <motion.span
          className="ml-px inline-block h-[1em] w-[2px] translate-y-[0.15em] rounded-sm bg-orange-400/80"
          animate={{ opacity: [1, 0, 1] }}
          transition={{ duration: 0.9, repeat: Infinity }}
          aria-hidden
        />
      )}

      {streamingText && !isActive && (
        <span className="ml-2 inline-block text-[10px] uppercase tracking-wider text-muted-foreground/60">
          Tab to commit
        </span>
      )}
    </div>
  );
}
