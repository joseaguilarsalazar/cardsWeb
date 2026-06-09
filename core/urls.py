# urls.py
from django.urls import path
from .views import (
    login_view, home_view, logout_view, create_card_view,
    card_detail_view, edit_card_view, delete_card_view,
    quiz_view, setup_password_view)


urlpatterns = [
    path('', home_view, name='home'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('nueva-entrada/', create_card_view, name='create_card'),

    path('entrada/<int:card_id>/', card_detail_view, name='card_detail'),
    path('entrada/<int:card_id>/editar/', edit_card_view, name='edit_card'),
    path('entrada/<int:card_id>/eliminar/', delete_card_view, name='delete_card'),

    path('recuerdos/', quiz_view, name='quiz'),
    path('configurar-contrasena/', setup_password_view, name='setup_password'),
]