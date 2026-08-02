import calendar
import json
import logging
import urllib.request
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import FoodForm, ProfileForm, UsernameChangeForm
from .models import MEAL_CHOICES, Food, MealItem, UserProfile

logger = logging.getLogger(__name__)

# List of default meal names derived from MEAL_CHOICES.
DEFAULT_MEAL_NAMES = [m[0] for m in MEAL_CHOICES]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _parse_float_value(val):
    """Convert a string value to float. Accept comma as decimal separator.

    Return 0.0 when the value is empty or cannot be converted.
    """
    if not val:
        return 0.0
    return float(str(val).replace(',', '.'))


def calculate_color(value, limit):
    """Return an HSL color string based on the ratio of value to limit.

    Color transitions from light green (0 % of limit) through darker green
    (at limit) and then to red (25 % above limit).
    Return 'transparent' when the limit is zero or not set.
    """
    if not limit or limit == 0:
        return 'transparent'

    value = float(value)
    limit = float(limit)

    # Allow a 5 % buffer above the limit before the color starts shifting red.
    buffer = limit * 0.05

    if value == 0:
        return 'hsl(120, 50%, 95%)'

    if value <= limit + buffer:
        ratio = min(value / (limit + buffer), 1.0)
        lightness = 95 - (ratio * 35)
        return f'hsl(120, 60%, {lightness}%)'

    # Value is above the buffer. Shift hue from green to red.
    excess = value - (limit + buffer)
    max_excess = limit * 0.25 or 1
    ratio = min(excess / max_excess, 1.0)
    hue = 120 - (ratio * 120)
    return f'hsl({hue}, 80%, 65%)'


def _get_foods_json(user):
    """Return all foods visible to the user as a JSON string.

    Superusers see all foods. Regular users see only their own foods.
    The result is used by the JavaScript autocomplete on the meal item form.
    """
    if user.is_superuser:
        qs = Food.objects.all()
    else:
        qs = Food.objects.filter(owner=user)

    food_list = [
        {
            'id': f.id,
            'name': f.name,
            'barcode': f.barcode,
            'kcal': float(f.calories),
            'protein': float(f.protein),
            'fat': float(f.fat),
            'carbs': float(f.carbs),
            'portions': f.portions,
        }
        for f in qs
    ]
    return json.dumps(food_list)


def _resolve_food_from_post(request, post_data):
    """Return a Food object from POST data.

    If food_id is present, fetch the existing record.
    If off_name is present, create a new food from the OpenFoodFacts data.
    Return None when neither identifier is supplied.
    """
    food_id = post_data.get('food_id')
    off_name = post_data.get('off_name')

    if food_id:
        return Food.objects.get(pk=food_id)

    if off_name:
        off_portions_raw = post_data.get('off_portions', '{}')
        try:
            portions_dict = json.loads(off_portions_raw)
        except (ValueError, json.JSONDecodeError):
            portions_dict = {}

        return Food.objects.create(
            name=off_name,
            barcode=post_data.get('off_barcode', ''),
            calories=_parse_float_value(post_data.get('off_kcal')),
            protein=_parse_float_value(post_data.get('off_protein')),
            fat=_parse_float_value(post_data.get('off_fat')),
            carbs=_parse_float_value(post_data.get('off_carbs')),
            portions=portions_dict,
            owner=request.user,
        )

    return None


# ---------------------------------------------------------------------------
# Authentication views
# ---------------------------------------------------------------------------

