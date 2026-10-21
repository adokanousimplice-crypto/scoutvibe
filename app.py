

import json
from datetime import date, datetime
from html import escape
from pathlib import Path
from uuid import uuid4

import streamlit as st

try:
    from supabase import create_client
except ImportError:
    create_client = None

DATA_FILE = Path(__file__).with_name("scoutvibe_data.json")
DEFAULT_PARISHES = ["Saint-Jean", "Notre-Dame des Bois", "Saint-Martin"]


def default_parish_data():
    return {
        "songs": [
            {
                "title": "Le chant de la promesse",
                "author": "Tradition scoute",
                "lyrics": "Ensemble, avançons sur le chemin.",
            }
        ],
        "materials": [
            "Tente et sardines",
            "Gourde",
            "Trousse de premiers secours",
        ],
        "checked_materials": [],
        "schedule": [
            {"time": "09:00", "activity": "Accueil et rassemblement", "lead": ""},
            {"time": "10:00", "activity": "Grand jeu", "lead": ""},
        ],
    }


def load_data():
    if not DATA_FILE.exists():
        return {}

    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    return data if isinstance(data, dict) else {}


def save_data():
    data = {
        "parishes": st.session_state["parishes"],
        "parish_data": st.session_state["parish_data"],
        "meetings": st.session_state.get("meetings", []),
    }

    if st.session_state.get("remote_mode"):
        st.session_state["supabase_client"].table("troop_data").upsert(
            {
                "troop_id": st.session_state["troop_id"],
                "data": data,
            },
            on_conflict="troop_id",
        ).execute()
        return

    temp_file = DATA_FILE.with_suffix(".tmp")
    temp_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_file.replace(DATA_FILE)


def save_material_checks(parish):
    parish_data = st.session_state["parish_data"][parish]
    parish_data["checked_materials"] = [
        index
        for index in range(len(parish_data["materials"]))
        if st.session_state.get(f"material_{parish}_{index}", False)
    ]
    save_data()


def get_supabase_settings():
    try:
        settings = st.secrets["supabase"]
        return settings["url"], settings["anon_key"]
    except Exception:
        return None, None


def save_auth_session(session):
    st.session_state["supabase_access_token"] = session.access_token
    st.session_state["supabase_refresh_token"] = session.refresh_token


def default_troop_data():
    return {
        "parishes": DEFAULT_PARISHES.copy(),
        "parish_data": {},
        "meetings": [],
    }


st.set_page_config(
    page_title="ScoutVibe",
    page_icon="⚜️",
    layout="wide",
)

