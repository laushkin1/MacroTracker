from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Food, MealItem, UserProfile


class FoodForm(forms.ModelForm):
    calories = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': '0', 'inputmode': 'decimal'}))
    protein = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': '0', 'inputmode': 'decimal'}))
    fat = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': '0', 'inputmode': 'decimal'}))
    carbs = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': '0', 'inputmode': 'decimal'}))

    class Meta:
        model = Food
        fields = ['name', 'barcode', 'calories', 'protein', 'fat', 'carbs', 'portions']
        labels = {
            'barcode': '',
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g. Chicken Breast', 'autocomplete': 'off'}),
            'barcode': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ['calories', 'protein', 'fat', 'carbs']:
            val = self.initial.get(field)
            if val in [0, 0.0, '0', '0.0', None]:
                self.initial[field] = ''

    def _parse_macro(self, field_name):
        val = self.cleaned_data.get(field_name)
        if not val:
            return 0.0
        try:
            return float(str(val).replace(',', '.'))
        except ValueError:
            return 0.0

    def clean_calories(self): 
        return self._parse_macro('calories')
        
    def clean_protein(self): 
        return self._parse_macro('protein')
        
    def clean_fat(self): 
        return self._parse_macro('fat')
        
    def clean_carbs(self): 
        return self._parse_macro('carbs')


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