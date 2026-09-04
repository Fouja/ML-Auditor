import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Tokens, User } from '../types';

interface AuthState {
  user: User | null;
  tokens: Tokens | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  setAuth: (user: User, tokens: Tokens) => Promise<void>;
  setUser: (user: User) => Promise<void>;
  logout: () => Promise<void>;
  hydrate: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  tokens: null,
  isLoading: true,
  isAuthenticated: false,

  setAuth: async (user, tokens) => {
    await AsyncStorage.setItem('tokens', JSON.stringify(tokens));
    await AsyncStorage.setItem('user', JSON.stringify(user));
    set({ user, tokens, isAuthenticated: true });
  },

  setUser: async (user) => {
    await AsyncStorage.setItem('user', JSON.stringify(user));
    set({ user });
  },

  logout: async () => {
    await AsyncStorage.removeItem('tokens');
    await AsyncStorage.removeItem('user');
    set({ user: null, tokens: null, isAuthenticated: false });
  },

  hydrate: async () => {
    try {
      const [tokensJson, userJson] = await Promise.all([
        AsyncStorage.getItem('tokens'),
        AsyncStorage.getItem('user'),
      ]);
      if (tokensJson && userJson) {
        const tokens = JSON.parse(tokensJson);
        const user = JSON.parse(userJson);
        set({ user, tokens, isAuthenticated: true });
      }
    } finally {
      set({ isLoading: false });
    }
  },
}));
