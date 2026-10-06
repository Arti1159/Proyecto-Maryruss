"""Run only against the isolated demo test instance on port 8002, never the real DB."""
import json
import os
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

BASE = os.environ.get('MARYRUSS_E2E_URL', 'http://127.0.0.1:8002')
address = urlparse(BASE)
if address.hostname not in ('127.0.0.1', 'localhost') or address.port != 8002:
    raise SystemExit('Esta prueba requiere una instancia demo aislada en el puerto 8002.')
OUTPUT = Path(os.environ.get('MARYRUSS_E2E_OUTPUT', 'test-results'))
OUTPUT.mkdir(parents=True, exist_ok=True)
checks = []
errors = []

def check(label, condition):
    assert condition, label
    checks.append(label)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'), headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width':1440, 'height':1000})
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(BASE + '/ingresar/')
    page.get_by_role('button', name='Entrar a la demostración').click()
    page.wait_for_url(BASE + '/')
    check('Demo aislada identificada', page.get_by_text('DEMO · datos ficticios').is_visible())
    page.goto(BASE + '/colecciones/nueva/')
    page.get_by_label('Nombre', exact=False).fill('Prueba de recorrido completo')
    page.get_by_label('Presupuesto disponible').fill('2000')
    page.get_by_role('button', name='Guardar registro').click()
    page.wait_for_url('**/colecciones/*/')
    collection_url = page.url
    page.get_by_role('link', name='Añadir modelo').click()
    page.get_by_label('Código').fill('E2E-001')
    page.get_by_label('Nombre del modelo').fill('Blusa de prueba completa')
    page.get_by_label('Unidades previstas').fill('20')
    page.get_by_label('Taller / responsable').fill('Taller de prueba')
    page.get_by_role('button', name='Guardar registro').click()
    page.wait_for_url('**/modelos/*/')
    model_url = page.url
    for category, label, basis, quantity, unit, price in [
        ('fabric', 'Tela 1.2 m', 'unit', '1.2', 'm', '10'),
        ('supplies', 'Botones', 'unit', '4', 'unidad', '0.5'),
        ('sewing', 'Confección', 'unit', '1', 'prenda', '8'),
        ('packaging', 'Empaque', 'unit', '1', 'prenda', '1'),
        ('transport', 'Servicio fijo', 'batch', '1', 'servicio', '100'),
    ]:
        page.get_by_role('link', name='Añadir concepto').click()
        page.get_by_label('Categoría').select_option(category)
        page.get_by_label('Concepto').fill(label)
        page.get_by_label('Se aplica').select_option(basis)
        page.get_by_label('Cantidad / consumo').fill(quantity)
        page.locator('#id_unit').fill(unit)
        page.get_by_label('Precio por unidad de insumo').fill(price)
        page.get_by_role('button', name='Guardar registro').click()
        page.wait_for_url('**#presupuesto')
    check('Presupuesto total calculado', 'S/ 560.00' in page.locator('#presupuesto').inner_text())
    check('Presupuesto unitario calculado', 'S/ 28.00' in page.locator('#presupuesto').inner_text())
    page.on('dialog', lambda dialog: dialog.accept())
    page.get_by_role('button', name='Aprobar presupuesto', exact=True).click()
    page.wait_for_url(model_url)
    check('Aprobación registrada', page.get_by_text('Presupuesto y unidades aprobados.').is_visible())
    for stage in ['cut', 'sewing', 'finishing', 'approved']:
        page.get_by_role('link', name='Registrar avance', exact=False).first.click()
        page.get_by_label('Etapa completada').select_option(stage)
        page.get_by_label('Unidades adicionales').fill('10')
        page.get_by_role('button', name='Guardar registro').click()
        page.wait_for_url('**#produccion')
    check('Producción parcial de 10 prendas', '10 buenas' in page.locator('#produccion').inner_text())
    page.get_by_role('link', name='Registrar costo', exact=False).first.click()
    page.get_by_label('Categoría').select_option('fabric')
    page.get_by_label('Concepto').fill('Consumos y servicios de 10 prendas')
    page.get_by_label('Costo real total').fill('330')
    page.get_by_label('Importe pagado').fill('100')
    page.get_by_role('button', name='Guardar registro').click()
    page.wait_for_url('**#gastos')
    check('Costo por unidad del plan', 'S/ 16.50' in page.locator('main').inner_text())
    check('Costo por prenda buena', 'S/ 33.00' in page.locator('main').inner_text())
    check('Costo y pago separados', 'S/ 330.00 registrados · S/ 100.00 pagados · S/ 230.00 pendientes' in page.locator('#gastos').inner_text())
    page.locator('#gastos').get_by_role('link', name='Pago', exact=True).click()
    page.get_by_label('Total pagado acumulado').fill('200')
    page.get_by_role('button', name='Guardar registro').click()
    page.wait_for_url('**#gastos')
    check('Pago actualizado sin duplicar costo', 'S/ 330.00 registrados · S/ 200.00 pagados · S/ 130.00 pendientes' in page.locator('#gastos').inner_text())
    from concurrent.futures import ThreadPoolExecutor
    from datetime import datetime
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen
    from zoneinfo import ZoneInfo
    import uuid
    cookies = {c['name']: c['value'] for c in page.context.cookies()}
    csrf_cookie = next(name for name in cookies if name.endswith('_csrf'))
    def concurrent_cut(_):
        data = urlencode({'garment': model_url.rstrip('/').split('/')[-1], 'stage': 'cut', 'quantity': '8',
                          'date': str(datetime.now(ZoneInfo('America/Lima')).date()), 'token': str(uuid.uuid4()),
                          'csrfmiddlewaretoken': cookies[csrf_cookie]}).encode()
        request = Request(BASE + '/avances/nuevo/', data=data, headers={
            'Cookie': '; '.join(f'{k}={v}' for k,v in cookies.items()), 'Referer': BASE + '/avances/nuevo/'})
        with urlopen(request, timeout=20) as response:
            return response.read().decode()
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(concurrent_cut, range(2)))
    check('Concurrencia: una operación excedente rechazada', sum('El corte no puede superar' in r for r in responses) == 1)
    page.goto(model_url)
    check('Concurrencia: saldo conservado en 18 cortadas', page.locator('.stage-grid > div').first.locator('strong').inner_text() == '18')
    page.screenshot(path=str(OUTPUT / 'modelo-desktop.png'), full_page=True, animations='disabled')
    page.reload()
    check('Registros conservados tras recarga', 'S/ 330.00 registrados' in page.locator('#gastos').inner_text())
    with page.expect_download() as info:
        page.goto(BASE + '/guia/')
        page.get_by_role('link', name='Descargar respaldo').click()
    downloaded = info.value
    downloaded.save_as(str(OUTPUT / 'respaldo-recorrido.zip'))
    check('Respaldo completo descargado', (OUTPUT / 'respaldo-recorrido.zip').stat().st_size > 1000)
    mobile = browser.new_page(viewport={'width':390,'height':844}, storage_state=page.context.storage_state())
    mobile.on('pageerror', lambda error: errors.append(str(error)))
    for path in ['/', '/modelos/', '/colecciones/', '/gastos/', '/gastos/nuevo/', model_url.removeprefix(BASE)]:
        mobile.goto(BASE + path)
        check('Sin desborde móvil: ' + path, mobile.evaluate('document.documentElement.scrollWidth <= innerWidth'))
    mobile.goto(model_url)
    mobile.screenshot(path=str(OUTPUT / 'modelo-movil.png'), full_page=True, animations='disabled')
    mobile.get_by_role('button', name='Abrir menú').click()
    mobile.get_by_role('link', name='Resumen', exact=True).click()
    check('Navegación móvil operativa', mobile.url == BASE + '/')
    check('Sin errores de JavaScript', not errors)
    browser.close()
result = {'passed': len(checks), 'checks': checks, 'javascript_errors': errors}
(OUTPUT / 'browser-check.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
print(json.dumps(result, ensure_ascii=False, indent=2))
