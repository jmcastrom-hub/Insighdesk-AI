import React, { useState } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export default function AuthPanel({ session, onSession }) {
  const [open, setOpen] = useState(false);
  const [username, setUsername] = useState('Jose Castro');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('');
    try {
      const response = await fetch(`${API_URL}/auth/login`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || `Error ${response.status}`);
      const next = { token: data.access_token, name: data.nombre, role: data.rol, expires: Date.now() + data.expires_in * 1000 };
      localStorage.setItem('insightdesk-session', JSON.stringify(next));
      onSession(next); setPassword(''); setOpen(false);
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  }

  if (!open) return session
    ? <div className="session-control"><span>{session.name} · {session.role === 'gerente' ? 'Gerente' : 'Vendedor'}</span><button type="button" onClick={() => { localStorage.removeItem('insightdesk-session'); onSession(null); }}>Cerrar sesión</button></div>
    : <button className="login-button" type="button" onClick={() => setOpen(true)}>Iniciar sesión</button>;

  return <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && setOpen(false)}>
    <form className="edit-modal" onSubmit={submit}>
      <div className="modal-heading"><div><span className="modal-kicker">ACCESO AL PANEL</span><h2>Iniciar sesión</h2></div><button type="button" className="icon-button" onClick={() => setOpen(false)} aria-label="Cerrar">×</button></div>
      <label>Nombre de usuario<input autoFocus required value={username} onChange={(event) => setUsername(event.target.value)} /></label>
      <label>Contraseña<input required type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="modal-actions"><button type="button" className="secondary-button" onClick={() => setOpen(false)}>Cancelar</button><button className="primary-button" disabled={busy}>{busy ? 'Validando…' : 'Entrar'}</button></div>
      <p className="auth-hint">El acceso de gerente usa MANAGER_PASSWORD configurada localmente en el backend.</p>
    </form>
  </div>;
}
