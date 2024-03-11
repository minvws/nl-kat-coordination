from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.utils.translation import gettext_lazy as _


class RockyPaginator(Paginator):
    def __init__(
        self,
        object_list,
        per_page: int | str,
        orphans: int = 0,
        allow_empty_first_page: bool = True,
    ) -> None:
        super().__init__(object_list, per_page, orphans, allow_empty_first_page)

        if orphans != 0:
            raise ValueError("Setting orphans is not supported")

    def validate_number(self, number):
        """Validate the given 1-based page number."""
        try:
            if isinstance(number, float) and not number.is_integer():
                raise ValueError
            number = int(number)
        except (TypeError, ValueError):
            raise PageNotAnInteger(_("That page number is not an integer"))
        if number < 1:
            raise EmptyPage(_("That page number is less than 1"))
        return number

    def page(self, number):
        """Return a Page object per page number."""
        number = self.validate_number(number)
        bottom = (number - 1) * self.per_page
        top = bottom + self.per_page
        page_objects = self.object_list[bottom:top]
        if not page_objects and number > self.num_pages:
            raise EmptyPage(_("That page contains no results"))
        return self._get_page(page_objects, number, self)
