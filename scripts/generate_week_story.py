from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from random import Random


@dataclass(frozen=True)
class Theme:
    slug: str
    templates: tuple[str, ...]


THEMES: tuple[Theme, ...] = (
    Theme(
        "auth-login",
        (
            "{tenant} users in {region} see login failures on {service}",
            "Sign-in attempts keep failing for {tenant} on {service} in {region}",
            "{service} is throwing {code} during login for {tenant}",
            "Authentication failures are rising in {region} for {tenant} accounts",
            "{tenant} cannot sign in because {service} returns {code}",
            "Login error volume spiked again for {tenant} on {service}",
            "Support reports repeated auth failures in {region} for {tenant}",
            "{service} login flow is broken for {tenant} with {code}",
        ),
    ),
    Theme(
        "checkout-payments",
        (
            "{gateway} payments time out during checkout for {tenant}",
            "Checkout with {gateway} keeps failing in {region} for {tenant}",
            "Card payment requests hit {code} at the {gateway} edge",
            "{tenant} shoppers cannot complete checkout on {gateway}",
            "{gateway} payment authorization is stalling in {region}",
            "Checkout retries are climbing for {tenant} because {gateway} is timing out",
            "{code} responses are coming back from {gateway} in checkout",
            "{tenant} checkout still fails when payment goes through {gateway}",
        ),
    ),
    Theme(
        "password-reset",
        (
            "Password reset links are failing for {tenant} users",
            "{tenant} reset emails open to an error page in {region}",
            "Recovery flow returns {code} for {tenant} password resets",
            "{tenant} users cannot finish password recovery",
            "Reset token validation is broken for {tenant} in {region}",
            "Password recovery is failing again for {tenant}",
            "{code} is blocking reset-link opens for {tenant}",
            "{tenant} support queue is filling with reset-link failures",
        ),
    ),
    Theme(
        "dashboard-ui",
        (
            "{dashboard} charts render blank for {tenant}",
            "{tenant} sees broken {dashboard} widgets in {region}",
            "Dashboard paint time jumped and {dashboard} loads incomplete",
            "{dashboard} visuals are missing labels for {tenant}",
            "{tenant} reports the {dashboard} page is visually broken",
            "Front-end logs show {code} while rendering {dashboard}",
            "{dashboard} keeps loading without data traces for {tenant}",
            "{tenant} still sees the {dashboard} UI glitch in {region}",
        ),
    ),
    Theme(
        "search-latency",
        (
            "Catalog search latency is spiking for {tenant} in {region}",
            "{tenant} product search takes too long on {service}",
            "{service} search queries are returning after {duration}",
            "Search timeouts are rising for {tenant} shoppers",
            "{region} users report very slow catalog search",
            "{service} search path is breaching latency SLOs for {tenant}",
            "{tenant} search results are delayed by {duration}",
            "Catalog search remains sluggish in {region} for {tenant}",
        ),
    ),
    Theme(
        "order-webhook",
        (
            "{partner} order webhooks are delayed for {tenant}",
            "{tenant} fulfillment updates arrive late from {partner}",
            "Order status callbacks from {partner} are stuck in {queue}",
            "{partner} webhook backlog is growing for {tenant}",
            "{tenant} order-state sync is lagging behind because of {partner}",
            "Delayed callbacks from {partner} are blocking order updates",
            "{queue} is filling with pending {partner} webhook deliveries",
            "{tenant} still has stale order status from {partner}",
        ),
    ),
    Theme(
        "invoice-export",
        (
            "Invoice export PDF generation is failing for {tenant}",
            "{tenant} cannot download invoices in {locale}",
            "Invoice export returns {code} for {tenant} finance users",
            "PDF export of invoices is broken in {region} for {tenant}",
            "{tenant} invoice downloads are empty again",
            "Invoice rendering pipeline is timing out for {tenant}",
            "{locale} invoice export is malformed for {tenant}",
            "{tenant} support tickets mention broken invoice PDFs",
        ),
    ),
    Theme(
        "mobile-crash",
        (
            "Android app version {app_version} crashes for {tenant} users",
            "{tenant} reports a mobile crash on startup in {region}",
            "Crash logs show {code} in app version {app_version}",
            "Mobile session drops immediately after launch for {tenant}",
            "{tenant} users on Android cannot open the app without crashing",
            "App version {app_version} is unstable in {region}",
            "{code} appears in mobile crash traces for {tenant}",
            "{tenant} still sees startup crashes in version {app_version}",
        ),
    ),
    Theme(
        "email-delivery",
        (
            "{provider} is delaying transactional email for {tenant}",
            "{tenant} password emails are not landing through {provider}",
            "Email delivery to {region} is bouncing with {code}",
            "{provider} bounce rate is rising for {tenant}",
            "{tenant} cannot receive account emails in {region}",
            "{provider} queue age is growing for {tenant} email",
            "{code} responses are coming back from {provider}",
            "Transactional mail remains delayed for {tenant}",
        ),
    ),
    Theme(
        "inventory-sync",
        (
            "Inventory sync is stale for {tenant} warehouse {warehouse}",
            "{warehouse} stock updates are not reaching {tenant} storefronts",
            "Inventory worker returns {code} for {tenant} in {region}",
            "{tenant} still sees incorrect stock levels from {warehouse}",
            "Warehouse sync backlog is growing for {tenant}",
            "{warehouse} inventory snapshots are delayed in {region}",
            "{tenant} reports stale inventory after recent updates",
            "Inventory replication from {warehouse} is broken for {tenant}",
        ),
    ),
    Theme(
        "reports-api",
        (
            "{service} returns {code} for scheduled reports",
            "{tenant} cannot load reports because {service} is failing",
            "Report-generation API is erroring in {region} for {tenant}",
            "{service} report exports are unavailable for {tenant}",
            "{tenant} sees report download failures with {code}",
            "Scheduled analytics jobs break when {service} responds {code}",
            "{region} report requests are failing for {tenant}",
            "{service} is still blocking report access for {tenant}",
        ),
    ),
    Theme(
        "file-upload",
        (
            "File uploads are stuck in malware scanning for {tenant}",
            "{tenant} uploads wait forever in {queue}",
            "Upload-processing service returns {code} in {region}",
            "{tenant} cannot finish document upload because scanning is blocked",
            "{queue} has a growing backlog of upload jobs for {tenant}",
            "Upload confirmations are delayed for {tenant} in {region}",
            "{tenant} support reports broken file upload flow",
            "Document uploads remain stuck behind scanning for {tenant}",
        ),
    ),
)

