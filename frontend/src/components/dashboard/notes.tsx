'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import api from '@/lib/api';
import { toast } from '@/hooks/use-toast';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Plus, Pin, PinOff, Trash2, FileText, BookOpen, Presentation, Newspaper, Sparkles, Loader2, X } from 'lucide-react';

const FORMATS = [
  { value: 'note', label: 'Note', icon: FileText, color: 'text-slate-500' },
  { value: 'book_chapter', label: 'Book Chapter', icon: BookOpen, color: 'text-amber-500' },
  { value: 'presentation', label: 'Presentation', icon: Presentation, color: 'text-blue-500' },
  { value: 'article', label: 'Article', icon: Newspaper, color: 'text-green-500' },
];

interface Note {
  id: string;
  title: string;
  content: string;
  format: string;
  tags: string[];
  is_pinned: boolean;
  created_at: string;
  updated_at: string;
}

const FORMAT_LABELS: Record<string, string> = {
  note: 'Note',
  book_chapter: 'Book Chapter',
  presentation: 'Presentation',
  article: 'Article',
};

export function Notes() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [selectedNote, setSelectedNote] = useState<Note | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterFormat, setFilterFormat] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generateResult, setGenerateResult] = useState<{ title: string; content: string; id: string } | null>(null);

  const fetchNotes = useCallback(async () => {
    try {
      const params: any = {};
      if (filterFormat) params.format = filterFormat;
      const response = await api.get('/workspace/notes', { params });
      setNotes(response.data);
    } catch {
      toast({ title: 'Error', description: 'Failed to load notes', variant: 'error' });
    } finally {
      setLoading(false);
    }
  }, [filterFormat]);

  useEffect(() => {
    fetchNotes();
  }, [fetchNotes]);

  const handleCreateNote = async () => {
    try {
      const response = await api.post('/workspace/notes', {
        title: 'Untitled Note',
        content: '',
        format: 'note',
        tags: [],
      });
      const newNote = response.data;
      setNotes(prev => [newNote, ...prev]);
      setSelectedNote(newNote);
    } catch {
      toast({ title: 'Error', description: 'Failed to create note', variant: 'error' });
    }
  };

  const handleUpdateNote = async (noteId: string, updates: Partial<Note>) => {
    try {
      const response = await api.put(`/workspace/notes/${noteId}`, updates);
      const updated = response.data;
      setNotes(prev => prev.map(n => n.id === noteId ? updated : n));
      if (selectedNote?.id === noteId) setSelectedNote(updated);
    } catch {
      toast({ title: 'Error', description: 'Failed to update note', variant: 'error' });
    }
  };

  const handleDeleteNote = async (noteId: string) => {
    try {
      await api.delete(`/workspace/notes/${noteId}`);
      setNotes(prev => prev.filter(n => n.id !== noteId));
      if (selectedNote?.id === noteId) setSelectedNote(null);
      toast({ title: 'Deleted', description: 'Note deleted', variant: 'default' });
    } catch {
      toast({ title: 'Error', description: 'Failed to delete note', variant: 'error' });
    }
  };

  const handleTogglePin = async (note: Note) => {
    await handleUpdateNote(note.id, { is_pinned: !note.is_pinned } as any);
  };

  const handleGenerate = async (targetFormat: string) => {
    if (!selectedNote) return;
    setIsGenerating(true);
    setGenerateResult(null);
    try {
      const response = await api.post(`/workspace/notes/${selectedNote.id}/generate`, {
        target_format: targetFormat,
        style: 'professional',
      });
      setGenerateResult({ title: response.data.title, content: response.data.content, id: response.data.id });
      toast({ title: 'Generated', description: `${targetFormat.replace('_', ' ')} created successfully`, variant: 'success' });
    } catch {
      setGenerateResult({ title: '', content: 'Generation failed. Make sure an AI model is configured.', id: '' });
      toast({ title: 'Error', description: 'Failed to generate. Check your AI model configuration.', variant: 'error' });
    } finally {
      setIsGenerating(false);
    }
  };

  const filteredNotes = notes.filter(n =>
    !searchQuery || n.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    n.content.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const pinnedNotes = filteredNotes.filter(n => n.is_pinned);
  const unpinnedNotes = filteredNotes.filter(n => !n.is_pinned);

  return (
    <div className="flex h-full">
      {/* Note List */}
      <div className="w-72 border-r flex flex-col">
        <div className="p-3 border-b space-y-2">
          <div className="flex items-center gap-2">
            <Input
              placeholder="Search notes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-8 text-sm"
            />
            <Button size="sm" onClick={handleCreateNote} className="h-8">
              <Plus className="h-4 w-4" />
            </Button>
          </div>
          <div className="flex gap-1">
            {FORMATS.map(f => (
              <button
                key={f.value}
                onClick={() => setFilterFormat(filterFormat === f.value ? '' : f.value)}
                className={`p-1 rounded text-xs transition-colors ${
                  filterFormat === f.value ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted'
                }`}
                title={f.label}
              >
                <f.icon className="h-3.5 w-3.5" />
              </button>
            ))}
          </div>
        </div>
        <div className="flex-1 overflow-auto p-2 space-y-1">
          {loading ? (
            <div className="text-sm text-muted-foreground p-2">Loading notes...</div>
          ) : notes.length === 0 ? (
            <div className="text-sm text-muted-foreground p-2">No notes yet. Create one!</div>
          ) : filteredNotes.length === 0 ? (
            <div className="text-sm text-muted-foreground p-2">No notes match your {searchQuery ? 'search' : 'format filter'}.</div>
          ) : (
            <>
              {pinnedNotes.map(note => (
                <NoteListItem
                  key={note.id}
                  note={note}
                  isSelected={selectedNote?.id === note.id}
                  onSelect={setSelectedNote}
                />
              ))}
              {pinnedNotes.length > 0 && unpinnedNotes.length > 0 && (
                <div className="border-t my-1" />
              )}
              {unpinnedNotes.map(note => (
                <NoteListItem
                  key={note.id}
                  note={note}
                  isSelected={selectedNote?.id === note.id}
                  onSelect={setSelectedNote}
                />
              ))}
            </>
          )}
        </div>
      </div>

      {/* Note Editor */}
      <div className="flex-1 flex flex-col">
        {selectedNote ? (
          <>
            <div className="flex items-center gap-2 p-3 border-b flex-wrap">
              <select
                value={selectedNote.format}
                onChange={(e) => handleUpdateNote(selectedNote.id, { format: e.target.value } as any)}
                className="h-8 text-xs rounded-md border border-input bg-background px-2"
              >
                {FORMATS.map(f => (
                  <option key={f.value} value={f.value}>{f.label}</option>
                ))}
              </select>
              <div className="flex items-center gap-1 flex-1 min-w-0">
                {(selectedNote.tags || []).map((tag, i) => (
                  <span key={i} className="inline-flex items-center gap-1 bg-muted text-muted-foreground text-xs rounded px-1.5 py-0.5">
                    {tag}
                    <button
                      onClick={() => {
                        const newTags = selectedNote.tags.filter((_: string, j: number) => j !== i);
                        handleUpdateNote(selectedNote.id, { tags: newTags } as any);
                        setSelectedNote({ ...selectedNote, tags: newTags });
                      }}
                      className="hover:text-destructive"
                    >
                      <X className="h-2.5 w-2.5" />
                    </button>
                  </span>
                ))}
                <input
                  placeholder="Add tag..."
                  className="h-6 text-xs bg-transparent border-none outline-none min-w-[60px] flex-1"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && (e.target as HTMLInputElement).value.trim()) {
                      const newTag = (e.target as HTMLInputElement).value.trim();
                      if (!(selectedNote.tags || []).includes(newTag)) {
                        const newTags = [...(selectedNote.tags || []), newTag];
                        handleUpdateNote(selectedNote.id, { tags: newTags } as any);
                        setSelectedNote({ ...selectedNote, tags: newTags });
                      }
                      (e.target as HTMLInputElement).value = '';
                    }
                  }}
                  onBlur={(e) => {
                    if (e.target.value.trim()) {
                      const newTag = e.target.value.trim();
                      if (!(selectedNote.tags || []).includes(newTag)) {
                        const newTags = [...(selectedNote.tags || []), newTag];
                        handleUpdateNote(selectedNote.id, { tags: newTags } as any);
                        setSelectedNote({ ...selectedNote, tags: newTags });
                      }
                      e.target.value = '';
                    }
                  }}
                />
              </div>
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7"
                  onClick={() => handleTogglePin(selectedNote)}
                  title={selectedNote.is_pinned ? 'Unpin' : 'Pin'}
                >
                  {selectedNote.is_pinned ? <PinOff className="h-3.5 w-3.5" /> : <Pin className="h-3.5 w-3.5" />}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-destructive"
                  onClick={() => handleDeleteNote(selectedNote.id)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
            <div className="flex-1 p-3 space-y-3 overflow-auto">
              <Input
                value={selectedNote.title}
                onChange={(e) => setSelectedNote({ ...selectedNote, title: e.target.value })}
                onBlur={() => handleUpdateNote(selectedNote.id, { title: selectedNote.title })}
                className="text-lg font-semibold border-none px-0 focus-visible:ring-0"
                placeholder="Note title..."
              />
              <textarea
                value={selectedNote.content}
                onChange={(e) => setSelectedNote({ ...selectedNote, content: e.target.value })}
                onBlur={() => handleUpdateNote(selectedNote.id, { content: selectedNote.content })}
                className="w-full h-[calc(100%-4rem)] resize-none bg-transparent border-none focus:outline-none text-sm leading-relaxed"
                placeholder="Start writing..."
              />
            </div>
            {/* Generate Actions */}
            <div className="border-t p-3">
              <p className="text-xs text-muted-foreground mb-2">Generate from this note:</p>
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="outline" className="h-7 text-xs gap-1" onClick={() => handleGenerate('presentation')} disabled={isGenerating}>
                  <Presentation className="h-3 w-3" />
                  {isGenerating ? 'Generating...' : 'Presentation'}
                </Button>
                <Button size="sm" variant="outline" className="h-7 text-xs gap-1" onClick={() => handleGenerate('book_chapter')} disabled={isGenerating}>
                  <BookOpen className="h-3 w-3" />
                  {isGenerating ? 'Generating...' : 'Chapter'}
                </Button>
                <Button size="sm" variant="outline" className="h-7 text-xs gap-1" onClick={() => handleGenerate('article')} disabled={isGenerating}>
                  <Newspaper className="h-3 w-3" />
                  {isGenerating ? 'Generating...' : 'Article'}
                </Button>
              </div>
              {generateResult && (
                <div className="mt-3 p-3 bg-muted rounded-md text-sm max-h-60 overflow-y-auto">
                  <div className="flex items-center gap-1 text-xs text-muted-foreground mb-2">
                    <Sparkles className="h-3 w-3 text-primary" />
                    Generated output
                    {generateResult.id && (
                      <Link href="/dashboard/generated" className="ml-auto text-primary hover:underline">
                        Open in Generated
                      </Link>
                    )}
                  </div>
                  <div className="whitespace-pre-wrap">{generateResult.content}</div>
                </div>
              )}
              {isGenerating && (
                <div className="mt-3 flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Generating...
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground">
            <div className="text-center space-y-2">
              <FileText className="h-8 w-8 mx-auto opacity-50" />
              <p>Select a note or create a new one</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function NoteListItem({ note, isSelected, onSelect }: { note: Note; isSelected: boolean; onSelect: (n: Note) => void }) {
  const FormatIcon = FORMATS.find(f => f.value === note.format)?.icon || FileText;
  const formatColor = FORMATS.find(f => f.value === note.format)?.color || 'text-slate-500';

  return (
    <button
      onClick={() => onSelect(note)}
      className={`w-full text-left p-2 rounded-md text-sm transition-colors ${
        isSelected ? 'bg-primary/10 text-primary' : 'hover:bg-muted'
      }`}
    >
      <div className="flex items-start gap-2">
        <FormatIcon className={`h-3.5 w-3.5 mt-0.5 ${formatColor}`} />
        <div className="flex-1 min-w-0">
          <p className="truncate font-medium text-xs">{note.title}</p>
          <p className="truncate text-xs text-muted-foreground mt-0.5">
            {note.content?.slice(0, 60) || 'Empty'}
          </p>
          {(note.tags || []).length > 0 && (
            <div className="flex gap-1 mt-1 flex-wrap">
              {note.tags.slice(0, 3).map((tag, i) => (
                <span key={i} className="text-[10px] bg-muted text-muted-foreground rounded px-1">{tag}</span>
              ))}
              {note.tags.length > 3 && (
                <span className="text-[10px] text-muted-foreground">+{note.tags.length - 3}</span>
              )}
            </div>
          )}
        </div>
        {note.is_pinned && <Pin className="h-3 w-3 text-muted-foreground flex-shrink-0" />}
      </div>
    </button>
  );
}
