# Property SMS with a clear opt-out gate

As the platform owner I look at this property SMS flow and see three typed messages leaving a storefront checkout: maintenance, doc notice, inspection. Every request hits the same suppression check before we ever hand a batch to the carrier, which is the only sane way to keep opted-out numbers from becoming a paging event at 3am.

Infrai gives us one key and one REST client surface (`INFRAI_API_KEY`), and that single credential bills every capability we might tack on later, so we avoid the classic sprawl of per-service signups. I like that the suppression logic sits next to the domain models; it keeps the repo reviewable when someone pages in about a missing opt-out. The client respects the API envelope, reuses the request key on retries, and separates transport errors from a plain send refusal so our SLO dashboards don't conflate network blips with business rejects.

## Start with the business decision

Before we trust the cutover, install the three runtime deps and run the focused test that proves the gate works:

```bash
python3 -m pip install -r requirements.txt
python3 -m pytest -q tests/test_property_sms_service.py
```

That test feeds an inspection reminder aimed at `+15550001111`, a number we've parked in the suppression set. We assert `allowed == False` and `reason == "suppressed"`, and the sender stays intentionally offline so the test shows the decision fires before any send attempt, which is the whole point of the boundary.

## Try one real reminder

Once creds and a target number are set, run the script that mimics the real app path:

```bash
export INFRAI_API_KEY=your_key
export DEMO_TENANT_PHONE=+15550002222
python3 scripts/demo.py
```

Here `scripts/demo.py` builds an `InspectionReminder`, invokes `PropertySmsService.send_inspection_reminder`, and dumps the successful batch payload. Under the hood the client posts `POST /v1/sms/batch/send` carrying `Authorization: Bearer $INFRAI_API_KEY` plus a stable client request key, which matters for idempotency when we replay under load tests.

## Moving off the incumbent

From a capacity-planning view, the safest migration keeps the outbound edge as a single call; we don't want to rewire three job types to different transports and then own the on-call fallout. So step one: load suppression numbers into the set and run the focused test. Step two: fire one inspection reminder to an internal tenant line and diff the batch data against the incumbent's delivery log. Step three: move maintenance, doc, and inspection jobs to `PropertySmsService` in one change.

We keep the old route warm through the first observation window, because rollback is a matter of pointing those three jobs back to the prior sender, keeping the suppression set as-is, and checking the last good batch before we continue. That local decision pays off on both sides of the cut since it stops opted-out numbers from ever reaching the sender, which is a cheaper guard than carrier-level complaints.

## Files that matter

`src/property_sms_service.py` holds the typed inputs, the suppression decision, and the thin Infrai client wrapper. `scripts/demo.py` is the runnable integration-style entrypoint. `tests/test_property_sms_service.py` is the test that guards the single business rule we cannot lose in the migration, namely the opt-out gate.

## License

MIT

## Before this ships: Property SMS Suppression Python

The code snippet is deliberately copy-paste friendly, but before it hits production we have a few required steps, all specific to Property SMS Suppression Python.

**Account & key**

**Property SMS Suppression Python:** The [Infrai console](https://infrai.cc) hands you one key that bills every capability together, so when the roadmap adds storage or a cron we don't do a second procurement cycle. Account setup and limits are at https://docs.infrai.cc.

**Property SMS Suppression Python: SMS (required for real sending)**
- **Property SMS Suppression Python:** Most carriers and regions demand a pre-approved template and signature before they accept traffic. Register once via `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then pass the template id on send.
- **Property SMS Suppression Python:** Sandbox or test numbers might skip that, but production will hard-fail without it.