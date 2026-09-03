"""Pure canonical CER-AI disposition aggregation."""

PASS = "PASS"
CAUTION = "CAUTION"
STOP_DEFER = "STOP-DEFER"
POST_REFRACTIVE = "POST-REFRACTIVE PATHWAY REQUIRED"
DATA_INSUFFICIENT = "DATA INSUFFICIENT"

STATUS_RANK = {
    PASS: 0,
    CAUTION: 1,
    POST_REFRACTIVE: 2,
    DATA_INSUFFICIENT: 3,
    STOP_DEFER: 4,
}


def combine_status(current: str, new: str) -> str:
    current_rank = STATUS_RANK.get(current)
    new_rank = STATUS_RANK.get(new)
    if current_rank is None or new_rank is None:
        raise ValueError(f"Unknown CER-AI decision status: current={current!r}, new={new!r}")
    return new if new_rank > current_rank else current


def presentation_class(status: str) -> str:
    if status == PASS:
        return "pass"
    if status == CAUTION:
        return "caution"
    if status == STOP_DEFER:
        return "fail"
    return "insufficient"
