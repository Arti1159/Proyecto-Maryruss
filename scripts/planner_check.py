"""End-to-end planner workflow; isolated demo instance on 8002 only."""
import csv
import io
import json
import os
import time
from datetime import datetime,timedelta
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright
BASE=os.environ.get('MARYRUSS_E2E_URL','http://127.0.0.1:8002')
url=urlparse(BASE)
if url.hostname not in ('127.0.0.1','localhost') or url.port!=8002:raise SystemExit('Usa demo aislada en el puerto 8002.')
OUTPUT=Path('test-results');OUTPUT.mkdir(exist_ok=True)
checks=[];errors=[]
def check(label,condition):
    assert condition,label
    checks.append(label)
def overflow(page):return page.evaluate('document.documentElement.scrollWidth > innerWidth')

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
    context=browser.new_context(viewport={'width':1440,'height':1000})
    page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(BASE+'/ingresar/');page.get_by_role('button',name='Entrar a la demostración').click();page.wait_for_url(BASE+'/')
    page.get_by_role('link',name='Planificador',exact=True).click()
    check('Área Planificador accesible desde menú',page.url==BASE+'/planificador/')
    page.get_by_role('link',name='Nueva colección a planificar').click()
    today=datetime.now(ZoneInfo('America/Lima')).date()
    for field,value in {'name':'UI · Plan '+str(time.time_ns()),'launch_date':str(today+timedelta(days=30)),'sell_by':str(today+timedelta(days=59)),'budget':'1000','reserve':'100','fixed_costs':'100','fixed_notes':'Fotos y transporte fijo de prueba','assumptions':'Prueba manual, no ventas garantizadas'}.items():page.locator('#id_'+field).fill(value)
    page.get_by_role('button',name='Guardar registro').click();page.wait_for_url('**/planificador/*/')
    plan_url=page.url
    page.get_by_role('link',name='Añadir producto',exact=False).click()
    for field,value in {'name':'Blusa de prueba','material':'Algodón','unit_cost':'20','minimum_model':'10','minimum_color':'5','multiple':'5','capacity':'60','lead_days':'10','retail_price':'40','wholesale_price':'30','colors':'Negro','sizes':'M, L'}.items():page.locator('#id_'+field).fill(value)
    page.locator('#id_material_available').check();page.locator('#id_cost_confirmed').check()
    page.get_by_role('button',name='Guardar registro').click();page.wait_for_url('**#productos')
    rows=page.locator('#variantes tbody tr[data-variant-id]')
    check('Variantes creadas con colores y tallas ingresados',rows.count()==2)
    first_id=rows.nth(0).get_attribute('data-variant-id')
    rows.nth(0).locator('[name$="-stock"]').fill('10')
    rows.nth(0).locator('[name$="-target"]').fill('30')
    rows.nth(1).locator('[name$="-target"]').fill('20')
    for i in (0,1):rows.nth(i).locator('[name$="-quantity"]').fill('20')
    page.wait_for_function('document.getElementById("plan-preview-status").textContent.includes("Cambios sin guardar")')
    check('Vista previa variable exacta', '800.00' in page.locator('#plan-variable').inner_text())
    check('Reserva y fijos sin duplicación','0.00' in page.locator('#plan-remaining').inner_text())
    check('Costo con fijos distribuidos','22.50' in page.locator('#plan-full-unit').inner_text())
    page.get_by_role('button',name='Proponer tres planes',exact=True).click()
    check('No se guardan versiones con cambios locales pendientes','Tienes cambios sin guardar' in page.locator('#plan-preview-status').inner_text())
    page.get_by_role('button',name='Guardar borrador',exact=True).click();page.wait_for_url('**#variantes')
    page.reload()
    check('Borrador conservado al recargar',page.locator('#plan-units').inner_text()=='40')
    check('Costos y caja diferenciados','Resultado bruto estimado' in page.locator('#resultados').inner_text() and 'Diferencia de caja' in page.locator('#resultados').inner_text())
    page.get_by_role('button',name='Proponer tres planes',exact=True).click();page.wait_for_url('**#versiones')
    check('Tres propuestas guardadas sin alterar borrador',page.locator('.plan-version-list>a').count()==3 and page.locator('#plan-units').inner_text()=='40')
    page.locator('.plan-version-list>a').filter(has_text='Conservador').click()
    check('Propuesta explica cantidad y confianza','Objetivo ingresado por ti' in page.locator('main').inner_text() and 'Baja · supuesto manual' in page.locator('main').inner_text())
    check('Propuesta conserva regla visible','factor 0.60' in page.locator('main').inner_text())
    version_url=page.url
    page.get_by_role('button',name='Cargar cantidades al borrador').click();page.wait_for_url('**#variantes')
    check('Cargar simulación actualiza solo borrador',page.locator('#plan-units').inner_text()=='25')
    page.get_by_role('link',name='Añadir evidencia').click()
    variant_options=page.locator('#id_variant option').all_text_contents()
    check('Registro de evidencia permite identificar variante',any('Negro · M' in value for value in variant_options))
    page.locator('#id_variant').select_option(first_id);page.locator('#id_kind').select_option('sales')
    for field,value in {'title':'Ventas propias de prueba','units':'10','period_start':str(today-timedelta(days=9)),'period_end':str(today),'days_in_stock':'5','signal':'Registro ficticio para verificar el cálculo; no es evidencia real del mercado.'}.items():page.locator('#id_'+field).fill(value)
    page.get_by_role('button',name='Guardar registro').click();page.wait_for_url('**#evidencia')
    check('Evidencia propia visible en plan','Ventas propias de prueba' in page.locator('#evidencia').inner_text())
    page.locator('#variantes tbody tr[data-variant-id]').first.locator('[name$="-target"]').fill('')
    page.get_by_role('button',name='Guardar borrador',exact=True).click();page.wait_for_url('**#variantes')
    page.get_by_role('button',name='Proponer tres planes').click();page.wait_for_url('**#versiones')
    page.locator('.plan-version-list>a').filter(has_text='Equilibrado').first.click()
    check('Ventas ajustadas por días con stock explicadas','10 / 5 días con stock × 30 días del plan' in page.locator('main').inner_text())
    page.get_by_role('button',name='Cargar cantidades al borrador').click();page.wait_for_url('**#variantes')
    page.locator('[name="reviewed"]').check()
    page.get_by_role('button',name='Aprobar versión del plan').click();page.wait_for_url('**/version/*/')
    approved_url=page.url
    check('Aprobación conserva versión del plan','Plan revisado y aprobado' in page.locator('main').inner_text())
    check('Evidencia conservada en versión','Ventas propias de prueba' in page.locator('main').inner_text())
    check('Margen y recargo distintos y explicados','margen sobre venta 50.00%' in page.locator('main').inner_text() and 'recargo sobre costo 100.00%' in page.locator('main').inner_text())
    with page.expect_download() as info:page.get_by_role('link',name='CSV del plan',exact=True).click()
    path=OUTPUT/'planificador-plan.csv';info.value.save_as(str(path))
    exported=list(csv.reader(io.StringIO(path.read_text(encoding='utf-8-sig'))))
    check('CSV coincide con plan aprobado',sum(int(row[8]) for row in exported[1:] if row[0]=='Plan revisado')==40)
    for entity in ('CSV de evidencia','CSV de supuestos'):
        with page.expect_download() as info:page.get_by_role('link',name=entity,exact=True).click()
        check(entity+' descargable',bool(info.value.suggested_filename))
    page.emulate_media(media='print')
    check('Resumen imprimible sin navegación',page.locator('.sidebar').evaluate('(e)=>getComputedStyle(e).display')=='none')
    page.emulate_media(media='screen')
    page.goto(plan_url)
    check('Investigación no simula conexión inexistente','Sin investigación actual online' in page.locator('#evidencia').inner_text() and page.get_by_role('button',name='Analizar temporada').is_disabled())
    product_edit=page.get_by_role('link',name='Editar producto',exact=True).get_attribute('href')
    evidence_create=page.get_by_role('link',name='Añadir evidencia').get_attribute('href')
    paths=['/planificador/',urlparse(plan_url).path,product_edit,evidence_create,urlparse(approved_url).path]
    for theme in ('light','dark'):
        page.get_by_label('Tema de la aplicación').select_option(theme)
        page.set_viewport_size({'width':390,'height':844})
        for path in paths:
            page.goto(BASE+path)
            check(theme+': planificador sin desborde '+path,not overflow(page))
            check(theme+': tema aplicado '+path,page.locator('html').get_attribute('data-theme')==theme)
        page.goto(plan_url);page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
        page.screenshot(path=str(OUTPUT/('planificador-'+theme+'-movil.png')),full_page=True)
    page.set_viewport_size({'width':1440,'height':1000});page.goto(plan_url)
    page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
    page.screenshot(path=str(OUTPUT/'planificador-oscuro-desktop.png'),full_page=True)
    check('Sin errores JavaScript',not errors)
    browser.close()
result={'passed':len(checks),'checks':checks,'javascript_errors':errors}
(OUTPUT/'planner-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2))
