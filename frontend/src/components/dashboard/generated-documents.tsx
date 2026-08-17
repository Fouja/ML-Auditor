'use client';

import React, { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import { toast } from '@/hooks/use-toast';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Check,
  FileDown,
  FileText,
  Loader2,
  Pencil,
  Presentation,
  RefreshCw,
  Sparkles,
  Trash2,
  X,
} from 'lucide-react';

interface GeneratedDoc {
  id: string;
  note_id: string;
  title: string;
  content: string;
  doc_format: string;
  file_format: string;
  style: string;
  created_at: string;
  updated_at: string;
}

const FORMAT_LABELS: Record<string, string> = {
  presentation: 'Presentation',
  article: 'Article',
  book_chapter: 'Book Chapter',
};

export function GeneratedDocuments() {
  const [docs, setDocs] = useState<GeneratedDoc[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  const [selected, setSelected] = useState<GeneratedDoc | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [regenerating, setRegenerating] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);

  const fetchDocs = useCallback(async () => {
    try {
      const params: any = {};
      if (filter) params.doc_format = filter;
      const response = await api.get('/workspace/generated-documents', { params });
      setDocs(response.data);
    } catch {
      toast({ title: 'Error', description: 'Failed to load generated documents', variant: 'error' });
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    fetchDocs();
  }, [fetchDocs]);

  const handleRename = async (docId: string) => {
    if (!editTitle.trim()) return;
    try {
      const response = await api.put(`/workspace/generated-documents/${docId}`, { title: editTitle });
      setDocs(prev => prev.map(d => (d.id === docId ? response.data : d)));
      if (selected?.id === docId) setSelected(response.data);
      setEditingId(null);
      toast({ title: 'Saved', description: 'Document renamed', variant: 'default' });
    } catch {
      toast({ title: 'Error', description: 'Failed to rename document', variant: 'error' });
    }
  };

  const handleDelete = async (doc: GeneratedDoc) => {
    if (!window.confirm(`Delete "${doc.title}"?`)) return;
    try {
      await api.delete(`/workspace/generated-documents/${doc.id}`);
      setDocs(prev => prev.filter(d => d.id !== doc.id));
      if (selected?.id === doc.id) setSelected(null);
      toast({ title: 'Deleted', description: 'Document deleted', variant: 'default' });
    } catch {
      toast({ title: 'Error', description: 'Failed to delete document', variant: 'error' });
    }
  };

  const handleRegenerate = async (doc: GeneratedDoc) => {
    setRegenerating(doc.id);
    try {
      const response = await api.post(`/workspace/generated-documents/${doc.id}/regenerate`, {
        target_format: doc.doc_format,
        style: doc.style,
      });
      setDocs(prev => prev.map(d => (d.id === doc.id ? response.data : d)));
      if (selected?.id === doc.id) setSelected(response.data);
      toast({ title: 'Regenerated', description: 'Document regenerated', variant: 'success' });
    } catch {
      toast({ title: 'Error', description: 'Regeneration failed. Check your AI model configuration.', variant: 'error' });
    } finally {
      setRegenerating(null);
    }
  };

  const handleDownload = async (doc: GeneratedDoc, format: string) => {
    setDownloading(doc.id);
    try {
      const response = await api.get(`/workspace/generated-documents/${doc.id}/download`, {
        params: { format },
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.download = `${doc.title.replace(/\s+/g, '_')}.${format}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      toast({ title: 'Error', description: 'Download failed', variant: 'error' });
    } finally {
      setDownloading(null);
    }
  };

  const filteredDocs = filter ? docs.filter(d => d.doc_format === filter) : docs;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">My Generated Documents</h1>
          <p className="text-muted-foreground">Presentations and articles generated from your notes.</p>
        </div>
        <div className="flex gap-2">
          {[
            { value: '', label: 'All' },
            { value: 'presentation', label: 'Presentations' },
            { value: 'article', label: 'Articles' },
          ].map((f) => (
            <Button
              key={f.value || 'all'}
              size="sm"
              variant={filter === f.value ? 'default' : 'outline'}
              onClick={() => setFilter(f.value)}
            >
              {f.label}
            </Button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-40 animate-pulse rounded-lg border bg-muted" />
          ))}
        </div>
      ) : filteredDocs.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16 text-center">
          <Sparkles className="h-10 w-10 text-muted-foreground opacity-50" />
          <p className="mt-3 text-sm font-medium">No generated documents yet</p>
          <p className="text-sm text-muted-foreground">
            Open a note in the Notes section and click Generate to create your first one.
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredDocs.map((doc) => (
            <div
              key={doc.id}
              className={`cursor-pointer rounded-lg border p-4 transition-colors hover:border-primary/50 ${
                selected?.id === doc.id ? 'border-primary bg-primary/5' : ''
              }`}
              onClick={() => setSelected(doc)}
            >
              <div className="flex items-start justify-between gap-2">
                <div className={`h-9 w-9 rounded-md flex items-center justify-center ${
                  doc.doc_format === 'presentation' ? 'bg-blue-500/15 text-blue-500' : 'bg-green-500/15 text-green-500'
                }`}>
                  {doc.doc_format === 'presentation' ? <Presentation className="h-4 w-4" /> : <FileText className="h-4 w-4" />}
                </div>
                {editingId === doc.id ? (
                  <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                    <Input
                      autoFocus
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleRename(doc.id);
                        if (e.key === 'Escape') setEditingId(null);
                      }}
                      className="h-7 w-40 text-xs"
                    />
                    <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => handleRename(doc.id)}>
                      <Check className="h-3 w-3" />
                    </Button>
                    <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => setEditingId(null)}>
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                ) : (
                  <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-7 w-7"
                      title="Rename"
                      onClick={() => { setEditingId(doc.id); setEditTitle(doc.title); }}
                    >
                      <Pencil className="h-3 w-3" />
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-7 w-7"
                      title="Regenerate"
                      disabled={regenerating === doc.id}
                      onClick={() => handleRegenerate(doc)}
                    >
                      {regenerating === doc.id ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-7 w-7 text-destructive"
                      title="Delete"
                      onClick={() => handleDelete(doc)}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                )}
              </div>
              <h3 className="mt-3 truncate text-sm font-semibold">{doc.title}</h3>
              <p className="text-xs text-muted-foreground">
                {FORMAT_LABELS[doc.doc_format] || doc.doc_format} · {doc.style} · {doc.file_format.toUpperCase()}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Updated {new Date(doc.updated_at).toLocaleDateString()}
              </p>
              <div className="mt-3 flex gap-1.5" onClick={(e) => e.stopPropagation()}>
                {doc.doc_format === 'presentation' ? (
                  <>
                    <Button size="sm" variant="outline" className="h-7 text-xs gap-1" disabled={downloading === doc.id} onClick={() => handleDownload(doc, 'pptx')}>
                      {downloading === doc.id ? <Loader2 className="h-3 w-3 animate-spin" /> : <FileDown className="h-3 w-3" />}
                      PPTX
                    </Button>
                    <Button size="sm" variant="outline" className="h-7 text-xs gap-1" disabled={downloading === doc.id} onClick={() => handleDownload(doc, 'md')}>
                      MD
                    </Button>
                  </>
                ) : (
                  <>
                    <Button size="sm" variant="outline" className="h-7 text-xs gap-1" disabled={downloading === doc.id} onClick={() => handleDownload(doc, 'docx')}>
                      {downloading === doc.id ? <Loader2 className="h-3 w-3 animate-spin" /> : <FileDown className="h-3 w-3" />}
                      DOCX
                    </Button>
                    <Button size="sm" variant="outline" className="h-7 text-xs gap-1" disabled={downloading === doc.id} onClick={() => handleDownload(doc, 'md')}>
                      MD
                    </Button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {selected && (
        <div className="rounded-lg border bg-card">
          <div className="flex items-center justify-between border-b p-4">
            <div>
              <h2 className="text-lg font-bold">{selected.title}</h2>
              <p className="text-xs text-muted-foreground">
                {FORMAT_LABELS[selected.doc_format] || selected.doc_format} · {selected.style} style
              </p>
            </div>
            <Button size="icon" variant="ghost" onClick={() => setSelected(null)}>
              <X className="h-4 w-4" />
            </Button>
          </div>
          <div className="whitespace-pre-wrap p-4 text-sm leading-relaxed">
            {selected.content}
          </div>
        </div>
      )}
    </div>
  );
}
