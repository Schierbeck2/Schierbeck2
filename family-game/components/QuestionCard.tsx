import { View, Text, StyleSheet } from 'react-native';
import { GameQuestion } from '../lib/types';
import { colors, borderRadius, fontSize, spacing, shadows } from '../lib/theme';

interface Props {
  question: GameQuestion;
  roundNumber: number;
  totalRounds: number;
}

const modeColors: Record<string, string> = {
  trivia: colors.trivia,
  conversation: colors.conversation,
  creative: colors.creative,
};

const modeEmojis: Record<string, string> = {
  trivia: '🧠',
  conversation: '💬',
  creative: '🎨',
};

export default function QuestionCard({ question, roundNumber, totalRounds }: Props) {
  const modeColor = modeColors[question.mode] || colors.primary;

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={[styles.category, { color: modeColor }]}>
          {modeEmojis[question.mode]} {question.category}
        </Text>
        <Text style={styles.round}>
          {roundNumber}/{totalRounds}
        </Text>
      </View>

      <Text style={styles.question}>{question.text}</Text>

      {question.forPlayer && (
        <View style={styles.playerTag}>
          <Text style={styles.playerTagText}>
            {question.forPlayer.emoji} {question.forPlayer.name}'s turn
          </Text>
        </View>
      )}

      {question.aboutPlayer && question.mode === 'trivia' && (
        <View style={[styles.aboutTag, { backgroundColor: modeColor + '20' }]}>
          <Text style={[styles.aboutTagText, { color: modeColor }]}>
            About {question.aboutPlayer.emoji} {question.aboutPlayer.name}
          </Text>
        </View>
      )}

      {question.options && question.options.length > 0 && (
        <View style={styles.instructions}>
          {question.options.map((opt, i) => (
            <Text key={i} style={styles.instructionText}>
              {opt}
            </Text>
          ))}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.xl,
    padding: spacing.xl,
    gap: spacing.md,
    ...shadows.card,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  category: {
    fontSize: fontSize.sm,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  round: {
    color: colors.textMuted,
    fontSize: fontSize.sm,
    fontWeight: '600',
  },
  question: {
    color: colors.text,
    fontSize: fontSize.xl,
    fontWeight: '700',
    lineHeight: 34,
    marginVertical: spacing.sm,
  },
  playerTag: {
    backgroundColor: colors.primary + '20',
    alignSelf: 'flex-start',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: borderRadius.full,
  },
  playerTagText: {
    color: colors.primaryLight,
    fontSize: fontSize.sm,
    fontWeight: '600',
  },
  aboutTag: {
    alignSelf: 'flex-start',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: borderRadius.full,
  },
  aboutTagText: {
    fontSize: fontSize.sm,
    fontWeight: '600',
  },
  instructions: {
    marginTop: spacing.sm,
    padding: spacing.md,
    backgroundColor: colors.surfaceLight,
    borderRadius: borderRadius.md,
    gap: spacing.xs,
  },
  instructionText: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
    lineHeight: 20,
  },
});
