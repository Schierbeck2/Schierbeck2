import AsyncStorage from '@react-native-async-storage/async-storage';
import { Family, Player, GameResult } from './types';

const KEYS = {
  FAMILY: 'family_data',
  GAME_HISTORY: 'game_history',
  LEARNED_FACTS: 'learned_facts',
};

// Generate a simple unique ID
export function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).substring(2, 8);
}

// Player emoji options
export const PLAYER_EMOJIS = [
  '😊', '🦊', '🌟', '🎨', '🎵', '🌈', '🦋', '🌻',
  '🐱', '🐶', '🦁', '🐻', '🦄', '🐬', '🦉', '🐝',
  '🚀', '⚡', '🔥', '💎', '🎯', '🏆', '🎪', '🎭',
];

// Family operations
export async function getFamily(): Promise<Family | null> {
  const data = await AsyncStorage.getItem(KEYS.FAMILY);
  return data ? JSON.parse(data) : null;
}

export async function saveFamily(family: Family): Promise<void> {
  await AsyncStorage.setItem(KEYS.FAMILY, JSON.stringify(family));
}

export async function createFamily(name: string): Promise<Family> {
  const family: Family = {
    id: generateId(),
    name,
    players: [],
    createdAt: Date.now(),
  };
  await saveFamily(family);
  return family;
}

export async function addPlayer(player: Omit<Player, 'id' | 'gamesPlayed' | 'createdAt' | 'funFacts'>): Promise<Player> {
  const family = await getFamily();
  if (!family) throw new Error('No family created yet');

  const newPlayer: Player = {
    ...player,
    id: generateId(),
    funFacts: [],
    gamesPlayed: 0,
    createdAt: Date.now(),
  };

  family.players.push(newPlayer);
  await saveFamily(family);
  return newPlayer;
}

export async function updatePlayer(playerId: string, updates: Partial<Player>): Promise<void> {
  const family = await getFamily();
  if (!family) return;

  const index = family.players.findIndex(p => p.id === playerId);
  if (index >= 0) {
    family.players[index] = { ...family.players[index], ...updates };
    await saveFamily(family);
  }
}

export async function removePlayer(playerId: string): Promise<void> {
  const family = await getFamily();
  if (!family) return;

  family.players = family.players.filter(p => p.id !== playerId);
  await saveFamily(family);
}

// Game history
export async function saveGameResult(result: GameResult): Promise<void> {
  const history = await getGameHistory();
  history.push(result);
  // Keep last 50 games
  if (history.length > 50) history.shift();
  await AsyncStorage.setItem(KEYS.GAME_HISTORY, JSON.stringify(history));
}

export async function getGameHistory(): Promise<GameResult[]> {
  const data = await AsyncStorage.getItem(KEYS.GAME_HISTORY);
  return data ? JSON.parse(data) : [];
}

// Learning about players - store facts discovered during games
export async function learnFact(playerId: string, fact: string): Promise<void> {
  const family = await getFamily();
  if (!family) return;

  const player = family.players.find(p => p.id === playerId);
  if (player && !player.funFacts.includes(fact)) {
    player.funFacts.push(fact);
    if (player.funFacts.length > 20) player.funFacts.shift();
    await saveFamily(family);
  }
}

export async function incrementGamesPlayed(playerIds: string[]): Promise<void> {
  const family = await getFamily();
  if (!family) return;

  for (const id of playerIds) {
    const player = family.players.find(p => p.id === id);
    if (player) player.gamesPlayed++;
  }
  await saveFamily(family);
}

// Reset all data
export async function resetAllData(): Promise<void> {
  await AsyncStorage.multiRemove([KEYS.FAMILY, KEYS.GAME_HISTORY, KEYS.LEARNED_FACTS]);
}
