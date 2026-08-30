import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, StyleSheet, FlatList, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { format, parseISO } from 'date-fns';
import { getEvents } from '../api/workspace';
import { CalendarEvent } from '../types';
import { colors, spacing, borderRadius, shadows } from '../theme';

export function CalendarScreen() {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);

  const loadEvents = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getEvents();
      setEvents(data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadEvents();
  }, [loadEvents]);

  const renderEvent = ({ item }: { item: CalendarEvent }) => {
    const start = parseISO(item.start_time);
    return (
      <View style={styles.eventCard}>
        <View style={styles.timeColumn}>
          <Text style={styles.timeText}>{format(start, 'HH:mm')}</Text>
          <Text style={styles.dateText}>{format(start, 'MMM d')}</Text>
        </View>
        <View style={styles.eventContent}>
          <Text style={styles.eventTitle}>{item.title}</Text>
          {item.location ? <Text style={styles.eventLocation}>{item.location}</Text> : null}
          {item.description ? (
            <Text style={styles.eventDescription} numberOfLines={2}>
              {item.description}
            </Text>
          ) : null}
        </View>
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Calendar</Text>
      </View>

      <FlatList
        data={events}
        keyExtractor={(item) => item.id}
        renderItem={renderEvent}
        contentContainerStyle={styles.list}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={loadEvents} tintColor={colors.text} />}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyText}>No upcoming events</Text>
          </View>
        }
      />
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
  list: {
    padding: spacing.lg,
    paddingTop: 0,
  },
  eventCard: {
    flexDirection: 'row',
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
    padding: spacing.lg,
    marginBottom: spacing.md,
    ...shadows.md,
  },
  timeColumn: {
    width: 60,
    borderRightWidth: 1,
    borderRightColor: colors.glassBorder,
    marginRight: spacing.md,
  },
  timeText: {
    fontSize: 18,
    fontWeight: '800',
    color: colors.primary,
  },
  dateText: {
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: spacing.xs,
  },
  eventContent: {
    flex: 1,
  },
  eventTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: colors.text,
  },
  eventLocation: {
    fontSize: 13,
    color: colors.secondary,
    marginTop: spacing.xs,
  },
  eventDescription: {
    fontSize: 13,
    color: colors.textSecondary,
    marginTop: spacing.sm,
  },
  empty: {
    alignItems: 'center',
    padding: spacing.xl,
  },
  emptyText: {
    color: colors.textSecondary,
    fontSize: 16,
  },
});
