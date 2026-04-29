from __future__ import annotations

import pytest
from openpyxl import Workbook

from agents.fund.sandbox import SandboxRejected, SandboxTimeout, execute


def test_sandbox_rejects_malicious_artifact_code():
    wb = Workbook()

    with pytest.raises(SandboxRejected):
        list(execute("import os\n\ndef parse(wb, ctx):\n    return []", wb, {}, timeout=2))

    with pytest.raises(SandboxRejected):
        list(execute("def parse(wb, ctx):\n    eval('1+1')\n    return []", wb, {}, timeout=2))

    with pytest.raises(SandboxTimeout):
        list(execute("def parse(wb, ctx):\n    while True:\n        pass\n    return []", wb, {}, timeout=1))
