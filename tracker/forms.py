from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Food, MealLog, UserProfile

class FoodForm(forms.ModelForm):
    class Meta:
        model = Food
        fields = ['name', 'barcode', 'calories', 'protein', 'fat', 'carbs']
        widgets = {
            'barcode': forms.HiddenInput() 
        }


class MealLogForm(forms.ModelForm):
    class Meta:
        model = MealLog
        fields = ['food', 'date', 'weight_grams']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'})
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set the max attribute dynamically to today
        self.fields['date'].widget.attrs['max'] = timezone.now().date().isoformat()

    def clean_date(self):
        selected_date = self.cleaned_data.get('date')
        if selected_date > timezone.now().date():
            raise ValidationError("You cannot log meals in the future.")
        return selected_date


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['daily_calories_limit', 'daily_protein_limit', 'daily_fat_limit', 'daily_carbs_limit']

class UsernameChangeForm(forms.Form):
    new_username = forms.CharField(max_length=150, label="New Username")
    password = forms.CharField(widget=forms.PasswordInput, label="Current Password")

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if not self.user.check_password(password):
            raise forms.ValidationError("Incorrect password.")
        return password