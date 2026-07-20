import calendar
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime, timedelta
import json
import urllib.request

from .models import MealLog, Food, UserProfile
from .forms import MealLogForm, FoodForm, ProfileForm, UsernameChangeForm

from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm



def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Automatically log the user in after successful registration
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
    # For 2000 kcal, it's 100 kcal. For 150g protein, it's 7.5g.
    buffer = limit * 0.05 
    
    if value == 0:
        return "hsl(120, 50%, 95%)"
        
    if value <= limit + buffer:
        # 0 to (limit + 5%): green gets darker/more saturated
        ratio = min(value / (limit + buffer), 1.0)
        lightness = 95 - (ratio * 35) # from 95% to 60%
        return f"hsl(120, 60%, {lightness}%)"
    else:
        # Over the limit + 5% buffer: transition from green to red
        excess = value - (limit + buffer)
        
        # Reaches solid red when exceeding the limit by 30%
        max_excess = limit * 0.25 
        
        if max_excess <= 0:
            max_excess = 1
            
        ratio = min(excess / max_excess, 1.0)
        hue = 120 - (ratio * 120) # 120 (Green) -> 0 (Red)
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

    daily_meals = MealLog.objects.filter(user=request.user, date=current_date)

    consumed_calories = sum(meal.total_calories for meal in daily_meals)
    consumed_protein = sum(meal.total_protein for meal in daily_meals)
    consumed_fat = sum(meal.total_fat for meal in daily_meals)
    consumed_carbs = sum(meal.total_carbs for meal in daily_meals)

    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = None

    # Calculate colors if profile exists
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

    logs = MealLog.objects.filter(user=request.user, date__year=year, date__month=month)
    
    daily_totals = {}
    for log in logs:
        d = log.date
        if d not in daily_totals:
            daily_totals[d] = {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0}
        daily_totals[d]['calories'] += log.total_calories
        daily_totals[d]['protein'] += log.total_protein
        daily_totals[d]['fat'] += log.total_fat
        daily_totals[d]['carbs'] += log.total_carbs

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
        qs = super().get_queryset()
        sort = self.request.GET.get('sort', 'newest')
        
        if sort == 'name_asc':
            return qs.order_by('name')
        elif sort == 'name_desc':
            return qs.order_by('-name')
        elif sort == 'oldest':
            return qs.order_by('id')
        else: # newest (default)
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

    def get_success_url(self):
        date_param = self.request.GET.get('date')
        base_url = reverse_lazy('tracker:food_list')
        return f"{base_url}?date={date_param}" if date_param else base_url

class FoodUpdateView(LoginRequiredMixin, UpdateView):
    model = Food
    form_class = FoodForm
    template_name = 'tracker/food_form.html'
    
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
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['origin_date'] = self.request.GET.get('date', '')
        return context

    def get_success_url(self):
        date_param = self.request.GET.get('date')
        base_url = reverse_lazy('tracker:food_list')
        return f"{base_url}?date={date_param}" if date_param else base_url


# --- MEAL LOG CRUD ---
class MealLogCreateView(LoginRequiredMixin, CreateView):
    model = MealLog
    form_class = MealLogForm
    template_name = 'tracker/meallog_form.html'
    
    def get_initial(self):
        # Retrieve the date from the URL to insert it into the form as the default value
        initial = super().get_initial()
        date_param = self.request.GET.get('date')
        if date_param:
            initial['date'] = date_param
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # We pass all the data in JSON format for searching via JavaScript
        foods = list(Food.objects.values('id', 'name', 'barcode'))
        context['foods_json'] = json.dumps(foods)
        return context

    def get_success_url(self):
        date_param = self.object.date.isoformat()
        return f"{reverse_lazy('tracker:dashboard')}?date={date_param}"

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class MealLogUpdateView(LoginRequiredMixin, UpdateView):
    model = MealLog
    form_class = MealLogForm
    template_name = 'tracker/meallog_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        foods = list(Food.objects.values('id', 'name', 'barcode'))
        context['foods_json'] = json.dumps(foods)
        return context

    def get_success_url(self):
        date_param = self.object.date.isoformat()
        return f"{reverse_lazy('tracker:dashboard')}?date={date_param}"

    def get_queryset(self):
        return MealLog.objects.filter(user=self.request.user)

class MealLogDeleteView(LoginRequiredMixin, DeleteView):
    model = MealLog
    template_name = 'tracker/meallog_confirm_delete.html'

    def get_success_url(self):
        date_param = self.object.date.isoformat()
        return f"{reverse_lazy('tracker:dashboard')}?date={date_param}"

    def get_queryset(self):
        return MealLog.objects.filter(user=self.request.user)


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = UserProfile
    form_class = ProfileForm
    template_name = 'tracker/profile_form.html'
    success_url = reverse_lazy('tracker:dashboard')

    def get_object(self, queryset=None):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile


# --- SETTINGS & BARCODE ---
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
    
    # General link to return to the ‘Add Food’ form (saving the date)
    base_url = reverse('tracker:food_create')
    redirect_url = f"{base_url}?date={origin_date}" if origin_date else base_url

    if request.method == 'POST':
        barcode = request.POST.get('barcode').strip()
        
        # 1. Check if a barcode like this already exists in the database
        existing_food = Food.objects.filter(barcode=barcode).first()
        if existing_food:
            messages.error(request, f"Product '{existing_food.name}' is already in your database.")
            return redirect(redirect_url)

        # 2. Send a request to the OpenFoodFacts API
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

                # 3. Don't save the data to the database; instead, store it in a temporary session
                request.session['scanned_food'] = {
                    'name': name,
                    'barcode': barcode,
                    'calories': safe_float(nutriments.get('energy-kcal_100g', 0)),
                    'protein': safe_float(nutriments.get('proteins_100g', 0)),
                    'fat': safe_float(nutriments.get('fat_100g', 0)),
                    'carbs': safe_float(nutriments.get('carbohydrates_100g', 0))
                }
                
                # Drag and drop into the ‘Add Food’ form to preview
                return redirect(redirect_url)
            else:
                messages.error(request, f"Product with barcode '{barcode}' not found on OpenFoodFacts.")
                return redirect(redirect_url)
        
        except Exception as e:
            messages.error(request, f"Error connecting to OpenFoodFacts: {str(e)}")
            return redirect(redirect_url)
        
    return render(request, 'tracker/barcode_form.html', {'origin_date': origin_date})