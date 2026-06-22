import { useState, useEffect } from 'react';
import SessionSidebar from './components/SessionSidebar';
import ChatWindow from './components/ChatWindow';

function App() {
  const [activeSession, setActiveSession] = useState(null);
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem('theme');
    if (saved) return saved;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });

  useEffect(() => {
    localStorage.setItem('theme', theme);
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => (prev === 'dark' ? 'light' : 'dark'));
  };

  return (
    <div className={`flex h-screen overflow-hidden transition-colors duration-200 ${
      theme === 'dark' ? 'bg-[#0f1117] text-slate-100' : 'bg-[#f8fafc] text-slate-800'
    }`}>
      <SessionSidebar 
        activeSession={activeSession} 
        onSelectSession={setActiveSession}
        theme={theme}
      />
      {activeSession ? (
        <ChatWindow 
          sessionId={activeSession} 
          theme={theme} 
          toggleTheme={toggleTheme} 
        />
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center gap-6 p-8 relative">
          {/* Top-Right Theme Toggle when no session is open */}
          <button 
            onClick={toggleTheme}
            className={`absolute top-6 right-6 p-2.5 rounded-xl border transition-all duration-150 ${
              theme === 'dark' 
                ? 'border-slate-800 bg-[#13151f] text-amber-400 hover:bg-slate-800' 
                : 'border-slate-200 bg-white text-indigo-600 hover:bg-slate-50 shadow-sm'
            }`}
            title="Toggle theme"
          >
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>

          <div className="w-20 h-20 rounded-2xl bg-indigo-600/10 flex items-center justify-center text-4xl shadow-inner">
            📇
          </div>
          <div className="text-center max-w-sm">
            <h1 className={`text-2xl font-bold tracking-tight mb-2 ${
              theme === 'dark' ? 'text-white' : 'text-slate-900'
            }`}>
              Welcome to CardFlow
            </h1>
            <p className={`text-sm ${
              theme === 'dark' ? 'text-slate-400' : 'text-slate-600'
            }`}>
              Select a session from the sidebar or click **+ New Session** to start digitizing business cards and orchestrating CRM contacts.
            </p>
          </div>

          <div className={`mt-8 p-5 rounded-2xl border flex flex-col items-center gap-3.5 max-w-sm w-full ${
            theme === 'dark' ? 'border-slate-800 bg-[#13151f]/50' : 'border-slate-200 bg-white shadow-sm'
          }`}>
            <p className="text-xs uppercase tracking-wider text-slate-500 font-semibold">Integrations Included</p>
            <div className="flex items-center gap-6">
              <span className="text-2xl" title="Google Sheets">📊</span>
              <span className="text-2xl" title="WhatsApp Business API">💬</span>
              <span className="text-2xl" title="Google Gemini API">🤖</span>
              <span className="text-2xl" title="LangGraph Orchestration">🕸️</span>
            </div>
            <p className="text-[10px] text-slate-400 font-medium">Powered by LangGraph + Gemini</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
