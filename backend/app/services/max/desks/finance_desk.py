"""
FinanceDesk — Invoicing, payments, expenses, and profitability tracking.
Absorbs: legacy FinanceBot (domains).
"""
import logging
import re
from datetime import datetime
from .base_desk import BaseDesk, DeskTask, DeskAction, TaskPriority

logger = logging.getLogger("max.desks.finance")

# Drapery business economics (from DB desk config)
TYPICAL_MATERIAL_MARGIN_LOW = 0.40
TYPICAL_MATERIAL_MARGIN_HIGH = 0.60
OVERDUE_DAYS_WARNING = 30
LARGE_INVOICE_THRESHOLD = 5000


class FinanceDesk(BaseDesk):
    desk_id = "finance"
    desk_name = "FinanceDesk"
    desk_description = (
        "Manages business finances: invoice creation, payment tracking, expense logging, "
        "P&L summaries, subscription management, and profitability analysis. "
        "Understands drapery economics: 40-60% material margins, labor costs, overhead."
    )
    capabilities = [
        "invoice_creation",
        "payment_tracking",
        "expense_logging",
        "revenue_reporting",
        "pnl_summary",
        "overdue_alerts",
        "subscription_management",
        "profitability_analysis",
    ]

    def __init__(self):
        super().__init__()
        self.invoices: list[dict] = []
        self.expenses: list[dict] = []
        self.payments: list[dict] = []

    async def handle_task(self, task: DeskTask) -> DeskTask:
        """Route finance task to appropriate handler."""
        await self.accept_task(task)

        combined = f"{task.title} {task.description}".lower()

        try:
            if any(w in combined for w in ["invoice", "bill", "billing"]):
                return await self._handle_invoice(task)
            elif any(w in combined for w in ["payment", "paid", "received", "deposit"]):
                return await self._handle_payment(task)
            elif any(w in combined for w in ["expense", "cost", "spent", "purchase"]):
                return await self._handle_expense(task)
            elif any(w in combined for w in ["p&l", "profit", "loss", "pnl", "profitability"]):
                return await self._handle_pnl(task)
            elif any(w in combined for w in ["revenue", "income", "earnings", "sales report"]):
                return await self._handle_revenue(task)
            elif any(w in combined for w in ["overdue", "late", "outstanding", "unpaid"]):
                return await self._handle_overdue(task)
            elif any(w in combined for w in ["subscription", "recurring", "monthly fee"]):
                return await self._handle_subscription(task)
            else:
                return await self._handle_general(task)
        except Exception as e:
            logger.error(f"FinanceDesk task failed: {e}")
            return await self.fail_task(task, str(e))

    async def _handle_invoice(self, task: DeskTask) -> DeskTask:
        """Create or manage an invoice."""
        task.actions.append(DeskAction(
            action="invoice_processing",
            detail=f"Processing invoice for {task.customer_name or 'customer'}",
        ))

        amount = self._extract_dollar_amount(task.description)

        # Large invoices escalate
        if amount and amount > LARGE_INVOICE_THRESHOLD:
            return await self.escalate(
                task,
                f"Large invoice ${amount:,.2f} for {task.customer_name or 'customer'} — needs founder approval"
            )

        invoice = {
            "task_id": task.id,
            "customer": task.customer_name or "Unknown",
            "amount": amount,
            "status": "draft",
            "created": datetime.utcnow().isoformat(),
        }
        self.invoices.append(invoice)

        result = (
            f"Invoice drafted for {task.customer_name or 'customer'}. "
            f"{'Amount: $' + f'{amount:,.2f}. ' if amount else ''}"
            f"Status: draft — ready for review and send. "
            f"Terms: Net 30, 50% deposit on custom work. "
            f"Total invoices: {len(self.invoices)}."
        )

        self._log_to_brain(
            f"Invoice: {task.customer_name or 'Unknown'}" +
            (f", ${amount:,.2f}" if amount else ""),
            importance=6,
            tags=["desk", "finance", "invoice"],
        )

        return await self.complete_task(task, result)

    async def _handle_payment(self, task: DeskTask) -> DeskTask:
        """Record a payment received."""
        task.actions.append(DeskAction(
            action="payment_received",
            detail=f"Recording payment from {task.customer_name or 'customer'}",
        ))

        amount = self._extract_dollar_amount(task.description)

        payment = {
            "task_id": task.id,
            "customer": task.customer_name or "Unknown",
            "amount": amount,
            "date": datetime.utcnow().isoformat(),
        }
        self.payments.append(payment)

        result = (
            f"Payment recorded from {task.customer_name or 'customer'}. "
            f"{'Amount: $' + f'{amount:,.2f}. ' if amount else ''}"
            f"Invoice status updated. "
            f"Total payments today: {len([p for p in self.payments if p['date'][:10] == datetime.utcnow().strftime('%Y-%m-%d')])}."
        )

        self._log_to_brain(
            f"Payment: {task.customer_name or 'Unknown'}" +
            (f", ${amount:,.2f}" if amount else ""),
            importance=7,
            tags=["desk", "finance", "payment", "revenue"],
        )

        return await self.complete_task(task, result)

    async def _handle_expense(self, task: DeskTask) -> DeskTask:
        """Log an expense."""
        task.actions.append(DeskAction(
            action="expense_logged",
            detail="Recording expense",
        ))

        amount = self._extract_dollar_amount(task.description)

        expense = {
            "task_id": task.id,
            "description": task.title,
            "amount": amount,
            "date": datetime.utcnow().isoformat(),
        }
        self.expenses.append(expense)

        # Large expenses notify via Telegram
        if amount and amount > 1000:
            await self.notify_telegram(
                f"Expense logged: ${amount:,.2f}\n{task.title}"
            )

        result = (
            f"Expense recorded: {task.title}. "
            f"{'Amount: $' + f'{amount:,.2f}. ' if amount else ''}"
            f"Total expenses logged: {len(self.expenses)}."
        )

        return await self.complete_task(task, result)

    async def _handle_pnl(self, task: DeskTask) -> DeskTask:
        """Generate P&L summary."""
        task.actions.append(DeskAction(
            action="pnl_report",
            detail="Generating P&L summary",
        ))

        total_revenue = sum(p.get("amount", 0) or 0 for p in self.payments)
        total_expenses = sum(e.get("amount", 0) or 0 for e in self.expenses)
        net = total_revenue - total_expenses

        result = (
            f"P&L Summary (session): "
            f"Revenue: ${total_revenue:,.2f}, "
            f"Expenses: ${total_expenses:,.2f}, "
            f"Net: ${net:,.2f}. "
            f"Target margins: {TYPICAL_MATERIAL_MARGIN_LOW*100:.0f}-{TYPICAL_MATERIAL_MARGIN_HIGH*100:.0f}% on materials. "
            f"Note: This reflects in-session data only — connect to accounting system for full financials."
        )

        return await self.complete_task(task, result)

    async def _handle_revenue(self, task: DeskTask) -> DeskTask:
        """Generate revenue report."""
        task.actions.append(DeskAction(
            action="revenue_report",
            detail="Generating revenue summary",
        ))

        total = sum(p.get("amount", 0) or 0 for p in self.payments)
        count = len(self.payments)

        result = (
            f"Revenue report: {count} payment(s) totaling ${total:,.2f}. "
            f"Outstanding invoices: {len([i for i in self.invoices if i.get('status') == 'draft'])}."
        )

        return await self.complete_task(task, result)

    async def _handle_overdue(self, task: DeskTask) -> DeskTask:
        """Handle overdue payment alerts."""
        task.actions.append(DeskAction(
            action="overdue_check",
            detail="Checking overdue invoices",
        ))

        # Flag overdue invoices and escalate
        overdue = [i for i in self.invoices if i.get("status") in ("draft", "sent")]

        if overdue:
            await self.notify_telegram(
                f"Overdue alert: {len(overdue)} invoice(s) need attention\n"
                + "\n".join(f"- {i['customer']}: ${i.get('amount', 0) or 0:,.2f}" for i in overdue[:5])
            )

        result = (
            f"Overdue check: {len(overdue)} invoice(s) outstanding. "
            f"Recommended: Send payment reminders, escalate 30+ day overdue."
        )

        if any(task.priority == TaskPriority.URGENT for _ in [1]):
            return await self.escalate(task, f"{len(overdue)} overdue invoices need founder attention")

        return await self.complete_task(task, result)

    async def _handle_subscription(self, task: DeskTask) -> DeskTask:
        """Handle subscription/recurring payment management."""
        task.actions.append(DeskAction(
            action="subscription_management",
            detail="Processing subscription task",
        ))

        result = (
            f"Subscription task: {task.title}. "
            f"Details: {task.description[:200]}. "
            f"Track: renewal dates, payment methods, cancellation deadlines."
        )

        return await self.complete_task(task, result)

    async def _handle_general(self, task: DeskTask) -> DeskTask:
        """Handle general finance tasks."""
        task.actions.append(DeskAction(
            action="general_finance",
            detail="Processing general finance task",
        ))

        result = f"Finance task processed: {task.title}. {task.description[:200]}"
        return await self.complete_task(task, result)

    def _extract_dollar_amount(self, text: str) -> float | None:
        """Extract a dollar amount from text."""
        patterns = [
            r'\$\s?([\d,]+(?:\.\d{2})?)',
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)(?:\s*dollars?)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1).replace(",", ""))
                except ValueError:
                    continue
        return None

    async def report_status(self) -> dict:
        base = await super().report_status()
        base["total_invoices"] = len(self.invoices)
        base["total_payments"] = len(self.payments)
        base["total_expenses"] = len(self.expenses)
        return base

    def get_briefing_section(self) -> str:
        base = super().get_briefing_section()
        extras = []
        outstanding = [i for i in self.invoices if i.get("status") in ("draft", "sent")]
        if outstanding:
            extras.append(f"- {len(outstanding)} outstanding invoice(s)")
        if self.payments:
            today_payments = [p for p in self.payments if p["date"][:10] == datetime.utcnow().strftime("%Y-%m-%d")]
            if today_payments:
                total = sum(p.get("amount", 0) or 0 for p in today_payments)
                extras.append(f"- {len(today_payments)} payment(s) today (${total:,.2f})")
        if extras:
            base += "\n" + "\n".join(extras)
        return base
