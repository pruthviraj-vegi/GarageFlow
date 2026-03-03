from django import forms


class PhoneLoginForm(forms.Form):
    """Login form with phone number and password."""

    phone = forms.CharField(
        max_length=10,
        min_length=10,
        widget=forms.TextInput(
            attrs={
                "type": "tel",
                "id": "phone",
                "placeholder": "Enter 10-digit number",
                "maxlength": "10",
                "pattern": "[0-9]{10}",
                "autofocus": True,
            }
        ),
        label="Phone Number",
    )

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "id": "password",
                "placeholder": "Enter your password",
            }
        ),
        label="Password",
    )
