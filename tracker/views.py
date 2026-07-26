import calendar
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime, timedelta
import json
import urllib.request

from .models import Meal, MealItem, Food, UserProfile
from .forms import MealForm, MealItemForm, FoodForm, ProfileForm, UsernameChangeForm

from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('tracker:dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


def calculate_color(value, limit):
    """
    Calculates HSL color gradient from green to red based on percentage of limit.
    """
    if not limit or limit == 0:
        return "transparent"

    value = float(value)
    limit = float(limit)

    # Dynamic buffer: 5% of the limit
    buffer = limit * 0.05

    if value == 0:
        return "hsl(120, 50%, 95%)"

    if value <= limit + buffer:
        ratio = min(value / (limit + buffer), 1.0)
        lightness = 95 - (ratio * 35)
        return f"hsl(120, 60%, {lightness}%)"
    else:
        excess = value - (limit + buffer)
        max_excess = limit * 0.25
        if max_excess <= 0:
            max_excess = 1
        ratio = min(excess / max_excess, 1.0)
        hue = 120 - (ratio * 120)
        return f"hsl({hue}, 80%, 65%)"


# --- DASHBOARDS ---
@login_required
def daily_dashboard(request):
    today = timezone.now().date()
    date_str = request.GET.get('date')

    if date_str:
        try:
            current_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            if current_date > today:
                current_date = today
        except ValueError:
            current_date = today
    else:
        current_date = today

    prev_date = current_date - timedelta(days=1)
    next_date = current_date + timedelta(days=1) if current_date < today else None

    DEFAULT_MEALS = [
        'Breakfast', 'Morning Snack', 'Lunch', 
        'Afternoon Snack', 'Dinner', 'Second Dinner'
    ]

    existing_names = set(Meal.objects.filter(
        user=request.user, date=current_date
    ).values_list('name', flat=True))

    # Создаем недостающие приемы пищи
    for name in DEFAULT_MEALS:
        if name not in existing_names:
            Meal.objects.create(
                user=request.user, 
                date=current_date, 
                name=name
            )
    # -----------------------------------------------------

    # Fetch all Meals for the day with prefetched items and food data
    daily_meals_qs = Meal.objects.filter(
        user=request.user, date=current_date
    ).prefetch_related('items__food')

    daily_meals = list(daily_meals_qs)
    daily_meals.sort(key=lambda m: DEFAULT_MEALS.index(m.name) if m.name in DEFAULT_MEALS else 999)

    # Total КБЖУ = sum across all Meals, each Meal = sum of its MealItems
    consumed_calories = sum(meal.total_calories for meal in daily_meals)
    consumed_protein = sum(meal.total_protein for meal in daily_meals)
    consumed_fat = sum(meal.total_fat for meal in daily_meals)
    consumed_carbs = sum(meal.total_carbs for meal in daily_meals)

    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = None

    colors = {}
    if profile:
        colors['calories'] = calculate_color(consumed_calories, profile.daily_calories_limit)
        colors['protein'] = calculate_color(consumed_protein, profile.daily_protein_limit)
        colors['fat'] = calculate_color(consumed_fat, profile.daily_fat_limit)
        colors['carbs'] = calculate_color(consumed_carbs, profile.daily_carbs_limit)

    context = {
        'current_date': current_date,
        'prev_date': prev_date,
        'next_date': next_date,
        'meals': daily_meals,
        'consumed_calories': consumed_calories,
        'consumed_protein': consumed_protein,
        'consumed_fat': consumed_fat,
        'consumed_carbs': consumed_carbs,
        'profile': profile,
        'colors': colors,
    }

    return render(request, 'tracker/dashboard.html', context)


@login_required
def monthly_dashboard(request):
    today = timezone.now().date()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    origin_date = request.GET.get('date', '')

    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = None

    meals = Meal.objects.filter(
        user=request.user, date__year=year, date__month=month
    ).prefetch_related('items__food')

    daily_totals = {}
    for meal in meals:
        d = meal.date
        if d not in daily_totals:
            daily_totals[d] = {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0}
        daily_totals[d]['calories'] += meal.total_calories
        daily_totals[d]['protein'] += meal.total_protein
        daily_totals[d]['fat'] += meal.total_fat
        daily_totals[d]['carbs'] += meal.total_carbs

    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.monthdatescalendar(year, month)

    weeks_data = []
    for week in month_days:
        week_dict = {'days': [], 'totals': {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0}}
        has_days_in_month = False

        for day in week:
            if day.month == month:
                has_days_in_month = True
                totals = daily_totals.get(day, {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0})

                week_dict['totals']['calories'] += totals['calories']
                week_dict['totals']['protein'] += totals['protein']
                week_dict['totals']['fat'] += totals['fat']
                week_dict['totals']['carbs'] += totals['carbs']

                colors = {}
                if profile:
                    colors['calories'] = calculate_color(totals['calories'], profile.daily_calories_limit)
                    colors['protein'] = calculate_color(totals['protein'], profile.daily_protein_limit)
                    colors['fat'] = calculate_color(totals['fat'], profile.daily_fat_limit)
                    colors['carbs'] = calculate_color(totals['carbs'], profile.daily_carbs_limit)

                week_dict['days'].append({
                    'date': day,
                    'name': day.strftime('%A'),
                    'totals': totals,
                    'colors': colors
                })

        if has_days_in_month:
            weeks_data.append(week_dict)

    month_name = calendar.month_name[month]

    prev_month_date = (today.replace(year=year, month=month, day=1) - timedelta(days=1))
    next_month_date = (today.replace(year=year, month=month, day=28) + timedelta(days=4))

    context = {
        'weeks_data': weeks_data,
        'month_name': month_name,
        'year': year,
        'prev_year': prev_month_date.year,
        'prev_month': prev_month_date.month,
        'next_year': next_month_date.year,
        'next_month': next_month_date.month,
        'profile': profile,
        'origin_date': origin_date
    }
    return render(request, 'tracker/monthly.html', context)


# --- FOOD CRUD ---
class FoodListView(LoginRequiredMixin, ListView):
    model = Food
    template_name = 'tracker/food_list.html'
    context_object_name = 'foods'

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            qs = Food.objects.all()
        else:
            qs = Food.objects.filter(owner=user)
        sort = self.request.GET.get('sort', 'newest')

        if sort == 'name_asc':
            return qs.order_by('name')
        elif sort == 'name_desc':
            return qs.order_by('-name')
        elif sort == 'oldest':
            return qs.order_by('id')
        else:
            return qs.order_by('-id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['origin_date'] = self.request.GET.get('date', '')
        context['current_sort'] = self.request.GET.get('sort', 'newest')
        return context


class FoodCreateView(LoginRequiredMixin, CreateView):
    model = Food
    form_class = FoodForm
    template_name = 'tracker/food_form.html'

    def get_initial(self):
        initial = super().get_initial()
        scanned_food = self.request.session.pop('scanned_food', None)
        if scanned_food:
            initial.update(scanned_food)
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['origin_date'] = self.request.GET.get('date', '')
        return context

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        date_param = self.request.GET.get('date')
        base_url = reverse_lazy('tracker:food_list')
        return f"{base_url}?date={date_param}" if date_param else base_url


class FoodUpdateView(LoginRequiredMixin, UpdateView):
    model = Food
    form_class = FoodForm
    template_name = 'tracker/food_form.html'

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Food.objects.all()
        return Food.objects.filter(owner=user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['origin_date'] = self.request.GET.get('date', '')
        return context

    def get_success_url(self):
        date_param = self.request.GET.get('date')
        base_url = reverse_lazy('tracker:food_list')
        return f"{base_url}?date={date_param}" if date_param else base_url


class FoodDeleteView(LoginRequiredMixin, DeleteView):
    model = Food
    template_name = 'tracker/food_confirm_delete.html'

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Food.objects.all()
        return Food.objects.filter(owner=user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['origin_date'] = self.request.GET.get('date', '')
        return context

    def get_success_url(self):
        date_param = self.request.GET.get('date')
        base_url = reverse_lazy('tracker:food_list')
        return f"{base_url}?date={date_param}" if date_param else base_url


# --- MEAL CRUD ---
def _get_foods_json(user):
    """Return foods for the current user as JSON for JS autocomplete."""
    if user.is_superuser:
        qs = Food.objects.all()
    else:
        qs = Food.objects.filter(owner=user)
    return json.dumps(list(qs.values('id', 'name', 'barcode')))


@login_required
def meal_create(request):
    """Create a Meal container with one or more food items."""
    date_param = request.GET.get('date', '')
    foods_json = _get_foods_json(request.user)

    if request.method == 'POST':
        form = MealForm(request.POST)
        if form.is_valid():
            meal = form.save(commit=False)
            meal.user = request.user
            meal.save()

            # Parse submitted food items (food_id_N, weight_N)
            i = 0
            while True:
                food_id = request.POST.get(f'food_id_{i}')
                weight = request.POST.get(f'weight_{i}')
                if food_id is None and weight is None:
                    break
                if food_id and weight:
                    try:
                        food_obj = Food.objects.get(pk=food_id)
                        weight_val = str(weight).replace(',', '.')
                        MealItem.objects.create(
                            meal=meal,
                            food=food_obj,
                            weight_grams=weight_val
                        )
                    except (Food.DoesNotExist, ValueError):
                        pass
                i += 1

            date_iso = meal.date.isoformat()
            return redirect(f"{reverse('tracker:dashboard')}?date={date_iso}")
    else:
        form = MealForm(initial={'date': date_param} if date_param else {})

    return render(request, 'tracker/meal_form.html', {
        'form': form,
        'foods_json': foods_json,
        'is_edit': False,
    })


@login_required
def meal_edit(request, pk):
    """Edit a Meal container (name, date) and its food items."""
    meal = get_object_or_404(Meal, pk=pk, user=request.user)
    foods_json = _get_foods_json(request.user)

    if request.method == 'POST':
        form = MealForm(request.POST, instance=meal)
        if form.is_valid():
            form.save()

            # Replace all items with submitted ones
            meal.items.all().delete()
            i = 0
            while True:
                food_id = request.POST.get(f'food_id_{i}')
                weight = request.POST.get(f'weight_{i}')
                if food_id is None and weight is None:
                    break
                if food_id and weight:
                    try:
                        food_obj = Food.objects.get(pk=food_id)
                        weight_val = str(weight).replace(',', '.')
                        MealItem.objects.create(
                            meal=meal,
                            food=food_obj,
                            weight_grams=weight_val
                        )
                    except (Food.DoesNotExist, ValueError):
                        pass
                i += 1

            date_iso = meal.date.isoformat()
            return redirect(f"{reverse('tracker:dashboard')}?date={date_iso}")
    else:
        form = MealForm(instance=meal)

    # Serialize existing items for JS pre-population
    existing_items = list(meal.items.values('food_id', 'food__name', 'weight_grams'))

    return render(request, 'tracker/meal_form.html', {
        'form': form,
        'foods_json': foods_json,
        'is_edit': True,
        'meal': meal,
        'existing_items_json': json.dumps(existing_items, default=str),
    })


@login_required
def meal_delete(request, pk):
    meal = get_object_or_404(Meal, pk=pk, user=request.user)
    date_iso = meal.date.isoformat()
    if request.method == 'POST':
        meal.delete()
        return redirect(f"{reverse('tracker:dashboard')}?date={date_iso}")
    return render(request, 'tracker/meal_confirm_delete.html', {'meal': meal})


@login_required
def meal_duplicate(request, pk):
    """Duplicate a Meal container (same date) with all its items."""
    meal = get_object_or_404(Meal, pk=pk, user=request.user)
    items = list(meal.items.all())
    new_meal = Meal.objects.create(
        user=request.user,
        name=meal.name,
        date=meal.date,
    )
    for item in items:
        MealItem.objects.create(
            meal=new_meal,
            food=item.food,
            weight_grams=item.weight_grams,
        )
    date_iso = meal.date.isoformat()
    return redirect(f"{reverse('tracker:dashboard')}?date={date_iso}")


# --- MEAL ITEM CRUD ---
@login_required
def meal_item_add(request, meal_pk=None):
    """Add a food item to a Meal container (with or without pre-selected meal)."""
    meal = None
    meals = []
    
    if meal_pk:
        meal = get_object_or_404(Meal, pk=meal_pk, user=request.user)
        current_date = meal.date
    else:
        date_str = request.GET.get('date')
        if date_str:
            try:
                current_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                current_date = timezone.now().date()
        else:
            current_date = timezone.now().date()
        
    meals_qs = Meal.objects.filter(user=request.user, date=current_date)
    DEFAULT_MEALS = [
        'Breakfast', 'Morning Snack', 'Lunch', 
        'Afternoon Snack', 'Dinner', 'Second Dinner'
    ]
    meals = list(meals_qs)
    meals.sort(key=lambda m: DEFAULT_MEALS.index(m.name) if m.name in DEFAULT_MEALS else 999)
    
    selected_meal_id = meal.pk if meal else None

    foods_json = _get_foods_json(request.user)

    if request.method == 'POST':
        form_meal_id = request.POST.get('meal_id')
        target_meal = get_object_or_404(Meal, pk=form_meal_id, user=request.user)

        food_id = request.POST.get('food_id')
        weight = request.POST.get('weight_grams')
        
        if food_id and weight:
            try:
                food_obj = Food.objects.get(pk=food_id)
                weight_val = str(weight).replace(',', '.')
                MealItem.objects.create(meal=target_meal, food=food_obj, weight_grams=weight_val)
            except (Food.DoesNotExist, ValueError):
                pass
                
        date_iso = target_meal.date.isoformat()
        return redirect(f"{reverse('tracker:dashboard')}?date={date_iso}")

    return render(request, 'tracker/meal_item_form.html', {
        'meal': meal,
        'meals': meals,
        'selected_meal_id': selected_meal_id,
        'foods_json': foods_json,
        'is_edit': False,
        'current_date': current_date,
    })


@login_required
def meal_item_edit(request, pk):
    """Edit a food item inside a Meal container (with meal selection)."""
    item = get_object_or_404(MealItem, pk=pk, meal__user=request.user)
    current_meal = item.meal
    current_date = current_meal.date

    meals_qs = Meal.objects.filter(user=request.user, date=current_date)
    DEFAULT_MEALS = [
        'Breakfast', 'Morning Snack', 'Lunch', 
        'Afternoon Snack', 'Dinner', 'Second Dinner'
    ]
    meals = list(meals_qs)
    meals.sort(key=lambda m: DEFAULT_MEALS.index(m.name) if m.name in DEFAULT_MEALS else 999)

    foods_json = _get_foods_json(request.user)

    if request.method == 'POST':
        form_meal_id = request.POST.get('meal_id')
        target_meal = get_object_or_404(Meal, pk=form_meal_id, user=request.user)

        food_id = request.POST.get('food_id')
        weight = request.POST.get('weight_grams')
        
        if food_id and weight:
            try:
                food_obj = Food.objects.get(pk=food_id)
                weight_val = str(weight).replace(',', '.')
                
                item.meal = target_meal
                item.food = food_obj
                item.weight_grams = weight_val
                item.save()
            except (Food.DoesNotExist, ValueError):
                pass
                
        date_iso = target_meal.date.isoformat()
        return redirect(f"{reverse('tracker:dashboard')}?date={date_iso}")

    return render(request, 'tracker/meal_item_form.html', {
        'meal': current_meal,
        'meals': meals,
        'selected_meal_id': current_meal.pk,
        'item': item,
        'foods_json': foods_json,
        'is_edit': True,
        'current_date': current_date,
    })


@login_required
def meal_item_delete(request, pk):
    item = get_object_or_404(MealItem, pk=pk, meal__user=request.user)
    date_iso = item.meal.date.isoformat()
    if request.method == 'POST':
        item.delete()
    return redirect(f"{reverse('tracker:dashboard')}?date={date_iso}")


@login_required
def meal_item_duplicate(request, pk):
    """Duplicate a food item inside the same Meal container."""
    item = get_object_or_404(MealItem, pk=pk, meal__user=request.user)
    MealItem.objects.create(
        meal=item.meal,
        food=item.food,
        weight_grams=item.weight_grams,
    )
    date_iso = item.meal.date.isoformat()
    return redirect(f"{reverse('tracker:dashboard')}?date={date_iso}")


# --- PROFILE & SETTINGS ---
class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = UserProfile
    form_class = ProfileForm
    template_name = 'tracker/profile_form.html'
    success_url = reverse_lazy('tracker:dashboard')

    def get_object(self, queryset=None):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile


@login_required
def settings_view(request):
    return render(request, 'tracker/settings.html')


@login_required
def edit_username(request):
    if request.method == 'POST':
        form = UsernameChangeForm(request.user, request.POST)
        if form.is_valid():
            request.user.username = form.cleaned_data['new_username']
            request.user.save()
            return redirect('tracker:dashboard')
    else:
        form = UsernameChangeForm(request.user)
    return render(request, 'tracker/username_form.html', {'form': form})


@login_required
def add_by_barcode(request):
    origin_date = request.GET.get('date', '')

    base_url = reverse('tracker:food_create')
    redirect_url = f"{base_url}?date={origin_date}" if origin_date else base_url

    if request.method == 'POST':
        barcode = request.POST.get('barcode').strip()

        # Check barcode only within the current user's foods
        if request.user.is_superuser:
            existing_food = Food.objects.filter(barcode=barcode).first()
        else:
            existing_food = Food.objects.filter(barcode=barcode, owner=request.user).first()
        if existing_food:
            messages.error(request, f"Product '{existing_food.name}' is already in your database.")
            return redirect(redirect_url)

        api_url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"

        try:
            req = urllib.request.Request(api_url, headers={'User-Agent': 'MacroTracker/1.0'})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode('utf-8'))

            if data.get('status') == 1:
                product = data.get('product', {})
                name = product.get('product_name', 'Unknown Product')
                nutriments = product.get('nutriments', {})

                def safe_float(val):
                    try:
                        return float(val) if val else 0.0
                    except ValueError:
                        return 0.0

                request.session['scanned_food'] = {
                    'name': name,
                    'barcode': barcode,
                    'calories': safe_float(nutriments.get('energy-kcal_100g', 0)),
                    'protein': safe_float(nutriments.get('proteins_100g', 0)),
                    'fat': safe_float(nutriments.get('fat_100g', 0)),
                    'carbs': safe_float(nutriments.get('carbohydrates_100g', 0)),
                }
                return redirect(redirect_url)
            else:
                messages.error(request, f"Product with barcode '{barcode}' not found on OpenFoodFacts.")
                return redirect(redirect_url)

        except Exception as e:
            messages.error(request, f"Error connecting to OpenFoodFacts: {str(e)}")
            return redirect(redirect_url)

    return render(request, 'tracker/barcode_form.html', {'origin_date': origin_date})


@login_required
@require_POST
def save_off_food(request):
    try:
        data = json.loads(request.body)
        barcode = data.get('barcode')
        
        if not barcode:
            return JsonResponse({'error': 'No barcode provided'}, status=400)

        def safe_float(val):
            try:
                return float(val) if val else 0.0
            except (ValueError, TypeError):
                return 0.0

        if request.user.is_superuser:
            existing_food = Food.objects.filter(barcode=barcode).first()
        else:
            existing_food = Food.objects.filter(barcode=barcode, owner=request.user).first()

        if existing_food:
            return JsonResponse({'id': existing_food.id, 'name': existing_food.name})

        new_food = Food.objects.create(
            owner=request.user,
            barcode=barcode,
            name=data.get('name', 'Unknown API Food'),
            calories=safe_float(data.get('kcal')),
            protein=safe_float(data.get('protein')),
            fat=safe_float(data.get('fat')),
            carbs=safe_float(data.get('carbs'))
        )
        
        return JsonResponse({'id': new_food.id, 'name': new_food.name})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)