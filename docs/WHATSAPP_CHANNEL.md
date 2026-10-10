# WhatsApp Business Cloud API

Each Empire instance has its own WhatsApp number. Max-e, Maxine, and Workroom Max do not share a token. The channel stays off until the variables below are set in that instance's environment. The status card in the command center says so.

Webhook: `/api/v1/whatsapp/webhook`

## English

### What you do in Meta

1. Use a phone number that belongs to this instance. Max-e, Maxine, and Workroom Max each need a different number.
2. In [Meta Business Suite](https://business.facebook.com/), create or open the Business that owns that number.
3. In [Meta for Developers](https://developers.facebook.com/), create an app of type Business and add the WhatsApp product.
4. On the WhatsApp API setup screen, copy the phone number ID and a temporary or permanent access token for this number only.
5. Under App settings, copy the app secret. Choose a verify token yourself. It is a password you invent for the webhook handshake.
6. Set the callback URL to `https://<this-instance-host>/api/v1/whatsapp/webhook` and subscribe to the `messages` field.
7. Put only the instance owner's WhatsApp numbers in `WHATSAPP_OWNER_NUMBERS`. Other senders are ignored and get no reply.

### Environment

Set these in the instance environment, or configure them through the guided "Connect WhatsApp" step during onboarding/settings (saved with file mode 0600 in the edition's data directory). Process environment variables override stored credentials.

| Variable | Purpose |
|---|---|
| `WHATSAPP_ACCESS_TOKEN` | Token for this number |
| `WHATSAPP_PHONE_NUMBER_ID` | Meta phone number ID for this number |
| `WHATSAPP_APP_SECRET` | Verifies `X-Hub-Signature-256` |
| `WHATSAPP_VERIFY_TOKEN` | Matches `hub.verify_token` on the handshake |
| `WHATSAPP_OWNER_NUMBERS` | Comma-separated owner numbers. Required before the channel answers |
| `WHATSAPP_APPROVED_TEMPLATES` | Optional comma-separated template names already approved in Meta |
| `WHATSAPP_REPLY_MODE` | `voice_text` (default), `text`, or `match` |
| `WHATSAPP_WEBHOOK_BASE_URL` | Optional base URL (defaults to `https://wa-amp.empirebox.store` for Max-e, `https://wa-maxine.empirebox.store` for Maxine) |

If any of the first four is missing, inbound webhooks return 503 and the UI shows the channel off.

### Family Editions Guided Walkthrough (Max-e & Maxine)

In the initial setup interview or the Command Center dashboard:
1. **Interactive Guided Setup**: The owner is asked whether they already have Meta credentials or need a step-by-step walkthrough.
2. **Step-by-Step Meta Walkthrough**:
   - Create a Meta for Developers account with the owner's OWN Facebook login.
   - Create a Business-type app and add the WhatsApp product.
   - Use Meta's free test number first and verify the owner's personal number with the 6-digit code.
   - Copy the Phone Number ID, Access Token, and App Secret into the edition form.
3. **Secure Storage**: Credentials are saved to `$EMPIRE_DATA_DIR/whatsapp_credentials.json` with strict `0600` permissions. Raw tokens and secrets are never returned by any API or shown in the UI.
4. **Test Connection**: A read-only verification action calls Meta Graph API to read `display_phone_number` and `verified_name` and check webhook handshake status without sending any WhatsApp message.
5. **Phase 2 Note**: WhatsApp voice calls are clearly marked for Phase 2; Phase 1 delivers interactive text, voice note audio transcription, and PDF document delivery.

### Behavior

- Text and voice notes use the same Spanish voice-to-document borrador. Voice is downloaded from Meta and transcribed. Nothing is emailed.
- Replies follow `WHATSAPP_REPLY_MODE`. `voice_text` (the default) sends an OGG/Opus voice note in the edition language — Spanish `es-CO` for Max-e and Maxine — and a short text summary of the same reply. `text` sends text only. `match` uses the voice note when the owner sent audio, and text when they wrote. If speech synthesis fails, the reply is text only and says so. PDF documents stay attachments.
- A PDF is sent back as a WhatsApp document only after the owner writes a confirmation such as `envía el borrador` or `send the draft`.
- Photos are saved on the project timeline. A caption like `proyecto Portal lote 12 etapa cimentacion` sets the project, lot, and stage.
- Session replies are allowed for 24 hours after the owner's last message. Outside that window the only outbound path is a name listed in `WHATSAPP_APPROVED_TEMPLATES`.
- Messages for a different phone number ID are ignored, so one webhook process cannot answer another instance's number.

### Files to copy onto `feature/drawing-standard`

- `backend/app/services/whatsapp_cloud.py`
- `backend/app/services/max/tts_service.py` (language argument for es-CO / English)
- `backend/app/routers/whatsapp.py`
- `backend/app/main.py` (the `load_router` line for `app.routers.whatsapp`)
- `backend/app/services/max/hermes_phase3.py` (live WhatsApp status instead of the placeholder)
- `backend/app/services/voice_doc/pipeline.py` (`channel_report`)
- `backend/app/services/voice_doc/store.py` (`latest_draft_for_channel`)
- `backend/app/services/instance_files.py` (photo source `whatsapp`)
- `backend/tests/test_whatsapp_cloud.py`
- `docs/WHATSAPP_CHANNEL.md`
- `empire-command-center/app/components/voice/WhatsAppStatus.tsx`
- `empire-command-center/app/components/screens/DashboardScreen.tsx`
- `empire-command-center/app/components/screens/ConstructionForgePage.tsx`
- `empire-command-center/app/ayuda/voz/page.tsx`

The voice-to-document engine and the photo timeline must already exist on the destination branch. Tests mock Meta. They do not call Graph.

---

# API de WhatsApp Business Cloud

Cada instancia de Empire tiene su propio número. Max-e, Maxine y Workroom Max no comparten token. El canal permanece apagado hasta que esas variables existan en el entorno de esa instancia. La tarjeta del centro de mando lo dice.

Webhook: `/api/v1/whatsapp/webhook`

## Español

### Lo que hace el dueño en Meta

1. Usa un número que pertenezca a esta instancia. Max-e, Maxine y Workroom Max necesitan números distintos.
2. En [Meta Business Suite](https://business.facebook.com/), crea o abre el negocio dueño de ese número.
3. En [Meta for Developers](https://developers.facebook.com/), crea una app tipo Business y agrega el producto WhatsApp.
4. En la pantalla de configuración de la API, copia el identificador del número y un token de acceso de ese número.
5. En la configuración de la app, copia el app secret. Inventa un verify token. Es la contraseña del apretón de manos del webhook.
6. La URL de devolución de llamada es `https://<anfitrión-de-esta-instancia>/api/v1/whatsapp/webhook`. Suscribe el campo `messages`.
7. En `WHATSAPP_OWNER_NUMBERS` van solo los números del dueño de la instancia. Los demás se ignoran y no reciben respuesta.

### Entorno

Estas variables viven en el entorno de la instancia o se configuran desde el paso guiado "Conectar WhatsApp" en la entrevista de bienvenida / centro de mando (guardadas con permisos estrictos 0600 en el directorio de datos de la edición). Las variables del entorno del proceso tienen prioridad como sobreescritura si existen.

| Variable | Para qué |
|---|---|
| `WHATSAPP_ACCESS_TOKEN` | Token de este número |
| `WHATSAPP_PHONE_NUMBER_ID` | ID del número en Meta |
| `WHATSAPP_APP_SECRET` | Verifica `X-Hub-Signature-256` |
| `WHATSAPP_VERIFY_TOKEN` | Coincide con `hub.verify_token` |
| `WHATSAPP_OWNER_NUMBERS` | Números del dueño, separados por coma. Sin esto el canal no contesta |
| `WHATSAPP_APPROVED_TEMPLATES` | Opcional. Nombres de plantillas ya aprobadas en Meta |
| `WHATSAPP_REPLY_MODE` | `voice_text` (predeterminado), `text` o `match` |
| `WHATSAPP_WEBHOOK_BASE_URL` | URL base opcional (por defecto `https://wa-amp.empirebox.store` en Max-e y `https://wa-maxine.empirebox.store` en Maxine) |

Si falta alguna de las cuatro primeras, el webhook responde 503 y la interfaz muestra el canal apagado.

### Tutorial Guiado en Ediciones Familiares (Max-e y Maxine)

En la entrevista inicial o desde el Centro de Mando:
1. **Paso Interactivo**: Pregunta al dueño si ya tiene credenciales de Meta o prefiere la guía paso a paso.
2. **Tutorial Numérico para Meta**:
   - Crear cuenta de desarrollador con su PROPIA cuenta de Facebook (no la de Rafael).
   - Crear una aplicación tipo Negocios (Business) y agregar WhatsApp.
   - Usar el número de prueba gratuito y registrar su celular personal con el código de 6 dígitos.
   - Copiar el Identificador del número de teléfono, el Token de acceso y la Clave secreta (App Secret).
3. **Almacenamiento Seguro**: Se guardan en `$EMPIRE_DATA_DIR/whatsapp_credentials.json` con permisos `0600`. Ninguna API devuelve los secretos crudos.
4. **Probar Conexión**: Botón de prueba de solo lectura que consulta en Graph API el `display_phone_number` y `verified_name`, y confirma si el webhook ya hizo el apretón de manos con Meta, sin enviar ningún mensaje de WhatsApp.
5. **Aviso Fase 2**: Se indica claramente que las llamadas de voz por WhatsApp llegarán en la Fase 2, funcionando actualmente texto, notas de voz y PDFs.

### Comportamiento

- El texto y las notas de voz entran al mismo borrador de voz a documento. La nota se descarga de Meta y se transcribe. No se envía correo.
- Las respuestas siguen `WHATSAPP_REPLY_MODE`. `voice_text`, el valor predeterminado, manda una nota de voz OGG/Opus en el idioma de la edición — español `es-CO` en Max-e y Maxine — y un texto corto con el mismo contenido resumido. `text` manda solo texto. `match` usa la nota de voz si el dueño envió audio, y texto si escribió. Si la síntesis de voz falla, sale solo el texto y lo dice. Los documentos siguen como PDF.
- El PDF vuelve como documento de WhatsApp solo después de que el dueño escriba una confirmación, por ejemplo `envía el borrador` o `send the draft`.
- Las fotos quedan en la línea de tiempo del proyecto. Un pie como `proyecto Portal lote 12 etapa cimentacion` fija proyecto, lote y etapa.
- Las respuestas de sesión caben en las 24 horas siguientes al último mensaje del dueño. Fuera de esa ventana solo sale una plantilla cuyo nombre esté en `WHATSAPP_APPROVED_TEMPLATES`.
- Un mensaje dirigido a otro ID de número se ignora. Un proceso no contesta el número de otra instancia.

### Archivos para llevar a `feature/drawing-standard`

Están listados en la sección en inglés, bajo “Files to copy onto `feature/drawing-standard`”. El motor de voz a documento y la línea de tiempo de fotos tienen que existir ya en esa rama. Las pruebas simulan a Meta. No llaman a Graph.
