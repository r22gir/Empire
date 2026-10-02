"""COP payment schedules. Installments are whole pesos and sum to the balance."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


def cop_round(value) -> int:
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def format_cop(amount: int) -> str:
    return f"${int(amount):,}".replace(",", ".")


def split_installments(balance: int, count: int) -> list[int]:
    """Whole pesos. The first remainder pesos go to the earliest installments."""
    total = int(balance)
    count = int(count)
    if count < 1:
        raise ValueError("El número de cuotas tiene que ser al menos 1")
    if total < 0:
        raise ValueError("El saldo no puede ser negativo")
    base = total // count
    remainder = total - (base * count)
    amounts = [base + (1 if index < remainder else 0) for index in range(count)]
    if sum(amounts) != total:
        raise RuntimeError("La suma de las cuotas no cierra con el saldo")
    return amounts


def build_schedule(
    *,
    price: int,
    separacion: int = 0,
    cuota_inicial_pct: float | None = None,
    cuota_inicial: int | None = None,
    installments: int = 1,
    balloon: int = 0,
    plan_id: str = "plan_a",
    label: str = "Plan A",
) -> dict:
    """Separación is part of the cuota inicial, not an extra charge on top."""
    price = cop_round(price)
    separacion = cop_round(separacion or 0)
    balloon = cop_round(balloon or 0)
    if price <= 0:
        raise ValueError("Indica el precio en COP. No invento precios.")
    if cuota_inicial is None:
        if cuota_inicial_pct is None:
            cuota = separacion
            cuota_inicial_pct = 0
        else:
            cuota = cop_round(Decimal(price) * Decimal(str(cuota_inicial_pct)) / Decimal(100))
    else:
        cuota = cop_round(cuota_inicial)
    if separacion > cuota:
        cuota = separacion
    if separacion < 0 or balloon < 0 or cuota < 0:
        raise ValueError("Los valores del plan no pueden ser negativos")
    if cuota + balloon > price:
        raise ValueError("La cuota inicial más el pago final superan el precio")
    balance = price - cuota - balloon
    amounts = split_installments(balance, installments)
    rows = [
        {"installment_number": index + 1, "amount": amount, "kind": "cuota"}
        for index, amount in enumerate(amounts)
    ]
    return {
        "id": plan_id,
        "label": label,
        "currency": "COP",
        "price": price,
        "separacion": separacion,
        "cuota_inicial": cuota,
        "cuota_inicial_pct": cuota_inicial_pct,
        "cuota_inicial_restante": cuota - separacion,
        "balloon": balloon,
        "balance": balance,
        "installments": rows,
        "installment_count": len(rows),
    }


def plan_summary(plan: dict) -> str:
    parts = [
        f"{plan['label']}: cuota inicial {format_cop(plan['cuota_inicial'])}",
    ]
    if plan.get("separacion"):
        parts.append(f"separación {format_cop(plan['separacion'])}")
    parts.append(f"{plan['installment_count']} cuotas sobre {format_cop(plan['balance'])}")
    if plan.get("balloon"):
        parts.append(f"cuota final contra crédito o subsidio {format_cop(plan['balloon'])}")
    return ", ".join(parts)


def payment_plan_options(
    *,
    price: int,
    separacion: int = 0,
    cuota_inicial_pct: float | None = 30,
    installments: int | None = None,
    balloon: int = 0,
) -> list[dict]:
    """Two or three calculated plans. Amounts come only from the given price."""
    pct = 30 if cuota_inicial_pct is None else float(cuota_inicial_pct)
    months = int(installments or 24)
    months = max(1, months)
    plan_a = build_schedule(
        price=price,
        separacion=separacion,
        cuota_inicial_pct=pct,
        installments=months,
        balloon=balloon,
        plan_id="plan_a",
        label="Plan A",
    )
    plan_b = build_schedule(
        price=price,
        separacion=separacion,
        cuota_inicial_pct=min(80, pct + 10),
        installments=months,
        balloon=balloon,
        plan_id="plan_b",
        label="Plan B",
    )
    cuota = plan_a["cuota_inicial"]
    remaining = price_int(price) - cuota
    final = remaining // 2
    plan_c = build_schedule(
        price=price,
        separacion=separacion,
        cuota_inicial=cuota,
        cuota_inicial_pct=pct,
        installments=months,
        balloon=final,
        plan_id="plan_c",
        label="Plan C",
    )
    plans = [plan_a, plan_b, plan_c]
    for plan in plans:
        paid = plan["cuota_inicial"] + plan["balloon"] + sum(row["amount"] for row in plan["installments"])
        if paid != plan["price"]:
            raise RuntimeError("El plan no suma el precio")
        if sum(row["amount"] for row in plan["installments"]) != plan["balance"]:
            raise RuntimeError("Las cuotas no suman el saldo")
        plan["summary"] = plan_summary(plan)
    return plans


def price_int(price) -> int:
    return cop_round(price)
