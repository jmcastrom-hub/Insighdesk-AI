import React, { useCallback, useEffect, useMemo, useState } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const today = (() => { const d = new Date(); d.setMinutes(d.getMinutes() - d.getTimezoneOffset()); return d.toISOString().slice(0, 10); })();
const money = new Intl.NumberFormat('es-CR', { style: 'currency', currency: 'CRC', maximumFractionDigits: 2 });
const currency = (amount, code = 'CRC') => new Intl.NumberFormat('es-CR', { style: 'currency', currency: code, maximumFractionDigits: 2 }).format(Number(amount) || 0);

async function api(path, options = {}, token) {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
  });
  if (!response.ok) {
    let message = `Error ${response.status}`;
    try { message = (await response.json()).detail || message; } catch { /* response has no JSON body */ }
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}

function RequestForm({ kind, item, products, sales, session, onClose, onSaved }) {
  const [form, setForm] = useState({ producto_id: item?.id || '', venta_id: item?.id || '', moneda: 'USD', cantidad: 1, monto_crc: '', monto_moneda: '', nuevo_precio: '', revendible: false, motivo: '' });
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  const title = { cambio_precio: 'Solicitar cambio de precio', devolucion: 'Registrar devolución', nota_credito: 'Solicitar nota de crédito', cambio_moneda: 'Registrar pago en otra moneda', entrada_inventario: 'Solicitar entrada de inventario' }[kind];
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('');
    const body = { tipo: kind, motivo: form.motivo };
    if (kind === 'cambio_precio') Object.assign(body, { producto_id: Number(form.producto_id), nuevo_precio: form.nuevo_precio });
    if (kind === 'entrada_inventario') Object.assign(body, { producto_id: Number(form.producto_id), cantidad: Number(form.cantidad) });
    if (kind === 'devolucion') Object.assign(body, { venta_id: Number(form.venta_id), cantidad: Number(form.cantidad), revendible: form.revendible });
    if (kind === 'nota_credito') Object.assign(body, { venta_id: Number(form.venta_id), monto_crc: form.monto_crc });
    if (kind === 'cambio_moneda') Object.assign(body, { venta_id: Number(form.venta_id), moneda: form.moneda, monto_moneda: form.monto_moneda });
    try { await api('/solicitudes', { method: 'POST', body: JSON.stringify(body) }, session?.token); await onSaved(); onClose(); }
    catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  return <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}><form className="edit-modal" onSubmit={submit}>
    <div className="modal-heading"><div><span className="modal-kicker">REQUIERE APROBACIÓN</span><h2>{title}</h2></div><button type="button" className="icon-button" onClick={onClose} aria-label="Cerrar">×</button></div>
    {(kind === 'cambio_precio' || kind === 'entrada_inventario') && <label>Producto<select required value={form.producto_id} onChange={(e) => setForm({ ...form, producto_id: e.target.value })}><option value="" disabled>Selecciona un producto</option>{products.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}</select></label>}
    {kind === 'cambio_precio' && <label>Nuevo precio (CRC)<input required type="number" min="0.01" step="0.01" value={form.nuevo_precio} onChange={(e) => setForm({ ...form, nuevo_precio: e.target.value })} /></label>}
    {kind === 'entrada_inventario' && <label>Unidades recibidas<input required type="number" min="1" step="1" value={form.cantidad} onChange={(e) => setForm({ ...form, cantidad: e.target.value })} /></label>}
    {['devolucion', 'nota_credito', 'cambio_moneda'].includes(kind) && <label>Venta<select required value={form.venta_id} onChange={(e) => setForm({ ...form, venta_id: e.target.value })}><option value="" disabled>Selecciona una venta</option>{sales.map((s) => <option key={s.id} value={s.id} disabled={s.estado_pago === 'pendiente'}>Venta #{s.id} · {money.format(Number(s.total))} · {s.estado_pago}</option>)}</select></label>}
    {kind === 'devolucion' && <><label>Unidades devueltas<input required type="number" min="1" step="1" value={form.cantidad} onChange={(e) => setForm({ ...form, cantidad: e.target.value })} /></label><label className="check-label"><input type="checkbox" checked={form.revendible} onChange={(e) => setForm({ ...form, revendible: e.target.checked })} /> El producto vuelve a estar disponible para venta</label></>}
    {kind === 'nota_credito' && <label>Monto (CRC)<input required type="number" min="0.01" step="0.01" value={form.monto_crc} onChange={(e) => setForm({ ...form, monto_crc: e.target.value })} /></label>}
    {kind === 'cambio_moneda' && <><label>Moneda<select value={form.moneda} onChange={(e) => setForm({ ...form, moneda: e.target.value })}><option value="USD">Dólares (USD)</option><option value="EUR">Euros (EUR)</option></select></label><label>Monto recibido ({form.moneda})<input required type="number" min="0.0001" step="0.0001" value={form.monto_moneda} onChange={(e) => setForm({ ...form, monto_moneda: e.target.value })} /></label><p className="form-hint">La solicitud consulta la tasa oficial del BCCR para la fecha de la venta. El monto y la fecha de la tasa quedan guardados.</p></>}
    <label>Motivo<textarea required minLength="3" maxLength="500" value={form.motivo} onChange={(e) => setForm({ ...form, motivo: e.target.value })} /></label>
    {error && <p className="form-error" role="alert">{error}</p>}<div className="modal-actions"><button type="button" className="secondary-button" onClick={onClose}>Cancelar</button><button className="primary-button" disabled={busy}>{busy ? 'Enviando…' : 'Enviar solicitud'}</button></div>
  </form></div>;
}

function ProductForm({ initial, session, onClose, onSaved }) {
  const [form, setForm] = useState(initial || { nombre: '', categoria: '', precio: '' }); const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('');
    const body = initial ? { nombre: form.nombre, categoria: form.categoria } : form;
    try { await api(initial ? `/productos/${initial.id}` : '/productos', { method: initial ? 'PATCH' : 'POST', body: JSON.stringify(body) }, session?.token); await onSaved(); onClose(); }
    catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  return <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}><form className="edit-modal" onSubmit={submit}>
    <div className="modal-heading"><div><span className="modal-kicker">CATÁLOGO</span><h2>{initial ? 'Editar producto' : 'Nuevo producto'}</h2></div><button type="button" className="icon-button" onClick={onClose} aria-label="Cerrar">×</button></div>
    <label>Nombre<input required maxLength="120" value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} /></label><label>Categoría<input required maxLength="80" value={form.categoria} onChange={(e) => setForm({ ...form, categoria: e.target.value })} /></label>
    {!initial && <label>Precio (CRC)<input required type="number" min="0.01" step="0.01" value={form.precio} onChange={(e) => setForm({ ...form, precio: e.target.value })} /></label>}
    {initial && <p className="form-hint">El cambio de precio debe enviarse por separado para aprobación de gerencia.</p>}{error && <p className="form-error" role="alert">{error}</p>}
    <div className="modal-actions"><button type="button" className="secondary-button" onClick={onClose}>Cancelar</button><button className="primary-button" disabled={busy}>{busy ? 'Guardando…' : 'Guardar'}</button></div>
  </form></div>;
}

