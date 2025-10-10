import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// The User interface is good as is.
interface User {
  id: string;
  email: string;
  name: string;
}

interface AuthState {
  user: User | null;
  token: string | null; // <-- ADDED: To store JWT or session token
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  setGithubAuth: (user: User, token: string) => void; // <-- ADDED: The new function for GitHub OAuth
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null, // <-- ADDED: Initial state for the token
      isAuthenticated: false,
      
      login: async (email: string, password: string) => {
        // ... (your existing login logic is unchanged)
        await new Promise(resolve => setTimeout(resolve, 1000));
        if (password.length < 6) {
          throw new Error('Invalid credentials');
        }
        const user = {
          id: '1',
          email,
          name: email.split('@')[0],
        };
        // For consistency, you might want to handle a token here too
        set({ user, isAuthenticated: true, token: 'mock-jwt-token' });
      },
      
      signup: async (name: string, email: string, password: string) => {
        // ... (your existing signup logic is unchanged)
        await new Promise(resolve => setTimeout(resolve, 1000));
        if (password.length < 6) {
          throw new Error('Password must be at least 6 characters');
        }
        const user = {
          id: '1',
          email,
          name,
        };
        // For consistency, you might want to handle a token here too
        set({ user, isAuthenticated: true, token: 'mock-jwt-token' });
      },
      
      // ADDED: The implementation for our new function
      setGithubAuth: (user: User, token: string) => {
        set({
          user: user,
          isAuthenticated: true,
          token: token,
        });
      },
      
      logout: () => {
        // UPDATED: Ensure the token is also cleared on logout
        set({ user: null, isAuthenticated: false, token: null });
      },
    }),
    {
      name: 'auth-storage', // This name is used for the key in localStorage
    }
  )
);