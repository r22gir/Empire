"""Edition trade profiles for LeadForge, SocialForge and CRM defaults.

Workroom (Rafael's main build) returns ``None`` everywhere here, so its
drapery LeadForge, SocialForge and campaign templates stay exactly as they
are. The family editions get their own trade:

* maxine (Camilo): real estate, GAC sales of Portal Campestre 2 / Argos
  Campestre lots in Cartago / Zaragoza, Valle del Cauca.
* amp (Juan Diego): AMP coaching (Spanish personal development) and
  Cibernettic IT (cybersecurity, DBA, networks/VoIP, BI, SLAs).

No prices, legal or company registration details live here.
"""
from __future__ import annotations

import os
from typing import Optional


def _edition() -> str:
    try:
        from app.edition import edition_name

        return (edition_name() or "").strip().lower()
    except Exception:
        return (os.getenv("EMPIRE_EDITION") or "workroom").strip().lower()


# ── Maxine: real estate ────────────────────────────────────────────────

_MAXINE = {
    "edition": "maxine",
    "family": True,
    "locale": "es",
    "title": "Prospectos",
    "subtitle": "Captación de compradores de lotes campestres",
    "default_unit": "gac",
    "business_units": [
        {
            "value": "gac",
            "label": "GAC · Portal Campestre 2 / Argos Campestre",
            "default_location": "Cartago / Zaragoza, Valle del Cauca, Colombia",
            "default_target": "compradores_lotes",
            "targets": [
                {"value": "compradores_lotes", "label": "Compradores de lote campestre"},
                {"value": "inversionistas", "label": "Inversionistas en finca raíz"},
                {"value": "colombianos_exterior", "label": "Colombianos en el exterior"},
                {"value": "agentes_inmobiliarios", "label": "Agentes inmobiliarios / inmobiliarias"},
            ],
        }
    ],
    "target_queries": {
        "compradores_lotes": "lotes campestres venta casas campestres condominio campestre",
        "inversionistas": "inversión finca raíz inversionistas inmobiliarios valorización",
        "colombianos_exterior": "colombianos en el exterior vivienda en Colombia inversión",
        "agentes_inmobiliarios": "inmobiliaria agente inmobiliario bienes raíces finca raíz",
    },
    "fit_tags": [
        {"key": "lote_campestre", "label": "lote campestre",
         "keywords": ["campestre", "lote", "finca", "parcela", "condominio", "casa de campo"]},
        {"key": "inversion", "label": "inversión",
         "keywords": ["inversi", "invest", "valoriza", "rentabilidad", "patrimonio"]},
        {"key": "financiacion", "label": "financiación",
         "keywords": ["financ", "crédito", "credito", "hipotec", "leasing", "cuotas", "plan de pago"]},
        {"key": "exterior", "label": "colombianos en el exterior",
         "keywords": ["exterior", "abroad", "diaspora", "remesa", "migrante", "estados unidos", "españa"]},
        {"key": "agente", "label": "agente inmobiliario",
         "keywords": ["inmobiliari", "real estate", "bienes raíces", "bienes raices", "finca raíz", "finca raiz", "corredor", "realtor"]},
    ],
    "relevance_keywords": {
        "lote": 4, "campestre": 5, "finca raíz": 4, "finca raiz": 4, "inmobiliaria": 4,
        "bienes raíces": 4, "bienes raices": 4, "real estate": 3, "vivienda": 3,
        "inversión": 3, "inversion": 3, "condominio": 3, "constructora": 2, "parcela": 3,
    },
    "proximity": ["cartago", "zaragoza", "valle del cauca", "pereira", "risaralda", "cali",
                  "tuluá", "tulua", "armenia", "quindío", "quindio", "obando", "ansermanuevo"],
    "keyword_terms": ["campestre", "lote", "finca raíz", "inmobiliaria", "inversión"],
    "angles": {
        "lote_campestre": "lote campestre en Zaragoza (Cartago) para vivir o descansar",
        "inversion": "inversión en lotes campestres en el norte del Valle",
        "financiacion": "plan de pagos para su lote campestre",
        "exterior": "vivienda campestre en Colombia para colombianos en el exterior",
        "agente": "alianza de referidos para vender lotes campestres",
    },
    "default_angle": "lotes campestres en Cartago y Zaragoza, Valle del Cauca",
    "client_types": {"agente": "agente", "inversion": "inversionista", "exterior": "exterior"},
    "default_client_type": "comprador",
    "social": {
        "hashtags": "#LoteCampestre #Cartago #Zaragoza #ValleDelCauca #InversiónInmobiliaria",
        "profile": {
            "business_name": "GAC",
            "tagline": "Vivienda campestre en Zaragoza (Cartago), Valle del Cauca",
            "website": "",
            "city": "Cartago",
            "state": "Valle del Cauca",
            "services": "Lotes y casas campestres, planes de pago, acompañamiento en la compra",
            "target_audience": "Compradores de lote campestre, inversionistas, colombianos en el exterior, agentes inmobiliarios",
            "style_keywords": "Campestre, Tranquilidad, Familia, Inversión",
            "brand_colors": "#b8960c, #1a1a1a, #faf9f7",
            "owner_name": "Camilo Giraldo",
            "service_area": "Cartago y Zaragoza, Valle del Cauca, Colombia",
        },
        "business_profiles": [
            {"business_key": "gac", "business_name": "GAC",
             "tagline": "Vivienda campestre en Zaragoza (Cartago)",
             "bio_short": "Lotes y casas campestres | Cartago • Zaragoza • Valle del Cauca",
             "category": "Inmobiliaria", "city": "Cartago", "state": "Valle del Cauca"},
        ],
    },
    "campaigns": [
        {
            "name": "Compradores de lote campestre — Portal Campestre 2",
            "description": "Seguimiento a personas interesadas en un lote o casa campestre en Zaragoza (Cartago).",
            "business_unit": "gac", "target_type": "compradores_lotes",
            "steps": [
                {"step_number": 1, "step_type": "email", "delay_days": 0,
                 "subject": "Lotes campestres en Zaragoza (Cartago) — {first_name}",
                 "body_template": (
                     "Hola {first_name},\n\n"
                     "Gracias por su interés en vivienda campestre en el norte del Valle. "
                     "En Portal Campestre 2, en Zaragoza (Cartago), tenemos lotes disponibles "
                     "para construir su casa de campo.\n\n"
                     "Con gusto le enviamos el plano de lotes, las áreas y la información de "
                     "planes de pago. ¿Prefiere que le escribamos por WhatsApp o que agendemos "
                     "una visita a la sala de ventas?\n\n"
                     "Cordialmente,\nEquipo GAC")},
                {"step_number": 2, "step_type": "follow_up_email", "delay_days": 3,
                 "subject": "Re: Lotes campestres en Zaragoza",
                 "body_template": (
                     "Hola {first_name},\n\n"
                     "Le escribo para saber si pudo revisar la información de Portal Campestre 2. "
                     "Los lotes disponibles cambian con las separaciones, así que con gusto le "
                     "confirmo cuáles siguen libres y le comparto el plan de pagos.\n\n"
                     "Cordialmente,\nEquipo GAC")},
                {"step_number": 3, "step_type": "phone_script", "delay_days": 7, "is_manual": True,
                 "subject": "Llamar o escribir por WhatsApp a {first_name}",
                 "body_template": (
                     "GUION (llamada o WhatsApp):\n"
                     "\"Hola {first_name}, le habla [nombre] de GAC. Le envié información de los "
                     "lotes campestres de Portal Campestre 2 en Zaragoza. ¿Le gustaría conocer "
                     "los lotes disponibles o agendar una visita?\"\n\n"
                     "PUNTOS CLAVE:\n"
                     "- Lotes disponibles según el plano vigente (confirmar antes de ofrecer)\n"
                     "- Plan de pagos a la medida, sujeto a aprobación\n"
                     "- Visita a la sala de ventas en Zaragoza\n"
                     "- No dar precios que no estén confirmados")},
                {"step_number": 4, "step_type": "follow_up_email", "delay_days": 15,
                 "subject": "Su lote campestre sigue esperando — {first_name}",
                 "body_template": (
                     "Hola {first_name},\n\n"
                     "Cuando quiera retomar la búsqueda de su lote campestre, aquí estamos. "
                     "Le podemos enviar el plano actualizado y resolver sus preguntas sobre "
                     "la separación y el plan de pagos.\n\n"
                     "Cordialmente,\nEquipo GAC")},
            ],
        },
        {
            "name": "Inversionistas — Valorización campestre",
            "description": "Contacto con inversionistas interesados en lotes campestres en el norte del Valle.",
            "business_unit": "gac", "target_type": "inversionistas",
            "steps": [
                {"step_number": 1, "step_type": "email", "delay_days": 0,
                 "subject": "Inversión en lotes campestres — norte del Valle",
                 "body_template": (
                     "Hola {first_name},\n\n"
                     "Le comparto una opción de inversión en finca raíz: lotes campestres en "
                     "Zaragoza (Cartago), Valle del Cauca. Podemos enviarle el plano de lotes "
                     "disponibles y las condiciones de pago vigentes.\n\n"
                     "¿Le interesa recibir la información?\n\n"
                     "Cordialmente,\nEquipo GAC")},
                {"step_number": 2, "step_type": "follow_up_email", "delay_days": 5,
                 "subject": "Re: Inversión en lotes campestres",
                 "body_template": (
                     "Hola {first_name},\n\n"
                     "Retomo mi mensaje sobre los lotes campestres en Zaragoza. Si lo desea, "
                     "agendamos una llamada corta o una visita al proyecto.\n\n"
                     "Cordialmente,\nEquipo GAC")},
            ],
        },
        {
            "name": "Colombianos en el exterior — Vivienda campestre en el Valle",
            "description": "Colombianos que viven fuera y buscan lote o casa campestre en el norte del Valle.",
            "business_unit": "gac", "target_type": "colombianos_exterior",
            "steps": [
                {"step_number": 1, "step_type": "email", "delay_days": 0,
                 "subject": "Su lote campestre en el Valle, desde donde esté",
                 "body_template": (
                     "Hola {first_name},\n\n"
                     "Si vive fuera de Colombia y piensa en una casa de campo en el Valle, "
                     "en Portal Campestre 2 (Zaragoza, Cartago) le acompañamos a distancia: "
                     "plano de lotes, videollamada, separación y plan de pagos.\n\n"
                     "¿Le enviamos la información por correo o por WhatsApp?\n\n"
                     "Cordialmente,\nEquipo GAC")},
                {"step_number": 2, "step_type": "follow_up_email", "delay_days": 4,
                 "subject": "Re: Lote campestre en el Valle",
                 "body_template": (
                     "Hola {first_name},\n\n"
                     "Quedo atento por si quiere agendar una videollamada para ver los lotes "
                     "disponibles y resolver sus dudas.\n\n"
                     "Cordialmente,\nEquipo GAC")},
            ],
        },
        {
            "name": "Agentes inmobiliarios — Alianza de referidos",
            "description": "Inmobiliarias y agentes de la región que pueden referir compradores.",
            "business_unit": "gac", "target_type": "agentes_inmobiliarios",
            "steps": [
                {"step_number": 1, "step_type": "email", "delay_days": 0,
                 "subject": "Alianza para lotes campestres en Zaragoza — {business}",
                 "body_template": (
                     "Hola {first_name},\n\n"
                     "Somos GAC y comercializamos lotes campestres en Zaragoza (Cartago). "
                     "Buscamos aliados en {location} que tengan clientes interesados en vivienda "
                     "campestre. ¿Podemos conversar sobre un esquema de referidos?\n\n"
                     "Cordialmente,\nEquipo GAC")},
                {"step_number": 2, "step_type": "phone_script", "delay_days": 5, "is_manual": True,
                 "subject": "Llamar a {first_name} en {business}",
                 "body_template": (
                     "GUION:\n\"Hola {first_name}, le habla [nombre] de GAC. Le escribí sobre una "
                     "alianza de referidos para lotes campestres en Zaragoza. ¿Tiene clientes "
                     "buscando lote o casa campestre en el norte del Valle?\"")},
            ],
        },
    ],
}


