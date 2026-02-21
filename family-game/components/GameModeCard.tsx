import { View, Text, StyleSheet, Pressable } from 'react-native';
import { GameModeInfo } from '../lib/types';
import { colors, borderRadius, fontSize, spacing, shadows } from '../lib/theme';

interface Props {
  mode: GameModeInfo;
  selected?: boolean;
  onPress: () => void;
}

export default function GameModeCard({ mode, selected, onPress }: Props) {
  return (
    <Pressable onPress={onPress}>
      <View
        style={[
          styles.card,
          { borderColor: selected ? mode.color : colors.border },
          selected && { backgroundColor: mode.color + '20' },
        ]}
      >
        <Text style={styles.emoji}>{mode.emoji}</Text>
        <View style={styles.content}>
          <Text style={[styles.title, selected && { color: mode.color }]}>
            {mode.title}
          </Text>
          <Text style={styles.description}>{mode.description}</Text>
          <Text style={styles.minPlayers}>
            {mode.minPlayers}+ players
          </Text>
        </View>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    padding: spacing.md,
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
    borderWidth: 2,
    gap: spacing.md,
    alignItems: 'center',
    ...shadows.card,
  },
  emoji: {
    fontSize: 40,
  },
  content: {
    flex: 1,
    gap: spacing.xs,
  },
  title: {
    color: colors.text,
    fontSize: fontSize.lg,
    fontWeight: '700',
  },
  description: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
    lineHeight: 20,
  },
  minPlayers: {
    color: colors.textMuted,
    fontSize: fontSize.xs,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
});
