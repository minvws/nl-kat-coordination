from django.views.generic import FormView

from rocky.views.ooi_view import BaseOOIFormView


class BoefjeSetupView(BaseOOIFormView, FormView):
    """View where the user can create a new boefje"""

    template_name = "boefje_setup.html"
