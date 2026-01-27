const { createApp, ref, reactive, computed, watch, nextTick, onMounted } = Vue;

const app = createApp({
  setup() {
    // ---- State ----
    const connections = ref([]);
    const activeConn = ref(null);    // connection config object
    const databases = ref([]);
    const activeDb = ref(null);
    const tables = ref([]);
    const activeTable = ref(null);
    const expandedConns = reactive({}); // connId -> bool
    const expandedDbs = reactive({});   // connId:db -> bool

    // Main view tabs: 'data' | 'structure' | 'query'
    const activeTab = ref('data');

    // Data browsing
    const tableData = ref(null);
    const dataPage = ref(1);
    const dataLoading = ref(false);

    // Table structure
    const tableStructure = ref([]);
    const tableIndexes = ref([]);
    const structureLoading = ref(false);

    const STRUCTURE_COL_ORDER = ['field', 'type', 'null', 'default', 'key', 'comment'];
    const structureColumns = computed(() => {
      if (!tableStructure.value.length) return [];
      const allKeys = Object.keys(tableStructure.value[0]);
      const ordered = [];
      for (const pref of STRUCTURE_COL_ORDER) {
        const found = allKeys.find(k => k.toLowerCase() === pref);
        if (found) ordered.push(found);
      }
      for (const k of allKeys) {
        if (!ordered.includes(k)) ordered.push(k);
      }
      return ordered;
    });

    // Query editor
    const queryText = ref('');
    const queryResult = ref(null);
    const queryLoading = ref(false);
    const queryError = ref('');
    const needsConfirmation = ref(false);

    // Chat
    const chatOpen = ref(true);
    const chatInput = ref('');
    const chatLoading = ref(false);

    // Conversations
    const conversations = ref([]);
    const activeConversationId = ref(null);
    let nextConversationId = 1;

    const activeConversation = computed(() =>
      conversations.value.find(c => c.id === activeConversationId.value) || null
    );
    const chatMessages = computed(() =>
      activeConversation.value ? activeConversation.value.messages : []
    );
    const chatQuote = computed({
      get() { return activeConversation.value ? activeConversation.value.quote : null; },
      set(val) { if (activeConversation.value) activeConversation.value.quote = val; },
    });

    // Autocomplete
    const autocompleteItems = ref([]);
    const autocompleteVisible = ref(false);
    const autocompleteIdx = ref(0);
    const autocompleteTarget = ref(null);  // 'chat' | 'query'
    const acPos = reactive({ top: 0, left: 0 });

    // Connection modal
    const showConnModal = ref(false);
    const connForm = reactive({
      id: '', name: '', type: 'mysql', host: '127.0.0.1', port: '3306',
      user: 'root', password: '', database: '', uri: '',
      ssh_enabled: false,
      ssh_host: '', ssh_port: '22', ssh_username: '', ssh_password: '', ssh_key_file: '',
    });
    const connFormError = ref('');

    // General error
    const globalError = ref('');

    // Console
    const consoleEntries = ref([]);
    const consoleBody = ref(null);

    // Theme
    const isDark = ref(true);
    function initTheme() {
      const saved = localStorage.getItem('openchatdb-theme');
      if (saved) {
        isDark.value = saved === 'dark';
      } else {
        isDark.value = window.matchMedia('(prefers-color-scheme: dark)').matches;
      }
      applyTheme();
    }
    function applyTheme() {
      document.documentElement.setAttribute('data-theme', isDark.value ? 'dark' : 'light');
    }
    function toggleTheme() {
      isDark.value = !isDark.value;
      applyTheme();
      localStorage.setItem('openchatdb-theme', isDark.value ? 'dark' : 'light');
    }

    // ---- Helpers ----
    function showError(msg) {
      globalError.value = msg;
      setTimeout(() => { globalError.value = ''; }, 5000);
    }

    // ---- Console helpers ----
    function logToConsole(text, type = 'info') {
      const now = new Date();
      const time = now.toLocaleTimeString('en-GB', { hour12: false });
      consoleEntries.value.push({ time, text, type });
      nextTick(() => {
        if (consoleBody.value) {
          consoleBody.value.scrollTop = consoleBody.value.scrollHeight;
        }
      });
    }

    function clearConsole() {
      consoleEntries.value = [];
    }

    // ---- Conversation management ----
    function generateConversationTitle(text) {
      const trimmed = text.trim();
      return trimmed.length > 30 ? trimmed.slice(0, 30) + '…' : trimmed;
    }

    function createConversation() {
      const conv = reactive({
        id: nextConversationId++,
        title: 'New Chat',
        messages: [],
        quote: null,
        createdAt: new Date(),
      });
      conversations.value.push(conv);
      activeConversationId.value = conv.id;
      chatInput.value = '';
      return conv;
    }

    function switchConversation(id) {
      activeConversationId.value = id;
      chatInput.value = '';
    }

    function deleteConversation(id) {
      const idx = conversations.value.findIndex(c => c.id === id);
      if (idx === -1) return;
      conversations.value.splice(idx, 1);
      if (activeConversationId.value === id) {
        if (conversations.value.length > 0) {
          // Switch to nearest conversation
          const newIdx = Math.min(idx, conversations.value.length - 1);
          activeConversationId.value = conversations.value[newIdx].id;
        } else {
          // Last one deleted — auto-create fresh
          createConversation();
        }
      }
    }

    function quoteToChat() {
      const sel = window.getSelection();
      const text = sel ? sel.toString().trim() : '';
      if (!text) return;
      const preview = text.length > 60 ? text.slice(0, 60) + '…' : text;
      if (!activeConversation.value) createConversation();
      activeConversation.value.quote = { text, preview };
      chatOpen.value = true;
      nextTick(() => {
        const el = document.querySelector('.chat-input-wrap textarea');
        if (el) el.focus();
      });
    }

    function dismissQuote() {
      if (activeConversation.value) activeConversation.value.quote = null;
    }

    // ---- Connection CRUD ----
    async function loadConnections() {
      try {
        connections.value = await API.listConnections();
      } catch (e) { showError(e.message); }
    }

    function openNewConnModal() {
      Object.assign(connForm, {
        id: '', name: '', type: 'mysql', host: '127.0.0.1', port: '3306',
        user: 'root', password: '', database: '', uri: '',
        ssh_enabled: false, ssh_host: '', ssh_port: '22', ssh_username: '', ssh_password: '', ssh_key_file: '',
      });
      connFormError.value = '';
      showConnModal.value = true;
    }

    function editConnection(conn) {
      Object.assign(connForm, {
        id: conn.id, name: conn.name || '', type: conn.type || 'mysql',
        host: conn.host || '127.0.0.1', port: String(conn.port || '3306'),
        user: conn.user || '', password: '', database: conn.database || '', uri: conn.uri || '',
        ssh_enabled: !!(conn.ssh && conn.ssh.host),
        ssh_host: conn.ssh?.host || '', ssh_port: String(conn.ssh?.port || '22'),
        ssh_username: conn.ssh?.username || '', ssh_password: '', ssh_key_file: conn.ssh?.key_file || '',
      });
      connFormError.value = '';
      showConnModal.value = true;
    }

    function onTypeChange() {
      const defaults = { mysql: '3306', mongodb: '27017', elasticsearch: '9200' };
      connForm.port = defaults[connForm.type] || '3306';
    }

    async function saveConnection() {
      const cfg = {
        name: connForm.name || `${connForm.type}@${connForm.host}`,
        type: connForm.type,
        host: connForm.host,
        port: parseInt(connForm.port) || 3306,
        user: connForm.user,
        password: connForm.password,
        database: connForm.database,
      };
      if (connForm.type === 'mongodb' && connForm.uri) {
        cfg.uri = connForm.uri;
      }
      if (connForm.ssh_enabled) {
        cfg.ssh = {
          host: connForm.ssh_host,
          port: parseInt(connForm.ssh_port) || 22,
          username: connForm.ssh_username,
          password: connForm.ssh_password,
          key_file: connForm.ssh_key_file,
        };
      }
      try {
        if (connForm.id) {
          await API.updateConnection(connForm.id, cfg);
        } else {
          await API.createConnection(cfg);
        }
        showConnModal.value = false;
        await loadConnections();
      } catch (e) {
        connFormError.value = e.message;
      }
    }

    async function testConn() {
      const cfg = {
        type: connForm.type, host: connForm.host, port: parseInt(connForm.port),
        user: connForm.user, password: connForm.password, database: connForm.database,
      };
      if (connForm.type === 'mongodb' && connForm.uri) cfg.uri = connForm.uri;
      if (connForm.ssh_enabled) {
        cfg.ssh = { host: connForm.ssh_host, port: parseInt(connForm.ssh_port), username: connForm.ssh_username, password: connForm.ssh_password, key_file: connForm.ssh_key_file };
      }
      try {
        const r = await API.testConnection(cfg);
        if (r.ok) { connFormError.value = ''; alert('Connection successful!'); }
        else connFormError.value = r.error || 'Connection failed';
      } catch (e) { connFormError.value = e.message; }
    }

    async function deleteConn(conn) {
      if (!confirm(`Delete connection "${conn.name}"?`)) return;
      try {
        await API.deleteConnection(conn.id);
        if (activeConn.value?.id === conn.id) {
          activeConn.value = null; databases.value = []; tables.value = []; activeDb.value = null; activeTable.value = null;
        }
        await loadConnections();
      } catch (e) { showError(e.message); }
    }

    // ---- Connect / Disconnect ----
    async function toggleConnect(conn) {
      try {
        if (conn.connected) {
          await API.disconnect(conn.id);
        } else {
          await API.connect(conn.id);
          activeConn.value = conn;
          expandedConns[conn.id] = true;
          await loadDatabases(conn.id);
        }
        await loadConnections();
      } catch (e) { showError(e.message); }
    }

    // ---- Database browsing ----
    async function loadDatabases(connId) {
      try {
        databases.value = await API.listDatabases(connId);
      } catch (e) { showError(e.message); }
    }

    async function selectDatabase(connId, db) {
      activeConn.value = connections.value.find(c => c.id === connId) || activeConn.value;
      activeDb.value = db;
      activeTable.value = null;
      tableData.value = null;
      expandedDbs[`${connId}:${db}`] = !expandedDbs[`${connId}:${db}`];
      try {
        tables.value = await API.listTables(connId, db);
        // Auto index schema
        await API.indexSchema(connId, db);
      } catch (e) { showError(e.message); }
    }

    async function selectTable(table) {
      activeTable.value = table;
      activeTab.value = 'data';
      dataPage.value = 1;
      await loadTableData();
    }

    async function loadTableData() {
      if (!activeConn.value || !activeDb.value || !activeTable.value) return;
      dataLoading.value = true;
      try {
        tableData.value = await API.browseData(
          activeConn.value.id, activeDb.value, activeTable.value, dataPage.value
        );
      } catch (e) { showError(e.message); }
      dataLoading.value = false;
    }

    async function loadStructure() {
      if (!activeConn.value || !activeDb.value || !activeTable.value) return;
      structureLoading.value = true;
      try {
        tableStructure.value = await API.tableStructure(activeConn.value.id, activeDb.value, activeTable.value);
        tableIndexes.value = await API.tableIndexes(activeConn.value.id, activeDb.value, activeTable.value);
      } catch (e) { showError(e.message); }
      structureLoading.value = false;
    }

    function nextPage() { dataPage.value++; loadTableData(); }
    function prevPage() { if (dataPage.value > 1) { dataPage.value--; loadTableData(); } }

    // ---- Tab switching ----
    function switchTab(tab) {
      activeTab.value = tab;
      if (tab === 'structure' && activeTable.value) loadStructure();
    }

    function editInQueryTab(query) {
      queryText.value = query;
      queryResult.value = null;
      queryError.value = '';
      needsConfirmation.value = false;
      activeTab.value = 'query';
    }

    // ---- Query execution ----
    async function runQuery() {
      if (!activeConn.value || !queryText.value.trim()) return;
      const sql = queryText.value.trim();
      queryLoading.value = true;
      queryError.value = '';
      queryResult.value = null;
      needsConfirmation.value = false;
      logToConsole(`Executing: ${sql}`, 'info');
      try {
        const r = await API.executeQuery(activeConn.value.id, activeDb.value, sql);
        if (r.needs_confirmation) {
          needsConfirmation.value = true;
          queryError.value = r.message;
          logToConsole('Write operation detected — awaiting confirmation', 'warn');
        } else {
          queryResult.value = r;
          if (r.affected_rows !== undefined) {
            logToConsole(`OK — ${r.affected_rows} affected rows`, 'success');
          } else if (r.rows) {
            logToConsole(`OK — ${r.rowcount} rows returned`, 'success');
          }
        }
      } catch (e) {
        queryError.value = e.message;
        logToConsole(`Error: ${e.message}`, 'error');
      }
      queryLoading.value = false;
    }

    async function confirmQuery() {
      const sql = queryText.value.trim();
      queryLoading.value = true;
      queryError.value = '';
      needsConfirmation.value = false;
      logToConsole(`Confirmed write: ${sql}`, 'info');
      try {
        queryResult.value = await API.executeQuery(activeConn.value.id, activeDb.value, sql, true);
        if (queryResult.value.affected_rows !== undefined) {
          logToConsole(`OK — ${queryResult.value.affected_rows} affected rows`, 'success');
        } else if (queryResult.value.rows) {
          logToConsole(`OK — ${queryResult.value.rowcount} rows returned`, 'success');
        }
      } catch (e) {
        queryError.value = e.message;
        logToConsole(`Error: ${e.message}`, 'error');
      }
      queryLoading.value = false;
    }

    // ---- Chat ----
    async function sendChat() {
      const text = chatInput.value.trim();
      if (!text || !activeConn.value || !activeDb.value) return;

      // Auto-create conversation if none
      if (!activeConversation.value) createConversation();
      const conv = activeConversation.value;

      // Capture and clear quote attachment
      const quote = conv.quote;
      conv.quote = null;

      // Auto-title on first user message
      if (!conv.messages.length) {
        conv.title = generateConversationTitle(text);
      }

      conv.messages.push({
        role: 'user', content: text,
        _quote: quote ? quote.text : null,
        _quotePreview: quote ? quote.preview : null,
        _quoteExpanded: false,
      });
      chatInput.value = '';
      chatLoading.value = true;

      // Push an empty streaming assistant message
      const assistantMsg = reactive({
        role: 'assistant', content: '', query: null, query_lang: null, is_write: false,
        _streaming: true,
      });
      conv.messages.push(assistantMsg);

      const scrollToBottom = () => {
        nextTick(() => {
          const el = document.querySelector('.chat-messages');
          if (el) el.scrollTop = el.scrollHeight;
        });
      };

      try {
        const msgs = conv.messages
          .filter(m => (m.role === 'user' || m.role === 'assistant') && m.content)
          .map(m => {
            let content = m.content;
            if (m._quote) {
              content = `[Referenced content]\n\`\`\`\n${m._quote}\n\`\`\`\n\n${content}`;
            }
            return { role: m.role, content };
          });
        // Remove last (empty assistant) from API messages
        if (msgs.length && msgs[msgs.length - 1].role === 'assistant' && !msgs[msgs.length - 1].content) {
          msgs.pop();
        }

        await API.sendChatStream(activeConn.value.id, activeDb.value, msgs, {
          onToken(token) {
            assistantMsg.content += token;
            scrollToBottom();
          },
          onDone(data) {
            assistantMsg.content = data.content;
            assistantMsg.query = data.query;
            assistantMsg.query_lang = data.query_lang;
            assistantMsg.is_write = data.is_write;
            assistantMsg._streaming = false;
          },
          onError(msg) {
            assistantMsg.content += `\nError: ${msg}`;
            assistantMsg._streaming = false;
          },
        });
      } catch (e) {
        assistantMsg.content = `Error: ${e.message}`;
        assistantMsg._streaming = false;
      }
      chatLoading.value = false;
      scrollToBottom();
    }

    async function executeChatQuery(msg) {
      if (msg.is_write && !confirm('This is a write operation. Proceed?')) return;
      msg._executing = true;
      logToConsole(`Chat query: ${msg.query}`, 'info');
      try {
        const r = await API.executeChatQuery(activeConn.value.id, activeDb.value, msg.query);
        msg._result = r;
        if (r.affected_rows !== undefined) {
          logToConsole(`OK — ${r.affected_rows} affected rows`, 'success');
        } else if (r.rows) {
          logToConsole(`OK — ${r.rowcount} rows returned`, 'success');
        }
      } catch (e) {
        msg._error = e.message;
        logToConsole(`Error: ${e.message}`, 'error');
      }
      msg._executing = false;
    }

    function handleAutocompleteKeydown(e) {
      if (e.key === 'ArrowDown') { e.preventDefault(); autocompleteIdx.value = Math.min(autocompleteIdx.value + 1, autocompleteItems.value.length - 1); return true; }
      if (e.key === 'ArrowUp') { e.preventDefault(); autocompleteIdx.value = Math.max(autocompleteIdx.value - 1, 0); return true; }
      if (e.key === 'Enter' || e.key === 'Tab') { e.preventDefault(); acceptAutocomplete(); return true; }
      if (e.key === 'Escape') { autocompleteVisible.value = false; return true; }
      return false;
    }

    function chatKeydown(e) {
      if (autocompleteVisible.value && handleAutocompleteKeydown(e)) return;
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendChat();
      }
    }

    function queryKeydown(e) {
      if (autocompleteVisible.value && handleAutocompleteKeydown(e)) return;
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        runQuery();
      }
    }

    // ---- Autocomplete ----
    function onChatInput(e) {
      chatInput.value = e.target.value;
      checkAutocomplete(e.target, 'chat');
    }

    function onQueryInput(e) {
      queryText.value = e.target.value;
      checkAutocomplete(e.target, 'query');
    }

    async function checkAutocomplete(el, target) {
      const val = el.value;
      const pos = el.selectionStart;
      // Look back for @ or #
      let triggerIdx = -1;
      let kind = 'all';
      for (let i = pos - 1; i >= 0; i--) {
        if (val[i] === '@') { triggerIdx = i; kind = 'table'; break; }
        if (val[i] === '#') { triggerIdx = i; kind = 'field'; break; }
        if (/\s/.test(val[i])) break;
      }
      if (triggerIdx < 0 || !activeConn.value || !activeDb.value) {
        autocompleteVisible.value = false;
        return;
      }
      const query = val.slice(triggerIdx + 1, pos);
      autocompleteTarget.value = target;

      // For # (field), find the most recent @tablename to scope fields
      let scopeTable = '';
      if (kind === 'field') {
        const textBefore = val.slice(0, triggerIdx);
        const tableMatches = textBefore.match(/@(\w+)/g);
        if (tableMatches) {
          scopeTable = tableMatches[tableMatches.length - 1].slice(1);
        } else if (activeTable.value) {
          scopeTable = activeTable.value;
        }
      }

      try {
        autocompleteItems.value = await API.searchSchema(activeConn.value.id, activeDb.value, query, kind, scopeTable);
        if (autocompleteItems.value.length > 0) {
          autocompleteVisible.value = true;
          autocompleteIdx.value = 0;
          // Position above the textarea (dropdown appears upward)
          const rect = el.getBoundingClientRect();
          acPos.top = rect.top - 4;
          acPos.left = rect.left;
        } else {
          autocompleteVisible.value = false;
        }
      } catch { autocompleteVisible.value = false; }
    }

    function acceptAutocomplete() {
      if (!autocompleteItems.value.length) return;
      const item = autocompleteItems.value[autocompleteIdx.value];
      const target = autocompleteTarget.value;
      const ref_val = target === 'chat' ? chatInput : queryText;
      const el = document.querySelector(target === 'chat' ? '.chat-input-wrap textarea' : '.query-editor-area textarea');
      if (!el) return;
      const val = ref_val.value;
      const pos = el.selectionStart;
      // Find trigger position
      let triggerIdx = -1;
      for (let i = pos - 1; i >= 0; i--) {
        if (val[i] === '@' || val[i] === '#') { triggerIdx = i; break; }
        if (/\s/.test(val[i])) break;
      }
      if (triggerIdx < 0) { autocompleteVisible.value = false; return; }
      const prefix = val[triggerIdx];
      const insert = item.display;
      const newVal = val.slice(0, triggerIdx) + prefix + insert + ' ' + val.slice(pos);
      const cursorPos = triggerIdx + prefix.length + insert.length + 1;
      ref_val.value = newVal;
      autocompleteVisible.value = false;
      nextTick(() => {
        el.value = newVal;
        el.selectionStart = el.selectionEnd = cursorPos;
        el.focus();
      });
    }

    // ---- Format helpers ----
    function formatValue(v) {
      if (v === null || v === undefined) return 'NULL';
      if (typeof v === 'object') return JSON.stringify(v);
      return String(v);
    }

    function renderMarkdown(text) {
      // Minimal markdown: code blocks, inline code, bold
      let html = text
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
      return html;
    }

    // ---- Lifecycle ----
    onMounted(() => {
      initTheme();
      loadConnections();
      createConversation();
    });

    // When clicking outside autocomplete, close it
    document.addEventListener('click', (e) => {
      if (!e.target.closest('.autocomplete')) {
        autocompleteVisible.value = false;
      }
    });

    return {
      connections, activeConn, databases, activeDb, tables, activeTable,
      expandedConns, expandedDbs, activeTab,
      tableData, dataPage, dataLoading,
      tableStructure, tableIndexes, structureLoading,
      queryText, queryResult, queryLoading, queryError, needsConfirmation,
      chatOpen, chatMessages, chatInput, chatLoading,
      conversations, activeConversationId,
      autocompleteItems, autocompleteVisible, autocompleteIdx, acPos,
      showConnModal, connForm, connFormError, globalError, isDark,
      consoleEntries, consoleBody,
      chatQuote, structureColumns,
      // methods
      loadConnections, openNewConnModal, editConnection, saveConnection, testConn, deleteConn,
      toggleTheme, onTypeChange, toggleConnect, loadDatabases, selectDatabase, selectTable,
      loadTableData, loadStructure, nextPage, prevPage, switchTab,
      runQuery, confirmQuery, editInQueryTab, sendChat, executeChatQuery,
      chatKeydown, queryKeydown, onChatInput, onQueryInput, acceptAutocomplete,
      formatValue, renderMarkdown,
      logToConsole, clearConsole, quoteToChat, dismissQuote,
      createConversation, switchConversation, deleteConversation,
    };
  },
});

app.mount('#app');
