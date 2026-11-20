from src.property_sms_service import InspectionReminder, PropertySmsService


class UnusedSender:
    def send_batch(self, batch):
        raise AssertionError("suppressed messages must never reach the sender")


def test_inspection_reminder_is_suppressed_before_sending():
    service = PropertySmsService({"+15550001111"}, UnusedSender())
    result = service.send_inspection_reminder(
        InspectionReminder(
            inspection_id="inspection-7",
            tenant_phone="+15550001111",
            address="14 Market Street",
            starts_at="2026-11-03 10:00",
        )
    )
    assert result.allowed is False
    assert result.reason == "suppressed"

