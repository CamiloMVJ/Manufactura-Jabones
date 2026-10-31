/* ESPUMA ENTERPRISE SUITE: Módulos conectados, Trazabilidad, Compras, Manufactura, Calidad, Monitores y Búsqueda Global. */
(() => {
  'use strict';

  const $ = (id) => document.getElementById(id);
  const page = document.body.dataset.page;
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const money = (value) => 'C$ ' + Number(value || 0).toLocaleString('es-NI', {minimumFractionDigits:2, maximumFractionDigits:2});
  const num = (value) => Number(value || 0).toLocaleString('es-NI');

  async function api(url, options = {}) {
    const token = sessionStorage.getItem('erp_token');
    const headers = {
      ...(options.body ? {'Content-Type':'application/json'} : {}),
      ...options.headers,
      ...(token ? {Authorization:`Bearer ${token}`} : {})
    };
    const res = await fetch(url, {...options, headers});
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Error en servidor (${res.status})`);
    }
    return res.json();
  }

  function toast(message, isError = false) {
    const t = document.createElement('div');
    t.className = 'toast' + (isError ? ' error' : '');
    t.textContent = message;
    $('toasts')?.append(t);
    setTimeout(() => t.remove(), 6000);
  }

  // ==========================================
  // TOPBAR: BÚSQUEDA GLOBAL (Ctrl+K)
  // ==========================================
  function initGlobalSearch() {
    const dialog = $('global-search-dialog');
    const input = $('gs-input');
    const results = $('gs-results');
    if (!dialog || !input) return;

    function openSearch() {
      dialog.showModal();
      input.value = '';
      input.focus();
      results.innerHTML = '<div class="search-hint-empty">Escribe al menos 2 caracteres para buscar en todos los módulos ERP.</div>';
    }

    $('global-search-btn')?.addEventListener('click', openSearch);

    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        openSearch();
      }
    });

    let debounceTimer;
    input.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      const query = input.value.trim();
      if (query.length < 2) {
        results.innerHTML = '<div class="search-hint-empty">Escribe al menos 2 caracteres para buscar en todos los módulos ERP.</div>';
        return;
      }
      debounceTimer = setTimeout(async () => {
        try {
          const data = await api(`/enterprise/global-search?q=${encodeURIComponent(query)}`);
          let html = '';
          const sections = [
            {key:'products', title:'Productos & Insumos'},
            {key:'lots', title:'Lotes de Inventario'},
            {key:'sales_orders', title:'Pedidos de Venta'},
            {key:'production_orders', title:'Órdenes de Producción'},
            {key:'suppliers', title:'Proveedores'},
            {key:'clients', title:'Clientes'}
          ];

          let totalFound = 0;
          for (const s of sections) {
            const items = data[s.key] || [];
            if (items.length > 0) {
              totalFound += items.length;
              html += `<div class="search-category-title">${s.title}</div><div class="search-category-items">`;
              for (const it of items) {
                html += `<a href="${it.url}" class="search-result-item"><strong>${esc(it.title)}</strong><small>${esc(it.subtitle)}</small></a>`;
              }
              html += `</div>`;
            }
          }
          results.innerHTML = totalFound > 0 ? html : '<div class="search-hint-empty">No se encontraron registros con ese término.</div>';
        } catch (err) {
          results.innerHTML = `<div class="search-hint-empty">${esc(err.message)}</div>`;
        }
      }, 250);
    });
  }

  // ==========================================
  // TOPBAR: LANZADOR DE MÓDULOS & APROBACIONES
  // ==========================================
  function initModuleLauncher() {
    $('module-launcher-btn')?.addEventListener('click', () => $('module-launcher-dialog')?.showModal());
    document.querySelectorAll('[data-action="close-launcher"]').forEach((b) => b.addEventListener('click', () => $('module-launcher-dialog')?.close()));
  }

  async function initApprovals() {
    const btn = $('approvals-btn');
    const badge = $('approvals-badge');
    const dialog = $('approvals-dialog');
    const list = $('approvals-list');
    if (!btn || !dialog) return;

    btn.addEventListener('click', () => {
      dialog.showModal();
      loadApprovals();
    });
    document.querySelectorAll('[data-action="close-approvals"]').forEach((b) => b.addEventListener('click', () => dialog.close()));

    async function loadApprovals() {
      try {
        const items = await api('/enterprise/approvals?status=pending');
        if (badge) {
          badge.textContent = items.length;
          badge.hidden = items.length === 0;
        }
        if (!list) return;
        if (!items.length) {
          list.innerHTML = '<div class="empty-cell"><strong>Bandeja al día</strong>No hay solicitudes pendientes de autorización.</div>';
          return;
        }
        list.innerHTML = items.map((a) => `
          <div class="approval-card">
            <div>
              <span class="badge badge-warning">${esc(a.document_type.replace('_',' ').toUpperCase())}</span>
              <strong>${esc(a.document_code)}</strong> · ${money(a.amount)}
              <p class="approval-reason">${esc(a.reason)}</p>
              <small>Solicitado por: ${esc(a.requested_by)} · ${esc(a.date)}</small>
            </div>
            <div class="approval-actions">
              <button class="btn btn-secondary btn-small" data-action="reject-approval" data-id="${a.id}">Rechazar</button>
              <button class="btn btn-primary btn-small" data-action="accept-approval" data-id="${a.id}">Aprobar</button>
            </div>
          </div>
        `).join('');
      } catch (_) {}
    }

    list?.addEventListener('click', async (e) => {
      const target = e.target.closest('[data-action]');
      if (!target) return;
      const id = target.dataset.id;
      const isAccept = target.dataset.action === 'accept-approval';
      try {
        target.disabled = true;
        await api(`/enterprise/approvals/${id}/action`, {
          method: 'POST',
          body: JSON.stringify({action: isAccept ? 'approve' : 'reject'})
        });
        toast(isAccept ? 'Documento aprobado.' : 'Documento rechazado.');
        loadApprovals();
      } catch (err) {
        toast(err.message, true);
      } finally {
        target.disabled = false;
      }
    });

    loadApprovals();
  }

  // ==========================================
  // SUBNAV TABS GENERAL
  // ==========================================
  function initSubnavTabs() {
    document.querySelectorAll('.subnav-tab').forEach((tab) => {
      tab.addEventListener('click', () => {
        const target = tab.dataset.tab;
        document.querySelectorAll('.subnav-tab').forEach((t) => {
          t.classList.toggle('active', t === tab);
          t.setAttribute('aria-selected', String(t === tab));
        });
        document.querySelectorAll('.tab-content').forEach((sec) => {
          sec.hidden = sec.id !== `tab-${target}`;
        });
      });
    });
  }

  // ==========================================
  // MÓDULO: COMPRAS Y ABASTECIMIENTO
  // ==========================================
  async function initProcurement() {
    if (page !== 'procurement') return;

    let products = [], suppliers = [];

    async function loadData() {
      try {
        const [pos, prs, sups] = await Promise.all([
          api('/enterprise/purchase-orders'),
          api('/enterprise/purchase-requests'),
          api('/enterprise/suppliers')
        ]);
        suppliers = sups;

        // KPIs
        $('kpi-po-count').textContent = pos.length;
        const vol = pos.reduce((s, p) => s + (p.total_amount || 0), 0);
        $('kpi-po-volume').textContent = money(vol);
        $('kpi-suppliers-count').textContent = sups.length;
        $('po-table-count').textContent = pos.length;
        $('pr-table-count').textContent = prs.length;
        $('sup-table-count').textContent = sups.length;

        // POs Table
        $('po-table-body').innerHTML = pos.length ? pos.map((po) => `
          <tr>
            <td><strong>${esc(po.code)}</strong></td>
            <td>${esc(po.supplier_name)}</td>
            <td>${esc(po.order_date)}</td>
            <td>${po.expected_delivery_date || '—'}</td>
            <td class="numeric"><strong>${money(po.total_amount)}</strong></td>
            <td><span class="badge badge-${po.status === 'received' ? 'success' : 'warning'}">${po.status === 'received' ? 'Recibida' : po.status === 'partial' ? 'Recepción parcial' : 'Aprobada'}</span></td>
            <td>
              ${po.status !== 'received' ? `<button class="btn btn-primary btn-small" data-action="open-reception" data-po='${JSON.stringify(po)}'>Recibir mercancía</button>` : '<span class="table-subtext">Completada</span>'}
            </td>
          </tr>
        `).join('') : '<tr><td colspan="7" class="empty-cell">No hay órdenes de compra registradas.</td></tr>';

        // PRs Table
        $('pr-table-body').innerHTML = prs.length ? prs.map((pr) => `
          <tr>
            <td><strong>${esc(pr.code)}</strong></td>
            <td>${esc(pr.requested_by)}</td>
            <td>${esc(pr.department)}</td>
            <td>${esc(pr.date)}</td>
            <td class="numeric">${money(pr.total_estimated)}</td>
            <td><span class="badge badge-${pr.status === 'approved' ? 'success' : 'warning'}">${pr.status}</span></td>
            <td>${pr.items.map((i) => `${i.quantity} uds. ${i.product_name}`).join(', ')}</td>
          </tr>
        `).join('') : '<tr><td colspan="7" class="empty-cell">No hay solicitudes registradas.</td></tr>';

        // Suppliers Table
        $('sup-table-body').innerHTML = sups.length ? sups.map((s) => `
          <tr>
            <td><strong>${esc(s.name)}</strong></td>
            <td>${esc(s.tax_id || '—')}</td>
            <td>${esc(s.contact_name || '—')}</td>
            <td>${esc(s.email || '—')}</td>
            <td>${esc(s.phone || '—')}</td>
            <td><span class="badge badge-neutral">${esc(s.category || 'General')}</span></td>
            <td>${esc(s.payment_terms || 'Contado')}</td>
          </tr>
        `).join('') : '<tr><td colspan="7" class="empty-cell">No hay proveedores registrados.</td></tr>';

      } catch (err) {
        toast('Error al cargar datos de compras: ' + err.message, true);
      }
    }

    // Modal PR
    document.querySelectorAll('[data-action="new-pr"]').forEach((b) => b.addEventListener('click', async () => {
      products = await api('/products/');
      const sel = $('pr-product-select');
      sel.innerHTML = products.map((p) => `<option value="${p.id}">${esc(p.name)} · (Actual: ${p.stock} uds.)</option>`).join('');
      $('pr-dialog')?.showModal();
    }));
    document.querySelectorAll('[data-action="close-pr"]').forEach((b) => b.addEventListener('click', () => $('pr-dialog')?.close()));
    $('pr-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const form = $('pr-form');
      const data = {
        requested_by: form.requested_by.value,
        department: form.department.value,
        notes: form.notes.value,
        items: [{
          product_id: Number(form.product_id.value),
          quantity: Number(form.quantity.value),
          estimated_unit_price: Number(form.estimated_unit_price.value)
        }]
      };
      try {
        await api('/enterprise/purchase-requests', {method:'POST', body:JSON.stringify(data)});
        $('pr-dialog').close();
        toast('Solicitud de compra creada y enviada a aprobación.');
        loadData();
      } catch (err) {
        toast(err.message, true);
      }
    });

    // Modal PO
    document.querySelectorAll('[data-action="new-po"]').forEach((b) => b.addEventListener('click', async () => {
      [products, suppliers] = await Promise.all([api('/products/'), api('/enterprise/suppliers')]);
      $('po-supplier-select').innerHTML = suppliers.map((s) => `<option value="${s.id}">${esc(s.name)}</option>`).join('');
      $('po-product-select').innerHTML = products.map((p) => `<option value="${p.id}" data-price="${p.price}">${esc(p.name)}</option>`).join('');
      calcPoTotal();
      $('po-dialog')?.showModal();
    }));
    document.querySelectorAll('[data-action="close-po"]').forEach((b) => b.addEventListener('click', () => $('po-dialog')?.close()));

    function calcPoTotal() {
      const qty = Number($('po-qty')?.value || 0);
      const price = Number($('po-price')?.value || 0);
      if ($('po-calc-total')) $('po-calc-total').textContent = money(qty * price);
    }
    $('po-qty')?.addEventListener('input', calcPoTotal);
    $('po-price')?.addEventListener('input', calcPoTotal);

    $('po-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const form = $('po-form');
      const data = {
        supplier_id: Number(form.supplier_id.value),
        expected_delivery_date: form.expected_delivery_date.value,
        items: [{
          product_id: Number(form.product_id.value),
          quantity: Number(form.quantity.value),
          unit_price: Number(form.unit_price.value)
        }]
      };
      try {
        await api('/enterprise/purchase-orders', {method:'POST', body:JSON.stringify(data)});
        $('po-dialog').close();
        toast('Orden de compra emitida a proveedor.');
        loadData();
      } catch (err) {
        toast(err.message, true);
      }
    });

    // Modal Recepción
    $('po-table-body')?.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-action="open-reception"]');
      if (!btn) return;
      const po = JSON.parse(btn.dataset.po);
      const item = po.items[0];
      if (!item) return;
      $('rec-po-id').value = po.id;
      $('rec-prod-id').value = item.product_id;
      $('rec-qty').value = item.quantity;
      $('rec-hint').textContent = `Recepción de ${item.quantity} unidades de «${item.product_name}» de la orden ${po.code}.`;
      $('rec-dialog')?.showModal();
    });
    document.querySelectorAll('[data-action="close-rec"]').forEach((b) => b.addEventListener('click', () => $('rec-dialog')?.close()));
    $('rec-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const form = $('rec-form');
      const data = {
        purchase_order_id: Number(form.purchase_order_id.value),
        warehouse_id: Number(form.warehouse_id.value),
        items: [{
          product_id: Number(form.product_id.value),
          quantity_received: Number(form.quantity_received.value),
        expiry_date: form.expiry_date.value || null,
          lot_number: form.lot_number.value.trim() || undefined
        }]
      };
      try {
        await api('/enterprise/material-receptions', {method:'POST', body:JSON.stringify(data)});
        $('rec-dialog').close();
        toast('Mercancía recibida e ingresada al inventario con lote.');
        loadData();
      } catch (err) {
        toast(err.message, true);
      }
    });

    // Modal Proveedor
    document.querySelectorAll('[data-action="new-supplier"]').forEach((b) => b.addEventListener('click', () => $('sup-dialog')?.showModal()));
    document.querySelectorAll('[data-action="close-sup"]').forEach((b) => b.addEventListener('click', () => $('sup-dialog')?.close()));
    $('sup-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const values = Object.fromEntries(new FormData($('sup-form')));
      try {
        await api('/enterprise/suppliers', {method:'POST', body:JSON.stringify(values)});
        $('sup-dialog').close();
        toast('Proveedor guardado correctamente.');
        loadData();
      } catch (err) {
        toast(err.message, true);
      }
    });

    loadData();
  }

  // ==========================================
  // MÓDULO: INVENTARIO & TRAZABILIDAD DE LOTES
  // ==========================================
  async function initInventorySuite() {
    if (page !== 'inventory') return;

    async function loadData() {
      try {
        const [sum, lots, movs] = await Promise.all([
          api('/enterprise/inventory-summary'),
          api('/enterprise/lots'),
          api('/enterprise/inventory-movements')
        ]);

        $('kpi-inv-units').textContent = num(sum.total_units);
        $('kpi-inv-val').textContent = money(sum.inventory_valuation);
        $('kpi-inv-lots').textContent = sum.active_lots;
        $('kpi-inv-movs').textContent = sum.total_movements;
        $('lots-count').textContent = lots.length;
        $('movs-count').textContent = movs.length;

        // Lotes
        $('lots-table-body').innerHTML = lots.length ? lots.map((l) => `
          <tr>
            <td><strong>${esc(l.lot_number)}</strong></td>
            <td>${esc(l.product_name)}</td>
            <td>${esc(l.supplier_name)}</td>
            <td class="numeric">${l.initial_quantity} uds.</td>
            <td class="numeric"><strong>${l.current_quantity} uds.</strong></td>
            <td>${l.manufacture_date || '—'}</td>
            <td>${l.expiry_date || '—'}</td>
            <td><span class="badge badge-success">${esc(l.status)}</span></td>
            <td>
              <button class="btn btn-secondary btn-small" data-action="inspect-lot" data-lot="${esc(l.lot_number)}">Ver Trazabilidad</button>
            </td>
          </tr>
        `).join('') : '<tr><td colspan="9" class="empty-cell">No hay lotes registrados.</td></tr>';

        // Movimientos
        $('movs-table-body').innerHTML = movs.length ? movs.map((m) => `
          <tr>
            <td><strong>${esc(m.code)}</strong></td>
            <td>${esc(m.product_name)}</td>
            <td>${esc(m.lot_number)}</td>
            <td><span class="badge badge-neutral">${esc(m.movement_type.replace('_',' '))}</span></td>
            <td class="numeric"><strong>${m.quantity} uds.</strong></td>
            <td>${esc(m.source)}</td>
            <td>${esc(m.destination)}</td>
            <td><small>${esc(m.reference_doc)}</small></td>
            <td>${esc(m.created_at)}</td>
          </tr>
        `).join('') : '<tr><td colspan="9" class="empty-cell">No hay movimientos registrados.</td></tr>';

      } catch (err) {
        toast('Error al cargar inventario: ' + err.message, true);
      }
    }

    async function traceLot(lotNumber) {
      if (!lotNumber) return;
      // Switch tab to traceability
      document.querySelector('[data-tab="traceability"]')?.click();
      $('trace-input').value = lotNumber;
      $('trace-result-view').innerHTML = '<div class="empty-cell">Generando árbol de trazabilidad bidireccional…</div>';

      try {
        const trace = await api(`/enterprise/lot-traceability/${encodeURIComponent(lotNumber)}`);
        const l = trace.lot;
        const orig = trace.origin;

        $('trace-result-view').innerHTML = `
          <div class="trace-header-card">
            <div>
              <span class="eyebrow">EXPEDIENTE DE TRAZABILIDAD</span>
              <h2>Lote: ${esc(l.lot_number)} · ${esc(l.product_name)}</h2>
              <p>Saldo en existencia: <strong>${l.current_quantity} uds.</strong> · Estado: <span class="badge badge-success">${l.status}</span></p>
            </div>
          </div>

          <div class="trace-flow-graph">
            <!-- 1. ORIGEN -->
            <div class="trace-node">
              <div class="node-badge">1. ORIGEN</div>
              <h4>${orig.type === 'supplier_reception' ? 'Recepción de Proveedor' : (orig.type === 'production_order' ? 'Manufactura en Planta' : 'Inventario Inicial')}</h4>
              <p>${orig.supplier ? `Proveedor: <strong>${esc(orig.supplier)}</strong>` : ''}</p>
              ${orig.purchase_order ? `<p>Orden de compra: <strong>${esc(orig.purchase_order)}</strong></p>` : ''}
              ${orig.reception_code ? `<p>Recepción: <strong>${esc(orig.reception_code)}</strong></p>` : ''}
              ${orig.produced_in_order ? `<p>Orden de Producción: <strong>${esc(orig.produced_in_order)}</strong></p>` : ''}
              ${orig.consumed_raw_lot ? `<p>Lote MP Consumido: <strong>${esc(orig.consumed_raw_lot)}</strong></p>` : ''}
            </div>

            <div class="trace-arrow">➔</div>

            <!-- 2. CONTROL DE CALIDAD -->
            <div class="trace-node">
              <div class="node-badge">2. CALIDAD & ENSAYOS</div>
              <h4>Inspecciones de Laboratorio</h4>
              ${trace.quality_inspections.length ? trace.quality_inspections.map((q) => `
                <div class="trace-subitem">
                  <strong>${esc(q.code)}</strong>: <span class="badge badge-${q.result === 'passed' ? 'success' : 'danger'}">${q.result.toUpperCase()}</span>
                  <small>${esc(q.measured)}</small>
                </div>
              `).join('') : '<p class="empty-inline">Sin ensayos reportados</p>'}
            </div>

            <div class="trace-arrow">➔</div>

            <!-- 3. DESTINO / VENTAS -->
            <div class="trace-node">
              <div class="node-badge">3. SALIDA / CLIENTE</div>
              <h4>Distribución y Ventas</h4>
              ${trace.sales_distribution.length ? trace.sales_distribution.map((s) => `
                <div class="trace-subitem">
                  <strong>Pedido #${s.order_id}</strong> · ${esc(s.client_name)} (${esc(s.zone)})
                  <div>${s.quantity_sold} uds. despachadas · <span class="badge badge-info">${s.order_status}</span></div>
                </div>
              `).join('') : '<p class="empty-inline">Lote en almacén, sin ventas asignadas aún.</p>'}
            </div>
          </div>
        `;
      } catch (err) {
        $('trace-result-view').innerHTML = `<div class="empty-cell error-text">${esc(err.message)}</div>`;
      }
    }

    $('trace-btn')?.addEventListener('click', () => traceLot($('trace-input')?.value.trim()));
    $('lots-table-body')?.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-action="inspect-lot"]');
      if (btn) traceLot(btn.dataset.lot);
    });

    // If URL has ?lot=...
    const urlLot = new URLSearchParams(location.search).get('lot');
    if (urlLot) traceLot(urlLot);

    loadData();
  }

  // ==========================================
  // MÓDULO: MANUFACTURA & PRODUCCIÓN
  // ==========================================
  async function initManufacturing() {
    if (page !== 'manufacturing') return;

    let products = [], boms = [], lots = [];

    async function loadData() {
      try {
        const [orders, allBoms, routings, wcs] = await Promise.all([
          api('/enterprise/production-orders'),
          api('/enterprise/boms'),
          api('/enterprise/routings'),
          api('/enterprise/work-centers')
        ]);
        boms = allBoms;

        $('prod-orders-count').textContent = orders.length;

        // Órdenes
        const statusMap = {
          draft: {label:'Borrador', cls:'neutral', next:'planned'},
          planned: {label:'Planificado', cls:'info', next:'materials_reserved'},
          materials_reserved: {label:'Disponibilidad verificada', cls:'warning', next:'in_production'},
          in_production: {label:'En Producción', cls:'purple', next:'quality_control'},
          quality_control: {label:'Control Calidad', cls:'warning', next:'completed'},
          completed: {label:'Completado', cls:'success', next:null}
        };

        $('prod-orders-table-body').innerHTML = orders.length ? orders.map((o) => {
          const st = statusMap[o.status] || {label:o.status, cls:'neutral'};
          return `
            <tr>
              <td><strong>${esc(o.code)}</strong><br><small>ID: ${o.id}</small></td>
              <td>${esc(o.product_name)}</td>
              <td class="numeric">${o.planned_quantity} uds.</td>
              <td class="numeric"><strong>${o.produced_quantity} uds.</strong></td>
              <td>${esc(o.raw_lot)}</td>
              <td><strong>${esc(o.finished_lot)}</strong></td>
              <td><span class="badge badge-${st.cls}">${st.label}</span></td>
              <td>
                ${st.next ? `<button class="btn btn-primary btn-small" data-action="advance-prod-order" data-id="${o.id}" data-next="${st.next}">Avanzar a ${statusMap[st.next].label}</button>` : '<span class="table-subtext">Cerrada</span>'}
              </td>
            </tr>
          `;
        }).join('') : '<tr><td colspan="8" class="empty-cell">No hay órdenes de producción registradas.</td></tr>';

        // BOMs
        $('boms-table-body').innerHTML = allBoms.length ? allBoms.map((b) => `
          <tr>
            <td><strong>${esc(b.code)}</strong></td>
            <td>${esc(b.finished_product_name)}</td>
            <td>v${b.version}</td>
            <td>${b.quantity} ud. terminada</td>
            <td>${b.components.map((c) => `${c.quantity} de ${c.product_name} (merma ${c.scrap_percentage}%)`).join(' + ')}</td>
            <td><span class="badge badge-success">Activo</span></td>
          </tr>
        `).join('') : '<tr><td colspan="6" class="empty-cell">No hay BOMs registradas.</td></tr>';

        // Work Centers
        $('wc-table-body').innerHTML = wcs.map((w) => `
          <tr>
            <td><strong>${esc(w.code)}</strong></td>
            <td>${esc(w.name)}</td>
            <td>${w.capacity_per_hour} uds/h</td>
            <td>C$ ${w.cost_per_hour}</td>
            <td><span class="badge badge-success">${w.status}</span></td>
          </tr>
        `).join('');

        // Routings
        $('routings-table-body').innerHTML = routings.map((r) => `
          <tr>
            <td><strong>${esc(r.code)}</strong></td>
            <td>${esc(r.finished_product_name)}</td>
            <td>${r.operations.map((op) => `Paso ${op.sequence}: ${op.operation_name} (${op.work_center_name}, ${op.duration_minutes} min)`).join(' ➔ ')}</td>
          </tr>
        `).join('');

      } catch (err) {
        toast('Error al cargar manufactura: ' + err.message, true);
      }
    }

    // Modal Crear Orden de Producción
    document.querySelectorAll('[data-action="new-production-order"]').forEach((b) => b.addEventListener('click', async () => {
      [products, lots] = await Promise.all([api('/products/'), api('/enterprise/lots')]);
      $('prod-order-product-select').innerHTML = products.filter(p => ['Jabones','Sales de baño','Kits'].includes(p.category)).map((p) => `<option value="${p.id}">${esc(p.name)}</option>`).join('');
      $('prod-order-lot-select').innerHTML = `<option value="">Auto-seleccionar lote de materia prima</option>` + lots.map((l) => `<option value="${l.id}">${esc(l.lot_number)} (${esc(l.product_name)} - Saldo: ${l.current_quantity})</option>`).join('');
      $('po-prod-dialog')?.showModal();
    }));
    document.querySelectorAll('[data-action="close-prod-order"]').forEach((b) => b.addEventListener('click', () => $('po-prod-dialog')?.close()));

    $('po-prod-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const form = $('po-prod-form');
      const data = {
        product_id: Number(form.product_id.value),
        planned_quantity: Number(form.planned_quantity.value),
        raw_material_lot_id: form.raw_material_lot_id.value ? Number(form.raw_material_lot_id.value) : undefined,
        notes: form.notes.value
      };
      try {
        await api('/enterprise/production-orders', {method:'POST', body:JSON.stringify(data)});
        $('po-prod-dialog').close();
        toast('Orden de producción planificada.');
        loadData();
      } catch (err) {
        toast(err.message, true);
      }
    });

    // Avanzar etapa
    $('prod-orders-table-body')?.addEventListener('click', async (e) => {
      const btn = e.target.closest('[data-action="advance-prod-order"]');
      if (!btn) return;
      const orderId = btn.dataset.id;
      const nextStatus = btn.dataset.next;
      try {
        btn.disabled = true;
        await api(`/enterprise/production-orders/${orderId}/status`, {
          method: 'PATCH',
          body: JSON.stringify({status: nextStatus})
        });
        toast('Orden avanzada a ' + nextStatus.replace('_',' '));
        loadData();
      } catch (err) {
        toast(err.message, true);
      } finally {
        btn.disabled = false;
      }
    });

    loadData();
  }

  // ==========================================
  // MÓDULO: CALIDAD
  // ==========================================
  async function initQuality() {
    if (page !== 'quality') return;

    let products = [];

    async function loadData() {
      try {
        const data = await api('/enterprise/quality/dashboard');
        const kpis = data.kpis;
        $('kpi-qc-total').textContent = kpis.total_inspections;
        $('kpi-qc-passrate').textContent = kpis.pass_rate + '%';
        $('kpi-qc-ncs').textContent = kpis.total_non_conformities;
        $('kpi-qc-open').textContent = kpis.open_non_conformities;
        $('inspections-count').textContent = data.inspections.length;
        $('ncs-count').textContent = data.non_conformities.length;

        // Inspecciones
        $('inspections-table-body').innerHTML = data.inspections.length ? data.inspections.map((i) => `
          <tr>
            <td><strong>${esc(i.code)}</strong></td>
            <td>${esc(i.product_name)}</td>
            <td>${esc(i.lot_number)}</td>
            <td><span class="badge badge-neutral">${esc(i.inspection_type.replace('_',' '))}</span></td>
            <td>${esc(i.expected_value || '—')}</td>
            <td><strong>${esc(i.measured_value || '—')}</strong></td>
            <td><span class="badge badge-${i.result === 'passed' ? 'success' : (i.result === 'failed' ? 'danger' : 'warning')}">${i.result.toUpperCase()}</span></td>
            <td>${esc(i.inspector)}</td>
            <td>${esc(i.date)}</td>
          </tr>
        `).join('') : '<tr><td colspan="9" class="empty-cell">No hay inspecciones registradas.</td></tr>';

        // No Conformidades
        $('ncs-table-body').innerHTML = data.non_conformities.length ? data.non_conformities.map((nc) => `
          <tr>
            <td><strong>${esc(nc.code)}</strong></td>
            <td>${esc(nc.product_name)}</td>
            <td>${esc(nc.lot_number)}</td>
            <td><span class="badge badge-${nc.severity === 'critical' ? 'danger' : 'warning'}">${nc.severity.toUpperCase()}</span></td>
            <td>${esc(nc.description)}</td>
            <td>${esc(nc.cause || 'En análisis')}</td>
            <td><span class="badge badge-purple">${esc(nc.disposition || 'Pendiente')}</span></td>
            <td><span class="badge badge-${nc.status === 'resolved' ? 'success' : 'warning'}">${nc.status}</span></td>
            <td>
              ${nc.status !== 'resolved' ? `<button class="btn btn-secondary btn-small" data-action="open-disp" data-id="${nc.id}" data-desc="${esc(nc.description)}">Definir disposición</button>` : '<span class="table-subtext">Resuelto</span>'}
            </td>
          </tr>
        `).join('') : '<tr><td colspan="9" class="empty-cell">No hay no conformidades activas.</td></tr>';

      } catch (err) {
        toast('Error al cargar calidad: ' + err.message, true);
      }
    }

    // Modal Inspección
    document.querySelectorAll('[data-action="new-inspection"]').forEach((b) => b.addEventListener('click', async () => {
      products = await api('/products/');
      $('qc-product-select').innerHTML = products.map((p) => `<option value="${p.id}">${esc(p.name)}</option>`).join('');
      $('qc-dialog')?.showModal();
    }));
    document.querySelectorAll('[data-action="close-qc"]').forEach((b) => b.addEventListener('click', () => $('qc-dialog')?.close()));
    $('qc-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const form = $('qc-form');
      const data = {
        product_id: Number(form.product_id.value),
        production_order_id: form.production_order_id.value ? Number(form.production_order_id.value) : null,
        inspection_type: form.inspection_type.value,
        result: form.result.value,
        expected_value: form.expected_value.value,
        measured_value: form.measured_value.value,
        observations: form.observations.value
      };
      try {
        await api('/enterprise/quality/inspections', {method:'POST', body:JSON.stringify(data)});
        $('qc-dialog').close();
        toast('Inspección de calidad registrada.');
        loadData();
      } catch (err) {
        toast(err.message, true);
      }
    });

    // Modal Disposición
    $('ncs-table-body')?.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-action="open-disp"]');
      if (!btn) return;
      $('disp-nc-id').value = btn.dataset.id;
      $('disp-nc-description').textContent = btn.dataset.desc;
      $('disposition-dialog')?.showModal();
    });
    document.querySelectorAll('[data-action="close-disp"]').forEach((b) => b.addEventListener('click', () => $('disposition-dialog')?.close()));
    $('disposition-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const form = $('disposition-form');
      const ncId = form.nc_id.value;
      const data = {
        disposition: form.disposition.value,
        notes: form.notes.value
      };
      try {
        await api(`/enterprise/quality/non-conformities/${ncId}/disposition`, {method:'PATCH', body:JSON.stringify(data)});
        $('disposition-dialog').close();
        toast('Disposición de no conformidad aplicada.');
        loadData();
      } catch (err) {
        toast(err.message, true);
      }
    });

    loadData();
  }

  // ==========================================
  // MÓDULO: ANALÍTICA & KPIS
  // ==========================================
  async function initAnalytics() {
    if (page !== 'analytics') return;
    try {
      const data = await api('/enterprise/analytics');
      const mfg = data.manufacturing;
      $('kpi-mfg-oee').textContent = mfg.oee;
      $('kpi-mfg-yield').textContent = mfg.yield_rate;
      $('kpi-mfg-scrap').textContent = mfg.scrap_rate;
      $('kpi-mfg-cycle').textContent = mfg.cycle_time;

      const inv = data.inventory;
      $('kpi-inv-turnover').textContent = inv.inventory_turnover;
      $('kpi-inv-valuation').textContent = inv.valuation;
      $('kpi-inv-coverage').textContent = inv.coverage_days;
      $('kpi-inv-alerts').textContent = inv.low_stock_alerts;

      const proc = data.procurement;
      $('kpi-proc-vol').textContent = proc.volume;
      $('kpi-proc-avg').textContent = proc.average_po_cost;
      $('kpi-proc-lead').textContent = proc.supplier_lead_time;
      $('kpi-proc-pending').textContent = proc.pending_receipts;

      const sls = data.sales;
      $('kpi-sales-rev').textContent = sls.revenue;
      $('kpi-sales-orders').textContent = sls.order_count;
      $('kpi-sales-aov').textContent = sls.average_order_value;
      $('kpi-sales-ontime').textContent = sls.dispatch_efficiency;
    } catch (err) {
      toast('Error al cargar analítica: ' + err.message, true);
    }
  }

  // ==========================================
  // MÓDULO: ADMINISTRACIÓN & MONITORES
  // ==========================================
  async function initAdministration() {
    if (page !== 'admin') return;
    try {
      const [sys, dh, logs, users] = await Promise.all([
        api('/enterprise/system-health'),
        api('/enterprise/data-health'),
        api('/enterprise/audit-logs'),
        api('/enterprise/users').catch(() => [])
      ]);

      // System Health
      $('sys-status-badge').textContent = sys.status;
      $('sys-db-status').textContent = `${sys.database.engine} (${sys.database.status})`;
      $('sys-db-size').textContent = `Tamaño: ${sys.database.size_mb} MB`;
      $('sys-mem-pct').textContent = `${sys.server.memory_usage_pct} %`;
      $('sys-disk-pct').textContent = `${sys.server.disk_usage_pct} %`;
      $('sys-python-ver').textContent = `Python ${sys.server.python_version} · ${sys.server.platform}`;
      $('sys-backup').textContent = sys.last_backup;
      $('sys-cron').textContent = sys.last_cron;

      // Data Health
      $('data-health-score').textContent = dh.health_score;
      $('data-health-status').textContent = dh.status;
      $('dh-products').textContent = dh.counts.products;
      $('dh-clients').textContent = dh.counts.clients;
      $('dh-suppliers').textContent = dh.counts.suppliers;
      $('dh-lots').textContent = dh.counts.lots;
      $('dh-boms').textContent = dh.counts.boms;
      $('dh-pos').textContent = dh.counts.production_orders;

      $('dh-inconsistencies').innerHTML = dh.inconsistencies.length ? dh.inconsistencies.map((inc) => `
        <div class="inconsistency-item inconsistency-${inc.severity}">
          <strong>${esc(inc.record)}</strong>
          <span>${esc(inc.detail)}</span>
        </div>
      `).join('') : '<div class="empty-inline text-success">No se detectaron inconsistencias en la base de datos. Salud óptima al 100%.</div>';

      // Audit Log
      $('audit-count').textContent = logs.length;
      $('audit-table-body').innerHTML = logs.length ? logs.map((l) => `
        <tr>
          <td><small>${esc(l.created_at)}</small></td>
          <td><strong>${esc(l.username)}</strong></td>
          <td><span class="badge badge-neutral">${esc(l.action)}</span></td>
          <td>${esc(l.module)}</td>
          <td>${esc(l.record_reference || '—')}</td>
          <td><small>${esc(l.ip_address)}</small></td>
          <td><small>${esc(l.before_state ? `${l.before_state} ➔ ${l.after_state}` : (l.after_state || '—'))}</small></td>
        </tr>
      `).join('') : '<tr><td colspan="7" class="empty-cell">Sin registros de auditoría aún.</td></tr>';

      // Users
      $('users-count').textContent = users.length;
      $('users-table-body').innerHTML = users.length ? users.map((u) => `
        <tr>
          <td>#${u.id}</td>
          <td><strong>${esc(u.username)}</strong></td>
          <td>${esc(u.email)}</td>
          <td><span class="badge badge-purple">${esc(u.role)}</span></td>
          <td><span class="badge badge-${u.is_active ? 'success' : 'danger'}">${u.is_active ? 'Activo' : 'Inactivo'}</span></td>
          <td><small>${esc(u.permissions)}</small></td>
        </tr>
      `).join('') : '<tr><td colspan="6" class="empty-cell">Acceso restringido a usuarios administradores.</td></tr>';

    } catch (err) {
      toast('Error al consultar administración: ' + err.message, true);
    }
  }

  // ==========================================
  // MÓDULO: BITÁCORA DE PROYECTO
  // ==========================================
  async function initProjectLogs() {
    if (page !== 'project_logs') return;
    try {
      const data = await api('/enterprise/project-logs');
      // Contribuciones
      $('contrib-table-body').innerHTML = data.contributions.map((c) => `
        <tr>
          <td><strong>${esc(c.contributor)}</strong></td>
          <td><strong>${esc(c.task)}</strong></td>
          <td><span class="badge badge-purple">${esc(c.module)}</span></td>
          <td>${esc(c.description)}</td>
          <td><code>${esc(c.commit_ref)}</code></td>
          <td><span class="badge badge-success">${esc(c.status)}</span></td>
        </tr>
      `).join('');

      // Incidencias
      $('issues-table-body').innerHTML = data.issues.map((i) => `
        <tr>
          <td><strong>${esc(i.issue)}</strong></td>
          <td><span class="badge badge-neutral">${esc(i.module)}</span></td>
          <td><span class="badge badge-${i.impact === 'high' ? 'danger' : 'warning'}">${esc(i.impact.toUpperCase())}</span></td>
          <td><small>${esc(i.cause)}</small></td>
          <td>${esc(i.solution)}</td>
          <td><span class="badge badge-success">${esc(i.status)}</span></td>
          <td>${esc(i.responsible)}</td>
        </tr>
      `).join('');
    } catch (err) {
      toast('Error al cargar bitácora: ' + err.message, true);
    }
  }

  // ==========================================
  // FLUJO DEMOSTRATIVO INTEGRAL (END-TO-END)
  // ==========================================
  function initDemoWorkflow() {
    document.querySelectorAll('[data-action="simulate-demo-flow"]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        btn.disabled = true;
        btn.textContent = 'Ejecutando ciclo de valor…';
        try {
          const res = await api('/enterprise/workflow/execute-demo-flow', {method:'POST'});
          const fl = res.flow;
          toast('¡Ciclo transaccional completo ejecutado con éxito!');
          const panel = $('demo-flow-result');
          if (panel) {
            panel.hidden = false;
            panel.innerHTML = `
              <div class="demo-success-box">
                <h4>Ciclo Demostrativo Completo Registrado en Base de Datos:</h4>
                <div class="flow-chips-row">
                  <span>1. Solicitud: <strong>${fl.purchase_request}</strong></span> ➔
                  <span>2. Compra: <strong>${fl.purchase_order}</strong></span> ➔
                  <span>3. Recepción: <strong>${fl.material_reception}</strong></span> ➔
                  <span>4. Producción: <strong>${fl.production_order}</strong></span> ➔
                  <span>5. Lote PT: <strong>${fl.finished_goods_lot}</strong></span> ➔
                  <span>6. Venta: <strong>${fl.sales_order}</strong></span>
                </div>
                <div style="margin-top:12px;">
                  <a href="${fl.traceability_url}" class="btn btn-primary btn-small">Ver Trazabilidad de este Lote ➔</a>
                </div>
              </div>
            `;
          }
        } catch (err) {
          toast(err.message, true);
        } finally {
          btn.disabled = false;
          btn.textContent = 'Ejecutar Flujo Completo Demostrativo';
        }
      });
    });
  }

  // Boot enterprise features
  document.addEventListener('DOMContentLoaded', () => {
    initGlobalSearch();
    initModuleLauncher();
    initApprovals();
    initSubnavTabs();
    initProcurement();
    initInventorySuite();
    initManufacturing();
    initQuality();
    initAnalytics();
    initAdministration();
    initProjectLogs();
    initDemoWorkflow();
  });
})();


