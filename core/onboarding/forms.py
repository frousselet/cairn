"""Forms for the first-run onboarding flow."""

from django import forms
from django.contrib.auth import password_validation
from django.utils.translation import gettext_lazy as _

from accounts.models import User


class FirstAdminForm(forms.Form):
    """Create the very first super-admin from the onboarding screen."""

    email = forms.EmailField(
        label=_("Email address"),
        widget=forms.EmailInput(attrs={"class": "form-control", "autofocus": True, "autocomplete": "username"}),
    )
    first_name = forms.CharField(
        label=_("First name"),
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        label=_("Last name"),
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    password1 = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label=_("Confirm password"),
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
    )

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("A user with this email already exists."))
        return email

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(_("The two password fields do not match."))
        password_validation.validate_password(password2)
        return password2

    def save(self):
        """Create and return the first super-admin."""
        return User.objects.create_superuser(
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password1"],
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
        )
