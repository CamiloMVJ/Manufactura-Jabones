/* ESPUMA ERP: sesión, navegación, tablas y formularios compartidos. */
(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const page = document.body.dataset.page;
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const money = (value) => 'C$ ' + Number(value || 0).toLocaleString('es-NI', {minimumFractionDigits:2, maximumFractionDigits:2});
  const num = (value) => Number(value || 0).toLocaleString('es-NI');
  const countLabel = (value, singular, plural) => num(value)+' '+(value === 1 ? singular : plural);
  const date = (value) => new Date(value).toLocaleDateString('es-NI', {day:'2-digit',month:'short',year:'numeric'});
  const statusNames = {pendiente:'Pendiente', preparado:'Preparado', en_ruta:'En ruta', entregado:'Entregado'};
  const statusClasses = {pendiente:'warning', preparado:'purple', en_ruta:'info', entregado:'success'};
  const nextStatus = {pendiente:'preparado', preparado:'en_ruta', en_ruta:'entregado'};
  const roleNames = {administrador:'Administrador', vendedor:'Vendedor', repartidor:'Repartidor'};
  const paths = {plus:'M12 5v14 M5 12h14',edit:'m16 3 5 5-12 12-6 1 1-6L16 3z M13 6l5 5',trash:'M3 6h18 M9 6V3h6v3 M5 6l1 15h12l1-15 M10 10v7 M14 10v7',eye:'M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7z M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0',box:'m12 3 9 5-9 5-9-5 9-5z M3 8v9l9 5 9-5V8 M12 13v9',clock:'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0 M12 7v5l3 2',check:'m5 12 4 4L19 6',close:'m6 6 12 12 M6 18 18 6'};
  const icon = (name) => `<svg class="icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[name] || paths.box}"/></svg>`;
  const badge = (status) => `<span class="badge badge-${statusClasses[status] || 'neutral'}">${esc(statusNames[status] || status)}</span>`;
  const actionButton = (action, id, label, symbol, extra='') => `<button class="icon-button ${extra}" data-action="${action}" data-id="${id}" title="${esc(label)}" aria-label="${esc(label)}">${icon(symbol)}</button>`;
  let user, rows = [], products = [], clients = [], currentPage = 1, editingId = null;
  let mode = '', loading = false, reloadRequested = false, socket, reconnectTimer, refreshTimer, reconnectCount = 0, leaving = false, confirmCallback;
  const canWrite = () => ['administrador','vendedor'].includes(user?.role);

  function logout() {
    leaving = true;
    clearTimeout(reconnectTimer);
    socket?.close();
    ['erp_token','erp_user'].forEach((key) => { sessionStorage.removeItem(key); localStorage.removeItem(key); });
    location.assign('/login');
  }
  async function api(url, options = {}) {
    const token = sessionStorage.getItem('erp_token');
    if (!token && page !== 'login') { logout(); throw new Error('Inicia sesión para continuar.'); }
    let response;
    try {
      response = await fetch(url, {...options, headers:{...(options.body ? {'Content-Type':'application/json'} : {}), ...options.headers, ...(token ? {Authorization:`Bearer ${token}`} : {})}, signal:options.signal || AbortSignal.timeout(20000)});
    } catch (error) { throw new Error(error.name === 'TimeoutError' ? 'El servidor tardó demasiado. Intenta de nuevo.' : 'No se pudo conectar. Revisa tu conexión y vuelve a intentar.'); }
    if (response.status === 401 && page !== 'login') { logout(); throw new Error('Tu sesión expiró. Vuelve a ingresar.'); }
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      const detail = Array.isArray(data.detail) ? data.detail.map((item) => `${item.loc?.slice(1).join('.') || 'Datos'}: ${item.msg}`).join('\n') : data.detail;
      throw new Error(detail || `No se pudo completar la operación (${response.status}).`);
    }
    return response;
  }
  const json = async (url, options) => (await api(url, options)).json();
  function toast(message, error = false) {
    const node = document.createElement('div'); node.className = 'toast' + (error ? ' error' : ''); node.textContent = message;
    $('toasts')?.append(node); setTimeout(() => node.remove(), 6000);
  }
  function setError(id, message) { const node = $(id); node.textContent = message || ''; node.hidden = !message; }
  function pageError(message) { $('page-error').hidden = !message; $('page-error-text').textContent = message || ''; }
  function setBusy(button, busy, label='Guardando…') {
    if (!button) return;
    if (busy) { button.dataset.original = button.innerHTML; button.textContent = label; }
    else if (button.dataset.original) button.innerHTML = button.dataset.original;
    button.disabled = busy;
  }

  function initLogin() {
    $('toggle-password').addEventListener('click', () => {
      const reveal = $('password').type === 'password'; $('password').type = reveal ? 'text' : 'password';
      $('toggle-password').setAttribute('aria-label', reveal ? 'Ocultar contraseña' : 'Mostrar contraseña');
      $('toggle-password').setAttribute('aria-pressed', String(reveal));
    });
    $('login-form').addEventListener('submit', async (event) => {
      event.preventDefault(); setError('login-error', ''); setBusy($('login-button'), true, 'Validando acceso…');
      try {
        const response = await fetch('/auth/login', {method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({username:$('username').value.trim(),password:$('password').value}),signal:AbortSignal.timeout(20000)});
        const data = await response.json();
        if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Revisa tus credenciales.');
        sessionStorage.setItem('erp_token', data.access_token); sessionStorage.setItem('erp_user', $('username').value.trim());
        location.assign('/');
      } catch (error) { setError('login-error', error instanceof TypeError || error.name === 'TimeoutError' ? 'No se pudo conectar con el servidor. Intenta de nuevo.' : error.message); }
      finally { setBusy($('login-button'), false); }
    });
  }

  function initShell() {
    $('today-label').textContent = new Date().toLocaleDateString('es-NI', {day:'numeric',month:'long',year:'numeric'});
    const isMobile = () => matchMedia('(max-width:700px)').matches;
    try { document.body.classList.toggle('sidebar-collapsed', localStorage.getItem('fridays_sidebar') === 'collapsed'); } catch (_) { /* Preferencia opcional. */ }
    const updateExpanded = () => {
      const expanded = isMobile() ? document.body.classList.contains('drawer-open') : !document.body.classList.contains('sidebar-collapsed');
      $('sidebar-toggle').setAttribute('aria-expanded', String(expanded));
      $('sidebar-toggle').setAttribute('aria-label', expanded ? 'Contraer navegación' : 'Abrir navegación');
      $('sidebar').inert = isMobile() && !expanded;
      $('drawer-shade').hidden = !isMobile() || !expanded;
    };
    function closeDrawer() { document.body.classList.remove('drawer-open'); updateExpanded(); }
    $('sidebar-toggle').addEventListener('click', () => {
      if (isMobile()) document.body.classList.toggle('drawer-open');
      else {
        document.body.classList.toggle('sidebar-collapsed');
        try { localStorage.setItem('fridays_sidebar', document.body.classList.contains('sidebar-collapsed') ? 'collapsed' : 'expanded'); } catch (_) { /* Preferencia opcional. */ }
      }
      updateExpanded();
    });
    $('drawer-shade').addEventListener('click', closeDrawer);
    document.addEventListener('keydown', (event) => { if (event.key === 'Escape') { closeDrawer(); $('notification-panel').hidden = true; $('notifications-button').setAttribute('aria-expanded','false'); } });
    matchMedia('(max-width:700px)').addEventListener('change', updateExpanded); updateExpanded();
    $('notifications-button').addEventListener('click', () => { $('notification-panel').hidden = !$('notification-panel').hidden; $('notifications-button').setAttribute('aria-expanded', String(!$('notification-panel').hidden)); });
    document.addEventListener('click', (event) => { if (!event.target.closest('#notification-panel, #notifications-button')) { $('notification-panel').hidden = true; $('notifications-button').setAttribute('aria-expanded', 'false'); } });
    $('user-avatar').textContent = user.username.slice(0,2).toUpperCase();
    $('user-avatar').title = `${user.username} · ${roleNames[user.role] || user.role}`;
    document.querySelectorAll('[data-module-filter]').forEach((button) => button.addEventListener('click', () => {
      const filter = button.dataset.moduleFilter;
      document.querySelectorAll('[data-module-filter]').forEach((node) => {const selected = node === button; node.classList.toggle('selected',selected); node.setAttribute('aria-pressed',String(selected));});
      document.querySelectorAll('[data-module]').forEach((tile) => {tile.hidden = (filter !== 'all' && tile.dataset.module !== filter) || (tile.hasAttribute('data-finance') && !canWrite());});
    }));
    document.querySelectorAll('[data-write]').forEach((node) => { node.hidden = !canWrite(); });
    document.querySelectorAll('[data-finance]').forEach((node) => {node.hidden = !canWrite();});
    document.querySelectorAll('[data-admin]').forEach((node) => {node.hidden = user.role !== 'administrador';});
    workspace.init();
    window.addEventListener('pagehide', () => { leaving = true; clearTimeout(reconnectTimer); socket?.close(); });
    window.addEventListener('pageshow', (event) => { if (event.persisted) { leaving = false; connect(); load(); } });
    document.addEventListener('visibilitychange', () => { if (!document.hidden && !leaving) load(); });
  }

  async function load() {
    if (leaving) return;
    if (loading) { reloadRequested = true; return; }
    loading = true; pageError('');
    document.querySelectorAll('[data-action="reload"]').forEach((b) => setBusy(b,true,'Actualizando…'));
    try {
      if (page === 'dashboard') await loadDashboard();
      else if (page === 'finance') await workspace.loadFinance();
      else if (page === 'profile') renderProfile();
      else if ($('table-search')) await loadList();
      await loadAlerts();
      $('last-updated').textContent = 'Actualizado a las ' + new Date().toLocaleTimeString('es-NI', {hour:'2-digit',minute:'2-digit'});
    } catch (error) {
      pageError(error.message);
      if ($('table-body') && !rows.length) $('table-body').innerHTML = '<tr><td colspan="7" class="empty-cell">No se pudieron cargar los registros. Usa Reintentar para volver a consultar.</td></tr>';
      $('last-updated').textContent = 'No se pudo actualizar';
    } finally {
      loading = false;
      document.querySelectorAll('[data-action="reload"]').forEach((b) => setBusy(b,false));
      if (reloadRequested) { reloadRequested = false; setTimeout(load,0); }
    }
  }
  async function loadAlerts() {
    const stats = await json('/reports/dashboard');
    $('notification-summary').textContent = stats.low_stock_alert ? `${stats.low_stock_alert} productos tienen menos de 10 unidades. Revisa las existencias para preparar tu próxima compra.` : 'Tus existencias están al día. No hay productos con stock bajo.';
    $('notification-dot').hidden = !stats.low_stock_alert;
  }
  async function loadDashboard() {
    const [stats, orders, low, trend, activity] = await Promise.all(['/reports/dashboard','/reports/recent-orders','/reports/low-stock','/reports/sales-trend','/reports/activity'].map((url) => json(url)));
    [['sales',money(stats.total_sales)],['orders',num(stats.orders_today)],['clients',num(stats.total_clients)],['stock',num(stats.low_stock_alert)]].forEach(([key,value]) => { $('kpi-'+key).textContent = value; $('kpi-'+key).classList.remove('skeleton'); });
    $('pending-summary').textContent = stats.pending_orders ? `Tienes ${num(stats.pending_orders)} pedidos por completar. Acompaña cada entrega desde aquí.` : 'No hay pedidos pendientes. Tu operación está al día.';
    $('dispatch-total').textContent = num(stats.pending_orders);
    const counts = stats.orders_by_status || {};
    $('dispatch-stages').innerHTML = ['pendiente','preparado','en_ruta'].map((status) => `<div><span class="stage-dot stage-${status}"></span><span>${statusNames[status]}</span><strong>${num(counts[status] || 0)}</strong></div>`).join('');
    $('module-products').textContent = countLabel(stats.total_products,'producto registrado','productos registrados');
    $('module-clients').textContent = countLabel(stats.total_clients,'cliente registrado','clientes registrados');
    $('module-orders').textContent = countLabel(Object.values(counts).reduce((n,c) => n+c,0),'pedido registrado','pedidos registrados');
    if ($('module-dispatch')) $('module-dispatch').textContent = countLabel(counts.en_ruta || 0,'pedido en ruta','pedidos en ruta');
    if ($('module-reports')) $('module-reports').textContent = countLabel(stats.low_stock_alert,'producto en alerta','productos en alerta');
    $('recent-orders').innerHTML = orders.length ? orders.map((o) => `<tr><td><strong>#${String(o.id).padStart(4,'0')}</strong></td><td>${esc(o.client)}</td><td>${esc(o.date)}</td><td class="numeric"><strong>${money(o.total)}</strong></td><td>${badge(o.status)}</td><td>${actionButton('view',o.id,'Ver pedido '+o.id,'eye')}</td></tr>`).join('') : '<tr><td colspan="6" class="empty-cell"><strong>Tu próximo pedido empieza aquí</strong>Registra clientes y productos para crear tu primera venta.</td></tr>';
    $('week-total').textContent = money(trend.reduce((sum,d) => sum+d.total,0));
    const max = Math.max(1,...trend.map((d) => d.total));
    $('sales-chart').innerHTML = trend.map((d) => { const label = new Date(d.date+'T12:00:00').toLocaleDateString('es-NI',{weekday:'short'}); const detail = date(d.date+'T12:00:00')+': '+money(d.total); return `<div class="chart-day" tabindex="0" title="${esc(detail)}" aria-label="${esc(detail)}"><div class="chart-bar" style="height:${Math.max(2,Math.round(d.total/max*115))}px"></div><span>${esc(label)}</span></div>`; }).join('');
    $('low-stock-list').innerHTML = low.length ? low.slice(0,4).map((p) => `<a class="stock-row" href="/productos?filter=low"><span class="item-icon">${icon('box')}</span><div><strong>${esc(p.name)}</strong><small>${esc(p.category)}</small></div><span class="badge badge-${p.stock === 0 ? 'danger' : 'warning'}">${p.stock} uds.</span></a>`).join('') : '<p class="empty-inline">Inventario en orden. No hay alertas de stock.</p>';
    $('activity-list').innerHTML = activity.length ? activity.slice(0,4).map((a) => `<div class="activity-row"><span class="item-icon">${icon('clock')}</span><div><strong>${esc(a.details || a.entity+' · '+a.action)}</strong><small>${esc(date(a.date))} · ${esc(new Date(a.date).toLocaleTimeString('es-NI',{hour:'2-digit',minute:'2-digit'}))}</small></div></div>`).join('') : '<p class="empty-inline">Los próximos movimientos de tu equipo aparecerán aquí.</p>';
    await workspace.renderDashboard();
  }

  async function loadList() {
    rows = await json(page === 'clients' ? '/clients/' : page === 'products' ? '/products/' : '/orders/?limit=1000');
    if (page === 'products') products = rows;
    if (page === 'clients') clients = rows;
    const oldFilter = $('table-filter').value;
    const filterOptions = page === 'products' ? [['all','Todos los productos'],['low','Stock bajo'],['available','Stock suficiente'],['empty','Sin existencias']] : page === 'clients' ? [['all','Todas las zonas'], ...[...new Set(rows.map((c) => c.zone || 'Sin zona'))].sort().map((z) => [z,z])] : [['all','Todos los estados'],...Object.entries(statusNames)];
    $('table-filter').innerHTML = filterOptions.map(([value,label]) => `<option value="${esc(value)}">${esc(label)}</option>`).join('');
    const initialFilter = new URLSearchParams(location.search).get('filter');
    $('table-filter').value = filterOptions.some(([v]) => v === oldFilter) ? oldFilter : 'all';
    if (initialFilter && !$('table-filter').dataset.initialized && filterOptions.some(([v]) => v === initialFilter)) $('table-filter').value = initialFilter;
    $('table-filter').dataset.initialized = '1';
    const summaries = page === 'products' ? [['Productos registrados',num(rows.length)],['Artículos con existencias',num(rows.filter(p => p.stock > 0).length)],['Valor a precios de catálogo',money(rows.reduce((n,p) => n+p.stock*p.price,0))]] : page === 'clients' ? [['Clientes registrados',num(rows.length)],['Zonas de entrega',num(new Set(rows.map((c) => c.zone).filter(Boolean)).size)],['Contactos registrados',num(rows.filter((c) => c.contact).length)]] : [['Pedidos consultados',num(rows.length)],['Importe registrado',money(rows.reduce((n,o) => n+o.total_amount,0))],['Pendientes de entrega',num(rows.filter((o) => o.status !== 'entregado').length)]];
    $('list-summary').innerHTML = summaries.map(([label,value]) => `<article class="kpi-card"><div class="kpi-top">${label}</div><strong class="kpi-value">${value}</strong></article>`).join('');
    $('record-count').textContent = num(rows.length);
    if (page === 'orders' || page === 'billing') $('table-context').textContent = 'Hasta 1,000 pedidos más recientes. Los importes corresponden a estos registros.';
    const headers = page === 'products' ? ['Producto','Categoría','Precio unitario','Existencias','Estado','Vencimiento','Acciones'] : page === 'clients' ? ['Cliente','Contacto','Zona','Correo electrónico','Dirección','Acciones'] : ['Pedido','Cliente','Fecha','Productos','Importe','Estado','Acciones'];
    $('table-head').innerHTML = '<tr>'+headers.map((h) => `<th scope="col">${h}</th>`).join('')+'</tr>';
    $('table-sort').options[1].textContent = page === 'orders' || page === 'billing' ? 'Cliente A–Z' : 'Nombre A–Z';
    $('table-sort').options[2].hidden = page === 'clients';
    renderTable();
  }
  function filteredRows() {
    const search = $('table-search').value.trim().toLocaleLowerCase();
    const filter = $('table-filter').value;
    const clientId = ['orders','billing'].includes(page) ? Number(new URLSearchParams(location.search).get('client')) : 0;
    let result = rows.filter((r) => {
      const haystack = page === 'products' ? [r.name,r.category,r.id] : page === 'clients' ? [r.name,r.contact,r.zone,r.email,r.address] : [r.id,r.client,statusNames[r.status]];
      const matches = haystack.join(' ').toLocaleLowerCase().includes(search);
      const condition = filter === 'all' || (page === 'products' ? filter === 'low' ? r.stock < 10 : filter === 'empty' ? r.stock === 0 : r.stock >= 10 : page === 'clients' ? (r.zone || 'Sin zona') === filter : r.status === filter);
      return matches && condition && (!clientId || r.client_id === clientId);
    });
    const sort = $('table-sort').value;
    if (sort === 'name') result.sort((a,b) => (a.name || a.client).localeCompare(b.name || b.client,'es'));
    else if (sort === 'amount') result.sort((a,b) => (b.price ?? b.total_amount) - (a.price ?? a.total_amount));
    else if (page === 'clients' || page === 'products') result.sort((a,b) => b.id-a.id);
    return result;
  }
  function renderTable() {
    const visible = filteredRows(), size = Number($('page-size').value), pages = Math.max(1,Math.ceil(visible.length/size));
    currentPage = Math.min(currentPage,pages);
    const start = (currentPage-1)*size;
    $('table-body').innerHTML = visible.length ? visible.slice(start,start+size).map(renderRow).join('') : `<tr><td colspan="7" class="empty-cell"><strong>${rows.length ? 'No encontramos coincidencias' : 'Aún no hay registros'}</strong>${rows.length ? 'Prueba otra búsqueda o cambia los filtros.' : 'Los nuevos registros aparecerán aquí.'}</td></tr>`;
    $('pagination-label').textContent = visible.length ? `${start+1}–${Math.min(start+size,visible.length)} de ${visible.length} registros` : '0 registros';
    $('page-number').textContent = `${currentPage} / ${pages}`;
    $('previous-page').disabled = currentPage === 1; $('next-page').disabled = currentPage === pages;
    workspace.renderKanban();
  }
  function renderRow(r) {
    if (page === 'products') return `<tr><td><strong>${esc(r.name)}</strong><span class="table-subtext">PRD-${String(r.id).padStart(4,'0')}</span></td><td>${esc(r.category || 'Sin categoría')}</td><td class="numeric">${money(r.price)}</td><td class="numeric"><strong>${num(r.stock)}</strong> ${r.name.endsWith('[g]') ? 'g' : 'u'}</td><td><span class="badge badge-${r.stock === 0 ? 'danger' : r.stock < 10 ? 'warning' : 'success'}">${r.stock === 0 ? 'Sin existencias' : r.stock < 10 ? 'Stock bajo' : 'Disponible'}</span></td><td>${r.expiry_date ? esc(date(r.expiry_date+'T12:00:00')) : '—'}</td><td><div class="row-actions">${canWrite() ? actionButton('edit',r.id,'Editar '+r.name,'edit') : '<span class="table-subtext">Solo lectura</span>'}${user.role === 'administrador' ? actionButton('delete',r.id,'Eliminar '+r.name,'trash','danger-icon') : ''}</div></td></tr>`;
    if (page === 'clients') return `<tr><td><strong>${esc(r.name)}</strong><span class="table-subtext">CLI-${String(r.id).padStart(4,'0')}</span></td><td>${esc(r.contact || 'Sin contacto')}</td><td><span class="badge badge-neutral">${esc(r.zone || 'Sin zona')}</span></td><td>${esc(r.email)}</td><td>${esc(r.address || '—')}</td><td><div class="row-actions">${canWrite() ? actionButton('edit',r.id,'Editar '+r.name,'edit') : ''}${actionButton('client-history',r.id,'Ver pedidos de '+r.name,'clock')}</div></td></tr>`;
    return `<tr><td><strong>#${String(r.id).padStart(4,'0')}</strong></td><td>${esc(r.client)}</td><td>${esc(date(r.date))}</td><td>${r.items.reduce((n,i) => n+i.quantity,0)} uds. <span class="table-subtext">${r.items.length} referencias</span></td><td class="numeric"><strong>${money(r.total_amount)}</strong></td><td>${badge(r.status)}</td><td><div class="row-actions">${actionButton('view',r.id,'Ver pedido '+r.id,'eye')}${page === 'orders' && nextStatus[r.status] && !(user.role === 'repartidor' && r.status === 'pendiente') ? `<button class="status-button" data-action="advance" data-id="${r.id}">Marcar ${statusNames[nextStatus[r.status]].toLowerCase()}</button>` : ''}</div></td></tr>`;
  }

  const field = (label, name, value='', type='text', required=false, extra='') => `<label class="field">${label}${required ? ' *' : ''}<input name="${name}" type="${type}" value="${esc(value)}" ${required ? 'required' : ''} ${extra}></label>`;
  async function openForm(id=null) {
    if (!canWrite()) throw new Error('Tu rol tiene acceso de consulta.');
    mode = page === 'clients' ? 'client' : page === 'products' ? 'product' : 'order';
    editingId = id; $('entity-form').reset(); setError('form-error','');
    const r = rows.find((r) => r.id === id) || {};
    $('dialog-title').textContent = `${id ? 'Editar' : 'Nuevo'} ${mode === 'client' ? 'cliente' : mode === 'product' ? 'producto' : 'pedido'}`;
    if (mode === 'product') {
      $('dialog-body').innerHTML = `<p class="form-section-title">INFORMACIÓN DEL PRODUCTO</p><div class="form-grid"><div class="full-width">${field('Nombre del producto','name',r.name,'text',true,'maxlength="200" placeholder="Ej. Arroz de primera 25 kg"')}</div>${field('Categoría','category',r.category,'text',false,'maxlength="200" placeholder="Ej. Granos básicos"')}${field('Fecha de vencimiento','expiry_date',r.expiry_date,'date')}${field('Precio unitario (C$)','price',r.price ?? '','number',true,'min="0" step="0.01"')}${field('Existencias (unidades)','stock',r.stock ?? '','number',true,'min="0" step="1"')}</div>`;
    } else if (mode === 'client') {
      $('dialog-body').innerHTML = `<p class="form-section-title">DATOS COMERCIALES Y DE ENTREGA</p><div class="form-grid"><div class="full-width">${field('Nombre o razón social','name',r.name,'text',true,'maxlength="200" placeholder="Ej. Abarrotes El Centro"')}</div>${field('Correo electrónico','email',r.email,'email',true,'maxlength="200"')}${field('Persona de contacto','contact',r.contact,'text',false,'maxlength="200"')}${field('Zona de entrega','zone',r.zone,'text',false,'maxlength="200"')}<div class="full-width">${field('Dirección','address',r.address,'text',false,'maxlength="500"')}</div></div>`;
    } else {
      [clients,products] = await Promise.all([json('/clients/'),json('/products/')]);
      if (!clients.length || !products.some((p) => p.stock > 0)) throw new Error('Registra al menos un cliente y un producto con existencias antes de crear un pedido.');
      $('dialog-body').innerHTML = `<label class="field">Cliente *<select name="client_id" required><option value="">Selecciona un cliente</option>${clients.map((c) => `<option value="${c.id}">${esc(c.name)}${c.zone ? ' · '+esc(c.zone) : ''}</option>`).join('')}</select></label><div class="order-lines"><p class="form-section-title">PRODUCTOS DEL PEDIDO</p><div id="order-lines"></div><button class="btn btn-secondary" type="button" data-action="add-line">${icon('plus')} Agregar producto</button></div><div class="order-total"><span>Total del pedido</span><strong id="order-total">${money(0)}</strong></div><p class="receipt-note">Las existencias se validan y descuentan al guardar el pedido.</p>`;
      addLine();
    }
    $('form-dialog').showModal();
  }
  function addLine() {
    const node = document.createElement('div'); node.className = 'order-line';
    node.innerHTML = `<label class="field">Producto *<select name="product_id" required><option value="">Selecciona un producto</option>${products.filter((p) => p.stock > 0 && ['Jabones','Sales de baño','Accesorios','Kits'].includes(p.category)).map((p) => `<option value="${p.id}">${esc(p.name)} · ${money(p.price)} · ${p.stock} uds.</option>`).join('')}</select></label><label class="field">Cantidad *<input name="quantity" type="number" min="1" max="1000000" step="1" value="1" required></label><button class="icon-button danger-icon" type="button" data-action="remove-line" aria-label="Quitar producto">${icon('trash')}</button>`;
    $('order-lines').append(node); totalOrder();
  }
  function totalOrder() {
    let total = 0;
    document.querySelectorAll('.order-line').forEach((line) => {
      const product = products.find((p) => p.id === Number(line.querySelector('select').value));
      const quantity = line.querySelector('input'); quantity.max = product?.stock || 1000000;
      total += Math.round((product?.price || 0)*Math.max(0,Number(quantity.value))*100)/100;
    });
    if ($('order-total')) $('order-total').textContent = money(total);
  }
  async function saveForm(event) {
    event.preventDefault(); setError('form-error','');
    setBusy($('save-button'),true);
    try {
      let url, data;
      const values = Object.fromEntries(new FormData($('entity-form')));
      if (mode === 'product') { data = {...values,price:Number(values.price),stock:Number(values.stock),expiry_date:values.expiry_date || null,category:values.category || null}; url = '/products/'+(editingId || ''); }
      else if (mode === 'client') { data = values; url = '/clients/'+(editingId || ''); }
      else {
        data = {client_id:Number(values.client_id),items:[...document.querySelectorAll('.order-line')].map((line) => ({product_id:Number(line.querySelector('select').value),quantity:Number(line.querySelector('input').value)}))};
        if (!data.items.length) throw new Error('Agrega al menos un producto.');
        url = '/orders/';
      }
      await json(url,{method:editingId ? 'PUT' : 'POST',body:JSON.stringify(data)});
      $('form-dialog').close(); toast(mode === 'order' ? 'Pedido creado. Inventario actualizado.' : 'Registro guardado correctamente.');
      load();
    } catch (error) { setError('form-error',error.message); }
    finally { setBusy($('save-button'),false); }
  }

  async function viewOrder(id) {
    const order = await json('/orders/'+id);
    $('detail-title').textContent = 'Pedido #'+String(id).padStart(4,'0');
    $('detail-body').innerHTML = `<div class="receipt-heading"><div><h3>ESPUMA JABONERÍA</h3><p>Comprobante de pedido #${String(id).padStart(4,'0')}</p></div><div>${badge(order.status)}<p>${esc(date(order.date))}</p></div></div><div class="receipt-client"><strong>Cliente</strong>${esc(order.client)}</div><div class="table-scroll"><table><thead><tr><th>Producto</th><th>Cantidad</th><th>Precio unitario</th><th>Subtotal</th></tr></thead><tbody>${order.items.map((item) => `<tr><td>${esc(item.name)}</td><td>${item.quantity}</td><td>${money(item.subtotal/item.quantity)}</td><td>${money(item.subtotal)}</td></tr>`).join('')}</tbody></table></div><p class="receipt-total">Total: ${money(order.total_amount)}</p><p class="receipt-note">Comprobante de pedido. Los importes corresponden a la venta registrada. No acredita pago ni sustituye una factura fiscal.</p>`;
    $('detail-body').insertAdjacentHTML('beforeend',workspace.timeline(order)+(canWrite() ? `<div class="detail-finance-action no-print"><span>Cobros y entregas se registran por separado.</span><button class="btn btn-secondary" data-action="new-payment" data-id="${order.id}">Registrar cobro</button></div>` : ''));
    $('detail-dialog').showModal();
  }
  async function exportStock() {
    const response = await api('/reports/export/pdf');
    const blob = await response.blob(); const url = URL.createObjectURL(blob);
    const link = document.createElement('a'); link.href = url; link.download = 'fridays-stock-bajo.pdf'; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 30000); toast('Reporte PDF descargado.');
  }
  function confirmAction(title,message,callback) {
    $('confirm-title').textContent = title; $('confirm-message').textContent = message; setError('confirm-error','');
    confirmCallback = callback; $('confirm-dialog').showModal();
  }
  function renderProfile() {
    $('profile-avatar').textContent = user.username.slice(0,2).toUpperCase();
    $('profile-name').textContent = user.username; $('profile-username').textContent = user.username;
    $('profile-email').textContent = user.email; $('profile-role').textContent = roleNames[user.role] || user.role;
    const permissions = ['Consultar clientes, inventario y reportes','Consultar pedidos y comprobantes','Actualizar el estado de las entregas'];
    if (canWrite()) permissions.push('Registrar clientes, productos y pedidos','Preparar pedidos para despacho');
    if (canWrite()) permissions.push('Consultar finanzas y registrar cobros de pedidos');
    if (user.role === 'administrador') permissions.push('Registrar gastos operativos');
    if (user.role === 'administrador') permissions.push('Eliminar productos sin ventas asociadas','Registrar usuarios desde la API administrativa');
    $('permission-list').innerHTML = permissions.map((text) => `<li>${icon('check')}${text}</li>`).join('');
  }

  function connect() {
    if (leaving) return;
    socket = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://')+location.host+'/ws/updates');
    socket.onopen = () => {
      socket.send(sessionStorage.getItem('erp_token'));
    };
    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'CONNECTED') {
          reconnectCount = 0; $('connection-dot').className = 'dot online'; $('connection-label').textContent = 'Actualizaciones en vivo';
          return;
        }
        if (data.type === 'NEW_ORDER') toast('Se ha registrado un nuevo pedido.');
        if (data.type === 'LOW_STOCK_WARNING') toast('Un producto necesita reabastecimiento.');
        clearTimeout(refreshTimer); refreshTimer = setTimeout(load,500);
      } catch (_) { /* Ignorar mensajes que no pertenecen al protocolo ERP. */ }
    };
    socket.onclose = (event) => {
      $('connection-dot').className = 'dot offline'; $('connection-label').textContent = 'Sin conexión en vivo';
      if (event.code === 1008) { logout(); return; }
      if (!leaving) reconnectTimer = setTimeout(connect,Math.min(30000,1500 * 2 ** reconnectCount++));
    };
    socket.onerror = () => socket.close();
  }

  async function handleAction(action, id, target) {
    if (await workspace.handleAction(action,id,target)) return;
    if (action === 'logout') return logout();
    if (action === 'reload') {
      if (['procurement','inventory','manufacturing','quality','analytics','admin','project_logs'].includes(page)) return location.reload();
      return load();
    }
    if (action === 'new') return openForm();
    if (action === 'edit') return openForm(id);
    if (action === 'close-dialog') return $('form-dialog').close();
    if (action === 'close-detail') return $('detail-dialog').close();
    if (action === 'print') return window.print();
    if (action === 'cancel-confirm') return $('confirm-dialog').close();
    if (action === 'view') return viewOrder(id);
    if (action === 'export') return exportStock();
    if (action === 'add-line') return addLine();
    if (action === 'remove-line') { target.closest('.order-line').remove(); return totalOrder(); }
    if (action === 'client-history') { const client = rows.find((r) => r.id === id); location.assign('/pedidos?client='+id+'&search='+encodeURIComponent(client.name)); return; }
    if (action === 'delete') {
      const product = rows.find((r) => r.id === id);
      return confirmAction('Eliminar producto',`¿Eliminar «${product.name}»? Esta acción no se puede deshacer. Los productos con ventas asociadas se conservarán.`,async () => { await json('/products/'+id,{method:'DELETE'}); toast('Producto eliminado.'); await load(); });
    }
    if (action === 'advance') {
      const order = rows.find((r) => r.id === id);
      if (!order) throw new Error('Actualiza el tablero para consultar este pedido.');
      return workspace.advance(order);
    }
    if (action === 'simulate') {
      return confirmAction('Simular un pedido real','Se registrará un pedido de una unidad para un cliente existente y se descontará inventario. ¿Continuar?',async () => {
        const [clients,products] = await Promise.all([json('/clients/'),json('/products/')]); const available = products.filter((p) => p.stock > 0 && ['Jabones','Sales de baño','Accesorios','Kits'].includes(p.category));
        if (!clients.length || !available.length) throw new Error('Necesitas un cliente y productos con existencias.');
        const product = available[Math.floor(Math.random()*available.length)];
        await json('/orders/',{method:'POST',body:JSON.stringify({client_id:clients[0].id,items:[{product_id:product.id,quantity:1}]})}); toast('Pedido de demostración creado.'); await load();
      });
    }
  }
  async function boot() {
    if (page === 'login') { initLogin(); return; }
    if (!sessionStorage.getItem('erp_token')) { logout(); return; }
    document.addEventListener('click', async (event) => {
      const target = event.target.closest('[data-action]'); if (!target || target.disabled) return;
      event.preventDefault();
      if (target.dataset.busy) return;
      target.dataset.busy = '1';
      try { await handleAction(target.dataset.action,Number(target.dataset.id),target); }
      catch (error) { toast(error.message,true); }
      finally { delete target.dataset.busy; }
    });
    $('confirm-button').addEventListener('click', async () => {
      setBusy($('confirm-button'),true,'Procesando…'); setError('confirm-error','');
      try { await confirmCallback(); $('confirm-dialog').close(); }
      catch (error) { setError('confirm-error',error.message); }
      finally { setBusy($('confirm-button'),false); }
    });
    $('entity-form').addEventListener('submit',saveForm);
    $('entity-form').addEventListener('input',() => { if (mode === 'order') totalOrder(); });
    $('entity-form').addEventListener('change',() => { if (mode === 'order') totalOrder(); });
    try {
      user = await json('/auth/me'); initShell();
      if ($('table-search')) {
        $('table-search').value = new URLSearchParams(location.search).get('search') || '';
        ['table-search','table-filter','table-sort','page-size'].forEach((id) => $(id).addEventListener(id === 'table-search' ? 'input' : 'change',() => { currentPage = 1; renderTable(); }));
        $('previous-page').addEventListener('click',() => { currentPage--; renderTable(); });
        $('next-page').addEventListener('click',() => { currentPage++; renderTable(); });
      }
      await load(); connect();
      if (new URLSearchParams(location.search).get('new') === '1' && canWrite()) await openForm();
    } catch (error) { pageError(error.message); }
  }
  const workspace = window.createOperations?.({$,page,json,esc,money,num,date,icon,badge,toast,setBusy,setError,confirmAction,getUser:()=>user,getRows:()=>rows,getFilteredRows:filteredRows,load}) || {};
  boot();
})();

