from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Meal type choices used in MealItem.meal_type.
MEAL_CHOICES = [
    ('Breakfast', 'Breakfast'),
    ('Morning Snack', 'Morning Snack'),
    ('Lunch', 'Lunch'),
    ('Afternoon Snack', 'Afternoon Snack'),
    ('Dinner', 'Dinner'),
    ('Second Dinner', 'Second Dinner'),
]


class UserProfile(models.Model):
    """Stores daily macro and calorie limits for one user."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    daily_calories_limit = models.PositiveIntegerField(
        default=0,
        verbose_name='Calorie limit',
    )
    daily_protein_limit = models.PositiveIntegerField(
        default=0,
        verbose_name='Protein limit (g)',
    )
    daily_fat_limit = models.PositiveIntegerField(
        default=0,
        verbose_name='Fat limit (g)',
    )
    daily_carbs_limit = models.PositiveIntegerField(
        default=0,
        verbose_name='Carb limit (g)',
    )

    def __str__(self):
        return f'User limits {self.user.username}'


class Food(models.Model):
    """Stores nutritional data for one food product per 100 g."""

    name = models.CharField(max_length=255, verbose_name='Product name')
    # Barcode value from OpenFoodFacts API. Optional.
    barcode = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='Barcode (for API)',
    )
    calories = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        default=0,
        verbose_name='Calories (per 100g)',
    )
    protein = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=0,
        verbose_name='Protein (per 100g)',
    )
    fat = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=0,
        verbose_name='Fat (per 100g)',
    )
    carbs = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=0,
        verbose_name='Carb (per 100g)',
    )
    portions = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Custom Portions',
    )
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='food',
        null=True,
        blank=True,
        help_text='User who owns the record',
    )

    class Meta:
        unique_together = ('owner', 'name')
        ordering = ['-id']

    def __str__(self):
        return self.name


class MealItem(models.Model):
    """Stores one food entry linked to a user, a date, and a meal type."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='meal_items',
    )
    date = models.DateField(default=timezone.now, verbose_name='Date')
    meal_type = models.CharField(
        max_length=50,
        choices=MEAL_CHOICES,
        verbose_name='Meal Type',
    )
    food = models.ForeignKey(
        'Food',
        on_delete=models.CASCADE,
        related_name='meal_items',
    )
    weight_grams = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Portion weight (in grams)',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.food.name} - {self.meal_type} ({self.date})'

    @property
    def total_calories(self):
        """Return calories for the logged weight."""
        return (self.food.calories * self.weight_grams) / 100

    @property
    def total_protein(self):
        """Return protein (g) for the logged weight."""
        return (self.food.protein * self.weight_grams) / 100

    @property
    def total_fat(self):
        """Return fat (g) for the logged weight."""
        return (self.food.fat * self.weight_grams) / 100

    @property
    def total_carbs(self):
        """Return carbs (g) for the logged weight."""
        return (self.food.carbs * self.weight_grams) / 100