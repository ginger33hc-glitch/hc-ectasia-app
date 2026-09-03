from types import SimpleNamespace

import srax_completion_policy as policy


def test_install_adds_binary_srax_completion_without_replacing_other_requests():
    calls = []

    def base_request(eye, message, extracted):
        calls.append((eye, message))
        return {"eye": eye, "kind": "instruction", "key": message}

    workflow = SimpleNamespace(PATTERNS={}, _request=base_request)
    policy.install(workflow)
    policy.install(workflow)

    assert workflow.PATTERNS["srax"] == ["YES", "NO"]
    item = workflow._request(
        "OD",
        "SRAX >20° confirmation from the Axial/Sagittal Curvature (Front) map",
        {},
    )
    assert item["eye"] == "OD"
    assert item["kind"] == "select"
    assert item["key"] == "srax"
    assert item["options"] == ["YES", "NO"]
    assert "Axial/Sagittal Curvature (Front)" in item["label"]
    assert "Exact 20° is NO" in item["help"]
    assert "KISA" in item["help"]
    assert calls == []

    other = workflow._request("OD", "Signed I-S (D) required", {})
    assert other["kind"] == "instruction"
    assert calls == [("OD", "Signed I-S (D) required")]
