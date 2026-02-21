// Conversation starter cards - prompts that spark discussion across generations
// These are designed to be thought-provoking, fun, and bring families closer

export interface ConversationCard {
  prompt: string;
  followUp?: string; // optional follow-up question
  category: string;
  mood: 'fun' | 'deep' | 'nostalgic' | 'creative' | 'silly';
  ageAppropriate: 'all' | 'teen+' | 'adult';
}

export const conversationCards: ConversationCard[] = [
  // Fun & Light
  {
    prompt: "If our family had a theme song, what would it be?",
    followUp: "Everyone hum their suggestion!",
    category: 'Family',
    mood: 'fun',
    ageAppropriate: 'all',
  },
  {
    prompt: "If you could swap lives with another family member for a day, who would you choose and why?",
    category: 'Family',
    mood: 'fun',
    ageAppropriate: 'all',
  },
  {
    prompt: "What's the funniest thing that's ever happened to our family?",
    followUp: "Does everyone remember it the same way?",
    category: 'Memories',
    mood: 'fun',
    ageAppropriate: 'all',
  },
  {
    prompt: "If our family was a TV show, what genre would it be?",
    category: 'Family',
    mood: 'fun',
    ageAppropriate: 'all',
  },
  {
    prompt: "What's the weirdest food combination you secretly enjoy?",
    category: 'Quirks',
    mood: 'fun',
    ageAppropriate: 'all',
  },
  {
    prompt: "If you could have any animal as a pet (no matter how wild), what would you choose?",
    category: 'Imagination',
    mood: 'fun',
    ageAppropriate: 'all',
  },
  {
    prompt: "What's the most useless talent you have?",
    followUp: "Demonstrate it for everyone!",
    category: 'Quirks',
    mood: 'silly',
    ageAppropriate: 'all',
  },
  {
    prompt: "If you had to eat one meal for the rest of your life, what would it be?",
    category: 'Favorites',
    mood: 'fun',
    ageAppropriate: 'all',
  },

  // Deep & Meaningful
  {
    prompt: "What's the best piece of advice you've ever received? Who gave it to you?",
    category: 'Wisdom',
    mood: 'deep',
    ageAppropriate: 'all',
  },
  {
    prompt: "What's something you're really proud of that you don't talk about much?",
    category: 'Personal',
    mood: 'deep',
    ageAppropriate: 'all',
  },
  {
    prompt: "What's one thing you wish you could tell your younger self?",
    category: 'Reflection',
    mood: 'deep',
    ageAppropriate: 'teen+',
  },
  {
    prompt: "What does 'home' mean to you?",
    category: 'Values',
    mood: 'deep',
    ageAppropriate: 'all',
  },
  {
    prompt: "What family value do you think is most important to pass down?",
    category: 'Values',
    mood: 'deep',
    ageAppropriate: 'all',
  },
  {
    prompt: "What's something about another family member that you really admire?",
    followUp: "Tell them directly!",
    category: 'Family',
    mood: 'deep',
    ageAppropriate: 'all',
  },
  {
    prompt: "What moment in your life changed you the most?",
    category: 'Reflection',
    mood: 'deep',
    ageAppropriate: 'teen+',
  },
  {
    prompt: "If you could master any skill instantly, what would it be and why?",
    category: 'Dreams',
    mood: 'deep',
    ageAppropriate: 'all',
  },

  // Nostalgic
  {
    prompt: "What's your earliest memory?",
    followUp: "How old were you?",
    category: 'Memories',
    mood: 'nostalgic',
    ageAppropriate: 'all',
  },
  {
    prompt: "What was your favorite toy or game growing up?",
    category: 'Memories',
    mood: 'nostalgic',
    ageAppropriate: 'all',
  },
  {
    prompt: "Tell us about a family tradition from when you were young.",
    followUp: "Should we bring that tradition back?",
    category: 'Traditions',
    mood: 'nostalgic',
    ageAppropriate: 'all',
  },
  {
    prompt: "What's the best vacation or trip our family has taken together?",
    followUp: "What made it so special?",
    category: 'Memories',
    mood: 'nostalgic',
    ageAppropriate: 'all',
  },
  {
    prompt: "What was a typical Sunday like in your family when you were growing up?",
    category: 'Memories',
    mood: 'nostalgic',
    ageAppropriate: 'all',
  },
  {
    prompt: "What was the first thing you ever cooked or baked?",
    followUp: "Was it any good?",
    category: 'Memories',
    mood: 'nostalgic',
    ageAppropriate: 'all',
  },
  {
    prompt: "What song reminds you of a specific moment in your life?",
    category: 'Memories',
    mood: 'nostalgic',
    ageAppropriate: 'all',
  },

  // Creative & Imaginative
  {
    prompt: "If our family could time travel to any era, where should we go?",
    followUp: "What would we do there?",
    category: 'Imagination',
    mood: 'creative',
    ageAppropriate: 'all',
  },
  {
    prompt: "Invent a new family holiday. What would we celebrate and how?",
    category: 'Imagination',
    mood: 'creative',
    ageAppropriate: 'all',
  },
  {
    prompt: "If you could design your dream house, what's the one room you'd definitely include?",
    category: 'Imagination',
    mood: 'creative',
    ageAppropriate: 'all',
  },
  {
    prompt: "If our family opened a restaurant together, what would we serve and what would it be called?",
    category: 'Imagination',
    mood: 'creative',
    ageAppropriate: 'all',
  },
  {
    prompt: "If you could create a new tradition for our family, what would it be?",
    category: 'Traditions',
    mood: 'creative',
    ageAppropriate: 'all',
  },

  // Silly
  {
    prompt: "What's the most ridiculous thing you've ever argued about?",
    category: 'Quirks',
    mood: 'silly',
    ageAppropriate: 'all',
  },
  {
    prompt: "If you were a sandwich, what kind would you be?",
    followUp: "Now assign sandwich types to everyone else!",
    category: 'Silly',
    mood: 'silly',
    ageAppropriate: 'all',
  },
  {
    prompt: "What's the worst fashion choice you've ever made?",
    followUp: "Does any photographic evidence exist?",
    category: 'Quirks',
    mood: 'silly',
    ageAppropriate: 'all',
  },
  {
    prompt: "If you could only communicate using one movie quote for a whole day, what would it be?",
    category: 'Silly',
    mood: 'silly',
    ageAppropriate: 'all',
  },
  {
    prompt: "What's the strangest dream you've ever had?",
    category: 'Quirks',
    mood: 'silly',
    ageAppropriate: 'all',
  },
  {
    prompt: "Act out your morning routine in 30 seconds. Everyone guess what each step is!",
    category: 'Silly',
    mood: 'silly',
    ageAppropriate: 'all',
  },
];
