import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuthStore } from '../store/authStore';
import { getTasks, getEvents, getIntegrationStatus } from '../api/workspace';
import { colors, spacing, borderRadius, shadows } from '../theme';

function StatCard({ title, value, color }: { title: string; value: string | number; color: string }) {
  return (
    <View style={[styles.statCard, { borderLeftColor: color, borderLeftWidth: 4 }]}>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statTitle}>{title}</Text>
    </View>
  );
}

export function DashboardScreen() {
  const user = useAuthStore((s) => s.user);
  const [stats, setStats] = useState({ tasks: 0, events: 0, integrations: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadStats() {
      try {
        const [tasks, events, status] = await Promise.all([
          getTasks(),
          getEvents(),
          getIntegrationStatus(),
        ]);
        const connected = Object.values(status || {}).filter(
          (s: any) => s && (s.connected || s.imap_connected || s.gmail_connected)
        ).length;
        setStats({ tasks: tasks.length, events: events.length, integrations: connected });
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    }
    loadStats();
  }, []);

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.header}>
          <Text style={styles.greeting}>Hello, {user?.first_name || user?.username || 'Argus User'}</Text>
          <Text style={styles.subtitle}>Your AI command center</Text>
        </View>

        <View style={styles.statsGrid}>
          <StatCard title="Tasks" value={loading ? '...' : stats.tasks} color={colors.primary} />
          <StatCard title="Events" value={loading ? '...' : stats.events} color={colors.secondary} />
          <StatCard title="Connected" value={loading ? '...' : stats.integrations} color={colors.success} />
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Quick Actions</Text>
          <View style={styles.actionsGrid}>
            {['Chat with Argus', 'View Tasks', 'Check Calendar', 'Manage Integrations'].map((action) => (
              <TouchableOpacity key={action} style={styles.actionCard}>
                <Text style={styles.actionText}>{action}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  scroll: {
    padding: spacing.lg,
  },
  header: {
    marginBottom: spacing.xl,
  },
  greeting: {
    fontSize: 28,
    fontWeight: '800',
    color: colors.text,
  },
  subtitle: {
    fontSize: 16,
    color: colors.textSecondary,
    marginTop: spacing.xs,
  },
  statsGrid: {
    flexDirection: 'row',
    gap: spacing.md,
    marginBottom: spacing.xl,
  },
  statCard: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
    padding: spacing.lg,
    ...shadows.md,
  },
  statValue: {
    fontSize: 28,
    fontWeight: '800',
    color: colors.text,
  },
  statTitle: {
    fontSize: 13,
    color: colors.textSecondary,
    marginTop: spacing.xs,
  },
  section: {
    marginTop: spacing.md,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: colors.text,
    marginBottom: spacing.md,
  },
  actionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
  },
  actionCard: {
    width: '47%',
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
    padding: spacing.lg,
    alignItems: 'center',
    ...shadows.md,
  },
  actionText: {
    color: colors.text,
    fontSize: 14,
    fontWeight: '600',
    textAlign: 'center',
  },
});
