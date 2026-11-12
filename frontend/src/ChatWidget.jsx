import React, { useEffect, useRef, useState } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const listRef = useRef(null);
  useEffect(() => { listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' }); }, [messages, busy, open]);

  async function send(text = draft) {
    const content = text.trim();
    if (!content || busy) return;
    const conversation = [...messages, { role: 'user', content }];
    setMessages(conversation); setDraft(''); setError(''); setBusy(true);
    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: conversation.slice(-12) }),
        signal: AbortSignal.timeout(30000),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || `Error ${response.status}`);
      setMessages([...conversation, { role: 'assistant', content: result.reply }]);
    } catch (err) {
      setError(err.name === 'TimeoutError' ? 'El asistente está tardando más de lo esperado. Inténtalo de nuevo.' : err.message);
    } finally { setBusy(false); }
  }

  return <>
    {open && <section className="chat-panel" aria-label="Chat de Insightdesk">
      <header className="chat-header"><div className="chat-avatar">✦</div><div className="chat-title"><strong>Insightdesk AI</strong><span><i /> Analista de ventas</span></div><button className="chat-close" onClick={() => setOpen(false)} aria-label="Cerrar chat">×</button></header>
      <div className="chat-messages" ref={listRef} aria-live="polite">
        {!messages.length && <div className="chat-welcome"><div className="welcome-spark">✦</div><h3>Hola, ¿qué quieres descubrir?</h3><p>Pregúntame por tus ventas. Responderé usando los datos registrados en tu negocio.</p><div className="chat-suggestions"><button onClick={() => send('¿Qué categoría genera más ingresos?')}>¿Qué categoría vende más?</button><button onClick={() => send('Resume el rendimiento de ventas actual.')}>Resume mis ventas</button></div></div>}
        {messages.map((message, index) => <div className={`chat-message ${message.role}`} key={`${index}-${message.role}`}><span>{message.content}</span></div>)}
        {busy && <div className="chat-message assistant"><span className="typing-dots"><i /><i /><i /></span></div>}
        {error && <div className="chat-error" role="alert">{error}</div>}
      </div>
      <form className="chat-composer" onSubmit={(event) => { event.preventDefault(); send(); }}><textarea value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Pregunta sobre tus ventas…" rows="1" maxLength="3000" onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); send(); } }} /><button disabled={busy || !draft.trim()} aria-label="Enviar mensaje">↑</button></form>
      <div className="chat-footnote">Respuestas basadas en los datos actuales de ventas</div>
    </section>}
    <button className={`chat-launcher ${open ? 'chat-launcher-open' : ''}`} onClick={() => setOpen(!open)} aria-label={open ? 'Cerrar chat' : 'Abrir chat con Insightdesk AI'}>{open ? '×' : <><span>✦</span><b>Preguntar a AI</b></>}</button>
  </>;
}
