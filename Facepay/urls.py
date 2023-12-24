"""
URL configuration for Facepay project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from Facepay import views
from django.conf import settings
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('login/', views.user_login, name='login'),
    path('signup/', views.signup, name='signup'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/',views.profile,name='profile'),
    path('transaction/',views.transaction,name='transaction'),
    path('receive/',views.receive,name='receive'),
    path('loadBalance/',views.loadBalance,name='loadBalance'),
    path('transferBalance/',views.transferBalance,name='transferBalance'),
    path('process_image/', views.process_image, name='process_image'),
    path('update/', views.update, name='update'),
    path('pinpage/', views.pinpage, name='pinpage'),
    path('confirm-transaction/',views.check_data, name='check_in_database')
]

if settings.DEBUG:
    urlpatterns+=static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

