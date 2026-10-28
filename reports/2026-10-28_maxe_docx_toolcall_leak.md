# Max-e: MiniMax tool-call leak + DOCX maestro/resumen (ticket fh-bec7a9e9f39e)

**Instance:** Max-e (Juan) · branch `family/amp-live-20261014`  
**Kind:** offline test output (no running Max-e in this cloud agent).  
**Seen:** 2026-10-28 from Centro de mando chat (`/ · Max-e · Centro de mando · chat`)

Tests do not overwrite these files. No live model. No paid APIs. No deploy.

---

## Exact ticket string

```
Esta vez voy a ejecutar el procesamiento real y no a describir un plan: buscaré el DOCX adjunto, revisaré su cuerpo completo, generaré el maestro y el resumen, y verificaré la paginación antes de publicar los enlaces.]<]minimax[>[<tool_call>
]<]minimax[>[ LibreOffice no está disponible en este runtime, así que no puedo paginar ni calcular la tabla de contenido con el método previsto. El DOCX sí queda localizado, pero no voy a publicar un maestro sin esas comprobaciones.]<]minimax[>[<tool_call>
to=functions.execute_code code errorType=unknown_error, error=Tool \"execute_code\" is not available in this environment.
```

## After (TestClient `/api/v1/max/chat`, mocked MiniMax payload)

Visible reply:

```
Listo. Leí el cuerpo completo de adjunto_juan.docx (6 bloque(s) de texto) y generé el maestro y el resumen.

- Maestro: /api/v1/files/view/documents/adjunto_juan_maestro_….docx
- Resumen: /api/v1/files/view/documents/adjunto_juan_resumen_….docx

No pude verificar la paginación exacta ni la tabla de contenido con LibreOffice (no está en este runtime).
```

Executed tools: `process_docx` only (leaked `execute_code` is dropped after redirect, no 3-round loop, no Quality-issue badge).

## Tests

There is no GitHub Actions workflow on this repo (only `.github/workflows-disabled/`). Local run:

```
cd backend && python3 -m pytest tests/test_docx_maestro_leak.py \
  tests/test_minimax_thinking_strip.py \
  tests/test_mm_think_toolcall_leak.py \
  tests/test_tool_block_parser_hotfix.py -q
```

**68 passed**, 7 warnings, 2.33s. Full transcript: `reports/2026-10-28_maxe_docx_pytest.txt`.

(The earlier report line `48 passed` was wrong — that three-file subset was never 48, and the PR body later said 67. This count is from the transcript above.)

The JSON/DOCX files next to this report are **offline test output** from TestClient + python-docx, not a capture from a live EmpireDell Max-e process. The first-PR JSON still shows the `process_docx` + `execute_code` ×3 loop; tests no longer write `reports/`.
