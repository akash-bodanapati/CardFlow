import React, { useState, useRef, useEffect } from 'react';
import { apiClient } from '../api/client';
import ConfirmationCard from './ConfirmationCard';

// Retrieve backend URL by stripping /api from the base url
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
const BACKEND_URL = API_BASE_URL.replace(/\/api$/, '');

function ToastContainer({ toasts, onClose }) {
  return (
    <div className="fixed bottom-24 right-6 z-50 flex flex-col gap-2 max-w-sm">
      {toasts.map(t => (
        <div 
          key={t.id}
          className={`flex items-center gap-2 px-4 py-3 rounded-xl shadow-lg border text-sm font-semibold animate-slide-in transition-all duration-200 ${
            t.type === 'error' 
              ? 'bg-red-500/10 border-red-500/30 text-red-400' 
              : t.type === 'warning' 
                ? 'bg-amber-500/10 border-amber-500/30 text-amber-400'
                : t.type === 'info'
                  ? 'bg-sky-500/10 border-sky-500/30 text-sky-400'
                  : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
          }`}
          data-toast-type={t.type}
        >
          <span>{t.type === 'error' ? '❌' : t.type === 'warning' ? '⚠️' : t.type === 'info' ? 'ℹ️' : '✅'}</span>
          <span>{t.text}</span>
          <button onClick={() => onClose(t.id)} className="ml-auto text-xs opacity-50 hover:opacity-100 pl-2">✕</button>
        </div>
      ))}
    </div>
  );
}

function UserBubble({ id, text, timestamp, sessionId, audioUrl }) {
  const isImageUpload = text.includes('Uploaded image:');
  const isAudioUpload = text.includes('Uploaded audio:') || text.includes('Recorded voice note');
  const audioRef = useRef(null);
  const srcUrl = audioUrl || `${BACKEND_URL}/uploads/${sessionId}.wav`;

  useEffect(() => {
    if (isAudioUpload) {
      console.log("[Audio Diagnostic]", {
        audioUrl: srcUrl,
        messageId: id,
        sessionId: sessionId,
        ref: audioRef.current,
        srcFromRef: audioRef.current?.src,
        readyState: audioRef.current?.readyState,
        networkState: audioRef.current?.networkState
      });
    }
  }, [srcUrl, id, sessionId, isAudioUpload]);

  useEffect(() => {
    return () => {
      if (audioUrl && audioUrl.startsWith('blob:')) {
        console.log("[Audio Diagnostic] Revoking Object URL on cleanup:", audioUrl);
        URL.revokeObjectURL(audioUrl);
      }
    };
  }, [audioUrl]);

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="max-w-[70%] bg-indigo-600 text-white px-4 py-2.5 rounded-2xl rounded-tr-sm text-sm leading-relaxed shadow-md shadow-indigo-600/5">
        <div>{text}</div>
        
        {/* Inline thumbnail for card images */}
        {isImageUpload && (
          <div className="mt-2 rounded-lg overflow-hidden border border-indigo-400/30">
            <img 
              src={`${BACKEND_URL}/uploads/${sessionId}_card.png?t=${new Date().getTime()}`} 
              alt="Uploaded card" 
              className="max-w-xs max-h-48 object-contain bg-slate-900/40"
              onError={(e) => {
                // If direct link fails, show a clean fallback icon
                e.target.style.display = 'none';
              }}
            />
          </div>
        )}

        {/* Inline player for voice notes */}
        {isAudioUpload && (
          <div className="mt-2 rounded-lg overflow-hidden border border-indigo-400/20 bg-indigo-700/30 p-1.5">
            <audio 
              ref={audioRef}
              controls 
              src={srcUrl} 
              className="w-full max-w-xs h-8 scale-95" 
            />
          </div>
        )}
      </div>
      <span className="text-[10px] text-slate-500 px-1 font-medium">{timestamp}</span>
    </div>
  );
}

