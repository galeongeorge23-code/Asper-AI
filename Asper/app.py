import streamlit as st
from google import genai

MODEL = "gemini-3.5-flash-lite"  # change here if you need to switch models

BASE_PROMPT = """You are Asper, a career guidance advisor for recent graduates.

Rules:
- Ask specific, concrete questions before giving advice. Never give generic advice like "network more" or "be a leader" without a concrete next step.
- Keep answers short, warm, and practical. Use plain language.
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


def ask_asper(user_text, system_text, contents):
    """Show the user's message, call the model, and show the reply."""
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
            except Exception as e:
                reply = f"Sorry, I couldn't reach the AI service right now. ({str(e)[:150]})"
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})


st.set_page_config(page_title="Asper", page_icon="🎓")
st.title("🎓 Asper")
st.caption("Career guidance for graduates")

import os
import streamlit as st
from google import genai

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

if "profile" not in st.session_state:
    st.session_state.profile = {}
if "posting" not in st.session_state:
    st.session_state.posting = ""
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi, I'm Asper. Set up your profile in the sidebar if you like, then tell me what you're thinking about. Are you exploring, or do you have a career in mind?"}
    ]

action = None  # which sidebar button was clicked this run

# ---------- Sidebar: three features ----------
with st.sidebar:
    with st.expander("👤 My profile", expanded=False):
        st.caption("Fill this in once. Asper uses it in every answer.")
        with st.form("intake"):
            degree = st.text_input("Degree / major", placeholder="e.g. BS Psychology")
            status = st.selectbox(
                "Graduation status",
                ["Just graduated", "Graduating soon", "Graduated a year or more ago"],
            )
            skills = st.text_area("Skills you have", placeholder="e.g. Excel, Canva, research writing")
            interests = st.text_area("Interests", placeholder="e.g. helping people, sports, games")
            location = st.text_input("Where you want to work", placeholder="e.g. Manila, or remote")
            target = st.text_input("Target career (leave blank if undecided)", placeholder="e.g. UX designer")
            if st.form_submit_button("Save profile"):
                st.session_state.profile = {
                    "Degree / major": degree.strip(),
                    "Graduation status": status,
                    "Skills": skills.strip(),
                    "Interests": interests.strip(),
                    "Preferred location": location.strip(),
                    "Target career": target.strip(),
                }
                st.success("Profile saved.")

    with st.expander("📋 Job posting check", expanded=False):
        st.caption("Paste a job posting and Asper will compare it to your profile.")
        st.session_state.posting = st.text_area(
            "Job posting", value=st.session_state.posting, height=200,
            placeholder="Paste the full job description here",
        )
        if st.button("Analyze my gap", type="primary"):
            action = "gap"

    with st.expander("🗺️ 90-day roadmap", expanded=False):
        st.caption("Uses your target career from My profile, or the job posting if you pasted one.")
        if st.button("Build my 90-day roadmap", type="primary"):
            action = "roadmap"

profile = st.session_state.profile

# ---------- Chat history ----------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------- Run the action or chat ----------
if action == "gap":
    if not st.session_state.posting.strip():
        st.warning("Paste a job posting in the sidebar first.")
    else:
        ask_asper(
            "Analyze my skills gap for this job posting.",
            build_system_prompt(profile),
            GAP_PROMPT.format(posting=st.session_state.posting.strip()),
        )

elif action == "roadmap":
    goal = profile.get("Target career", "")
    posting = st.session_state.posting.strip()
    if not goal and posting:
        goal = "the role described in the job posting"
    if not goal:
        st.warning("Add a target career in My profile, or paste a job posting, first.")
    else:
        ask_asper(
            "Build my 90-day roadmap.",
            build_system_prompt(profile),
            ROADMAP_PROMPT.format(goal=goal, posting=posting or "None provided"),
        )

elif user_input := st.chat_input("Type your message..."):
    history = "\n".join(
        f"{m['role'].capitalize()}: {m['content']}" for m in st.session_state.messages
    ) + f"\nUser: {user_input}"
    ask_asper(user_input, build_system_prompt(profile), history)