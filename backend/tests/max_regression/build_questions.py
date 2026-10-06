"""Generates questions.json (kept so the fixture is easy to edit). Run: python build_questions.py"""
import json
from pathlib import Path

WEB = ["web_search", "web_read"]
NOSEND = ["send_email", "send_quote_email", "share_file"]
QLOOK = ["get_quote", "search_quotes", "show_quote_for_review", "open_final_doc", "find_files", "shortcut:quote_lookup"]
DAHLIA_HIST = [
    {"role": "user", "content": "What's the most recent quote we were working on?"},
    {"role": "assistant", "content": "EST-2026-297 for Dahlia Design (Nehal Elrefai, Phase 1 living room and office), $3,411.84, draft. Phase 2 is EST-2026-298, $9,350.76, draft."},
]
BASSETT_HIST = [
    {"role": "user", "content": "Okay, so can you look up any documents we have for Lauren Bassett on a well unit?"},
    {"role": "assistant", "content": "I found Lauren Bassett quotes (EST-2026-291, EST-2026-262) but nothing named 'well unit'. Did you mean something else?"},
]

Q = []
def q(id, kind, channel, message, source, expect, history=None):
    item = {"id": id, "kind": kind, "channel": channel, "message": message, "source": source, "expect": expect}
    if history:
        item["history"] = history
    Q.append(item)

# quote lookups by number
q("q01", "quote_number", "studio", "What's the status of EST-2026-297?", "variant",
  {"tools_any": QLOOK, "tools_none": WEB, "must_any": [["EST-2026-297"], ["draft"], ["3,411\\.84", "4,759\\.96"]], "max_words": 70})
q("q02", "quote_number", "studio", "EST-2026-298 total?", "variant",
  {"tools_any": QLOOK, "tools_none": WEB, "must_any": [["9,350\\.76"]], "max_words": 60})
q("q03", "quote_number", "whatsapp", "send me EST-2026-295 here", "variant (WhatsApp 'send me a pdf here' 2026-10-04)",
  {"tools_none": WEB, "must_any": [["EST-2026-295"]], "must_not": ["can't send", "cannot send"], "max_words": 70})
q("q04", "quote_number", "studio", "Is EST-2026-284 sent?", "variant",
  {"tools_any": QLOOK, "tools_none": WEB, "must_any": [["sent"], ["Maura", "Lindsey", "395"]], "max_words": 60})
q("q05", "quote_number", "studio", "pull up EST-2026-083", "variant",
  {"tools_any": QLOOK, "tools_none": WEB, "must_any": [["EST-2026-083"], ["Naomi", "Phillip", "Philipp"]], "max_words": 80})

# quote lookups by client / alias
q("q06", "quote_client", "studio", "What's the latest quote for Dahlia?", "2026-10-04 voice 17:01",
  {"tools_any": QLOOK, "tools_none": WEB, "must_any": [["EST-2026-298"]], "must_not": ["2,430", "twenty-five line items"], "max_words": 80})
q("q07", "quote_client", "studio", "Can you send me like a voice message, like a status on the last Marley's quote?", "2026-10-04 voice-doc 20:03",
  {"tools_any": QLOOK, "tools_none": WEB, "must_any": [["EST-2026-29[45]", "EST-2026-27[2-5]", "INV-2026-123"]],
   "must_not": ["Missing:", "Client name", "What to make"], "max_words": 90})
q("q08", "quote_client", "whatsapp", "Send me last quote", "2026-10-04 voice-doc 20:05",
  {"tools_none": WEB, "must_any": [["EST-2026-29[78]", "which"]], "must_not": ["Missing:", "What to make"], "max_words": 80})
q("q09", "quote_client", "studio", "Isn't there an accompanying quote, like a sister quote, basically like the phase two part?",
  "2026-10-05 voice 18:36", {"tools_none": WEB, "must_any": [["EST-2026-298"]], "max_words": 70}, history=DAHLIA_HIST[:1] + [
      {"role": "assistant", "content": "The most recent quote is EST-2026-297 for Dahlia Design, Phase 1 living room and office, $3,411.84, still in draft."}])
