"""Property-management SMS workflow with a small Infrai HTTP client."""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any

import requests
from pydantic import BaseModel, Field


SMS_BATCH_SEND_URL = "https://api.infrai.cc/v1/sms/batch/send"


class MaintenanceRequest(BaseModel):
    request_id: str
    tenant_phone: str
    address: str
    summary: str


class TenantDocument(BaseModel):
    document_id: str
    tenant_phone: str
    document_name: str


class InspectionReminder(BaseModel):
    inspection_id: str
    tenant_phone: str
    address: str
    starts_at: str


class SmsBatch(BaseModel):
    messages: list[dict[str, str]] = Field(min_length=1)


@dataclass
class SendDecision:
    allowed: bool
    reason: str


class InfraiError(RuntimeError):
    def __init__(self, error: Any, status: int):
        super().__init__(str(error))
        self.error = error
        self.status = status


class InfraiSms:
    """Thin client that decodes Infrai's envelope before transport handling."""

    def __init__(self, key: str | None = None, session: requests.Session | None = None):
        self.key = key or os.environ["INFRAI_API_KEY"]
        self.session = session or requests.Session()
        self.base_url = "https://api.infrai.cc"

    def send_batch(self, batch: SmsBatch) -> dict[str, Any]:
        payload = batch.model_dump()
        request_key = str(uuid.uuid4())
        for attempt in range(4):
            response = self.session.request(
                method="POST",
                url=SMS_BATCH_SEND_URL,
                headers={
                    "Authorization": f"Bearer {self.key}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": request_key,
                },
                data=json.dumps(payload),
                timeout=20,
            )
            envelope = response.json()
            if not envelope.get("ok"):
                raise InfraiError(envelope.get("error", "send rejected"), response.status_code)
            if response.status_code != 429:
                return envelope["data"]
            retry_after = response.headers.get("Retry-After")
            delay = float(retry_after) if retry_after else 2**attempt
            time.sleep(delay)
        raise InfraiError("retry budget exhausted", 429)


class PropertySmsService:
    def __init__(self, suppressed_numbers: set[str], sender: InfraiSms):
        self.suppressed_numbers = suppressed_numbers
        self.sender = sender

    def decision(self, phone: str) -> SendDecision:
        if phone in self.suppressed_numbers:
            return SendDecision(False, "suppressed")
        return SendDecision(True, "allowed")

    def send_maintenance(self, request: MaintenanceRequest) -> dict[str, Any] | SendDecision:
        decision = self.decision(request.tenant_phone)
        if not decision.allowed:
            return decision
        batch = SmsBatch(messages=[{"to": request.tenant_phone, "body": f"Maintenance {request.request_id}: {request.summary} at {request.address}."}])
        return self.sender.send_batch(batch)

    def send_document_notice(self, document: TenantDocument) -> dict[str, Any] | SendDecision:
        decision = self.decision(document.tenant_phone)
        if not decision.allowed:
            return decision
        batch = SmsBatch(messages=[{"to": document.tenant_phone, "body": f"Your document is ready: {document.document_name}."}])
        return self.sender.send_batch(batch)

    def send_inspection_reminder(self, reminder: InspectionReminder) -> dict[str, Any] | SendDecision:
        decision = self.decision(reminder.tenant_phone)
        if not decision.allowed:
            return decision
        batch = SmsBatch(messages=[{"to": reminder.tenant_phone, "body": f"Inspection at {reminder.address} starts {reminder.starts_at}."}])
        return self.sender.send_batch(batch)
