import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const API = '/api';
const NEXT = { OPEN: 'INVESTIGATING', INVESTIGATING: 'RESOLVED', RESOLVED: 'OPEN' };
const FILTERS = ['ALL', 'OPEN', 'INVESTIGATING', 'RESOLVED'];

function App() {
  const [incidents, setIncidents] = useState([]);
  const [stats, setStats] = useState({ total: 0, open: 0, investigating: 0, resolved: 0, sev1Open: 0 });
  const [cfg, setCfg] = useState({ environment: '', banner: '' });
  const [filter, setFilter] = useState('ALL');
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = async () => {
    try {
      setError('');
      const [a, b, c] = await Promise.all([fetch(`${API}/incidents`), fetch(`${API}/incidents/stats`), fetch(`${API}/config`)]);
      if (!a.ok || !b.ok || !c.ok) throw Error('Backend unavailable');
      setIncidents(await a.json());
      setStats(await b.json());
      setCfg(await c.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const advance = async (i) => {
    await fetch(`${API}/incidents/${i.id}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status: NEXT[i.status] }),
    });
    load();
  };

  const create = async (e) => {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form);
    await fetch(`${API}/incidents`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(Object.fromEntries(['title', 'service', 'severity', 'owner', 'description'].map((k) => [k, f.get(k)]))),
    });
    form.reset();
    setShowForm(false);
    load();
  };

  const visible = filter === 'ALL' ? incidents : incidents.filter((i) => i.status === filter);

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">I</span><div><b>IncidentBoard</b><small>{cfg.environment || '...'}</small></div></div>
        <nav><a className="active">▦ <span>Incidents</span></a></nav>
        <div className="side-bottom"><div className="upgrade"><strong>On-call</strong><p>Track an outage from first alert to resolution.</p></div></div>
      </aside>
      <main className="main">
        <header>
          <div><p className="eyebrow">ON-CALL / OVERVIEW</p><h1>{cfg.banner || 'IncidentBoard'}</h1><p className="muted">Open incidents across all services.</p></div>
          <button className="primary" onClick={() => setShowForm(true)}>＋ Declare incident</button>
        </header>
        {error && <div className="alert">⚠ {error}. Check the backend and PostgreSQL, then refresh.</div>}
        <section className="stats">
          <Stat label="Total" value={stats.total} icon="▦" />
          <Stat label="Open" value={stats.open} icon="○" />
          <Stat label="Investigating" value={stats.investigating} icon="◔" />
          <Stat label="Open SEV1" value={stats.sev1Open} icon="!" />
        </section>
        <section className="content-grid">
          <div className="panel tasks-panel">
            <div className="panel-head">
              <div><h2>Incidents</h2><p className="muted">Click ↻ to move an incident to its next state.</p></div>
              <div className="filters">{FILTERS.map((x) => <button key={x} className={filter === x ? 'selected' : ''} onClick={() => setFilter(x)}>{x}</button>)}</div>
            </div>
            {loading ? <div className="empty">Loading incidents…</div> : (
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Incident</th><th>Service</th><th>Owner</th><th>Severity</th><th>Status</th><th></th></tr></thead>
                  <tbody>{visible.map((i) => (
                    <tr key={i.id}>
                      <td><div className="task-title"><span className={`dot ${i.status.toLowerCase()}`}></span><div><b>{i.title}</b><small>{i.description}</small></div></div></td>
                      <td>{i.service}</td>
                      <td>{i.owner}</td>
                      <td><span className={`priority ${i.severity.toLowerCase()}`}>{i.severity}</span></td>
                      <td><span className={`status ${i.status.toLowerCase()}`}>{i.status}</span></td>
                      <td><button className="icon-btn" onClick={() => advance(i)} title="Next state">↻</button></td>
                    </tr>
                  ))}</tbody>
                </table>
                {!visible.length && <div className="empty">No incidents in this filter.</div>}
              </div>
            )}
          </div>
          <aside className="panel activity">
            <div className="panel-head"><div><h2>Delivery pipeline</h2><p className="muted">How this page reached the cluster.</p></div></div>
            <div className="pipeline"><span>Test</span><i></i><span>Scan</span><i></i><span>GHCR</span><i></i><span>Argo CD</span></div>
          </aside>
        </section>
        {showForm && (
          <div className="modal-backdrop">
            <form className="modal" onSubmit={create}>
              <div className="modal-head"><div><p className="eyebrow">DECLARE INCIDENT</p><h2>What is broken?</h2></div><button type="button" className="close" onClick={() => setShowForm(false)}>×</button></div>
              <label>Title<input name="title" required placeholder="e.g. Checkout returns 500" /></label>
              <label>Description<textarea name="description" placeholder="Symptom, first alert, impact" /></label>
              <div className="form-row">
                <label>Service<input name="service" defaultValue="checkout" /></label>
                <label>Severity<select name="severity"><option>SEV1</option><option>SEV2</option><option>SEV3</option></select></label>
              </div>
              <label>Owner<input name="owner" defaultValue="Bibek" /></label>
              <button className="primary full">Declare</button>
            </form>
          </div>
        )}
      </main>
    </div>
  );
}

function Stat({ label, value, icon }) {
  return <div className="stat"><div className="stat-icon">{icon}</div><div><small>{label}</small><strong>{value}</strong></div></div>;
}

createRoot(document.getElementById('root')).render(<App />);