# ── Max-e (AMP edition): coaching + IT ─────────────────────────────────

_AMP = {
    "edition": "amp",
    "family": True,
    "locale": "es",
    "title": "Prospectos",
    "subtitle": "AMP coaching y Cibernettic IT",
    "default_unit": "amp",
    "business_units": [
        {
            "value": "amp",
            "label": "AMP · Actitud Mental Positiva (coaching)",
            "default_location": "Colombia y comunidad hispana (online)",
            "default_target": "crecimiento_personal",
            "targets": [
                {"value": "crecimiento_personal", "label": "Personas que buscan crecimiento personal"},
                {"value": "talleres_empresas", "label": "Empresas: talleres para equipos"},
                {"value": "emprendedores_lideres", "label": "Emprendedores y líderes"},
                {"value": "comunidad_hispana", "label": "Comunidad hispana (programas online)"},
            ],
        },
        {
            "value": "cibernettic",
            "label": "Cibernettic IT (ciberseguridad y datos)",
            "default_location": "Colombia",
            "default_target": "pymes_ciberseguridad",
            "targets": [
                {"value": "pymes_ciberseguridad", "label": "Pymes que necesitan ciberseguridad"},
                {"value": "pymes_datos_dba", "label": "Pymes: bases de datos / DBA"},
                {"value": "pymes_redes_voip", "label": "Pymes: redes y VoIP"},
                {"value": "pymes_bi", "label": "Pymes: inteligencia de negocios (BI)"},
            ],
        },
    ],
    "target_queries": {
        "crecimiento_personal": "coaching desarrollo personal crecimiento personal mentalidad positiva",
        "talleres_empresas": "talleres bienestar empresarial capacitación equipos recursos humanos",
        "emprendedores_lideres": "emprendedores liderazgo comunidad de emprendimiento",
        "comunidad_hispana": "comunidad hispana latina desarrollo personal grupos",
        "pymes_ciberseguridad": "pyme empresa ciberseguridad seguridad informática",
        "pymes_datos_dba": "empresa base de datos administración SQL Oracle DBA",
        "pymes_redes_voip": "empresa redes cableado telefonía VoIP PBX",
        "pymes_bi": "empresa business intelligence Power BI analítica reportes",
    },
    "fit_tags": [
        {"key": "crecimiento", "label": "crecimiento personal", "unit": "amp",
         "keywords": ["coach", "desarrollo personal", "crecimiento", "mindset", "mentalidad", "bienestar", "motivaci"]},
        {"key": "talleres", "label": "talleres", "unit": "amp",
         "keywords": ["taller", "workshop", "seminario", "capacitaci", "conferencia", "retiro"]},
        {"key": "programas", "label": "programas", "unit": "amp",
         "keywords": ["programa", "curso", "mentor", "academia", "escuela"]},
        {"key": "ciberseguridad", "label": "ciberseguridad", "unit": "cibernettic",
         "keywords": ["ciberseguridad", "cybersecurity", "seguridad informática", "seguridad informatica", "firewall", "ransomware", "pentest"]},
        {"key": "dba", "label": "DBA / datos", "unit": "cibernettic",
         "keywords": ["base de datos", "bases de datos", "database", "sql", "oracle", "dba", "gestión de datos"]},
        {"key": "redes_voip", "label": "redes / VoIP", "unit": "cibernettic",
         "keywords": ["redes", "network", "voip", "telefonía", "telefonia", "pbx", "cableado"]},
        {"key": "bi", "label": "BI", "unit": "cibernettic",
         "keywords": ["business intelligence", "power bi", "analítica", "analitica", "dashboard", "inteligencia de negocios"]},
        {"key": "sla", "label": "soporte / SLA", "unit": "cibernettic",
         "keywords": ["soporte", "mesa de ayuda", "sla", "outsourcing", "mantenimiento", "help desk"]},
    ],
    "relevance_keywords": {
        "coaching": 5, "coach": 4, "desarrollo personal": 5, "crecimiento personal": 5,
        "taller": 3, "capacitación": 3, "bienestar": 3, "liderazgo": 3,
        "ciberseguridad": 5, "seguridad informática": 5, "base de datos": 4, "voip": 4,
        "redes": 3, "business intelligence": 4, "power bi": 4, "pyme": 3, "empresa": 1,
    },
    "proximity": ["colombia", "bogotá", "bogota", "medellín", "medellin", "cali", "pereira",
                  "cartago", "barranquilla", "latino", "hispan"],
    "keyword_terms": ["coaching", "desarrollo personal", "ciberseguridad", "voip", "base de datos"],
    "angles": {
        "crecimiento": "programas de actitud mental positiva para su crecimiento personal",
        "talleres": "talleres AMP para equipos y comunidades",
        "programas": "programas y mentorías AMP en español",
        "ciberseguridad": "diagnóstico de ciberseguridad para su empresa",
        "dba": "administración y respaldo de bases de datos",
        "redes_voip": "redes y telefonía VoIP con soporte",
        "bi": "tableros de inteligencia de negocios (BI)",
        "sla": "soporte TI con acuerdos de nivel de servicio (SLA)",
    },
    "default_angle": "coaching AMP y servicios de tecnología Cibernettic",
    "client_types": {"ciberseguridad": "empresa", "dba": "empresa", "redes_voip": "empresa",
                     "bi": "empresa", "sla": "empresa", "talleres": "empresa"},
    "default_client_type": "persona",
    "social": {
        "hashtags": "#ActitudMentalPositiva #CrecimientoPersonal #Coaching #Ciberseguridad #Pymes",
        "profile": {
            "business_name": "AMP · Actitud Mental Positiva",
            "tagline": "Coaching en español para una actitud mental positiva",
            "website": "",
            "city": "",
            "state": "Colombia",
            "services": "Programas de coaching, talleres y mentorías de crecimiento personal",
            "target_audience": "Personas que buscan crecimiento personal, equipos de trabajo, comunidad hispana",
            "style_keywords": "Positivo, Cercano, Motivador, Práctico",
            "brand_colors": "#b8960c, #1a1a1a, #faf9f7",
            "owner_name": "Juan Diego Giraldo",
            "service_area": "Colombia y comunidad hispana (online)",
        },
        "profiles_by_business": {
            "cibernettic": {
                "business_name": "Cibernettic",
                "tagline": "Ciberseguridad, datos y redes para pymes",
                "website": "",
                "city": "",
                "state": "Colombia",
                "services": "Ciberseguridad, administración de bases de datos (DBA), redes y VoIP, inteligencia de negocios (BI), soporte con SLA",
                "target_audience": "Pymes que necesitan seguridad, datos confiables y redes estables",
                "style_keywords": "Confiable, Técnico, Claro, Seguro",
                "brand_colors": "#1f6feb, #1a1a1a, #faf9f7",
                "owner_name": "Juan Diego Giraldo",
                "service_area": "Colombia",
            },
        },
        "business_profiles": [
            {"business_key": "amp", "business_name": "AMP · Actitud Mental Positiva",
             "tagline": "Coaching en español",
             "bio_short": "Coaching y talleres de actitud mental positiva | En español",
             "category": "Coach", "city": "", "state": "Colombia"},
            {"business_key": "cibernettic", "business_name": "Cibernettic",
             "tagline": "Ciberseguridad, datos y redes",
             "bio_short": "Ciberseguridad • DBA • Redes/VoIP • BI • SLA para pymes",
             "category": "Servicios de TI", "city": "", "state": "Colombia"},
        ],
    },
    "campaigns": [
        {
            "name": "AMP — Invitación a talleres de crecimiento personal",
            "description": "Personas que buscan crecimiento personal: invitación a talleres y programas AMP en español.",
            "business_unit": "amp", "target_type": "crecimiento_personal",
            "steps": [
                {"step_number": 1, "step_type": "email", "delay_days": 0,
                 "subject": "{first_name}, una invitación para cultivar una actitud mental positiva",
                 "body_template": (
                     "Hola {first_name},\n\n"
                     "Soy Juan Diego Giraldo, de AMP · Actitud Mental Positiva. Acompaño a "
                     "personas que quieren crecer, ordenar sus metas y sostener una mentalidad "
                     "positiva en el día a día.\n\n"
                     "Tenemos talleres y programas en español. ¿Le gustaría recibir las "
                     "próximas fechas?\n\n"
                     "Un abrazo,\nJuan Diego · AMP")},
                {"step_number": 2, "step_type": "follow_up_email", "delay_days": 4,
                 "subject": "Re: talleres AMP",
                 "body_template": (
                     "Hola {first_name},\n\n"
                     "Retomo mi invitación. Si quiere, conversamos 15 minutos para ver qué "
                     "programa le sirve más en este momento.\n\n"
                     "Un abrazo,\nJuan Diego · AMP")},
                {"step_number": 3, "step_type": "phone_script", "delay_days": 9, "is_manual": True,
                 "subject": "Mensaje de WhatsApp a {first_name}",
                 "body_template": (
                     "GUION:\n\"Hola {first_name}, soy Juan Diego de AMP. Te escribí sobre los "
                     "talleres de actitud mental positiva. ¿Te comparto las próximas fechas?\"")},
            ],
        },
        {
            "name": "AMP — Talleres para equipos de trabajo",
            "description": "Empresas y organizaciones: talleres de actitud mental positiva para sus equipos.",
            "business_unit": "amp", "target_type": "talleres_empresas",
            "steps": [
                {"step_number": 1, "step_type": "email", "delay_days": 0,
                 "subject": "Talleres de actitud mental positiva para el equipo de {business}",
                 "body_template": (
                     "Hola {first_name},\n\n"
                     "En AMP diseñamos talleres en español para equipos que quieren mejorar su "
                     "comunicación, motivación y bienestar. ¿Podemos conversar sobre lo que "
                     "necesita {business}?\n\n"
                     "Saludos,\nJuan Diego Giraldo · AMP")},
                {"step_number": 2, "step_type": "follow_up_email", "delay_days": 5,
                 "subject": "Re: talleres para {business}",
                 "body_template": (
                     "Hola {first_name},\n\n"
                     "Quedo atento por si le interesa una propuesta de taller a la medida "
                     "para su equipo.\n\n"
                     "Saludos,\nJuan Diego Giraldo · AMP")},
            ],
        },
        {
            "name": "Cibernettic — Diagnóstico de ciberseguridad para pymes",
            "description": "Pymes que necesitan proteger su información: diagnóstico de ciberseguridad.",
            "business_unit": "cibernettic", "target_type": "pymes_ciberseguridad",
            "steps": [
                {"step_number": 1, "step_type": "email", "delay_days": 0,
                 "subject": "¿Qué tan protegida está la información de {business}?",
                 "body_template": (
                     "Hola {first_name},\n\n"
                     "En Cibernettic ayudamos a pymes a proteger su información: revisión de "
                     "accesos, respaldos, correo y red. Proponemos empezar con un diagnóstico "
                     "para identificar los riesgos principales.\n\n"
                     "¿Le interesa agendar una conversación?\n\n"
                     "Saludos,\nEquipo Cibernettic")},
                {"step_number": 2, "step_type": "follow_up_email", "delay_days": 4,
                 "subject": "Re: ciberseguridad para {business}",
                 "body_template": (
                     "Hola {first_name},\n\n"
                     "Retomo mi mensaje. Si su equipo ya tuvo un incidente o le preocupa el "
                     "ransomware, con gusto le explicamos cómo trabajamos.\n\n"
                     "Saludos,\nEquipo Cibernettic")},
                {"step_number": 3, "step_type": "phone_script", "delay_days": 8, "is_manual": True,
                 "subject": "Llamar a {first_name} en {business}",
                 "body_template": (
                     "GUION:\n\"Hola {first_name}, le habla [nombre] de Cibernettic. Le escribí "
                     "sobre un diagnóstico de ciberseguridad para {business}. ¿Quién maneja hoy "
                     "la seguridad y los respaldos en su empresa?\"\n\n"
                     "PUNTOS CLAVE:\n- Ciberseguridad y respaldos\n- Bases de datos (DBA)\n"
                     "- Redes y VoIP\n- BI\n- Soporte con SLA")},
            ],
        },
        {
            "name": "Cibernettic — Datos, redes/VoIP y BI con SLA",
            "description": "Pymes que necesitan administración de bases de datos, redes/VoIP o tableros de BI con soporte.",
            "business_unit": "cibernettic", "target_type": "pymes_datos_dba",
            "steps": [
                {"step_number": 1, "step_type": "email", "delay_days": 0,
                 "subject": "Bases de datos, redes y BI para {business}",
                 "body_template": (
                     "Hola {first_name},\n\n"
                     "Cibernettic administra bases de datos (DBA), redes y telefonía VoIP, y "
                     "construye tableros de inteligencia de negocios (BI), con soporte bajo "
                     "acuerdos de nivel de servicio (SLA).\n\n"
                     "¿Le sirve una llamada corta para revisar sus necesidades?\n\n"
                     "Saludos,\nEquipo Cibernettic")},
                {"step_number": 2, "step_type": "follow_up_email", "delay_days": 5,
                 "subject": "Re: datos y redes para {business}",
                 "body_template": (
                     "Hola {first_name},\n\n"
                     "Quedo atento. Podemos empezar por lo más urgente: respaldos, rendimiento "
                     "de la base de datos o estabilidad de la red.\n\n"
                     "Saludos,\nEquipo Cibernettic")},
            ],
        },
    ],
}

