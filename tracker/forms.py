from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Food, Meal, MealItem, UserProfile


class FoodForm(forms.ModelForm):
    class Meta:
        model = Food
        fields = ['name', 'barcode', 'calories', 'protein', 'fat', 'carbs', 'portions']
        labels = {
            'barcode': '',
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g. Chicken Breast', 'autocomplete': 'off'}),
            'barcode': forms.HiddenInput(),
            'carbs': forms.NumberInput(attrs={'placeholder': '0', 'step': 'any', 'min': '0'}),
        }

        def clean_carbs(self):
            return self.cleaned_data.get('carbs') or 0.0


class MealItemForm(forms.ModelForm):
    class Meta:
        model = MealItem
        fields = ['food', 'weight_grams']
        widgets = {
            'food': forms.HiddenInput(),
            'weight_grams': forms.NumberInput(attrs={
                'step': 'any', 'min': '0.01', 'placeholder': 'e.g. 150'
            }),
        }

    def full_clean(self):
        if self.is_bound and self.data:
            weight_val = self.data.get('weight_grams')
            if isinstance(weight_val, str) and ',' in weight_val:
                mutable_data = self.data.copy()
                mutable_data['weight_grams'] = weight_val.replace(',', '.')
                self.data = mutable_data
        super().full_clean()


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