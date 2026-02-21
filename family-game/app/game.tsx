import { useState, useEffect, useRef } from 'react';
import { View, Text, StyleSheet, Pressable, Animated, ScrollView, TextInput, Alert } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Player, GameMode, GameState } from '../lib/types';
import { getFamily, learnFact } from '../lib/storage';
import { startGame, getCurrentQuestion, awardPoints, nextRound, finishGame, getLeaderboard } from '../lib/gameEngine';
import { colors, spacing, fontSize, borderRadius, shadows } from '../lib/theme';
import QuestionCard from '../components/QuestionCard';

export default function GameScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ mode: string; players: string; rounds: string }>();

  const [game, setGame] = useState<GameState | null>(null);
  const [showScoreboard, setShowScoreboard] = useState(false);
  const [answer, setAnswer] = useState('');
  const [timer, setTimer] = useState<number | null>(null);
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(50)).current;

  useEffect(() => {
    initGame();
  }, []);

  useEffect(() => {
    // Animate card entrance
    if (game && game.phase === 'question') {
      fadeAnim.setValue(0);
      slideAnim.setValue(50);
      Animated.parallel([
        Animated.timing(fadeAnim, {
          toValue: 1,
          duration: 400,
          useNativeDriver: true,
        }),
        Animated.timing(slideAnim, {
          toValue: 0,
          duration: 400,
          useNativeDriver: true,
        }),
      ]).start();
    }
  }, [game?.currentRound, game?.phase]);

  const initGame = async () => {
    const family = await getFamily();
    if (!family) return;

    const mode = params.mode as GameMode;
    const playerIds = params.players?.split(',') || [];
    const roundCount = parseInt(params.rounds || '8', 10);

    const activePlayers = family.players.filter(p => playerIds.includes(p.id));

    if (activePlayers.length < 2) {
      Alert.alert('Error', 'Need at least 2 players');
      router.back();
      return;
    }

    const newGame = startGame(mode, activePlayers, roundCount);
    setGame(newGame);
  };

  const handleAwardPoints = (playerId: string, points: number) => {
    if (!game) return;
    setGame(awardPoints(game, playerId, points));
  };

  const handleNext = async () => {
    if (!game) return;

    // Save any answer as a learned fact for trivia mode
    if (game.mode === 'trivia' && answer.trim()) {
      const question = getCurrentQuestion(game);
      if (question?.aboutPlayer) {
        await learnFact(
          question.aboutPlayer.id,
          `${question.text} → ${answer.trim()}`
        );
      }
    }

    setAnswer('');
    const nextGame = nextRound(game);

    if (nextGame.phase === 'finished') {
      const result = await finishGame(nextGame);
      router.replace(`/results?gameId=${result.id}`);
    } else {
      setGame(nextGame);
      setShowScoreboard(false);
    }
  };

  const handleQuit = () => {
    Alert.alert(
      'Quit Game?',
      'Your progress will be lost.',
      [
        { text: 'Keep Playing', style: 'cancel' },
        {
          text: 'Quit',
          style: 'destructive',
          onPress: () => router.replace('/'),
        },
      ]
    );
  };

  if (!game) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.center}>
          <Text style={styles.loadingText}>Setting up game...</Text>
        </View>
      </SafeAreaView>
    );
  }

  const question = getCurrentQuestion(game);
  const leaderboard = getLeaderboard(game);
  const modeColor = colors[game.mode as keyof typeof colors] || colors.primary;

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Top bar */}
        <View style={styles.topBar}>
          <Pressable onPress={handleQuit} style={styles.quitButton}>
            <Text style={styles.quitButtonText}>Quit</Text>
          </Pressable>

          {/* Mini scoreboard toggle */}
          <Pressable
            onPress={() => setShowScoreboard(!showScoreboard)}
            style={styles.scoreToggle}
          >
            <Text style={styles.scoreToggleText}>
              {showScoreboard ? 'Hide Scores' : 'Scores'}
            </Text>
          </Pressable>
        </View>

        {/* Progress bar */}
        <View style={styles.progressContainer}>
          <View style={styles.progressBar}>
            <View
              style={[
                styles.progressFill,
                {
                  width: `${((game.currentRound + 1) / game.totalRounds) * 100}%`,
                  backgroundColor: modeColor as string,
                },
              ]}
            />
          </View>
        </View>

        {/* Scoreboard (expandable) */}
        {showScoreboard && (
          <View style={styles.scoreboard}>
            {leaderboard.map(({ player, score, rank }) => (
              <View key={player.id} style={styles.scoreRow}>
                <Text style={styles.scoreRank}>
                  {rank === 1 ? '👑' : `#${rank}`}
                </Text>
                <Text style={styles.scoreEmoji}>{player.emoji}</Text>
                <Text style={styles.scoreName}>{player.name}</Text>
                <Text style={styles.scoreValue}>{score} pts</Text>
              </View>
            ))}
          </View>
        )}

        {/* Question Card */}
        {question && (
          <Animated.View
            style={[
              { opacity: fadeAnim, transform: [{ translateY: slideAnim }] },
            ]}
          >
            <QuestionCard
              question={question}
              roundNumber={game.currentRound + 1}
              totalRounds={game.totalRounds}
            />
          </Animated.View>
        )}

        {/* Answer area for trivia */}
        {game.mode === 'trivia' && (
          <View style={styles.answerSection}>
            <Text style={styles.answerLabel}>
              {question?.aboutPlayer?.name} reveals the answer:
            </Text>
            <TextInput
              style={styles.answerInput}
              placeholder="Type the real answer..."
              placeholderTextColor={colors.textMuted}
              value={answer}
              onChangeText={setAnswer}
              multiline
            />
          </View>
        )}

        {/* Points awarding (for trivia) */}
        {game.mode === 'trivia' && (
          <View style={styles.pointsSection}>
            <Text style={styles.pointsTitle}>Award Points</Text>
            <Text style={styles.pointsSubtitle}>
              Tap players who got it right!
            </Text>
            <View style={styles.pointsGrid}>
              {game.players
                .filter(p => p.id !== question?.aboutPlayer?.id)
                .map(player => {
                  const hasPoints = (game.rounds[game.currentRound]?.scores[player.id] || 0) > 0;
                  return (
                    <Pressable
                      key={player.id}
                      onPress={() => handleAwardPoints(player.id, hasPoints ? 0 : 1)}
                      style={[
                        styles.pointsPlayer,
                        hasPoints && styles.pointsPlayerCorrect,
                      ]}
                    >
                      <Text style={styles.pointsEmoji}>{player.emoji}</Text>
                      <Text style={styles.pointsName}>{player.name}</Text>
                      <Text style={styles.pointsCheck}>
                        {hasPoints ? '✅' : '⬜'}
                      </Text>
                    </Pressable>
                  );
                })}
            </View>
          </View>
        )}

        {/* Conversation mode - everyone discusses */}
        {game.mode === 'conversation' && (
          <View style={styles.discussSection}>
            <Text style={styles.discussEmoji}>💭</Text>
            <Text style={styles.discussText}>
              Take turns sharing your thoughts. When everyone has spoken, tap Next!
            </Text>

            {/* Vote for best answer */}
            <Text style={styles.voteTitle}>Who had the best answer?</Text>
            <View style={styles.voteGrid}>
              {game.players.map(player => {
                const hasPoints = (game.rounds[game.currentRound]?.scores[player.id] || 0) > 0;
                return (
                  <Pressable
                    key={player.id}
                    onPress={() => {
                      // Clear previous votes, award to this player
                      let g = game;
                      game.players.forEach(p => { g = awardPoints(g, p.id, 0); });
                      g = awardPoints(g, player.id, 1);
                      setGame(g);
                    }}
                    style={[
                      styles.votePlayer,
                      hasPoints && styles.votePlayerSelected,
                    ]}
                  >
                    <Text style={styles.voteEmoji}>{player.emoji}</Text>
                    <Text style={styles.voteName}>{player.name}</Text>
                  </Pressable>
                );
              })}
            </View>
          </View>
        )}

        {/* Creative mode */}
        {game.mode === 'creative' && (
          <View style={styles.discussSection}>
            <Text style={styles.discussEmoji}>✨</Text>
            <Text style={styles.discussText}>
              Complete the challenge together! Vote for the MVP when done.
            </Text>

            <Text style={styles.voteTitle}>Challenge MVP</Text>
            <View style={styles.voteGrid}>
              {game.players.map(player => {
                const hasPoints = (game.rounds[game.currentRound]?.scores[player.id] || 0) > 0;
                return (
                  <Pressable
                    key={player.id}
                    onPress={() => {
                      let g = game;
                      game.players.forEach(p => { g = awardPoints(g, p.id, 0); });
                      g = awardPoints(g, player.id, 2);
                      setGame(g);
                    }}
                    style={[
                      styles.votePlayer,
                      hasPoints && styles.votePlayerSelected,
                    ]}
                  >
                    <Text style={styles.voteEmoji}>{player.emoji}</Text>
                    <Text style={styles.voteName}>{player.name}</Text>
                  </Pressable>
                );
              })}
            </View>
          </View>
        )}
      </ScrollView>

      {/* Next button */}
      <View style={styles.bottomBar}>
        <Pressable style={styles.nextButton} onPress={handleNext}>
          <Text style={styles.nextButtonText}>
            {game.currentRound + 1 >= game.totalRounds ? 'See Results' : 'Next Round'}
          </Text>
          <Text style={styles.nextButtonArrow}>→</Text>
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
    paddingBottom: 100,
  },

  // Top bar
  topBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  quitButton: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
  },
  quitButtonText: {
    color: colors.textMuted,
    fontSize: fontSize.sm,
    fontWeight: '600',
  },
  scoreToggle: {
    backgroundColor: colors.surface,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: borderRadius.full,
  },
  scoreToggleText: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
    fontWeight: '600',
  },

  // Progress
  progressContainer: {
    marginBottom: spacing.lg,
  },
  progressBar: {
    height: 6,
    backgroundColor: colors.surface,
    borderRadius: 3,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: 3,
  },

  // Scoreboard
  scoreboard: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
    padding: spacing.md,
    marginBottom: spacing.lg,
    gap: spacing.sm,
  },
  scoreRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  scoreRank: {
    width: 32,
    textAlign: 'center',
    fontSize: fontSize.sm,
    color: colors.textMuted,
  },
  scoreEmoji: {
    fontSize: 20,
  },
  scoreName: {
    flex: 1,
    color: colors.text,
    fontSize: fontSize.md,
    fontWeight: '600',
  },
  scoreValue: {
    color: colors.primary,
    fontSize: fontSize.md,
    fontWeight: '700',
  },

  // Answer section
  answerSection: {
    marginTop: spacing.lg,
    gap: spacing.sm,
  },
  answerLabel: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
    fontWeight: '600',
  },
  answerInput: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    color: colors.text,
    fontSize: fontSize.md,
    borderWidth: 1,
    borderColor: colors.border,
    minHeight: 60,
  },

  // Points section
  pointsSection: {
    marginTop: spacing.lg,
    gap: spacing.sm,
  },
  pointsTitle: {
    color: colors.text,
    fontSize: fontSize.md,
    fontWeight: '700',
  },
  pointsSubtitle: {
    color: colors.textMuted,
    fontSize: fontSize.sm,
  },
  pointsGrid: {
    gap: spacing.sm,
  },
  pointsPlayer: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing.md,
    backgroundColor: colors.surface,
    borderRadius: borderRadius.md,
    gap: spacing.sm,
    borderWidth: 1,
    borderColor: colors.border,
  },
  pointsPlayerCorrect: {
    borderColor: colors.success,
    backgroundColor: colors.success + '15',
  },
  pointsEmoji: {
    fontSize: 24,
  },
  pointsName: {
    flex: 1,
    color: colors.text,
    fontSize: fontSize.md,
    fontWeight: '600',
  },
  pointsCheck: {
    fontSize: 20,
  },

  // Discuss section (conversation & creative)
  discussSection: {
    marginTop: spacing.xl,
    alignItems: 'center',
    gap: spacing.md,
  },
  discussEmoji: {
    fontSize: 40,
  },
  discussText: {
    color: colors.textSecondary,
    fontSize: fontSize.md,
    textAlign: 'center',
    lineHeight: 24,
  },
  voteTitle: {
    color: colors.text,
    fontSize: fontSize.md,
    fontWeight: '700',
    marginTop: spacing.md,
  },
  voteGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    justifyContent: 'center',
  },
  votePlayer: {
    alignItems: 'center',
    padding: spacing.md,
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
    borderWidth: 2,
    borderColor: colors.border,
    width: 80,
    gap: spacing.xs,
  },
  votePlayerSelected: {
    borderColor: colors.primary,
    backgroundColor: colors.primary + '20',
  },
  voteEmoji: {
    fontSize: 28,
  },
  voteName: {
    color: colors.text,
    fontSize: fontSize.xs,
    fontWeight: '600',
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
  nextButton: {
    backgroundColor: colors.primary,
    paddingVertical: spacing.md,
    borderRadius: borderRadius.xl,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
    ...shadows.button,
  },
  nextButtonText: {
    color: colors.text,
    fontSize: fontSize.lg,
    fontWeight: '700',
  },
  nextButtonArrow: {
    color: colors.text,
    fontSize: fontSize.lg,
    fontWeight: '700',
  },
});
