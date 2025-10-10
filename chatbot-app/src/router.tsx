import { createBrowserRouter } from 'react-router-dom';
import Login from './pages/Login';
import Signup from './pages/Singup';
import Chat from './pages/Chat';
// import Dashboard from './pages/Dashboard';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Login />,
  },
  {
    path: '/signup',
    element: <Signup />,
  },
  {
    path: '/chat',
    element: <Chat />,
  },
  // {
  //   path: '/dashboard',
  //   element: <Dashboard />,
  // },
]);