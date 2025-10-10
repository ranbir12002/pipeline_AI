// src/App.tsx

import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { useAuthStore } from './store/authStore';
import Login from './pages/Login';
import Signup from './pages/Singup';
import Chat from './pages/Chat';
import axios from 'axios'; // <-- Make sure to import axios

// Your ProtectedRoute and PublicRoute components remain the same...

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  if (!isAuthenticated) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  if (isAuthenticated) {
    return <Navigate to="/chat" replace />;
  }
  return <>{children}</>;
}


// A new component to contain the logic, to access hooks
function AppLogic() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((state) => state.setGithubAuth); // <-- Get the new setAuth function

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');

    if (code) {
      const handleGithubCallback = async (authCode: string) => {
        try {
          // Send the code to your backend
          const response = await axios.post('http://localhost:4000/auth/github', { code: authCode });
          
          // Assuming your backend responds with { user, token }
          const { user, token } = response.data;

          // Use the new store action to set the authentication state
          setAuth(user, token);

          // Clean the URL (removes the ?code=... part)
          window.history.pushState({}, '', '/chat');
          
          // Navigate to the chat page
          navigate('/chat');

        } catch (error) {
          console.error("Error authenticating with GitHub:", error);
          // Optional: redirect to login with an error message
          navigate('/?error=github_auth_failed');
        }
      };

      handleGithubCallback(code);
    }
  }, [navigate, setAuth]);

  return (
    <Routes>
      <Route
        path="/"
        element={
          <PublicRoute>
            <Login />
          </PublicRoute>
        }
      />
      <Route
        path="/signup"
        element={
          <PublicRoute>
            <Signup />
          </PublicRoute>
        }
      />
      <Route
        path="/chat"
        element={
          <ProtectedRoute>
            <Chat />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}


function App() {
  return (
    <BrowserRouter>
      <AppLogic />
    </BrowserRouter>
  );
}

export default App;