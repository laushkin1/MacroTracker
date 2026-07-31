"""
Unit tests for the MacroTracker application.

Tests cover models, forms, helper functions, and all views.
Each test class focuses on one module or feature area.
"""

import json
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import FoodForm, ProfileForm, UsernameChangeForm
from .models import Food, MealItem, UserProfile
from .views import _parse_float_value, calculate_color


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class ParseFloatHelperTest(TestCase):
    """Tests for the _parse_float_value() helper."""

    def test_integer_string_returns_float(self):
        self.assertEqual(_parse_float_value('42'), 42.0)

    def test_dot_decimal_string(self):
        self.assertAlmostEqual(_parse_float_value('3.14'), 3.14)

    def test_comma_decimal_string(self):
        """Comma must be accepted as a decimal separator."""
        self.assertAlmostEqual(_parse_float_value('3,14'), 3.14)

    def test_empty_string_returns_zero(self):
        self.assertEqual(_parse_float_value(''), 0.0)

    def test_none_returns_zero(self):
        self.assertEqual(_parse_float_value(None), 0.0)

    def test_integer_input(self):
        self.assertEqual(_parse_float_value(10), 10.0)


class CalculateColorTest(TestCase):
    """Tests for the calculate_color() helper."""

    def test_zero_limit_returns_transparent(self):
        self.assertEqual(calculate_color(100, 0), 'transparent')

    def test_none_limit_returns_transparent(self):
        self.assertEqual(calculate_color(100, None), 'transparent')

    def test_zero_value_returns_light_green(self):
        result = calculate_color(0, 2000)
        self.assertEqual(result, 'hsl(120, 50%, 95%)')

    def test_value_within_limit_returns_green_hsl(self):
        result = calculate_color(1000, 2000)
        self.assertTrue(result.startswith('hsl(120,'))

    def test_value_at_limit_returns_green_hsl(self):
        result = calculate_color(2000, 2000)
        self.assertTrue(result.startswith('hsl(120,'))

    def test_value_over_limit_returns_non_green_hsl(self):
        """A value 30 % above the limit must shift the hue toward red."""
        result = calculate_color(2600, 2000)
        self.assertTrue(result.startswith('hsl('))
        # Extract hue value and check it is less than 120 (shifted toward red).
        hue = float(result.split('(')[1].split(',')[0])
        self.assertLess(hue, 120)

    def test_far_over_limit_approaches_red(self):
        """A value far above the limit must produce a hue close to 0 (red)."""
        result = calculate_color(10000, 2000)
        hue = float(result.split('(')[1].split(',')[0])
        self.assertAlmostEqual(hue, 0, delta=1)


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class UserProfileModelTest(TestCase):
    """Tests for the UserProfile model."""

    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pass')

    def test_str_contains_username(self):
        profile = UserProfile.objects.create(user=self.user)
        self.assertIn('alice', str(profile))

    def test_default_limits_are_zero(self):
        profile = UserProfile.objects.create(user=self.user)
        self.assertEqual(profile.daily_calories_limit, 0)
        self.assertEqual(profile.daily_protein_limit, 0)
        self.assertEqual(profile.daily_fat_limit, 0)
        self.assertEqual(profile.daily_carbs_limit, 0)


class FoodModelTest(TestCase):
    """Tests for the Food model."""

    def setUp(self):
        self.user = User.objects.create_user(username='bob', password='pass')
        self.food = Food.objects.create(
            name='Oats',
            calories=Decimal('389.0'),
            protein=Decimal('17.0'),
            fat=Decimal('7.0'),
            carbs=Decimal('66.0'),
            owner=self.user,
        )

    def test_str_returns_food_name(self):
        self.assertEqual(str(self.food), 'Oats')

    def test_unique_together_owner_name(self):
        """Creating a second food with the same owner and name must fail."""
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Food.objects.create(name='Oats', owner=self.user)


