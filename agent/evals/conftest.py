# AI-generated: Claude Code (claude.ai/code) — eval fixtures
import os

import pytest


def pytest_collection_modifyitems(config, items):
    """Skip all eval tests if OpenEMR credentials are not configured."""
    client_id = os.environ.get("OPENEMR_CLIENT_ID", "")
    if not client_id:
        skip = pytest.mark.skip(reason="OPENEMR_CLIENT_ID not set — skipping evals")
        for item in items:
            item.add_marker(skip)
# end AI-generated
