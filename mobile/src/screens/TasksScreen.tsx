import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  RefreshControl,
  Modal,
  TextInput,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { getTasks, createTask, updateTask, deleteTask } from '../api/workspace';
import { Task } from '../types';
import { colors, spacing, borderRadius, shadows } from '../theme';

const STATUS_COLORS: Record<string, string> = {
  todo: colors.textSecondary,
  in_progress: colors.primary,
  review: colors.warning,
  done: colors.success,
};

const PRIORITY_COLORS: Record<string, string> = {
  low: colors.textSecondary,
  medium: colors.secondary,
  high: colors.warning,
  critical: colors.error,
};

const STATUS_OPTIONS = ['todo', 'in_progress', 'review', 'done'];
const PRIORITY_OPTIONS = ['low', 'medium', 'high', 'critical'];

export function TasksScreen() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [editStatus, setEditStatus] = useState<string>('todo');
  const [editPriority, setEditPriority] = useState<string>('medium');

  const loadTasks = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getTasks();
      setTasks(data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  const handleCreate = async () => {
    if (!newTaskTitle.trim()) return;
    await createTask({ title: newTaskTitle.trim(), status: 'todo', priority: 'medium' });
    setNewTaskTitle('');
    setModalVisible(false);
    loadTasks();
  };

  const handleDelete = async (id: string) => {
    await deleteTask(id);
    loadTasks();
  };

  const openEdit = (task: Task) => {
    setEditingTask(task);
    setEditStatus(task.status);
    setEditPriority(task.priority);
  };

  const handleUpdate = async () => {
    if (!editingTask) return;
    await updateTask(editingTask.id, { status: editStatus as any, priority: editPriority as any });
    setEditingTask(null);
    loadTasks();
  };

  const quickSetStatus = async (id: string, status: string) => {
    await updateTask(id, { status: status as any });
    loadTasks();
  };

  const quickSetPriority = async (id: string, priority: string) => {
    await updateTask(id, { priority: priority as any });
    loadTasks();
  };

  const renderTask = ({ item }: { item: Task }) => (
    <View style={styles.taskCard}>
      <View style={styles.taskHeader}>
        <TouchableOpacity style={{ flex: 1 }} onPress={() => openEdit(item)}>
          <Text style={styles.taskTitle}>{item.title}</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={() => handleDelete(item.id)}>
          <Text style={styles.deleteText}>Delete</Text>
        </TouchableOpacity>
      </View>
      <View style={styles.statusRow}>
        {STATUS_OPTIONS.map((status) => (
          <TouchableOpacity
            key={status}
            onPress={() => quickSetStatus(item.id, status)}
            style={[
              styles.statusChip,
              item.status === status && { backgroundColor: STATUS_COLORS[status] + '30' },
            ]}
          >
            <Text
              style={[
                styles.statusChipText,
                item.status === status && { color: STATUS_COLORS[status], fontWeight: '700' },
              ]}
            >
              {status.replace('_', ' ')}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
      <View style={styles.taskMeta}>
        <TouchableOpacity
          style={[styles.badge, { backgroundColor: PRIORITY_COLORS[item.priority] + '30' }]}
          onPress={() => openEdit(item)}
        >
          <Text style={[styles.badgeText, { color: PRIORITY_COLORS[item.priority] }]}>
            {item.priority}
          </Text>
        </TouchableOpacity>
        <Text style={styles.tapHint}>Tap to edit</Text>
      </View>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Tasks</Text>
        <TouchableOpacity style={styles.addButton} onPress={() => setModalVisible(true)}>
          <Text style={styles.addButtonText}>+ New</Text>
        </TouchableOpacity>
      </View>

      <FlatList
        data={tasks}
        keyExtractor={(item) => item.id}
        renderItem={renderTask}
        contentContainerStyle={styles.list}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={loadTasks} tintColor={colors.text} />}
      />

      <Modal visible={modalVisible} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>New Task</Text>
            <TextInput
              style={styles.input}
              placeholder="Task title"
              placeholderTextColor={colors.textSecondary}
              value={newTaskTitle}
              onChangeText={setNewTaskTitle}
            />
            <View style={styles.modalButtons}>
              <TouchableOpacity style={styles.modalButtonSecondary} onPress={() => setModalVisible(false)}>
                <Text style={styles.modalButtonText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.modalButtonPrimary} onPress={handleCreate}>
                <Text style={styles.modalButtonText}>Create</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      <Modal visible={!!editingTask} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Edit Task</Text>
            <Text style={styles.modalLabel}>Status</Text>
            <View style={styles.chipGroup}>
              {STATUS_OPTIONS.map((status) => (
                <TouchableOpacity
                  key={status}
                  onPress={() => setEditStatus(status)}
                  style={[
                    styles.pickerChip,
                    editStatus === status && { backgroundColor: STATUS_COLORS[status] + '40', borderColor: STATUS_COLORS[status] },
                  ]}
                >
                  <Text
                    style={[
                      styles.pickerChipText,
                      editStatus === status && { color: STATUS_COLORS[status], fontWeight: '700' },
                    ]}
                  >
                    {status.replace('_', ' ')}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
            <Text style={[styles.modalLabel, { marginTop: spacing.md }]}>Priority</Text>
            <View style={styles.chipGroup}>
              {PRIORITY_OPTIONS.map((priority) => (
                <TouchableOpacity
                  key={priority}
                  onPress={() => setEditPriority(priority)}
                  style={[
                    styles.pickerChip,
                    editPriority === priority && { backgroundColor: PRIORITY_COLORS[priority] + '40', borderColor: PRIORITY_COLORS[priority] },
                  ]}
                >
                  <Text
                    style={[
                      styles.pickerChipText,
                      editPriority === priority && { color: PRIORITY_COLORS[priority], fontWeight: '700' },
                    ]}
                  >
                    {priority}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
            <View style={[styles.modalButtons, { marginTop: spacing.lg }]}>
              <TouchableOpacity style={styles.modalButtonSecondary} onPress={() => setEditingTask(null)}>
                <Text style={styles.modalButtonText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.modalButtonPrimary} onPress={handleUpdate}>
                <Text style={styles.modalButtonText}>Save</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: spacing.lg,
  },
  title: {
    fontSize: 28,
    fontWeight: '800',
    color: colors.text,
  },
  addButton: {
    backgroundColor: colors.primary,
    borderRadius: borderRadius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    ...shadows.glow,
  },
  addButtonText: {
    color: colors.text,
    fontWeight: '700',
  },
  list: {
    padding: spacing.lg,
    paddingTop: 0,
  },
  taskCard: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
    padding: spacing.lg,
    marginBottom: spacing.md,
    ...shadows.md,
  },
  taskHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: spacing.sm,
  },
  taskTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: colors.text,
    flex: 1,
    marginRight: spacing.sm,
  },
  deleteText: {
    color: colors.error,
    fontSize: 13,
  },
  statusRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.xs,
    marginTop: spacing.sm,
    marginBottom: spacing.sm,
  },
  statusChip: {
    borderRadius: borderRadius.round,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
    borderWidth: 1,
    borderColor: colors.glassBorder,
  },
  statusChipText: {
    fontSize: 11,
    color: colors.textSecondary,
    textTransform: 'capitalize',
  },
  taskMeta: {
    flexDirection: 'row',
    gap: spacing.sm,
    alignItems: 'center',
  },
  tapHint: {
    fontSize: 11,
    color: colors.textSecondary,
  },
  badge: {
    borderRadius: borderRadius.round,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
  },
  badgeText: {
    fontSize: 12,
    fontWeight: '600',
    textTransform: 'capitalize',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'center',
    padding: spacing.lg,
  },
  modalContent: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.xl,
    padding: spacing.xl,
    ...shadows.lg,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: colors.text,
    marginBottom: spacing.md,
  },
  modalLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: colors.textSecondary,
    marginBottom: spacing.xs,
  },
  chipGroup: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  pickerChip: {
    borderRadius: borderRadius.round,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderWidth: 1,
    borderColor: colors.glassBorder,
  },
  pickerChipText: {
    fontSize: 13,
    color: colors.textSecondary,
    textTransform: 'capitalize',
  },
  input: {
    backgroundColor: colors.background,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    color: colors.text,
    fontSize: 16,
    marginBottom: spacing.lg,
  },
  modalButtons: {
    flexDirection: 'row',
    gap: spacing.md,
  },
  modalButtonSecondary: {
    flex: 1,
    backgroundColor: colors.surfaceVariant,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    alignItems: 'center',
  },
  modalButtonPrimary: {
    flex: 1,
    backgroundColor: colors.primary,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    alignItems: 'center',
  },
  modalButtonText: {
    color: colors.text,
    fontWeight: '700',
  },
});