class MealItemModelTest(TestCase):
    """Tests for MealItem model properties."""

    def setUp(self):
        self.user = User.objects.create_user(username='carol', password='pass')
        self.food = Food.objects.create(
            name='Chicken Breast',
            calories=Decimal('165.0'),
            protein=Decimal('31.0'),
            fat=Decimal('3.6'),
            carbs=Decimal('0.0'),
            owner=self.user,
        )
        self.item = MealItem.objects.create(
            user=self.user,
            date=timezone.now().date(),
            meal_type='Lunch',
            food=self.food,
            weight_grams=Decimal('200.0'),
        )

    def test_total_calories(self):
        """165 kcal/100 g × 200 g = 330 kcal."""
        self.assertAlmostEqual(float(self.item.total_calories), 330.0, places=1)

    def test_total_protein(self):
        """31 g/100 g × 200 g = 62 g."""
        self.assertAlmostEqual(float(self.item.total_protein), 62.0, places=1)

    def test_total_fat(self):
        """3.6 g/100 g × 200 g = 7.2 g."""
        self.assertAlmostEqual(float(self.item.total_fat), 7.2, places=1)

    def test_total_carbs(self):
        """0 g/100 g × 200 g = 0 g."""
        self.assertAlmostEqual(float(self.item.total_carbs), 0.0, places=1)

    def test_str_contains_food_name_and_meal(self):
        self.assertIn('Chicken Breast', str(self.item))
        self.assertIn('Lunch', str(self.item))

    def test_weight_stored_correctly(self):
        self.assertEqual(self.item.weight_grams, Decimal('200.00'))


# ---------------------------------------------------------------------------
# Form tests
# ---------------------------------------------------------------------------

class FoodFormTest(TestCase):
    """Tests for FoodForm."""

    def _valid_data(self, **overrides):
        data = {
            'name': 'Test Food',
            'calories': '100',
            'protein': '10',
            'fat': '5',
            'carbs': '20',
            'portions': '{}',
        }
        data.update(overrides)
        return data

    def test_valid_form(self):
        form = FoodForm(data=self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_comma_decimal_accepted_for_calories(self):
        form = FoodForm(data=self._valid_data(calories='99,5'))
        self.assertTrue(form.is_valid())
        self.assertAlmostEqual(form.cleaned_data['calories'], 99.5)

    def test_empty_macro_defaults_to_zero(self):
        form = FoodForm(data=self._valid_data(protein=''))
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['protein'], 0.0)

    def test_name_is_required(self):
        form = FoodForm(data=self._valid_data(name=''))
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)


class ProfileFormTest(TestCase):
    """Tests for ProfileForm."""

    def test_valid_form_saves_limits(self):
        data = {
            'daily_calories_limit': 2000,
            'daily_protein_limit': 150,
            'daily_fat_limit': 70,
            'daily_carbs_limit': 250,
        }
        form = ProfileForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_negative_limit_is_invalid(self):
        data = {
            'daily_calories_limit': -100,
            'daily_protein_limit': 150,
            'daily_fat_limit': 70,
            'daily_carbs_limit': 250,
        }
        form = ProfileForm(data=data)
        self.assertFalse(form.is_valid())


