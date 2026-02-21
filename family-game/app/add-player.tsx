import { useState, useEffect } from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView, TextInput, Alert } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Player } from '../lib/types';
import { addPlayer, getFamily, updatePlayer, removePlayer, PLAYER_EMOJIS } from '../lib/storage';
import { colors, spacing, fontSize, borderRadius, shadows } from '../lib/theme';

const INTEREST_OPTIONS = [
  'Sports', 'Music', 'Cooking', 'Travel', 'Gaming',
  'Reading', 'Movies', 'Outdoors', 'Art', 'Science',
  'Animals', 'Dance', 'Photography', 'Gardening', 'Tech',
  'Fashion', 'History', 'Crafts',
];

export default function AddPlayerScreen() {
  const router = useRouter();
  const { edit } = useLocalSearchParams<{ edit?: string }>();
  const isEditing = !!edit;

  const [name, setName] = useState('');
  const [emoji, setEmoji] = useState(PLAYER_EMOJIS[0]);
  const [age, setAge] = useState('');
  const [interests, setInterests] = useState<string[]>([]);
  const [existingPlayer, setExistingPlayer] = useState<Player | null>(null);

  useEffect(() => {
    if (isEditing) {
      loadPlayer();
    }
  }, [edit]);

  const loadPlayer = async () => {
    const family = await getFamily();
    if (!family) return;
    const player = family.players.find(p => p.id === edit);
    if (player) {
      setExistingPlayer(player);
      setName(player.name);
      setEmoji(player.emoji);
      setAge(player.age ? String(player.age) : '');
      setInterests(player.interests);
    }
  };

  const toggleInterest = (interest: string) => {
    setInterests(prev =>
      prev.includes(interest)
        ? prev.filter(i => i !== interest)
        : [...prev, interest]
    );
  };

  const handleSave = async () => {
    if (!name.trim()) {
      Alert.alert('Name required', 'Please enter a name for this player.');
      return;
    }

    const playerData = {
      name: name.trim(),
      emoji,
      age: age ? parseInt(age, 10) : undefined,
      interests,
      favorites: existingPlayer?.favorites || {},
    };

    if (isEditing && existingPlayer) {
      await updatePlayer(existingPlayer.id, playerData);
    } else {
      await addPlayer(playerData);
    }

    router.back();
  };

  const handleDelete = async () => {
    if (!existingPlayer) return;
    Alert.alert(
      'Remove Player',
      `Remove ${existingPlayer.name} from the family?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Remove',
          style: 'destructive',
          onPress: async () => {
            await removePlayer(existingPlayer.id);
            router.back();
          },
        },
      ]
    );
  };

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Emoji Picker */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Choose an avatar</Text>
          <View style={styles.emojiGrid}>
            {PLAYER_EMOJIS.map(e => (
              <Pressable
                key={e}
                onPress={() => setEmoji(e)}
                style={[
                  styles.emojiOption,
                  emoji === e && styles.emojiSelected,
                ]}
              >
                <Text style={styles.emojiText}>{e}</Text>
              </Pressable>
            ))}
          </View>
        </View>

        {/* Name */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Name</Text>
          <TextInput
            style={styles.input}
            placeholder="Enter name"
            placeholderTextColor={colors.textMuted}
            value={name}
            onChangeText={setName}
            autoFocus={!isEditing}
          />
        </View>

        {/* Age */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Age (optional)</Text>
          <TextInput
            style={[styles.input, styles.ageInput]}
            placeholder="e.g. 12"
            placeholderTextColor={colors.textMuted}
            value={age}
            onChangeText={setAge}
            keyboardType="number-pad"
            maxLength={3}
          />
          <Text style={styles.helpText}>
            Helps tailor questions to be age-appropriate
          </Text>
        </View>

        {/* Interests */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Interests</Text>
          <Text style={styles.helpText}>
            Pick a few - this helps personalize the game!
          </Text>
          <View style={styles.interestGrid}>
            {INTEREST_OPTIONS.map(interest => (
              <Pressable
                key={interest}
                onPress={() => toggleInterest(interest.toLowerCase())}
                style={[
                  styles.interestChip,
                  interests.includes(interest.toLowerCase()) && styles.interestSelected,
                ]}
              >
                <Text
                  style={[
                    styles.interestText,
                    interests.includes(interest.toLowerCase()) && styles.interestTextSelected,
                  ]}
                >
                  {interest}
                </Text>
              </Pressable>
            ))}
          </View>
        </View>

        {/* Preview */}
        <View style={styles.preview}>
          <Text style={styles.previewEmoji}>{emoji}</Text>
          <Text style={styles.previewName}>{name || 'Player Name'}</Text>
          {age && <Text style={styles.previewAge}>Age {age}</Text>}
          {interests.length > 0 && (
            <Text style={styles.previewInterests}>
              Loves: {interests.join(', ')}
            </Text>
          )}
        </View>
      </ScrollView>

      {/* Bottom buttons */}
      <View style={styles.bottomBar}>
        {isEditing && (
          <Pressable style={styles.deleteButton} onPress={handleDelete}>
            <Text style={styles.deleteButtonText}>Remove</Text>
          </Pressable>
        )}
        <Pressable
          style={[styles.saveButton, !name.trim() && styles.buttonDisabled]}
          onPress={handleSave}
          disabled={!name.trim()}
        >
          <Text style={styles.saveButtonText}>
            {isEditing ? 'Save Changes' : 'Add Player'}
          </Text>
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
    marginBottom: spacing.sm,
  },
  helpText: {
    color: colors.textMuted,
    fontSize: fontSize.sm,
    marginTop: spacing.xs,
    marginBottom: spacing.sm,
  },

  // Emoji grid
  emojiGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  emojiOption: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: colors.surface,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: 'transparent',
  },
  emojiSelected: {
    borderColor: colors.primary,
    backgroundColor: colors.primary + '20',
  },
  emojiText: {
    fontSize: 24,
  },

  // Input
  input: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    color: colors.text,
    fontSize: fontSize.lg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  ageInput: {
    width: 100,
  },

  // Interests
  interestGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  interestChip: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    backgroundColor: colors.surface,
    borderRadius: borderRadius.full,
    borderWidth: 1,
    borderColor: colors.border,
  },
  interestSelected: {
    backgroundColor: colors.primary + '20',
    borderColor: colors.primary,
  },
  interestText: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
    fontWeight: '600',
  },
  interestTextSelected: {
    color: colors.primary,
  },

  // Preview
  preview: {
    alignItems: 'center',
    padding: spacing.xl,
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
    gap: spacing.xs,
    ...shadows.card,
  },
  previewEmoji: {
    fontSize: 48,
    marginBottom: spacing.sm,
  },
  previewName: {
    color: colors.text,
    fontSize: fontSize.xl,
    fontWeight: '700',
  },
  previewAge: {
    color: colors.textSecondary,
    fontSize: fontSize.sm,
  },
  previewInterests: {
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
    flexDirection: 'row',
    padding: spacing.lg,
    paddingBottom: spacing.xl,
    backgroundColor: colors.background,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    gap: spacing.sm,
  },
  saveButton: {
    flex: 1,
    backgroundColor: colors.primary,
    paddingVertical: spacing.md,
    borderRadius: borderRadius.full,
    alignItems: 'center',
    ...shadows.button,
  },
  saveButtonText: {
    color: colors.text,
    fontSize: fontSize.md,
    fontWeight: '700',
  },
  deleteButton: {
    backgroundColor: colors.accent + '20',
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    borderRadius: borderRadius.full,
    alignItems: 'center',
  },
  deleteButtonText: {
    color: colors.accent,
    fontSize: fontSize.md,
    fontWeight: '700',
  },
  buttonDisabled: {
    opacity: 0.4,
  },
});
