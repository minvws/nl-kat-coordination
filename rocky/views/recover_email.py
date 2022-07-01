from django.shortcuts import render
from django.views.generic import TemplateView


class RecoverEmailView(TemplateView):
    """
    Handler for email recovery.
    """

    template_name = "account/recover_email.html"
