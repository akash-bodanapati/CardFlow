import React from 'react';
import { apiClient } from '../api/client';

export default function SessionSidebar({ activeSession, onSelectSession, theme }) {
  const [sessions, setSessions] = React.useState([]);
  const [sessionToDelete, setSessionToDelete] = React.useState(null);

  React.useEffect(() => {
    loadSessions();
  }, [activeSession]); // Reload on active session change to sync snippets

  // Escape key listener to close custom delete confirmation modal
  React.useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setSessionToDelete(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const loadSessions = async () => {
    try {
      const data = await apiClient.getSessions();
      setSessions(data);
    } catch (e) {
      console.error(e);
    }
  };

  const createSession = async () => {
    try {
      const data = await apiClient.createSession();
      const dateStr = new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      const tempLabel = `New Session · ${dateStr}`;
      
      const newSession = { 
        session_id: data.session_id, 
        label: tempLabel, 
        last_message: "No messages yet" 
      };
      setSessions([newSession, ...sessions]);
      onSelectSession(data.session_id);
    } catch (e) {
      console.error(e);
    }
  };

  const handleConfirmDelete = async () => {
    if (!sessionToDelete) return;
    try {
      await apiClient.deleteSession(sessionToDelete);
      const updated = sessions.filter(s => s.session_id !== sessionToDelete);
      setSessions(updated);
      
      if (activeSession === sessionToDelete) {
        if (updated.length > 0) {
          onSelectSession(updated[0].session_id);
        } else {
          onSelectSession(null);
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSessionToDelete(null);
    }
  };

  const formatId = (id) => id ? id.slice(0, 8) + '…' : '—';

  const isDark = theme === 'dark';

  return (
    <div className={`w-64 shrink-0 border-r flex flex-col transition-colors duration-150 ${
      isDark ? 'bg-[#13151f] border-slate-800/80' : 'bg-[#fcfdfe] border-slate-200'
    }`}>
      {/* Logo / Branding */}
      <div className={`px-5 py-5 border-b transition-colors duration-150 ${
        isDark ? 'border-slate-800/80' : 'border-slate-100'
      }`}>
        <div className="flex items-center gap-2.5">
          <span className="text-2xl filter drop-shadow-md">📇</span>
          <span className={`text-lg font-bold tracking-tight ${
            isDark ? 'text-white' : 'text-slate-900'
          }`}>
            CardFlow
          </span>
        </div>
        <p className={`text-xs mt-1 font-medium ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
          Business Card Digitizer
        </p>
      </div>

      {/* New Session Button */}
      <div className="px-4 py-4">
        <button 
          onClick={createSession}
          className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold py-2.5 px-4 rounded-xl transition-all duration-150 shadow-md shadow-indigo-600/10 hover:shadow-indigo-600/20 active:scale-[0.98]"
        >
          <span className="text-lg font-normal">+</span>
          New Session
        </button>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto px-3 py-1 space-y-1">
        <p className={`text-[10px] uppercase tracking-widest px-2 mb-2 font-bold ${
          isDark ? 'text-slate-600' : 'text-slate-400'
        }`}>
          Recent Sessions
        </p>
        
        {sessions.length === 0 && (
          <p className={`text-xs px-2 py-3 ${isDark ? 'text-slate-600' : 'text-slate-400'}`}>No sessions yet.</p>
        )}
        
        {sessions.map((s) => {
          const isActive = activeSession === s.session_id;
          return (
            <div key={s.session_id} className="relative group rounded-xl">
              <button
                onClick={() => onSelectSession(s.session_id)}
                title={s.session_id}
                className={`w-full flex items-start gap-2.5 text-left p-3 pr-8 rounded-xl border transition-all duration-100 ${
                  isActive 
                    ? isDark 
                      ? 'bg-indigo-600/10 text-indigo-300 border-indigo-500/30 shadow-sm shadow-indigo-600/5' 
                      : 'bg-indigo-50/70 text-indigo-600 border-indigo-200/60 shadow-sm'
                    : isDark 
                      ? 'text-slate-300 hover:bg-slate-800/40 hover:text-slate-200 border-transparent' 
                      : 'text-slate-600 hover:bg-slate-100/50 hover:text-slate-900 border-transparent'
                }`}
              >
                <span className={`text-base shrink-0 mt-0.5 ${isActive ? 'text-indigo-500' : 'text-slate-400'}`}>💬</span>
                <div className="flex-1 min-w-0 flex flex-col">
                  <span className={`truncate text-xs font-semibold ${
                    isActive ? isDark ? 'text-white' : 'text-indigo-700' : isDark ? 'text-slate-300' : 'text-slate-700'
                  }`}>
                    {s.label || formatId(s.session_id)}
                  </span>
                  <span className={`truncate text-[10px] mt-0.5 font-normal ${
                    isActive ? isDark ? 'text-indigo-400/80' : 'text-indigo-500' : isDark ? 'text-slate-500' : 'text-slate-400'
                  }`}>
                    {s.last_message || 'No messages yet'}
                  </span>
                </div>
              </button>
              
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setSessionToDelete(s.session_id);
                }}
                title="Delete session"
                className={`absolute right-2 top-1/2 -translate-y-1/2 w-7 h-7 flex items-center justify-center rounded-lg opacity-0 group-hover:opacity-100 transition-all duration-100 ${
                  isDark 
                    ? 'text-slate-500 hover:text-red-400 hover:bg-slate-800' 
                    : 'text-slate-400 hover:text-red-600 hover:bg-slate-200/60'
                }`}
              >
                🗑️
              </button>
            </div>
          );
        })}
      </div>

      {/* Footer Area */}
      <div className={`px-4 py-3.5 border-t transition-colors duration-150 text-[10px] font-medium flex flex-col gap-1 ${
        isDark ? 'border-slate-800/80 bg-[#10121a] text-slate-600' : 'border-slate-100 bg-[#f9fafc] text-slate-400'
      }`}>
        <p>Orchestrator: LangGraph</p>
        <p>LLM Provider: Gemini 2.5</p>
      </div>

      {/* Custom Delete Confirmation Modal */}
      {sessionToDelete && (
        <div 
          onClick={() => setSessionToDelete(null)}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4"
        >
          <div 
            onClick={(e) => e.stopPropagation()}
            className={`w-full max-w-sm rounded-2xl border p-5 shadow-2xl transition-all duration-150 animate-in fade-in zoom-in-95 ${
              isDark ? 'bg-[#1a1d2e] border-slate-700/60' : 'bg-white border-slate-200'
            }`}
          >
            <h3 className={`text-base font-bold mb-2 ${isDark ? 'text-white' : 'text-slate-900'}`}>
              Delete Session
            </h3>
            <p className={`text-xs mb-5 leading-relaxed ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
              Are you sure you want to delete this session? This action will permanently delete the session and all associated chat history.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setSessionToDelete(null)}
                className={`px-4 py-2 text-xs font-semibold rounded-xl border transition-all duration-100 ${
                  isDark 
                    ? 'border-slate-700 text-slate-400 hover:text-slate-200 hover:bg-slate-800' 
                    : 'border-slate-200 text-slate-500 hover:text-slate-800 hover:bg-slate-100'
                }`}
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmDelete}
                className="px-4 py-2 text-xs font-bold rounded-xl bg-red-600 hover:bg-red-500 text-white transition-all duration-100 shadow-md shadow-red-600/10 active:scale-[0.98]"
              >
                Delete Session
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
