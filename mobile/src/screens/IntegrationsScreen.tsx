import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, StyleSheet, ScrollView, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { getIntegrationStatus } from '../api/workspace';
import { colors, spacing, borderRadius, shadows } from '../theme';

interface IntegrationItemProps {
  name: string;
  icon: string;
  connected: boolean;
}

function IntegrationItem({ name, icon, connected }: IntegrationItemProps) {
  return (
    <View style={styles.integrationCard}>
      <Text style={styles.integrationIcon}>{icon}</Text>
      <View style={styles.integrationInfo}>
        <Text style={styles.integrationName}>{name}</Text>
        <View style={[styles.statusBadge, connected ? styles.connected : styles.disconnected]}>
          <Text style={[styles.statusText, connected ? styles.connectedText : styles.disconnectedText]}>
            {connected ? 'Connected' : 'Not connected'}
          </Text>
        </View>
      </View>
    </View>
  );
}

export function IntegrationsScreen() {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const loadStatus = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getIntegrationStatus();
      setStatus(data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  const integrations = status
    ? [
        { name: 'Gmail', icon: '✉️', connected: status.gmail?.connected },
        { name: 'Google Calendar', icon: '📅', connected: status.calendar?.connected },
        { name: 'Plaid Banking', icon: '🏦', connected: status.plaid?.connected },
        { name: 'Canva', icon: '🎨', connected: status.canva?.connected },
        { name: 'Jira', icon: '⬣', connected: status.jira?.connected },
      ]
    : [];

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Integrations</Text>
      </View>

      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={loadStatus} tintColor={colors.text} />}
      >
        {integrations.map((item) => (
          <IntegrationItem key={item.name} {...item} />
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    padding: spacing.lg,
  },
  title: {
    fontSize: 28,
    fontWeight: '800',
    color: colors.text,
  },
  scroll: {
    padding: spacing.lg,
    paddingTop: 0,
  },
  integrationCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
    padding: spacing.lg,
    marginBottom: spacing.md,
    ...shadows.md,
  },
  integrationIcon: {
    fontSize: 28,
    marginRight: spacing.md,
  },
  integrationInfo: {
    flex: 1,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  integrationName: {
    fontSize: 16,
    fontWeight: '700',
    color: colors.text,
  },
  statusBadge: {
    borderRadius: borderRadius.round,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
  },
  connected: {
    backgroundColor: colors.success + '30',
  },
  disconnected: {
    backgroundColor: colors.surfaceVariant,
  },
  statusText: {
    fontSize: 12,
    fontWeight: '600',
  },
  connectedText: {
    color: colors.success,
  },
  disconnectedText: {
    color: colors.textSecondary,
  },
});
