// Family Game Night - Design System
// Warm, inviting colors that work across generations

export const colors = {
  // Primary palette
  primary: '#6C63FF',      // Friendly purple
  primaryLight: '#8B83FF',
  primaryDark: '#4A42D4',

  // Accent colors
  accent: '#FF6B6B',       // Warm coral
  accentLight: '#FF8E8E',
  success: '#4ECB71',      // Fresh green
  warning: '#FFB347',      // Warm orange
  info: '#54C7FC',         // Sky blue

  // Game mode colors
  trivia: '#FF6B6B',
  conversation: '#4ECB71',
  creative: '#FFB347',

  // Backgrounds
  background: '#1A1A2E',    // Deep navy
  surface: '#252547',       // Card background
  surfaceLight: '#2D2D5E',  // Elevated surface
  overlay: 'rgba(0,0,0,0.5)',

  // Text
  text: '#FFFFFF',
  textSecondary: '#B8B8D4',
  textMuted: '#6C6C8A',

  // Borders
  border: '#3A3A5C',
  borderLight: '#4A4A6C',
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
};

export const borderRadius = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  full: 999,
};

export const fontSize = {
  xs: 12,
  sm: 14,
  md: 16,
  lg: 20,
  xl: 24,
  xxl: 32,
  hero: 40,
};

export const shadows = {
  card: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 8,
    elevation: 5,
  },
  button: {
    shadowColor: '#6C63FF',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
};
