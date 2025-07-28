from unittest.mock import patch

from admin_auto_tests.test_model import ModelAdminTestCase
from model_mommy import mommy, random_gen

from account.models import AuthToken
from openkat.models import Organization

mommy.generators.add("account.models.LowercaseEmailField", random_gen.gen_email)
mommy.generators.add("openkat.models.LowerCaseSlugField", random_gen.gen_slug)


class OrganizationAdminTestCase(ModelAdminTestCase):
    model = Organization

    def setUp(self):
        super().setUp()

        octopoes_patcher = patch("octopoes.connector.octopoes.OctopoesAPIConnector")
        octopoes_patcher.start()
        self.addCleanup(octopoes_patcher.stop)


class AuthTokenAdminTestCase(ModelAdminTestCase):
    model = AuthToken

    def create_form_instance_data(self, response, instance_data=None):
        ret = super().create_form_instance_data(response, instance_data)

        return ret

    def create(self, commit=True, model=None, follow_fk=True, generate_fk=True, field_values=None):
        model = model or self.model
        field_values = field_values or self.field_values or {}
        if commit:
            instance = mommy.make(model, **field_values)
        else:
            instance = mommy.prepare(model, **field_values, _save_related=True)
        return instance