class UsernameChangeFormTest(TestCase):
    """Tests for UsernameChangeForm."""

    def setUp(self):
        self.user = User.objects.create_user(username='dave', password='correct_pass')

    def test_valid_form_with_correct_password(self):
        form = UsernameChangeForm(
            self.user,
            data={'new_username': 'dave_new', 'password': 'correct_pass'},
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_wrong_password_raises_validation_error(self):
        form = UsernameChangeForm(
            self.user,
            data={'new_username': 'dave_new', 'password': 'wrong_pass'},
        )
        self.assertFalse(form.is_valid())
        self.assertIn('password', form.errors)

    def test_empty_username_is_invalid(self):
        form = UsernameChangeForm(
            self.user,
            data={'new_username': '', 'password': 'correct_pass'},
        )
        self.assertFalse(form.is_valid())


# ---------------------------------------------------------------------------
# View tests — authentication
# ---------------------------------------------------------------------------

class RegisterViewTest(TestCase):
    """Tests for the register view."""

    def test_get_renders_form(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/register.html')

    def test_post_valid_data_creates_user_and_redirects(self):
        data = {
            'username': 'newuser',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        }
        response = self.client.post(reverse('register'), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_post_invalid_data_re_renders_form(self):
        data = {'username': 'u', 'password1': 'abc', 'password2': 'xyz'}
        response = self.client.post(reverse('register'), data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/register.html')


# ---------------------------------------------------------------------------
# View tests — dashboards
# ---------------------------------------------------------------------------

class DailyDashboardViewTest(TestCase):
    """Tests for the daily_dashboard view."""

    def setUp(self):
        self.user = User.objects.create_user(username='eve', password='pass')
        self.client.login(username='eve', password='pass')

    def test_login_required_redirects_anonymous(self):
        self.client.logout()
        response = self.client.get(reverse('tracker:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_get_returns_200(self):
        response = self.client.get(reverse('tracker:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/dashboard.html')

    def test_context_contains_meals(self):
        response = self.client.get(reverse('tracker:dashboard'))
        self.assertIn('meals', response.context)

    def test_future_date_param_is_clamped_to_today(self):
        future_date = '2099-01-01'
        response = self.client.get(
            reverse('tracker:dashboard'), {'date': future_date}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_date'], timezone.now().date())

    def test_invalid_date_param_uses_today(self):
        response = self.client.get(
            reverse('tracker:dashboard'), {'date': 'not-a-date'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_date'], timezone.now().date())

    def test_context_shows_consumed_totals(self):
        food = Food.objects.create(
            name='Apple',
            calories=Decimal('52.0'),
            protein=Decimal('0.3'),
            fat=Decimal('0.2'),
            carbs=Decimal('14.0'),
            owner=self.user,
        )
        MealItem.objects.create(
            user=self.user,
            date=timezone.now().date(),
            meal_type='Breakfast',
            food=food,
            weight_grams=Decimal('100'),
        )
        response = self.client.get(reverse('tracker:dashboard'))
        self.assertAlmostEqual(
            float(response.context['consumed_calories']), 52.0, places=1
        )


class MonthlyDashboardViewTest(TestCase):
    """Tests for the monthly_dashboard view."""

    def setUp(self):
        self.user = User.objects.create_user(username='frank', password='pass')
        self.client.login(username='frank', password='pass')

    def test_login_required_redirects_anonymous(self):
        self.client.logout()
        response = self.client.get(reverse('tracker:monthly_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_get_returns_200_with_calendar_template(self):
        response = self.client.get(reverse('tracker:monthly_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/calendar.html')

    def test_context_contains_weeks_data(self):
        response = self.client.get(reverse('tracker:monthly_dashboard'))
        self.assertIn('weeks_data', response.context)

    def test_custom_year_month_params(self):
        response = self.client.get(
            reverse('tracker:monthly_dashboard'), {'year': 2024, 'month': 3}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['month_name'], 'March')


# ---------------------------------------------------------------------------
# View tests — Food CRUD
# ---------------------------------------------------------------------------

class FoodListViewTest(TestCase):
    """Tests for FoodListView."""

    def setUp(self):
        self.user = User.objects.create_user(username='grace', password='pass')
        self.other_user = User.objects.create_user(username='harry', password='pass')
        self.client.login(username='grace', password='pass')
        Food.objects.create(
            name='Banana', calories=89, protein=1, fat=0, carbs=23, owner=self.user
        )
        Food.objects.create(
            name='Orange', calories=47, protein=1, fat=0, carbs=12, owner=self.other_user
        )

    def test_login_required(self):
        self.client.logout()
        response = self.client.get(reverse('tracker:food_list'))
        self.assertEqual(response.status_code, 302)

    def test_user_sees_only_own_foods(self):
        response = self.client.get(reverse('tracker:food_list'))
        foods = list(response.context['foods'])
        names = [f.name for f in foods]
        self.assertIn('Banana', names)
        self.assertNotIn('Orange', names)

    def test_sort_by_name_asc(self):
        Food.objects.create(
            name='Apple', calories=52, protein=0, fat=0, carbs=14, owner=self.user
        )
        response = self.client.get(
            reverse('tracker:food_list'), {'sort': 'name_asc'}
        )
        foods = list(response.context['foods'])
        names = [f.name for f in foods]
        self.assertEqual(names, sorted(names))


class FoodCreateViewTest(TestCase):
    """Tests for FoodCreateView."""

    def setUp(self):
        self.user = User.objects.create_user(username='ivy', password='pass')
        self.client.login(username='ivy', password='pass')

    def test_get_renders_form(self):
        response = self.client.get(reverse('tracker:food_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/food_form.html')

    def test_post_creates_food_and_redirects(self):
        data = {
            'name': 'Broccoli',
            'calories': '34',
            'protein': '3',
            'fat': '1',
            'carbs': '7',
            'portions': '{}',
        }
        response = self.client.post(reverse('tracker:food_create'), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Food.objects.filter(name='Broccoli', owner=self.user).exists())

    def test_post_invalid_data_re_renders_form(self):
        response = self.client.post(reverse('tracker:food_create'), {'name': ''})
        self.assertEqual(response.status_code, 200)


class FoodUpdateViewTest(TestCase):
    """Tests for FoodUpdateView."""

    def setUp(self):
        self.user = User.objects.create_user(username='jack', password='pass')
        self.client.login(username='jack', password='pass')
        self.food = Food.objects.create(
            name='Rice', calories=130, protein=2, fat=0, carbs=28, owner=self.user
        )

    def test_get_renders_form(self):
        response = self.client.get(
            reverse('tracker:food_update', args=[self.food.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_post_updates_food(self):
        data = {
            'name': 'Brown Rice',
            'calories': '111',
            'protein': '3',
            'fat': '1',
            'carbs': '23',
            'portions': '{}',
        }
        self.client.post(reverse('tracker:food_update', args=[self.food.pk]), data)
        self.food.refresh_from_db()
        self.assertEqual(self.food.name, 'Brown Rice')

    def test_other_user_cannot_edit_food(self):
        other = User.objects.create_user(username='kate', password='pass')
        self.client.login(username='kate', password='pass')
        response = self.client.get(
            reverse('tracker:food_update', args=[self.food.pk])
        )
        self.assertEqual(response.status_code, 404)


class FoodDeleteViewTest(TestCase):
    """Tests for FoodDeleteView."""

    def setUp(self):
        self.user = User.objects.create_user(username='leo', password='pass')
        self.client.login(username='leo', password='pass')
        self.food = Food.objects.create(
            name='Butter', calories=717, protein=1, fat=81, carbs=0, owner=self.user
        )

    def test_post_deletes_food(self):
        self.client.post(reverse('tracker:food_delete', args=[self.food.pk]))
        self.assertFalse(Food.objects.filter(pk=self.food.pk).exists())

    def test_other_user_cannot_delete_food(self):
        other = User.objects.create_user(username='mia', password='pass')
        self.client.login(username='mia', password='pass')
        response = self.client.post(
            reverse('tracker:food_delete', args=[self.food.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Food.objects.filter(pk=self.food.pk).exists())


# ---------------------------------------------------------------------------
# View tests — Meal item CRUD
# ---------------------------------------------------------------------------

class MealItemAddViewTest(TestCase):
    """Tests for the meal_item_add view."""

    def setUp(self):
        self.user = User.objects.create_user(username='noah', password='pass')
        self.client.login(username='noah', password='pass')
        self.food = Food.objects.create(
            name='Egg', calories=155, protein=13, fat=11, carbs=1, owner=self.user
        )

    def test_get_renders_form(self):
        response = self.client.get(reverse('tracker:meal_item_add'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/meal_item_form.html')

    def test_post_creates_meal_item(self):
        today = timezone.now().date().isoformat()
        data = {
            'meal_type': 'Breakfast',
            'food_id': self.food.pk,
            'quantity': '2',
            'portion_multiplier': '50',
        }
        response = self.client.post(
            f"{reverse('tracker:meal_item_add')}?date={today}", data
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(MealItem.objects.filter(user=self.user).count(), 1)
        item = MealItem.objects.get(user=self.user)
        self.assertAlmostEqual(float(item.weight_grams), 100.0)

    def test_login_required(self):
        self.client.logout()
        response = self.client.get(reverse('tracker:meal_item_add'))
        self.assertEqual(response.status_code, 302)


class MealItemEditViewTest(TestCase):
    """Tests for the meal_item_edit view."""

    def setUp(self):
        self.user = User.objects.create_user(username='olivia', password='pass')
        self.client.login(username='olivia', password='pass')
        self.food = Food.objects.create(
            name='Tuna', calories=144, protein=30, fat=1, carbs=0, owner=self.user
        )
        self.item = MealItem.objects.create(
            user=self.user,
            date=timezone.now().date(),
            meal_type='Lunch',
            food=self.food,
            weight_grams=Decimal('100'),
        )

    def test_get_renders_form(self):
        response = self.client.get(
            reverse('tracker:meal_item_edit', args=[self.item.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_post_updates_weight(self):
        data = {
            'meal_type': 'Dinner',
            'food_id': self.food.pk,
            'quantity': '3',
            'portion_multiplier': '50',
        }
        self.client.post(
            reverse('tracker:meal_item_edit', args=[self.item.pk]), data
        )
        self.item.refresh_from_db()
        self.assertAlmostEqual(float(self.item.weight_grams), 150.0)
        self.assertEqual(self.item.meal_type, 'Dinner')

    def test_other_user_gets_404(self):
        other = User.objects.create_user(username='peter', password='pass')
        self.client.login(username='peter', password='pass')
        response = self.client.get(
            reverse('tracker:meal_item_edit', args=[self.item.pk])
        )
        self.assertEqual(response.status_code, 404)


class MealItemDeleteViewTest(TestCase):
    """Tests for the meal_item_delete view."""

    def setUp(self):
        self.user = User.objects.create_user(username='quinn', password='pass')
        self.client.login(username='quinn', password='pass')
        food = Food.objects.create(
            name='Milk', calories=42, protein=3, fat=1, carbs=5, owner=self.user
        )
        self.item = MealItem.objects.create(
            user=self.user,
            date=timezone.now().date(),
            meal_type='Breakfast',
            food=food,
            weight_grams=Decimal('200'),
        )

    def test_post_deletes_item(self):
        self.client.post(reverse('tracker:meal_item_delete', args=[self.item.pk]))
        self.assertFalse(MealItem.objects.filter(pk=self.item.pk).exists())

    def test_get_does_not_delete_item(self):
        """A GET request must not delete the item."""
        self.client.get(reverse('tracker:meal_item_delete', args=[self.item.pk]))
        self.assertTrue(MealItem.objects.filter(pk=self.item.pk).exists())


class MealItemDuplicateViewTest(TestCase):
    """Tests for the meal_item_duplicate view."""

    def setUp(self):
        self.user = User.objects.create_user(username='rose', password='pass')
        self.client.login(username='rose', password='pass')
        food = Food.objects.create(
            name='Yogurt', calories=61, protein=5, fat=3, carbs=5, owner=self.user
        )
        self.item = MealItem.objects.create(
            user=self.user,
            date=timezone.now().date(),
            meal_type='Breakfast',
            food=food,
            weight_grams=Decimal('150'),
        )

    def test_duplicates_meal_item(self):
        self.client.get(
            reverse('tracker:meal_item_duplicate', args=[self.item.pk])
        )
        self.assertEqual(MealItem.objects.filter(user=self.user).count(), 2)

    def test_duplicate_has_same_attributes(self):
        self.client.get(
            reverse('tracker:meal_item_duplicate', args=[self.item.pk])
        )
        items = MealItem.objects.filter(user=self.user).order_by('created_at')
        original, copy = items[0], items[1]
        self.assertEqual(original.food, copy.food)
        self.assertEqual(original.weight_grams, copy.weight_grams)
        self.assertEqual(original.meal_type, copy.meal_type)


# ---------------------------------------------------------------------------
# View tests — Profile and settings
# ---------------------------------------------------------------------------

class ProfileUpdateViewTest(TestCase):
    """Tests for ProfileUpdateView."""

    def setUp(self):
        self.user = User.objects.create_user(username='sam', password='pass')
        self.client.login(username='sam', password='pass')

    def test_get_renders_form(self):
        response = self.client.get(reverse('tracker:profile_edit'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/edit_daily_limits_form.html')

    def test_post_creates_profile_when_none_exists(self):
        data = {
            'daily_calories_limit': 2500,
            'daily_protein_limit': 180,
            'daily_fat_limit': 80,
            'daily_carbs_limit': 300,
        }
        self.client.post(reverse('tracker:profile_edit'), data)
        self.assertTrue(UserProfile.objects.filter(user=self.user).exists())

    def test_post_updates_existing_profile(self):
        UserProfile.objects.create(
            user=self.user,
            daily_calories_limit=2000,
            daily_protein_limit=150,
            daily_fat_limit=70,
            daily_carbs_limit=250,
        )
        data = {
            'daily_calories_limit': 2200,
            'daily_protein_limit': 160,
            'daily_fat_limit': 75,
            'daily_carbs_limit': 270,
        }
        self.client.post(reverse('tracker:profile_edit'), data)
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.daily_calories_limit, 2200)


class SettingsViewTest(TestCase):
    """Tests for the settings_view."""

    def setUp(self):
        self.user = User.objects.create_user(username='tina', password='pass')
        self.client.login(username='tina', password='pass')

    def test_get_returns_200(self):
        response = self.client.get(reverse('tracker:settings'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tracker/settings.html')

    def test_login_required(self):
        self.client.logout()
        response = self.client.get(reverse('tracker:settings'))
        self.assertEqual(response.status_code, 302)


class EditUsernameViewTest(TestCase):
    """Tests for the edit_username view."""

    def setUp(self):
        self.user = User.objects.create_user(username='uma', password='mypass')
        self.client.login(username='uma', password='mypass')

    def test_get_renders_form(self):
        response = self.client.get(reverse('tracker:username_edit'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/change_username.html')

    def test_post_valid_data_changes_username(self):
        data = {'new_username': 'uma_renamed', 'password': 'mypass'}
        response = self.client.post(reverse('tracker:username_edit'), data)
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'uma_renamed')

    def test_post_wrong_password_does_not_change_username(self):
        data = {'new_username': 'uma_renamed', 'password': 'wrongpass'}
        self.client.post(reverse('tracker:username_edit'), data)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'uma')


# ---------------------------------------------------------------------------
# View tests — OpenFoodFacts integration
# ---------------------------------------------------------------------------

class SaveOFFFoodViewTest(TestCase):
    """Tests for the save_off_food view."""

    def setUp(self):
        self.user = User.objects.create_user(username='vera', password='pass')
        self.client.login(username='vera', password='pass')

    def _post_json(self, payload):
        return self.client.post(
            reverse('tracker:save_off_food'),
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_missing_barcode_returns_400(self):
        response = self._post_json({'name': 'No Barcode Food'})
        self.assertEqual(response.status_code, 400)

    def test_valid_payload_creates_food(self):
        payload = {
            'barcode': '1234567890',
            'name': 'Test Bar',
            'kcal': 450,
            'protein': 10,
            'fat': 20,
            'carbs': 55,
        }
        response = self._post_json(payload)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('id', data)
        self.assertTrue(Food.objects.filter(barcode='1234567890', owner=self.user).exists())

    def test_existing_barcode_returns_existing_food(self):
        food = Food.objects.create(
            name='Existing Bar',
            barcode='9999999999',
            calories=300,
            protein=5,
            fat=10,
            carbs=40,
            owner=self.user,
        )
        payload = {
            'barcode': '9999999999',
            'name': 'Duplicate',
            'kcal': 300,
            'protein': 5,
            'fat': 10,
            'carbs': 40,
        }
        response = self._post_json(payload)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['id'], food.id)
        # No duplicate record must be created.
        self.assertEqual(
            Food.objects.filter(barcode='9999999999', owner=self.user).count(), 1
        )

    def test_login_required(self):
        self.client.logout()
        response = self._post_json({'barcode': '123'})
        self.assertEqual(response.status_code, 302)
