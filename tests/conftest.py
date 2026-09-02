import importlib
import os

import pytest


# Unit and equivalence tests exercise clinical endpoints directly. Production
# access control has dedicated tests and is enabled by default outside pytest.
os.environ.setdefault("CERAI_REQUIRE_ACCESS_KEY", "0")


def _runtime_state_baseline():
    """Capture the composed canonical callable surface before test collection.

    Several legacy policy test modules perform wrapper installation or other
    module-level mutations during pytest collection. Capturing the baseline only
    when the first test starts is therefore too late. This snapshot is taken as
    conftest is imported, before pytest imports the test modules themselves.
    Production runtime composition is unchanged.
    """
    import canonical_engine
    import runtime_composition

    core = canonical_engine.core
    modules = {"app": core}
    for phase_modules in runtime_composition.COMPOSITION_PHASES.values():
        for module_name in phase_modules:
            modules[module_name] = importlib.import_module(module_name)

    snapshots = {}
    for module_name, module in modules.items():
        state = {}
        for name, value in vars(module).items():
            if callable(value) or name.startswith(("_previous_", "_original_")):
                state[name] = value
        snapshots[module_name] = (module, state)
    return snapshots


# Critical: capture before pytest collection imports test modules.
_CANONICAL_TEST_BASELINE = _runtime_state_baseline()


@pytest.fixture(autouse=True)
def _restore_canonical_runtime_state_between_tests():
    """Prevent legacy wrapper/global state from leaking between test cases."""
    for module, state in _CANONICAL_TEST_BASELINE.values():
        for name, value in state.items():
            setattr(module, name, value)

    yield

    for module, state in _CANONICAL_TEST_BASELINE.values():
        for name, value in state.items():
            setattr(module, name, value)