q("q10", "alias", "studio", "What do we have for Nehal?", "variant (Nehal = Dahlia alias)",
  {"tools_any": QLOOK + ["search_contacts"], "tools_none": WEB, "must_any": [["EST-2026-29[78]"]], "max_words": 110})
q("q11", "alias", "studio", "Show me Nehal's phase 1 quote", "variant",
  {"tools_any": QLOOK, "tools_none": WEB, "must_any": [["EST-2026-297"]], "must_not": ["couldn't find", "could not find"], "max_words": 80})
q("q12", "alias", "whatsapp", "What's the total on Dalia phase 2?", "variant (typo alias)",
  {"tools_none": WEB, "must_any": [["9,350\\.76"]], "max_words": 60})

# file finding / docs
q("q13", "file_find", "studio", "Okay, so can you look up any documents we have for Lauren Bassett on a well unit?", "2026-10-05 studio 20:58",
  {"tools_any": ["find_files", "search_quotes", "open_final_doc"], "tools_none": WEB,
   "must_any": [["wall unit", "Philipp", "Phillip", "Naomi", "R6"]], "must_not": ["window well", "wellhead", "egress"], "max_words": 120})
q("q14", "file_find", "studio", "There is no crock bot and its a wall unit not a well unit. And there are documents related to the led lighting system. I need those",
  "2026-10-05 studio 21:08", {"tools_any": ["find_files"], "tools_none": WEB + ["shell_execute"],
   "must_any": [["LED", "lighting"]], "must_not": ["needs your PIN", "Still no files found"], "max_words": 120}, history=BASSETT_HIST)
q("q15", "send_me", "whatsapp", "Send me led documents from Phillip and Naomi", "2026-10-05 WhatsApp 22:00",
  {"tools_none": WEB, "must_any": [["LED", "R6"]], "must_not": ["No LED documents found", "no LED spec"], "max_words": 90})
q("q16", "file_find", "studio", "Find the Willard addendum PDF", "variant",
  {"tools_any": ["find_files", "open_final_doc", "search_quotes"], "tools_none": WEB, "must_any": [["EST-2026-293", "838", "Willard"]], "max_words": 100})
q("q17", "file_find", "studio", "Where are the docs you have completed?", "2026-10-04 (quick_replies docstring)",
  {"tools_none": WEB, "must_any": [["Final Docs", "final-docs"]], "max_words": 120})
q("q54", "file_find", "studio", "Wall Unit for Philip and Naomi.", "2026-10-05 studio 20:59",
  {"tools_any": ["find_files", "search_quotes", "open_final_doc", "get_quote"], "tools_none": WEB,
   "must_any": [["Philipp", "Phillip", "Naomi"], ["INV-2026-119", "2,276\\.40", "R6", "LED", "EST-2026-083", "walnut"]], "max_words": 120},
  history=BASSETT_HIST)

# send me X / email to me
q("q18", "send_me", "studio", "Email me the Dahlia phase 2 quote", "variant",
  {"tools_any": ["send_quote_email", "send_email", "share_file"], "tools_none": WEB, "must_any": [["EST-2026-298", "phase 2", "Phase 2"]],
   "must_not": ["can't send", "cannot send", "need your PIN"], "max_words": 70})
q("q19", "send_me", "studio", "Can you send those two quotes to my email?", "2026-10-05 voice 18:37",
  {"tools_any": ["send_quote_email", "send_email", "share_file"], "tools_none": WEB, "must_any": [["297"], ["298"]],
   "must_not": ["can't send email", "cannot send email", "queued it"], "max_words": 70}, history=DAHLIA_HIST)
q("q20", "email_me", "studio", "can you send me a test e mail", "2026-10-05 studio 18:03",
  {"tools_any": ["send_email"], "tools_none": WEB, "must_any": [["sent", "Sent"]], "max_words": 40})
q("q21", "send_me", "whatsapp", "Send me a pdf here", "2026-10-04 WhatsApp 21:40",
  {"tools_none": WEB + NOSEND, "must_ask": True, "max_words": 50})

