from django.urls import path
from . import views
app_name='planner'
urlpatterns=[
    path('',views.index,name='index'),
    path('nuevo/',views.project_form,name='create'),
    path('<int:pk>/',views.detail,name='detail'),
    path('<int:pk>/editar/',views.project_form,name='edit'),
    path('<int:pk>/cantidades/',views.quantities,name='quantities'),
    path('<int:pk>/vista-previa/',views.quantities,{'preview':True},name='preview'),
    path('<int:pk>/productos/nuevo/',views.product_form,name='product_create'),
    path('<int:pk>/productos/<int:product_id>/editar/',views.product_form,name='product_edit'),
    path('<int:pk>/productos/<int:product_id>/componente/',views.child_form,{'kind':'component'},name='component_create'),
    path('<int:pk>/productos/<int:product_id>/componente/<int:child_id>/',views.child_form,{'kind':'component'},name='component_edit'),
    path('<int:pk>/productos/<int:product_id>/variante/',views.child_form,{'kind':'variant'},name='variant_create'),
    path('<int:pk>/productos/<int:product_id>/variante/<int:child_id>/',views.child_form,{'kind':'variant'},name='variant_edit'),
    path('<int:pk>/evidencia/nueva/',views.evidence_form,name='evidence_create'),
    path('<int:pk>/evidencia/<int:evidence_id>/',views.evidence_form,name='evidence_edit'),
    path('<int:pk>/proponer/',views.generate,name='generate'),
    path('<int:pk>/guardar-version/',views.version_save,name='save'),
    path('<int:pk>/version/<int:version_id>/',views.version_detail,name='version'),
    path('<int:pk>/version/<int:version_id>/cargar/',views.apply_version,name='apply'),
    path('<int:pk>/version/<int:version_id>/exportar/<str:entity>/',views.export,name='export'),
    path('<int:pk>/investigar/',views.research,name='research'),
]
