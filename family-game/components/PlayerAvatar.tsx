import { View, Text, StyleSheet, Pressable } from 'react-native';
import { Player } from '../lib/types';
import { colors, borderRadius, fontSize, spacing } from '../lib/theme';

interface Props {
  player: Player;
  size?: 'small' | 'medium' | 'large';
  selected?: boolean;
  onPress?: () => void;
  showName?: boolean;
}

const sizes = {
  small: { container: 48, emoji: 22, name: fontSize.xs },
  medium: { container: 64, emoji: 28, name: fontSize.sm },
  large: { container: 80, emoji: 36, name: fontSize.md },
};

export default function PlayerAvatar({ player, size = 'medium', selected, onPress, showName = true }: Props) {
  const s = sizes[size];

  const content = (
    <View style={styles.wrapper}>
      <View
        style={[
          styles.container,
          {
            width: s.container,
            height: s.container,
            borderRadius: s.container / 2,
          },
          selected && styles.selected,
        ]}
      >
        <Text style={{ fontSize: s.emoji }}>{player.emoji}</Text>
      </View>
      {showName && (
        <Text style={[styles.name, { fontSize: s.name }]} numberOfLines={1}>
          {player.name}
        </Text>
      )}
    </View>
  );

  if (onPress) {
    return <Pressable onPress={onPress}>{content}</Pressable>;
  }

  return content;
}

const styles = StyleSheet.create({
  wrapper: {
    alignItems: 'center',
    gap: spacing.xs,
  },
  container: {
    backgroundColor: colors.surface,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: colors.border,
  },
  selected: {
    borderColor: colors.primary,
    backgroundColor: colors.surfaceLight,
  },
  name: {
    color: colors.text,
    fontWeight: '600',
    maxWidth: 80,
    textAlign: 'center',
  },
});
