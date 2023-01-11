from unittest.mock import patch

from admin_auto_tests.test_model import ModelAdminTestCase
from model_mommy import mommy, random_gen

from tools.models import Organization


mommy.generators.add("account.models.LowercaseEmailField", random_gen.gen_email)
mommy.generators.add("tools.fields.LowerCaseSlugField", random_gen.gen_slug)


class OrganizationAdminTestCase(ModelAdminTestCase):
    model = Organization

    def setUp(self):
        super().setUp()

        katalogus_patcher = patch("tools.models.get_katalogus")
        katalogus_patcher.start()
        self.addCleanup(katalogus_patcher.stop)

        octopoes_patcher = patch("tools.models.OctopoesAPIConnector")
        octopoes_patcher.start()
        self.addCleanup(octopoes_patcher.stop)
