from enum import Enum
from io import BytesIO

from django.http import HttpResponse
from django.template.loader import get_template
from django.utils.translation import gettext_lazy as _
from xhtml2pdf import pisa

from tools.ooi_helpers import OOI_TYPES_WITHOUT_FINDINGS

translated_blank_choice = _("--- Select an option ----")
BLANK_CHOICE = [("", translated_blank_choice)]


def transform_ooi_types_to_choices():
    choices = BLANK_CHOICE.copy()
    for ooi_type in OOI_TYPES_WITHOUT_FINDINGS:
        choices.append((ooi_type, ooi_type))
    return tuple(choices)


OOI_TYPES = transform_ooi_types_to_choices()


def html_to_pdf(template_src, context_dict={}):
    encoder_type = "ISO-8859-1"
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode(encoder_type)), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type="application/pdf")
    return None


class RiskClass(Enum):
    NONE = None
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    VERY_LOW = "Very low"


def calculate_risk_class(frequency_level, detectability_level, severity_level):
    """
    Calculates the Risk Class of a failure mode based on 3 variables:
    Severity Level, Frequency Level and Detectabality Level.
    """
    risk_class = RiskClass.NONE
    risk_priority_number = severity_level * frequency_level * detectability_level
    critical_score = severity_level * frequency_level

    if risk_priority_number > 60 or critical_score > 14:
        risk_class = RiskClass.CRITICAL
    elif (40 <= risk_priority_number <= 60) or (11 <= critical_score <= 14):
        risk_class = RiskClass.HIGH
    elif (28 <= risk_priority_number <= 39) or (6 <= critical_score <= 10):
        risk_class = RiskClass.MEDIUM
    elif (9 <= risk_priority_number <= 27) or (3 <= critical_score <= 5):
        risk_class = RiskClass.LOW
    elif (1 <= risk_priority_number <= 8) or (1 <= critical_score <= 2):
        risk_class = RiskClass.VERY_LOW
    return risk_class
