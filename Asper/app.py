import os
import streamlit as st
from google import genai

MODEL = "gemini-3.5-flash-lite"  # change here if you need to switch models

# ---------- API key (works on Streamlit Cloud and your computer) ----------
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("Missing GEMINI_API_KEY. Add it in the app's Secrets settings.")
    st.stop()

client = genai.Client(api_key=api_key)

# ---------- Prompts ----------
BASE_PROMPT = """You are Asper, a friendly career guide for recent graduates.

Rules:
- Use plain, everyday language. Avoid jargon, and explain any term you must use.
- Ask specific, concrete questions before giving advice. Never give generic advice like "network more" or "be a leader" without a concrete next step.
- Keep answers short, warm, and practical.
- If a user is undecided about a career, run discovery: ask about classes or projects they enjoyed, whether they prefer working with people, data, things, or ideas, what they want to avoid, and what matters most (salary, stability, creativity, impact, flexibility). Ask at most 2 questions at a time, and cap discovery at about 6 questions.
- After discovery, suggest 3 career directions. For each: why it fits, a typical day, entry-level roles, and what the user is missing.
- If the user has a target career, focus on what they need to get there.
- Never present one answer as the user's "perfect" career. Frame results as options to explore.
- For salaries or job demand, say the numbers vary by location and may be outdated, and suggest checking local job sites.
- You are not a licensed counselor. If the user mentions serious stress or hopelessness, encourage them to talk to someone they trust or a campus counselor.
"""

GAP_PROMPT = """Compare the user's profile to the job posting below. Respond in this format:

**Skills you already have**
- Bullet list, matched to the posting's requirements

**Skills missing (most important first)**
- Bullet list, each with one sentence on why it matters for this role

**Your 2-week action plan**
1. A concrete step they can finish in a few days
2. A second step (e.g. a free course, a mini project, or a portfolio item)
3. A third step (e.g. apply to specific entry-level roles, or message someone in the field)

If the profile is missing details you need, say so briefly and ask for them. Keep it under 300 words.

Job posting:
{posting}
"""

ROADMAP_PROMPT = """Create a 30/60/90-day career roadmap for this goal: {goal}

Job posting (if any): {posting}

Respond in this format:

**Days 1-30: Learn and prepare**
- 3 specific actions, each with a measurable finish line (e.g. "complete 10 SQL practice problems")

**Days 31-60: Build proof**
- 3 specific actions, such as a mini project, portfolio item, or informational interview

**Days 61-90: Apply and connect**
- 3 specific actions, such as applying to a set number of roles or following up with contacts

**Milestone check:** one sentence on what success looks like at day 90.

Base the steps on the user's profile where it's relevant. Keep it under 350 words.
"""

EXAMPLES = [
    "I studied a class but I don't know what to do with it",
    "I want a certain job. Could you tell me where I am missing?",
    "I feel stuck and unsure about my job search",
]

# ---------- Styling: dark, with orange and yellow accents ----------
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

.stApp, .stMarkdown, .stChatMessage, .stTextInput, .stTextArea,
.stSelectbox, .stButton, .stExpander, [data-testid="stSidebar"] {
    font-family: 'Plus Jakarta Sans', sans-serif;
}

