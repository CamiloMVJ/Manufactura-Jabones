/* Módulos operativos: Kanban, trazabilidad y tesorería sobre las API reales. */
window.createOperations = function (ctx) {
  'use strict';
  const {$,page,json,esc,money,num,date,icon,badge,toast,setBusy,setError,confirmAction,getUser,getRows,getFilteredRows,load} = ctx;
  const stages = ['pendiente','preparado','en_ruta','entregado'];
  const names = {pendiente:'Pendiente',preparado:'Preparado',en_ruta:'En ruta',entregado:'Entregado'};
  const next = {pendiente:'preparado',preparado:'en_ruta',en_ruta:'entregado'};
  const stageHints = {pendiente:'Validar y preparar mercancía',preparado:'Listo para despacho',en_ruta:'En proceso de entrega',entregado:'Entrega completada'};
  let orderView = 'kanban', draggedOrder = null, financeData = null, financeMode = 'payment';
  let accountPage = 1, movementPage = 1, mobileStage = null;
  const limits = Object.fromEntries(stages.map((stage) => [stage,25]));
  const canAdvance = (order) => !!next[order.status] && !(getUser().role === 'repartidor' && order.status === 'pendiente');
  const age = (value) => Math.max(0,Math.floor((Date.now()-new Date(value).getTime())/86400000));
  const ageLabel = (days) => days === 0 ? 'Hoy' : days === 1 ? '1 día' : days+' días';

  function init() {
    if ($('kanban-board')) {
      try { orderView = new URLSearchParams(location.search).get('view') || localStorage.getItem('fridays_orders_view') || 'kanban'; } catch (_) { /* Preferencia opcional. */ }
      document.querySelectorAll('[data-order-view]').forEach((button) => button.addEventListener('click',() => setView(button.dataset.orderView)));
      setView(orderView);
      const board = $('kanban-board');
      board.addEventListener('dragstart',(event) => {
        const card = event.target.closest('.kanban-card');
        const order = getRows().find((o) => o.id === Number(card?.dataset.orderId));
        if (!order || !canAdvance(order)) { event.preventDefault(); return; }
        draggedOrder = order.id; event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('text/plain',String(order.id)); card.classList.add('dragging');
      });
      board.addEventListener('dragend',clearDrag);
      board.addEventListener('dragover',(event) => {
        const column = event.target.closest('[data-stage]');
        const order = getRows().find((o) => o.id === draggedOrder);
        document.querySelectorAll('.drop-ready').forEach((node) => node.classList.remove('drop-ready'));
        if (order && column?.dataset.stage === next[order.status] && canAdvance(order)) {
          event.preventDefault(); event.dataTransfer.dropEffect = 'move'; column.classList.add('drop-ready');
        }
      });
      board.addEventListener('drop',(event) => {
        event.preventDefault(); const column = event.target.closest('[data-stage]');
        const order = getRows().find((o) => o.id === draggedOrder);
        clearDrag();
        if (order && canAdvance(order) && column?.dataset.stage === next[order.status]) advance(order);
        else toast('El pedido solo puede avanzar a su siguiente etapa.',true);
      });
    }
    $('finance-form')?.addEventListener('submit',saveMoney);
    $('finance-form')?.addEventListener('change',(event) => {if (event.target.name === 'order_id') paymentBalance();});
    ['account-search','account-filter','movement-search','movement-filter'].forEach((id) => $(id)?.addEventListener(id.endsWith('search') ? 'input' : 'change',() => {accountPage=1;movementPage=1;renderFinanceTables();}));
  }
  function clearDrag() {
    draggedOrder = null;
    document.querySelectorAll('.dragging,.drop-ready').forEach((node) => node.classList.remove('dragging','drop-ready'));
  }
  function setView(view) {
    orderView = view === 'list' ? 'list' : 'kanban';
    if (!$('kanban-board')) return;
    $('kanban-board').hidden = orderView !== 'kanban';
    $('kanban-help').hidden = orderView !== 'kanban';
    $('kanban-mobile-tabs').hidden = orderView !== 'kanban';
    $('table-view').hidden = orderView !== 'list';
    $('list-pagination').hidden = orderView !== 'list';
    document.querySelectorAll('[data-order-view]').forEach((button) => { const selected = button.dataset.orderView === orderView;button.classList.toggle('selected',selected);button.setAttribute('aria-pressed',String(selected)); });
    try { localStorage.setItem('fridays_orders_view',orderView); } catch (_) { /* Preferencia opcional. */ }
  }
  function renderKanban() {
    if (!$('kanban-board')) return;
    const filtered = getFilteredRows();
    if (!mobileStage) mobileStage=stages.find((s) => filtered.some((o) => o.status === s)) || 'pendiente';
    $('kanban-mobile-tabs').innerHTML = stages.map((stage) => `<button data-action="kanban-stage" data-stage="${stage}" class="${mobileStage === stage ? 'selected' : ''}" aria-pressed="${mobileStage === stage}">${names[stage]}<span>${filtered.filter((o) => o.status === stage).length}</span></button>`).join('');
    $('kanban-board').innerHTML = stages.map((stage) => {
      const orders = filtered.filter((o) => o.status === stage);
      return `<section class="kanban-column stage-column-${stage}" data-stage="${stage}" aria-label="${names[stage]}"><div class="kanban-column-heading"><h3><span class="stage-dot stage-${stage}"></span>${names[stage]} <span class="kanban-count">${orders.length}</span></h3><strong>${money(orders.reduce((sum,o) => sum+o.total_amount,0))}</strong><p>${stageHints[stage]}</p></div><div class="kanban-cards">${orders.length ? orders.slice(0,limits[stage]).map(renderCard).join('') : `<div class="kanban-empty">${icon(stage === 'entregado' ? 'check' : 'box')}<strong>Sin pedidos en esta etapa</strong><span>${stage === 'pendiente' ? 'Los nuevos pedidos aparecerán aquí.' : 'Avanza un pedido desde la etapa anterior.'}</span></div>`}</div>${orders.length > limits[stage] ? `<button class="kanban-more" data-action="kanban-more" data-stage="${stage}">Ver ${Math.min(25,orders.length-limits[stage])} más de ${orders.length}</button>` : ''}</section>`;
    }).join('');
    document.querySelectorAll('#kanban-board [data-stage]').forEach((column) => {column.dataset.mobileActive=String(column.dataset.stage===mobileStage);});
    $('kanban-help').innerHTML = `${icon('box')} ${filtered.length} ${filtered.length===1 ? 'pedido visible' : 'pedidos visibles'} · avanza al siguiente estado con los botones o mediante arrastre. Los importes representan ventas, no cobros.`;
  }
  function renderCard(order) {
    const days = age(order.date), units = order.items.reduce((n,i) => n+i.quantity,0);
    const old = days >= 7 && order.status !== 'entregado';
    return `<article class="kanban-card ${old ? 'aged-order' : ''}" draggable="${canAdvance(order)}" data-order-id="${order.id}"><div class="kanban-card-meta"><button class="order-number" data-action="view" data-id="${order.id}">#${String(order.id).padStart(4,'0')}</button><span class="order-age ${old ? 'age-warning' : ''}" title="Antigüedad desde la venta">${icon('clock')}${ageLabel(days)}</span></div><button class="kanban-client" data-action="view" data-id="${order.id}">${esc(order.client)}</button><span class="kanban-zone">${esc(order.zone || 'Sin zona de entrega')}</span><p class="kanban-products">${esc(order.items.slice(0,2).map((i) => `${i.quantity} × ${i.name}`).join(' · '))}${order.items.length > 2 ? ' · +'+(order.items.length-2)+' referencias' : ''}</p><div class="kanban-card-total"><span>${units} uds. · ${order.items.length} ref.</span><strong>${money(order.total_amount)}</strong></div><div class="kanban-card-footer"><button class="icon-button" data-action="view" data-id="${order.id}" aria-label="Ver detalle del pedido ${order.id}">${icon('eye')}</button>${canAdvance(order) ? `<button class="kanban-advance" data-action="advance" data-id="${order.id}">${names[next[order.status]]} ${icon('check')}</button>` : `<span class="kanban-final">${order.status === 'entregado' ? icon('check')+' Entrega completa' : 'Pendiente de preparación'}</span>`}</div></article>`;
  }
  function advance(order) {
    if (!canAdvance(order)) { toast('Tu rol no puede realizar este cambio.',true); return; }
    const status = next[order.status];
    confirmAction('Avanzar pedido',`Pedido #${order.id} · ${order.client}. ¿Mover de «${names[order.status]}» a «${names[status]}»?`,async () => {
      await json(`/orders/${order.id}/status`,{method:'PATCH',body:JSON.stringify({status})});
      mobileStage=status;
      toast('Pedido movido a '+names[status].toLowerCase()+'.');await load();
    });
  }
  function timeline(order) {
    return `<section class="order-trace"><h3>Flujo del pedido</h3><ol class="order-progress">${stages.map((stage,i) => `<li class="${stages.indexOf(order.status) >= i ? 'completed' : ''}"><span>${stages.indexOf(order.status) > i ? icon('check') : i+1}</span>${names[stage]}</li>`).join('')}</ol><h3>Historial de cambios</h3><div class="order-timeline"><div><span class="timeline-dot"></span><p><strong>Pedido registrado</strong><small>${esc(date(order.date))}</small></p></div>${(order.timeline || []).map((e) => `<div><span class="timeline-dot"></span><p><strong>${esc(e.previous_status ? names[e.previous_status]+' → '+names[e.status] : names[e.status])}</strong><small>${esc(e.username)} · ${esc(new Date(e.date).toLocaleString('es-NI'))}</small></p></div>`).join('')}</div>${!order.timeline?.length ? '<p class="receipt-note">El pedido es anterior al historial detallado. Los próximos cambios se registrarán aquí.</p>' : ''}</section>`;
  }

  async function loadFinance() {
    financeData = await json('/finance/overview');
    const s = financeData.summary;
    const kpis = [['Cobros registrados',s.collected,'Ingresos efectivamente registrados','success'],['Por cobrar',s.outstanding,s.unpaid_orders+' pedidos con saldo','warning'],['Gastos registrados',s.expenses,'Salidas registradas por administración','danger'],['Flujo neto registrado',s.net_recorded,'Cobros menos gastos · acumulado','info']];
    $('finance-kpis').innerHTML = kpis.map(([label,value,hint,color]) => `<article class="kpi-card finance-kpi-${color}"><div class="kpi-top">${label}</div><strong class="kpi-value">${money(value)}</strong><p>${hint}</p></article>`).join('');
    const ratio = Number(s.sales) > 0 ? Math.min(100,Number(s.collected)/Number(s.sales)*100) : 0;
    $('collection-ratio').textContent = ratio.toLocaleString('es-NI',{maximumFractionDigits:1})+'%';
    $('collection-meter').style.width = ratio+'%';
    $('collection-breakdown').innerHTML = `<div><dt>Ventas registradas</dt><dd>${money(s.sales)}</dd></div><div><dt>Cobros aplicados</dt><dd>${money(s.collected)}</dd></div><div><dt>Saldo pendiente</dt><dd>${money(s.outstanding)}</dd></div>`;
    const max = Math.max(1,...financeData.trend.flatMap((d) => [Number(d.collected),Number(d.expenses)]));
    $('cashflow-chart').innerHTML = financeData.trend.map((d) => `<div class="cashflow-day" tabindex="0" title="${esc(date(d.date+'T12:00:00'))}: cobros ${money(d.collected)}, gastos ${money(d.expenses)}" aria-label="${esc(date(d.date+'T12:00:00'))}: cobros ${money(d.collected)}, gastos ${money(d.expenses)}"><div class="cashflow-bars"><div class="cashflow-collected" style="height:${Math.max(2,Number(d.collected)/max*120)}px"></div><div class="cashflow-expense" style="height:${Math.max(2,Number(d.expenses)/max*120)}px"></div></div><small>${esc(new Date(d.date+'T12:00:00').toLocaleDateString('es-NI',{weekday:'short'}))}</small></div>`).join('');
    renderFinanceTables();
  }
  function movementRows() {
    const search = $('movement-search').value.trim().toLocaleLowerCase(), filter = $('movement-filter').value;
    return financeData.movements.filter((r) => (filter === 'all' || r.kind === filter) && [r.description,r.reference,r.method,r.category].join(' ').toLocaleLowerCase().includes(search));
  }
  function paginate(items,pageNumber,prefix,render) {
    const total = Math.max(1,Math.ceil(items.length/10));
    pageNumber = Math.min(total,Math.max(1,pageNumber));const start = (pageNumber-1)*10;
    $(prefix+'-body').innerHTML = items.length ? items.slice(start,start+10).map(render).join('') : `<tr><td colspan="7" class="empty-cell"><strong>Sin registros para esta vista</strong>${prefix === 'account' ? 'Los pedidos con saldo pendiente aparecerán aquí.' : 'Registra un cobro o un gasto para empezar a dar seguimiento.'}</td></tr>`;
    $(prefix+'-page-label').textContent = items.length ? `${start+1}–${Math.min(start+10,items.length)} de ${items.length} registros` : '0 registros';
    $(prefix+'-page-number').textContent = pageNumber+' / '+total;
    $(prefix+'-prev').disabled = pageNumber === 1; $(prefix+'-next').disabled = pageNumber === total;
    return pageNumber;
  }
  function renderFinanceTables() {
    if (!financeData || !$('account-body')) return;
    const search = $('account-search').value.trim().toLocaleLowerCase(),filter = $('account-filter').value;
    const accounts = financeData.receivables.filter((r) => [r.id,r.client].join(' ').toLocaleLowerCase().includes(search) && (filter === 'all' || (filter === 'open' ? Number(r.balance)>0 : Number(r.balance)===0)));
    $('account-count').textContent = num(accounts.length);
    accountPage = paginate(accounts,accountPage,'account',(r) => `<tr><td><button class="order-number" data-action="view" data-id="${r.id}">#${String(r.id).padStart(4,'0')}</button><span class="table-subtext">${esc(r.client)}</span></td><td>${ageLabel(r.age_days)}</td><td class="numeric">${money(r.total)}</td><td class="numeric text-success">${money(r.paid)}</td><td class="numeric"><strong>${money(r.balance)}</strong></td><td><span class="badge badge-${Number(r.balance)===0 ? 'success' : Number(r.paid)>0 ? 'info' : 'warning'}">${Number(r.balance)===0 ? 'Liquidado' : Number(r.paid)>0 ? 'Cobro parcial' : 'Por cobrar'}</span></td><td>${Number(r.balance)>0 ? `<button class="btn btn-secondary btn-small" data-action="new-payment" data-id="${r.id}">Registrar cobro</button>` : icon('check')}</td></tr>`);
    movementPage = paginate(movementRows(),movementPage,'movement',(r) => `<tr><td>${esc(new Date(r.date).toLocaleString('es-NI',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}))}</td><td><strong>${esc(r.description)}</strong><span class="table-subtext">${esc(r.reference || 'Sin referencia')} · ${esc(r.category)}</span></td><td><span class="badge badge-${r.kind === 'cobro' ? 'success' : 'danger'}">${r.kind === 'cobro' ? 'Cobro' : 'Gasto'}</span></td><td>${esc(r.method)}</td><td class="numeric ${r.kind === 'cobro' ? 'text-success' : 'text-danger'}">${r.kind === 'cobro' ? '+' : '−'} ${money(r.amount)}</td></tr>`);
  }
  async function openMoney(kind,orderId) {
    if (!['administrador','vendedor'].includes(getUser().role)) throw new Error('Tu rol no tiene acceso a finanzas.');
    if (kind === 'expense' && getUser().role !== 'administrador') throw new Error('Solo un administrador puede registrar gastos.');
    financeMode = kind;setError('finance-form-error','');
    $('finance-form').reset();$('finance-dialog-title').textContent = kind === 'payment' ? 'Registrar cobro de pedido' : 'Registrar gasto';
    const common = `<div class="form-grid"><label class="field">Importe (C$) *<input name="amount" type="number" min="0.01" max="999999999999.99" step="0.01" required placeholder="0.00"></label><label class="field">Método *<select name="method"><option value="efectivo">Efectivo</option><option value="transferencia">Transferencia</option><option value="tarjeta">Tarjeta</option></select></label><label class="field full-width">Referencia / comprobante<input name="reference" maxlength="200" placeholder="Ej. número de transferencia"></label></div><input type="hidden" name="request_id" value="${crypto.randomUUID()}"><p class="receipt-note">Registra únicamente movimientos realizados. El registro quedará en el historial financiero y de auditoría.</p>`;
    if (kind === 'payment') {
      financeData = await json('/finance/overview');
      const open = financeData.receivables.filter((o) => Number(o.balance)>0);
      if (!open.length) throw new Error('No hay pedidos con saldo pendiente. Registra una venta antes de aplicar un cobro.');
      $('finance-form-body').innerHTML = `<label class="field">Pedido por cobrar *<select name="order_id" required><option value="">Selecciona un pedido</option>${open.map((o) => `<option value="${o.id}">#${o.id} · ${esc(o.client)} · saldo ${money(o.balance)}</option>`).join('')}</select></label><div id="payment-balance" class="payment-balance">Selecciona el pedido para consultar su saldo.</div>`+common;
      if (orderId && open.some((o) => o.id === orderId)) $('finance-form').elements.order_id.value = orderId;
      paymentBalance();
    } else {
      $('finance-form-body').innerHTML = `<div class="form-grid finance-expense-fields"><label class="field full-width">Concepto del gasto *<input name="description" minlength="3" maxlength="200" required placeholder="Ej. Combustible de reparto"></label><label class="field full-width">Categoría *<select name="category"><option value="transporte">Transporte</option><option value="servicios">Servicios</option><option value="compras">Compras</option><option value="personal">Personal</option><option value="otros">Otros</option></select></label></div>`+common;
    }
    $('finance-dialog').showModal();
  }
  function paymentBalance() {
    if (financeMode !== 'payment' || !$('payment-balance')) return;
    const order = financeData.receivables.find((r) => r.id === Number($('finance-form').elements.order_id.value));
    const input = $('finance-form').elements.amount;
    if (order) { $('payment-balance').textContent = `Total ${money(order.total)} · cobrado ${money(order.paid)} · pendiente ${money(order.balance)}`;input.max=order.balance; }
    else {$('payment-balance').textContent = 'Selecciona el pedido para consultar su saldo.';input.max='999999999999.99';}
  }
  async function saveMoney(event) {
    event.preventDefault();setError('finance-form-error','');setBusy($('finance-save'),true,'Registrando…');
    const values = Object.fromEntries(new FormData($('finance-form')));if (financeMode === 'payment') values.order_id=Number(values.order_id);
    values.reference = values.reference.trim() || null;
    try {
      await json(financeMode === 'payment' ? '/finance/payments' : '/finance/expenses',{method:'POST',body:JSON.stringify(values)});
      $('finance-dialog').close();toast(financeMode === 'payment' ? 'Cobro registrado y saldo actualizado.' : 'Gasto registrado.');financeData=null;load();
    } catch(error) {setError('finance-form-error',error.message);}
    finally {setBusy($('finance-save'),false);}
  }
  function exportFinance() {
    const quote = (v) => {let text=String(v ?? '');if (/^[=+\-@\t\r]/.test(text)) text="'"+text;return '"'+text.replaceAll('"','""')+'"';};
    const csv = [['Fecha','Tipo','Concepto','Método','Importe C$','Referencia'],...movementRows().map((r) => [r.date,r.kind,r.description,r.method,r.amount,r.reference])].map((row) => row.map(quote).join(',')).join('\r\n');
    const url=URL.createObjectURL(new Blob(['\ufeff'+csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='fridays-movimientos.csv';a.click();setTimeout(() => URL.revokeObjectURL(url),30000);toast('Movimientos filtrados exportados.');
  }
  async function renderDashboard() {
    const operations = await json('/reports/operations');
    const ranking = (items,labelKey,valueKey,format) => items.length ? items.map((r,index) => `<div class="ranking-row"><span class="rank-number">${index+1}</span><div><strong>${esc(r[labelKey])}</strong><span class="ranking-track"><span style="width:${Math.round(Number(r[valueKey])/Math.max(1,...items.map((i) => Number(i[valueKey])))*100)}%"></span></span></div><b>${format(r[valueKey])}</b></div>`).join('') : '<p class="empty-inline">Las ventas registradas mostrarán aquí sus resultados.</p>';
    $('top-products').innerHTML = ranking(operations.top_products,'product','sold',(v) => num(v)+' uds.');
    $('top-clients').innerHTML = ranking(operations.top_clients,'name','total',money);
    $('zone-list').innerHTML = operations.zones.length ? operations.zones.slice(0,6).map((z) => `<div class="zone-row"><span>${esc(z.name)}</span><span>${z.orders} pedidos</span><strong>${money(z.total)}</strong></div>`).join('') : '<p class="empty-inline">Asigna zonas a tus clientes para analizar la distribución.</p>';
    $('attention-list').innerHTML = [...operations.oldest_orders.map((o) => `<a href="/pedidos?search=${o.id}" class="attention-row"><span class="attention-symbol">${icon('clock')}</span><div><strong>Pedido #${o.id} · ${esc(o.client)}</strong><small>${names[o.status]} · antigüedad ${ageLabel(age(o.date))}</small></div><b>${money(o.total)}</b></a>`),...operations.expiring_products.map((p) => `<a href="/productos" class="attention-row"><span class="attention-symbol danger-symbol">${icon('box')}</span><div><strong>${esc(p.name)}</strong><small>${p.expired ? 'Vencido' : 'Vence'} ${esc(date(p.expiry_date+'T12:00:00'))} · ${p.stock} uds.</small></div></a>`)].slice(0,6).join('') || '<p class="empty-inline">Sin pedidos abiertos ni productos próximos a vencer.</p>';
    if (['administrador','vendedor'].includes(getUser().role) && $('dashboard-finance')) {
      const data=await json('/finance/overview');const s=data.summary;
      $('dashboard-finance').innerHTML = [['Cobros registrados',s.collected,'success'],['Cuentas por cobrar',s.outstanding,'warning'],['Gastos registrados',s.expenses,'danger'],['Flujo neto registrado',s.net_recorded,'info']].map(([label,value,color]) => `<a href="/finanzas" class="finance-mini finance-mini-${color}"><span>${label}</span><strong>${money(value)}</strong></a>`).join('');
    }
  }
  async function handleAction(action,id,target) {
    if (action === 'kanban-stage') {mobileStage=target.dataset.stage;renderKanban();return true;}
    if (action === 'kanban-more') {limits[target.dataset.stage]+=25;renderKanban();return true;}
    if (action === 'new-payment') {await openMoney('payment',id);return true;}
    if (action === 'new-expense') {await openMoney('expense');return true;}
    if (action === 'close-finance') {$('finance-dialog').close();return true;}
    if (action === 'export-finance') {exportFinance();return true;}
    if (['account-prev','account-next','movement-prev','movement-next'].includes(action)) {
      if (action.startsWith('account')) accountPage+=action.endsWith('next')?1:-1;else movementPage+=action.endsWith('next')?1:-1;
      renderFinanceTables();return true;
    }
    return false;
  }
  return {init,renderKanban,timeline,loadFinance,renderDashboard,handleAction,advance,openMoney};
};

