'use strict';
document.querySelectorAll('[data-print]').forEach(button=>button.addEventListener('click',()=>window.print()));
const planForm=document.querySelector('[data-plan-preview]');
if(planForm){
  let timer,controller;
  const status=document.getElementById('plan-preview-status');
  const savedValues=new URLSearchParams(new FormData(planForm)).toString();
  document.addEventListener('submit',event=>{
    if(event.target.matches('[data-plan-needs-save]')&&new URLSearchParams(new FormData(planForm)).toString()!==savedValues){
      event.preventDefault();event.stopImmediatePropagation();
      status.textContent='Tienes cambios sin guardar. Pulsa Guardar borrador antes de proponer, guardar una versión o aprobar.';
      status.scrollIntoView({block:'center',behavior:'smooth'});
    }
  },true);
  const format=new Intl.NumberFormat('es-PE',{style:'currency',currency:planForm.dataset.currency});
  const amount=value=>value===null?'Por confirmar':format.format(Number(value));
  const list=(id,values)=>document.getElementById(id).replaceChildren(...values.map(value=>{const li=document.createElement('li');li.textContent=value;return li;}));
  const preview=async()=>{
    if(controller)controller.abort();controller=new AbortController();
    status.textContent='Calculando vista previa sin guardar…';
    try{
      const response=await fetch(planForm.dataset.planPreview,{method:'POST',body:new FormData(planForm),signal:controller.signal,headers:{'Accept':'application/json'}});
      if(!response.headers.get('Content-Type')?.includes('application/json'))throw new Error('Sesión o conexión no disponible.');
      const data=await response.json();
      if(!data.valid){status.textContent=data.error;return;}
      document.getElementById('plan-variable').textContent=data.costs_complete?amount(data.variable):'Costo pendiente';
      document.getElementById('plan-remaining').textContent=data.costs_complete?amount(data.remaining):'Por confirmar';
      document.getElementById('plan-remaining').classList.toggle('text-danger',Number(data.remaining)<0);
      document.getElementById('plan-units').textContent=data.units;
      document.getElementById('plan-full-unit').textContent=amount(data.full_unit_cost);
      document.querySelector('[data-plan-unit-count]').textContent=data.units;
      list('plan-errors',data.errors);list('plan-warnings',data.warnings);
      data.rows.forEach(row=>{const cell=planForm.querySelector(`[data-variant-id="${row.variant_id}"] [data-row-total]`);if(cell)cell.textContent=row.unit_cost===null&&row.quantity?'Por confirmar':amount(row.total);});
      status.textContent=(data.ready?'Vista previa: lote factible con costos confirmados.':data.feasible?'Vista previa: simulación dentro del presupuesto.':'Vista previa con conflictos: revisa las restricciones.')+' Cambios sin guardar.';
    }catch(error){if(error.name!=='AbortError')status.textContent='No se pudo recalcular. Revisa tu conexión y sesión. Guarda el borrador para comprobarlo en el servidor.';}
  };
  planForm.addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(preview,250);});
  planForm.addEventListener('change',()=>{clearTimeout(timer);timer=setTimeout(preview,250);});
}
