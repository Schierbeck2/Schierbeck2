// Creative challenges - drawing, acting, storytelling prompts for families

export interface CreativeChallenge {
  type: 'draw' | 'act' | 'story' | 'build' | 'sing';
  prompt: string;
  instructions: string;
  timeLimit?: number; // seconds
  category: string;
  teamBased: boolean; // true = work together, false = individual
  ageAppropriate: 'all' | 'teen+' | 'adult';
}

export const creativeChallenges: CreativeChallenge[] = [
  // Drawing challenges
  {
    type: 'draw',
    prompt: "Draw your favorite family memory",
    instructions: "You have 60 seconds! No words allowed. Everyone else guesses what memory it is.",
    timeLimit: 60,
    category: 'Drawing',
    teamBased: false,
    ageAppropriate: 'all',
  },
  {
    type: 'draw',
    prompt: "Draw another family member as a superhero",
    instructions: "Include their superpower! The person drawn gets to guess their power.",
    timeLimit: 90,
    category: 'Drawing',
    teamBased: false,
    ageAppropriate: 'all',
  },
  {
    type: 'draw',
    prompt: "Draw what our family would look like as animals",
    instructions: "Draw all family members as the animal that best represents them. Everyone guesses who is who!",
    timeLimit: 120,
    category: 'Drawing',
    teamBased: false,
    ageAppropriate: 'all',
  },
  {
    type: 'draw',
    prompt: "Design a family crest",
    instructions: "Include symbols that represent your family's values, inside jokes, or shared interests.",
    timeLimit: 120,
    category: 'Drawing',
    teamBased: true,
    ageAppropriate: 'all',
  },
  {
    type: 'draw',
    prompt: "Collaborative drawing: each person adds to the picture",
    instructions: "First person starts, then pass it along. Each person has 15 seconds to add something. No talking!",
    timeLimit: 15,
    category: 'Drawing',
    teamBased: true,
    ageAppropriate: 'all',
  },

  // Acting challenges
  {
    type: 'act',
    prompt: "Act out a family inside joke without speaking",
    instructions: "No words! Use only gestures and expressions. Others try to guess the inside joke.",
    timeLimit: 60,
    category: 'Acting',
    teamBased: false,
    ageAppropriate: 'all',
  },
  {
    type: 'act',
    prompt: "Impersonate another family member's morning routine",
    instructions: "Act it out and everyone guesses who you're being. Be kind and funny!",
    timeLimit: 45,
    category: 'Acting',
    teamBased: false,
    ageAppropriate: 'all',
  },
  {
    type: 'act',
    prompt: "Act out a famous movie scene - family style",
    instructions: "Pick a famous movie scene and act it out. Others guess the movie!",
    timeLimit: 60,
    category: 'Acting',
    teamBased: false,
    ageAppropriate: 'all',
  },
  {
    type: 'act',
    prompt: "Freeze frame challenge: strike a pose that represents your mood",
    instructions: "On the count of 3, everyone freezes in a pose. Then explain your pose!",
    category: 'Acting',
    teamBased: true,
    ageAppropriate: 'all',
  },
  {
    type: 'act',
    prompt: "Commercial time: sell something ordinary as if it's amazing",
    instructions: "Pick any household object and create a 30-second infomercial for it. Be dramatic!",
    timeLimit: 30,
    category: 'Acting',
    teamBased: false,
    ageAppropriate: 'all',
  },

  // Storytelling challenges
  {
    type: 'story',
    prompt: "Round-robin story: one sentence at a time",
    instructions: "First player starts with 'Once upon a time...' Each person adds one sentence. Go around 3 times!",
    category: 'Storytelling',
    teamBased: true,
    ageAppropriate: 'all',
  },
  {
    type: 'story',
    prompt: "Two truths and a dream",
    instructions: "Share two true things about yourself and one thing you wish were true. Others guess which is the dream!",
    category: 'Storytelling',
    teamBased: false,
    ageAppropriate: 'all',
  },
  {
    type: 'story',
    prompt: "Tell the story of how you met your best friend",
    instructions: "Share the story! Other family members can ask questions.",
    category: 'Storytelling',
    teamBased: false,
    ageAppropriate: 'all',
  },
  {
    type: 'story',
    prompt: "Create a family origin story - but make it epic",
    instructions: "Retell how your family came together as if it were a movie trailer. Be dramatic, exaggerate, have fun!",
    category: 'Storytelling',
    teamBased: true,
    ageAppropriate: 'all',
  },
  {
    type: 'story',
    prompt: "Future prediction: What will each family member be doing in 10 years?",
    instructions: "Make a prediction for every player. Be creative and positive! The person being predicted gets to react.",
    category: 'Storytelling',
    teamBased: false,
    ageAppropriate: 'all',
  },
  {
    type: 'story',
    prompt: "Caption this: describe a photo from memory in the most dramatic way possible",
    instructions: "Think of a family photo and describe what's happening as if you're narrating a documentary.",
    timeLimit: 60,
    category: 'Storytelling',
    teamBased: false,
    ageAppropriate: 'all',
  },

  // Build/Create challenges
  {
    type: 'build',
    prompt: "Design the family's dream vacation",
    instructions: "Work together! Each person contributes one must-do activity. Plan the ultimate family trip.",
    category: 'Creating',
    teamBased: true,
    ageAppropriate: 'all',
  },
  {
    type: 'build',
    prompt: "Create a family motto",
    instructions: "Everyone suggests ideas. Vote on the best one. Bonus points if it rhymes!",
    category: 'Creating',
    teamBased: true,
    ageAppropriate: 'all',
  },
  {
    type: 'build',
    prompt: "Playlist challenge: build a family road trip playlist",
    instructions: "Each person picks 2 songs. Explain why each song is essential for the drive!",
    category: 'Creating',
    teamBased: true,
    ageAppropriate: 'all',
  },

  // Singing challenges
  {
    type: 'sing',
    prompt: "Sing a song that describes your week",
    instructions: "Pick any song and sing the chorus. Explain why it fits your week!",
    category: 'Singing',
    teamBased: false,
    ageAppropriate: 'all',
  },
  {
    type: 'sing',
    prompt: "Family karaoke: everyone sings one line of the same song",
    instructions: "Pick a song everyone knows. Go around the group, each person sings the next line!",
    category: 'Singing',
    teamBased: true,
    ageAppropriate: 'all',
  },
  {
    type: 'sing',
    prompt: "Make up a jingle about your family",
    instructions: "Create a short song (4 lines) about your family. Perform it together!",
    timeLimit: 120,
    category: 'Singing',
    teamBased: true,
    ageAppropriate: 'all',
  },
];

export const challengeTypeEmojis: Record<CreativeChallenge['type'], string> = {
  draw: '🎨',
  act: '🎭',
  story: '📖',
  build: '🏗️',
  sing: '🎤',
};
