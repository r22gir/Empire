# Actitud Mental Positiva (AMP) — El Portal de la Alegría
### Sitio Web Público & Plataforma Digital — Juan Diego Giraldo

Bienvenido al nuevo portal público y plataforma web de **Actitud Mental Positiva (AMP)**, "El Portal de la Alegría", diseñado con estándares visuales inspirados en Calm, Headspace y Mindvalley, 100% en español, mobile-first y accesible (WCAG 2.2 AA).

---

## 🌟 Arquitectura y Características

1. **Sistema de Diseño**:
   - Paleta cromática: `gold` (#E0A526), `sunrise` (#F28C6B), `sage` (#7E9F84), `night` (#14122B), `cream` (#FFF9F1).
   - Tipografía: **Fraunces** (titulares humanistas y cálidos) + **Inter** (cuerpo de texto legible).
   - Modo Claro y Modo Oscuro con detección automática del sistema y selector manual.
   - Animaciones suaves de respiración (`breathe-orb`), gradientes fluidos y microinteracciones.
2. **Navegación Móvil y de Escritorio**:
   - Barra de navegación superior fija en escritorio con accesos directos y llamada a la acción.
   - Barra de navegación inferior tipo aplicación móvil nativa (`MobileBottomNav`) en pantallas pequeñas.
   - Sin bloqueos de scroll (`100vh traps` o `overflow: hidden` descontrolado).
3. **Reproductor de Audio Global y Persistente (`GlobalAudioPlayer`)**:
   - Mantiene la reproducción continua mientras el usuario navega entre cualquier página del sitio.
   - Controles de reproducción, retroceso/adelanto de 15 segundos, barra de progreso (scrubber), selector de velocidad (`0.75x`, `1x`, `1.25x`, `1.5x`).
   - Modo barra inferior compacta, minimizado (pill flotante) y modal expandido inmersivo con visualizador de respiración y transcripción.
   - Integración nativa con **MediaSession API** para control desde la pantalla de bloqueo en iOS y Android.
4. **Páginas Públicas**:
   - `/` (**Inicio**): Hero inmersivo, valor diferencial, los 3 pilares (Mentalidad, Bienestar, Liderazgo), check-in emocional instantáneo, meditaciones destacadas, perfiles de coaches, testimonios y llamada a membresía.
   - `/conocenos` (**Conócenos**): Biografías completas, filosofía y credenciales de Juan Diego Giraldo, Andrea Silva, Dericielo Jiménez y Lina Valencia Triviño.
   - `/servicios` (**Servicios**): Sesiones 1:1, talleres grupales, membresía y bienestar corporativo.
   - `/biblioteca` (**Biblioteca de Audio**): Explorador temático (Ansiedad, Sueño, Gratitud, Autoestima, Duelo, Liderazgo), filtro por duración y coach, con reproducción directa.
   - `/blog` y `/blog/[slug]` (**Blog**): Artículos reflexivos y guías de vida con meditaciones sugeridas.
   - `/agenda` (**Agenda & Encuentros**): Reserva de sesiones con selector de coach e integración con Cal.com / Google Calendar.
   - `/membresia` (**Membresía**): Planes Gratuito y Premium ($9.99/mes o $79.99/año con 7 días de prueba), listado de beneficios y pasarela Stripe Checkout en modo prueba.
   - `/animo` (**¿Cómo te sientes hoy?**): Registro diario de estado de ánimo conectado al API de AMP (`/api/v1/amp/moods`), notas reflexivas, historial en calendario y recomendaciones personalizadas.
   - `/onboarding` (**Diagnóstico Inicial & Registro**): Cuestionario de 3 pasos, creación de cuenta vía AMP Auth (`/api/v1/amp/signup`) e inyección automática del prospecto al CRM LeadForge (`/api/v1/leads/`).

---

## 🚀 Cómo Ejecutar en Desarrollo y Producción

### Requisitos Previos
- Node.js 18+ (recomendado Node 20 LTS)
- Backend de EmpireBox / AMP API corriendo en puerto 8000 o 8011

### 1. Instalación de Dependencias
```bash
cd amp
npm install
```

### 2. Variables de Entorno (`.env.local`)
Crea un archivo `.env.local` en la raíz de `amp/` con las siguientes claves:

```bash
# URL del backend de APIs (AMP y LeadForge)
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1

# URL de reserva de citas (Cal.com o Google Calendar)
NEXT_PUBLIC_CALCOM_URL=https://cal.com/amp-edition

# Stripe (Modo Prueba para desarrollo / producción)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PRICE_MONTHLY=price_12345
STRIPE_PRICE_ANNUAL=price_67890
```

### 3. Ejecución Local (Puerto 3011 para convivir con EmpireBox)
```bash
# Desarrollo en puerto 3011
PORT=3011 npm run dev

# Compilación de producción
npm run build

# Servidor de producción en puerto 3011
PORT=3011 npm start
```

---

## 🌐 Cómo Servir en un Hostname Propio (`actitudmentalpositiva.com`)

El proyecto está desacoplado para ser publicado en su propio dominio o subdominio sin interferir con la infraestructura existente de EmpireBox:

### Opción A: Despliegue en Servidor Propio (Dell / Nginx)
Configura un bloque de servidor Nginx que redirija el dominio `actitudmentalpositiva.com` al puerto local `3011`:

```nginx
server {
    server_name actitudmentalpositiva.com www.actitudmentalpositiva.com;

    location / {
        proxy_pass http://127.0.0.1:3011;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Redirección de llamadas API al backend (puerto 8000 / 8011)
    location /api/v1/ {
        proxy_pass http://127.0.0.1:8000/api/v1/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Opción B: Despliegue en Vercel o Cloudflare Pages
1. Conecta el repositorio de GitHub y selecciona el subdirectorio `amp`.
2. Asigna las variables de entorno (`NEXT_PUBLIC_API_URL`, etc.).
3. Vincula el dominio `actitudmentalpositiva.com` en la configuración de dominios de Vercel/Cloudflare.

---

## 📝 Lista de Elementos Reemplazables para Juan Diego Giraldo (Checklist)

Los siguientes elementos cuentan actualmente con marcadores de posición (*placeholders*) claramente señalizados y deben ser provistos o actualizados para el lanzamiento final:

- [ ] **Fotografías Oficiales de Coaches** (`src/lib/amp-content.ts` y `/public/coaches/`):
  - **Juan Diego Giraldo**: Fotografía en alta resolución para el hero y ficha de coach.
  - **Andrea Silva**: Fotografía profesional orientada a crianza y familia.
  - **Dericielo Jiménez**: Fotografía profesional orientada a amor propio y duelo.
  - **Lina Valencia Triviño**: Fotografía profesional orientada a resiliencia y liderazgo.
- [ ] **Video / Imagen de Fondo del Hero** (`src/app/page.tsx`):
  - Video relajante de naturaleza o animación sutil en bucle (mp4/webm) o fotografía de amanecer en alta resolución.
- [ ] **Audios de Meditaciones Reales** (`src/lib/amp-content.ts`):
  - Cargar los archivos de audio definitivos (.mp3 o .m4a) en un bucket S3 o CDN y reemplazar las URLs de muestra en la constante `SAMPLE_TRACKS`.
- [ ] **Enlaces de Agenda Cal.com / Google Calendar** (`src/app/agenda/page.tsx` y `.env.local`):
  - Configurar las cuentas individuales de Cal.com de Juan Diego, Andrea, Dericielo y Lina o configurar `NEXT_PUBLIC_CALCOM_URL`.
- [ ] **Stripe en Modo Real (Live)** (`.env.local`):
  - Crear los dos productos de suscripción en el Dashboard de Stripe (Membresía Mensual $9.99 USD y Anual $79.99 USD) e insertar los Price IDs reales (`price_...`).
- [ ] **Testimonios Reales** (`src/app/page.tsx`):
  - Sustituir los testimonios de muestra por historias y citas reales de clientes y miembros de la comunidad AMP.
- [ ] **Redes Sociales y Enlaces de Contacto** (`src/components/SiteFooter.tsx`):
  - Confirmar enlaces a Instagram, YouTube, Spotify y número de WhatsApp de soporte.
