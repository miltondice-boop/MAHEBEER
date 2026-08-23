(function(){'use strict';
function money(v){return new Intl.NumberFormat('es-CO',{style:'currency',currency:'COP',maximumFractionDigits:0}).format(Number(v||0))}
let employeeCache=[];
async function getEmployees(){
 const r=await db.from('empleados').select('id,nombre_completo,activo').eq('activo',true).order('nombre_completo');
 if(r.error)throw r.error;
 employeeCache=r.data||[];return employeeCache;
}
async function adjust(emp,sign){
 const raw=prompt((sign>0?'SUMAR / PRÉSTAMO':'DESCONTAR')+' para '+emp.nombre_completo+'\n\nEscribe el valor en pesos, sin signos.');if(raw===null)return;
 const clean=String(raw).replace(/[^0-9.,-]/g,'').replace(/\./g,'').replace(',','.');const amount=Math.abs(Number(clean));
 if(!Number.isFinite(amount)||amount<=0)return alert('Ingresa un valor válido mayor que cero.');
 const note=prompt('Concepto (opcional):',sign>0?'Préstamo/adelanto':'Descuento')||'';
 const r=await db.rpc('registrar_ajuste_personal',{p_empleado_id:emp.id,p_monto:sign*amount,p_observacion:note});
 if(r.error)return alert('No se pudo registrar el ajuste: '+r.error.message);
 alert((sign>0?'Se sumaron ':'Se descontaron ')+money(amount)+' a '+emp.nombre_completo+'.');
 employeeCache=[];try{await getEmployees()}catch(e){};if(typeof window.loadAll==='function')await window.loadAll();setTimeout(addControls,500);
}
async function addControls(){
 const grid=document.getElementById('weeklyGrid');if(!grid)return;
 if(!employeeCache.length){try{await getEmployees()}catch(e){return}}
 Array.from(grid.querySelectorAll('.weekly-card')).forEach(card=>{
  if(card.querySelector('.adjustment-actions'))return;
  const text=(card.querySelector('.wn')?.textContent||card.textContent||'').trim().toLowerCase();
  const emp=employeeCache.find(e=>text.includes(String(e.nombre_completo||'').trim().toLowerCase()));if(!emp)return;
  const box=document.createElement('div');box.className='adjustment-actions';
  box.innerHTML='<div class="adjustment-title">Ajustar pago</div><div class="adjustment-buttons"><button type="button" class="add-money">➕ SUMAR</button><button type="button" class="subtract-money">➖ DESCONTAR</button></div>';
  card.appendChild(box);box.querySelector('.add-money').onclick=()=>adjust(emp,1);box.querySelector('.subtract-money').onclick=()=>adjust(emp,-1);
 });
}
function css(){if(document.getElementById('adjustment-css'))return;const s=document.createElement('style');s.id='adjustment-css';s.textContent='.adjustment-actions{display:block!important;margin-top:10px;padding-top:10px;border-top:1px solid #303842}.adjustment-title{font-size:11px;color:#9ba5b1;margin-bottom:6px;text-transform:uppercase;font-weight:700}.adjustment-buttons{display:grid!important;grid-template-columns:1fr 1fr!important;gap:6px}.adjustment-buttons button{display:block!important;font-size:11px!important;padding:8px 5px!important;margin:0!important;border-radius:8px!important;color:#fff!important}.adjustment-buttons .add-money{background:#165c45!important;border:1px solid #1d8b66!important}.adjustment-buttons .subtract-money{background:#6b3030!important;border:1px solid #a73e3b!important}';document.head.appendChild(s)}
async function init(){css();await addControls();const grid=document.getElementById('weeklyGrid');if(grid)new MutationObserver(()=>setTimeout(addControls,100)).observe(grid,{childList:true,subtree:true})}
const t=setInterval(()=>{if(document.getElementById('weeklyGrid')&&typeof db!=='undefined'){clearInterval(t);init()}},300);
})();