function AgentBubble({ text, isError, timestamp, theme, onRetry }) {
  const isDark = theme === 'dark';
  return (
    <div className="flex justify-start items-start gap-3">
      <div className={`w-8 h-8 shrink-0 rounded-xl border flex items-center justify-center text-sm shadow-sm transition-colors duration-150 ${
        isDark ? 'bg-slate-800 border-slate-700' : 'bg-slate-100 border-slate-200'
      }`}>
        🤖
      </div>
      <div className="flex flex-col gap-1 w-full max-w-[70%]">
        <div className={`px-4 py-2.5 rounded-2xl rounded-tl-sm text-sm leading-relaxed shadow-md transition-colors duration-150 ${
          isError 
            ? 'bg-red-900/10 text-red-400 border border-red-500/20' 
            : isDark 
              ? 'bg-[#1e2130] text-slate-200 border border-slate-800/80' 
              : 'bg-[#f1f5f9] text-slate-800 border border-slate-200/50'
        }`}>
          <div>{text}</div>
          {isError && onRetry && (
            <div className="mt-2.5">
              <button
                onClick={onRetry}
                className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-red-500 hover:bg-red-600 text-white transition-all duration-150 active:scale-[0.98] shadow-sm flex items-center gap-1.5 cursor-pointer"
              >
                <span>🔄</span> Retry
              </button>
            </div>
          )}
        </div>
        <span className="text-[10px] text-slate-500 px-1 font-medium">{timestamp}</span>
      </div>
    </div>
  );
}

function TypingIndicator({ theme }) {
  const isDark = theme === 'dark';
  return (
    <div className="flex justify-start items-start gap-3">
      <div className={`w-8 h-8 shrink-0 rounded-xl border flex items-center justify-center text-sm transition-colors duration-150 ${
        isDark ? 'bg-slate-800 border-slate-700' : 'bg-slate-100 border-slate-200'
      }`}>
        🤖
      </div>
      <div className={`border px-4 py-3 rounded-2xl rounded-tl-sm transition-colors duration-150 ${
        isDark ? 'bg-[#1e2130] border-slate-800/80' : 'bg-[#f1f5f9] border-slate-200/50'
      }`}>
        <div className="flex gap-1 items-center">
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-bounce [animation-delay:0ms]"></span>
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-bounce [animation-delay:150ms]"></span>
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-bounce [animation-delay:300ms]"></span>
        </div>
      </div>
    </div>
  );
}

