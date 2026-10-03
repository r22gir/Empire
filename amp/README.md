# Actitud Mental Positiva (AMP) — El Portal de la Alegría
### Sitio Web Público & Plataforma Digital — Juan Diego Giraldo

Portal público y plataforma web de **Actitud Mental Positiva (AMP)**, "El Portal de la Alegría", diseñado con los más altos estándares visuales inspirados en **Mindvalley**, **Calm**, **Headspace** e **Insight Timer**, 100% en español, mobile-first y accesible (WCAG 2.2 AA).

---

## 🌟 Arquitectura y Experiencia Visual Premium

1. **Sistema de Diseño de Nivel Internacional**:
   - **Paleta cromática**: `gold` (#E0A526), `sunrise` (#F28C6B), `sage` (#7E9F84), `night` (#0E0C1C / #17142E), `cream` (#FFFDF9 / #FDF8F0).
   - **Tipografía**: **Fraunces** (titulares humanistas, editoriales y cálidos) + **Inter** (cuerpo de texto con legibilidad óptima y escala tipográfica refinada).
   - **Glassmorphism & Profundidad**: Encabezados translúcidos con desenfoque de fondo (`backdrop-filter`), tarjetas con borde sutil y sombras multicapa.
   - **Modo Claro y Modo Oscuro** con detección automática del sistema operativo y selector manual sin parpadeos.
   - **Animaciones sutiles**: Orbe de respiración pulsante (`breathe-orb`), gradientes en movimiento y respeto estricto a `prefers-reduced-motion`.
2. **Hero Cinematográfico Full-Bleed**:
   - Fondo inmersivo fotográfico de amanecer y naturaleza con velo de gradiente y scrim reforzado para contraste y legibilidad accesible (WCAG AA) en móvil y escritorio.
   - Check-in emocional interactivo inmediato ("¿Cómo te sientes hoy?") sin registro previo que recomienda la práctica adecuada al instante.
   - Franja neutral de credibilidad delimitada con placeholders claros para avales o medios reales de Juan Diego.
3. **Diseño Centrado en Maestros (Teacher-Forward - Estilo Mindvalley)**:
   - Tarjetas de retratos grandes para los cuatro guías principales: **Juan Diego Giraldo**, **Andrea Silva**, **Dericielo Jiménez** y **Lina Valencia Triviño**.
   - Tarjetas de **Programas y Retos de 21 Días** con arte de portada temático, nombre del mentor, nivel, lecciones y semanas de duración.
4. **Reproductor de Audio Global y Persistente (`GlobalAudioPlayer`)**:
   - **Persistencia total**: Sigue sonando ininterrumpidamente mientras el usuario navega entre cualquier página del sitio.
   - **Archivos de audio reales locales**: Pistas sonoras binaurales generadas en frecuencias Solfeggio (174Hz, 285Hz, 528Hz armónico) alojadas en `/public/audio/` para reproducción inmediata sin URLs rotas.
   - **Modo Inmersivo a Pantalla Completa**: Fondo difuminado con la temática, orbe de respiración consciente, transcripción accesible completa, selector de velocidad (`0.75x`, `1x`, `1.25x`, `1.5x`), saltos de 15 segundos y barra de avance interactiva.
   - **MediaSession API**: Permite pausar, reanudar y controlar desde la pantalla de bloqueo en iPhone, Android o Apple Watch.
5. **Biblioteca al Estilo Calm / Headspace**:
   - Mosaicos fotográficos inmersivos para cada ambiente temático (*Ansiedad & Calma, Sueño Profundo, Gratitud & Dicha, Amor Propio, Duelo & Sanación, Liderazgo & Enfoque*).
   - Filtros dinámicos por temática, duración y coach, con tarjetas de audio que muestran duración, categoría y botón de escucha inmediata.
6. **Módulo de Membresía & Comparador**:
   - Tabla comparativa de beneficios detallada entre el plan Gratuito y Premium Alegría ($9.99/mes o $79.99/año con 7 días de prueba gratis).
   - Conexión con Stripe Checkout en modo prueba (`/api/v1/payments/create-checkout-session`).
7. **Navegación Móvil y Accesibilidad**:
   - Barra de navegación inferior móvil (`MobileBottomNav`) con sensación de app nativa.
   - Banner persistente de llamado a la acción (*sticky CTA*) en móviles.
   - Scroll nativo y fluido sin bloqueos (`no overflow-hidden / 100vh traps`).

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
# URL del backend de APIs (AMP y LeadForge CRM)
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

## 📝 Lista de Elementos Reemplazables para Juan Diego Giraldo (Checklist de Placeholders)

Los siguientes recursos y textos cuentan actualmente con sustitutos de muestra (placeholders claramente rotulados, stock libre de derechos y tonos sonoros sintéticos calibrados) para que Juan Diego y su equipo los reemplacen con material propio:

- [ ] **Audios de Meditación y Frecuencias** (`public/audio/*.wav` y `src/lib/amp-content.ts`):
  - **Aviso importante**: Los archivos actuales en `/public/audio/` (`respiracion-ansiedad.wav`, `gratitud-matutina.wav`, `lider-interior.wav`, `sanar-duelo.wav`, `merezco-prosperidad.wav`, `sueno-profundo.wav`) son **tonos ambientales sintéticos de muestra** (frecuencias Solfeggio 174Hz, 285Hz, 528Hz con envolvente senoidal y ruido rosa) generados para que el reproductor web funcione en vivo. **Deben ser sustituidos por las grabaciones de voz y meditaciones guiadas oficiales grabadas por Juan Diego y sus mentores** (.mp3 / .m4a / .wav).
- [ ] **Fotografías de Coaches / Mentores** (`public/coaches/` y `src/lib/amp-content.ts`):
  - **Juan Diego Giraldo** (`public/coaches/juan-diego.jpg`): Retrato de alta resolución en estudio o entorno natural.
  - **Andrea Silva** (`public/coaches/andrea-silva.jpg`): Fotografía profesional orientada a crianza y familia.
  - **Dericielo Jiménez** (`public/coaches/dericielo-jimenez.jpg`): Fotografía profesional orientada a sanación y amor propio.
  - **Lina Valencia Triviño** (`public/coaches/lina-valencia.jpg`): Fotografía profesional orientada a transiciones y duelo.
- [ ] **Video / Fotografía Principal del Hero** (`public/hero/sunrise-hero.jpg`):
  - Clip de video en bucle (mp4/webm de ~15 segundos en baja tasa de bits con poster fallback) o fotografía panorámica de Juan Diego en una cumbre o amanecer.
- [ ] **Portadas de Cursos y Programas** (`public/programs/`):
  - Portadas gráficas personalizadas para *Mentalidad Invencible*, *Crianza con Amor*, *Sanación del Niño Interior* y *Trascendiendo el Duelo*.
- [ ] **Avales y Logos de Prensa / Credibilidad** (`src/app/page.tsx` - sección `PRESS_LOGOS`):
  - Reemplazar los 4 bloques neutrales `[Enfoque Metodológico]`, `[Acompañamiento]`, `[Espacio Sonoro]` y `[Comunidad]` por los medios, podcasts, certificaciones o métricas comunitarias verificadas de Juan Diego.
- [ ] **Testimonios Reales de Clientes / Alumnos** (`src/app/page.tsx`):
  - Sustituir los 3 placeholders `[Testimonio real de Juan a confirmar]` por citas textuales, nombres, fotos reales y perfiles de participantes de los programas de Juan Diego.
- [ ] **Biografías y Credenciales de Mentores** (`src/lib/amp-content.ts`):
  - Validar y ratificar las certificaciones y acreditaciones formales de cada mentora invitada.
- [ ] **Enlaces de Agendamiento Cal.com** (`src/app/agenda/page.tsx` y variable `NEXT_PUBLIC_CALCOM_URL`):
  - Vincular las cuentas reales de Cal.com / Google Calendar de cada coach.
- [ ] **Stripe en Modo Real (Live)** (`.env.local`):
  - Cargar los Price IDs reales creados en el panel de Stripe de Juan Diego (`STRIPE_PRICE_MONTHLY` y `STRIPE_PRICE_ANNUAL`).
