from datetime import datetime, timezone, timedelta
import json
import os
import time
import urllib.parse
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


# ---------------------------------------------------------
# ZONA HORARIA COLOMBIA (UTC-5)
# ---------------------------------------------------------
COT = timezone(timedelta(hours=-5))

# ---------------------------------------------------------
# ID DEL GOOGLE SHEET
# ---------------------------------------------------------
SPREADSHEET_ID = "1CvPEtDspm7g3T7yXDluEUD7kGyWH5abNAP1nkalX6sI"

# ---------------------------------------------------------
# ARCHIVO DE PERSISTENCIA LOCAL PARA LA BITÁCORA
# ---------------------------------------------------------
BITACORA_FILE = "bitacora_storage.json"

def cargar_bitacora_local():
    if os.path.exists(BITACORA_FILE):
        try:
            with open(BITACORA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def guardar_bitacora_local(mensajes):
    try:
        with open(BITACORA_FILE, "w", encoding="utf-8") as f:
            json.dump(mensajes, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# ---------------------------------------------------------
# LISTA DE INVOLUCRADOS (EMISORES Y RECEPTORES)
# ---------------------------------------------------------
LISTA_EMISORES = [
    "Jeison Altamar",
    "Nicolas Arevalo",
    "Jhojan Pasachoa",
    "Sonia Gonzales"
]

LISTA_RECEPTORES = [
    "Todos",
    "Jeison Altamar",
    "Nicolas Arevalo",
    "Jhojan Pasachoa",
    "Sonia Gonzales"
]

# ---------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Tablero de Control - Laboratorio", page_icon="📊", layout="wide"
)

# ---------------------------------------------------------
# ESTADO GLOBAL COMPARTIDO (Servidor / Entre Usuarios)
# ---------------------------------------------------------
@st.cache_resource
def obtener_estado_global():
    mensajes_guardados = cargar_bitacora_local()
    return {
        "mensajes_bitacora": mensajes_guardados, # Historial persistido de chat de bitácora
        "cargado_gsheet": False,                 # Bandera de lectura inicial desde Google Sheets
    }

ESTADO_GLOBAL = obtener_estado_global()

# ESTADOS DE SESIÓN LOCALES (INDEPENDIENTES POR NAVEGADOR / PC)
if "page_index" not in st.session_state:
    st.session_state.page_index = 0
if "last_switch_time" not in st.session_state:
    st.session_state.last_switch_time = time.time()
if "search_input" not in st.session_state:
    st.session_state.search_input = ""
if "manual_nav_bonus" not in st.session_state:
    st.session_state.manual_nav_bonus = 0
if "notif_enabled" not in st.session_state:
    st.session_state.notif_enabled = True
if "sound_enabled" not in st.session_state:
    st.session_state.sound_enabled = True
if "session_start_time" not in st.session_state:
    st.session_state.session_start_time = time.time()

if "prog_day_page" not in st.session_state:
    st.session_state.prog_day_page = 0
if "prog_day_last_switch" not in st.session_state:
    st.session_state.prog_day_last_switch = time.time()
if "alert_filter" not in st.session_state:
    st.session_state.alert_filter = "TODAS"

# MEMORIA LOCAL DE EMISOR POR NAVEGADOR
if "emisor_local" not in st.session_state:
    st.session_state.emisor_local = LISTA_EMISORES[0]


# ---------------------------------------------------------
# ESTILOS MODO OSCURO + FIX DE VISIBILIDAD DE INPUTS & TOGGLES
# ---------------------------------------------------------
st.markdown(
    """
<style>
    /* OCULTAR ENCABEZADOS Y AJUSTAR CONTENEDOR PRINCIPAL */
    header, [data-testid="stHeader"] { display: none !important; }
    .block-container { 
        padding-top: 0.3rem !important; 
        padding-bottom: 0.2rem !important; 
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    .stApp { background-color: #0B1120; color: #F3F4F6; font-size: 14px; }

    /* FIX DE VISIBILIDAD EN INPUTS, TEXTAREAS Y SELECTBOXES */
    input, textarea, select {
        color: #FFFFFF !important;
        background-color: #1F2937 !important;
    }
    .stTextInput input, .stTextArea textarea {
        color: #FFFFFF !important;
        background-color: #1F2937 !important;
        border: 1px solid #374151 !important;
        border-radius: 6px !important;
    }
    div[data-baseweb="select"] > div {
        background-color: #1F2937 !important;
        color: #FFFFFF !important;
        border: 1px solid #374151 !important;
    }
    div[data-baseweb="popover"] *, div[role="listbox"] * {
        background-color: #111827 !important;
        color: #FFFFFF !important;
    }

    /* CONTROLES COMPACTOS Y DELGADOS EN BITÁCORA PARA AHORRAR ESPACIO */
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        min-height: 26px !important;
        height: 26px !important;
        padding-top: 0px !important;
        padding-bottom: 0px !important;
        padding-left: 6px !important;
        padding-right: 6px !important;
        font-size: 11px !important;
    }
    div[data-testid="stSelectbox"] div[data-baseweb="select"] * {
        font-size: 11px !important;
    }

    /* BANNER SUPERIOR DE ALERTA CRÍTICA */
    @keyframes pulse-banner {
        0% { box-shadow: 0 0 10px rgba(239, 68, 68, 0.5); }
        50% { box-shadow: 0 0 25px rgba(239, 68, 68, 0.95); }
        100% { box-shadow: 0 0 10px rgba(239, 68, 68, 0.5); }
    }
    .top-urgent-banner {
        background: linear-gradient(90deg, #DC2626 0%, #991B1B 100%);
        color: #FFFFFF;
        padding: 6px 14px;
        border-radius: 6px;
        margin-bottom: 8px;
        font-weight: 800;
        text-align: center;
        font-size: 13.5px;
        letter-spacing: 0.5px;
        border: 1px solid #EF4444;
        animation: pulse-banner 1.5s infinite;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    /* TARJETAS KPI */
    .kpi-card {
        background-color: #111827;
        border: 1px solid #1F2937;
        border-radius: 6px;
        padding: 6px 10px;
        text-align: center;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.4);
    }
    .kpi-title {
        color: #9CA3AF;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        margin-bottom: 1px;
    }
    .kpi-value { color: #FFFFFF; font-size: 22px; font-weight: 800; line-height: 1.1; }

    /* TARJETAS DE PROGRESO DE ETAPA */
    .progress-order-card {
        background-color: #111827;
        border: 1px solid #1F2937;
        border-radius: 4px;
        padding: 3px 6px;
        margin-bottom: 2px;
    }

    /* CONTROLES Y BOTONES GENERALES ESTÁNDAR */
    div.stButton > button {
        background-color: #1E293B !important;
        color: #38BDF8 !important;
        border: 1px solid #3B82F6 !important;
        border-radius: 5px !important;
        font-weight: 700 !important;
        font-size: 11px !important;
        padding: 1px 4px !important;
        width: 100% !important;
        height: 26px !important;
        min-height: 26px !important;
        transition: all 0.2s ease-in-out !important;
    }
    div.stButton > button:hover {
        background-color: #2563EB !important;
        color: #FFFFFF !important;
        border-color: #60A5FA !important;
        cursor: pointer !important;
        box-shadow: 0 0 8px rgba(59, 130, 246, 0.5) !important;
    }

    /* SELECTOR SEGMENTADO MODO OSCURO (RADIO BUTTONS) */
    div[data-testid="stRadio"] > div {
        display: flex;
        flex-direction: row;
        background-color: #111827;
        border: 1px solid #374151;
        border-radius: 6px;
        padding: 2px;
        gap: 3px;
    }
    div[data-testid="stRadio"] label {
        flex: 1;
        text-align: center;
        background-color: #1F2937;
        border-radius: 4px;
        padding: 3px 6px !important;
        font-size: 11px !important;
        font-weight: 700 !important;
        color: #D1D5DB !important;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    /* ESTILOS DE MÓDULO CHAT / BITÁCORA - OPTIMIZACIÓN DE ESPACIO */
    .chat-container {
        max-height: 420px;
        overflow-y: auto;
        padding-right: 4px;
        display: flex;
        flex-direction: column;
        gap: 4px;
    }

    .msg-card-normal {
        background: #111827;
        border-left: 4px solid #10B981;
        border-radius: 6px;
        padding: 4px 8px;
        border-top: 1px solid #1F2937;
        border-right: 1px solid #1F2937;
        border-bottom: 1px solid #1F2937;
    }

    .msg-card-auditoria {
        background: #161D2F;
        border-left: 4px solid #F59E0B;
        border: 1px solid #F59E0B;
        border-radius: 6px;
        padding: 4px 8px;
        box-shadow: 0 0 8px rgba(245, 158, 11, 0.2);
    }

    /* ESTADOS URGENCIA 4 MINUTOS */
    .msg-card-urgente-verde {
        background: linear-gradient(180deg, #064E3B 0%, #111827 100%);
        border: 2px solid #10B981;
        border-radius: 6px;
        padding: 4px 8px;
        box-shadow: 0 0 10px rgba(16, 185, 129, 0.4);
    }

    .msg-card-urgente-naranja {
        background: linear-gradient(180deg, #78350F 0%, #111827 100%);
        border: 2px solid #F59E0B;
        border-radius: 6px;
        padding: 4px 8px;
        box-shadow: 0 0 12px rgba(245, 158, 11, 0.5);
    }

    @keyframes pulse-urgente {
        0% { border-color: #EF4444; box-shadow: 0 0 5px rgba(239, 68, 68, 0.4); }
        50% { border-color: #FCA5A5; box-shadow: 0 0 16px rgba(239, 68, 68, 0.9); }
        100% { border-color: #EF4444; box-shadow: 0 0 5px rgba(239, 68, 68, 0.4); }
    }

    .msg-card-urgente-rojo {
        background: linear-gradient(180deg, #450A0A 0%, #111827 100%);
        border: 2px solid #EF4444;
        animation: pulse-urgente 1.2s infinite;
        border-radius: 6px;
        padding: 4px 8px;
    }

    .msg-card-atendido {
        background: #0D1520;
        border-left: 4px solid #10B981;
        border: 1px solid #1F2937;
        border-radius: 6px;
        padding: 4px 8px;
        opacity: 0.95;
    }

    .badge-prio-normal {
        background-color: rgba(16, 185, 129, 0.2);
        color: #A7F3D0;
        border: 1px solid #10B981;
        font-size: 10px;
        font-weight: 700;
        padding: 1px 5px;
        border-radius: 4px;
    }

    .badge-prio-auditoria {
        background-color: rgba(245, 158, 11, 0.25);
        color: #FDE68A;
        border: 1px solid #F59E0B;
        font-size: 10px;
        font-weight: 800;
        padding: 1px 5px;
        border-radius: 4px;
        letter-spacing: 0.5px;
    }

    /* ESTILO DE RESPUESTAS (CHAT SECUNDARIO) */
    .reply-box {
        background: #1F2937;
        border-left: 3px solid #3B82F6;
        border-radius: 4px;
        padding: 4px 6px;
        margin-top: 4px;
        font-size: 11.5px;
    }

    /* ANIMACIÓN PARPADEO TABLA CORRECCIÓN */
    @keyframes pulse-correccion {
        0% { background-color: rgba(239, 68, 68, 0.12); }
        50% { background-color: rgba(239, 68, 68, 0.30); }
        100% { background-color: rgba(239, 68, 68, 0.12); }
    }
    .row-correccion {
        animation: pulse-correccion 2.2s infinite !important;
        border-left: 4px solid #EF4444 !important;
    }

    /* SCROLLBARS */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #111827; border-radius: 4px; }
    ::-webkit-scrollbar-thumb { background: #374151; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #3B82F6; }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# SISTEMA DE NOTIFICACIONES DE ESCRITORIO MEJORADAS & AUDIO
# ---------------------------------------------------------
def solicitar_permisos_notificaciones_js():
    components.html(
        """
        <script>
        (function() {
            var parentWin = window.parent || window;
            var navNotif = parentWin.Notification || window.Notification;
            if (navNotif) {
                navNotif.requestPermission().then(function(perm) {
                    if (perm === "granted") {
                        alert("✅ Notificaciones del sistema y sonido activados correctamente.");
                    } else {
                        alert("⚠️ Debes permitir las notificaciones en el navegador para recibir las alertas flotantes.");
                    }
                });
            }
            try {
                var AudioCtx = parentWin.AudioContext || parentWin.webkitAudioContext;
                if (AudioCtx) {
                    var ctx = new AudioCtx();
                    if (ctx.state === 'suspended') ctx.resume();
                }
            } catch(e) {}
        })();
        </script>
        """,
        height=0,
        width=0,
    )

def emitir_notificacion_y_audio_js(msg_id, emisor, receptor, prioridad, contenido, sound_enabled):
    contenido_esc = contenido.replace('"', '\\"').replace('\n', ' ')
    emisor_esc = emisor.replace('"', '\\"')
    receptor_esc = receptor.replace('"', '\\"')

    components.html(
        f"""
        <script>
        (function() {{
            var parentWin = window.parent || window;
            var navNotif = parentWin.Notification || window.Notification;

            if (!parentWin._processedMsgs) {{
                parentWin._processedMsgs = {{}};
            }}

            var msgId = "{msg_id}";
            var prioridad = "{prioridad}";
            var emisor = "{emisor_esc}";
            var receptor = "{receptor_esc}";
            var contenido = "{contenido_esc}";
            var soundEnabled = {str(sound_enabled).lower()};

            if (msgId && !parentWin._processedMsgs[msgId]) {{
                parentWin._processedMsgs[msgId] = true;

                // 1. NOTIFICACIÓN DE ESCRITORIO BONITA EN SEGUNDO PLANO (FORMATO COMPACTO)
                if (navNotif && navNotif.permission === "granted") {{
                    var titulo = (prioridad === 'Urgente') ? "🚨 ¡ALERTA URGENTE DE LABORATORIO!" : "💬 NUEVA NOVEDAD DE BITÁCORA";
                    var cuerpo = emisor + " ➔ " + receptor + "\\n📝 " + contenido;
                    var icono = (prioridad === 'Urgente') 
                        ? "https://cdn-icons-png.flaticon.com/512/1827/1827504.png"
                        : "https://cdn-icons-png.flaticon.com/512/3718/3718167.png";

                    try {{
                        var notif = new navNotif(titulo, {{
                            body: cuerpo,
                            icon: icono,
                            badge: icono,
                            tag: msgId,
                            renotify: true,
                            requireInteraction: (prioridad === 'Urgente')
                        }});
                    }} catch(e) {{ console.error("Error en notificación:", e); }}
                }}

                // 2. REPRODUCIR SONIDO SOLO SI ES URGENTE
                if (prioridad === "Urgente" && soundEnabled) {{
                    try {{
                        var AudioCtx = parentWin.AudioContext || parentWin.webkitAudioContext;
                        if (AudioCtx) {{
                            var ctx = new AudioCtx();
                            if (ctx.state === 'suspended') {{
                                ctx.resume();
                            }}
                            var now = ctx.currentTime;
                            var freqs = [880, 1200, 880, 1200, 1500];
                            freqs.forEach(function(freq, i) {{
                                var t = now + (i * 0.14);
                                var osc = ctx.createOscillator();
                                var gain = ctx.createGain();
                                osc.type = 'sawtooth';
                                osc.frequency.setValueAtTime(freq, t);
                                gain.gain.setValueAtTime(0.5, t);
                                gain.gain.exponentialRampToValueAtTime(0.001, t + 0.12);
                                osc.connect(gain);
                                gain.connect(ctx.destination);
                                osc.start(t);
                                osc.stop(t + 0.13);
                            }});
                        }}
                    }} catch(e) {{ console.error("Error al reproducir audio:", e); }}
                }}
            }}
        }})();
        </script>
        """,
        height=0,
        width=0,
    )


# ---------------------------------------------------------
# FUNCIONES AUXILIARES Y PARSER
# ---------------------------------------------------------
def limpiar_texto(val):
    if pd.isna(val) or val is None:
        return ""
    val_str = str(val).strip()
    if val_str.endswith(".0"):
        val_str = val_str[:-2]
    return val_str


def leer_hoja_google(nombre_hoja, header_none=False):
    nombre_enc = urllib.parse.quote(nombre_hoja)
    nocache = int(time.time() * 1000)
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={nombre_enc}&_cb={nocache}"
    if header_none:
        return pd.read_csv(url, header=None, keep_default_na=False)
    return pd.read_csv(url, keep_default_na=False)


def parsear_fecha(val):
    if pd.isna(val) or val is None:
        return None
    if isinstance(val, (datetime, pd.Timestamp)):
        return val.date()

    val_str = str(val).strip()
    if not val_str or val_str.lower() in ["nan", "none", "nat", "null"] or val_str.startswith("#"):
        return None

    try:
        num_val = float(val_str)
        if 30000 < num_val < 70000:
            dt = pd.to_datetime(num_val, unit="D", origin="1899-12-30")
            return dt.date()
    except (ValueError, TypeError):
        pass

    val_clean = val_str.split(" ")[0].strip()

    try:
        dt = pd.to_datetime(val_clean, dayfirst=False, errors="coerce")
        if pd.notna(dt):
            return dt.date()
    except Exception:
        pass

    try:
        dt = pd.to_datetime(val_clean, dayfirst=True, errors="coerce")
        if pd.notna(dt):
            return dt.date()
    except Exception:
        pass

    return None


def calcular_progreso_orden(row):
    progreso = 25
    cer = str(row.get("Cer firmado", row.get("CER FIRMADO", ""))).strip().upper()
    env = str(row.get("Enviado", row.get("ENVIADO", ""))).strip().upper()

    faltantes = []
    if cer in ["SI", "SÍ"]:
        progreso += 25
    else:
        faltantes.append("CER Firmado")

    if env in ["SI", "SÍ"]:
        progreso += 25
    else:
        faltantes.append("Enviado")

    crm_sal = str(row.get("CRM salida", row.get("CRM SALIDA", ""))).strip().upper()
    if crm_sal in ["SI", "SÍ"]:
        progreso += 25
    else:
        faltantes.append("CRM Salida")

    texto_falta = f"Falta: {', '.join(faltantes)}" if faltantes else "¡Completo! 🎉"
    return min(100, progreso), texto_falta


def cargar_datos_gsheets():
    try:
        df_proceso_raw = leer_hoja_google("C. Proceso órdenes", header_none=True)
        df_notas_raw = leer_hoja_google("NOTAS DEL DIA", header_none=True)

        df_proceso = pd.DataFrame()
        if df_proceso_raw is not None and not df_proceso_raw.empty:
            header_idx = None
            for idx, row in df_proceso_raw.iterrows():
                row_str = " ".join(row.dropna().astype(str)).upper()
                if "FECHA" in row_str and ("ORDEN" in row_str or "CER" in row_str):
                    header_idx = idx
                    break

            if header_idx is not None:
                df_proceso = df_proceso_raw.iloc[header_idx + 1 :].copy()
                df_proceso.columns = [str(c).strip() for c in df_proceso_raw.iloc[header_idx].values]
            else:
                df_proceso = df_proceso_raw.iloc[1:].copy()
                df_proceso.columns = [str(c).strip() for c in df_proceso_raw.iloc[0].values]

        df_notas = pd.DataFrame()
        if df_notas_raw is not None and not df_notas_raw.empty:
            header_n_idx = None
            for idx, row in df_notas_raw.iterrows():
                row_str = " ".join(row.dropna().astype(str)).upper()
                if any(k in row_str for k in ["DESCRIPCIÓN", "DESCRIPCION", "PRIORIDA", "TIPO", "NOTA"]):
                    header_n_idx = idx
                    break

            if header_n_idx is not None:
                df_notas = df_notas_raw.iloc[header_n_idx + 1 :].copy()
                df_notas.columns = df_notas_raw.iloc[header_n_idx].values
            else:
                df_notas = df_notas_raw.copy()

            df_notas.columns = [str(col).strip() for col in df_notas.columns]
            df_notas = df_notas.replace("", np.nan).dropna(how="all")

        return df_proceso, df_notas, "Conectado correctamente"

    except Exception as e:
        return None, None, f"Error al conectar con Google Sheets: {str(e)}"


def render_dark_table(df_page):
    if df_page.empty:
        return "<div style='color: #9CA3AF; text-align: center; padding: 10px; font-size: 13px;'>Sin datos o registros coincidentes.</div>"

    # Filtrar cualquier columna oculta para que no aparezca en la cabecera visual
    headers = [c for c in list(df_page.columns) if "OCULT" not in str(c).upper()]

    col_resp = next((c for c in headers if "RESP" in c.upper()), None)
    col_cer = next((c for c in headers if "CER" in c.upper() and "FIRM" in c.upper()), None)
    col_env = next((c for c in headers if "ENV" in c.upper()), None)
    col_crm_salida = next((c for c in headers if "CRM" in c.upper() and "SALIDA" in c.upper()), None)
    col_orden = next((c for c in headers if "ORDEN" in c.upper()), None)

    html = '<div style="overflow-x: auto; border: 1px solid #1F2937; border-radius: 6px; background-color: #111827; margin-bottom: 4px;"><table style="width: 100%; border-collapse: collapse; color: #F3F4F6; font-size: 12.5px; text-align: left;"><thead><tr style="background-color: #1F2937; color: #9CA3AF; font-weight: 700; text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px;">'

    for h in headers:
        if h == col_resp:
            html += f'<th style="padding: 5px 4px; border-bottom: 1px solid #374151; width: 75px; text-align: center; white-space: nowrap;">{h}</th>'
        else:
            html += f'<th style="padding: 5px 8px; border-bottom: 1px solid #374151;">{h}</th>'
    html += "</tr></thead><tbody>"

    for idx, row in df_page.iterrows():
        cer_val = str(row[col_cer]).strip().upper() if col_cer and pd.notna(row[col_cer]) else ""

        es_correccion = "CORREC" in cer_val
        cer_es_si = cer_val in ["SI", "SÍ"]
        
        # CORRECCIÓN SOLICITADA:
        # Atascada SOLO si Cer firmado tiene algún texto, es diferente de SI y no es corrección.
        # Si está en blanco (""), NO sale atascada.
        es_atascada = (cer_val != "") and (not cer_es_si) and (not es_correccion)

        if es_correccion:
            tr_style = 'style="border-bottom: 1px solid #EF4444;" class="row-correccion"'
        elif es_atascada:
            tr_style = 'style="border-bottom: 1px solid #F59E0B; background-color: rgba(245, 158, 11, 0.08); border-left: 4px solid #F59E0B;"'
        else:
            tr_style = 'style="border-bottom: 1px solid #1F2937;"'

        html += f"<tr {tr_style}>"
        for h in headers:
            val = limpiar_texto(row[h])
            val_upper = val.upper()

            td_style = "padding: 4px 8px;"

            if h == col_resp:
                td_style = "padding: 4px 4px; text-align: center; width: 75px; white-space: nowrap;"
                badge = f'<span style="color: #38BDF8; font-weight: 700; font-size: 11.5px;">{val}</span>'
            elif h == col_orden and es_atascada:
                badge = f'{val} <span style="background-color: rgba(245, 158, 11, 0.25); color: #FBBF24; border: 1px solid #F59E0B; padding: 1px 5px; border-radius: 4px; font-weight: 700; font-size: 10px;" title="Certificado pendiente de firma">⚠️ Atascada</span>'
            elif val_upper in ["SI", "SÍ"]:
                badge = '<span style="background-color: rgba(16, 185, 129, 0.2); color: #A7F3D0; border: 1px solid #10B981; padding: 1px 6px; border-radius: 4px; font-weight: 700; font-size: 10.5px;">Si</span>'
            elif val != "":
                if any(k in val_upper for k in ["CORREC", "ERROR", "RECHAZ", "CANCEL"]):
                    badge = f'<span style="background-color: rgba(239, 68, 68, 0.25); color: #FCA5A5; border: 1px solid #EF4444; padding: 1px 6px; border-radius: 4px; font-weight: 700; font-size: 10.5px;">{val} ⚠</span>'
                elif h in [col_env, col_crm_salida, col_cer] or any(k in val_upper for k in ["APROBAC", "PENDIENTE", "P.", "FIRMAR", "REVISAR"]):
                    badge = f'<span style="background-color: rgba(245, 158, 11, 0.2); color: #FDE68A; border: 1px solid #F59E0B; padding: 1px 6px; border-radius: 4px; font-weight: 600; font-size: 10.5px;">{val}</span>'
                else:
                    badge = val
            else:
                badge = ""

            html += f'<td style="{td_style}">{badge}</td>'
        html += "</tr>"

    html += "</tbody></table></div>"
    return html


# ---------------------------------------------------------
# ORDENAMIENTO DE MENSAJES POR PRIORIDAD Y TIEMPO
# ---------------------------------------------------------
def obtener_orden_mensaje(msg):
    prio_rank = {"Urgente": 1, "Auditoría": 2, "Normal": 3}
    estado_rank = {"Pendiente": 1, "Atendido": 2}

    st_rank = estado_rank.get(msg.get("estado", "Pendiente"), 1)
    pr_rank = prio_rank.get(msg.get("prioridad", "Normal"), 3)
    ts = msg.get("timestamp", 0)

    if st_rank == 1:
        return (1, pr_rank, ts)
    else:
        return (2, pr_rank, -ts)


# ---------------------------------------------------------
# RENDERIZADO DE NOVEDADES (BITÁCORA / CHAT Y RESPUESTAS)
# ---------------------------------------------------------
def render_chat_message_html(msg, cycle_sec=0, cycle_num=0):
    emisor = msg.get("emisor", "Jeison Altamar")
    receptor = msg.get("receptor", "Todos")
    prioridad = msg.get("prioridad", "Normal")
    contenido = msg.get("contenido", "")
    fecha_hora = msg.get("fecha_hora", "")
    estado = msg.get("estado", "Pendiente")
    usuario_enterado = msg.get("usuario_enterado", None)
    fecha_enterado = msg.get("fecha_enterado", None)
    respuestas = msg.get("respuestas", [])

    # CÁLCULO DE TIEMPO TRANSCURRIDO (DESDE CREACIÓN)
    now_curr = time.time()
    ts_msg = msg.get("timestamp", now_curr)
    elapsed_sec = max(0, int(now_curr - ts_msg))
    min_elapsed = elapsed_sec // 60
    if min_elapsed >= 60:
        hrs = min_elapsed // 60
        time_elapsed_str = f"⏱️ Hace {hrs}h {min_elapsed % 60}m"
    elif min_elapsed > 0:
        time_elapsed_str = f"⏱️ Hace {min_elapsed}m"
    else:
        time_elapsed_str = "⏱️ Hace un momento"

    # HTML DE RESPUESTAS HILADAS
    respuestas_html = ""
    if respuestas:
        respuestas_html += "<div style='margin-top: 6px; display: flex; flex-direction: column; gap: 4px;'>"
        for r in respuestas:
            respuestas_html += f'''
            <div class="reply-box">
                <div style="display: flex; justify-content: space-between; font-size: 10px; color: #9CA3AF; margin-bottom: 2px;">
                    <strong style="color: #60A5FA;">💬 {r.get("usuario")}</strong>
                    <span>{r.get("fecha_hora")}</span>
                </div>
                <div style="color: #E5E7EB;">{r.get("texto")}</div>
            </div>
            '''
        respuestas_html += "</div>"

    if prioridad == "Urgente":
        if estado == "Pendiente":
            min_exp = int(cycle_sec // 60)
            sec_exp = int(cycle_sec % 60)
            c_num_str = f" | Ciclo #{cycle_num + 1}" if cycle_num > 0 else ""

            if cycle_sec < 120:
                card_class = "msg-card-urgente-verde"
                prio_badge = f'<span style="background: rgba(16, 185, 129, 0.25); color: #A7F3D0; border: 1px solid #10B981; font-size: 10px; font-weight: 800; padding: 2px 6px; border-radius: 4px;">🟢 URGENTE ({min_exp}m {sec_exp:02d}s{c_num_str})</span>'
            elif cycle_sec < 180:
                card_class = "msg-card-urgente-naranja"
                prio_badge = f'<span style="background: rgba(245, 158, 11, 0.25); color: #FDE68A; border: 1px solid #F59E0B; font-size: 10px; font-weight: 800; padding: 2px 6px; border-radius: 4px;">🟡 ADVERTENCIA ({min_exp}m {sec_exp:02d}s{c_num_str})</span>'
            else:
                card_class = "msg-card-urgente-rojo"
                prio_badge = f'<span style="background: rgba(239, 68, 68, 0.35); color: #FCA5A5; border: 1px solid #EF4444; font-size: 10px; font-weight: 800; padding: 2px 6px; border-radius: 4px;">🔴 CRÍTICO / RE-ALERTA ({min_exp}m {sec_exp:02d}s{c_num_str})</span>'

            return f'''
            <div class="{card_class}">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    {prio_badge}
                    <span style="font-size: 10px; color: #F3F4F6; font-weight: 700;">{fecha_hora} ({time_elapsed_str})</span>
                </div>
                <div style="font-size: 11px; color: #9CA3AF; margin-bottom: 4px;">
                    <strong style="color: #F3F4F6;">De:</strong> {emisor} &nbsp;|&nbsp; <strong style="color: #F3F4F6;">Para:</strong> {receptor}
                </div>
                <div style="color: #FFFFFF; font-size: 12.5px; font-weight: 700; line-height: 1.3; margin-bottom: 4px;">
                    🚨 {contenido}
                </div>
                {respuestas_html}
            </div>
            '''
        else:
            return f'''
            <div class="msg-card-atendido">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px;">
                    <span style="background: rgba(16, 185, 129, 0.2); color: #A7F3D0; border: 1px solid #10B981; font-size: 9.5px; font-weight: 800; padding: 2px 6px; border-radius: 4px;">
                        ✓ REALIZADO / ATENDIDO
                    </span>
                    <span style="font-size: 10px; color: #9CA3AF;">{fecha_hora}</span>
                </div>
                <div style="font-size: 11px; color: #9CA3AF; margin-bottom: 2px;">
                    <strong style="color: #D1D5DB;">De:</strong> {emisor} &nbsp;|&nbsp; <strong style="color: #D1D5DB;">Para:</strong> {receptor}
                </div>
                <div style="color: #E5E7EB; font-size: 12px; font-weight: 500; line-height: 1.25;">
                    {contenido}
                </div>
                <div style="font-size: 9.5px; color: #34D399; margin-top: 4px; font-weight: 600;">
                    ✅ Realizado por: <strong>{usuario_enterado}</strong> a las {fecha_enterado}
                </div>
                {respuestas_html}
            </div>
            '''

    elif prioridad == "Auditoría":
        if estado == "Atendido":
            return f'''
            <div class="msg-card-atendido">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px;">
                    <span style="background: rgba(16, 185, 129, 0.2); color: #A7F3D0; border: 1px solid #10B981; font-size: 9.5px; font-weight: 800; padding: 2px 6px; border-radius: 4px;">
                        ✓ REALIZADO / AUDITADO
                    </span>
                    <span style="font-size: 10px; color: #9CA3AF;">{fecha_hora}</span>
                </div>
                <div style="font-size: 11px; color: #9CA3AF; margin-bottom: 2px;">
                    <strong style="color: #D1D5DB;">De:</strong> {emisor} &nbsp;|&nbsp; <strong style="color: #D1D5DB;">Para:</strong> {receptor}
                </div>
                <div style="color: #E5E7EB; font-size: 12px; font-weight: 500; line-height: 1.25;">
                    {contenido}
                </div>
                <div style="font-size: 9.5px; color: #34D399; margin-top: 4px; font-weight: 600;">
                    ✅ Realizado por: <strong>{usuario_enterado}</strong> a las {fecha_enterado}
                </div>
                {respuestas_html}
            </div>
            '''
        else:
            return f'''
            <div class="msg-card-auditoria">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <span class="badge-prio-auditoria">🟡 AUDITORÍA / CALIDAD</span>
                    <span style="font-size: 10px; color: #FDE68A; font-weight: 700;">{fecha_hora} ({time_elapsed_str})</span>
                </div>
                <div style="font-size: 11px; color: #9CA3AF; margin-bottom: 4px;">
                    <strong style="color: #F3F4F6;">De:</strong> {emisor} &nbsp;|&nbsp; <strong style="color: #F3F4F6;">Para:</strong> {receptor}
                </div>
                <div style="color: #F3F4F6; font-size: 12px; font-weight: 600; line-height: 1.3;">
                    {contenido}
                </div>
                {respuestas_html}
            </div>
            '''

    else:  # Normal
        if estado == "Atendido":
            return f'''
            <div class="msg-card-atendido">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px;">
                    <span style="background: rgba(16, 185, 129, 0.2); color: #A7F3D0; border: 1px solid #10B981; font-size: 9.5px; font-weight: 800; padding: 2px 6px; border-radius: 4px;">
                        ✓ REALIZADO
                    </span>
                    <span style="font-size: 10px; color: #9CA3AF;">{fecha_hora}</span>
                </div>
                <div style="font-size: 10.5px; color: #9CA3AF; margin-bottom: 3px;">
                    <strong style="color: #D1D5DB;">De:</strong> {emisor} &nbsp;|&nbsp; <strong style="color: #D1D5DB;">Para:</strong> {receptor}
                </div>
                <div style="color: #F3F4F6; font-size: 12px; font-weight: 500; line-height: 1.25;">
                    {contenido}
                </div>
                <div style="font-size: 9.5px; color: #34D399; margin-top: 4px; font-weight: 600;">
                    ✅ Realizado por: <strong>{usuario_enterado}</strong> a las {fecha_enterado}
                </div>
                {respuestas_html}
            </div>
            '''
        else:
            return f'''
            <div class="msg-card-normal">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px;">
                    <span class="badge-prio-normal">🟢 NORMAL</span>
                    <span style="font-size: 10px; color: #9CA3AF;">{fecha_hora} ({time_elapsed_str})</span>
                </div>
                <div style="font-size: 10.5px; color: #9CA3AF; margin-bottom: 3px;">
                    <strong style="color: #D1D5DB;">De:</strong> {emisor} &nbsp;|&nbsp; <strong style="color: #D1D5DB;">Para:</strong> {receptor}
                </div>
                <div style="color: #F3F4F6; font-size: 12px; font-weight: 500; line-height: 1.25;">
                    {contenido}
                </div>
                {respuestas_html}
            </div>
            '''


# ---------------------------------------------------------
# CALLBACKS
# ---------------------------------------------------------
def borrar_busqueda():
    st.session_state.search_input = ""


# ---------------------------------------------------------
# TABLERO DE CONTROL DINÁMICO
# ---------------------------------------------------------
@st.fragment(run_every=5)
def render_tablero_fluido():
    df_main, df_bitacora, info_estado = cargar_datos_gsheets()

    if "mensajes_bitacora" not in ESTADO_GLOBAL:
        ESTADO_GLOBAL["mensajes_bitacora"] = cargar_bitacora_local()

    # MIGRACIÓN DE MENSAJES EXISTENTES
    for m in ESTADO_GLOBAL["mensajes_bitacora"]:
        if "permitir_respuestas" not in m:
            m["permitir_respuestas"] = False
        if "mostrar_respuestas" not in m:
            m["mostrar_respuestas"] = False
        if "respuestas" not in m:
            m["respuestas"] = []

    if not ESTADO_GLOBAL.get("cargado_gsheet", False) and df_bitacora is not None and not df_bitacora.empty:
        col_p = next((c for c in df_bitacora.columns if any(k in str(c).upper() for k in ["PRIORI", "PO", "TIPO"])), None)
        col_d = next((c for c in df_bitacora.columns if any(k in str(c).upper() for k in ["DESCRIP", "NOTA", "AVISO"])), None)
        col_e = next((c for c in df_bitacora.columns if "ESTADO" in str(c).upper()), None)
        col_em = next((c for c in df_bitacora.columns if "DE" in str(c).upper() or "EMISOR" in str(c).upper()), None)
        col_rec = next((c for c in df_bitacora.columns if "PARA" in str(c).upper() or "RECEPTOR" in str(c).upper()), None)

        now_ts = time.time()
        cargados_nuevos = False
        for idx_b, r in df_bitacora.iterrows():
            d_val = str(r[col_d] if col_d else "").strip()
            if not d_val:
                continue
            
            p_val_raw = str(r[col_p] if col_p else "NORMAL").strip().upper()
            if "URG" in p_val_raw:
                prio_clean = "Urgente"
            elif "AUD" in p_val_raw or "CALID" in p_val_raw:
                prio_clean = "Auditoría"
            else:
                prio_clean = "Normal"

            e_val_raw = str(r[col_e] if col_e else "PENDIENTE").strip().upper()
            est_clean = "Atendido" if "ATEND" in e_val_raw or "COMPLET" in e_val_raw or "REALIZ" in e_val_raw else "Pendiente"
            
            emisor_raw = str(r[col_em]).strip() if col_em and str(r[col_em]).strip() in LISTA_EMISORES else "Jeison Altamar"
            receptor_raw = str(r[col_rec]).strip() if col_rec and str(r[col_rec]).strip() in LISTA_RECEPTORES else "Todos"

            msg_id_gs = f"gs_{idx_b}_{d_val[:15]}"
            if not any(m.get("id") == msg_id_gs for m in ESTADO_GLOBAL["mensajes_bitacora"]):
                ESTADO_GLOBAL["mensajes_bitacora"].append({
                    "id": msg_id_gs,
                    "emisor": emisor_raw,
                    "receptor": receptor_raw,
                    "prioridad": prio_clean,
                    "contenido": d_val,
                    "fecha_hora": datetime.now(COT).strftime("%d/%m/%Y %H:%M"),
                    "timestamp": now_ts,
                    "estado": est_clean,
                    "usuario_enterado": None,
                    "fecha_enterado": None,
                    "permitir_respuestas": False,
                    "mostrar_respuestas": False,
                    "respuestas": []
                })
                cargados_nuevos = True

        if cargados_nuevos:
            guardar_bitacora_local(ESTADO_GLOBAL["mensajes_bitacora"])
        ESTADO_GLOBAL["cargado_gsheet"] = True

    # VERIFICAR Y DISPARAR NOTIFICACIONES Y SONIDOS A CADA NAVEGADOR ABIERTO
    mensajes_bit = ESTADO_GLOBAL.get("mensajes_bitacora", [])
    if mensajes_bit:
        ultimo_msg = mensajes_bit[0]
        if ultimo_msg.get("timestamp", 0) >= (st.session_state.session_start_time - 10):
            if st.session_state.get("notif_enabled", True):
                emitir_notificacion_y_audio_js(
                    msg_id=ultimo_msg.get("id"),
                    emisor=ultimo_msg.get("emisor", "Sistema"),
                    receptor=ultimo_msg.get("receptor", "Todos"),
                    prioridad=ultimo_msg.get("prioridad", "Normal"),
                    contenido=ultimo_msg.get("contenido", ""),
                    sound_enabled=st.session_state.sound_enabled
                )

    # EVALUACIÓN DE MENSAJES URGENTES PENDIENTES
    urgentes_pendientes = [
        m for m in ESTADO_GLOBAL["mensajes_bitacora"]
        if m.get("prioridad") == "Urgente" and m.get("estado") == "Pendiente"
    ]
    cant_urgencias_activas = len(urgentes_pendientes)

    if cant_urgencias_activas > 0:
        st.markdown(
            f'''
            <div class="top-urgent-banner">
                <span>🚨 ATENCIÓN INMEDIATA: Hay {cant_urgencias_activas} novedad(es) URGENTE(S) sin atender en la Bitácora.</span>
                <span style="font-size: 11px; background: rgba(0,0,0,0.3); padding: 2px 8px; border-radius: 4px;">Atender abajo en Bitácora ⬇️</span>
            </div>
            ''',
            unsafe_allow_html=True
        )

    cols_deseadas = [
        "Fecha",
        "# Orden",
        "Responsables",
        "Cer firmado",
        "Enviado",
        "CRM salida",
        "Aprob. Comercial",
        "CRM cert.",
        "Oculto",
    ]
    df_vista = pd.DataFrame()
    df_ocultas = pd.DataFrame()
    df_hoy = pd.DataFrame()
    df_anteriores_incompletas = pd.DataFrame()

    total_hoy = 0
    hoy_dt = datetime.now(COT).date()
    fecha_activa_str = hoy_dt.strftime("%d/%m/%Y")

    total_reg = 0
    total_firm = 0
    total_env = 0
    total_pend = 0
    cant_atascadas = 0
    cant_correcciones = 0

    if df_main is not None and not df_main.empty:
        mapa_cols = {}
        cols_raw = list(df_main.columns)

        for idx, col in enumerate(cols_raw):
            c_upper = str(col).upper().strip()
            if "FECHA" in c_upper and "Fecha" not in mapa_cols.values():
                mapa_cols[col] = "Fecha"
            elif (("ORDEN" in c_upper or "ORD" in c_upper) and "# Orden" not in mapa_cols.values()):
                mapa_cols[col] = "# Orden"
            elif (("RESP" in c_upper or "RESPONSABLE" in c_upper or "ENCARGADO" in c_upper) and "Responsables" not in mapa_cols.values()):
                mapa_cols[col] = "Responsables"
            elif ("CER" in c_upper and "FIRM" in c_upper) and "Cer firmado" not in mapa_cols.values():
                mapa_cols[col] = "Cer firmado"
            elif "ENV" in c_upper and "Enviado" not in mapa_cols.values():
                mapa_cols[col] = "Enviado"
            elif ("CRM" in c_upper and "SAL" in c_upper) and "CRM salida" not in mapa_cols.values():
                mapa_cols[col] = "CRM salida"
            elif (("APROB" in c_upper or "COMER" in c_upper) and "Aprob. Comercial" not in mapa_cols.values()):
                mapa_cols[col] = "Aprob. Comercial"
            elif ("CRM" in c_upper and "CERT" in c_upper) and "CRM cert." not in mapa_cols.values():
                mapa_cols[col] = "CRM cert."
            # Mapea tanto si la columna se llama 'Oculto' como si se llama 'visible' en la hoja de Google Sheets
            elif ("OCULT" in c_upper or "VISIB" in c_upper) and "Oculto" not in mapa_cols.values():
                mapa_cols[col] = "Oculto"

        df_renamed = df_main.rename(columns=mapa_cols)

        col_fecha = "Fecha" if "Fecha" in df_renamed.columns else df_renamed.columns[0]
        df_renamed["_dt"] = df_renamed[col_fecha].apply(parsear_fecha)

        cols_existentes = [c for c in cols_deseadas if c in df_renamed.columns]
        df_vista = df_renamed[cols_existentes].copy()

        # MANEJO DE COLUMNA OCULTO / VISIBLE
        if "Oculto" in df_vista.columns:
            def _check_oculto(val):
                v = str(val).strip().upper()
                if not v or v in ["NAN", "NONE", "NULL"]:
                    return False
                if any(k in v for k in ["NO VIS", "OCULT", "TRUE", "1"]):
                    return True
                if v == "NO":  # Detecta 'No' o 'No visible'
                    return True
                return False

            es_oculta = df_vista["Oculto"].apply(_check_oculto)
            df_ocultas = df_vista[es_oculta].drop(columns=["Oculto"], errors="ignore").copy()
            df_vista = df_vista[~es_oculta].drop(columns=["Oculto"], errors="ignore").copy()
        else:
            df_ocultas = pd.DataFrame()

        total_reg = len(df_vista)

        if not df_vista.empty:
            col_cer_check = next((c for c in df_vista.columns if "CER" in c.upper()), None)
            
            for _, r_m in df_vista.iterrows():
                cer_m = str(r_m[col_cer_check]).strip().upper() if col_cer_check else ""
                
                if "CORREC" in cer_m:
                    cant_correcciones += 1
                elif cer_m != "" and cer_m not in ["SI", "SÍ"]: # REGLA: Atascado SOLO si tiene texto y es diferente a SI
                    cant_atascadas += 1

            # CONTEOS KPI
            col_cer = next((c for c in df_vista.columns if "CER" in c.upper()), None)
            col_env = next((c for c in df_vista.columns if "ENV" in c.upper()), None)

            if col_cer:
                df_vista["_firm"] = df_vista[col_cer].astype(str).str.strip().str.upper().isin(["SI", "SÍ"])
                total_firm = df_vista["_firm"].sum()

            if col_env:
                df_vista["_env"] = df_vista[col_env].astype(str).str.strip().str.upper().isin(["SI", "SÍ"])
                total_env = df_vista["_env"].sum()

            total_pend = max(0, total_reg - total_env)

            # FILTRADO DE ÓRDENES PARA KPI DE PROGRESO DEL DÍA
            df_renamed_valid = df_renamed[df_renamed["_dt"].notna()].copy()
            df_hoy = df_renamed_valid[df_renamed_valid["_dt"] == hoy_dt]
            df_anteriores_incompletas = df_renamed_valid[df_renamed_valid["_dt"] < hoy_dt]

            if not df_anteriores_incompletas.empty and col_env:
                df_anteriores_incompletas = df_anteriores_incompletas[
                    ~df_anteriores_incompletas[col_env].astype(str).str.strip().str.upper().isin(["SI", "SÍ"])
                ]

            total_hoy = len(df_hoy)
            fechas_validas = df_renamed_valid["_dt"].tolist()
            if fechas_validas:
                fecha_activa_str = max(fechas_validas).strftime("%d/%m/%Y")

    # 1. ENCABEZADO DE KPIS SUPERIORES
    kcol1, kcol2, kcol3, kcol4, kcol5 = st.columns(5)
    with kcol1:
        st.markdown(f'<div class="kpi-card"><div class="kpi-title">TOTAL ÓRDENES</div><div class="kpi-value">{total_reg}</div></div>', unsafe_allow_html=True)
    with kcol2:
        st.markdown(f'<div class="kpi-card"><div class="kpi-title">FIRMADOS</div><div class="kpi-value" style="color: #38BDF8;">{total_firm}</div></div>', unsafe_allow_html=True)
    with kcol3:
        st.markdown(f'<div class="kpi-card"><div class="kpi-title">ENVIADOS</div><div class="kpi-value" style="color: #10B981;">{total_env}</div></div>', unsafe_allow_html=True)
    with kcol4:
        st.markdown(f'<div class="kpi-card"><div class="kpi-title">PENDIENTES</div><div class="kpi-value" style="color: #F59E0B;">{total_pend}</div></div>', unsafe_allow_html=True)
    with kcol5:
        st.markdown(f'<div class="kpi-card"><div class="kpi-title">FECHA HOY</div><div class="kpi-value" style="font-size: 16px; padding-top: 4px;">{fecha_activa_str}</div></div>', unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom: 6px;'></div>", unsafe_allow_html=True)

    # 2. CONTROLES Y BUSCADOR (CON BOTÓN DE OCULTAS INCLUIDO)
    if (df_vista is not None and not df_vista.empty) or (df_ocultas is not None and not df_ocultas.empty):
        col_btn1, col_btn2, col_f_todas, col_f_atasc, col_f_correc, col_f_ocult, col_search_box, col_info = st.columns(
            [0.5, 0.5, 0.85, 1.15, 1.15, 1.0, 2.0, 1.35]
        )

        with col_btn1:
            if st.button("⬆️ Subir"):
                st.session_state.page_index = max(0, st.session_state.page_index - 1)
                st.session_state.last_switch_time = time.time()
                st.session_state.manual_nav_bonus = 30
                st.rerun()

        with col_btn2:
            if st.button("⬇️ Bajar"):
                st.session_state.page_index += 1
                st.session_state.last_switch_time = time.time()
                st.session_state.manual_nav_bonus = 30
                st.rerun()

        with col_f_todas:
            lbl_todas = "📋 Todas" if st.session_state.alert_filter != "TODAS" else "▶ 📋 Todas"
            if st.button(lbl_todas, key="btn_f_todas"):
                st.session_state.alert_filter = "TODAS"
                st.session_state.search_input = ""
                st.session_state.page_index = 0
                st.rerun()

        with col_f_atasc:
            lbl_atasc = f"⚠️ Atascadas ({cant_atascadas})" if st.session_state.alert_filter != "ATASCADAS" else f"▶ ⚠️ Atascadas ({cant_atascadas})"
            if st.button(lbl_atasc, key="btn_f_atasc"):
                st.session_state.alert_filter = "ATASCADAS"
                st.session_state.search_input = ""
                st.session_state.page_index = 0
                st.rerun()

        with col_f_correc:
            lbl_correc = f"🚨 Corrección ({cant_correcciones})" if st.session_state.alert_filter != "CORRECCION" else f"▶ 🚨 Corrección ({cant_correcciones})"
            if st.button(lbl_correc, key="btn_f_correc"):
                st.session_state.alert_filter = "CORRECCION"
                st.session_state.search_input = ""
                st.session_state.page_index = 0
                st.rerun()

        cant_ocultas = len(df_ocultas)
        with col_f_ocult:
            lbl_ocult = f"👁️ Ocultas ({cant_ocultas})" if st.session_state.alert_filter != "OCULTAS" else f"▶ 👁️ Ocultas ({cant_ocultas})"
            if st.button(lbl_ocult, key="btn_f_ocult"):
                st.session_state.alert_filter = "OCULTAS"
                st.session_state.search_input = ""
                st.session_state.page_index = 0
                st.rerun()

        # FILTRADO SEGÚN EL BOTÓN SELECCIONADO
        col_cer_f = next((c for c in df_vista.columns if "CER" in c.upper()), None)

        if st.session_state.alert_filter == "OCULTAS":
            df_vista = df_ocultas.copy()
        elif st.session_state.alert_filter == "ATASCADAS" and col_cer_f:
            cer_s = df_vista[col_cer_f].astype(str).str.strip().str.upper()
            df_vista = df_vista[
                (cer_s != "")
                & (~cer_s.isin(["SI", "SÍ"]))
                & (~cer_s.str.contains("CORREC", na=False))
            ]
        elif st.session_state.alert_filter == "CORRECCION" and col_cer_f:
            df_vista = df_vista[df_vista[col_cer_f].astype(str).str.upper().str.contains("CORREC", na=False)]

        # BÚSQUEDA RÁPIDA POR # ORDEN O CUALQUIER TEXTO
        with col_search_box:
            st.text_input(
                label="Buscar",
                key="search_input",
                placeholder="🔍 Buscar # Orden, responsable...",
                label_visibility="collapsed",
            )

        term_search = st.session_state.get("search_input", "").strip().lower()
        if term_search:
            col_target = "# Orden" if "# Orden" in df_vista.columns else df_vista.columns[0]
            df_vista = df_vista[df_vista[col_target].astype(str).str.lower().str.contains(term_search, na=False)]

        # CÁLCULO DE PAGINACIÓN AUTOMÁTICA
        PAGE_SIZE = 12
        total_items = len(df_vista)
        total_pages = max(1, (total_items + PAGE_SIZE - 1) // PAGE_SIZE)

        # ROTACIÓN AUTOMÁTICA DE PÁGINAS
        now = time.time()
        time_limit = 15 + st.session_state.manual_nav_bonus
        if now - st.session_state.last_switch_time > time_limit:
            st.session_state.page_index = (st.session_state.page_index + 1) % total_pages
            st.session_state.last_switch_time = now
            st.session_state.manual_nav_bonus = 0
            st.rerun()

        if st.session_state.page_index >= total_pages:
            st.session_state.page_index = 0

        cur_page = st.session_state.page_index + 1
        start_idx = st.session_state.page_index * PAGE_SIZE
        end_idx = start_idx + PAGE_SIZE
        df_pagina = df_vista.iloc[start_idx:end_idx]

        with col_info:
            filtro_txt = f" [{st.session_state.alert_filter}]" if st.session_state.alert_filter != "TODAS" else ""
            st.markdown(
                f"<div style='text-align: right; color: #9CA3AF; font-size: 11px; font-weight: 700; padding-top: 5px;'>"
                f"PÁG {cur_page}/{total_pages}{filtro_txt} | ITEMS {start_idx+1}-{min(end_idx, total_items)} DE {total_items}</div>",
                unsafe_allow_html=True,
            )

        # RENDER TABLA
        st.markdown(render_dark_table(df_pagina), unsafe_allow_html=True)

    else:
        st.warning("⚠️ No se encontraron datos en la hoja de proceso.")

    # EXPANDER INFERIOR PARA ÓRDENES OCULTAS (SI SE ESTÁ EN OTRA VISTA)
    if st.session_state.alert_filter != "OCULTAS" and not df_ocultas.empty:
        st.markdown("<hr style='border-color: #1F2937; margin: 12px 0 8px 0;'>", unsafe_allow_html=True)
        with st.expander(f"👁️ Desplegar Órdenes Ocultas ({len(df_ocultas)})", expanded=False):
            st.markdown(render_dark_table(df_ocultas), unsafe_allow_html=True)

    # 3. SECCIÓN INFERIOR: SEGUIMIENTO DE HOY + NOVEDADES / BITÁCORA EN PARALELO
    st.markdown("<hr style='border-color: #1F2937; margin: 8px 0;'>", unsafe_allow_html=True)
    col_progreso, col_bitacora = st.columns([1.1, 1.0])

    # COLUMNA IZQUIERDA: PROGRESO Y SEGUIMIENTO DE ETAPAS
    with col_progreso:
        st.markdown(
            f'<div style="font-weight: 800; font-size: 13px; color: #38BDF8; margin-bottom: 6px;">'
            f'📌 AVANCE DE HOY Y PENDIENTES ({total_hoy} de hoy | {len(df_anteriores_incompletas)} anteriores)</div>',
            unsafe_allow_html=True,
        )

        df_comb = pd.concat([df_hoy, df_anteriores_incompletas], ignore_index=True)
        if not df_comb.empty:
            PROG_PAGE_SIZE = 4
            tot_prog_items = len(df_comb)
            tot_prog_pages = max(1, (tot_prog_items + PROG_PAGE_SIZE - 1) // PROG_PAGE_SIZE)

            if now - st.session_state.prog_day_last_switch > 12:
                st.session_state.prog_day_page = (st.session_state.prog_day_page + 1) % tot_prog_pages
                st.session_state.prog_day_last_switch = now

            if st.session_state.prog_day_page >= tot_prog_pages:
                st.session_state.prog_day_page = 0

            p_start = st.session_state.prog_day_page * PROG_PAGE_SIZE
            p_end = p_start + PROG_PAGE_SIZE
            df_prog_pag = df_comb.iloc[p_start:p_end]

            for _, r_p in df_prog_pag.iterrows():
                ord_p = limpiar_texto(r_p.get("# Orden", r_p.get("ORDEN", "N/A")))
                resp_p = limpiar_texto(r_p.get("Responsables", r_p.get("RESPONSABLE", "")))
                pct, falta_txt = calcular_progreso_orden(r_p)

                bar_color = "#10B981" if pct == 100 else "#3B82F6" if pct >= 50 else "#F59E0B"

                st.markdown(
                    f'''
                    <div class="progress-order-card">
                        <div style="display: flex; justify-content: space-between; font-weight: 700; font-size: 11.5px; margin-bottom: 2px;">
                            <span>Orden #{ord_p} <span style="color: #9CA3AF; font-weight: 400;">({resp_p})</span></span>
                            <span style="color: {bar_color};">{pct}%</span>
                        </div>
                        <div style="background-color: #1F2937; border-radius: 3px; height: 5px; width: 100%; margin-bottom: 2px; overflow: hidden;">
                            <div style="background-color: {bar_color}; width: {pct}%; height: 100%;"></div>
                        </div>
                        <div style="font-size: 10px; color: #9CA3AF;">{falta_txt}</div>
                    </div>
                    ''',
                    unsafe_allow_html=True,
                )
        else:
            st.info("Sin órdenes en progreso registradas para el día de hoy.")

    # COLUMNA DERECHA: NOVEDADES Y BITÁCORA INTERACTIVA MULTIUSUARIO
    with col_bitacora:
        st.markdown(
            '<div style="font-weight: 800; font-size: 13px; color: #10B981; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center;">'
            '<span>💬 BITÁCORA Y NOVEDADES EN VIVO</span>'
            '<span style="font-size: 10px; color: #9CA3AF; font-weight: 500;">Sincronizado entre PCs</span></div>',
            unsafe_allow_html=True,
        )

        # CONFIGURACIÓN RÁPIDA DE EMISOR Y PERMISOS DE NOTIFICACIÓN
        c_emis, c_notif = st.columns([1.6, 1.0])
        with c_emis:
            idx_actual = LISTA_EMISORES.index(st.session_state.emisor_local) if st.session_state.emisor_local in LISTA_EMISORES else 0
            emisor_sel = st.selectbox(
                "Mi usuario:",
                LISTA_EMISORES,
                index=idx_actual,
                key="sb_emisor_local",
                label_visibility="collapsed"
            )
            st.session_state.emisor_local = emisor_sel

        with c_notif:
            if st.button("🔔 Activar Sonido/Notif", key="btn_permisos_notif"):
                solicitar_permisos_notificaciones_js()

        # FORMULARIO PARA REGISTRAR NUEVA NOVEDAD
        with st.form(key="form_nueva_novedad", clear_on_submit=True):
            col_rec, col_prio = st.columns([1.2, 1.0])
            with col_rec:
                receptor_input = st.selectbox("Dirigido a:", LISTA_RECEPTORES, index=0)
            with col_prio:
                prioridad_input = st.selectbox("Prioridad:", ["Normal", "Auditoría", "Urgente"], index=0)

            texto_novedad = st.text_area("Mensaje de Novedad:", placeholder="Escribe la novedad o aviso urgente aquí...", height=55)
            btn_enviar = st.form_submit_button("🚀 PUBLICAR EN BITÁCORA")

            if btn_enviar and texto_novedad.strip():
                now_dt = datetime.now(COT)
                nuevo_msg = {
                    "id": f"msg_{int(time.time()*1000)}",
                    "emisor": st.session_state.emisor_local,
                    "receptor": receptor_input,
                    "prioridad": prioridad_input,
                    "contenido": texto_novedad.strip(),
                    "fecha_hora": now_dt.strftime("%d/%m/%Y %H:%M"),
                    "timestamp": time.time(),
                    "estado": "Pendiente",
                    "usuario_enterado": None,
                    "fecha_enterado": None,
                    "permitir_respuestas": False,
                    "mostrar_respuestas": False,
                    "respuestas": []
                }
                ESTADO_GLOBAL["mensajes_bitacora"].insert(0, nuevo_msg)
                guardar_bitacora_local(ESTADO_GLOBAL["mensajes_bitacora"])
                st.success("✅ Novedad publicada correctamente.")
                st.rerun()

        # RENDER Y ACCIONES SOBRE LISTA DE NOVEDADES
        mensajes_actuales = ESTADO_GLOBAL.get("mensajes_bitacora", [])
        if mensajes_actuales:
            mensajes_ordenados = sorted(mensajes_actuales, key=obtener_orden_mensaje)

            st.markdown('<div class="chat-container">', unsafe_allow_html=True)
            for m in mensajes_ordenados:
                m_id = m.get("id")
                prio = m.get("prioridad")
                est = m.get("estado")
                
                now_t = time.time()
                ts_orig = m.get("timestamp", now_t)
                elapsed = max(0, now_t - ts_orig)
                cycle_sec = elapsed % 240
                cycle_num = int(elapsed // 240)

                st.markdown(render_chat_message_html(m, cycle_sec=cycle_sec, cycle_num=cycle_num), unsafe_allow_html=True)

                c_act1, c_act2, c_act3 = st.columns([1.2, 1.1, 1.1])
                
                with c_act1:
                    if est == "Pendiente":
                        if st.button("✅ Marcar Realizado", key=f"btn_enterado_{m_id}"):
                            m["estado"] = "Atendido"
                            m["usuario_enterado"] = st.session_state.emisor_local
                            m["fecha_enterado"] = datetime.now(COT).strftime("%d/%m/%Y %H:%M")
                            guardar_bitacora_local(ESTADO_GLOBAL["mensajes_bitacora"])
                            st.rerun()

                with c_act2:
                    val_resp = m.get("permitir_respuestas", False)
                    txt_btn_resp = "💬 Responder" if not val_resp else "✖️ Cancelar"
                    if st.button(txt_btn_resp, key=f"btn_toggle_resp_{m_id}"):
                        m["permitir_respuestas"] = not val_resp
                        st.rerun()

                with c_act3:
                    if st.button("🗑️ Borrar", key=f"btn_del_{m_id}"):
                        ESTADO_GLOBAL["mensajes_bitacora"] = [x for x in ESTADO_GLOBAL["mensajes_bitacora"] if x.get("id") != m_id]
                        guardar_bitacora_local(ESTADO_GLOBAL["mensajes_bitacora"])
                        st.rerun()

                # CAJA EXPANDIBLE PARA ESCRIBIR RESPUESTAS HILADAS
                if m.get("permitir_respuestas", False):
                    with st.form(key=f"form_resp_{m_id}"):
                        txt_reply = st.text_input("Respuesta:", placeholder="Escribe tu respuesta...", key=f"in_resp_{m_id}")
                        if st.form_submit_button("Enviar Respuesta"):
                            if txt_reply.strip():
                                if "respuestas" not in m:
                                    m["respuestas"] = []
                                m["respuestas"].append({
                                    "usuario": st.session_state.emisor_local,
                                    "texto": txt_reply.strip(),
                                    "fecha_hora": datetime.now(COT).strftime("%d/%m %H:%M")
                                })
                                m["permitir_respuestas"] = False
                                guardar_bitacora_local(ESTADO_GLOBAL["mensajes_bitacora"])
                                st.rerun()

                st.markdown("<div style='margin-bottom: 6px;'></div>", unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No hay novedades registradas en la bitácora actualmente.")


# ---------------------------------------------------------
# EJECUCIÓN PRINCIPAL DE LA APLICACIÓN
# ---------------------------------------------------------
if __name__ == "__main__":
    render_tablero_fluido()
