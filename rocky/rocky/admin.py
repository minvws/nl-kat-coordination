from django.contrib import messages
from django.http import HttpResponseRedirect

from rocky.exceptions import RockyError


class AdminErrorMessageMixin:
    def add_view(self, request, *args, **kwargs):
        try:
            return super().add_view(request, *args, **kwargs)
        except RockyError as e:
            self.message_user(request, str(e), level=messages.ERROR)
            return HttpResponseRedirect(request.get_full_path())
