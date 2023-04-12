from tools.models import OrganizationTag


def test_organizationtag_cssclass():
    tag = OrganizationTag(color="blue-dark", border_type="dashed")

    assert tag.css_class == "tags-blue-dark dashed"


def test_user_organization_cache(superuser_member, django_assert_num_queries):
    with django_assert_num_queries(1):
        assert len(superuser_member.user.organizations) == 1
        assert len(superuser_member.user.organizations) == 1
