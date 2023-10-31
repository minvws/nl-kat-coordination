from django.core.management.commands import makemessages


class Command(makemessages.Command):
    def write_po_file(self, *args, **kwargs):
        """Overwrite method to do nothing.

        We do not want to interfere with Weblate's
        "Update PO files to match POT (msgmerge)" addon
        """
        pass
