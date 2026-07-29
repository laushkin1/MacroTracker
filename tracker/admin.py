from django.contrib import admin
from .models import UserProfile, Food, MealItem

admin.site.register(UserProfile)
admin.site.register(Food)
admin.site.register(MealItem)