def register(request):
    """Register a new user account and log them in immediately."""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('tracker:dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


# ---------------------------------------------------------------------------
# Dashboard views
# ---------------------------------------------------------------------------

@login_required
def daily_dashboard(request):
    """Render the daily nutrition dashboard for the requested date.

    Use today's date when no date parameter is provided or the supplied
    date is in the future.
    """
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

    daily_items = (
        MealItem.objects
        .filter(user=request.user, date=current_date)
        .select_related('food')
    )

    daily_meals = []
    consumed_calories = consumed_protein = consumed_fat = consumed_carbs = 0

    for name in DEFAULT_MEAL_NAMES:
        items = [item for item in daily_items if item.meal_type == name]

        m_cal = sum(item.total_calories for item in items)
        m_pro = sum(item.total_protein for item in items)
        m_fat = sum(item.total_fat for item in items)
        m_car = sum(item.total_carbs for item in items)
        m_weight = sum(item.weight_grams for item in items)

        consumed_calories += m_cal
        consumed_protein += m_pro
        consumed_fat += m_fat
        consumed_carbs += m_car

        daily_meals.append({
            'name': name,
            'slug': name.replace(' ', '-').lower(),
            'items': items,
            'total_weight': m_weight,
            'total_calories': m_cal,
            'total_protein': m_pro,
            'total_fat': m_fat,
            'total_carbs': m_car,
        })

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
    """Render the monthly calendar view with daily nutrition totals."""
    today = timezone.now().date()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    origin_date = request.GET.get('date', '')

    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = None

    items = (
        MealItem.objects
        .filter(user=request.user, date__year=year, date__month=month)
        .select_related('food')
    )

    # Aggregate totals per day.
    daily_totals = {}
    for item in items:
        d = item.date
        if d not in daily_totals:
            daily_totals[d] = {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0}
        daily_totals[d]['calories'] += item.total_calories
        daily_totals[d]['protein'] += item.total_protein
        daily_totals[d]['fat'] += item.total_fat
        daily_totals[d]['carbs'] += item.total_carbs

    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.monthdatescalendar(year, month)

    weeks_data = []
    for week in month_days:
        week_dict = {
            'days': [],
            'totals': {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0},
        }
        has_days_in_month = False

        for day in week:
            if day.month != month:
                continue

            has_days_in_month = True
            totals = daily_totals.get(
                day, {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0}
            )

            week_dict['totals']['calories'] += totals['calories']
            week_dict['totals']['protein'] += totals['protein']
            week_dict['totals']['fat'] += totals['fat']
            week_dict['totals']['carbs'] += totals['carbs']

            colors = {}
            if profile:
                colors['calories'] = calculate_color(
                    totals['calories'], profile.daily_calories_limit
                )
                colors['protein'] = calculate_color(
                    totals['protein'], profile.daily_protein_limit
                )
                colors['fat'] = calculate_color(
                    totals['fat'], profile.daily_fat_limit
                )
                colors['carbs'] = calculate_color(
                    totals['carbs'], profile.daily_carbs_limit
                )

            week_dict['days'].append({
                'date': day,
                'name': day.strftime('%A'),
                'totals': totals,
                'colors': colors,
            })

        if has_days_in_month:
            weeks_data.append(week_dict)

    month_name = calendar.month_name[month]
    prev_month_date = today.replace(year=year, month=month, day=1) - timedelta(days=1)
    next_month_date = today.replace(year=year, month=month, day=28) + timedelta(days=4)

    context = {
        'weeks_data': weeks_data,
        'month_name': month_name,
        'year': year,
        'prev_year': prev_month_date.year,
        'prev_month': prev_month_date.month,
        'next_year': next_month_date.year,
        'next_month': next_month_date.month,
        'profile': profile,
        'origin_date': origin_date,
    }
    return render(request, 'tracker/calendar.html', context)


# ---------------------------------------------------------------------------
# Food CRUD views
# ---------------------------------------------------------------------------

class FoodListView(LoginRequiredMixin, ListView):
    """List food records. Superusers see all records; users see their own."""

    model = Food
    template_name = 'tracker/food_list.html'
    context_object_name = 'foods'

    def get_queryset(self):
        user = self.request.user
        qs = Food.objects.all() if user.is_superuser else Food.objects.filter(owner=user)

        sort = self.request.GET.get('sort', 'newest')
        sort_map = {
            'name_asc': 'name',
            'name_desc': '-name',
            'oldest': 'id',
        }
        return qs.order_by(sort_map.get(sort, '-id'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['origin_date'] = self.request.GET.get('date', '')
        context['current_sort'] = self.request.GET.get('sort', 'newest')
        return context


class FoodCreateView(LoginRequiredMixin, CreateView):
    """Create a new food record. Pre-fills data from the barcode scanner session."""

    model = Food
    form_class = FoodForm
    template_name = 'tracker/food_form.html'

    def get_initial(self):
        initial = super().get_initial()
        # Pop scanned food data from session if a barcode scan preceded this form.
        scanned_food = self.request.session.pop('scanned_food', None)
        if scanned_food:
            initial.update(scanned_food)
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['origin_date'] = self.request.GET.get('date', '')
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        date_param = self.request.GET.get('date')
        base_url = reverse_lazy('tracker:food_list')
        return f'{base_url}?date={date_param}' if date_param else str(base_url)


class FoodUpdateView(LoginRequiredMixin, UpdateView):
    """Edit an existing food record owned by the current user."""

    model = Food
    form_class = FoodForm
    template_name = 'tracker/food_form.html'

    def get_queryset(self):
        user = self.request.user
        return Food.objects.all() if user.is_superuser else Food.objects.filter(owner=user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['origin_date'] = self.request.GET.get('date', '')
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        date_param = self.request.GET.get('date')
        base_url = reverse_lazy('tracker:food_list')
        return f'{base_url}?date={date_param}' if date_param else str(base_url)


class FoodDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a food record owned by the current user."""

    model = Food
    template_name = 'tracker/food_confirm_delete.html'

    def get_queryset(self):
        user = self.request.user
        return Food.objects.all() if user.is_superuser else Food.objects.filter(owner=user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['origin_date'] = self.request.GET.get('date', '')
        return context

    def get_success_url(self):
        date_param = self.request.GET.get('date')
        base_url = reverse_lazy('tracker:food_list')
        return f'{base_url}?date={date_param}' if date_param else str(base_url)


# ---------------------------------------------------------------------------
# Meal item CRUD views
# ---------------------------------------------------------------------------

@login_required
def meal_item_add(request):
    """Add a food item to a specific date and meal type.

    GET  — render the form.
    POST — create the MealItem record and redirect to the dashboard.
    """
    date_str = request.GET.get('date')
    selected_meal_type = request.GET.get('meal_type')

    if date_str:
        try:
            current_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            current_date = timezone.now().date()
    else:
        current_date = timezone.now().date()

    foods_json = _get_foods_json(request.user)

    if request.method == 'POST':
        meal_type = request.POST.get('meal_type')
        quantity_str = request.POST.get('quantity')
        multiplier_str = request.POST.get('portion_multiplier')

        if quantity_str and multiplier_str and meal_type:
            try:
                quantity = _parse_float_value(quantity_str)
                multiplier = _parse_float_value(multiplier_str)
                final_weight = quantity * multiplier

                food_obj = _resolve_food_from_post(request, request.POST)

                if food_obj:
                    MealItem.objects.create(
                        user=request.user,
                        date=current_date,
                        meal_type=meal_type,
                        food=food_obj,
                        weight_grams=final_weight,
                    )
            except Exception:
                logger.exception('Failed to add meal item')

        return redirect(
            f"{reverse('tracker:dashboard')}?date={current_date.isoformat()}"
        )

    return render(request, 'tracker/meal_item_form.html', {
        'default_meals': DEFAULT_MEAL_NAMES,
        'selected_meal_type': selected_meal_type,
        'foods_json': foods_json,
        'is_edit': False,
        'current_date': current_date,
    })


@login_required
def meal_item_edit(request, pk):
    """Edit an existing meal item owned by the current user.

    GET  — render the form pre-filled with current values.
    POST — update the record and redirect to the dashboard.
    """
    item = get_object_or_404(MealItem, pk=pk, user=request.user)
    current_date = item.date
    foods_json = _get_foods_json(request.user)

    if request.method == 'POST':
        meal_type = request.POST.get('meal_type')
        quantity_str = request.POST.get('quantity')
        multiplier_str = request.POST.get('portion_multiplier')

        if quantity_str and multiplier_str and meal_type:
            try:
                quantity = _parse_float_value(quantity_str)
                multiplier = _parse_float_value(multiplier_str)
                final_weight = quantity * multiplier

                food_obj = _resolve_food_from_post(request, request.POST)

                if food_obj:
                    item.meal_type = meal_type
                    item.food = food_obj
                    item.weight_grams = final_weight
                    item.save()
            except Exception:
                logger.exception('Failed to edit meal item')

        return redirect(
            f"{reverse('tracker:dashboard')}?date={current_date.isoformat()}"
        )

    return render(request, 'tracker/meal_item_form.html', {
        'item': item,
        'default_meals': DEFAULT_MEAL_NAMES,
        'selected_meal_type': item.meal_type,
        'foods_json': foods_json,
        'is_edit': True,
        'current_date': current_date,
    })


@login_required
def meal_item_delete(request, pk):
    """Delete a meal item. Accept POST only; redirect to dashboard after delete."""
    item = get_object_or_404(MealItem, pk=pk, user=request.user)
    date_iso = item.date.isoformat()
    if request.method == 'POST':
        item.delete()
    return redirect(f"{reverse('tracker:dashboard')}?date={date_iso}")


@login_required
def meal_item_duplicate(request, pk):
    """Create a copy of a meal item with the same food, date, and meal type."""
    item = get_object_or_404(MealItem, pk=pk, user=request.user)
    MealItem.objects.create(
        user=item.user,
        date=item.date,
        meal_type=item.meal_type,
        food=item.food,
        weight_grams=item.weight_grams,
    )
    return redirect(f"{reverse('tracker:dashboard')}?date={item.date.isoformat()}")


# ---------------------------------------------------------------------------
# Profile and settings views
# ---------------------------------------------------------------------------

class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """Edit the current user's daily macro limits.

    Create a new UserProfile when one does not exist yet.
    """

    model = UserProfile
    form_class = ProfileForm
    template_name = 'tracker/edit_daily_limits_form.html'
    success_url = reverse_lazy('tracker:dashboard')

    def get_object(self, queryset=None):
        try:
            return self.request.user.profile
        except UserProfile.DoesNotExist:
            return UserProfile(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Use the referer as the cancel destination; fall back to the dashboard.
        cancel_url = (
            self.request.POST.get('cancel_url')
            or self.request.META.get('HTTP_REFERER')
            or reverse('tracker:dashboard')
        )
        context['cancel_url'] = cancel_url
        return context


@login_required
def settings_view(request):
    """Render the settings page."""
    return render(request, 'tracker/settings.html')


@login_required
def edit_username(request):
    """Change the current user's username after password verification.

    GET  — render the form.
    POST — save the new username and redirect to the dashboard.
    """
    if request.method == 'POST':
        form = UsernameChangeForm(request.user, request.POST)
        if form.is_valid():
            request.user.username = form.cleaned_data['new_username']
            request.user.save()
            return redirect('tracker:dashboard')
    else:
        form = UsernameChangeForm(request.user)
    return render(request, 'registration/change_username.html', {'form': form})


# ---------------------------------------------------------------------------
# Barcode and OpenFoodFacts integration views
# ---------------------------------------------------------------------------

@login_required
def add_by_barcode(request):
    """Scan a barcode and fetch product data from OpenFoodFacts.

    On success, store the product data in the session and redirect to the
    food creation form so the user can review and save it.
    """
    origin_date = request.GET.get('date', '')
    base_url = reverse('tracker:food_create')
    redirect_url = f'{base_url}?date={origin_date}' if origin_date else base_url

    if request.method == 'POST':
        barcode = request.POST.get('barcode').strip()

        # Check if the product already exists in the user's food database.
        if request.user.is_superuser:
            existing_food = Food.objects.filter(barcode=barcode).first()
        else:
            existing_food = Food.objects.filter(
                barcode=barcode, owner=request.user
            ).first()

        if existing_food:
            messages.error(
                request,
                f"Product '{existing_food.name}' is already in your database.",
            )
            return redirect(redirect_url)

        api_url = f'https://world.openfoodfacts.org/api/v0/product/{barcode}.json'

        try:
            req = urllib.request.Request(api_url, headers={'User-Agent': 'MacroTracker/1.0'})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode('utf-8'))

            if data.get('status') == 1:
                product = data.get('product', {})
                name = product.get('product_name', 'Unknown Product')
                nutriments = product.get('nutriments', {})

                def safe_float(val):
                    """Convert API value to float. Return 0.0 on failure."""
                    try:
                        return float(val) if val else 0.0
                    except (ValueError, TypeError):
                        return 0.0

                serving_qty = product.get('serving_quantity')
                serving_text = product.get('serving_size')

                custom_portions = {}
                if serving_qty:
                    qty_float = safe_float(serving_qty)
                    if qty_float > 0:
                        portion_name = (
                            serving_text if serving_text else f'Portion ({qty_float}g/ml)'
                        )
                        custom_portions[portion_name] = qty_float

                request.session['scanned_food'] = {
                    'name': name,
                    'barcode': barcode,
                    'calories': safe_float(nutriments.get('energy-kcal_100g', 0)),
                    'protein': safe_float(nutriments.get('proteins_100g', 0)),
                    'fat': safe_float(nutriments.get('fat_100g', 0)),
                    'carbs': safe_float(nutriments.get('carbohydrates_100g', 0)),
                    'portions': custom_portions,
                }
                return redirect(redirect_url)

            messages.error(
                request,
                f"Product with barcode '{barcode}' not found on OpenFoodFacts.",
            )
            return redirect(redirect_url)

        except Exception:
            logger.exception('Error connecting to OpenFoodFacts')
            messages.error(request, 'Error connecting to OpenFoodFacts.')
            return redirect(redirect_url)

    return render(request, 'tracker/barcode_form.html', {'origin_date': origin_date})


@login_required
@require_POST
def save_off_food(request):
    """Save an OpenFoodFacts product to the user's food database.

    Accept a JSON body. Return the saved food id and name as JSON.
    If the product already exists (by barcode), return the existing record.
    """
    try:
        data = json.loads(request.body)
        barcode = data.get('barcode')

        if not barcode:
            return JsonResponse({'error': 'No barcode provided'}, status=400)

        def safe_float(val):
            """Convert value to float. Return 0.0 on failure."""
            try:
                return float(val) if val else 0.0
            except (ValueError, TypeError):
                return 0.0

        if request.user.is_superuser:
            existing_food = Food.objects.filter(barcode=barcode).first()
        else:
            existing_food = Food.objects.filter(
                barcode=barcode, owner=request.user
            ).first()

        if existing_food:
            return JsonResponse({'id': existing_food.id, 'name': existing_food.name})

        new_food = Food.objects.create(
            owner=request.user,
            barcode=barcode,
            name=data.get('name', 'Unknown API Food'),
            calories=safe_float(data.get('kcal')),
            protein=safe_float(data.get('protein')),
            fat=safe_float(data.get('fat')),
            carbs=safe_float(data.get('carbs')),
        )
        return JsonResponse({'id': new_food.id, 'name': new_food.name})

    except Exception:
        logger.exception('Failed to save OpenFoodFacts food')
        return JsonResponse({'error': 'Internal error'}, status=400)


def off_search(request):
    """Render the OpenFoodFacts product search page."""
    return render(request, 'tracker/off_search.html')