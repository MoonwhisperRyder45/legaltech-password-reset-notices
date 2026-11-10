from src.password_reset import InfraiClient, MatterIntake, ResetRequest, start_reset


def test_reset_notice_carries_matter_follow_up_and_returns_message_id():
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        if path.endswith("reset_request"):
            return 200, {"ok": True, "data": {"reset_link": "https://portal.test/reset/abc"}}
        return 200, {"ok": True, "data": {"message_id": "msg-42"}}

    flow = ResetRequest("client@example.com", MatterIntake("M-7", "Lee", "delivered", "2026-12-01"))
    result = start_reset(flow, InfraiClient("test-key", transport=transport))

    assert result == "msg-42"
    assert calls[0] == ("POST", "/v1/auth/password/reset_request", {"email": "client@example.com"})
    assert calls[1][0:2] == ("POST", "/v1/email/send")
    assert "M-7" in calls[1][2]["body"]
    assert "2026-12-01" in calls[1][2]["body"]
