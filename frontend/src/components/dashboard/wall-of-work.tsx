'use client';

import React, { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Plus, GripVertical, Calendar, Tag, MoreHorizontal, Trash2, ArrowRight, Clock, AlertTriangle } from 'lucide-react';

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

const PRIORITY_OPTIONS = ['low', 'medium', 'high', 'critical'];

export function WallOfWork() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [addingToColumn, setAddingToColumn] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [draggedTask, setDraggedTask] = useState<string | null>(null);
  const [dragOverColumn, setDragOverColumn] = useState<string | null>(null);
  const [editingTask, setEditingTask] = useState<string | null>(null);
  const [editPriority, setEditPriority] = useState('medium');

  useEffect(() => {
    fetchTasks();
  }, []);

  const fetchTasks = async () => {
    try {
      const response = await api.get('/workspace/tasks');
      setTasks(response.data);
    } catch (error) {
      console.error('Failed to fetch tasks:', error);
    } finally {
      setLoading(false);
    }
  };

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
      setEditingTask(null);
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

  const handleDragStart = (taskId: string) => {
    setDraggedTask(taskId);
  };

  const handleDragOver = (e: React.DragEvent, columnId: string) => {
    e.preventDefault();
    setDragOverColumn(columnId);
  };

  const handleDragLeave = () => {
    setDragOverColumn(null);
  };

  const handleDrop = (columnId: string) => {
    if (draggedTask) {
      handleMoveTask(draggedTask, columnId);
    }
    setDraggedTask(null);
    setDragOverColumn(null);
  };

  const getTasksByStatus = (status: string) =>
    tasks.filter(t => t.status === status).sort((a, b) => a.position - b.position);

  const getStats = () => ({
    total: tasks.length,
    todo: getTasksByStatus('todo').length,
    in_progress: getTasksByStatus('in_progress').length,
    review: getTasksByStatus('review').length,
    done: getTasksByStatus('done').length,
    overdue: tasks.filter(t => t.due_date && new Date(t.due_date) < new Date() && t.status !== 'done').length,
  });

  if (loading) {
    return <div className="p-4 text-sm text-muted-foreground">Loading tasks...</div>;
  }

  const stats = getStats();

  return (
    <div className="flex flex-col h-full">
      {/* Stats Bar */}
      <div className="flex items-center gap-4 px-4 py-2 border-b text-xs text-muted-foreground">
        <span className="font-medium">{stats.total} tasks</span>
        <span>{stats.in_progress} in progress</span>
        <span>{stats.review} in review</span>
        <span>{stats.done} done</span>
        {stats.overdue > 0 && (
          <span className="text-orange-600 flex items-center gap-1">
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
            className={`flex-1 min-w-[220px] ${
              dragOverColumn === column.id ? 'bg-muted/50 rounded-lg' : ''
            }`}
            onDragOver={(e) => handleDragOver(e, column.id)}
            onDragLeave={handleDragLeave}
            onDrop={() => handleDrop(column.id)}
          >
            <div className="flex items-center gap-2 mb-2 px-1">
              <div className={`w-2 h-2 rounded-full ${column.color}`} />
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
                  isEditing={editingTask === task.id}
                  onToggleEdit={() => setEditingTask(editingTask === task.id ? null : task.id)}
                  editPriority={editPriority}
                  onEditPriorityChange={setEditPriority}
                  isDragging={draggedTask === task.id}
                />
              ))}

              {addingToColumn === column.id ? (
                <div className="space-y-2">
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
                  className="w-full justify-start text-muted-foreground"
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
  isEditing,
  onToggleEdit,
  editPriority,
  onEditPriorityChange,
  isDragging,
}: {
  task: Task;
  onDragStart: (id: string) => void;
  onDragEnd: () => void;
  onMove: (id: string, status: string) => void;
  onDelete: (id: string) => void;
  onEditPriority: (id: string, priority: string) => void;
  isEditing: boolean;
  onToggleEdit: () => void;
  editPriority: string;
  onEditPriorityChange: (p: string) => void;
  isDragging: boolean;
}) {
  const [showMenu, setShowMenu] = useState(false);

  const isOverdue = task.due_date && new Date(task.due_date) < new Date() && task.status !== 'done';

  return (
    <Card
      className={`cursor-grab active:cursor-grabbing hover:shadow-md transition-all ${
        isDragging ? 'opacity-50 scale-95' : ''
      } ${isOverdue ? 'border-orange-300' : ''}`}
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
          <div className="relative">
            <button
              onClick={onToggleEdit}
              className="p-1 hover:bg-muted rounded"
            >
              <MoreHorizontal className="h-4 w-4" />
            </button>
            {isEditing && (
              <div className="absolute right-0 top-8 z-10 bg-popover border rounded-md shadow-lg py-2 min-w-[140px]">
                <p className="px-3 text-xs font-medium text-muted-foreground mb-1">Priority</p>
                <div className="px-2 flex flex-wrap gap-1">
                  {PRIORITY_OPTIONS.map(p => (
                    <button
                      key={p}
                      className={`px-2 py-0.5 text-xs rounded border ${
                        task.priority === p ? 'ring-2 ring-primary' : ''
                      } ${PRIORITY_COLORS[p]}`}
                      onClick={() => onEditPriority(task.id, p)}
                    >
                      {p}
                    </button>
                  ))}
                </div>
                <hr className="my-2" />
                {COLUMNS.filter(c => c.id !== task.status).map(column => (
                  <button
                    key={column.id}
                    className="w-full px-3 py-1 text-sm text-left hover:bg-muted flex items-center gap-2"
                    onClick={() => {
                      onMove(task.id, column.id);
                      onToggleEdit();
                    }}
                  >
                    <ArrowRight className="h-3 w-3" />
                    Move to {column.title}
                  </button>
                ))}
                <hr className="my-1" />
                <button
                  className="w-full px-3 py-1 text-sm text-left text-destructive hover:bg-destructive/10 flex items-center gap-2"
                  onClick={() => {
                    onDelete(task.id);
                    onToggleEdit();
                  }}
                >
                  <Trash2 className="h-3 w-3" />
                  Delete
                </button>
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 mt-2 flex-wrap">
          <span className={`text-xs px-2 py-0.5 rounded-full border ${PRIORITY_COLORS[task.priority]}`}>
            {task.priority}
          </span>
          {task.due_date && (
            <span className={`text-xs flex items-center gap-1 ${isOverdue ? 'text-orange-600 font-medium' : 'text-muted-foreground'}`}>
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
