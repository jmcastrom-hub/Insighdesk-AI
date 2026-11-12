import React, { useCallback, useEffect, useState } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const today = (() => {
  const local = new Date();
  local.setMinutes(local.getMinutes() - local.getTimezoneOffset());
  return local.toISOString().slice(0, 10);
})();
const money = new Intl.NumberFormat('es-CR', { style: 'currency', currency: 'CRC', maximumFractionDigits: 2 });

async function api(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  });
  if (!response.ok) {
    let message = `Error ${response.status}`;
    try { message = (await response.json()).detail || message; } catch { /* usa el estado HTTP */ }
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}

function ProductForm({ initial, onClose, onSaved }) {
  const [form, setForm] = useState(initial || { nombre: '', categoria: '', precio: '' });
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  async function submit(event) {
    event.preventDefault(); setSaving(true); setError('');
    try {
      await api(initial ? `/productos/${initial.id}` : '/productos', {
        method: initial ? 'PATCH' : 'POST',
        body: JSON.stringify({ nombre: form.nombre, categoria: form.categoria, precio: form.precio }),
      });
      await onSaved(); onClose();
    } catch (err) { setError(err.message); } finally { setSaving(false); }
  }
  return <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
    <form className="edit-modal" onSubmit={submit}>
      <div className="modal-heading"><div><span className="modal-kicker">CATÁLOGO</span><h2>{initial ? 'Editar producto' : 'Nuevo producto'}</h2></div><button type="button" className="icon-button" onClick={onClose} aria-label="Cerrar">×</button></div>
      <label>Nombre<input autoFocus required maxLength="120" value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} /></label>
      <label>Categoría<input required maxLength="80" value={form.categoria} onChange={(e) => setForm({ ...form, categoria: e.target.value })} /></label>
      <label>Precio (CRC)<input required type="number" min="0.01" step="0.01" value={form.precio} onChange={(e) => setForm({ ...form, precio: e.target.value })} /></label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="modal-actions"><button type="button" className="secondary-button" onClick={onClose}>Cancelar</button><button className="primary-button" disabled={saving}>{saving ? 'Guardando…' : 'Guardar producto'}</button></div>
    </form>
  </div>;
}

function SaleForm({ initial, products, onClose, onSaved }) {
  const [form, setForm] = useState(initial || { producto_id: products[0]?.id || '', cantidad: 1, fecha: today });
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  async function submit(event) {
    event.preventDefault(); setSaving(true); setError('');
    try {
      await api(initial ? `/ventas/${initial.id}` : '/ventas', {
        method: initial ? 'PATCH' : 'POST',
        body: JSON.stringify({ producto_id: Number(form.producto_id), cantidad: Number(form.cantidad), fecha: form.fecha }),
      });
      await onSaved(); onClose();
    } catch (err) { setError(err.message); } finally { setSaving(false); }
  }
  return <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
    <form className="edit-modal" onSubmit={submit}>
      <div className="modal-heading"><div><span className="modal-kicker">MOVIMIENTOS</span><h2>{initial ? 'Editar venta' : 'Registrar venta'}</h2></div><button type="button" className="icon-button" onClick={onClose} aria-label="Cerrar">×</button></div>
      <label>Producto<select required value={form.producto_id} onChange={(e) => setForm({ ...form, producto_id: e.target.value })}><option value="" disabled>Selecciona un producto</option>{products.map((product) => <option key={product.id} value={product.id}>{product.nombre} · {money.format(Number(product.precio))}</option>)}</select></label>
      <label>Cantidad<input required type="number" min="1" max="1000000" step="1" value={form.cantidad} onChange={(e) => setForm({ ...form, cantidad: e.target.value })} /></label>
      <label>Fecha<input required type="date" value={form.fecha} onChange={(e) => setForm({ ...form, fecha: e.target.value })} /></label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="modal-actions"><button type="button" className="secondary-button" onClick={onClose}>Cancelar</button><button className="primary-button" disabled={saving || !products.length}>{saving ? 'Guardando…' : 'Guardar venta'}</button></div>
    </form>
  </div>;
}

export default function Management({ section, onDataChange }) {
  const [products, setProducts] = useState([]);
  const [sales, setSales] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [form, setForm] = useState(null);
  const load = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const [productData, saleData] = await Promise.all([api('/productos'), api('/ventas')]);
      setProducts(productData); setSales(saleData);
    } catch (err) { setError(err.message); } finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  async function remove(type, item) {
    if (!window.confirm(`¿Eliminar ${type === 'productos' ? `el producto “${item.nombre}”` : `la venta #${item.id}`}?`)) return;
    try { await api(`/${type}/${item.id}`, { method: 'DELETE' }); await load(); await onDataChange(); }
    catch (err) { setError(err.message); }
  }
  async function saved() { await load(); await onDataChange(); }

  const isProducts = section === 'productos';
  const productById = Object.fromEntries(products.map((product) => [product.id, product]));
  return <section className="management-card">
    <div className="management-heading"><div><p className="eyebrow">GESTIÓN DE DATOS</p><h2>{isProducts ? 'Productos' : 'Ventas'}</h2><p>{isProducts ? 'Administra el catálogo y los precios.' : 'Registra y corrige operaciones guardadas.'}</p></div>
      <button className="primary-button" onClick={() => setForm({ kind: isProducts ? 'product' : 'sale' })}>＋ {isProducts ? 'Nuevo producto' : 'Registrar venta'}</button>
    </div>
    {error && <div className="management-error" role="alert">{error}<button onClick={load}>Volver a cargar</button></div>}
    {loading ? <div className="management-empty">Cargando datos…</div> : isProducts ? (
      <div className="table-scroll"><table><thead><tr><th>Producto</th><th>Categoría</th><th>Precio</th><th className="actions-heading">Acciones</th></tr></thead><tbody>{products.map((product) => <tr key={product.id}><td><strong>{product.nombre}</strong><small>ID {product.id}</small></td><td><span className="category-pill">{product.categoria}</span></td><td>{money.format(Number(product.precio))}</td><td className="row-actions"><button onClick={() => setForm({ kind: 'product', initial: product })}>Editar</button><button className="delete-action" onClick={() => remove('productos', product)}>Eliminar</button></td></tr>)}</tbody></table>{!products.length && <div className="management-empty">Todavía no hay productos. Registra uno para comenzar a vender.</div>}</div>
    ) : (
      <div className="table-scroll"><table><thead><tr><th>Fecha</th><th>Producto</th><th>Cantidad</th><th>Ingreso</th><th className="actions-heading">Acciones</th></tr></thead><tbody>{sales.map((sale) => <tr key={sale.id}><td>{sale.fecha}</td><td><strong>{productById[sale.producto_id]?.nombre || `Producto ${sale.producto_id}`}</strong><small>ID venta {sale.id}</small></td><td>{sale.cantidad}</td><td>{money.format(Number(sale.total))}</td><td className="row-actions"><button onClick={() => setForm({ kind: 'sale', initial: { ...sale, producto_id: String(sale.producto_id) } })}>Editar</button><button className="delete-action" onClick={() => remove('ventas', sale)}>Eliminar</button></td></tr>)}</tbody></table>{!sales.length && <div className="management-empty">Aún no hay ventas registradas.</div>}</div>
    )}
    {form?.kind === 'product' && <ProductForm initial={form.initial} onClose={() => setForm(null)} onSaved={saved} />}
    {form?.kind === 'sale' && <SaleForm initial={form.initial} products={products} onClose={() => setForm(null)} onSaved={saved} />}
  </section>;
}