_PROFILES = {"maxine": _MAXINE, "amp": _AMP}


def trade_profile(edition: Optional[str] = None) -> Optional[dict]:
    """The family edition's trade profile, or None on the workroom build."""
    return _PROFILES.get((edition or _edition()).strip().lower())


def public_profile(edition: Optional[str] = None) -> dict:
    """What the frontend needs (no campaign bodies)."""
    prof = trade_profile(edition)
    if not prof:
        return {"edition": (edition or _edition()) or "workroom", "family": False}
    return {
        "edition": prof["edition"],
        "family": True,
        "title": prof["title"],
        "subtitle": prof["subtitle"],
        "default_unit": prof["default_unit"],
        "business_units": prof["business_units"],
        "fit_tags": [{k: v for k, v in t.items()} for t in prof["fit_tags"]],
        "hashtags": prof["social"]["hashtags"],
    }


def fit_tags_for(text: str, edition: Optional[str] = None) -> list[str]:
    prof = trade_profile(edition)
    if not prof:
        return []
    low = (text or "").lower()
    return [t["key"] for t in prof["fit_tags"] if any(k in low for k in t["keywords"])]


def social_default_profile(business_slug: str = "", edition: Optional[str] = None) -> Optional[dict]:
    prof = trade_profile(edition)
    if not prof:
        return None
    social = prof["social"]
    base = dict(social["profile"])
    override = (social.get("profiles_by_business") or {}).get((business_slug or "").strip().lower())
    if override:
        base.update(override)
    return base
