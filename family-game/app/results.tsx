import { useState, useEffect, useRef } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, Animated } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { GameResult } from '../lib/types';
import { getGameHistory } from '../lib/storage';
import { colors, spacing, fontSize, borderRadius, shadows } from '../lib/theme';

const RANK_EMOJIS = ['👑', '🥈', '🥉', '🎖️', '🎖️', '🎖️'];

export default function ResultsScreen() {
  const router = useRouter();
  const { gameId } = useLocalSearchParams<{ gameId: string }>();
  const [result, setResult] = useState<GameResult | null>(null);
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(0.8)).current;

  useEffect(() => {
    loadResult();
  }, []);

  useEffect(() => {
    if (result) {
      Animated.parallel([
        Animated.timing(fadeAnim, {
          toValue: 1,
          duration: 600,
          useNativeDriver: true,
        }),
        Animated.spring(scaleAnim, {
          toValue: 1,
          friction: 6,
          tension: 40,
          useNativeDriver: true,
        }),
      ]).start();
    }
  }, [result]);

  const loadResult = async () => {
    const history = await getGameHistory();
    const game = history.find(g => g.id === gameId);
    if (game) setResult(game);
  };

  if (!result) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.center}>
          <Text style={styles.loadingText}>Tallying results...</Text>
        </View>
      </SafeAreaView>
    );
  }

  // Sort players by score
  const sortedPlayers = [...result.players].sort(
    (a, b) => (result.scores[b.id] || 0) - (result.scores[a.id] || 0)
  );

  const winner = sortedPlayers[0];
  const winnerScore = result.scores[winner.id] || 0;

  const modeNames: Record<string, string> = {
    trivia: 'How Well Do You Know Me?',
    conversation: 'Conversation Starters',
    creative: 'Creative Challenges',
  };

  const modeEmojis: Record<string, string> = {
    trivia: '🧠',
    conversation: '💬',
    creative: '🎨',
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Winner celebration */}
        <Animated.View
          style={[
            styles.winnerSection,
            {
              opacity: fadeAnim,
              transform: [{ scale: scaleAnim }],
            },
          ]}
        >
          <Text style={styles.confetti}>🎉</Text>
          <Text style={styles.winnerEmoji}>{winner.emoji}</Text>
          <Text style={styles.winnerName}>{winner.name} Wins!</Text>
          <Text style={styles.winnerScore}>{winnerScore} points</Text>
        </Animated.View>

        {/* Game info */}
        <View style={styles.gameInfo}>
          <Text style={styles.gameMode}>
            {modeEmojis[result.mode]} {modeNames[result.mode]}
          </Text>
          <Text style={styles.gameStats}>
            {result.rounds.length} rounds • {result.players.length} players
          </Text>
        </View>

        {/* Full leaderboard */}
        <View style={styles.leaderboard}>
          <Text style={styles.sectionTitle}>Final Standings</Text>
          {sortedPlayers.map((player, index) => {
            const score = result.scores[player.id] || 0;
            const maxScore = winnerScore || 1;
            const barWidth = (score / maxScore) * 100;

            return (
              <View key={player.id} style={styles.leaderRow}>
                <Text style={styles.rankEmoji}>
                  {RANK_EMOJIS[index] || '🎖️'}
                </Text>
                <View style={styles.leaderInfo}>
                  <View style={styles.leaderTop}>
                    <Text style={styles.leaderEmoji}>{player.emoji}</Text>
                    <Text style={styles.leaderName}>{player.name}</Text>
                    <Text style={styles.leaderScore}>{score} pts</Text>
                  </View>
                  <View style={styles.scoreBar}>
                    <View
                      style={[
                        styles.scoreBarFill,
                        {
                          width: `${Math.max(barWidth, 5)}%`,
                          backgroundColor: index === 0 ? colors.warning : colors.primary,
                        },
                      ]}
                    />
                  </View>
                </View>
              </View>
            );
          })}
        </View>

        {/* Fun moments */}
        {result.funMoments.length > 0 && (
          <View style={styles.momentsSection}>
            <Text style={styles.sectionTitle}>Game Highlights</Text>
            {result.funMoments.map((moment, i) => (
              <View key={i} style={styles.momentCard}>
                <Text style={styles.momentText}>{moment}</Text>
              </View>
            ))}
          </View>
        )}

        {/* Action buttons */}
        <View style={styles.actions}>
          <Pressable
            style={styles.playAgainButton}
            onPress={() => router.replace('/lobby')}
          >
            <Text style={styles.playAgainEmoji}>🔄</Text>
            <Text style={styles.playAgainText}>Play Again</Text>
          </Pressable>

          <Pressable
            style={styles.homeButton}
            onPress={() => router.replace('/')}
          >
            <Text style={styles.homeButtonText}>Back Home</Text>
          </Pressable>
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
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    color: colors.textSecondary,
    fontSize: fontSize.lg,
  },
  scrollContent: {
    padding: spacing.lg,
    paddingBottom: spacing.xxl,
  },

  // Winner
  winnerSection: {
    alignItems: 'center',
    paddingVertical: spacing.xl,
    gap: spacing.sm,
  },
  confetti: {
    fontSize: 48,
    marginBottom: spacing.sm,
  },
  winnerEmoji: {
    fontSize: 72,
  },
  winnerName: {
    color: colors.text,
    fontSize: fontSize.hero,
    fontWeight: '800',
    textAlign: 'center',
  },
  winnerScore: {
    color: colors.warning,
    fontSize: fontSize.xl,
    fontWeight: '700',
  },

  // Game info
  gameInfo: {
    alignItems: 'center',
    marginBottom: spacing.xl,
    gap: spacing.xs,
  },
  gameMode: {
    color: colors.textSecondary,
    fontSize: fontSize.md,
    fontWeight: '600',
  },
  gameStats: {
    color: colors.textMuted,
    fontSize: fontSize.sm,
  },

  // Leaderboard
  leaderboard: {
    marginBottom: spacing.xl,
    gap: spacing.md,
  },
  sectionTitle: {
    color: colors.text,
    fontSize: fontSize.lg,
    fontWeight: '700',
    marginBottom: spacing.sm,
  },
  leaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing.md,
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
    gap: spacing.md,
  },
  rankEmoji: {
    fontSize: 24,
    width: 36,
    textAlign: 'center',
  },
  leaderInfo: {
    flex: 1,
    gap: spacing.sm,
  },
  leaderTop: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  leaderEmoji: {
    fontSize: 20,
  },
  leaderName: {
    flex: 1,
    color: colors.text,
    fontSize: fontSize.md,
    fontWeight: '600',
  },
  leaderScore: {
    color: colors.primary,
    fontSize: fontSize.md,
    fontWeight: '700',
  },
  scoreBar: {
    height: 6,
    backgroundColor: colors.surfaceLight,
    borderRadius: 3,
    overflow: 'hidden',
  },
  scoreBarFill: {
    height: '100%',
    borderRadius: 3,
  },

  // Fun moments
  momentsSection: {
    marginBottom: spacing.xl,
    gap: spacing.sm,
  },
  momentCard: {
    padding: spacing.md,
    backgroundColor: colors.surface,
    borderRadius: borderRadius.md,
    borderLeftWidth: 3,
    borderLeftColor: colors.warning,
  },
  momentText: {
    color: colors.textSecondary,
    fontSize: fontSize.md,
    lineHeight: 22,
  },

  // Actions
  actions: {
    gap: spacing.md,
  },
  playAgainButton: {
    backgroundColor: colors.success,
    paddingVertical: spacing.lg,
    borderRadius: borderRadius.xl,
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'center',
    gap: spacing.sm,
    ...shadows.button,
  },
  playAgainEmoji: {
    fontSize: 20,
  },
  playAgainText: {
    color: colors.text,
    fontSize: fontSize.lg,
    fontWeight: '700',
  },
  homeButton: {
    paddingVertical: spacing.md,
    borderRadius: borderRadius.xl,
    alignItems: 'center',
    backgroundColor: colors.surface,
  },
  homeButtonText: {
    color: colors.textSecondary,
    fontSize: fontSize.md,
    fontWeight: '600',
  },
});
