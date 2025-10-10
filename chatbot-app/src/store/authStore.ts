import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: string;
  email: string;
  name: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      
      login: async (email: string, password: string) => {
        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // TODO: Replace with actual API call
        // Example:
        // const response = await fetch('/api/auth/login', {
        //   method: 'POST',
        //   headers: { 'Content-Type': 'application/json' },
        //   body: JSON.stringify({ email, password })
        // });
        // const data = await response.json();
        
        // Mock validation - remove this in production
        if (password.length < 6) {
          throw new Error('Invalid credentials');
        }
        
        // Mock user data - replace with actual API response
        const user = {
          id: '1',
          email,
          name: email.split('@')[0],
        };
        
        set({ user, isAuthenticated: true });
      },
      
      signup: async (name: string, email: string, password: string) => {
        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // TODO: Replace with actual API call
        // Example:
        // const response = await fetch('/api/auth/signup', {
        //   method: 'POST',
        //   headers: { 'Content-Type': 'application/json' },
        //   body: JSON.stringify({ name, email, password })
        // });
        // const data = await response.json();
        
        // Mock validation - remove this in production
        if (password.length < 6) {
          throw new Error('Password must be at least 6 characters');
        }
        
        // Mock user data - replace with actual API response
        const user = {
          id: '1',
          email,
          name,
        };
        
        set({ user, isAuthenticated: true });
      },
      
      logout: () => {
        set({ user: null, isAuthenticated: false });
      },
    }),
    {
      name: 'auth-storage',
    }
  )
);