from django.urls import path

from account.views.account import AccountView
from account.views.login import LoginOpenKATView, LogoutOpenKATView, SetupOpenKATView
from account.views.password_reset import PasswordResetConfirmView, PasswordResetView
from account.views.recover_email import RecoverEmailView

urlpatterns = [
    path("<organization_code>/account/", AccountView.as_view(), name="account_detail"),
    path("login/", LoginOpenKATView.as_view(), name="login"),  # Bypass the two_factor login
    path("logout/", LogoutOpenKATView.as_view(), name="logout"),
    path(
        "two_factor/setup/", SetupOpenKATView.as_view(), name="setup"
    ),  # Bypass the two_factor setup show that users have to be verified
    path("recover-email/", RecoverEmailView.as_view(), name="recover_email"),
    path("password_reset/", PasswordResetView.as_view(), name="password_reset"),
    path("reset/<uidb64>/<token>/", PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
]
