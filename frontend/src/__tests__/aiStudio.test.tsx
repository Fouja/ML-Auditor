import { describe, it, expect, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { useAiStudio, DEFAULT_KNOBS } from '@/stores/aiStudioStore';
import { TactileThinkingSliders } from '@/components/studio/TactileThinkingSliders';

beforeEach(() => {
  useAiStudio.setState({
    isActive: false,
    isRetrieving: false,
    knobs: { ...DEFAULT_KNOBS },
    creativityLevel: 'normal',
  });
});

describe('aiStudioStore — AI response lifecycle', () => {
  it('starts with defaults', () => {
    const s = useAiStudio.getState();
    expect(s.isActive).toBe(false);
    expect(s.isRetrieving).toBe(false);
    expect(s.creativityLevel).toBe('normal');
  });

  it('retrieving then generating flags the visual states', () => {
    useAiStudio.getState().retrieveStarted();
    expect(useAiStudio.getState().isRetrieving).toBe(true);

    useAiStudio.getState().retrieveDone();
    useAiStudio.getState().beginResponse();
    expect(useAiStudio.getState().isRetrieving).toBe(false);
    expect(useAiStudio.getState().isActive).toBe(true);
  });

  it('setKnob clamps to 0..100', () => {
    const { setKnob } = useAiStudio.getState();
    setKnob('creativity', 140);
    expect(useAiStudio.getState().knobs.creativity).toBe(100);
    setKnob('contextDepth', -10);
    expect(useAiStudio.getState().knobs.contextDepth).toBe(0);
  });

  it('setCreativityLevel maps low/normal/high', () => {
    useAiStudio.getState().setCreativityLevel('low');
    expect(useAiStudio.getState().creativityLevel).toBe('low');
    expect(useAiStudio.getState().knobs.creativity).toBe(20);
    useAiStudio.getState().setCreativityLevel('high');
    expect(useAiStudio.getState().creativityLevel).toBe('high');
    expect(useAiStudio.getState().knobs.creativity).toBe(85);
  });

  it('setLastLlmMetrics stores model and latency', () => {
    useAiStudio.getState().setLastLlmMetrics('meta/llama-3.3-70b-instruct', 1234);
    expect(useAiStudio.getState().lastModel).toBe('meta/llama-3.3-70b-instruct');
    expect(useAiStudio.getState().lastLatencyMs).toBe(1234);
  });

  it('consumeTokens increases tokensConsumed (draining the budget display)', () => {
    useAiStudio.setState({ tokensConsumed: 0 });
    useAiStudio.getState().consumeTokens(30);
    expect(useAiStudio.getState().tokensConsumed).toBe(30);
  });

  it('setStreamingText feeds the ghost text', () => {
    useAiStudio.getState().setStreamingText('Hello from the model');
    expect(useAiStudio.getState().streamingText).toBe('Hello from the model');
  });

  it('commitStream promotes ghost text into committed ink', () => {
    useAiStudio.setState({ streamingText: 'First draft', committedText: '' });
    useAiStudio.getState().commitStream();
    expect(useAiStudio.getState().committedText).toBe('First draft');
    expect(useAiStudio.getState().streamingText).toBe('');
  });

  it('commitStream appends consecutive streams and ignores empty ghost', () => {
    useAiStudio.setState({ streamingText: 'part one', committedText: 'intro' });
    useAiStudio.getState().commitStream();
    expect(useAiStudio.getState().committedText).toBe('intro part one');

    const before = useAiStudio.getState().committedText;
    useAiStudio.setState({ streamingText: '   ' });
    useAiStudio.getState().commitStream();
    expect(useAiStudio.getState().committedText).toBe(before);
  });

  it('reset clears the streaming ghost', () => {
    useAiStudio.setState({ isActive: true, isRetrieving: true, streamingText: 'draft' });
    useAiStudio.getState().reset();
    const s = useAiStudio.getState();
    expect(s.isActive).toBe(false);
    expect(s.isRetrieving).toBe(false);
    expect(s.streamingText).toBe('');
  });
});

describe('TactileThinkingSliders', () => {
  it('renders dial labels, LLM panel and creativity presets', () => {
    render(<TactileThinkingSliders />);
    expect(screen.getByText('Creativity Weight')).toBeTruthy();
    expect(screen.getByText('Token Budget')).toBeTruthy();
    expect(screen.getByText('LLM')).toBeTruthy();
    expect(screen.getByText('Low')).toBeTruthy();
    expect(screen.getByText('Normal')).toBeTruthy();
    expect(screen.getByText('High')).toBeTruthy();
  });

  it('clicking High sets creativity level', () => {
    render(<TactileThinkingSliders />);
    fireEvent.click(screen.getByText('High'));
    expect(useAiStudio.getState().creativityLevel).toBe('high');
  });
});
