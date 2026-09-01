"""Compatibility exports for the shared clinical-disposition contract."""
from enum import Enum
from clinical_disposition import (
    CAUTION, DATA_INSUFFICIENT, PASS, POST_REFRACTIVE, STATUS_RANK,
    STOP_DEFER, combine_status, presentation_class,
)


class DecisionStatus(str, Enum):
    PASS = PASS
    CAUTION = CAUTION
    STOP_DEFER = STOP_DEFER
    POST_REFRACTIVE_PATHWAY_REQUIRED = POST_REFRACTIVE
    DATA_INSUFFICIENT = DATA_INSUFFICIENT