# Style général
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

        :root {
            --pine: #173c32;
            --pine-deep: #102e28;
            --leaf: #a9c779;
            --citrus: #e5a34b;
            --coral: #cf6848;
            --sky: #d8e9e7;
            --paper: #f5f7f2;
            --ink: #20342d;
            --muted: #68776e;
            --line: #dce4dc;
        }

        html, body, [class*="css"] {
            font-family: 'DM Sans', sans-serif;
            letter-spacing: 0;
        }

        .stApp {
            background:
                repeating-linear-gradient(0deg, rgba(23, 60, 50, 0.018) 0, rgba(23, 60, 50, 0.018) 1px, transparent 1px, transparent 30px),
                var(--paper);
            color: var(--ink);
        }

        [data-testid="stHeader"] {
            background: transparent;
        }

        .block-container {
            max-width: 1320px;
            padding-top: 1.6rem;
            padding-bottom: 4rem;
        }

        h1, h2, h3, h4 {
            color: var(--pine);
            font-family: 'Space Grotesk', sans-serif;
            letter-spacing: 0;
        }

        .st-key-hero_copy {
            min-height: 340px;
            height: 100%;
            padding: 2rem 2.2rem;
            display: flex;
            flex-direction: column;
            justify-content: center;
            background: var(--pine);
            border-left: 6px solid var(--citrus);
            border-radius: 6px;
            color: #f4f7ef;
        }

        .st-key-hero_copy h1 {
            color: #fff;
            font-size: 2.8rem;
            line-height: 1.05;
            margin: 0.25rem 0 0.8rem;
        }

        .hero-kicker {
            color: var(--leaf);
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
        }

        .hero-copy {
            color: #dce8df;
            font-size: 1rem;
            line-height: 1.65;
            max-width: 36rem;
            margin: 0 0 1.25rem;
        }

        .hero-photo img {
            height: 340px;
            object-fit: cover;
            border-radius: 6px;
        }

        .hero-photo [data-testid="stImage"] {
            height: 100%;
        }

        .st-key-hero_copy [data-testid="stWidgetLabel"] p {
            color: #e5eee4;
            font-weight: 600;
        }

        [data-testid="stMetric"] {
            padding: 1rem 1.1rem;
            background: #fff;
            border: 1px solid var(--line);
            border-top: 3px solid var(--leaf);
            border-radius: 5px;
        }

        [data-testid="stMetricLabel"] p {
            color: var(--muted);
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
        }

        [data-testid="stMetricValue"] {
            color: var(--pine);
            font-family: 'Space Grotesk', sans-serif;
        }

        [data-testid="stTabs"] {
            margin-top: 1.5rem;
        }

        [data-testid="stTabs"] [role="tablist"] {
            gap: 0.35rem;
            border-bottom: 1px solid var(--line);
        }

        [data-testid="stTabs"] button[role="tab"] {
            min-height: 48px;
            color: var(--muted);
            font-weight: 700;
            border-radius: 5px 5px 0 0;
        }

        [data-testid="stTabs"] button[aria-selected="true"] {
            color: var(--pine);
            background: #e8efe7;
            border-bottom: 3px solid var(--coral);
        }

        .field-note {
            padding: 0.8rem 1rem;
            margin: 0.2rem 0 1.2rem;
            color: #264a3c;
            background: var(--sky);
            border-left: 4px solid #4c8b80;
            border-radius: 3px;
        }

        .section-rule {
            height: 1px;
            margin: 1.4rem 0 0.8rem;
            background: var(--line);
        }

        [data-testid="stVerticalBlockBorderWrapper"] {
            border-color: var(--line);
            border-radius: 5px;
            background: rgba(255, 255, 255, 0.78);
        }

        [data-testid="stExpander"] {
            background: #fff;
            border-color: var(--line);
            border-radius: 5px;
        }

        [data-testid="stForm"] {
            padding: 1.2rem;
            border: 1px solid var(--line);
            border-radius: 5px;
            background: rgba(255, 255, 255, 0.82);
        }

        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea,
        [data-testid="stDateInput"] input,
        [data-testid="stTimeInput"] input,
        [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            color: var(--ink) !important;
            background-color: #fff !important;
            border-radius: 4px;
            border-color: #cbd8cf;
        }

        [data-testid="stTextInput"] label,
        [data-testid="stTextInput"] label p,
        [data-testid="stTextArea"] label,
        [data-testid="stTextArea"] label p,
        [data-testid="stRadio"] label,
        [data-testid="stRadio"] label p,
        [data-testid="stWidgetLabel"] p {
            color: var(--pine) !important;
            font-weight: 600;
        }

        [data-testid="stRadio"] [role="radiogroup"] {
            gap: 0.5rem;
            padding: 0.65rem 0.8rem;
            background: #e8eee7;
            border: 1px solid #cbd8cf;
            border-radius: 5px;
        }

        [data-testid="stRadio"] [role="radio"] {
            color: var(--pine) !important;
            font-weight: 600;
        }

        [data-testid="stRadio"] [role="radio"][aria-checked="true"] {
            color: var(--pine-deep) !important;
            font-weight: 700;
        }

        [data-testid="stRadio"] input {
            accent-color: var(--coral);
        }

        [data-testid="stTextInput"] input:focus,
        [data-testid="stTextArea"] textarea:focus {
            border-color: #4c8b80;
            box-shadow: 0 0 0 1px #4c8b80;
        }

        [data-testid="stTextInput"] input::placeholder,
        [data-testid="stTextArea"] textarea::placeholder {
            color: #78867e !important;
            opacity: 1;
        }

        .stButton > button, [data-testid="stFormSubmitButton"] > button {
            min-height: 42px;
            padding: 0.45rem 1rem;
            color: #fff;
            background: var(--pine);
            border: 1px solid var(--pine);
            border-radius: 4px;
            font-weight: 700;
            transition: background 150ms ease, transform 150ms ease;
        }

        .stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover {
            color: #fff;
            background: var(--pine-deep);
            border-color: var(--pine-deep);
            transform: translateY(-1px);
        }

        [data-testid="stSidebar"] {
            background: #e8eee7;
            border-right: 1px solid var(--line);
        }

        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
            color: var(--pine);
        }

        @media (max-width: 760px) {
            .block-container {
                padding: 1rem 1rem 3rem;
            }

            .st-key-hero_copy {
                min-height: 0;
                padding: 1.4rem;
                margin-top: 0.8rem;
            }

            .st-key-hero_copy h1 {
                font-size: 2.15rem;
            }

            .hero-photo img {
                height: 220px;
            }

            [data-testid="stTabs"] [role="tablist"] {
                overflow-x: auto;
                flex-wrap: nowrap;
            }

            [data-testid="stTabs"] button[role="tab"] {
                flex: 0 0 auto;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

supabase_url, supabase_key = get_supabase_settings()
remote_mode = bool(supabase_url and supabase_key)
user = None
supabase_client = None
active_membership = None
active_troop = None

if remote_mode:
    if create_client is None:
        st.error("Installez les dépendances de requirements.txt pour activer les comptes.")
        st.stop()

    supabase_client = create_client(supabase_url, supabase_key)
    access_token = st.session_state.get("supabase_access_token")
    refresh_token = st.session_state.get("supabase_refresh_token")

    if access_token and refresh_token:
        try:
            auth_response = supabase_client.auth.set_session(access_token, refresh_token)
            refreshed_session = getattr(auth_response, "session", None) or auth_response
            save_auth_session(refreshed_session)
            user = supabase_client.auth.get_user().user
        except Exception:
            st.session_state.pop("supabase_access_token", None)
            st.session_state.pop("supabase_refresh_token", None)

    if user is None:
        st.title("⚜️ ScoutVibe")
        st.subheader("Connexion à votre troupe")
        auth_mode = st.radio(
            "Compte",
            ["Se connecter", "Créer un compte"],
            horizontal=True,
        )
        with st.form("auth_form"):
            display_name = ""
            if auth_mode == "Créer un compte":
                display_name = st.text_input("Nom affiché")
            email = st.text_input("Adresse e-mail")
            password = st.text_input("Mot de passe", type="password")
            auth_submitted = st.form_submit_button(auth_mode)

        if auth_submitted:
            try:
                if auth_mode == "Créer un compte":
                    if not display_name.strip():
                        st.error("Saisissez le nom qui sera visible par votre troupe.")
                    else:
                        response = supabase_client.auth.sign_up(
                            {
                                "email": email.strip(),
                                "password": password,
                                "options": {"data": {"display_name": display_name.strip()}},
                            }
                        )
                        if response.session:
                            save_auth_session(response.session)
                            st.rerun()
                        else:
                            st.success("Compte créé. Vérifiez votre e-mail pour le confirmer.")
                else:
                    response = supabase_client.auth.sign_in_with_password(
                        {"email": email.strip(), "password": password}
                    )
                    save_auth_session(response.session)
                    st.rerun()
            except Exception as error:
                st.error(f"Impossible de traiter la demande : {error}")
        st.stop()

    st.session_state["supabase_client"] = supabase_client
    st.session_state["user_id"] = str(user.id)
    memberships = (
        supabase_client.table("memberships")
        .select("troop_id, role")
        .eq("user_id", str(user.id))
        .execute()
        .data
        or []
    )

    if not memberships:
        st.title("⚜️ ScoutVibe")
        st.subheader("Créer ou rejoindre une troupe")
        create_tab, join_tab = st.tabs(["Créer une troupe", "Rejoindre une troupe"])

        with create_tab:
            with st.form("create_troop_form"):
                troop_name = st.text_input("Nom de la troupe")
                import_local_data = st.checkbox(
                    "Importer le JSON présent sur le serveur",
                    value=DATA_FILE.exists(),
                )
                uploaded_json = st.file_uploader(
                    "Ou importer un fichier JSON depuis votre appareil",
                    type=["json"],
                )
                create_submitted = st.form_submit_button("Créer la troupe")
            if create_submitted:
                if not troop_name.strip():
                    st.error("Saisissez le nom de la troupe.")
                else:
                    try:
                        created = supabase_client.rpc(
                            "create_troop", {"troop_name": troop_name.strip()}
                        ).execute()
                        troop_id = created.data
                        if isinstance(troop_id, list):
                            troop_id = troop_id[0]
                        if uploaded_json is not None:
                            imported_data = json.loads(uploaded_json.getvalue().decode("utf-8"))
                            if not isinstance(imported_data, dict):
                                raise ValueError("Le fichier JSON doit contenir un objet de données.")
                        elif import_local_data:
                            imported_data = load_data() or default_troop_data()
                        else:
                            imported_data = default_troop_data()
                        imported_data.setdefault("parishes", DEFAULT_PARISHES.copy())
                        imported_data.setdefault("parish_data", {})
                        imported_data.setdefault("meetings", [])
                        supabase_client.table("troop_data").upsert(
                            {"troop_id": str(troop_id), "data": imported_data},
                            on_conflict="troop_id",
                        ).execute()
                        st.rerun()
                    except Exception as error:
                        st.error(f"Création impossible : {error}")

        with join_tab:
            with st.form("join_troop_form"):
                invite_code = st.text_input("Code d’invitation")
                join_submitted = st.form_submit_button("Rejoindre")
            if join_submitted:
                try:
                    supabase_client.rpc(
                        "join_troop", {"invite_code_input": invite_code.strip().upper()}
                    ).execute()
                    st.rerun()
                except Exception as error:
                    st.error(f"Impossible de rejoindre cette troupe : {error}")
        st.stop()

    troop_options = []
    for membership in memberships:
        troop_result = (
            supabase_client.table("troops")
            .select("id, name")
            .eq("id", membership["troop_id"])
            .limit(1)
            .execute()
        )
        if troop_result.data:
            troop_options.append((troop_result.data[0], membership["role"]))

    if not troop_options:
        st.error("Aucune troupe accessible. Vérifiez le schéma SQL Supabase.")
        st.stop()

    if len(troop_options) > 1:
        selected_troop_name = st.selectbox(
            "Troupe",
            [option[0]["name"] for option in troop_options],
            key="active_troop_name",
        )
        selected_option = next(
            option for option in troop_options if option[0]["name"] == selected_troop_name
        )
    else:
        selected_option = troop_options[0]

    active_troop, active_role = selected_option
    active_membership = {"role": active_role}
    st.session_state["remote_mode"] = True
    st.session_state["troop_id"] = str(active_troop["id"])
    st.session_state["troop_name"] = active_troop["name"]
    st.session_state["role"] = active_role
    st.session_state["can_manage"] = active_role in ("chef", "assistant")

    display_name = (user.user_metadata or {}).get("display_name") or user.email or "Scout"
    with st.sidebar:
        st.write(f"**{display_name}**")
        st.caption(f"{active_troop['name']} · {active_role}")
        if active_role == "chef":
            try:
                invite_result = supabase_client.rpc(
                    "get_troop_invite_code", {"target_troop": str(active_troop["id"])}
                ).execute()
                st.caption(f"Code d’invitation : `{invite_result.data}`")
            except Exception:
                st.caption("Code d’invitation indisponible.")
        if st.button("Se déconnecter"):
            st.session_state.pop("supabase_access_token", None)
            st.session_state.pop("supabase_refresh_token", None)
            st.session_state.pop("data_scope", None)
            st.rerun()
else:
    st.session_state["remote_mode"] = False
    st.session_state["can_manage"] = True

data_scope = (
    f"troop:{active_troop['id']}" if remote_mode and active_troop else "local"
)
if st.session_state.get("data_scope") != data_scope:
    for state_key in list(st.session_state):
        if state_key.startswith("material_"):
            del st.session_state[state_key]

    if remote_mode:
        stored_result = (
            supabase_client.table("troop_data")
            .select("data")
            .eq("troop_id", str(active_troop["id"]))
            .limit(1)
            .execute()
        )
        saved_data = stored_result.data[0]["data"] if stored_result.data else default_troop_data()
    else:
        saved_data = load_data()

    if not isinstance(saved_data, dict):
        saved_data = default_troop_data()
    saved_parishes = saved_data.get("parishes", DEFAULT_PARISHES)
    saved_parish_data = saved_data.get("parish_data", {})
    st.session_state["parishes"] = (
        saved_parishes if isinstance(saved_parishes, list) else DEFAULT_PARISHES.copy()
    )
    st.session_state["parish_data"] = (
        saved_parish_data if isinstance(saved_parish_data, dict) else {}
    )
    st.session_state["meetings"] = saved_data.get("meetings", [])
    st.session_state["data_scope"] = data_scope

# Sélectionner automatiquement la paroisse qui vient d'être ajoutée.
if "next_parish" in st.session_state:
    st.session_state["parish_choice"] = st.session_state.pop("next_parish")

for parish in st.session_state["parishes"]:
    parish_data = st.session_state["parish_data"].setdefault(
        parish, default_parish_data()
    )
    parish_defaults = default_parish_data()
    for key, default_value in parish_defaults.items():
        parish_data.setdefault(key, default_value)

if remote_mode:
    st.caption(f"{active_troop['name']} · espace partagé")
else:
    st.caption("Mode local · les données restent sur cet appareil")

image_column, welcome_column = st.columns([1.05, 0.95], gap="medium", vertical_alignment="stretch")

with image_column:
    with st.container(key="hero_photo"):
        st.image(
            "https://images.unsplash.com/photo-1504851149312-7a075b496cc7"
            "?auto=format&fit=crop&w=1400&q=90",
            caption="Le camp commence ici.",
            use_container_width=True,
        )

with welcome_column:
    with st.container(key="hero_copy"):
        st.markdown(
            '<div class="hero-kicker">ScoutVibe · Vie de troupe</div>'
            '<h1>Ensemble, prêts pour l’aventure.</h1>'
            '<p class="hero-copy">Les rendez-vous, les chants et le matériel de votre troupe, réunis au même endroit.</p>',
            unsafe_allow_html=True,
        )
        parish_options = st.session_state["parishes"].copy()
        if st.session_state["can_manage"]:
            parish_options.append("➕ Ajouter une paroisse")
        selected_parish = st.selectbox(
            "Espace de la troupe",
            options=parish_options,
            key="parish_choice",
        )

if selected_parish != "➕ Ajouter une paroisse":
    overview_data = st.session_state["parish_data"][selected_parish]
    if remote_mode:
        upcoming_meetings = (
            supabase_client.table("meetings")
            .select("id")
            .eq("troop_id", str(active_troop["id"]))
            .gte("starts_at", datetime.now().astimezone().isoformat())
            .execute()
            .data
            or []
        )
    else:
        upcoming_meetings = [
            meeting
            for meeting in st.session_state.get("meetings", [])
            if datetime.fromisoformat(meeting["starts_at"].replace("Z", "+00:00")).date() >= date.today()
        ]
    metric_columns = st.columns(3, gap="medium")
    metric_columns[0].metric("Chants", len(overview_data["songs"]), "Carnet de troupe")
    metric_columns[1].metric("Équipements", len(overview_data["materials"]), "Liste de matériel")
    metric_columns[2].metric("Réunions à venir", len(upcoming_meetings), "Au calendrier")
    st.markdown("<div class='section-rule'></div>", unsafe_allow_html=True)

if st.session_state["can_manage"] and selected_parish == "➕ Ajouter une paroisse":
    st.subheader("Nouvelle paroisse")

    with st.form("add_parish_form", clear_on_submit=True):
        new_parish = st.text_input("Nom de la paroisse")
        submitted = st.form_submit_button("Ajouter la paroisse")

    if submitted:
        parish_name = new_parish.strip()
        if not parish_name:
            st.warning("Saisissez le nom de la paroisse.")
        elif parish_name in st.session_state["parishes"]:
            st.warning("Cette paroisse existe déjà.")
        else:
            st.session_state["parishes"].append(parish_name)
            st.session_state["parish_data"][parish_name] = default_parish_data()
            st.session_state["next_parish"] = parish_name
            save_data()
            st.rerun()

else:
    safe_parish = escape(selected_parish)
    day_seed = date.today().toordinal() + sum(ord(char) for char in selected_parish)
    welcome_messages = [
        "Un pas après l'autre, l'aventure se construit ensemble.",
        "Le meilleur équipement d'une patrouille, c'est son esprit d'équipe.",
        "Dehors, chaque sentier est une nouvelle histoire à vivre.",
        "Prêts, solidaires et curieux : le camp peut commencer !",
    ]
    welcome_message = welcome_messages[day_seed % len(welcome_messages)]

    st.markdown(
        f"""
        <div class="welcome-banner">
            <h2>Bienvenue à {safe_parish} ⚜️</h2>
            <p>{welcome_message} 🔥⛺</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    parish_data = st.session_state["parish_data"][selected_parish]

    songs_tab, materials_tab, schedule_tab, meetings_tab = st.tabs(
        [
            "🎵 Carnet de Chants",
            "🎒 Sac à Dos / Matériel",
            "📊 Conducteur / Planning",
            "📅 Réunions",
        ]
    )

    with songs_tab:
        st.subheader("🎵 Carnet de Chants")
        st.markdown(
            '<div class="field-note">🎶 Une patrouille qui chante avance d’un bon pas.</div>',
            unsafe_allow_html=True,
        )

        if parish_data["songs"]:
            for song in parish_data["songs"]:
                with st.expander(f"{song['title']} · {song['author']}"):
                    st.write(song["lyrics"])
        else:
            st.info("Le carnet est vide pour le moment.")

        if st.session_state["can_manage"]:
            with st.form("add_song_form", clear_on_submit=True):
                st.markdown("**Ajouter un chant**")
                song_title = st.text_input("Titre")
                song_author = st.text_input("Auteur ou origine")
                song_lyrics = st.text_area("Paroles")
                add_song = st.form_submit_button("Ajouter le chant")

            if add_song:
                if not song_title.strip():
                    st.warning("Le titre du chant est obligatoire.")
                else:
                    parish_data["songs"].append(
                        {
                            "title": song_title.strip(),
                            "author": song_author.strip() or "Auteur inconnu",
                            "lyrics": song_lyrics.strip() or "Aucune parole renseignée.",
                        }
                    )
                    save_data()
                    st.rerun()

    with materials_tab:
        st.subheader("🎒 Sac à Dos / Matériel")
        st.markdown(
            '<div class="field-note">🧭 On vérifie son sac, puis on part l’esprit léger.</div>',
            unsafe_allow_html=True,
        )

        if parish_data["materials"]:
            for index, item in enumerate(parish_data["materials"]):
                checkbox_key = f"material_{selected_parish}_{index}"
                if checkbox_key not in st.session_state:
                    st.session_state[checkbox_key] = index in parish_data["checked_materials"]
                st.checkbox(
                    item,
                    key=checkbox_key,
                    disabled=not st.session_state["can_manage"],
                    on_change=save_material_checks if st.session_state["can_manage"] else None,
                    args=(selected_parish,),
                )
        else:
            st.info("La liste de matériel est vide.")

        if st.session_state["can_manage"]:
            with st.form("add_material_form", clear_on_submit=True):
                new_item = st.text_input("Ajouter un élément")
                add_material = st.form_submit_button("Ajouter à la liste")

            if add_material:
                if new_item.strip():
                    parish_data["materials"].append(new_item.strip())
                    save_data()
                    st.rerun()
                else:
                    st.warning("Saisissez le nom d'un élément.")

    with schedule_tab:
        st.subheader("📊 Conducteur / Planning")
        st.markdown(
            '<div class="field-note">⏱️ Un bon programme laisse aussi de la place aux surprises.</div>',
            unsafe_allow_html=True,
        )

        if parish_data["schedule"]:
            for entry in sorted(parish_data["schedule"], key=lambda item: item["time"]):
                lead = f" · Responsable : {entry['lead']}" if entry["lead"] else ""
                st.write(f"**{entry['time']}** — {entry['activity']}{lead}")
        else:
            st.info("Aucune activité n'est encore planifiée.")

        if st.session_state["can_manage"]:
            with st.form("add_schedule_form", clear_on_submit=True):
                st.markdown("**Ajouter une activité**")
                activity_time = st.time_input("Heure")
                activity_name = st.text_input("Activité")
                activity_lead = st.text_input("Responsable (facultatif)")
                add_activity = st.form_submit_button("Ajouter au planning")

            if add_activity:
                if not activity_name.strip():
                    st.warning("Le nom de l'activité est obligatoire.")
                else:
                    parish_data["schedule"].append(
                        {
                            "time": activity_time.strftime("%H:%M"),
                            "activity": activity_name.strip(),
                            "lead": activity_lead.strip(),
                        }
                    )
                    save_data()
                    st.rerun()

    with meetings_tab:
        st.subheader("📅 Réunions de la troupe")

        if st.session_state["can_manage"]:
            with st.form("add_meeting_form", clear_on_submit=True):
                meeting_title = st.text_input("Nom de la réunion")
                meeting_date = st.date_input("Date", value=date.today())
                meeting_time = st.time_input("Heure", value=datetime.now().time().replace(second=0, microsecond=0))
                meeting_location = st.text_input("Lieu")
                meeting_notes = st.text_area("Informations utiles")
                add_meeting = st.form_submit_button("Planifier la réunion")

            if add_meeting:
                if not meeting_title.strip():
                    st.warning("Le nom de la réunion est obligatoire.")
                elif remote_mode:
                    try:
                        supabase_client.table("meetings").insert(
                            {
                                "troop_id": str(active_troop["id"]),
                                "title": meeting_title.strip(),
                                "starts_at": datetime.combine(meeting_date, meeting_time).astimezone().isoformat(),
                                "location": meeting_location.strip(),
                                "notes": meeting_notes.strip(),
                            }
                        ).execute()
                        st.rerun()
                    except Exception as error:
                        st.error(f"Impossible de planifier la réunion : {error}")
                else:
                    st.session_state["meetings"].append(
                        {
                            "id": str(uuid4()),
                            "title": meeting_title.strip(),
                            "starts_at": datetime.combine(meeting_date, meeting_time).isoformat(),
                            "location": meeting_location.strip(),
                            "notes": meeting_notes.strip(),
                        }
                    )
                    save_data()
                    st.rerun()

        if remote_mode:
            meeting_rows = (
                supabase_client.table("meetings")
                .select("id, title, starts_at, location, notes")
                .eq("troop_id", str(active_troop["id"]))
                .order("starts_at")
                .execute()
                .data
                or []
            )
        else:
            meeting_rows = sorted(
                st.session_state["meetings"], key=lambda meeting: meeting["starts_at"]
            )

        if not meeting_rows:
            st.info("Aucune réunion planifiée.")

        for meeting in meeting_rows:
            starts_at = datetime.fromisoformat(meeting["starts_at"].replace("Z", "+00:00"))
            with st.container(border=True):
                st.markdown(f"**{meeting['title']}** · {starts_at.astimezone().strftime('%d/%m/%Y à %H:%M')}")
                if meeting.get("location"):
                    st.write(f"Lieu : {meeting['location']}")
                if meeting.get("notes"):
                    st.write(meeting["notes"])

                if remote_mode and st.session_state["can_manage"]:
                    with st.expander("Suivre les présences"):
                        attendance_rows = (
                            supabase_client.table("meeting_attendance")
                            .select("user_id, status")
                            .eq("meeting_id", meeting["id"])
                            .execute()
                            .data
                            or []
                        )
                        user_ids = [row["user_id"] for row in attendance_rows]
                        profiles = []
                        if user_ids:
                            profiles = (
                                supabase_client.table("profiles")
                                .select("user_id, display_name")
                                .in_("user_id", user_ids)
                                .execute()
                                .data
                                or []
                            )
                        display_names = {profile["user_id"]: profile["display_name"] for profile in profiles}
                        if attendance_rows:
                            for row in attendance_rows:
                                name = display_names.get(row["user_id"], "Membre")
                                st.write(f"{name} : {row['status']}")
                        else:
                            st.caption("Aucune réponse pour le moment.")

                elif remote_mode:
                    with st.form(f"attendance_form_{meeting['id']}"):
                        attendance_options = ["À confirmer", "Présent", "Absent"]
                        previous = (
                            supabase_client.table("meeting_attendance")
                            .select("status")
                            .eq("meeting_id", meeting["id"])
                            .eq("user_id", str(user.id))
                            .limit(1)
                            .execute()
                            .data
                            or []
                        )
                        status_map = {"pending": "À confirmer", "present": "Présent", "absent": "Absent"}
                        previous_status = status_map.get(previous[0]["status"], "À confirmer") if previous else "À confirmer"
                        chosen_status = st.radio(
                            "Votre présence",
                            attendance_options,
                            index=attendance_options.index(previous_status),
                            horizontal=True,
                            key=f"attendance_choice_{meeting['id']}",
                        )
                        confirm_attendance = st.form_submit_button("Enregistrer ma réponse")
                    if confirm_attendance:
                        status_value = {"À confirmer": "pending", "Présent": "present", "Absent": "absent"}[chosen_status]
                        try:
                            supabase_client.table("meeting_attendance").upsert(
                                {
                                    "meeting_id": meeting["id"],
                                    "user_id": str(user.id),
                                    "status": status_value,
                                },
                                on_conflict="meeting_id,user_id",
                            ).execute()
                            st.success("Votre réponse est enregistrée.")
                            st.rerun()
                        except Exception as error:
                            st.error(f"Impossible d’enregistrer votre réponse : {error}")
                elif st.session_state["can_manage"]:
                    if st.button("Supprimer la réunion", key=f"delete_local_meeting_{meeting['id']}"):
                        st.session_state["meetings"] = [
                            row for row in st.session_state["meetings"] if row["id"] != meeting["id"]
                        ]
                        save_data()
                        st.rerun()

                if remote_mode and st.session_state["can_manage"]:
                    if st.button("Supprimer la réunion", key=f"delete_meeting_{meeting['id']}"):
                        try:
                            supabase_client.table("meetings").delete().eq("id", meeting["id"]).execute()
                            st.rerun()
                        except Exception as error:
                            st.error(f"Impossible de supprimer la réunion : {error}")

        if not remote_mode:
            st.info("Les confirmations individuelles de présence sont disponibles après configuration de Supabase.")