'use client';

import React, { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Plus, ExternalLink, Bookmark, CheckCircle } from 'lucide-react';

interface NewsArticle {
  id: string;
  title: string;
  url: string;
  summary: string;
  content?: string;
  author: string;
  published_at: string;
  is_read: boolean;
  is_bookmarked: boolean;
}

interface NewsFeed {
  id: string;
  name: string;
  url: string;
  feed_type: string;
}

export function NewsFeedWidget() {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [feeds, setFeeds] = useState<NewsFeed[]>([]);
  const [showAddFeed, setShowAddFeed] = useState(false);
  const [newFeed, setNewFeed] = useState({ name: '', url: '' });
  const [selectedArticle, setSelectedArticle] = useState<NewsArticle | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchFeeds();
    fetchArticles();
  }, []);

  const fetchFeeds = async () => {
    try {
      const response = await api.get('/workspace/feeds');
      setFeeds(response.data);
    } catch (error) {
      console.error('Failed to fetch feeds:', error);
    }
  };

  const fetchArticles = async () => {
    try {
      const response = await api.get('/workspace/articles', {
        params: { limit: 20, is_read: false },
      });
      setArticles(response.data);
    } catch (error) {
      console.error('Failed to fetch articles:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddFeed = async () => {
    if (!newFeed.name || !newFeed.url) return;

    try {
      const response = await api.post('/workspace/feeds', {
        ...newFeed,
        feed_type: 'webpage',
        scrape_interval_minutes: 60,
      });
      setFeeds(prev => [...prev, response.data]);
      setShowAddFeed(false);
      setNewFeed({ name: '', url: '' });
    } catch (error) {
      console.error('Failed to add feed:', error);
    }
  };

  const handleMarkRead = async (articleId: string) => {
    try {
      await api.put(`/workspace/articles/${articleId}/read`);
      setArticles(prev => prev.map(a =>
        a.id === articleId ? { ...a, is_read: true } : a
      ));
    } catch (error) {
      console.error('Failed to mark as read:', error);
    }
  };

  const handleBookmark = async (articleId: string) => {
    try {
      const response = await api.put(`/workspace/articles/${articleId}/bookmark`);
      setArticles(prev => prev.map(a =>
        a.id === articleId ? { ...a, is_bookmarked: response.data.is_bookmarked } : a
      ));
    } catch (error) {
      console.error('Failed to toggle bookmark:', error);
    }
  };

  if (loading) {
    return <div className="p-4 text-sm text-muted-foreground">Loading articles...</div>;
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b">
        <span className="text-sm font-medium">
          {feeds.length} feed{feeds.length !== 1 ? 's' : ''} • {articles.length} unread
        </span>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowAddFeed(true)}
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      {/* Articles list */}
      <div className="flex-1 overflow-auto p-2 space-y-1">
        {articles.length === 0 ? (
          <div className="text-center text-muted-foreground py-8">
            <p className="text-sm">No articles yet</p>
            <p className="text-xs">Add a feed to get started</p>
          </div>
        ) : (
          articles.map(article => (
            <div
              key={article.id}
              className={`p-2 rounded cursor-pointer hover:bg-muted transition-colors ${
                selectedArticle?.id === article.id ? 'bg-muted' : ''
              }`}
              onClick={() => setSelectedArticle(article)}
            >
              <div className="flex items-start gap-2">
                <div className="flex-1 min-w-0">
                  <p className={`text-sm font-medium line-clamp-2 ${
                    article.is_read ? 'text-muted-foreground' : ''
                  }`}>
                    {article.title}
                  </p>
                  {article.summary && (
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                      {article.summary}
                    </p>
                  )}
                  <div className="flex items-center gap-2 mt-1">
                    {article.author && (
                      <span className="text-xs text-muted-foreground">{article.author}</span>
                    )}
                    {article.published_at && (
                      <span className="text-xs text-muted-foreground">
                        • {new Date(article.published_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex flex-col gap-1">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleBookmark(article.id);
                    }}
                    className="p-1 hover:bg-muted rounded"
                  >
                    <Bookmark
                      className={`h-3 w-3 ${
                        article.is_bookmarked ? 'fill-primary text-primary' : 'text-muted-foreground'
                      }`}
                    />
                  </button>
                  {!article.is_read && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleMarkRead(article.id);
                      }}
                      className="p-1 hover:bg-muted rounded"
                    >
                      <CheckCircle className="h-3 w-3 text-muted-foreground" />
                    </button>
                  )}
                  <a
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="p-1 hover:bg-muted rounded"
                  >
                    <ExternalLink className="h-3 w-3 text-muted-foreground" />
                  </a>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Article detail modal */}
      {selectedArticle && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-card rounded-lg p-4 w-[500px] max-h-[80vh] overflow-auto">
            <div className="flex items-start justify-between mb-4">
              <h3 className="font-medium pr-4">{selectedArticle.title}</h3>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedArticle(null)}
              >
                ×
              </Button>
            </div>
            {selectedArticle.summary && (
              <p className="text-sm text-muted-foreground mb-4">{selectedArticle.summary}</p>
            )}
            {selectedArticle.content && (
              <div className="text-sm mb-4 whitespace-pre-wrap">{selectedArticle.content}</div>
            )}
            <div className="flex gap-2">
              <a
                href={selectedArticle.url}
                target="_blank"
                rel="noopener noreferrer"
              >
                <Button variant="outline" size="sm">
                  <ExternalLink className="h-4 w-4 mr-1" />
                  Open Original
                </Button>
              </a>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleMarkRead(selectedArticle.id)}
              >
                Mark as Read
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Add Feed Modal */}
      {showAddFeed && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-card rounded-lg p-4 w-80 space-y-3">
            <h3 className="font-medium">Add News Feed</h3>
            <Input
              placeholder="Feed name"
              value={newFeed.name}
              onChange={(e) => setNewFeed({ ...newFeed, name: e.target.value })}
            />
            <Input
              placeholder="URL to scrape"
              value={newFeed.url}
              onChange={(e) => setNewFeed({ ...newFeed, url: e.target.value })}
            />
            <div className="flex gap-2">
              <Button onClick={handleAddFeed}>Add</Button>
              <Button variant="ghost" onClick={() => setShowAddFeed(false)}>
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
