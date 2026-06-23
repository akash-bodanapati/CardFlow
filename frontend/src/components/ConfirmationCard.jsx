import React, { useState, useEffect } from 'react';

export default function ConfirmationCard({ data, onConfirm, onDiscard, theme }) {
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    email: '',
    company: '',
  });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (data) {
      setFormData({
        name: data.name || '',
        phone: data.phone || '',
        email: data.email || '',
        company: data.company || '',
      });
    }
  }, [data]);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleConfirmClick = () => {
    if (submitting) return;
    setSubmitting(true);
    onConfirm(formData);
  };

  const fields = [
    { name: 'name',    label: 'Full Name',    icon: '👤', placeholder: 'Jane Doe' },
    { name: 'phone',   label: 'Phone',         icon: '📞', placeholder: '+1 555 0199' },
    { name: 'email',   label: 'Email',         icon: '✉️',  placeholder: 'jane@company.com' },
    { name: 'company', label: 'Company',       icon: '🏢', placeholder: 'Acme Corp' },
  ];

  const isDark = theme === 'dark';

  return (
    <div className={`w-80 border rounded-2xl shadow-xl overflow-hidden transition-all duration-150 ${
      isDark ? 'bg-[#1a1d2e] border-slate-700/60' : 'bg-white border-slate-200'
    }`}>
      {/* ... */}
      <div className={`bg-gradient-to-r border-b px-5 py-4 ${
        isDark 
          ? 'from-indigo-950/40 to-purple-950/40 border-slate-700/60' 
          : 'from-indigo-50/50 to-purple-50/50 border-slate-200/60'
      }`}>
        <div className="flex items-center gap-2.5">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-base border ${
            isDark ? 'bg-indigo-500/10 border-indigo-500/30' : 'bg-indigo-50 border-indigo-200'
          }`}>
            📋
          </div>
          <div>
            <h3 className={`text-sm font-bold leading-tight ${isDark ? 'text-white' : 'text-slate-900'}`}>
              Review Contact Info
            </h3>
            <p className={`text-[10px] mt-0.5 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
              Gemini extracted the fields below — edit if needed
            </p>
          </div>
        </div>
      </div>

      {/* Form Fields */}
      <div className="px-5 py-4 space-y-3.5">
        {fields.map(({ name, label, icon, placeholder }) => (
          <div key={name}>
            <label className={`flex items-center gap-1.5 text-xs font-semibold mb-1.5 ${
              isDark ? 'text-slate-400' : 'text-slate-500'
            }`}>
              <span>{icon}</span>
              {label}
            </label>
            <input
              type="text"
              name={name}
              value={formData[name]}
              onChange={handleChange}
              placeholder={placeholder}
              disabled={submitting}
              className={`w-full border rounded-xl px-3 py-2 text-sm outline-none transition-all duration-150 ${
                isDark 
                  ? 'bg-[#12141f] border-slate-700 text-slate-100 placeholder-slate-600 focus:border-indigo-500' 
                  : 'bg-slate-50 border-slate-200 text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:bg-white'
              } ${submitting ? 'opacity-65 cursor-not-allowed' : ''}`}
            />
          </div>
        ))}
      </div>

      {/* Action Buttons */}
      <div className="px-5 py-4 pt-0 flex gap-2">
        <button
          onClick={onDiscard}
          disabled={submitting}
          className={`flex-1 px-3 py-2 text-sm font-semibold rounded-xl border transition-all duration-150 ${
            isDark 
              ? 'border-slate-700 text-slate-400 hover:text-slate-200 hover:bg-slate-800/60' 
              : 'border-slate-200 text-slate-500 hover:text-slate-800 hover:bg-slate-100'
          } ${submitting ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          Discard
        </button>
        <button
          onClick={handleConfirmClick}
          disabled={submitting}
          className={`flex-1 px-3 py-2 text-sm font-bold rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white transition-all duration-150 shadow-md shadow-indigo-600/10 active:scale-[0.98] ${
            submitting ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        >
          {submitting ? 'Saving...' : '✓ Confirm & Save'}
        </button>
      </div>
    </div>
  );
}