export default function ChatWindow({ sessionId, theme, toggleTheme }) {
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [awaitingConfirm, setAwaitingConfirm] = useState(false);
  const [rawExtraction, setRawExtraction] = useState(null);
  const [toasts, setToasts] = useState([]);
  const [lastAttempt, setLastAttempt] = useState(null);
  const [loadingSeconds, setLoadingSeconds] = useState(0);
  
  const [recording, setRecording] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  
  const endRef = useRef(null);
  const imageInputRef = useRef(null);
  const audioInputRef = useRef(null);

  useEffect(() => {
    let interval;
    if (loading && messages.length === 0) {
      setLoadingSeconds(0);
      interval = setInterval(() => {
        setLoadingSeconds(prev => prev + 1);
      }, 1000);
    } else {
      setLoadingSeconds(0);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [loading, messages.length]);

  const showToast = (toastText, type = 'success') => {
    console.trace("SHOW_TOAST", toastText, type);
    const id = Date.now() + Math.random().toString();
    setToasts(prev => [...prev, { id, text: toastText, type }]);
    setTimeout(() => {
      removeToast(id);
    }, 4500);
  };

  const removeToast = (id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  };

  const clearAllToasts = () => {
    setToasts([]);
  };

  const dismissToastsByType = (type) => {
    setToasts(prev => prev.filter(t => t.type !== type));
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const localUrl = URL.createObjectURL(audioBlob);
        const fd = new FormData();
        fd.append('audio', audioBlob, 'recorded_voice.webm');
        send(fd, `🎤 Recorded voice note`, localUrl);
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setRecording(true);
      showToast("🎙️ Recording started...", "warning");
    } catch (err) {
      console.error('Failed to start recording', err);
      showToast("Could not access microphone.", "error");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && recording) {
      mediaRecorderRef.current.stop();
      setRecording(false);
    }
  };

  const handleMicClick = () => {
    if (recording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  const getCurrentTimeString = () => {
    return new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  useEffect(() => {
    if (!sessionId) return;
    // Synchronously reset messages and states to avoid flashes and stray indicators
    setMessages([]);
    setAwaitingConfirm(false);
    setRawExtraction(null);
    
    let active = true;
    const loadSession = async () => {
      setLoading(true);
      try {
        const res = await apiClient.getMessages(sessionId);
        if (!active) return;
        if (res.status === 'success' && res.messages && res.messages.length > 0) {
          // Format old messages to have a simulated timestamp
          const formatted = res.messages.map((m, idx) => ({
            ...m,
            id: m.id || `${sessionId}-${idx}-${(m.text || '').slice(0, 10)}`,
            timestamp: m.timestamp || getCurrentTimeString()
          }));
          setMessages(formatted);
          setAwaitingConfirm(res.awaiting_confirmation || false);
          setRawExtraction(res.raw_extraction || null);
        } else {
          setMessages([{
            type: 'agent',
            text: 'Hello! Upload a business card image to get started, or type a message.',
            timestamp: getCurrentTimeString()
          }]);
          setAwaitingConfirm(false);
          setRawExtraction(null);
        }
      } catch (e) {
        console.error(e);
        if (active) {
          setMessages([{
            type: 'agent',
            text: 'Hello! Upload a business card image to get started, or type a message.',
            timestamp: getCurrentTimeString()
          }]);
        }
        showToast("Failed to sync message history.", "error");
      }
      if (active) {
        setLoading(false);
      }
    };
    loadSession();
    return () => {
      active = false;
    };
  }, [sessionId]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, awaitingConfirm, loading]);

  const addUserMsg = (text, audioUrl = null) => setMessages(prev => [...prev, { 
    id: `msg-${Date.now()}-${Math.random()}`, 
    type: 'user', 
    text, 
    timestamp: getCurrentTimeString(),
    audioUrl 
  }]);
  const addAgentMsg = (text, isError = false) => setMessages(prev => [...prev, { 
    id: `msg-${Date.now()}-${Math.random()}`, 
    type: 'agent', 
    text, 
    isError, 
    timestamp: getCurrentTimeString() 
  }]);

  const handleRetry = () => {
    if (!lastAttempt) return;
    if (lastAttempt.type === 'confirm') {
      handleConfirm(lastAttempt.data);
    } else {
      send(lastAttempt.formData, lastAttempt.displayMsg, lastAttempt.audioUrl);
    }
  };

  const triggerResponseToasts = (res) => {
    if (!res) return;
    const details = res.details || {};
    
    console.log("TOAST_DEBUG", {
      action: res.action,
      status: res.status,
      duplicate_found: details.duplicate_found,
      saved_to_sheet: details.saved_to_sheet,
      whatsapp_sent: details.whatsapp_sent
    });
    
    if (details.duplicate_found || res.action === 'duplicate_check') {
      clearAllToasts();
      showToast("Duplicate contact found.", "warning");
      return;
    }
    
    const toast_type = res.status;
    const duplicate_found = details.duplicate_found;
    const saved_to_sheet = details.saved_to_sheet;
    const whatsapp_sent = details.whatsapp_sent;
    const response_payload = res;
    
    if (res.action === 'ocr') {
      if (res.success) {
        console.log("TOAST_DEBUG", {
          toast_type,
          duplicate_found,
          saved_to_sheet,
          whatsapp_sent,
          response_payload
        });
        showToast("⚠️ Verification required!", "warning");
      } else {
        console.log("TOAST_DEBUG", {
          toast_type,
          duplicate_found,
          saved_to_sheet,
          whatsapp_sent,
          response_payload
        });
        showToast(res.message || "OCR failed.", "error");
      }
    } else if (res.action === 'transcription') {
      if (details.transcription_completed) {
        console.log("TOAST_DEBUG", {
          toast_type,
          duplicate_found,
          saved_to_sheet,
          whatsapp_sent,
          response_payload
        });
        showToast("🎙️ Voice note transcribed!", "success");
        console.log("TOAST_DEBUG", {
          toast_type,
          duplicate_found,
          saved_to_sheet,
          whatsapp_sent,
          response_payload
        });
        showToast("📊 Google Sheet updated!", "success");
      } else {
        console.log("TOAST_DEBUG", {
          toast_type,
          duplicate_found,
          saved_to_sheet,
          whatsapp_sent,
          response_payload
        });
        showToast("⚠️ Audio uploaded, transcription failed.", "warning");
      }
    } else if (res.action === 'duplicate_check' || details.duplicate_found) {
      dismissToastsByType('success');
      console.log("TOAST_DEBUG", {
        toast_type,
        duplicate_found,
        saved_to_sheet,
        whatsapp_sent,
        response_payload
      });
      showToast("⚠️ Duplicate contact found", "warning");
    } else if (res.action === 'sheet_write' || details.saved_to_sheet) {
      if (details.saved_to_sheet) {
        console.log("TOAST_DEBUG", {
          toast_type,
          duplicate_found,
          saved_to_sheet,
          whatsapp_sent,
          response_payload
        });
        showToast("📊 Saved to Google Sheets", "success");
      }
      if (details.whatsapp_sent) {
        console.log("TOAST_DEBUG", {
          toast_type,
          duplicate_found,
          saved_to_sheet,
          whatsapp_sent,
          response_payload
        });
        showToast("📱 WhatsApp notification sent", "success");
      } else {
        console.log("TOAST_DEBUG", {
          toast_type,
          duplicate_found,
          saved_to_sheet,
          whatsapp_sent,
          response_payload
        });
        showToast("⚠️ WhatsApp failed to send", "warning");
      }
    }
  };

  const send = async (formData, displayMsg, audioUrl = null) => {
    if (loading) return;
    clearAllToasts();
    setLastAttempt({ type: 'send', formData, displayMsg, audioUrl });
    addUserMsg(displayMsg, audioUrl);
    setLoading(true);
    try {
      const res = await apiClient.sendMessage(sessionId, formData);
      if (res && res.status) {
        if (res.awaiting_confirmation) {
          setAwaitingConfirm(true);
          setRawExtraction(res.raw_extraction);
        }
        addAgentMsg(res.message || 'Processed successfully.', res.status === 'error');
        triggerResponseToasts(res);
      } else {
        addAgentMsg('Something went wrong. Please try again in a moment.', true);
        showToast("Something went wrong.", "error");
      }
    } catch (e) {
      console.error(e);
      addAgentMsg('Something went wrong. Please try again in a moment.', true);
      showToast("Something went wrong.", "error");
    }
    setLoading(false);
  };

  const handleSendText = () => {
    if (!text.trim()) return;
    const fd = new FormData();
    fd.append('text', text);
    send(fd, text);
    setText('');
  };

  const handleFileUpload = (e, type) => {
    const file = e.target.files[0];
    if (!file) return;
    const fd = new FormData();
    fd.append(type, file);
    const localUrl = type === 'audio' ? URL.createObjectURL(file) : null;
    send(fd, `📎 Uploaded ${type}: ${file.name}`, localUrl);
    e.target.value = '';
  };

  const handleConfirm = async (confirmedData) => {
    if (loading) return;
    clearAllToasts();
    setAwaitingConfirm(false);
    setLoading(true);
    setLastAttempt({ type: 'confirm', data: confirmedData });
    try {
      const res = await apiClient.confirmExtraction(sessionId, confirmedData);
      addUserMsg(`✓ Confirmed: ${confirmedData.name} (${confirmedData.company})`);
      
      if (res && res.status) {
        addAgentMsg(res.message || '✅ Contact saved successfully.', res.status === 'error');
        triggerResponseToasts(res);
      } else {
        addAgentMsg('Something went wrong. Please try again in a moment.', true);
        showToast("Something went wrong.", "error");
      }
    } catch (e) {
      console.error(e);
      addAgentMsg('Something went wrong. Please try again in a moment.', true);
      showToast("Something went wrong.", "error");
    }
    setLoading(false);
  };

  const handleDiscard = () => {
    setAwaitingConfirm(false);
    setRawExtraction(null);
    addAgentMsg('Card discarded. Upload another card or send a message.');
    showToast("Card discarded.", "warning");
  };

  const shortId = sessionId ? sessionId.slice(0, 8) + '…' : '';
  const isDark = theme === 'dark';

  return (
    <div className={`flex-1 flex flex-col h-screen overflow-hidden transition-colors duration-150 ${
      isDark ? 'bg-[#0f1117]' : 'bg-[#f8fafc]'
    }`}>
      {/* Header */}
      <div className={`shrink-0 px-6 py-4 border-b flex items-center justify-between transition-colors duration-150 ${
        isDark ? 'bg-[#13151f] border-slate-800/80' : 'bg-white border-slate-200'
      }`}>
        <div className="flex items-center gap-3">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)] animate-pulse"></div>
          <h2 className={`text-sm font-bold ${isDark ? 'text-slate-200' : 'text-slate-800'}`}>
            Digitization Chat
          </h2>
        </div>

        <div className="flex items-center gap-4">
          <span className={`font-mono text-xs select-all ${isDark ? 'text-slate-600' : 'text-slate-400'}`} title={sessionId}>
            {shortId}
          </span>
          <button 
            onClick={toggleTheme}
            className={`p-2 rounded-lg border transition-all duration-150 ${
              isDark 
                ? 'border-slate-800 bg-slate-900 text-amber-400 hover:bg-slate-800' 
                : 'border-slate-200 bg-slate-50 text-indigo-600 hover:bg-slate-100 shadow-sm'
            }`}
            title="Toggle theme"
          >
            {isDark ? '☀️' : '🌙'}
          </button>
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
        {loading && messages.length === 0 ? (() => {
          let loadingTitle = "Loading your workspace...";
          let loadingSubtitle = "Connecting securely to CardFlow services.";

          if (loadingSeconds > 45) {
            loadingTitle = "Still waking up backend services...";
            loadingSubtitle = "Almost there.";
          } else if (loadingSeconds > 15) {
            loadingTitle = "Starting backend services...";
            loadingSubtitle = "This can take a few moments on free hosting.";
          }

          return (
            <div className="flex flex-col items-center justify-center py-24 text-center space-y-4 animate-fade-in">
              <div className="w-9 h-9 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
              <div className="space-y-1">
                <p className={`text-sm font-bold ${isDark ? 'text-slate-400' : 'text-slate-700'}`}>{loadingTitle}</p>
                <p className={`text-xs max-w-xs ${isDark ? 'text-slate-600' : 'text-slate-500'}`}>
                  {loadingSubtitle}
                </p>
              </div>
            </div>
          );
        })() : (
          <>
            {messages.map((m, i) =>
              m.type === 'user'
                ? <UserBubble key={m.id || i} id={m.id || `user-msg-${i}`} text={m.text} timestamp={m.timestamp} sessionId={sessionId} audioUrl={m.audioUrl} />
                : <AgentBubble key={m.id || i} id={m.id || `agent-msg-${i}`} text={m.text} isError={m.isError} timestamp={m.timestamp} theme={theme} onRetry={i === messages.length - 1 ? handleRetry : undefined} />
            )}
            
            {loading && <TypingIndicator theme={theme} />}
          </>
        )}
        
        {awaitingConfirm && !loading && (
          <div className="flex justify-start pl-11">
            <ConfirmationCard 
              data={rawExtraction} 
              onConfirm={handleConfirm}
              onDiscard={handleDiscard}
              theme={theme}
            />
          </div>
        )}

        <div ref={endRef} />
      </div>

      {/* Input Bar */}
      <div className={`shrink-0 px-5 py-4 border-t transition-colors duration-150 ${
        isDark ? 'bg-[#13151f] border-slate-800/80' : 'bg-white border-slate-200'
      }`}>
        <div className={`flex items-center gap-2 border rounded-2xl px-3 py-2.5 focus-within:ring-2 focus-within:ring-indigo-500/20 transition-all duration-150 ${
          isDark 
            ? 'bg-[#1e2130] border-slate-800 focus-within:border-indigo-500' 
            : 'bg-slate-50 border-slate-200 focus-within:border-indigo-500 focus-within:bg-white'
        }`}>
          {/* Upload buttons */}
          <button
            onClick={() => imageInputRef.current?.click()}
            className={`shrink-0 w-8 h-8 flex items-center justify-center rounded-lg transition-colors duration-150 ${
              isDark ? 'text-slate-400 hover:text-indigo-400 hover:bg-slate-800' : 'text-slate-500 hover:text-indigo-600 hover:bg-slate-200/50'
            }`}
            title="Upload visiting card image"
          >
            📷
          </button>
          <input
            ref={imageInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => handleFileUpload(e, 'image')}
          />

          <button
            onClick={handleMicClick}
            className={`shrink-0 w-8 h-8 flex items-center justify-center rounded-lg transition-all duration-150 ${
              recording 
                ? 'bg-red-500 text-white animate-pulse shadow-md shadow-red-500/20' 
                : isDark ? 'text-slate-400 hover:text-indigo-400 hover:bg-slate-800' : 'text-slate-500 hover:text-indigo-600 hover:bg-slate-200/50'
            }`}
            title={recording ? "Stop recording" : "Record voice note"}
          >
            🎤
          </button>
          
          <button
            onClick={() => audioInputRef.current?.click()}
            className={`shrink-0 w-8 h-8 flex items-center justify-center rounded-lg transition-colors duration-150 ${
              isDark ? 'text-slate-400 hover:text-indigo-400 hover:bg-slate-800' : 'text-slate-500 hover:text-indigo-600 hover:bg-slate-200/50'
            }`}
            title="Upload audio file"
          >
            📎
          </button>
          <input
            ref={audioInputRef}
            type="file"
            accept="audio/*"
            className="hidden"
            onChange={(e) => handleFileUpload(e, 'audio')}
          />

          <div className={`w-px h-5 mx-1 shrink-0 ${isDark ? 'bg-slate-800' : 'bg-slate-200'}`}></div>

          {/* Text input */}
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSendText()}
            placeholder="Type a follow-up message…"
            disabled={loading}
            className={`flex-1 bg-transparent text-sm outline-none min-w-0 py-1 transition-colors duration-150 ${
              isDark ? 'text-slate-200 placeholder-slate-600' : 'text-slate-800 placeholder-slate-400'
            }`}
          />

          {/* Send button */}
          <button
            onClick={handleSendText}
            disabled={!text.trim() || loading}
            className="shrink-0 w-8 h-8 flex items-center justify-center rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-30 disabled:cursor-not-allowed text-white transition-all duration-150 shadow-md shadow-indigo-600/10 active:scale-[0.98]"
            title="Send"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4.5 h-4.5">
              <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
            </svg>
          </button>
        </div>
        <p className={`text-center text-[10px] mt-2 transition-colors duration-150 ${
          isDark ? 'text-slate-700' : 'text-slate-400'
        }`}>
          Enter to send · 📷 to upload card · 🎤 to record voice note
        </p>
      </div>

      {/* Toast Notifications */}
      <ToastContainer toasts={toasts} onClose={removeToast} />
    </div>
  );
}
