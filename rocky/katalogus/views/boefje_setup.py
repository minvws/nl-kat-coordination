from django.http import HttpResponseRedirect
from django.views.generic.edit import FormView
from tools.forms.boefje import BoefjeAddForm


class BoefjeSetupView(FormView):
    """View where the user can create a new boefje"""

    template_name = "boefje_setup.html"
    form_class = BoefjeAddForm

    def form_valid(self, form):
        """If the form is valid, redirect to the supplied URL."""
        return HttpResponseRedirect(self.get_success_url())

    def get_form(self, form_class=None) -> BoefjeAddForm:
        if form_class is None:
            form_class = self.get_form_class()

        return form_class(**self.get_form_kwargs())
