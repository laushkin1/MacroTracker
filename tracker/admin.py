from django.contrib import admin
from .models import UserProfile, Food, Meal, MealItem

admin.site.register(UserProfile)
admin.site.register(Food)
admin.site.register(Meal)
admin.site.register(MealItem)