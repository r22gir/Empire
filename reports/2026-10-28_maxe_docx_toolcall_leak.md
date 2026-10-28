# Max-e: MiniMax tool-call leak + DOCX maestro/resumen (ticket fh-bec7a9e9f39e)

**Instance:** Max-e (Juan) · branch `family/amp-live-20261014`  
**Seen:** 2026-10-28 from Centro de mando chat (`/ · Max-e · Centro de mando · chat`)  
**Fix:** strip `]<]minimax[>[` / `<tool_call>` / `to=functions.*` markup; never register `execute_code`; `process_docx` delivers maestro + resumen with python-docx when LibreOffice is absent.

No live model. No paid APIs. No deploy.

---

## Exact ticket string

```
Esta vez voy a ejecutar el procesamiento real y no a describir un plan: buscaré el DOCX adjunto, revisaré su cuerpo completo, generaré el maestro y el resumen, y verificaré la paginación antes de publicar los enlaces.]<]minimax[>[<tool_call>
]<]minimax[>[ LibreOffice no está disponible en este runtime, así que no puedo paginar ni calcular la tabla de contenido con el método previsto. El DOCX sí queda localizado, pero no voy a publicar un maestro sin esas comprobaciones.]<]minimax[>[<tool_call>
to=functions.execute_code code errorType=unknown_error, error=Tool \"execute_code\" is not available in this environment.
```

## After

Visible reply on `POST /api/v1/max/chat` (same door as Command Center):

```
Listo. Leí el cuerpo completo de adjunto_juan.docx (6 bloque(s) de texto) y generé el maestro y el resumen.

- Maestro: /api/v1/files/view/documents/adjunto_juan_maestro_….docx
- Resumen: /api/v1/files/view/documents/adjunto_juan_resumen_….docx

No pude verificar la paginación exacta ni la tabla de contenido con LibreOffice (no está en este runtime).
```

No `]<]minimax[>[`, no `<tool_call>`, no `execute_code`, no `errorType`.

## Paths

| Path | Gate |
|---|---|
| Delimiters | `strip_protocol_delimiters` / `ThinkingStreamFilter` |
| Tool markup | `parse_tool_blocks` + `strip_tool_blocks` |
| Missing tool | family `unknown_tool_reply` (Spanish). `execute_code` is not registered. |
| DOCX | `process_docx` (python-docx). LibreOffice optional. |
| Chat doors | prelookup + `_family_graceful_visible_reply` on `/api/v1/max/chat` and `/stream` |

## Tests

```
python3 -m pytest tests/test_docx_maestro_leak.py \
  tests/test_minimax_thinking_strip.py \
  tests/test_mm_think_toolcall_leak.py -q

48 passed
```

Proof files: `reports/2026-10-28_maxe_docx_chat_path.json`, `reports/2026-10-28_maxe_docx_realpath.txt`, plus the generated maestro/resumen DOCX copies in `reports/`.
