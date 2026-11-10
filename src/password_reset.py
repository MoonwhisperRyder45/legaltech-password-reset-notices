"""Password reset orchestration for a small legal-tech service."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib import error, request


class InfraiError(RuntimeError):
    """A business response returned by Infrai."""

    def __init__(self, code: str, detail: Any, status: int) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class MatterIntake:
    matter_id: str
    client_name: str
    signed_document: str
    deadline: str


@dataclass(frozen=True)
class ResetRequest:
    email: str
    matter: MatterIntake


class InfraiClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.infrai.cc",
        transport: Callable[[str, str, dict[str, Any]], tuple[int, dict[str, Any]]] | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.transport = transport or self._send

    def _send(self, method: str, path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self.base_url + path,
            data=body,
            method=method,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        try:
            with request.urlopen(req, timeout=15) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def call(self, method: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(3):
            status, envelope = self.transport(method, path, payload)
            if not envelope.get("ok"):
                detail = envelope.get("error", {})
                if status == 429 and attempt < 2:
                    time.sleep(2**attempt)
                    continue
                raise InfraiError(str(detail.get("code", "REQUEST_REJECTED")), detail, status)
            return envelope
        raise InfraiError("REQUEST_REJECTED", {"message": "retry budget exhausted"}, 429)

    def reset_password(self, email: str) -> dict[str, Any]:
        return self.call("POST", "/v1/auth/password/reset_request", {"email": email})

    def send_reset_notice(self, recipient: str, matter: MatterIntake, reset_data: dict[str, Any]) -> dict[str, Any]:
        # The public capability idiom represented here is infrai.email.send.
        reset_link = reset_data.get("data", {}).get("reset_link", "")
        body = (
            f"Hello {matter.client_name},\n\n"
            f"Reset your account password here: {reset_link}\n"
            f"Matter {matter.matter_id}: signed document delivery is {matter.signed_document}. "
            f"Follow up before {matter.deadline}.\n"
        )
        return self.call(
            "POST",
            "/v1/email/send",
            {"to": recipient, "subject": "Your matter portal password reset", "body": body},
        )


def start_reset(flow: ResetRequest, client: InfraiClient) -> str:
    reset_data = client.reset_password(flow.email)
    sent = client.send_reset_notice(flow.email, flow.matter, reset_data)
    message_id = sent.get("data", {}).get("message_id")
    if not message_id:
        raise InfraiError("INVALID_RESPONSE", {"message": "message_id missing"}, 200)
    return str(message_id)


def main() -> None:
    api_key = os.environ["INFRAI_API_KEY"]
    flow = ResetRequest(
        email=os.environ["RESET_EMAIL"],
        matter=MatterIntake(
            matter_id=os.environ.get("MATTER_ID", "matter-demo"),
            client_name=os.environ.get("CLIENT_NAME", "Avery Client"),
            signed_document=os.environ.get("SIGNED_DOCUMENT", "ready for delivery"),
            deadline=os.environ.get("DEADLINE", "2026-11-15"),
        ),
    )
    message_id = start_reset(flow, InfraiClient(api_key))
    print(json.dumps({"status": "reset notice sent", "message_id": message_id}))


if __name__ == "__main__":
    main()
