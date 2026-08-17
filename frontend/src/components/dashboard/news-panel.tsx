'use client';

import React, { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';
import {
  Plus,
  ExternalLink,
  Bookmark,
  CheckCircle,
  Trash2,
  RefreshCw,
  Rss,
  Globe,
  MoreHorizontal,
  Newspaper,
  Clock,
  ImageOff,
} from 'lucide-react';

interface NewsArticle {
  id: string;
  title: string;
  url: string;
  summary: string;
  content?: string;
  image_url?: string;
  author: string;
  published_at: string;
  is_read: boolean;
  is_bookmarked: boolean;
  created_at: string;
}

interface NewsFeed {
  id: string;
  name: string;
  url: string;
  feed_type: string;
  is_active: boolean;
  last_scraped: string | null;
  created_at: string;
}

type Filter = 'all' | 'unread' | 'bookmarked';

function getDomain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return '';
  }
}

function getDomainInitials(domain: string): string {
  return domain
    .split('.')
    .filter(Boolean)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .slice(0, 2)
    .join('');
}

function ArticleImage({ article }: { article: NewsArticle }) {
  const [failed, setFailed] = useState(false);
  const domain = getDomain(article.url);
  const faviconUrl = domain
    ? `https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=128`
    : '';
  const src = article.image_url || faviconUrl;

  if (!src || failed) {
    const initials = getDomainInitials(domain);
    return (
      <div className="flex h-full w-full flex-col items-center justify-center bg-gradient-to-br from-muted to-muted/50 p-2 text-center">
        {initials ? (
          <>
            <span className="text-xl font-bold text-muted-foreground/60">{initials}</span>
            <span className="max-w-full truncate text-[10px] text-muted-foreground/60">{domain}</span>
          </>
        ) : (
          <ImageOff className="h-6 w-6 text-muted-foreground/40" />
        )}
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={article.title}
      className="h-full w-full object-cover group-hover:scale-105 transition-transform duration-300"
      onError={() => setFailed(true)}
    />
  );
}

export function NewsPanel() {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [feeds, setFeeds] = useState<NewsFeed[]>([]);
  const [filter, setFilter] = useState<Filter>('all');
  const [showAddFeed, setShowAddFeed] = useState(false);
  const [newFeed, setNewFeed] = useState({ name: '', url: '', feed_type: 'rss' });
  const [refreshingFeed, setRefreshingFeed] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchAll();
  }, []);

  const fetchAll = useCallback(async () => {
    try {
      const [feedsRes, articlesRes] = await Promise.all([
        api.get('/workspace/feeds'),
        api.get('/workspace/articles', { params: { limit: 50 } }),
      ]);
      setFeeds(feedsRes.data);
      setArticles(articlesRes.data);
    } catch (err) {
      console.error('Failed to fetch news data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleAddFeed = async () => {
    if (!newFeed.name.trim() || !newFeed.url.trim()) return;
    setError('');
    try {
      await api.post('/workspace/feeds', {
        name: newFeed.name.trim(),
        url: newFeed.url.trim(),
        feed_type: newFeed.feed_type,
        scrape_interval_minutes: 60,
      });
      setShowAddFeed(false);
      setNewFeed({ name: '', url: '', feed_type: 'rss' });
      await fetchAll();
    } catch (err) {
      setError('Failed to add feed. Check the URL and try again.');
    }
  };

  const handleDeleteFeed = async (feedId: string) => {
    if (!window.confirm('Delete this feed and its articles?')) return;
    try {
      await api.delete(`/workspace/feeds/${feedId}`);
      await fetchAll();
    } catch (err) {
      console.error('Failed to delete feed:', err);
    }
  };

  const handleRefreshFeed = async (feedId: string) => {
    setRefreshingFeed(feedId);
    try {
      await api.post(`/workspace/feeds/${feedId}/scrape`);
      await fetchAll();
    } catch (err) {
      console.error('Failed to refresh feed:', err);
    } finally {
      setRefreshingFeed(null);
    }
  };

  const handleMarkRead = async (articleId: string) => {
    try {
      await api.put(`/workspace/articles/${articleId}/read`);
      setArticles(prev => prev.map(a =>
        a.id === articleId ? { ...a, is_read: true } : a
      ));
    } catch (err) {
      console.error('Failed to mark as read:', err);
    }
  };

  const handleBookmark = async (articleId: string) => {
    try {
      const response = await api.put(`/workspace/articles/${articleId}/bookmark`);
      setArticles(prev => prev.map(a =>
        a.id === articleId ? { ...a, is_bookmarked: response.data.is_bookmarked } : a
      ));
    } catch (err) {
      console.error('Failed to toggle bookmark:', err);
    }
  };

  const filteredArticles = articles
    .filter(a => {
      if (filter === 'unread') return !a.is_read;
      if (filter === 'bookmarked') return a.is_bookmarked;
      return true;
    })
    .sort((a, b) => new Date(b.published_at || b.created_at).getTime() - new Date(a.published_at || a.created_at).getTime());

  if (loading) {
    return <div className="p-4 text-sm text-muted-foreground">Loading news...</div>;
  }

  return (
    <div className="flex flex-col h-full overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b sticky top-0 bg-background/95 backdrop-blur z-10">
        <div className="flex items-center gap-2">
          <Newspaper className="h-4 w-4 text-primary" />
          <span className="text-sm font-medium">Actualités</span>
          <span className="text-xs text-muted-foreground">
            {feeds.length} source{feeds.length !== 1 ? 's' : ''} • {articles.filter(a => !a.is_read).length} unread
          </span>
        </div>
        <Button size="sm" onClick={() => setShowAddFeed(true)}>
          <Plus className="h-4 w-4 mr-1" />
          Add source
        </Button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-1 px-4 py-2 border-b">
        {(['all', 'unread', 'bookmarked'] as Filter[]).map(f => (
          <button
            key={f}
            className={cn(
              'px-3 py-1 text-xs font-medium rounded-full transition-colors capitalize',
              filter === f
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:bg-muted'
            )}
            onClick={() => setFilter(f)}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Feeds */}
      <div className="px-4 pt-3">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">Sources</p>
        {feeds.length === 0 ? (
          <div className="text-sm text-muted-foreground border border-dashed rounded-lg p-4 text-center">
            No sources yet — add an RSS feed or any webpage (X, LinkedIn, blog...)
          </div>
        ) : (
          <div className="flex gap-2 overflow-x-auto pb-1">
            {feeds.map(feed => (
              <div
                key={feed.id}
                className="flex items-center gap-2 bg-card border rounded-lg px-3 py-2 min-w-[180px] animate-fade-in-up"
              >
                <div className={cn(
                  'flex items-center justify-center h-7 w-7 rounded-md shrink-0',
                  feed.feed_type === 'rss' ? 'bg-orange-100 text-orange-600' : 'bg-blue-100 text-blue-600'
                )}>
                  {feed.feed_type === 'rss' ? <Rss className="h-3.5 w-3.5" /> : <Globe className="h-3.5 w-3.5" />}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium truncate">{feed.name}</p>
                  <p className="text-[10px] text-muted-foreground flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {feed.last_scraped
                      ? new Date(feed.last_scraped).toLocaleDateString()
                      : 'never scraped'}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={() => handleRefreshFeed(feed.id)}
                  disabled={refreshingFeed === feed.id}
                  title="Refresh now"
                >
                  <RefreshCw className={cn('h-3.5 w-3.5', refreshingFeed === feed.id && 'animate-spin')} />
                </Button>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon" className="h-7 w-7">
                      <MoreHorizontal className="h-3.5 w-3.5" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => handleRefreshFeed(feed.id)}>
                      <RefreshCw className="h-4 w-4" />
                      Refresh now
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      className="text-destructive focus:text-destructive focus:bg-destructive/10"
                      onClick={() => handleDeleteFeed(feed.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                      Delete source
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Articles */}
      <div className="px-4 pt-4 pb-6">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">Articles</p>
        {filteredArticles.length === 0 ? (
          <div className="text-sm text-muted-foreground border border-dashed rounded-lg p-8 text-center">
            <Newspaper className="h-8 w-8 mx-auto mb-2 text-muted-foreground/40" />
            No articles{filter !== 'all' ? ` ${filter}` : ''}. Add a source or refresh it.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {filteredArticles.map(article => (
              <div
                key={article.id}
                className={cn(
                  'group bg-card border rounded-xl overflow-hidden flex flex-col transition-all duration-200',
                  'hover:-translate-y-0.5 hover:shadow-lg hover:border-primary/30 animate-fade-in-up',
                  article.is_read && 'opacity-70'
                )}
              >
                <div className="h-32 bg-muted relative overflow-hidden shrink-0">
                  <ArticleImage article={article} />
                  {!article.is_read && (
                    <span className="absolute left-2 top-2">
                      <Badge variant="secondary" className="bg-primary text-primary-foreground">
                        New
                      </Badge>
                    </span>
                  )}
                </div>

                <div className="p-3 flex flex-col flex-1 gap-1.5">
                  <p className="text-sm font-medium line-clamp-2 leading-snug">{article.title}</p>
                  {article.summary && (
                    <p className="text-xs text-muted-foreground line-clamp-3">{article.summary}</p>
                  )}
                  <div className="flex items-center gap-2 text-[10px] text-muted-foreground mt-auto pt-1">
                    {article.author && <span className="truncate max-w-[120px]">{article.author}</span>}
                    {article.published_at && (
                      <span>• {new Date(article.published_at).toLocaleDateString()}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-1 pt-1">
                    <a
                      href={article.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-1.5 hover:bg-accent rounded-md transition-colors"
                      title="Open original"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                    <button
                      onClick={() => handleBookmark(article.id)}
                      className="p-1.5 hover:bg-accent rounded-md transition-colors"
                      title={article.is_bookmarked ? 'Remove bookmark' : 'Bookmark'}
                    >
                      <Bookmark
                        className={cn(
                          'h-3.5 w-3.5',
                          article.is_bookmarked && 'fill-primary text-primary'
                        )}
                      />
                    </button>
                    {!article.is_read && (
                      <button
                        onClick={() => handleMarkRead(article.id)}
                        className="p-1.5 hover:bg-accent rounded-md transition-colors"
                        title="Mark as read"
                      >
                        <CheckCircle className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add Source Modal */}
      {showAddFeed && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 animate-fade-in">
          <div className="bg-card border rounded-xl p-5 w-[400px] space-y-4 shadow-2xl">
            <div>
              <h3 className="font-medium text-lg">Add News Source</h3>
              <p className="text-xs text-muted-foreground">
                Paste an RSS feed URL or any webpage (X, LinkedIn, blog...) — we&apos;ll scrape and summarize it daily.
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="feed-name">Name</Label>
              <Input
                id="feed-name"
                placeholder="e.g. Hacker News"
                value={newFeed.name}
                onChange={(e) => setNewFeed({ ...newFeed, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="feed-url">URL</Label>
              <Input
                id="feed-url"
                placeholder="https://..."
                value={newFeed.url}
                onChange={(e) => setNewFeed({ ...newFeed, url: e.target.value })}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleAddFeed();
                }}
              />
            </div>
            <div className="space-y-2">
              <Label>Type</Label>
              <div className="flex gap-2">
                {[
                  { value: 'rss', label: 'RSS Feed', icon: Rss },
                  { value: 'webpage', label: 'Webpage', icon: Globe },
                ].map(option => (
                  <button
                    key={option.value}
                    className={cn(
                      'flex items-center gap-2 flex-1 px-3 py-2 text-xs font-medium rounded-lg border transition-colors',
                      newFeed.feed_type === option.value
                        ? 'border-primary bg-primary/10 text-foreground'
                        : 'border-border text-muted-foreground hover:bg-muted'
                    )}
                    onClick={() => setNewFeed({ ...newFeed, feed_type: option.value })}
                  >
                    <option.icon className="h-3.5 w-3.5" />
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
            {error && <p className="text-xs text-destructive">{error}</p>}
            <div className="flex gap-2 justify-end pt-1">
              <Button variant="ghost" onClick={() => setShowAddFeed(false)}>
                Cancel
              </Button>
              <Button onClick={handleAddFeed}>
                <Plus className="h-4 w-4 mr-1" />
                Add source
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
