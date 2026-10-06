from django.contrib.auth import views as auth_views
from django.urls import path
from studio import views

urlpatterns = [
    path('ingresar/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('salir/', auth_views.LogoutView.as_view(), name='logout'),
    path('demo/entrar/', views.demo_login, name='demo_login'),
    path('cuenta/contrasena/', auth_views.PasswordChangeView.as_view(template_name='studio/password.html', success_url='/'), name='password_change'),
    path('', views.dashboard, name='dashboard'),
    path('colecciones/', views.collection_list, name='collection_list'),
    path('colecciones/nueva/', views.collection_form, name='collection_create'),
    path('colecciones/<int:pk>/', views.collection_detail, name='collection_detail'),
    path('colecciones/<int:pk>/editar/', views.collection_form, name='collection_edit'),
    path('modelos/', views.garment_list, name='garment_list'),
    path('modelos/nuevo/', views.garment_form, name='garment_create'),
    path('modelos/<int:pk>/', views.garment_detail, name='garment_detail'),
    path('modelos/<int:pk>/editar/', views.garment_form, name='garment_edit'),
    path('modelos/<int:pk>/costos/nuevo/', views.budget_line_form, name='budget_create'),
    path('modelos/<int:pk>/costos/<int:line_id>/editar/', views.budget_line_form, name='budget_edit'),
    path('modelos/<int:pk>/costos/<int:line_id>/retirar/', views.delete_budget_line, name='budget_delete'),
    path('modelos/<int:pk>/aprobar/', views.approve, name='budget_approve'),
    path('registro/<str:entity>/<int:pk>/archivar/', views.archive, name='archive'),
    path('avances/nuevo/', views.production_form, name='production_create'),
    path('gastos/', views.expense_list, name='expense_list'),
    path('gastos/nuevo/', views.expense_form, name='expense_create'),
    path('gastos/<int:pk>/pago/', views.paid_form, name='paid_update'),
    path('registro/<str:entity>/<int:pk>/anular/', views.void_form, name='void'),
    path('actividad/', views.activity, name='activity'),
    path('guia/', views.guide, name='guide'),
    path('exportar/<str:entity>/', views.export_csv, name='export'),
    path('respaldo/', views.backup_download, name='backup'),
]
