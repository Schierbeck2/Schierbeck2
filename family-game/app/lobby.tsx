import { useState, useEffect } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, Alert } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Family, Player, GameMode, GameModeInfo } from '../lib/types';
import { getFamily } from '../lib/storage';
import { colors, spacing, fontSize, borderRadius, shadows } from '../lib/theme';
import PlayerAvatar from '../components/PlayerAvatar';
import GameModeCard from '../components/GameModeCard';

const GAME_MODES: GameModeInfo[] = [
  {
    id: 'trivia',
    title: 'How Well Do You Know Me?',
    description: 'Answer questions about each other. Find out who really knows the family best!',
    emoji: '🧠',
    minPlayers: 2,
    color: colors.trivia,
  },
  {
    id: 'conversation',
    title: 'Conversation Starters',
    description: 'Thought-provoking prompts that spark stories and laughter across generations.',
    emoji: '💬',
    minPlayers: 2,
    color: colors.conversation,
  },
  {
    id: 'creative',
    title: 'Creative Challenges',
    description: 'Draw, act, tell stories, and create together. No talent required - just fun!',
    emoji: '🎨',
    minPlayers: 2,
    color: colors.creative,
  },
];

const ROUND_OPTIONS = [5, 8, 12, 15];

export default function LobbyScreen() {
  const router = useRouter();
  const [family, setFamily] = useState<Family | null>(null);
  const [selectedPlayers, setSelectedPlayers] = useState<Set<string>>(new Set());
  const [selectedMode, setSelectedMode] = useState<GameMode | null>(null);
  const [rounds, setRounds] = useState(8);

  useEffect(() => {
    loadFamily();
  }, []);

  const loadFamily = async () => {
    const fam = await getFamily();
    if (fam) {
      setFamily(fam);
      // Select all players by default
      setSelectedPlayers(new Set(fam.players.map(p => p.id)));
    }
  };

  const togglePlayer = (id: string) => {
    setSelectedPlayers(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleStart = () => {
    if (!selectedMode) {
      Alert.alert('Pick a game mode', 'Choose a game mode to play!');
      return;
    }
    if (selectedPlayers.size < 2) {
      Alert.alert('Need more players', 'Select at least 2 players to play.');
      return;
    }

    const playerIds = Array.from(selectedPlayers).join(',');
    router.push(`/game?mode=${selectedMode}&players=${playerIds}&rounds=${rounds}`);
  };

  const canStart = selectedMode && selectedPlayers.size >= 2;

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Who's Playing */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Who's Playing?</Text>
          <Text style={styles.sectionSubtitle}>
            Tap to select ({selectedPlayers.size} selected)
          </Text>
          <View style={styles.playerRow}>
            {family?.players.map(player => (
              <PlayerAvatar
                key={player.id}
                player={player}
                size="medium"
                selected={selectedPlayers.has(player.id)}
                onPress={() => togglePlayer(player.id)}
              />
            ))}
          </View>
        </View>

        {/* Game Mode */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Choose Your Game</Text>
          <View style={styles.modesContainer}>
            {GAME_MODES.map(mode => (
              <GameModeCard
                key={mode.id}
                mode={mode}
                selected={selectedMode === mode.id}
                onPress={() => setSelectedMode(mode.id)}
              />
            ))}
          </View>
        </View>

        {/* Rounds */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>How Many Rounds?</Text>
          <View style={styles.roundsRow}>
            {ROUND_OPTIONS.map(r => (
              <Pressable
                key={r}
                onPress={() => setRounds(r)}
                style={[
                  styles.roundOption,
                  rounds === r && styles.roundSelected,
                ]}
              >
                <Text
                  style={[
                    styles.roundText,
                    rounds === r && styles.roundTextSelected,
                  ]}
                >
                  {r}
                </Text>
              </Pressable>
            ))}
          </View>
          <Text style={styles.roundEstimate}>
            ~{Math.round(rounds * 1.5)} minutes
          </Text>
        </View>
      </ScrollView>

      {/* Start Button */}
      <View style={styles.bottomBar}>
        <Pressable
          style={[styles.startButton, !canStart && styles.buttonDisabled]}
          onPress={handleStart}
          disabled={!canStart}
        >
          <Text style={styles.startButtonEmoji}>🚀</Text>
          <Text style={styles.startButtonText}>Start Game!</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  scrollContent: {
    padding: spacing.lg,
    paddingBottom: 100,
  },

  section: {
    marginBottom: spacing.xl,
  },
  sectionTitle: {
    color: colors.text,
    fontSize: fontSize.lg,
    fontWeight: '700',
    marginBottom: spacing.xs,
  },
  sectionSubtitle: {
    color: colors.textMuted,
    fontSize: fontSize.sm,
    marginBottom: spacing.md,
  },

  // Players
  playerRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.lg,
    justifyContent: 'center',
    padding: spacing.md,
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
  },

  // Modes
  modesContainer: {
    gap: spacing.md,
  },

  // Rounds
  roundsRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginBottom: spacing.sm,
  },
  roundOption: {
    flex: 1,
    paddingVertical: spacing.md,
    backgroundColor: colors.surface,
    borderRadius: borderRadius.md,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: colors.border,
  },
  roundSelected: {
    borderColor: colors.primary,
    backgroundColor: colors.primary + '20',
  },
  roundText: {
    color: colors.textSecondary,
    fontSize: fontSize.lg,
    fontWeight: '700',
  },
  roundTextSelected: {
    color: colors.primary,
  },
  roundEstimate: {
    color: colors.textMuted,
    fontSize: fontSize.sm,
    textAlign: 'center',
  },

  // Bottom bar
  bottomBar: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    padding: spacing.lg,
    paddingBottom: spacing.xl,
    backgroundColor: colors.background,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  startButton: {
    backgroundColor: colors.success,
    paddingVertical: spacing.lg,
    borderRadius: borderRadius.xl,
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'center',
    gap: spacing.sm,
    ...shadows.button,
  },
  startButtonEmoji: {
    fontSize: 24,
  },
  startButtonText: {
    color: colors.text,
    fontSize: fontSize.xl,
    fontWeight: '800',
  },
  buttonDisabled: {
    opacity: 0.4,
  },
});