.stApp { background: #14110E; color: #F4EDE2; }
[data-testid="stSidebar"] { background: #1C1813; border-right: 1px solid #2E2820; }
#MainMenu, footer { visibility: hidden; }

.asper-title {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 3rem; font-weight: 800; line-height: 1.1; margin-bottom: 0.2rem;
    letter-spacing: -0.02em;
    background: linear-gradient(90deg, #FF9F1C, #FFD166);
    -webkit-background-clip: text; background-clip: text; color: transparent;
}
.asper-tagline {
    font-family: 'Plus Jakarta Sans', sans-serif;
    color: #BDB2A3; font-size: 1.05rem; margin-bottom: 1.2rem; line-height: 1.5;
}

.stButton > button {
    background: #FF9F1C; color: #14110E; border: none; border-radius: 10px;
    font-weight: 600; transition: background 0.2s ease;
}
.stButton > button:hover { background: #FFD166; color: #14110E; border: none; }
.stButton > button:focus { box-shadow: none; }

[data-testid="stExpander"] {
    background: #221D17; border: 1px solid #2E2820; border-radius: 12px;
}
[data-testid="stChatMessage"] {
    background: #1F1B16; border: 1px solid #2E2820; border-radius: 14px;
    padding: 0.9rem 1rem; line-height: 1.6;
}
textarea, input, [data-baseweb="select"] > div {
    background: #221D17 !important; color: #F4EDE2 !important;
}
[data-testid="stChatInput"] textarea { background: #1F1B16 !important; }
.stAlert { border-radius: 12px; }
</style>
"""

st.set_page_config(page_title="Asper", page_icon="🎓", layout="centered")
st.markdown(CSS, unsafe_allow_html=True)

st.markdown('<div class="asper-title">Asper</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="asper-tagline">Your friendly career guide. Let\'s figure out your next step '
    "together, one simple question at a time.</div>",
    unsafe_allow_html=True,
)

# ---------- Session state ----------
if "profile" not in st.session_state:
    st.session_state.profile = {}
if "posting" not in st.session_state:
    st.session_state.posting = ""
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi! I'm Asper. Are you still exploring what to do next, or do you already have a career in mind?"}
    ]


def build_system_prompt(profile):
    """Add the saved profile to Asper's instructions, if one exists."""
    filled = {k: v for k, v in profile.items() if v}
    if not filled:
        return BASE_PROMPT
    details = "\n".join(f"- {label}: {value}" for label, value in filled.items())
    return (
        BASE_PROMPT
        + "\nUser profile (use it to personalize answers; don't repeat it back unless it helps):\n"
        + details
    )


def ask_asper(user_text, contents, system_text):
    """Show the user's message, get Asper's reply, and show it."""
    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    with st.chat_message("assistant"):
        with st.spinner("Asper is thinking..."):
            try:
                response = client.models.generate_content(
                    model=MODEL,
                    contents=contents,
                    config={"system_instruction": system_text},
                )
                reply = response.text
            except Exception:
                reply = (
                    "Sorry, Asper is busy right now. Please wait a minute and try again. "
                    "If it keeps happening, the free daily limit may be used up."
                )
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})


# ---------- Sidebar: three tools + reset ----------
with st.sidebar:
    st.markdown("### Your tools")

    with st.expander("👤 My profile", expanded=False):
        st.caption("Fill this in once. Asper uses it in every answer.")
        with st.form("intake"):
            degree = st.text_input("Degree or major", placeholder="e.g. BS Psychology")
            status = st.selectbox(
                "Where are you now?",
                ["Just graduated", "Graduating soon", "Graduated a year or more ago"],
            )
            skills = st.text_area("Skills you have", placeholder="e.g. Excel, Canva, research writing")
            interests = st.text_area("Things you enjoy", placeholder="e.g. helping people, sports, games")
            location = st.text_input("Where you'd like to work", placeholder="e.g. Manila, or remote")
            target = st.text_input("Dream job (leave blank if unsure)", placeholder="e.g. UX designer")
            if st.form_submit_button("Save profile"):
                st.session_state.profile = {
                    "Degree / major": degree.strip(),
                    "Graduation status": status,
                    "Skills": skills.strip(),
                    "Interests": interests.strip(),
                    "Preferred location": location.strip(),
                    "Target career": target.strip(),
                }
                st.success("Saved! Asper will use this from now on.")

    with st.expander("🔍 Job match check", expanded=False):
        st.caption("Paste a job posting to see how well you match it and what to work on.")
        st.session_state.posting = st.text_area(
            "Job posting", value=st.session_state.posting, height=180,
            placeholder="Paste the full job description here",
        )
        check_clicked = st.button("Check my match", type="primary")

    with st.expander("🗺️ My 90-day plan", expanded=False):
        st.caption("A step-by-step plan based on your dream job or the posting above.")
        plan_clicked = st.button("Build my plan", type="primary")

    st.divider()
    if st.button("Start a new chat"):
        st.session_state.messages = [
            {"role": "assistant", "content": "Fresh start! What would you like to work on?"}
        ]
        st.rerun()

profile = st.session_state.profile

# ---------- Example prompts for first-time users ----------
if len(st.session_state.messages) == 1:
    st.markdown("**Not sure where to start? Try one of these:**")
    cols = st.columns(len(EXAMPLES))
    for i, (col, example) in enumerate(zip(cols, EXAMPLES)):
        with col:
            if st.button(example, key=f"example_{i}", use_container_width=True):
                st.session_state.pending = example
                st.rerun()

# ---------- Chat history ----------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------- Run a tool or a chat message ----------
pending = st.session_state.pop("pending", None)

if check_clicked:
    if not st.session_state.posting.strip():
        st.warning("Paste a job posting in the sidebar first.")
    else:
        ask_asper(
            "Check my match for this job posting.",
            GAP_PROMPT.format(posting=st.session_state.posting.strip()),
            build_system_prompt(profile),
        )

elif plan_clicked:
    goal = profile.get("Target career", "")
    posting = st.session_state.posting.strip()
    if not goal and posting:
        goal = "the role described in the job posting"
    if not goal:
        st.warning("Add a dream job in My profile, or paste a job posting, first.")
    else:
        ask_asper(
            "Build my 90-day plan.",
            ROADMAP_PROMPT.format(goal=goal, posting=posting or "None provided"),
            build_system_prompt(profile),
        )

else:
    user_input = st.chat_input("Ask Asper anything about your career...") or pending
    if user_input:
        history = "\n".join(
            f"{m['role'].capitalize()}: {m['content']}" for m in st.session_state.messages
        ) + f"\nUser: {user_input}"
        ask_asper(user_input, history, build_system_prompt(profile))
