from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

app_name = 'tracker'

urlpatterns = [
    path('', views.daily_dashboard, name='dashboard'),
    path('monthly/', views.monthly_dashboard, name='monthly_dashboard'),

    # Food Routes
    path('food/', views.FoodListView.as_view(), name='food_list'),
    path('food/add/', views.FoodCreateView.as_view(), name='food_create'),
    path('food/barcode/', views.add_by_barcode, name='add_by_barcode'),
    path('food/<int:pk>/edit/', views.FoodUpdateView.as_view(), name='food_update'),
    path('food/<int:pk>/delete/', views.FoodDeleteView.as_view(), name='food_delete'),
    
    # MealLog Routes
    path('meal/add/', views.MealLogCreateView.as_view(), name='meallog_create'),
    path('meal/<int:pk>/edit/', views.MealLogUpdateView.as_view(), name='meallog_update'),
    path('meal/<int:pk>/delete/', views.MealLogDeleteView.as_view(), name='meallog_delete'),

    # Profile & Password Routes
    path('settings/', views.settings_view, name='settings'),
    path('settings/username/', views.edit_username, name='username_edit'),
    path('profile/edit/', views.ProfileUpdateView.as_view(), name='profile_edit'),
    path('profile/password/', auth_views.PasswordChangeView.as_view(
        template_name='registration/password_change.html',
        success_url=reverse_lazy('tracker:dashboard')
    ), name='password_change'),

]