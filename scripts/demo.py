import os

from src.property_sms_service import InfraiSms, InspectionReminder, PropertySmsService


phone = os.environ.get("DEMO_TENANT_PHONE")
if not phone:
    raise SystemExit("Set DEMO_TENANT_PHONE before running the demo")

service = PropertySmsService(set(), InfraiSms())
result = service.send_inspection_reminder(
    InspectionReminder(
        inspection_id="inspection-demo",
        tenant_phone=phone,
        address="14 Market Street",
        starts_at="2026-11-03 10:00",
    )
)
print("inspection reminder result:", result)

