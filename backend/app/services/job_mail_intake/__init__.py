"""Read-only job-mail intake.

Reads connected inboxes Max already has (business Gmail, personal Gmail
read-only when opted in, Outlook only when JOB_MAIL_OUTLOOK_INBOX=1).
Matches each message to a job or client, writes a timeline note, proposes
calendar changes for founder approval, and parks unmatched mail in a review
queue. System and internal mail is ignored.

This package never sends email or WhatsApp and never writes live calendar
or supplier checkouts. Tests inject messages via TEST_INBOX.
"""

from app.services.job_mail_intake.service import (
    OUTBOUND_POLICY,
    TEST_INBOX,
    approve_calendar_proposal,
    intake_status,
    list_calendar_proposals,
    list_review_queue,
    list_supplier_events,
    list_timeline_notes,
    run_intake,
)

__all__ = [
    "OUTBOUND_POLICY",
    "TEST_INBOX",
    "approve_calendar_proposal",
    "intake_status",
    "list_calendar_proposals",
    "list_review_queue",
    "list_supplier_events",
    "list_timeline_notes",
    "run_intake",
]
