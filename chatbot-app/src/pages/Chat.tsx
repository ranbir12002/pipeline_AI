import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { LogOut, Terminal } from 'lucide-react';

export default function Chat() {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      <div className="bg-black/40 backdrop-blur-lg border-b border-purple-500/30 px-6 py-4">
        <div className="flex items-center justify-between max-w-7xl mx-auto">
          <div className="flex items-center gap-3">
            <div className="bg-gradient-to-r from-purple-500 to-pink-500 p-2 rounded-lg">
              <Terminal className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">CI Workflow Assistant</h1>
              <p className="text-sm text-purple-300">Welcome back, {user?.name}!</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 bg-slate-800/50 hover:bg-slate-700/50 text-white px-4 py-2 rounded-lg transition-all border border-purple-500/30"
          >
            <LogOut className="w-4 h-4" />
            Logout
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex items-center justify-center h-[calc(100vh-80px)] p-6">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-24 h-24 bg-gradient-to-r from-purple-500 to-pink-500 rounded-2xl mb-6">
            <Terminal className="w-12 h-12 text-white" />
          </div>
          <h2 className="text-3xl font-bold text-white mb-4">Chat Interface Coming Soon!</h2>
          <p className="text-gray-400 max-w-md mx-auto">
            The complete chat interface with CI workflow assistance will be implemented next.
            For now, you can test the authentication flow.
          </p>
          <div className="mt-8 inline-flex items-center gap-2 bg-purple-500/10 border border-purple-500/30 px-6 py-3 rounded-lg">
            <span className="text-purple-300">Logged in as:</span>
            <span className="text-white font-semibold">{user?.email}</span>
          </div>
        </div>
      </div>
    </div>
  );
}