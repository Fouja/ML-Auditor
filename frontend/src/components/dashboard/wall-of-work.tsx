'use client';

import React, { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';
import { Plus, MoreHorizontal, Calendar, Tag, Trash2, ArrowRight, AlertTriangle } from 'lucide-react';

interface Task {
  id: string;
  title: string;
  description: string;
  status: string;
  priority: string;
  due_date?: string;
  tags: string[];
  position: number;
}

const COLUMNS = [
  { id: 'todo', title: 'To Do', color: 'bg-slate-500', icon: '📋' },
  { id: 'in_progress', title: 'In Progress', color: 'bg-blue-500', icon: '🔨' },
  { id: 'review', title: 'Review', color: 'bg-yellow-500', icon: '👀' },
  { id: 'done', title: 'Done', color: 'bg-green-500', icon: '✅' },
];

const PRIORITY_COLORS: Record<string, string> = {
  low: 'bg-slate-100 text-slate-600 border-slate-200',
  medium: 'bg-blue-100 text-blue-700 border-blue-200',
  high: 'bg-orange-100 text-orange-700 border-orange-200',
  critical: 'bg-red-100 text-red-700 border-red-200',
};

const PRIORITY_DOTS: Record<string, string> = {
  low: 'bg-slate-400',
  medium: 'bg-blue-500',
  high: 'bg-orange-500',
  critical: 'bg-red-500',
};

const PRIORITY_OPTIONS = ['low', 'medium', 'high', 'critical'];

export function WallOfWork() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [addingToColumn, setAddingToColumn] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [draggedTask, setDraggedTask] = useState<string | null>(null);
  const [dragOverColumn, setDragOverColumn] = useState<string | null>(null);

  useEffect(() => {
    fetchTasks();
  }, []);

  const fetchTasks = useCallback(async () => {
    try {
      const response = await api.get('/workspace/tasks');
      setTasks(response.data);
    } catch (error) {
      console.error('Failed to fetch tasks:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleAddTask = async (status: string) => {
    if (!newTaskTitle.trim()) return;
    try {
      const response = await api.post('/workspace/tasks', {
        title: newTaskTitle,
        status,
        priority: 'medium',
      });
      setTasks(prev => [...prev, response.data]);
      setNewTaskTitle('');
      setAddingToColumn(null);
    } catch (error) {
      console.error('Failed to create task:', error);
    }
  };

  const handleMoveTask = async (taskId: string, newStatus: string) => {
    try {
      await api.put(`/workspace/tasks/${taskId}/move`, null, {
        params: { status: newStatus, position: 0 },
      });
      setTasks(prev => prev.map(t =>
        t.id === taskId ? { ...t, status: newStatus } : t
      ));
    } catch (error) {
      console.error('Failed to move task:', error);
    }
  };

  const handleUpdatePriority = async (taskId: string, priority: string) => {
    try {
      await api.put(`/workspace/tasks/${taskId}`, { priority });
      setTasks(prev => prev.map(t =>
        t.id === taskId ? { ...t, priority } : t
      ));
    } catch (error) {
      console.error('Failed to update task:', error);
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    try {
      await api.delete(`/workspace/tasks/${taskId}`);
      setTasks(prev => prev.filter(t => t.id !== taskId));
    } catch (error) {
      console.error('Failed to delete task:', error);
    }
  };

  const handleDragStart = (taskId: string) => setDraggedTask(taskId);

  const handleDragOver = (e: React.DragEvent, columnId: string) => {
    e.preventDefault();
    setDragOverColumn(columnId);
  };

  const handleDragLeave = () => setDragOverColumn(null);

  const handleDrop = (columnId: string) => {
    if (draggedTask) handleMoveTask(draggedTask, columnId);
    setDraggedTask(null);
    setDragOverColumn(null);
  };

  const getTasksByStatus = (status: string) =>
    tasks.filter(t => t.status === status).sort((a, b) => a.position - b.position);

  const stats = {
    total: tasks.length,
    todo: getTasksByStatus('todo').length,
    in_progress: getTasksByStatus('in_progress').length,
    review: getTasksByStatus('review').length,
    done: getTasksByStatus('done').length,
    overdue: tasks.filter(t => t.due_date && new Date(t.due_date) < new Date() && t.status !== 'done').length,
  };

  if (loading) {
    return <div className="p-4 text-sm text-muted-foreground">Loading tasks...</div>;
  }

  return (
    <div className="flex flex-col h-full">
      {/* Stats Bar */}
      <div className="flex items-center gap-4 px-4 py-2 border-b text-xs text-muted-foreground">
        <span className="font-medium">{stats.total} tasks</span>
        <span>{stats.in_progress} in progress</span>
        <span>{stats.review} in review</span>
        <span>{stats.done} done</span>
        {stats.overdue > 0 && (
          <span className="text-destructive flex items-center gap-1 font-medium">
            <AlertTriangle className="h-3 w-3" />
            {stats.overdue} overdue
          </span>
        )}
      </div>

      {/* Kanban Board */}
      <div className="flex gap-3 p-3 overflow-x-auto flex-1">
        {COLUMNS.map(column => (
          <div
            key={column.id}
            className={cn(
              'flex-1 min-w-[220px] rounded-xl transition-colors',
              dragOverColumn === column.id && 'bg-accent/60 ring-1 ring-accent'
            )}
            onDragOver={(e) => handleDragOver(e, column.id)}
            onDragLeave={handleDragLeave}
            onDrop={() => handleDrop(column.id)}
          >
            <div className="flex items-center gap-2 mb-2 px-1">
              <div className={cn('w-2 h-2 rounded-full', column.color)} />
              <span className="text-sm font-medium">{column.title}</span>
              <span className="text-xs text-muted-foreground bg-muted px-1.5 rounded-full">
                {getTasksByStatus(column.id).length}
              </span>
            </div>

            <div className="space-y-2 min-h-[100px]">
              {getTasksByStatus(column.id).map(task => (
                <TaskCard
                  key={task.id}
                  task={task}
                  onDragStart={handleDragStart}
                  onDragEnd={() => setDraggedTask(null)}
                  onMove={handleMoveTask}
                  onDelete={handleDeleteTask}
                  onEditPriority={handleUpdatePriority}
                  isDragging={draggedTask === task.id}
                />
              ))}

              {addingToColumn === column.id ? (
                <div className="space-y-2 animate-fade-in">
                  <Input
                    value={newTaskTitle}
                    onChange={(e) => setNewTaskTitle(e.target.value)}
                    placeholder="Task title..."
                    className="text-sm"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleAddTask(column.id);
                      if (e.key === 'Escape') setAddingToColumn(null);
                    }}
                    autoFocus
                  />
                  <div className="flex gap-1">
                    <Button size="sm" onClick={() => handleAddTask(column.id)}>
                      Add
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => setAddingToColumn(null)}>
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full justify-start text-muted-foreground hover:text-foreground"
                  onClick={() => setAddingToColumn(column.id)}
                >
                  <Plus className="h-4 w-4 mr-1" />
                  Add task
                </Button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function TaskCard({
  task,
  onDragStart,
  onDragEnd,
  onMove,
  onDelete,
  onEditPriority,
  isDragging,
}: {
  task: Task;
  onDragStart: (id: string) => void;
  onDragEnd: () => void;
  onMove: (id: string, status: string) => void;
  onDelete: (id: string) => void;
  onEditPriority: (id: string, priority: string) => void;
  isDragging: boolean;
}) {
  const isOverdue = task.due_date && new Date(task.due_date) < new Date() && task.status !== 'done';

  return (
    <Card
      className={cn(
        'cursor-grab active:cursor-grabbing hover:-translate-y-0.5 hover:shadow-lg hover:border-primary/30',
        'transition-all duration-200 animate-fade-in-up',
        isDragging && 'opacity-50 scale-95 shadow-xl rotate-2',
        isOverdue && 'border-destructive/50'
      )}
      draggable
      onDragStart={() => onDragStart(task.id)}
      onDragEnd={onDragEnd}
    >
      <CardContent className="p-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{task.title}</p>
            {task.description && (
              <p className="text-xs text-muted-foreground truncate mt-1">
                {task.description}
              </p>
            )}
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                className="p-1.5 hover:bg-accent hover:text-accent-foreground rounded-lg transition-colors outline-none focus-visible:ring-2 ring-ring"
                aria-label="Task actions"
              >
                <MoreHorizontal className="h-4 w-4" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-44">
              <DropdownMenuLabel>Priority</DropdownMenuLabel>
              <DropdownMenuRadioGroup
                value={task.priority}
                onValueChange={(value) => onEditPriority(task.id, value)}
              >
                {PRIORITY_OPTIONS.map(p => (
                  <DropdownMenuRadioItem key={p} value={p} className="capitalize gap-2">
                    <span className={cn('h-1.5 w-1.5 rounded-full', PRIORITY_DOTS[p])} />
                    {p}
                  </DropdownMenuRadioItem>
                ))}
              </DropdownMenuRadioGroup>
              <DropdownMenuSeparator />
              <DropdownMenuSub>
                <DropdownMenuSubTrigger>
                  <ArrowRight className="h-4 w-4" />
                  Move to
                </DropdownMenuSubTrigger>
                <DropdownMenuSubContent>
                  {COLUMNS.filter(c => c.id !== task.status).map(column => (
                    <DropdownMenuItem
                      key={column.id}
                      onClick={() => onMove(task.id, column.id)}
                    >
                      <span className={cn('h-1.5 w-1.5 rounded-full', column.color)} />
                      {column.title}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuSubContent>
              </DropdownMenuSub>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-destructive focus:text-destructive focus:bg-destructive/10"
                onClick={() => onDelete(task.id)}
              >
                <Trash2 className="h-4 w-4" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        <div className="flex items-center gap-2 mt-2 flex-wrap">
          <Badge variant="outline" className={cn('capitalize', PRIORITY_COLORS[task.priority])}>
            {task.priority}
          </Badge>
          {task.due_date && (
            <span className={cn(
              'text-xs flex items-center gap-1',
              isOverdue ? 'text-destructive font-medium' : 'text-muted-foreground'
            )}>
              <Calendar className="h-3 w-3" />
              {new Date(task.due_date).toLocaleDateString()}
              {isOverdue && ' (overdue)'}
            </span>
          )}
          {task.tags.length > 0 && (
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              <Tag className="h-3 w-3" />
              {task.tags.length}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
