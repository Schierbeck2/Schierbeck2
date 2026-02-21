import { Player } from '../types';

// Templates for trivia questions about family members
// {name} gets replaced with the subject player's name
// These questions help families learn about each other

export interface TriviaTemplate {
  question: string;
  category: string;
  generateOptions?: (player: Player) => string[];
  difficulty: 'easy' | 'medium' | 'hard';
  ageAppropriate: 'all' | 'teen+' | 'adult';
}

export const triviaTemplates: TriviaTemplate[] = [
  // Favorites
  {
    question: "What is {name}'s favorite color?",
    category: 'Favorites',
    difficulty: 'easy',
    ageAppropriate: 'all',
  },
  {
    question: "What is {name}'s favorite food?",
    category: 'Favorites',
    difficulty: 'easy',
    ageAppropriate: 'all',
  },
  {
    question: "What is {name}'s favorite movie or TV show?",
    category: 'Favorites',
    difficulty: 'easy',
    ageAppropriate: 'all',
  },
  {
    question: "What is {name}'s favorite season of the year?",
    category: 'Favorites',
    difficulty: 'easy',
    ageAppropriate: 'all',
  },
  {
    question: "What is {name}'s favorite animal?",
    category: 'Favorites',
    difficulty: 'easy',
    ageAppropriate: 'all',
  },
  {
    question: "What is {name}'s favorite song or band?",
    category: 'Favorites',
    difficulty: 'medium',
    ageAppropriate: 'all',
  },
  {
    question: "What is {name}'s favorite holiday?",
    category: 'Favorites',
    difficulty: 'easy',
    ageAppropriate: 'all',
  },
  {
    question: "What is {name}'s favorite thing to do on a weekend?",
    category: 'Favorites',
    difficulty: 'medium',
    ageAppropriate: 'all',
  },

  // Personality
  {
    question: "Is {name} more of a morning person or a night owl?",
    category: 'Personality',
    difficulty: 'easy',
    ageAppropriate: 'all',
  },
  {
    question: "What makes {name} laugh the most?",
    category: 'Personality',
    difficulty: 'medium',
    ageAppropriate: 'all',
  },
  {
    question: "What is {name} most afraid of?",
    category: 'Personality',
    difficulty: 'medium',
    ageAppropriate: 'all',
  },
  {
    question: "What is {name}'s hidden talent?",
    category: 'Personality',
    difficulty: 'hard',
    ageAppropriate: 'all',
  },
  {
    question: "What would {name}'s superpower be if they could choose one?",
    category: 'Personality',
    difficulty: 'medium',
    ageAppropriate: 'all',
  },
  {
    question: "What is {name}'s most-used emoji?",
    category: 'Personality',
    difficulty: 'hard',
    ageAppropriate: 'all',
  },

  // Dreams & Wishes
  {
    question: "Where would {name} most love to travel?",
    category: 'Dreams',
    difficulty: 'medium',
    ageAppropriate: 'all',
  },
  {
    question: "What did {name} want to be when they grew up?",
    category: 'Dreams',
    difficulty: 'medium',
    ageAppropriate: 'all',
  },
  {
    question: "If {name} won the lottery, what would they do first?",
    category: 'Dreams',
    difficulty: 'medium',
    ageAppropriate: 'all',
  },
  {
    question: "What is something on {name}'s bucket list?",
    category: 'Dreams',
    difficulty: 'hard',
    ageAppropriate: 'all',
  },

  // Memories
  {
    question: "What is {name}'s favorite family memory?",
    category: 'Memories',
    difficulty: 'hard',
    ageAppropriate: 'all',
  },
  {
    question: "What was {name}'s most embarrassing moment?",
    category: 'Memories',
    difficulty: 'hard',
    ageAppropriate: 'all',
  },
  {
    question: "What was the best gift {name} ever received?",
    category: 'Memories',
    difficulty: 'medium',
    ageAppropriate: 'all',
  },
  {
    question: "What is {name}'s favorite family tradition?",
    category: 'Memories',
    difficulty: 'medium',
    ageAppropriate: 'all',
  },

  // Hypotheticals
  {
    question: "If {name} could have dinner with anyone, who would it be?",
    category: 'Hypothetical',
    difficulty: 'medium',
    ageAppropriate: 'all',
  },
  {
    question: "If {name} could live in any time period, when would it be?",
    category: 'Hypothetical',
    difficulty: 'hard',
    ageAppropriate: 'teen+',
  },
  {
    question: "If {name} were stranded on an island, what 3 things would they bring?",
    category: 'Hypothetical',
    difficulty: 'medium',
    ageAppropriate: 'all',
  },
  {
    question: "What would {name} name their autobiography?",
    category: 'Hypothetical',
    difficulty: 'hard',
    ageAppropriate: 'teen+',
  },
];

// Interest-based bonus questions
export const interestQuestions: Record<string, TriviaTemplate[]> = {
  sports: [
    { question: "What is {name}'s favorite sports team?", category: 'Interests', difficulty: 'easy', ageAppropriate: 'all' },
    { question: "What sport did {name} play growing up?", category: 'Interests', difficulty: 'medium', ageAppropriate: 'all' },
  ],
  music: [
    { question: "What was the first concert {name} ever attended?", category: 'Interests', difficulty: 'hard', ageAppropriate: 'all' },
    { question: "What instrument does (or would) {name} play?", category: 'Interests', difficulty: 'medium', ageAppropriate: 'all' },
  ],
  cooking: [
    { question: "What is {name}'s signature dish?", category: 'Interests', difficulty: 'medium', ageAppropriate: 'all' },
    { question: "What food will {name} absolutely not eat?", category: 'Interests', difficulty: 'easy', ageAppropriate: 'all' },
  ],
  travel: [
    { question: "What is {name}'s favorite place they've visited?", category: 'Interests', difficulty: 'medium', ageAppropriate: 'all' },
    { question: "Does {name} prefer the beach or the mountains?", category: 'Interests', difficulty: 'easy', ageAppropriate: 'all' },
  ],
  gaming: [
    { question: "What is {name}'s all-time favorite video game?", category: 'Interests', difficulty: 'medium', ageAppropriate: 'all' },
  ],
  reading: [
    { question: "What is {name}'s favorite book?", category: 'Interests', difficulty: 'medium', ageAppropriate: 'all' },
    { question: "What genre does {name} read the most?", category: 'Interests', difficulty: 'easy', ageAppropriate: 'all' },
  ],
  movies: [
    { question: "What movie can {name} watch over and over?", category: 'Interests', difficulty: 'easy', ageAppropriate: 'all' },
    { question: "Who is {name}'s favorite actor or actress?", category: 'Interests', difficulty: 'medium', ageAppropriate: 'all' },
  ],
  outdoors: [
    { question: "What is {name}'s favorite outdoor activity?", category: 'Interests', difficulty: 'easy', ageAppropriate: 'all' },
  ],
  art: [
    { question: "What kind of art does {name} enjoy most?", category: 'Interests', difficulty: 'medium', ageAppropriate: 'all' },
  ],
};
