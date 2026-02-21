import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { colors } from '../lib/theme';

export default function RootLayout() {
  return (
    <>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: colors.background },
          headerTintColor: colors.text,
          headerTitleStyle: { fontWeight: '700' },
          contentStyle: { backgroundColor: colors.background },
          headerShadowVisible: false,
        }}
      >
        <Stack.Screen
          name="index"
          options={{ title: 'Family Game Night', headerShown: false }}
        />
        <Stack.Screen
          name="add-player"
          options={{ title: 'Add Player', presentation: 'modal' }}
        />
        <Stack.Screen
          name="lobby"
          options={{ title: 'Game Lobby' }}
        />
        <Stack.Screen
          name="game"
          options={{ title: 'Playing', headerBackVisible: false, gestureEnabled: false }}
        />
        <Stack.Screen
          name="results"
          options={{ title: 'Results', headerBackVisible: false, gestureEnabled: false }}
        />
      </Stack>
    </>
  );
}
