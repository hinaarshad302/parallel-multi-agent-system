            """
            - Password aur API keys kisi ke saath share na karein.
            - API keys GitHub source code mein na likhein.
            - Supabase email verification aur RLS policies check karein.
            - Strong password use karein.
            - Account issue par password reset karein.
            """
        )


# --------------------------------------------------
# 8. ENTRY POINT
# --------------------------------------------------

def main() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

        :root {
            --app-bg: #0b1020;
            --panel-bg: #111a2e;
            --panel-border: rgba(148, 163, 184, .17);
            --muted: #9aa8c2;
            --accent: #8b5cf6;
            --accent-2: #22d3ee;
        }
        .stApp {
            background:
                radial-gradient(ellipse at 12% 0%, rgba(91, 33, 182, .18), transparent 38%),
                radial-gradient(ellipse at 90% 12%, rgba(8, 145, 178, .12), transparent 32%),
                var(--app-bg);
            color: #edf2ff;
            font-family: 'DM Sans', sans-serif;
        }
        [data-testid="stHeader"] { background: rgba(11, 16, 32, .78); }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #10182b 0%, #0d1425 100%);
            border-right: 1px solid var(--panel-border);
        }
        [data-testid="stSidebar"] * { color: #e7edff; }
        .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1280px; }
        h1, h2, h3 { font-family: 'Space Grotesk', sans-serif !important; letter-spacing: -.035em; }
        h1 { font-size: clamp(2rem, 4vw, 3rem) !important; }
        h2 { font-size: 1.7rem !important; }
        p, label, .stMarkdown { line-height: 1.65; }
        [data-testid="stMetric"] {
            background: linear-gradient(145deg, rgba(23, 35, 59, .96), rgba(16, 25, 44, .96));
            border: 1px solid var(--panel-border);
            padding: 1rem 1.1rem;
            border-radius: 16px;
        }
        [data-testid="stMetricLabel"] { color: var(--muted) !important; }
        [data-testid="stMetricValue"] { color: #f4f7ff !important; font-family: 'Space Grotesk', sans-serif; }
        [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea {
            background: #0e1729 !important;
            color: #f4f7ff !important;
            border: 1px solid #2b3956 !important;
            border-radius: 12px !important;
        }
        [data-testid="stTextInput"] input:focus, [data-testid="stTextArea"] textarea:focus {
            border-color: #8b5cf6 !important;
            box-shadow: 0 0 0 1px #8b5cf6 !important;
        }
        .stButton > button, [data-testid="stFormSubmitButton"] button {
            border-radius: 11px;
            min-height: 2.8rem;
            font-weight: 700;
            border: 1px solid rgba(139, 92, 246, .5);
            transition: all .18s ease;
        }
        .stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primary"] {
            background: linear-gradient(100deg, #7c3aed, #4f46e5);
            color: white;
        }
        .stButton > button:hover { transform: translateY(-1px); border-color: #a78bfa; }
        [data-testid="stTabs"] button { font-weight: 600; }
        [data-testid="stExpander"] {
            background: rgba(17, 26, 46, .75);
            border: 1px solid var(--panel-border);
            border-radius: 13px;
        }
        [data-testid="stAlert"] { border-radius: 12px; }
        .hero {
            padding: 1.5rem 1.6rem;
            margin: .3rem 0 1.2rem;
            border-radius: 22px;
            border: 1px solid rgba(139, 92, 246, .32);
            background: linear-gradient(115deg, rgba(91, 33, 182, .24), rgba(17, 26, 46, .92) 54%, rgba(8, 145, 178, .14));
        }
        .eyebrow {
            color: #a5b4fc; text-transform: uppercase; letter-spacing: .16em;
            font-size: .72rem; font-weight: 700; margin-bottom: .5rem;
        }
        .hero-title { font-family: 'Space Grotesk', sans-serif; font-size: clamp(1.8rem, 4vw, 2.65rem); font-weight: 700; line-height: 1.15; }
        .hero-copy { color: #b9c5dc; max-width: 760px; margin-top: .7rem; }
        .section-kicker { color: #a5b4fc; font-size: .76rem; text-transform: uppercase; letter-spacing: .13em; font-weight: 700; }
        .stCaption, small { color: #9aa8c2 !important; }
        @media (max-width: 700px) {
            .block-container { padding: 1rem .8rem 2rem; }
            .hero { padding: 1.1rem; border-radius: 16px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    try:
        get_supabase_config()
    except Exception:
        st.error(
            "Supabase setup check karein. Streamlit Secrets mein "
            "SUPABASE_URL aur SUPABASE_ANON_KEY sahi honi chahiye. "
            "URL mein /rest/v1 ya /auth/v1 path na ho."
        )
        st.stop()

    user = get_authenticated_user()

    if user is None:
        render_authentication()
    else:
        render_app(user)


if __name__ == "__main__":
    main()
