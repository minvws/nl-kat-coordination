from rocky.views.finding_list import Top10FindingListView


class OrganizationCrisisRoomView(Top10FindingListView):
    template_name = "organizations/organization_crisis_room.html"
