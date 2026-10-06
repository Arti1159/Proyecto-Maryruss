from django.conf import settings
from django.utils import timezone

def environment(request):
    return {'demo_mode': settings.DEMO_MODE, 'today': timezone.localdate()}
