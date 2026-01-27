/**
 * API client for OpenChatDB backend.
 */
const API = {
  async _fetch(url, options = {}) {
    const resp = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
    const data = await resp.json();
    if (!resp.ok && !data.needs_confirmation) {
      throw new Error(data.error || `HTTP ${resp.status}`);
    }
    return data;
  },

  // --- Connections ---
  listConnections() {
    return this._fetch('/api/connections');
  },
  createConnection(cfg) {
    return this._fetch('/api/connections', { method: 'POST', body: JSON.stringify(cfg) });
  },
  updateConnection(id, cfg) {
    return this._fetch(`/api/connections/${id}`, { method: 'PUT', body: JSON.stringify(cfg) });
  },
  deleteConnection(id) {
    return this._fetch(`/api/connections/${id}`, { method: 'DELETE' });
  },
  connect(id) {
    return this._fetch(`/api/connections/${id}/connect`, { method: 'POST' });
  },
  disconnect(id) {
    return this._fetch(`/api/connections/${id}/disconnect`, { method: 'POST' });
  },
  testConnection(cfg) {
    return this._fetch('/api/connections/test', { method: 'POST', body: JSON.stringify(cfg) });
  },

  // --- Database browsing ---
  listDatabases(connId) {
    return this._fetch(`/api/db/${connId}/databases`);
  },
  listTables(connId, db) {
    return this._fetch(`/api/db/${connId}/${db}/tables`);
  },
  tableStructure(connId, db, table) {
    return this._fetch(`/api/db/${connId}/${db}/${table}/structure`);
  },
  browseData(connId, db, table, page = 1, pageSize = 50) {
    return this._fetch(`/api/db/${connId}/${db}/${table}/data?page=${page}&page_size=${pageSize}`);
  },
  tableIndexes(connId, db, table) {
    return this._fetch(`/api/db/${connId}/${db}/${table}/indexes`);
  },

  // --- Query ---
  executeQuery(connId, database, query, confirmed = false) {
    return this._fetch('/api/query/execute', {
      method: 'POST',
      body: JSON.stringify({ conn_id: connId, database, query, confirmed }),
    });
  },

  // --- Schema ---
  indexSchema(connId, db) {
    return this._fetch(`/api/schema/${connId}/${db}/index`, { method: 'POST' });
  },
  searchSchema(connId, db, q, kind = 'all', table = '') {
    let url = `/api/schema/${connId}/${db}/search?q=${encodeURIComponent(q)}&kind=${kind}`;
    if (table) url += `&table=${encodeURIComponent(table)}`;
    return this._fetch(url);
  },

  // --- Chat ---
  sendChat(connId, database, messages) {
    return this._fetch('/api/chat/send', {
      method: 'POST',
      body: JSON.stringify({ conn_id: connId, database, messages }),
    });
  },
  executeChatQuery(connId, database, query) {
    return this._fetch('/api/chat/execute', {
      method: 'POST',
      body: JSON.stringify({ conn_id: connId, database, query }),
    });
  },
};
