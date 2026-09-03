import os


# Unit and equivalence tests exercise clinical endpoints directly. Production
# access control has dedicated tests and is enabled by default outside pytest.
os.environ.setdefault("CERAI_REQUIRE_ACCESS_KEY", "0")
