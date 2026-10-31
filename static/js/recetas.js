(async () => {
 const esc = v => String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const money = v => 'C$ '+Number(v).toFixed(2);
 try {
  const token=sessionStorage.getItem('erp_token');if(!token)return;
  const res=await fetch('/enterprise/soap-catalog',{headers:{Authorization:'Bearer '+token}});
  if(!res.ok)throw Error('No se pudo cargar el catálogo');
  const c=await res.json(), ins=Object.fromEntries(c.insumos.map(r=>[r[0],{name:r[1],cost:r[3]}]));
  const cost=p=>p.ingredientes ? (p.ingredientes.reduce((s,[sku,q])=>s+q*ins[sku].cost,0)+p.mano_obra_lote+p.indirectos_lote)/p.lote_base : p.costo_compra;
  for(const p of c.productos)ins[p.sku]={name:p.nombre,cost:cost(p)};
  document.getElementById('recipe-status').textContent=c.nota;
  document.getElementById('recipe-cards').innerHTML=c.productos.map(p=>`<article class="panel" style="padding:24px"><p class="eyebrow">${esc(p.sku)} · ${esc(p.categoria)}</p><h2>${esc(p.nombre)}</h2><p>Precio ejemplo: <strong>${money(p.precio)}</strong> · Costo estimado: <strong>${money(ins[p.sku].cost)}</strong></p><p>Margen estimado sobre venta: ${((p.precio-ins[p.sku].cost)/p.precio*100).toFixed(1)}%. No incluye impuestos, comisiones ni distribución.</p>${p.ingredientes?`<h3>Fórmula para ${p.lote_base} unidad(es)</h3><div class="table-scroll"><table><thead><tr><th>Insumo</th><th>Cantidad</th></tr></thead><tbody>${p.ingredientes.map(([sku,q])=>`<tr><td>${esc(ins[sku].name)}</td><td>${q}</td></tr>`).join('')}</tbody></table></div><p>Mano de obra por lote: ${money(p.mano_obra_lote)} · Indirectos: ${money(p.indirectos_lote)}</p>`:'<p>Accesorio de reventa; se compra terminado.</p>'}<h3>Procedimiento</h3><ol>${p.pasos.map(s=>`<li>${esc(s)}</li>`).join('')}</ol><h3>Control de calidad</h3><p>${esc(p.calidad)}</p></article>`).join('')+`<article class="panel" style="padding:24px;grid-column:1/-1"><h2>Condiciones de fabricación</h2><ul>${c.condiciones.map(s=>`<li>${esc(s)}</li>`).join('')}</ul><p>Costos de planificación del archivo data/catalogo.json. Cambiar precios de venta en Productos no recalcula estos supuestos.</p></article>`;
 }catch(e){document.getElementById('recipe-status').textContent=e.message;}
})();
