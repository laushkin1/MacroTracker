from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    daily_calories_limit = models.PositiveIntegerField(default=0, verbose_name="Calorie limit")
    daily_protein_limit = models.PositiveIntegerField(default=0, verbose_name="Protein limit (g)")
    daily_fat_limit = models.PositiveIntegerField(default=0, verbose_name="Fat limit (g)")
    daily_carbs_limit = models.PositiveIntegerField(default=0, verbose_name="Carb limit (g)")

    def __str__(self):
        return f"User limits {self.user.username}"


class Food(models.Model):
    name = models.CharField(max_length=255, verbose_name="Product name")
    # Field for parsing from OpenFoodFacts
    barcode = models.CharField(max_length=50, blank=True, null=True, verbose_name="Barcode (for API)")

    calories = models.DecimalField(max_digits=6, decimal_places=1, default=0, verbose_name="Calories (per 100g)")
    protein = models.DecimalField(max_digits=5, decimal_places=1, default=0, verbose_name="Protein (per 100g)")
    fat = models.DecimalField(max_digits=5, decimal_places=1, default=0, verbose_name="Fat (per 100g)")
    carbs = models.DecimalField(max_digits=5, decimal_places=1, default=0, verbose_name="Carb (per 100g)")

    portions = models.JSONField(default=dict, blank=True, verbose_name="Custom Portions")

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='food',
        null=True,
        blank=True,
        help_text='User who owns the record'
    )

    class Meta:
        unique_together = ('owner', 'name')
        ordering = ['-id']

    def __str__(self):
        return self.name


class Meal(models.Model):
    """A meal container (e.g. Breakfast, Lunch) grouping multiple food items."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meals')
    name = models.CharField(max_length=255, verbose_name="Meal name")
    date = models.DateField(default=timezone.now, verbose_name="Date")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.name} ({self.date})"

    @property
    def total_weight(self):
        return sum(item.weight_grams for item in self.items.all())

    @property
    def total_calories(self):
        return sum(item.total_calories for item in self.items.all())

    @property
    def total_protein(self):
        return sum(item.total_protein for item in self.items.all())

    @property
    def total_fat(self):
        return sum(item.total_fat for item in self.items.all())

    @property
    def total_carbs(self):
        return sum(item.total_carbs for item in self.items.all())


class MealItem(models.Model):
    """A single food entry inside a Meal container."""
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE, related_name='items')
    food = models.ForeignKey(Food, on_delete=models.CASCADE, related_name='meal_items')
    weight_grams = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Portion weight (in grams)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.food.name} - {self.weight_grams}g"

    @property
    def total_calories(self):
        return (self.food.calories * self.weight_grams) / 100

    @property
    def total_protein(self):
        return (self.food.protein * self.weight_grams) / 100

    @property
    def total_fat(self):
        return (self.food.fat * self.weight_grams) / 100

    @property
    def total_carbs(self):
        return (self.food.carbs * self.weight_grams) / 100