import { Player, GameMode, GameQuestion, GameState, GameResult } from './types';
import { triviaTemplates, interestQuestions } from './content/trivia';
import { conversationCards } from './content/conversation';
import { creativeChallenges } from './content/creative';
import { generateId, saveGameResult, incrementGamesPlayed, learnFact } from './storage';

// Shuffle array in place (Fisher-Yates)
function shuffle<T>(array: T[]): T[] {
  const arr = [...array];
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

// Pick N random items from an array
function pickRandom<T>(array: T[], count: number): T[] {
  return shuffle(array).slice(0, count);
}

// Generate trivia questions personalized to the playing group
function generateTriviaQuestions(players: Player[], count: number): GameQuestion[] {
  const questions: GameQuestion[] = [];

  // Get all applicable templates
  let templates = [...triviaTemplates];

  // Add interest-based questions for each player's interests
  for (const player of players) {
    for (const interest of player.interests) {
      const key = interest.toLowerCase();
      if (interestQuestions[key]) {
        templates.push(...interestQuestions[key]);
      }
    }
  }

  // Filter by age appropriateness
  const hasYoungPlayers = players.some(p => p.age && p.age < 13);
  const hasTeens = players.some(p => p.age && p.age >= 13 && p.age < 18);

  if (hasYoungPlayers) {
    templates = templates.filter(t => t.ageAppropriate === 'all');
  } else if (hasTeens) {
    templates = templates.filter(t => t.ageAppropriate !== 'adult');
  }

  // Shuffle and generate questions
  const selectedTemplates = pickRandom(templates, count);

  for (const template of selectedTemplates) {
    // Pick a random subject player for the question
    const aboutPlayer = players[Math.floor(Math.random() * players.length)];
    // Pick someone else to answer (or all players)
    const otherPlayers = players.filter(p => p.id !== aboutPlayer.id);
    const forPlayer = otherPlayers.length > 0
      ? otherPlayers[Math.floor(Math.random() * otherPlayers.length)]
      : aboutPlayer;

    questions.push({
      id: generateId(),
      mode: 'trivia',
      text: template.question.replace('{name}', aboutPlayer.name),
      aboutPlayer,
      forPlayer,
      category: template.category,
      difficulty: template.difficulty,
    });
  }

  return questions;
}

// Generate conversation questions
function generateConversationQuestions(players: Player[], count: number): GameQuestion[] {
  const hasYoungPlayers = players.some(p => p.age && p.age < 13);
  const hasTeens = players.some(p => p.age && p.age >= 13 && p.age < 18);

  let cards = [...conversationCards];
  if (hasYoungPlayers) {
    cards = cards.filter(c => c.ageAppropriate === 'all');
  } else if (hasTeens) {
    cards = cards.filter(c => c.ageAppropriate !== 'adult');
  }

  const selected = pickRandom(cards, count);

  return selected.map((card, i) => ({
    id: generateId(),
    mode: 'conversation' as GameMode,
    text: card.prompt,
    forPlayer: players[i % players.length],
    category: card.category,
    difficulty: 'medium' as const,
    options: card.followUp ? [card.followUp] : undefined,
  }));
}

// Generate creative challenges
function generateCreativeQuestions(players: Player[], count: number): GameQuestion[] {
  let challenges = [...creativeChallenges];
  const hasYoungPlayers = players.some(p => p.age && p.age < 13);
  const hasTeens = players.some(p => p.age && p.age >= 13 && p.age < 18);

  if (hasYoungPlayers) {
    challenges = challenges.filter(c => c.ageAppropriate === 'all');
  } else if (hasTeens) {
    challenges = challenges.filter(c => c.ageAppropriate !== 'adult');
  }

  const selected = pickRandom(challenges, count);

  return selected.map((challenge, i) => ({
    id: generateId(),
    mode: 'creative' as GameMode,
    text: challenge.prompt,
    forPlayer: challenge.teamBased ? undefined : players[i % players.length],
    category: `${challenge.type.toUpperCase()} - ${challenge.category}`,
    difficulty: 'medium' as const,
    options: [
      challenge.instructions,
      ...(challenge.timeLimit ? [`Time: ${challenge.timeLimit} seconds`] : []),
      challenge.teamBased ? 'Everyone participates!' : '',
    ].filter(Boolean),
  }));
}

// Start a new game
export function startGame(mode: GameMode, players: Player[], roundCount: number = 8): GameState {
  let questions: GameQuestion[];

  switch (mode) {
    case 'trivia':
      questions = generateTriviaQuestions(players, roundCount);
      break;
    case 'conversation':
      questions = generateConversationQuestions(players, roundCount);
      break;
    case 'creative':
      questions = generateCreativeQuestions(players, roundCount);
      break;
  }

  const initialScores: Record<string, number> = {};
  players.forEach(p => { initialScores[p.id] = 0; });

  return {
    id: generateId(),
    mode,
    players,
    rounds: questions.map((q, i) => ({
      questionIndex: i,
      question: q,
      answers: {},
      scores: {},
    })),
    currentRound: 0,
    totalRounds: questions.length,
    scores: initialScores,
    currentPlayerIndex: 0,
    phase: 'question',
    startedAt: Date.now(),
  };
}

// Award points for a round
export function awardPoints(
  game: GameState,
  playerId: string,
  points: number
): GameState {
  const newGame = { ...game };
  newGame.scores = { ...game.scores };
  newGame.scores[playerId] = (newGame.scores[playerId] || 0) + points;

  const round = { ...newGame.rounds[game.currentRound] };
  round.scores = { ...round.scores };
  round.scores[playerId] = points;
  newGame.rounds = [...newGame.rounds];
  newGame.rounds[game.currentRound] = round;

  return newGame;
}

// Advance to next round
export function nextRound(game: GameState): GameState {
  const nextRoundIndex = game.currentRound + 1;

  if (nextRoundIndex >= game.totalRounds) {
    return { ...game, phase: 'finished' };
  }

  return {
    ...game,
    currentRound: nextRoundIndex,
    currentPlayerIndex: nextRoundIndex % game.players.length,
    phase: 'question',
  };
}

// Finish the game and save results
export async function finishGame(game: GameState): Promise<GameResult> {
  // Find fun moments
  const funMoments: string[] = [];

  // Find highest scorer
  const sortedPlayers = [...game.players].sort(
    (a, b) => (game.scores[b.id] || 0) - (game.scores[a.id] || 0)
  );

  if (sortedPlayers.length > 0) {
    funMoments.push(`${sortedPlayers[0].emoji} ${sortedPlayers[0].name} took the crown!`);
  }

  // Find closest rivalry
  if (sortedPlayers.length > 1) {
    const gap = (game.scores[sortedPlayers[0].id] || 0) - (game.scores[sortedPlayers[1].id] || 0);
    if (gap <= 2) {
      funMoments.push(`Nail-biter! ${sortedPlayers[0].name} and ${sortedPlayers[1].name} were neck and neck!`);
    }
  }

  funMoments.push(`${game.totalRounds} rounds of ${game.mode} played together!`);

  const result: GameResult = {
    id: game.id,
    mode: game.mode,
    players: game.players,
    scores: game.scores,
    rounds: game.rounds,
    funMoments,
    playedAt: Date.now(),
  };

  // Persist
  await saveGameResult(result);
  await incrementGamesPlayed(game.players.map(p => p.id));

  return result;
}

// Get the current question
export function getCurrentQuestion(game: GameState): GameQuestion | null {
  if (game.currentRound >= game.rounds.length) return null;
  return game.rounds[game.currentRound].question;
}

// Get leaderboard
export function getLeaderboard(game: GameState): Array<{ player: Player; score: number; rank: number }> {
  return game.players
    .map(player => ({
      player,
      score: game.scores[player.id] || 0,
      rank: 0,
    }))
    .sort((a, b) => b.score - a.score)
    .map((entry, i) => ({ ...entry, rank: i + 1 }));
}
