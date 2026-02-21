export interface Player {
  id: string;
  name: string;
  emoji: string;
  age?: number;
  interests: string[];
  favorites: Record<string, string>; // e.g. { color: "blue", food: "pizza" }
  funFacts: string[]; // learned during gameplay
  gamesPlayed: number;
  createdAt: number;
}

export interface Family {
  id: string;
  name: string;
  players: Player[];
  createdAt: number;
}

export type GameMode = 'trivia' | 'conversation' | 'creative';

export interface GameModeInfo {
  id: GameMode;
  title: string;
  description: string;
  emoji: string;
  minPlayers: number;
  color: string;
}

export interface GameQuestion {
  id: string;
  mode: GameMode;
  text: string;
  aboutPlayer?: Player; // for trivia - who the question is about
  forPlayer?: Player;   // who should answer
  options?: string[];   // multiple choice options
  category: string;
  difficulty: 'easy' | 'medium' | 'hard';
}

export interface GameRound {
  questionIndex: number;
  question: GameQuestion;
  answers: Record<string, string>; // playerId -> answer
  scores: Record<string, number>;  // playerId -> points earned this round
}

export interface GameState {
  id: string;
  mode: GameMode;
  players: Player[];
  rounds: GameRound[];
  currentRound: number;
  totalRounds: number;
  scores: Record<string, number>; // cumulative scores
  currentPlayerIndex: number;
  phase: 'question' | 'answer' | 'reveal' | 'finished';
  startedAt: number;
}

export interface GameResult {
  id: string;
  mode: GameMode;
  players: Player[];
  scores: Record<string, number>;
  rounds: GameRound[];
  funMoments: string[];
  playedAt: number;
}
