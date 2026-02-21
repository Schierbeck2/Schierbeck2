import { useEffect, useState, useCallback } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, TextInput, Alert } from 'react-native';
import { useRouter } from 'expo-router';
import { useFocusEffect } from '@react-navigation/native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Family } from '../lib/types';
import { getFamily, createFamily, getGameHistory } from '../lib/storage';
import { colors, spacing, fontSize, borderRadius, shadows } from '../lib/theme';
import PlayerAvatar from '../components/PlayerAvatar';

export default function HomeScreen() {
  const router = useRouter();
  const [family, setFamily] = useState<Family | null>(null);
  const [loading, setLoading] = useState(true);
  const [showSetup, setShowSetup] = useState(false);
  const [familyName, setFamilyName] = useState('');
  const [totalGames, setTotalGames] = useState(0);

  const loadData = useCallback(async () => {
    const fam = await getFamily();
    const history = await getGameHistory();
    setFamily(fam);
    setTotalGames(history.length);
    setLoading(false);
    if (!fam) setShowSetup(true);
  }, []);

  useFocusEffect(
    useCallback(() => {
      loadData();
    }, [loadData])
  );

  const handleCreateFamily = async () => {
    if (!familyName.trim()) return;
    const fam = await createFamily(familyName.trim());
    setFamily(fam);
    setShowSetup(false);
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.center}>
          <Text style={styles.loadingEmoji}>🎲</Text>
          <Text style={styles.loadingText}>Loading...</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (showSetup) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.setupContainer}>
          <Text style={styles.setupEmoji}>👨‍👩‍👧‍👦</Text>
          <Text style={styles.setupTitle}>Family Game Night</Text>
          <Text style={styles.setupSubtitle}>
            Bring your family together with games, conversation, and creativity
          </Text>

          <View style={styles.inputContainer}>
            <Text style={styles.inputLabel}>What's your family name?</Text>
            <TextInput
              style={styles.input}
              placeholder="e.g. The Johnsons"
              placeholderTextColor={colors.textMuted}
              value={familyName}
              onChangeText={setFamilyName}
              autoFocus
              returnKeyType="done"
              onSubmitEditing={handleCreateFamily}
            />
          </View>

          <Pressable
            style={[styles.primaryButton, !familyName.trim() && styles.buttonDisabled]}
            onPress={handleCreateFamily}
            disabled={!familyName.trim()}
          >
            <Text style={styles.primaryButtonText}>Get Started</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  const canPlay = family && family.players.length >= 2;

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.headerEmoji}>🎲</Text>
          <Text style={styles.title}>{family?.name || 'Family Game Night'}</Text>
          {totalGames > 0 && (
            <Text style={styles.statsText}>
              {totalGames} game{totalGames !== 1 ? 's' : ''} played together
            </Text>
          )}
        </View>

        {/* Players Section */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Family Members</Text>
            <Pressable
              style={styles.addButton}
              onPress={() => router.push('/add-player')}
            >
              <Text style={styles.addButtonText}>+ Add</Text>
            </Pressable>
          </View>

          {family && family.players.length > 0 ? (
            <View style={styles.playersGrid}>
              {family.players.map(player => (
                <PlayerAvatar
                  key={player.id}
                  player={player}
                  size="large"
                  onPress={() => router.push(`/add-player?edit=${player.id}`)}
                />
              ))}
            </View>
          ) : (
            <View style={styles.emptyState}>
              <Text style={styles.emptyEmoji}>👤</Text>
              <Text style={styles.emptyText}>
                Add family members to get started!
              </Text>
              <Text style={styles.emptySubtext}>
                You need at least 2 players to play
              </Text>
            </View>
          )}
        </View>

        {/* Play Button */}
        <Pressable
          style={[styles.playButton, !canPlay && styles.buttonDisabled]}
          onPress={() => canPlay && router.push('/lobby')}
          disabled={!canPlay}
        >
          <Text style={styles.playButtonEmoji}>🎮</Text>
          <Text style={styles.playButtonText}>
            {canPlay ? "Let's Play!" : 'Add 2+ players to start'}
          </Text>
        </Pressable>

        {/* Quick stats */}
        {family && family.players.length > 0 && (
          <View style={styles.quickStats}>
            <View style={styles.statItem}>
              <Text style={styles.statNumber}>{family.players.length}</Text>
              <Text style={styles.statLabel}>Players</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statItem}>
              <Text style={styles.statNumber}>{totalGames}</Text>
              <Text style={styles.statLabel}>Games</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statItem}>
              <Text style={styles.statNumber}>
                {family.players.reduce((sum, p) => sum + p.funFacts.length, 0)}
              </Text>
              <Text style={styles.statLabel}>Facts Learned</Text>
            </View>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingEmoji: {
    fontSize: 48,
    marginBottom: spacing.md,
  },
  loadingText: {
    color: colors.textSecondary,
    fontSize: fontSize.lg,
  },
  scrollContent: {
    padding: spacing.lg,
    paddingBottom: spacing.xxl,
  },

  // Header
  header: {
    alignItems: 'center',
    marginBottom: spacing.xl,
    marginTop: spacing.md,
  },
  headerEmoji: {
    fontSize: 56,
    marginBottom: spacing.sm,
  },
  title: {
    color: colors.text,
    fontSize: fontSize.xxl,
    fontWeight: '800',
    textAlign: 'center',
  },
  statsText: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
    marginTop: spacing.xs,
  },

  // Setup
  setupContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.xl,
    gap: spacing.md,
  },
  setupEmoji: {
    fontSize: 72,
    marginBottom: spacing.sm,
  },
  setupTitle: {
    color: colors.text,
    fontSize: fontSize.hero,
    fontWeight: '800',
    textAlign: 'center',
  },
  setupSubtitle: {
    color: colors.textSecondary,
    fontSize: fontSize.md,
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: spacing.lg,
  },
  inputContainer: {
    width: '100%',
    gap: spacing.sm,
  },
  inputLabel: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
    fontWeight: '600',
  },
  input: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    color: colors.text,
    fontSize: fontSize.lg,
    borderWidth: 1,
    borderColor: colors.border,
  },

  // Sections
  section: {
    marginBottom: spacing.xl,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  sectionTitle: {
    color: colors.text,
    fontSize: fontSize.lg,
    fontWeight: '700',
  },
  addButton: {
    backgroundColor: colors.primary + '20',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: borderRadius.full,
  },
  addButtonText: {
    color: colors.primary,
    fontSize: fontSize.sm,
    fontWeight: '700',
  },

  // Players grid
  playersGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.lg,
    justifyContent: 'center',
    padding: spacing.md,
  },

  // Empty state
  emptyState: {
    alignItems: 'center',
    padding: spacing.xl,
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
    gap: spacing.sm,
  },
  emptyEmoji: {
    fontSize: 40,
  },
  emptyText: {
    color: colors.text,
    fontSize: fontSize.md,
    fontWeight: '600',
  },
  emptySubtext: {
    color: colors.textMuted,
    fontSize: fontSize.sm,
  },

  // Buttons
  primaryButton: {
    backgroundColor: colors.primary,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.xl,
    borderRadius: borderRadius.full,
    width: '100%',
    alignItems: 'center',
    marginTop: spacing.md,
    ...shadows.button,
  },
  primaryButtonText: {
    color: colors.text,
    fontSize: fontSize.lg,
    fontWeight: '700',
  },
  buttonDisabled: {
    opacity: 0.4,
  },

  // Play button
  playButton: {
    backgroundColor: colors.primary,
    paddingVertical: spacing.lg,
    borderRadius: borderRadius.xl,
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'center',
    gap: spacing.sm,
    marginBottom: spacing.xl,
    ...shadows.button,
  },
  playButtonEmoji: {
    fontSize: 24,
  },
  playButtonText: {
    color: colors.text,
    fontSize: fontSize.xl,
    fontWeight: '800',
  },

  // Quick stats
  quickStats: {
    flexDirection: 'row',
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
    padding: spacing.lg,
    justifyContent: 'space-around',
    alignItems: 'center',
  },
  statItem: {
    alignItems: 'center',
    gap: spacing.xs,
  },
  statNumber: {
    color: colors.primary,
    fontSize: fontSize.xl,
    fontWeight: '800',
  },
  statLabel: {
    color: colors.textMuted,
    fontSize: fontSize.xs,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  statDivider: {
    width: 1,
    height: 32,
    backgroundColor: colors.border,
  },
});