# status / what are you building
q("q22", "status", "studio", "What are you building now?", "2026-10-06 (Rafael's complaint)",
  {"tools_any": ["max_status", "shortcut:max_status"], "tools_none": WEB, "must_not": ["https?://", "leadership", "blog"], "max_words": 100})
q("q23", "status", "whatsapp", "what is empirebox next step with you", "2026-10-06 (Rafael's complaint)",
  {"tools_any": ["max_status", "shortcut:max_status"], "tools_none": WEB, "must_not": ["https?://", "roadmap"], "max_words": 100})
q("q24", "status", "studio", "Is Max operating normally?", "2026-10-05 studio 08:54",
  {"tools_none": WEB, "max_words": 50})
q("q25", "status", "studio", "Are you fixed now", "2026-10-05 studio 13:39",
  {"tools_none": WEB, "max_words": 70})
q("q26", "status", "studio", "What needs my approval?", "2026-10-05 studio 17:44",
  {"tools_any": ["list_quotes_awaiting_review", "get_tasks", "max_status", "shortcut:max_status"], "tools_none": WEB, "max_words": 90})
q("q27", "status", "whatsapp", "What's new", "2026-10-05 WhatsApp 21:59",
  {"tools_none": WEB, "must_not": ["https?://"], "max_words": 90})
q("q55", "status", "whatsapp", "Did you get my call", "2026-10-04 WhatsApp 21:34",
  {"tools_none": WEB, "max_words": 60})

# solar / Travelers
q("q28", "solar", "studio", "Research what's new in For this house on the traveles claim whatt is a good solar aystem. You have elec and give me the 3 things worth my time.",
  "2026-10-05 studio 18:02", {"research": True, "tools_none": ["shortcut:whats_new"], "must_any": [["solar"], ["Travelers", "claim", "Burns", "JJN4296"]],
   "must_not": ["9974207c", "commit", "Live backend"], "max_words": 260})
q("q29", "solar", "studio", "Research the latest on For this house on the traveles claim whatt is a good solar aystem. You have elec for me and summarize what matters.",
  "2026-10-04 studio 19:22", {"research": True, "must_any": [["solar"], ["Travelers", "claim", "Burns", "JJN4296"]], "max_words": 260})
q("q30", "solar", "studio", "For the Travelers claim house, what size solar system makes sense?", "variant",
  {"must_any": [["Travelers", "claim", "Burns", "JJN4296"], ["solar", "kW"]], "max_words": 160})

# explicit research / public facts
q("q31", "research", "studio", "So how much did that Pentagon monument for the 9/11 thing cost?", "2026-10-05 voice 19:52",
  {"tools_any": ["web_search"], "must_any": [["22 million", "\\$22"]], "max_words": 80})
q("q32", "research", "studio", "Research the best 24V COB LED strip options for a walnut wall unit and give me the top 3", "variant",
  {"research": True, "tools_any": ["web_search"], "must_any": [["COB"]], "max_words": 300})
q("q33", "research", "studio", "What's the weather in Hyattsville tomorrow?", "variant (voice weather tool)",
  {"tools_any": ["get_weather", "web_search"], "max_words": 60})

# email read
q("q34", "email_read", "studio", "Check e mail from nelma", "2026-10-05 studio 10:48",
  {"tools_any": ["check_email", "search_email", "gmail"], "tools_none": WEB + ["shell_execute"], "must_not": ["PIN"], "max_words": 90})
q("q35", "email_read", "studio", "What inbox are you checking?", "2026-10-05 voice 19:28",
  {"tools_none": WEB, "must_any": [["empirebox2026"]], "max_words": 50})

# capability / meta asks
q("q36", "capability", "studio", "Why do I need a pin. I am the founder. Fix that", "2026-10-05 studio 10:51",
  {"tools_any": ["request_improvement"], "tools_none": WEB, "must_not": ["IRS", "IP PIN"], "max_words": 90})
