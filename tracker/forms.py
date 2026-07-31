from django import forms

from .models import Food, UserProfile


class FoodForm(forms.ModelForm):
    """Form for creating and editing a food record."""

    # Use CharField so users can enter decimals with a comma or a dot.
    calories = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={'placeholder': '0', 'inputmode': 'decimal'}
        ),
    )
    protein = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={'placeholder': '0', 'inputmode': 'decimal'}
        ),
    )
    fat = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={'placeholder': '0', 'inputmode': 'decimal'}
        ),
    )
    carbs = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={'placeholder': '0', 'inputmode': 'decimal'}
        ),
    )

    class Meta:
        model = Food
        fields = ['name', 'barcode', 'calories', 'protein', 'fat', 'carbs', 'portions']
        labels = {
            'barcode': '',
        }
        widgets = {
            'name': forms.TextInput(
                attrs={'placeholder': 'e.g. Chicken Breast', 'autocomplete': 'off'}
            ),
            'barcode': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Do not pre-fill zero values — keep the field empty for better UX.
        for field in ['calories', 'protein', 'fat', 'carbs']:
            val = self.initial.get(field)
            if val in [0, 0.0, '0', '0.0', None]:
                self.initial[field] = ''

    def _parse_macro(self, field_name):
        """Convert a macro field value to float. Replace comma with dot."""
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
    """Form for editing the user's daily macro limits."""

    class Meta:
        model = UserProfile
        fields = [
            'daily_calories_limit',
            'daily_protein_limit',
            'daily_fat_limit',
            'daily_carbs_limit',
        ]


class UsernameChangeForm(forms.Form):
    """Form for changing the username. Requires the current password."""

    new_username = forms.CharField(max_length=150, label='New Username')
    password = forms.CharField(widget=forms.PasswordInput, label='Current Password')

    def __init__(self, user, *args, **kwargs):
        # Store user so the password check can access it.
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        """Reject the form if the supplied password does not match."""
        password = self.cleaned_data.get('password')
        if not self.user.check_password(password):
            raise forms.ValidationError('Incorrect password.')
        return password