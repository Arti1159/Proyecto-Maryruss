"""Real server-side Tavily search/reading. No credentials means no fabricated results."""
import hashlib
import json
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from urllib.request import Request, urlopen
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import ResearchRun, Evidence

MAX_RESPONSE=2*1024*1024

def configured():return bool(settings.MARYRUSS_RESEARCH_API_KEY)

def canonical_url(value):
    if not isinstance(value,str):return ''
    try:parts=urlsplit(value)
    except ValueError:return ''
    if parts.scheme not in ('http','https') or not parts.hostname or parts.username or parts.password:return ''
    # Fragments and tracking queries do not create independent evidence.
    params=[(key,value) for key,value in parse_qsl(parts.query,keep_blank_values=True) if not key.lower().startswith('utm_') and key.lower() not in ('fbclid','gclid')]
    return urlunsplit((parts.scheme,parts.netloc.lower(),parts.path.rstrip('/'),urlencode(params),''))

def research_query(project):
    products=', '.join(p.name+' '+p.category+' '+p.material for p in project.products.all())[:700]
    return f'Ropa moda catálogos precios colores materiales {project.market} {project.resale_cities} {project.style} {project.audience} {products} temporada lanzamiento {project.launch_date} publicaciones últimos {project.research_days} días'

def run_research(project,force=False):
    if not configured():raise ValidationError('Investigación online sin conectar. Configura Tavily en el servidor; mientras tanto puedes registrar evidencia manual.')
    query=research_query(project)
    fingerprint=hashlib.sha256(query.encode()).hexdigest()
    cached=project.research_runs.filter(fingerprint=fingerprint,created_at__gte=timezone.now()-timedelta(hours=6)).first()
    if cached and not force:return cached,True
    request=Request('https://api.tavily.com/search',data=json.dumps({'query':query,'search_depth':'basic','max_results':8,'include_raw_content':True,'include_answer':False}).encode(),headers={'Authorization':'Bearer '+settings.MARYRUSS_RESEARCH_API_KEY,'Content-Type':'application/json','Accept':'application/json'},method='POST')
    try:
        with urlopen(request,timeout=25) as response:
            raw=response.read(MAX_RESPONSE+1)
        if len(raw)>MAX_RESPONSE:raise ValueError('Respuesta demasiado grande')
        payload=json.loads(raw)
        if not isinstance(payload.get('results'),list):raise ValueError('Respuesta sin fuentes')
    except (HTTPError,URLError,TimeoutError,ValueError,OSError) as error:
        # Never return the key, upstream request, or full error payload to a browser or logs.
        raise ValidationError('No se pudo consultar el servicio de investigación. Revisa su conexión, clave y cuota en el servidor. Tu presupuesto sigue disponible.') from error
    sources=[];seen=set()
    for result in payload['results'][:8]:
        if not isinstance(result,dict):continue
        url=canonical_url(result.get('url',''))
        if not url or url in seen:continue
        seen.add(url)
        source={'url':url,'title':str(result.get('title') or 'Fuente sin título')[:180], 'excerpt':str(result.get('raw_content') or result.get('content') or '')[:16000], 'published_date':result.get('published_date') or None,'consulted_at':timezone.now().isoformat(),'market':'Por verificar: consulta para '+project.market,'limitation':'Resultado de búsqueda, no venta comprobada. Verifica región, fecha de publicación, comparabilidad y campaña antes de usarlo. La consulta no prueba actualidad.'}
        source['reading_available']=bool(result.get('raw_content'))
        if not source['reading_available']:source['limitation']+=' Texto completo no disponible: se conserva el extracto de búsqueda.'
        sources.append(source)
    report={'provider':'Tavily','sources':sources,'sample_size':len(sources),'limitations':['No se infieren ventas, tallas ni cantidades de la popularidad online.','No hay acceso garantizado a feeds privados o publicaciones bloqueadas.','Sin comparación temporal no se clasifica una tendencia como ascendente o descendente.','Esta muestra no garantiza cobertura completa del mercado.','La ventana de la consulta solicita actualidad; las fechas de publicación se conservan como desconocidas si el servicio no las aporta.'],'trend_status':'Evidencia insuficiente para clasificar evolución: revisar y contrastar fuentes.'}
    return ResearchRun.objects.create(project=project,fingerprint=fingerprint,query=query,report=report),False

def evidence_report(project):
    seen=set();rows=[];duplicates=0
    for item in project.evidence.all():
        key=('campaign',item.campaign.casefold()) if item.campaign else ('url',canonical_url(item.url)) if item.url else ('record',item.pk)
        if key in seen and item.kind=='external':duplicates+=1;continue
        if item.kind=='external':seen.add(key)
        rows.append(item)
    cutoff=timezone.localdate()-timedelta(days=project.research_days)
    unknown=sum(e.kind=='external' and e.published_date is None for e in rows)
    stale=sum(e.kind=='external' and e.published_date is not None and e.published_date<cutoff for e in rows)
    local=sum(e.kind=='external' and e.source_type=='local' for e in rows)
    return {'rows':rows,'sample_size':len(rows),'duplicates':duplicates,'unknown_dates':unknown,'stale':stale,'local':local,'trend_status':'Evidencia insuficiente para clasificar ascenso o descenso. Las observaciones son referencias; las decisiones de talla y cantidad priorizan tus ventas y reservas.'}
