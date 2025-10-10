export interface User {
  id: string;
  email: string;
  name: string;
}

export interface Message {
  id: string;
  type: 'user' | 'bot' | 'quick-actions';
  content: string;
  timestamp: Date;
  codeBlock?: string;
  codeLanguage?: string;
  list?: string[];
  listType?: 'instructions' | 'suggestions';
  fullData?: boolean;
}

export interface LoginFormData {
  email: string;
  password: string;
}

export interface SignupFormData {
  name: string;
  email: string;
  password: string;
  confirmPassword: string;
}