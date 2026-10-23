"""Max-e chat tools: companies + WhatsApp guide. Amp only at call time."""
from __future__ import annotations

def _args(params: dict) -> dict:
    data = dict(params or {})
    inner = data.get("params")
    if isinstance(inner, dict):
        data.update(inner)
    return data


MAXE_GUIDES_DOC = """
Empresas de Juan (Max-e):
- **list_companies** — Lee las empresas de EMPIRE_DATA_DIR/businesses.
- **save_company** — Crea o actualiza una empresa. Primera llamada SIN confirm (preview).
  Solo con confirm=true después de que Juan diga que sí. Una pregunta a la vez.
- **company_setup_guide** — Siguiente pregunta de la entrevista fácil.
- **whatsapp_setup_guide** — Guía de Meta / WhatsApp de Juan. NUNCA pidas tokens en el chat.
  Las llaves van a /amp/whatsapp. El número de Juan no avisa a Rafael.
"""


def register_tools(tool, ToolResult):
    @tool("list_companies")
    def list_companies(params: dict, desk=None):
        """List Juan's companies from this instance data dir."""
        try:
            from app.edition import is_amp
            from app.services.amp_businesses import company_choices, companies_prompt_block

            if not is_amp():
                return ToolResult(tool="list_companies", success=False, error="Solo en Max-e")
            rows = company_choices()
            return ToolResult(
                tool="list_companies",
                success=True,
                result={
                    "companies": rows,
                    "context": companies_prompt_block(),
                    "count": len(rows),
                },
            )
        except Exception as exc:
            return ToolResult(tool="list_companies", success=False, error=str(exc)[:300])

    @tool("save_company")
    def save_company(params: dict, desk=None):
        """Create/update a company. Requires confirm=true after Juan says yes."""
        try:
            from app.edition import is_amp
            from app.services.amp_businesses import update_business

            if not is_amp():
                return ToolResult(tool="save_company", success=False, error="Solo en Max-e")
            args = _args(params)
            slug = str(args.get("slug") or args.get("name") or "").strip()
            confirm = str(args.get("confirm") or "").lower() in {"1", "true", "yes", "si", "sí"}
            fields = {
                key: args.get(key)
                for key in (
                    "name",
                    "industry",
                    "description",
                    "also_known_as",
                    "legal_name",
                    "trade_name",
                    "country",
                    "city",
                    "contact_email",
                    "contact_phone",
                    "website",
                    "currency",
                )
                if params.get(key) not in (None, "")
            }
            result = update_business(slug, fields=fields, confirm=confirm)
            return ToolResult(tool="save_company", success=True, result=result)
        except Exception as exc:
            return ToolResult(tool="save_company", success=False, error=str(exc)[:300])

    @tool("company_setup_guide")
    def company_setup_guide(params: dict, desk=None):
        """Next easy company question. One at a time."""
        try:
            from app.edition import is_amp
            from app.services.maxe_guides import company_guide_next

            if not is_amp():
                return ToolResult(tool="company_setup_guide", success=False, error="Solo en Max-e")
            args = _args(params)
            answers = args.get("answers") if isinstance(args.get("answers"), dict) else args
            return ToolResult(
                tool="company_setup_guide",
                success=True,
                result=company_guide_next(answers),
            )
        except Exception as exc:
            return ToolResult(tool="company_setup_guide", success=False, error=str(exc)[:300])

    @tool("whatsapp_setup_guide")
    def whatsapp_setup_guide(params: dict, desk=None):
        """Walk the owner through their own Meta/WhatsApp. Never collect secrets."""
        try:
            from app.edition import is_family_edition
            from app.services.maxe_guides import looks_like_secret, run_whatsapp_setup_guide, secret_refusal, whatsapp_setup_path

            if not is_family_edition():
                return ToolResult(tool="whatsapp_setup_guide", success=False, error="Solo en ediciones familiares")
            args = _args(params)
            spoken = str(args.get("text") or args.get("answer") or "")
            if looks_like_secret(spoken):
                return ToolResult(
                    tool="whatsapp_setup_guide",
                    success=True,
                    result={"refused": True, "message": secret_refusal(), "setup_path": whatsapp_setup_path()},
                )
            step = str(args.get("step") or "")
            guide = run_whatsapp_setup_guide(step, persist=True)
            return ToolResult(tool="whatsapp_setup_guide", success=True, result=guide)
        except Exception as exc:
            return ToolResult(tool="whatsapp_setup_guide", success=False, error=str(exc)[:300])
