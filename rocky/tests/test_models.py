from tools.models import OrganizationTag


def test_organizationtag_cssclass():
    tag = OrganizationTag(color="blue-dark", border_type="dashed")

    assert tag.css_class == "tags-blue-dark dashed"