TENANTS = ("northwind", "contoso", "fabrikam", "globex", "initech", "umbrella")
REGIONS = ("ap-south-1", "eu-west-1", "us-east-1", "sa-east-1")
SERVICES = ("auth-service", "checkout-gateway", "reports-api", "search-api", "sync-worker")
GATEWAYS = ("stripe", "adyen", "braintree", "razorpay")
PROVIDERS = ("ses", "sendgrid", "mailgun")
PARTNERS = ("shopify", "netsuite", "shipstation", "salesforce")
QUEUES = ("retry-queue", "dead-letter-retry", "webhook-outbox", "scan-jobs")
WAREHOUSES = ("blr-01", "hyd-02", "mum-03", "fra-04")
DASHBOARDS = ("sales-dashboard", "inventory-dashboard", "ops-dashboard", "risk-dashboard")
LOCALES = ("en-IN", "en-GB", "de-DE", "fr-FR")
DURATIONS = ("2.8s", "3.1s", "4.7s", "6.4s")
APP_VERSIONS = ("4.12.0", "4.12.1", "4.13.0", "5.0.0")
CODES = ("401", "429", "500", "502", "503", "504")
SOURCES = ("support", "query", "log", "ticket", "pager")


def build_story() -> tuple[list[dict[str, object]], dict[str, str]]:
    rng = Random(42)
    story: list[dict[str, object]] = []
    labels: dict[str, str] = {}
    start = datetime(2026, 4, 13, 0, 0, tzinfo=timezone.utc)
    incidents = 125
    events_per_incident = 8
    spacing_minutes = (7 * 24 * 60) / incidents
    event_offsets = (0, 3, 7, 12, 20, 33, 55, 89)

    event_counter = 1
    for incident_idx in range(incidents):
        theme = THEMES[incident_idx % len(THEMES)]
        incident_label = f"{theme.slug}-incident-{incident_idx + 1:03d}"
        anchor = start + timedelta(minutes=round(incident_idx * spacing_minutes))
        payload = {
            "tenant": TENANTS[(incident_idx + 1) % len(TENANTS)],
            "region": REGIONS[(incident_idx + 2) % len(REGIONS)],
            "service": SERVICES[(incident_idx + 3) % len(SERVICES)],
            "gateway": GATEWAYS[(incident_idx + 4) % len(GATEWAYS)],
            "provider": PROVIDERS[(incident_idx + 5) % len(PROVIDERS)],
            "partner": PARTNERS[(incident_idx + 6) % len(PARTNERS)],
            "queue": QUEUES[(incident_idx + 7) % len(QUEUES)],
            "warehouse": WAREHOUSES[(incident_idx + 1) % len(WAREHOUSES)],
            "dashboard": DASHBOARDS[(incident_idx + 2) % len(DASHBOARDS)],
            "locale": LOCALES[(incident_idx + 3) % len(LOCALES)],
            "duration": DURATIONS[(incident_idx + 4) % len(DURATIONS)],
            "app_version": APP_VERSIONS[(incident_idx + 5) % len(APP_VERSIONS)],
            "code": CODES[(incident_idx + 6) % len(CODES)],
        }
        template_indexes = list(range(len(theme.templates)))
        rng.shuffle(template_indexes)
        for position, minutes_after in enumerate(event_offsets):
            event_id = f"wk-{event_counter:04d}"
            event_counter += 1
            template = theme.templates[template_indexes[position % len(template_indexes)]]
            text = template.format(**payload)
            occurred_at = anchor + timedelta(minutes=minutes_after)
            source = SOURCES[(incident_idx + position) % len(SOURCES)]
            event = {
                "event_id": event_id,
                "source": source,
                "occurred_at": occurred_at.isoformat().replace("+00:00", "Z"),
                "text": text,
                "metadata": {
                    "expected_cluster": incident_label,
                    "theme": theme.slug,
                    "week_story": True,
                },
            }
            story.append(event)
            labels[event_id] = incident_label
    return story, labels


def main() -> None:
    story, labels = build_story()
    data_dir = Path(__file__).resolve().parents[1] / "data"
    story_path = data_dir / "week_story_1000.jsonl"
    labels_path = data_dir / "week_story_1000.labels.json"
    with story_path.open("w", encoding="utf-8") as handle:
        for item in story:
            handle.write(json.dumps(item, separators=(",", ":")) + "\n")
    labels_path.write_text(
        json.dumps({"story_id": "week-story-1000-v1", "labels": labels}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(story)} events to {story_path}")
    print(f"Wrote labels to {labels_path}")


if __name__ == "__main__":
    main()