function SellerForm({ session, onSaved, onClose }) {
  const [name, setName] = useState(''); const [password, setPassword] = useState(''); const [error, setError] = useState('');
  async function submit(e) { e.preventDefault(); setError(''); try { await api('/vendedores', { method: 'POST', body: JSON.stringify({ nombre: name, password }) }, session.token); await onSaved(); onClose(); } catch (err) { setError(err.message); } }
  return <div className="modal-backdrop"><form className="edit-modal" onSubmit={submit}><div className="modal-heading"><div><span className="modal-kicker">EQUIPO</span><h2>Agregar vendedor</h2></div><button type="button" className="icon-button" onClick={onClose}>×</button></div><label>Nombre<input required maxLength="120" value={name} onChange={(e) => setName(e.target.value)} /></label><label>Contraseña individual<input required type="password" minLength="8" value={password} onChange={(e) => setPassword(e.target.value)} /></label>{error && <p className="form-error">{error}</p>}<div className="modal-actions"><button type="button" className="secondary-button" onClick={onClose}>Cancelar</button><button className="primary-button">Guardar vendedor</button></div></form></div>;
}

export default function Management({ section, onDataChange, session }) {
  const [products, setProducts] = useState([]); const [sales, setSales] = useState([]); const [sellers, setSellers] = useState([]); const [sellerMetrics, setSellerMetrics] = useState([]); const [requests, setRequests] = useState([]); const [events, setEvents] = useState([]); const [movements, setMovements] = useState([]);
  const [loading, setLoading] = useState(true); const [error, setError] = useState(''); const [modal, setModal] = useState(null);
  const [search, setSearch] = useState(''); const [requestFilter, setRequestFilter] = useState('todos');
  const token = session?.token;
  useEffect(() => { setSearch(''); setRequestFilter('todos'); }, [section]);
  const load = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const calls = [api('/productos'), api('/ventas'), api('/vendedores'), api('/vendedores/indicadores'), api('/solicitudes'), api('/inventario/movimientos'), api('/auditoria')];
      const data = await Promise.all(calls); setProducts(data[0]); setSales(data[1]); setSellers(data[2]); setSellerMetrics(data[3]); setRequests(data[4]); setMovements(data[5]);
      setEvents(data[6]);
    } catch (err) { setError(err.message); } finally { setLoading(false); }
  }, [token]);
  useEffect(() => { load(); }, [load]);
  const productById = useMemo(() => Object.fromEntries(products.map((p) => [p.id, p])), [products]);
  async function saved() { await load(); await onDataChange(); }
  async function reassign(sale, sellerId) {
    try { await api(`/ventas/${sale.id}`, { method: 'PATCH', body: JSON.stringify({ vendedor_id: Number(sellerId) }) }, token); await saved(); }
    catch (err) { setError(err.message); }
  }
  async function removeProduct(product) {
    if (!window.confirm(`¿Eliminar el producto “${product.nombre}”? Solo se puede si no tiene ventas.`)) return;
    try { await api(`/productos/${product.id}`, { method: 'DELETE' }, token); await saved(); }
    catch (err) { setError(err.message); }
  }
  async function decide(request, decision) {
    const respuesta = window.prompt(decision === 'aprobada' ? 'Comentario de aprobación (opcional):' : 'Motivo de denegación:');
    if (respuesta === null) return;
    try { await api(`/solicitudes/${request.id}/resolver`, { method: 'POST', body: JSON.stringify({ decision, respuesta }) }, token); await saved(); }
    catch (err) { setError(err.message); }
  }
  const isManager = session?.role === 'gerente';
  const title = { productos: 'Productos', ventas: 'Ventas', inventario: 'Inventario', vendedores: 'Vendedores', solicitudes: 'Aprobaciones', auditoria: 'Registro de acciones' }[section];
  const attributedSales = sales.filter((sale) => sale.vendedor_id !== null);
  const totalUnits = sales.reduce((sum, sale) => sum + Number(sale.cantidad || 0), 0);
  const inventoryUnits = products.reduce((sum, product) => sum + Number(product.existencias || 0), 0);
  const approvedRequests = requests.filter((request) => request.estado === 'aprobada').length;
  const deniedRequests = requests.filter((request) => request.estado === 'denegada').length;
  const pendingRequests = requests.filter((request) => request.estado === 'pendiente').length;
  const workspaceStats = {
    productos: [['Productos', products.length, 'en el catálogo', '▦'], ['Categorías', new Set(products.map((item) => item.categoria)).size, 'líneas de producto', '◈'], ['Precio promedio', money.format(products.length ? products.reduce((sum, item) => sum + Number(item.precio), 0) / products.length : 0), 'por unidad', '↗']],
    ventas: [['Transacciones', sales.length, 'registros históricos', '▤'], ['Unidades', totalUnits, 'en las ventas', '↗'], ['Ventas atribuidas', attributedSales.length, 'con responsable', '♙']],
    inventario: [['Productos', products.length, 'referencias activas', '▦'], ['Unidades disponibles', inventoryUnits, 'existencias actuales', '▣'], ['Movimientos', movements.length, 'con trazabilidad', '↻']],
    vendedores: [['Equipo activo', sellers.length, 'cuentas disponibles', '♙'], ['Ventas asignadas', attributedSales.length, 'con vendedor', '▤'], ['Unidades vendidas', sellerMetrics.reduce((sum, row) => sum + Number(row.unidades || 0), 0), 'netas de devoluciones', '↗']],
    solicitudes: [['Solicitudes', requests.length, 'en el historial', '◇'], ['Aprobadas', approvedRequests, 'decisiones registradas', '✓'], ['Denegadas', deniedRequests, `${pendingRequests} pendientes`, '×']],
    auditoria: [['Eventos', events.length, 'en el registro', '≡'], ['Vendedores', sellers.length, 'con actividad demo', '♙'], ['Movimientos', movements.length, 'de inventario', '↻']],
  }[section] || [];
  const query = search.trim().toLocaleLowerCase('es-CR');
  const visibleProducts = products.filter((item) => `${item.nombre} ${item.categoria}`.toLocaleLowerCase('es-CR').includes(query));
  const visibleSales = sales.filter((item) => `${item.id} ${item.fecha} ${productById[item.producto_id]?.nombre || ''} ${sellers.find((seller) => seller.id === item.vendedor_id)?.nombre || 'sin asignar'}`.toLocaleLowerCase('es-CR').includes(query));
  const visibleMovements = movements.filter((item) => `${item.producto} ${item.actor} ${item.tipo} ${item.motivo}`.toLocaleLowerCase('es-CR').includes(query));
  const visibleSellerMetrics = sellerMetrics.filter((item) => `${item.vendedor} ${item.ventas} ${item.unidades}`.toLocaleLowerCase('es-CR').includes(query));
  const visibleRequests = requests.filter((item) => (requestFilter === 'todos' || item.estado === requestFilter) && `${item.tipo} ${item.estado} ${item.motivo} ${item.solicitante_nombre} ${item.revisor_nombre || ''}`.toLocaleLowerCase('es-CR').includes(query));
  const visibleEvents = events.filter((item) => `${item.actor} ${item.accion} ${item.entidad} ${JSON.stringify(item.detalles)}`.toLocaleLowerCase('es-CR').includes(query));
  const visibleCount = { productos: visibleProducts.length, ventas: visibleSales.length, inventario: visibleProducts.length + visibleMovements.length, vendedores: visibleSellerMetrics.length, solicitudes: visibleRequests.length, auditoria: visibleEvents.length }[section] || 0;
  return <section className="management-card">
    <div className="management-heading"><div><p className="eyebrow">GESTIÓN Y TRAZABILIDAD</p><h2>{title}</h2><p>{section === 'solicitudes' ? 'Las solicitudes son visibles para el equipo; solo José Castro puede resolverlas desde su equipo.' : 'Cada operación queda identificada y registrada.'}</p></div>
      {section === 'productos' && <button className="primary-button" onClick={() => setModal({ kind: 'producto' })}>＋ Nuevo producto</button>}
      {section === 'ventas' && <button className="primary-button" onClick={() => setModal({ kind: 'venta' })}>＋ Registrar venta</button>}
      {section === 'vendedores' && isManager && <button className="primary-button" onClick={() => setModal({ kind: 'vendedor' })}>＋ Agregar vendedor</button>}
    </div>
    {!session && <div className="management-notice">Inicia sesión para registrar cambios, solicitar aprobaciones o consultar el registro de acciones.</div>}
    {!!workspaceStats.length && <div className="workspace-stats">{workspaceStats.map(([label, value, note, icon], index) => <article className="workspace-stat" key={label} style={{ '--stat-index': index }}><span className="workspace-stat-icon">{icon}</span><div><small>{label}</small><strong>{value}</strong><span>{note}</span></div></article>)}</div>}
    <div className="workspace-toolbar"><label className="workspace-search"><span aria-hidden="true">⌕</span><input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder={`Buscar en ${title.toLowerCase()}…`} aria-label={`Buscar en ${title.toLowerCase()}`} />{search && <button type="button" onClick={() => setSearch('')} aria-label="Limpiar búsqueda">×</button>}</label>{section === 'solicitudes' && <div className="request-filters" role="group" aria-label="Filtrar solicitudes"><button className={requestFilter === 'todos' ? 'selected' : ''} onClick={() => setRequestFilter('todos')}>Todas {requests.length}</button><button className={requestFilter === 'aprobada' ? 'selected' : ''} onClick={() => setRequestFilter('aprobada')}>Aprobadas {approvedRequests}</button><button className={requestFilter === 'denegada' ? 'selected' : ''} onClick={() => setRequestFilter('denegada')}>Denegadas {deniedRequests}</button><button className={requestFilter === 'pendiente' ? 'selected' : ''} onClick={() => setRequestFilter('pendiente')}>Pendientes {pendingRequests}</button></div>}<span className="workspace-result-count">{visibleCount} resultados</span></div>
    {error && <div className="management-error" role="alert">{error}<button onClick={load}>Volver a cargar</button></div>}
    {loading ? <div className="management-empty">Cargando…</div> : section === 'productos' ? <div className="table-scroll"><table><thead><tr><th>Producto</th><th>Categoría</th><th>Precio</th><th>Existencias</th><th>Acciones</th></tr></thead><tbody>{visibleProducts.map((p) => <tr key={p.id}><td><strong>{p.nombre}</strong><small>ID {p.id}</small></td><td>{p.categoria}</td><td>{money.format(Number(p.precio))}</td><td>{p.existencias}</td><td className="row-actions">{session && <><button onClick={() => setModal({ kind: 'producto', item: p })}>Editar</button><button onClick={() => setModal({ kind: 'cambio_precio', item: p })}>Solicitar precio</button><button onClick={() => setModal({ kind: 'entrada_inventario', item: p })}>Entrada</button>{isManager && <button className="delete-action" onClick={() => removeProduct(p)}>Eliminar</button>}</>}</td></tr>)}</tbody></table>{!products.length && <div className="management-empty">Todavía no hay productos.</div>}</div>
    : section === 'ventas' ? <div className="table-scroll"><table><thead><tr><th>Fecha</th><th>Producto</th><th>Vendedor</th><th>Cantidad</th><th>Ingreso CRC</th><th>Cobro</th><th>Estado</th><th>Acciones</th></tr></thead><tbody>{visibleSales.map((sale) => <tr key={sale.id}><td>{sale.fecha}</td><td>{productById[sale.producto_id]?.nombre || `Producto ${sale.producto_id}`}<small>Venta #{sale.id}</small></td><td>{sellers.find((s) => s.id === sale.vendedor_id)?.nombre || 'Sin asignar'}{isManager && sellers.length > 0 && <select aria-label="Asignar vendedor" value={sale.vendedor_id || ''} onChange={(e) => reassign(sale, e.target.value)}><option value="" disabled>Asignar…</option>{sellers.map((seller) => <option value={seller.id} key={seller.id}>{seller.nombre}</option>)}</select>}</td><td>{sale.cantidad}</td><td>{money.format(Number(sale.total))}</td><td>{sale.moneda_pago === 'CRC' ? 'CRC' : `${currency(sale.monto_moneda, sale.moneda_pago)} · BCCR`}</td><td><span className={`status-pill ${sale.estado_pago}`}>{sale.estado_pago}</span></td><td className="row-actions">{session && sale.estado_pago !== 'pendiente' && <><button onClick={() => setModal({ kind: 'devolucion', item: sale })}>Devolución</button><button onClick={() => setModal({ kind: 'nota_credito', item: sale })}>Nota</button><button onClick={() => setModal({ kind: 'cambio_moneda', item: sale })}>Moneda</button></>}</td></tr>)}</tbody></table></div>
    : section === 'inventario' ? <><div className="table-scroll"><table><thead><tr><th>Producto</th><th>Existencias actuales</th><th>Acción</th></tr></thead><tbody>{visibleProducts.map((p) => <tr key={p.id}><td><strong>{p.nombre}</strong></td><td><span className={p.existencias <= 0 ? 'stock-empty' : 'stock-count'}>{p.existencias}</span></td><td className="row-actions">{session && <button onClick={() => setModal({ kind: 'entrada_inventario', item: p })}>Solicitar entrada</button>}</td></tr>)}</tbody></table></div><h3 className="subsection-title">Movimientos de inventario</h3><div className="table-scroll"><table><thead><tr><th>Fecha</th><th>Producto</th><th>Movimiento</th><th>Unidades</th><th>Responsable</th><th>Motivo</th></tr></thead><tbody>{visibleMovements.map((m) => <tr key={m.id}><td>{m.creado_en.slice(0, 10)}</td><td>{m.producto}</td><td>{m.tipo}</td><td>{m.cantidad > 0 ? `+${m.cantidad}` : m.cantidad}</td><td>{m.actor}</td><td>{m.motivo}</td></tr>)}</tbody></table></div></>
    : section === 'vendedores' ? <div className="table-scroll"><table><thead><tr><th>Vendedor</th><th>Ventas</th><th>Unidades</th><th>Ingresos netos</th></tr></thead><tbody>{visibleSellerMetrics.map((row) => <tr key={row.vendedor_id ?? 'unassigned'}><td><strong>{row.vendedor}</strong></td><td>{row.ventas}</td><td>{row.unidades}</td><td>{money.format(Number(row.ingresos))}</td></tr>)}</tbody></table><p className="form-hint">Las ventas seed permanecen «Sin asignar» hasta que gerencia las distribuya entre los vendedores reales.</p></div>
    : section === 'solicitudes' ? <div className="approval-list">{visibleRequests.map((r) => <article className="approval-item" key={r.id}><div className="approval-top"><strong>#{r.id} · {requestTitle(r.tipo)}</strong><span className={`status-pill ${r.estado}`}>{r.estado}</span>{r.motivo.startsWith('DEMO-HISTORY-v1-') && <span className="demo-badge">MUESTRA</span>}</div><p>{r.motivo}</p><small>Solicita {r.solicitante_nombre} · {new Date(r.creada_en).toLocaleString('es-CR')}</small><RequestDetails request={r} products={productById} sales={sales} />{r.respuesta && <p className="approval-response">Respuesta: {r.respuesta} · {r.revisor_nombre}</p>}{isManager && r.estado === 'pendiente' && <div className="approval-actions"><button className="secondary-button" onClick={() => decide(r, 'denegada')}>Denegar</button><button className="primary-button" onClick={() => decide(r, 'aprobada')}>Aprobar</button></div>}</article>)}{!visibleRequests.length && <div className="management-empty">No hay solicitudes que coincidan con el filtro.</div>}</div>
    : <div className="table-scroll"><table><thead><tr><th>Fecha</th><th>Persona</th><th>Acción</th><th>Registro</th><th>Detalles</th></tr></thead><tbody>{visibleEvents.map((e) => <tr key={e.id}><td>{new Date(e.creado_en).toLocaleString('es-CR')}</td><td><strong>{e.actor}</strong></td><td>{e.accion}</td><td>{e.entidad} {e.entidad_id ? `#${e.entidad_id}` : ''}</td><td><code>{JSON.stringify(e.detalles)}</code></td></tr>)}</tbody></table>{!events.length && <div className="management-empty">Todavía no hay acciones registradas.</div>}</div>}
    {modal?.kind === 'producto' && <ProductForm initial={modal.item} session={session} onClose={() => setModal(null)} onSaved={saved} />}
    {modal?.kind === 'vendedor' && <SellerForm session={session} onClose={() => setModal(null)} onSaved={saved} />}
    {modal && !['producto', 'vendedor', 'venta'].includes(modal.kind) && <RequestForm kind={modal.kind} item={modal.item} products={products} sales={sales} session={session} onClose={() => setModal(null)} onSaved={saved} />}
    {modal?.kind === 'venta' && <SaleForm products={products} sellers={sellers} session={session} onClose={() => setModal(null)} onSaved={saved} />}
  </section>;
}

function requestTitle(type) { return ({ cambio_precio: 'Cambio de precio', devolucion: 'Devolución', nota_credito: 'Nota de crédito', cambio_moneda: 'Cambio de moneda', entrada_inventario: 'Entrada de inventario' })[type] || type; }
function RequestDetails({ request, products, sales }) {
  const d = request.datos; const sale = sales.find((s) => s.id === Number(d.venta_id));
  if (request.tipo === 'cambio_precio') return <p>Producto {products[d.producto_id]?.nombre || `#${d.producto_id}`} · Nuevo precio {money.format(Number(d.nuevo_precio))}</p>;
  if (request.tipo === 'entrada_inventario') return <p>Producto {products[d.producto_id]?.nombre || `#${d.producto_id}`} · Entrada {d.cantidad} unidades</p>;
  if (request.tipo === 'devolucion') return <p>Venta #{d.venta_id} · {d.cantidad} unidades · {d.revendible ? 'Reingresa al inventario' : 'No revendible'}</p>;
  if (request.tipo === 'nota_credito') return <p>Venta #{d.venta_id} · {money.format(Number(d.monto_crc))}</p>;
  const fx = d.detalle_tasas_bccr || {};
  return <p>Venta #{d.venta_id} · {d.monto_moneda} {d.moneda} → {money.format(Number(d.equivalente_crc))} · BCCR {d.fecha_tipo_cambio} (1 {d.moneda} = {d.tipo_cambio} CRC){d.moneda === 'EUR' && fx.eur_usd && <> · EUR/USD {fx.eur_usd} ({fx.fecha_eur_usd}); compra USD/CRC {fx.usd_crc_compra} ({fx.fecha_usd})</>}</p>;
}

function SaleForm({ products, sellers, session, onClose, onSaved }) {
  const [form, setForm] = useState({ producto_id: products[0]?.id || '', vendedor_id: '', cantidad: 1, fecha: today }); const [error, setError] = useState('');
  async function submit(event) { event.preventDefault(); setError(''); const body = { producto_id: Number(form.producto_id), cantidad: Number(form.cantidad), fecha: form.fecha }; if (session?.role === 'gerente' && form.vendedor_id) body.vendedor_id = Number(form.vendedor_id); try { await api('/ventas', { method: 'POST', body: JSON.stringify(body) }, session?.token); await onSaved(); onClose(); } catch (err) { setError(err.message); } }
  return <div className="modal-backdrop"><form className="edit-modal" onSubmit={submit}><div className="modal-heading"><div><span className="modal-kicker">VENTA NUEVA</span><h2>Registrar venta</h2></div><button type="button" className="icon-button" onClick={onClose}>×</button></div><label>Producto<select required value={form.producto_id} onChange={(e) => setForm({ ...form, producto_id: e.target.value })}><option value="" disabled>Selecciona</option>{products.map((p) => <option key={p.id} value={p.id} disabled={p.existencias < 1}>{p.nombre} · {money.format(Number(p.precio))} · stock {p.existencias}</option>)}</select></label>{session?.role === 'gerente' && <label>Vendedor<select value={form.vendedor_id} onChange={(e) => setForm({ ...form, vendedor_id: e.target.value })}><option value="">Sin asignar</option>{sellers.map((s) => <option key={s.id} value={s.id}>{s.nombre}</option>)}</select></label>}<label>Cantidad<input required type="number" min="1" step="1" value={form.cantidad} onChange={(e) => setForm({ ...form, cantidad: e.target.value })} /></label><label>Fecha<input required type="date" value={form.fecha} onChange={(e) => setForm({ ...form, fecha: e.target.value })} /></label>{error && <p className="form-error">{error}</p>}<div className="modal-actions"><button type="button" className="secondary-button" onClick={onClose}>Cancelar</button><button className="primary-button">Guardar venta</button></div></form></div>;
}
