from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Food, MealLog
from .forms import MealLogForm

class MealLogDecimalWeightTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.food = Food.objects.create(
            name='Chicken Breast',
            calories=Decimal('165.0'),
            protein=Decimal('31.0'),
            fat=Decimal('3.6'),
            carbs=Decimal('0.0')
        )

    def test_decimal_weight_creation(self):
        meal = MealLog.objects.create(
            user=self.user,
            food=self.food,
            weight_grams=Decimal('150.5')
        )
        self.assertEqual(meal.weight_grams, Decimal('150.50'))
        self.assertEqual(meal.total_protein, Decimal('46.655'))

    def test_form_accepts_comma_decimal(self):
        form_data = {
            'food': self.food.id,
            'date': timezone.now().date().isoformat(),
            'weight_grams': '150,5'
        }
        form = MealLogForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['weight_grams'], Decimal('150.5'))

    def test_duplicate_meal(self):
        from django.urls import reverse
        meal = MealLog.objects.create(
            user=self.user,
            food=self.food,
            weight_grams=Decimal('150.5'),
            date=timezone.now().date()
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse('tracker:meallog_duplicate', args=[meal.pk]))
        self.assertEqual(response.status_code, 302)
        logs = MealLog.objects.filter(user=self.user)
        self.assertEqual(logs.count(), 2)
        new_meal = logs.exclude(pk=meal.pk).first()
        self.assertEqual(new_meal.food, meal.food)
        self.assertEqual(new_meal.weight_grams, meal.weight_grams)
        self.assertEqual(new_meal.date, meal.date)

