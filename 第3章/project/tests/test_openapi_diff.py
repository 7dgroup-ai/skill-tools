from contract.openapi_diff import Change, diff_compat

OLD = {
    "paths": {
        "/api/order/pay": {
            "post": {
                "requestBody": {"content": {"application/json": {"schema": {
                    "type": "object",
                    "required": ["order_id", "pay_type"],
                    "properties": {"order_id": {"type": "string"},
                                   "pay_type": {"type": "string"},
                                   "remark": {"type": "string"}},
                }}}},
            }
        },
        "/api/order/legacy": {"get": {}},
    }
}

NEW = {
    "paths": {
        "/api/order/pay": {
            "post": {
                "requestBody": {"content": {"application/json": {"schema": {
                    "type": "object",
                    "required": ["order_id"],
                    "properties": {"order_id": {"type": "string"},
                                   "pay_type": {"type": "string"}},
                }}}},
            }
        },
        "/api/order/v2": {"get": {}},
    }
}


def test_breaking_change_required_field_removed():
    changes = diff_compat(OLD, NEW)
    breaking = [c for c in changes if c.breaking]
    assert any(c.kind == "required_removed" and "pay_type" in c.target for c in breaking)


def test_breaking_change_path_removed():
    changes = diff_compat(OLD, NEW)
    assert any(c.kind == "remove_path" and c.target == "/api/order/legacy" for c in changes)


def test_compatible_change_add_path():
    changes = diff_compat(OLD, NEW)
    assert any(c.kind == "add_path" and not c.breaking for c in changes)
