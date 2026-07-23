from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Food, Meal, MealItem


class MealItemWeightTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.food = Food.objects.create(
            name='Chicken Breast',
            calories=Decimal('165.0'),
            protein=Decimal('31.0'),
            fat=Decimal('3.6'),
            carbs=Decimal('0.0')
        )
        self.meal = Meal.objects.create(
            user=self.user,
            name='Lunch',
            date=timezone.now().date()
        )

    def test_meal_item_creation(self):
        item = MealItem.objects.create(
            meal=self.meal,
            food=self.food,
            weight_grams=Decimal('150.5')
        )
        self.assertEqual(item.weight_grams, Decimal('150.50'))
        self.assertAlmostEqual(float(item.total_protein), 46.655, places=2)

    def test_meal_totals_aggregate_items(self):
        MealItem.objects.create(meal=self.meal, food=self.food, weight_grams=Decimal('100'))
        MealItem.objects.create(meal=self.meal, food=self.food, weight_grams=Decimal('50'))
        self.assertAlmostEqual(float(self.meal.total_weight), 150, places=1)
        self.assertAlmostEqual(float(self.meal.total_calories), 247.5, places=1)

    def test_duplicate_meal(self):
        from django.urls import reverse
        MealItem.objects.create(meal=self.meal, food=self.food, weight_grams=Decimal('150.5'))
        self.client.force_login(self.user)
        response = self.client.get(reverse('tracker:meal_duplicate', args=[self.meal.pk]))
        self.assertEqual(response.status_code, 302)
        meals = Meal.objects.filter(user=self.user)
        self.assertEqual(meals.count(), 2)
        new_meal = meals.exclude(pk=self.meal.pk).first()
        self.assertEqual(new_meal.name, self.meal.name)
        self.assertEqual(new_meal.date, self.meal.date)
        self.assertEqual(new_meal.items.count(), 1)
