import React, { useCallback, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import Management from './Management.jsx';
import ChatWidget from './ChatWidget.jsx';
import AuthPanel from './AuthPanel.jsx';
import './management.css';
import {
  Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts';
import './styles.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const COLORS = ['#2563eb', '#60a5fa', '#1d4ed8', '#93c5fd', '#3b82f6', '#bfdbfe'];
const currency = new Intl.NumberFormat('es-CR', {
  style: 'currency', currency: 'CRC', maximumFractionDigits: 0,
});
const number = new Intl.NumberFormat('es-CR');

function formatMoney(value) {
  return currency.format(Number(value) || 0);
}

function MetricCard({ label, value, caption, icon, accent }) {
  return (
    <article className={`metric-card ${accent}`}>
      <div className="metric-top"><span>{label}</span><span className="metric-icon">{icon}</span></div>
      <strong className="metric-value">{value}</strong>
      <span className="metric-caption">{caption}</span>
    </article>
  );
}

function ChartToggle({ value, onChange, label }) {
  return <div className="chart-toggle" role="group" aria-label={`Tipo de gráfico: ${label}`}>
    <button type="button" aria-pressed={value === 'bar'} className={value === 'bar' ? 'selected' : ''} onClick={() => onChange('bar')}>Barras</button>
    <button type="button" aria-pressed={value === 'pie'} className={value === 'pie' ? 'selected' : ''} onClick={() => onChange('pie')}>Pastel</button>
  </div>;
}

function App() {
  const [section, setSection] = useState('resumen');
  const [data, setData] = useState(null);
  const [sellerMetrics, setSellerMetrics] = useState([]);
  const [sellerLoadError, setSellerLoadError] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [session, setSession] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem('insightdesk-session'));
      return saved?.expires > Date.now() ? saved : null;
    } catch { return null; }
  });
  const [categoryChart, setCategoryChart] = useState('bar');
  const [distributionChart, setDistributionChart] = useState('pie');

  const loadIndicators = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [response, sellersResponse] = await Promise.all([
        fetch(`${API_URL}/indicadores`),
        fetch(`${API_URL}/vendedores/indicadores`),
      ]);
      if (!response.ok) throw new Error(`La API respondió con estado ${response.status}.`);
      const indicators = await response.json();
      if (!Array.isArray(indicators.ventas_por_categoria)) {
        throw new Error('La respuesta de indicadores no tiene el formato esperado.');
      }
      setData(indicators);
      if (sellersResponse.ok) {
        setSellerMetrics(await sellersResponse.json());
        setSellerLoadError('');
      } else {
        setSellerMetrics([]);
        setSellerLoadError(`No se pudo cargar el equipo (${sellersResponse.status}).`);
      }
    } catch (requestError) {
      setError(`${requestError.message} Comprueba que FastAPI esté activo en ${API_URL}.`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadIndicators(); }, [loadIndicators]);
  useEffect(() => {
    if (!session?.token) return;
    fetch(`${API_URL}/auth/me`, { headers: { Authorization: `Bearer ${session.token}` } }).then((response) => {
      if (!response.ok) { localStorage.removeItem('insightdesk-session'); setSession(null); }
    }).catch(() => {});
  }, [session?.token]);

  const categories = (data?.ventas_por_categoria ?? []).map((item) => ({ ...item, ingresos: Number(item.ingresos) || 0, numero_ventas: Number(item.numero_ventas) || 0 }));
  const totalTransactions = categories.reduce((sum, item) => sum + Number(item.numero_ventas || 0), 0);
  const totalRevenue = categories.reduce((sum, item) => sum + Number(item.ingresos || 0), 0);
  const chartData = categories.filter((item) => item.ingresos > 0);
  const rankedSellers = sellerMetrics
    .filter((seller) => seller.vendedor_id !== null && Number(seller.ventas) > 0)
    .sort((a, b) => Number(b.ingresos) - Number(a.ingresos))
    .slice(0, 6);
  const topSellerRevenue = Math.max(1, ...rankedSellers.map((seller) => Number(seller.ingresos) || 0));

  return (
    <main className="dashboard-shell">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="Insightdesk inicio">
          <span className="brand-mark">I</span><span>insightdesk<span className="brand-ai">.ai</span></span>
        </a>
        <div className="side-section-label">ESPACIO DE TRABAJO</div>
        <button className={`nav-item ${section === 'resumen' ? 'active' : ''}`} onClick={() => setSection('resumen')}><span className="nav-icon">▦</span> Resumen de ventas</button>
        <button className={`nav-item ${section === 'productos' ? 'active' : ''}`} onClick={() => setSection('productos')}><span className="nav-icon">◇</span> Productos</button>
        <button className={`nav-item ${section === 'ventas' ? 'active' : ''}`} onClick={() => setSection('ventas')}><span className="nav-icon">↗</span> Ventas</button>
        <button className={`nav-item ${section === 'inventario' ? 'active' : ''}`} onClick={() => setSection('inventario')}><span className="nav-icon">▣</span> Inventario</button>
        <button className={`nav-item ${section === 'vendedores' ? 'active' : ''}`} onClick={() => setSection('vendedores')}><span className="nav-icon">♙</span> Vendedores</button>
        <button className={`nav-item ${section === 'solicitudes' ? 'active' : ''}`} onClick={() => setSection('solicitudes')}><span className="nav-icon">◷</span> Aprobaciones</button>
        <button className={`nav-item ${section === 'auditoria' ? 'active' : ''}`} onClick={() => setSection('auditoria')}><span className="nav-icon">≡</span> Registro de acciones</button>
        <div className="sidebar-bottom"><span className="connection-dot" /> Panel conectado</div>
      </aside>

      <section className="main-area" id="resumen">
        <header className="topbar">
          <div className="breadcrumb">Panel <span>/</span> <strong>{section === 'resumen' ? 'Resumen de ventas' : section === 'solicitudes' ? 'Aprobaciones' : section === 'auditoria' ? 'Registro de acciones' : section[0].toUpperCase() + section.slice(1)}</strong></div>
          <div className="topbar-right"><span className="phase-tag"><span className="status-dot" /> Datos de ventas</span><AuthPanel session={session} onSession={setSession} /><div className="avatar">ID</div></div>
        </header>

        <div className="content">
          <div className="page-heading">
            <div><p className="eyebrow">INTELIGENCIA PARA TU NEGOCIO</p><h1>{section === 'resumen' ? 'Resumen de ventas' : section === 'productos' ? 'Catálogo de productos' : section === 'ventas' ? 'Registro de ventas' : section === 'solicitudes' ? 'Aprobaciones' : section === 'auditoria' ? 'Registro de acciones' : section[0].toUpperCase() + section.slice(1)}</h1><p className="intro">{section === 'resumen' ? 'Una vista clara del rendimiento de tu negocio.' : section === 'solicitudes' ? 'Sigue el estado de solicitudes y decisiones de gerencia.' : section === 'auditoria' ? 'Consulta las operaciones registradas por vendedor y gerencia.' : 'Administra las operaciones de tu negocio con trazabilidad.'}</p></div>
            {section === 'resumen' && <button className="refresh-button" onClick={loadIndicators} disabled={loading}>
              <span className={loading ? 'refresh-icon spinning' : 'refresh-icon'}>↻</span>
              {loading ? 'Actualizando' : 'Actualizar'}
            </button>}
          </div>

          {section === 'resumen' && error && <div className="error-banner" role="alert"><span>!</span><div><strong>No se pudieron cargar los indicadores</strong><p>{error}</p></div><button onClick={loadIndicators}>Reintentar</button></div>}

          {section !== 'resumen' ? <Management section={section} onDataChange={loadIndicators} session={session} /> : <>
          <section className="welcome-banner">
            <div className="welcome-copy"><span className="welcome-kicker"><span className="welcome-pulse" /> TU RESUMEN DE NEGOCIO</span><h2>Las ventas, en perspectiva.</h2><p>Indicadores actualizados desde tus registros, con el rendimiento del equipo a un vistazo.</p></div>
            <div className="welcome-highlight"><span>Transacciones registradas</span><strong>{data ? number.format(totalTransactions) : '—'}</strong><button type="button" onClick={() => setSection('vendedores')}>Ver equipo <span aria-hidden="true">→</span></button></div>
            <div className="welcome-orb welcome-orb-one" /><div className="welcome-orb welcome-orb-two" />
          </section>
          <div className="metrics-grid" aria-live="polite">
            <MetricCard label="Ingresos netos" value={data ? formatMoney(data.ingresos_totales) : '—'} caption={data ? `Brutos ${formatMoney(data.ingresos_brutos)} · ajustes ${formatMoney(data.ajustes_aprobados)}` : 'Ventas menos ajustes aprobados'} icon="$" accent="mint" />
            <MetricCard label="Cantidad vendida" value={data ? number.format(data.cantidad_total_vendida) : '—'} caption="Unidades en ventas registradas" icon="↗" accent="blue" />
            <MetricCard label="Ticket promedio" value={data ? formatMoney(data.ticket_promedio) : '—'} caption="Ingreso promedio por venta" icon="⌁" accent="sand" />
            <MetricCard label="Transacciones" value={data ? number.format(totalTransactions) : '—'} caption="Ventas registradas" icon="▤" accent="lavender" />
          </div>

          <div className="charts-grid">
            <section className="chart-card category-chart">
              <div className="chart-heading"><div><h2>Ingresos por categoría</h2><p>Ventas menos devoluciones y notas aprobadas</p></div><div className="chart-actions"><span className="chart-badge">CRC</span><ChartToggle label="ingresos por categoría" value={categoryChart} onChange={setCategoryChart} /></div></div>
              {loading && !data ? <div className="chart-state">Cargando indicadores…</div> : categories.length === 0 ? <div className="chart-state">Aún no hay ventas para mostrar.</div> : (
                <div className="chart-body"><ResponsiveContainer width="100%" height="100%">{categoryChart === 'bar' ? <BarChart data={categories} margin={{ top: 10, right: 12, left: 4, bottom: 4 }}>
                  <CartesianGrid stroke="#edf1f2" vertical={false} />
                  <XAxis dataKey="categoria" axisLine={false} tickLine={false} tick={{ fill: '#869397', fontSize: 11 }} tickMargin={12} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: '#9aa5a7', fontSize: 10 }} tickFormatter={(value) => `${number.format(value / 1000)}k`} width={42} />
                  <Tooltip formatter={(value) => [formatMoney(value), 'Ingresos']} contentStyle={{ border: '1px solid #e9eeee', borderRadius: 10, boxShadow: '0 8px 24px #1c3e3a12' }} />
                  <Bar dataKey="ingresos" fill="#2563eb" radius={[6, 6, 0, 0]} maxBarSize={54} />
                </BarChart> : <PieChart><Tooltip formatter={(value) => [formatMoney(value), 'Ingresos']} /><Pie data={chartData} dataKey="ingresos" nameKey="categoria" cx="50%" cy="50%" innerRadius="38%" outerRadius="68%" paddingAngle={3} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>{chartData.map((item, index) => <Cell key={item.categoria} fill={COLORS[index % COLORS.length]} />)}</Pie></PieChart>}</ResponsiveContainer></div>
              )}
            </section>

            <section className="chart-card distribution-chart">
              <div className="chart-heading"><div><h2>Participación de ingresos</h2><p>Proporción del ingreso neto</p></div><ChartToggle label="ingresos por categoría" value={distributionChart} onChange={setDistributionChart} /></div>
              {loading && !data ? <div className="chart-state">Cargando indicadores…</div> : categories.length === 0 ? <div className="chart-state">Aún no hay ventas para mostrar.</div> : (
                distributionChart === 'pie' ? <div className="donut-layout"><div className="donut-wrap"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={chartData} dataKey="ingresos" nameKey="categoria" cx="50%" cy="50%" innerRadius="62%" outerRadius="92%" paddingAngle={3}>{chartData.map((item, index) => <Cell key={item.categoria} fill={COLORS[index % COLORS.length]} />)}</Pie></PieChart></ResponsiveContainer><div className="donut-total"><strong>{chartData.length}</strong><span>categorías</span></div></div>
                  <div className="legend">{categories.map((item, index) => <div className="legend-row" key={item.categoria}><span className="legend-dot" style={{ background: COLORS[index % COLORS.length] }} /><span className="legend-name">{item.categoria}</span><strong>{totalRevenue ? Math.round(Number(item.ingresos) / totalRevenue * 100) : 0}%</strong></div>)}</div></div>
                : <div className="chart-body distribution-bars"><ResponsiveContainer width="100%" height="100%"><BarChart data={categories} margin={{ top: 10, right: 12, left: 4, bottom: 4 }}><CartesianGrid stroke="#edf1f2" vertical={false} /><XAxis dataKey="categoria" axisLine={false} tickLine={false} tick={{ fill: '#869397', fontSize: 10 }} /><YAxis axisLine={false} tickLine={false} tick={{ fill: '#9aa5a7', fontSize: 10 }} tickFormatter={(value) => `${number.format(value / 1000)}k`} width={42} /><Tooltip formatter={(value) => [formatMoney(value), 'Ingresos']} /><Bar dataKey="ingresos" radius={[6, 6, 0, 0]} maxBarSize={48}>{categories.map((item, index) => <Cell key={item.categoria} fill={COLORS[index % COLORS.length]} />)}</Bar></BarChart></ResponsiveContainer></div>
              )}
            </section>
          </div>

          <section className="team-card">
            <div className="team-heading"><div><p className="eyebrow">EL EQUIPO</p><h2>Rendimiento por vendedor</h2><p>Ventas atribuidas a cada cuenta. Las 50 ventas originales del seed siguen sin asignar.</p></div><button type="button" onClick={() => setSection('vendedores')}>Ver métricas <span aria-hidden="true">→</span></button></div>
            {sellerLoadError ? <div className="team-empty" role="status">{sellerLoadError}</div> : rankedSellers.length ? <div className="seller-ranking">{rankedSellers.map((seller, index) => <div className="seller-rank-row" key={seller.vendedor_id} style={{ '--rank-index': index }}><span className={`seller-rank-number ${index === 0 ? 'rank-first' : ''}`}>{String(index + 1).padStart(2, '0')}</span><span className="seller-rank-avatar">{seller.vendedor.split(' ').map((part) => part[0]).slice(0, 2).join('').toUpperCase()}</span><div className="seller-rank-info"><div className="seller-rank-label"><strong>{seller.vendedor}</strong><span>{number.format(Number(seller.ventas))} ventas · {number.format(Number(seller.unidades))} unidades</span></div><div className="seller-progress"><span style={{ width: `${Math.max(4, (Number(seller.ingresos) / topSellerRevenue) * 100)}%` }} /></div></div><strong className="seller-rank-revenue">{formatMoney(seller.ingresos)}</strong></div>)}</div> : <div className="team-empty">{loading ? 'Cargando equipo…' : 'Todavía no hay ventas atribuidas a vendedores.'}</div>}
            <div className="demo-data-note"><span>i</span>Los perfiles y ventas de muestra son ficticios; verifica los datos antes del uso operativo.</div>
          </section>

          <div className="data-note"><span className="note-icon">i</span><span>Los indicadores incluyen todas las ventas persistidas en la base de datos.</span><span className="updated-label">Insightdesk · Panel de ventas</span></div>
          </>}
        </div>
      </section>
      <ChatWidget />
    </main>
  );
}

createRoot(document.getElementById('root')).render(<App />);
