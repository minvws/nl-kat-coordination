from admin_auto_tests.test_model import ModelAdminTestCase
from model_mommy import mommy, random_gen

from tools.models import Organization


mommy.generators.add("account.models.LowercaseEmailField", random_gen.gen_email)
mommy.generators.add("tools.fields.LowerCaseSlugField", random_gen.gen_slug)


class OrganizationAdminTestCase(ModelAdminTestCase):
    model = Organization