q("q37", "capability", "studio", "I think you need to add GropBot usage in the charts and in the module that relates to API expenses.", "2026-10-04 studio 20:56",
  {"tools_any": ["request_improvement"], "tools_none": WEB, "must_not": ["I don't edit my own code", "I can't edit"], "max_words": 80})
q("q38", "capability", "studio", "So you cant see memory on grok bot)", "2026-10-04 studio 19:24",
  {"tools_none": WEB, "must_not": ["✅", "❌"], "max_words": 80})
q("q39", "capability", "whatsapp", "Why is the document not loading", "2026-10-04 WhatsApp 21:40",
  {"tools_none": WEB, "must_ask": True, "max_words": 60})
q("q40", "capability", "studio", "can you see my attachments?", "2026-10-05 studio 17:52",
  {"tools_none": WEB, "max_words": 50})
q("q52", "capability", "studio", "did you get this update yet? in reference to the pdf i just gave you", "2026-10-05 studio 17:58",
  {"tools_none": WEB, "max_words": 70})

# small talk
q("q41", "small_talk", "whatsapp", "Hi", "2026-10-04 WhatsApp 19:46",
  {"tools_none": WEB + ["get_services_health"], "must_not": ["services", "OpenClaw", "configured email"], "max_words": 25})
q("q42", "small_talk", "whatsapp", "Who am I ?", "2026-10-04 WhatsApp 20:33",
  {"tools_none": WEB, "must_any": [["Rafael"]], "max_words": 70})
q("q43", "small_talk", "whatsapp", "But now you can speak in English. Sorry for the confusion", "2026-10-04 WhatsApp 21:35",
  {"tools_none": WEB, "max_words": 30})
q("q44", "small_talk", "studio", "thanks Max", "variant",
  {"tools_none": WEB, "max_words": 25})
q("q56", "small_talk", "studio", "hi", "2026-10-05 studio 18:02",
  {"tools_none": WEB, "max_words": 25})

# Spanish
q("q45", "spanish", "studio", "¿Cuáles son las últimas noticias en Cartago Valle?", "2026-10-04 voice 20:54",
  {"tools_any": ["web_search"], "lang": "es", "must_not": ["No tengo acceso"], "max_words": 140})
q("q46", "spanish", "whatsapp", "¿Cuál es la última cotización de Dahlia?", "variant",
  {"tools_none": WEB, "lang": "es", "must_any": [["EST-2026-298"]], "max_words": 80})
q("q47", "spanish", "studio", "¿Qué estás construyendo ahora?", "variant of 2026-10-06",
  {"tools_none": WEB, "lang": "es", "max_words": 100})
q("q48", "spanish", "whatsapp", "Mándame la cotización EST-2026-297 aquí", "variant",
  {"tools_none": WEB, "lang": "es", "must_any": [["EST-2026-297"]], "max_words": 80})

# multi-part
q("q49", "multi_part", "studio", "So, is voice working? Are we a hundred percent? Are you connected to what's going on? What's the most recent quote we were working on?",
  "2026-10-05 voice 18:36", {"tools_none": WEB, "must_any": [["EST-2026-29[78]"]], "max_words": 100})
q("q50", "multi_part", "studio", "What's the total of Dahlia phase 1 and phase 2, and which one is newer?", "variant",
  {"tools_none": WEB, "must_any": [["3,411\\.84", "4,759\\.96"], ["9,350\\.76"]], "max_words": 90})
q("q51", "multi_part", "studio", "Find the Willard final estimate and tell me the deposit amount", "variant",
  {"tools_none": WEB, "must_any": [["EST-2026-293", "Willard"], ["4,644"]], "max_words": 90})

Path(__file__).with_name("questions.json").write_text(json.dumps({
    "version": 1,
    "created": "2026-10-06",
    "note": "Rafael's real questions from max-sessions 2026-10-04..06 plus close variants. Expected kinds: short, grounded, right tool, no headers. Scored by scoring.py; run with run_eval.py on a test copy only.",
    "questions": Q}, indent=1, ensure_ascii=False) + "\n")
print(len(Q), "questions")
