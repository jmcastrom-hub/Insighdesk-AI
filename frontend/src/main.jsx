import React, { useCallback, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import Management from './Management.jsx';
import ChatWidget from './ChatWidget.jsx';
import './management.css';
import {
  Bar, BarChart, CartesianGrid, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts';
import './styles.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const COLORS = ['#287b70', '#6eaa96', '#d39b57', '#8093b1', '#c27864', '#a3b765'];
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

function App() {
  const [section, setSection] = useState('resumen');
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const loadIndicators = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${API_URL}/indicadores`);
      if (!response.ok) throw new Error(`La API respondió con estado ${response.status}.`);
      const indicators = await response.json();
      if (!Array.isArray(indicators.ventas_por_categoria)) {
        throw new Error('La respuesta de indicadores no tiene el formato esperado.');
      }
      setData(indicators);
    } catch (requestError) {
      setError(`${requestError.message} Comprueba que FastAPI esté activo en ${API_URL}.`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadIndicators(); }, [loadIndicators]);

  const categories = data?.ventas_por_categoria ?? [];
  const totalTransactions = categories.reduce((sum, item) => sum + Number(item.numero_ventas || 0), 0);
  const totalRevenue = categories.reduce((sum, item) => sum + Number(item.ingresos || 0), 0);
  let categoryOffset = 0;
  const categoryStops = categories.map((item, index) => {
    const start = categoryOffset;
    const share = totalRevenue ? Number(item.ingresos) / totalRevenue * 100 : 0;
    categoryOffset += share;
    return `${COLORS[index % COLORS.length]} ${start}% ${categoryOffset}%`;
  });
  const donutBackground = categoryStops.length
    ? `conic-gradient(${categoryStops.join(', ')})`
    : '#edf1f2';

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
        <div className="sidebar-bottom"><span className="connection-dot" /> Panel conectado</div>
      </aside>

      <section className="main-area" id="resumen">
        <header className="topbar">
          <div className="breadcrumb">Panel <span>/</span> <strong>{section === 'resumen' ? 'Resumen de ventas' : section[0].toUpperCase() + section.slice(1)}</strong></div>
          <div className="topbar-right"><span className="phase-tag"><span className="status-dot" /> Datos de ventas</span><div className="avatar">ID</div></div>
        </header>

        <div className="content">
          <div className="page-heading">
            <div><p className="eyebrow">INTELIGENCIA PARA TU NEGOCIO</p><h1>{section === 'resumen' ? 'Resumen de ventas' : section === 'productos' ? 'Catálogo de productos' : 'Registro de ventas'}</h1><p className="intro">{section === 'resumen' ? 'Una vista clara del rendimiento de tu negocio.' : section === 'productos' ? 'Mantén al día los productos, categorías y precios.' : 'Registra y actualiza las operaciones de tu negocio.'}</p></div>
            {section === 'resumen' && <button className="refresh-button" onClick={loadIndicators} disabled={loading}>
              <span className={loading ? 'refresh-icon spinning' : 'refresh-icon'}>↻</span>
              {loading ? 'Actualizando' : 'Actualizar'}
            </button>}
          </div>

          {section === 'resumen' && error && <div className="error-banner" role="alert"><span>!</span><div><strong>No se pudieron cargar los indicadores</strong><p>{error}</p></div><button onClick={loadIndicators}>Reintentar</button></div>}

          {section !== 'resumen' ? <Management section={section} onDataChange={loadIndicators} /> : <>
          <div className="metrics-grid" aria-live="polite">
            <MetricCard label="Ingresos totales" value={data ? formatMoney(data.ingresos_totales) : '—'} caption="Ventas brutas acumuladas" icon="$" accent="mint" />
            <MetricCard label="Cantidad vendida" value={data ? number.format(data.cantidad_total_vendida) : '—'} caption="Unidades en ventas registradas" icon="↗" accent="blue" />
            <MetricCard label="Ticket promedio" value={data ? formatMoney(data.ticket_promedio) : '—'} caption="Ingreso promedio por venta" icon="⌁" accent="sand" />
            <MetricCard label="Transacciones" value={data ? number.format(totalTransactions) : '—'} caption="Ventas registradas" icon="▤" accent="lavender" />
          </div>

          <div className="charts-grid">
            <section className="chart-card category-chart">
              <div className="chart-heading"><div><h2>Ingresos por categoría</h2><p>Distribución de ventas brutas</p></div><span className="chart-badge">CRC</span></div>
              {loading && !data ? <div className="chart-state">Cargando indicadores…</div> : categories.length === 0 ? <div className="chart-state">Aún no hay ventas para mostrar.</div> : (
                <div className="chart-body"><ResponsiveContainer width="100%" height="100%"><BarChart data={categories} margin={{ top: 10, right: 12, left: 4, bottom: 4 }}>
                  <CartesianGrid stroke="#edf1f2" vertical={false} />
                  <XAxis dataKey="categoria" axisLine={false} tickLine={false} tick={{ fill: '#869397', fontSize: 11 }} tickMargin={12} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: '#9aa5a7', fontSize: 10 }} tickFormatter={(value) => `${number.format(value / 1000)}k`} width={42} />
                  <Tooltip formatter={(value) => [formatMoney(value), 'Ingresos']} contentStyle={{ border: '1px solid #e9eeee', borderRadius: 10, boxShadow: '0 8px 24px #1c3e3a12' }} />
                  <Bar dataKey="ingresos" fill="#287b70" radius={[6, 6, 0, 0]} maxBarSize={54} />
                </BarChart></ResponsiveContainer></div>
              )}
            </section>

            <section className="chart-card distribution-chart">
              <div className="chart-heading"><div><h2>Participación por categoría</h2><p>Proporción de ingresos totales</p></div><span className="chart-menu">···</span></div>
              {loading && !data ? <div className="chart-state">Cargando indicadores…</div> : categories.length === 0 ? <div className="chart-state">Aún no hay ventas para mostrar.</div> : (
                <div className="donut-layout"><div className="donut-wrap"><div className="donut-graphic" role="img" aria-label={categories.map((item) => `${item.categoria}: ${formatMoney(item.ingresos)}`).join('; ')} style={{ background: donutBackground }} /><div className="donut-total"><strong>{categories.length}</strong><span>categorías</span></div></div>
                  <div className="legend">{categories.map((item, index) => <div className="legend-row" key={item.categoria}><span className="legend-dot" style={{ background: COLORS[index % COLORS.length] }} /><span className="legend-name">{item.categoria}</span><strong>{totalTransactions ? Math.round(Number(item.numero_ventas) / totalTransactions * 100) : 0}%</strong></div>)}</div></div>
              )}
            </section>
          </div>

          <div className="data-note"><span className="note-icon">i</span><span>Los indicadores incluyen todas las ventas persistidas en la base de datos.</span><span className="updated-label">Insightdesk · Panel de ventas</span></div>
          </>}
        </div>
      </section>
      <ChatWidget />
    </main>
  );
}

createRoot(document.getElementById('root')).render(<App />);
