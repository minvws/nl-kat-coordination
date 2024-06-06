from rocky.views.finding_list import Top10FindingListView


class OrganizationCrisisRoomView(Top10FindingListView):
    template_name = "organizations/organization_crisis_room.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
