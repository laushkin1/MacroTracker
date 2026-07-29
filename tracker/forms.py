from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Food, MealItem, UserProfile


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
        }



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