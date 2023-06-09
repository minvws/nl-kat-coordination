from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from tools.models import Organization, OrganizationTag


def test_organizationtag_cssclass():
    tag = OrganizationTag(color="blue-dark", border_type="dashed")

    assert tag.css_class == "tags-blue-dark dashed"


def test_user_organization_cache(superuser_member, django_assert_num_queries):
    with django_assert_num_queries(1):
        assert len(superuser_member.user.organizations) == 1
        assert len(superuser_member.user.organizations) == 1


def test_organizationmember_no_permissions(active_member, django_assert_num_queries):
    with django_assert_num_queries(3):
        assert not active_member.has_perm("tools.view_organization")
        assert not active_member.has_perm("tools.can_scan_organization")
        assert not active_member.has_perm("tools.can_enable_disable_boefje")


def test_organizationmember_permissions(active_member, django_assert_num_queries):
    content_type = ContentType.objects.get_for_model(Organization)
    view_organization = Permission.objects.get(codename="view_organization", content_type=content_type)
    can_scan_organization = Permission.objects.get(codename="can_scan_organization", content_type=content_type)
    can_enable_disable_boefje = Permission.objects.get(codename="can_enable_disable_boefje", content_type=content_type)

    group1 = Group.objects.create(name="group1")
    group2 = Group.objects.create(name="group2")

    active_member.user.user_permissions.add(view_organization)
    group1.permissions.add(can_scan_organization)
    group2.permissions.add(can_enable_disable_boefje)

    active_member.user.groups.add(group1)
    active_member.groups.add(group2)

    with django_assert_num_queries(3):
        assert active_member.has_perm("tools.view_organization")
        assert active_member.has_perm("tools.can_scan_organization")
        assert active_member.has_perm("tools.can_enable_disable_boefje")


def test_organizationmember_permissions_superuser(superuser_member, django_assert_num_queries):
    with django_assert_num_queries(1):
        assert superuser_member.has_perm("tools.view_organization")
        assert superuser_member.has_perm("tools.can_scan_organization")
        assert superuser_member.has_perm("tools.can_enable_disable_boefje")
