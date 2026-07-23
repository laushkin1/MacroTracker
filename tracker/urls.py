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

    # Meal (container) Routes
    path('meal/add/', views.meal_create, name='meal_create'),
    path('meal/<int:pk>/edit/', views.meal_edit, name='meal_edit'),
    path('meal/<int:pk>/delete/', views.meal_delete, name='meal_delete'),
    path('meal/<int:pk>/duplicate/', views.meal_duplicate, name='meal_duplicate'),

    # MealItem Routes
    path('meal/<int:meal_pk>/item/add/', views.meal_item_add, name='meal_item_add'),
    path('meal-item/<int:pk>/edit/', views.meal_item_edit, name='meal_item_edit'),
    path('meal-item/<int:pk>/delete/', views.meal_item_delete, name='meal_item_delete'),
    path('meal-item/<int:pk>/duplicate/', views.meal_item_duplicate, name='meal_item_duplicate'),

    # Profile & Password Routes
    path('settings/', views.settings_view, name='settings'),
    path('settings/username/', views.edit_username, name='username_edit'),
    path('profile/edit/', views.ProfileUpdateView.as_view(), name='profile_edit'),
    path('profile/password/', auth_views.PasswordChangeView.as_view(
        template_name='registration/password_change.html',
        success_url=reverse_lazy('tracker:dashboard')
    ), name='password_change'),
]