import os
import requests
import streamlit as st
import json
from requests.exceptions import JSONDecodeError
import time
import random

# Properly construct the API URL
base_url = os.getenv("BACKEND_URL",
                     "https://6c07-34-150-185-119.ngrok-free.app")
API = f"{base_url}/api/chat"

# Initialize session state variables
if "user" not in st.session_state:
    st.session_state.user = ""
if "logged" not in st.session_state:
    st.session_state.logged = False
if "token" not in st.session_state:
    st.session_state.token = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "waiting_for_response" not in st.session_state:
    st.session_state.waiting_for_response = False
if "personality_type" not in st.session_state:
    st.session_state.personality_type = None
if "sessions" not in st.session_state:
    st.session_state.sessions = []
if "view" not in st.session_state:
    st.session_state.view = "intro"  # Options: intro, mbti_test, loading, results, register, login, chat, profile
if "mbti_results" not in st.session_state:
    st.session_state.mbti_results = {
        "E": 0,
        "I": 0,
        "S": 0,
        "N": 0,
        "T": 0,
        "F": 0,
        "J": 0,
        "P": 0
    }
if "test_responses" not in st.session_state:
    st.session_state.test_responses = {}
if "personality_results" not in st.session_state:
    st.session_state.personality_results = None
if "current_page" not in st.session_state:
    st.session_state.current_page = 0

# Custom CSS for top-right login button
st.markdown("""
<style>
    div.stButton > button {
        background-color: #3B82F6;
        color: white;
        font-weight: bold;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 0.375rem;
    }
    div.stButton > button:hover {
        background-color: #2563EB;
    }
    .top-right-container {
        position: fixed;
        top: 1rem;
        right: 2rem;
        z-index: 1000;
        display: flex;
        align-items: center;
    }
    .user-info {
        margin-right: 1rem;
        color: #4B5563;
        font-weight: 500;
    }
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem 0;
    }
    .profile-card {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        background-color: #f9fafb;
    }
    .personality-card {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        background-color: white;
    }
    .personality-badge {
        display: inline-block;
        background-color: rgba(59, 130, 246, 0.1);
        color: #3B82F6;
        border-radius: 9999px;
        padding: 5px 12px;
        font-size: 14px;
        font-weight: 500;
        margin-bottom: 10px;
    }
    .trait-card {
        background-color: #f9fafb;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
    }
</style>
""",
            unsafe_allow_html=True)


# Top-right login/profile button
def render_top_right_button():
    if st.session_state.logged:
        with st.container():
            col1, col2, col3 = st.columns([6, 2, 2])
            with col3:
                if st.button("Logout", key="logout_button"):
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.session_state.view = "intro"
                    st.rerun()
            with col2:
                if st.button("Profile", key="profile_button"):
                    st.session_state.view = "profile"
                    st.rerun()
            with col1:
                st.markdown(f"""
                <div style="text-align: right; padding-right: 10px; color: #4B5563;">
                    Logged in as: <b>{st.session_state.user}</b>
                </div>
                """,
                            unsafe_allow_html=True)
    else:
        col1, col2 = st.columns([8, 2])
        with col2:
            if st.button("Login", key="login_button"):
                st.session_state.view = "login"
                st.rerun()


# Intro Screen
def intro_screen():
    render_top_right_button()

    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="font-size: 2rem; font-weight: 600; margin-bottom: 1rem;">Discover Your Personality Type</h1>
        <p style="font-size: 1.1rem; margin-bottom: 1.5rem;">Take this short personality assessment to receive personalized insights and advice for your challenges.</p>
    </div>
    """,
                unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="display: flex; align-items: center; margin-bottom: 1rem; font-size: 1.05rem;">
            <span style="margin-right: 0.75rem; font-size: 1.25rem;">⏱️</span>
            <span>Takes approximately 5-7 minutes</span>
        </div>
        """,
                    unsafe_allow_html=True)

        st.markdown("""
        <div style="display: flex; align-items: center; margin-bottom: 1rem; font-size: 1.05rem;">
            <span style="margin-right: 0.75rem; font-size: 1.25rem;">🛡️</span>
            <span>Your responses are private and secure</span>
        </div>
        """,
                    unsafe_allow_html=True)

        st.markdown("""
        <div style="display: flex; align-items: center; margin-bottom: 1.5rem; font-size: 1.05rem;">
            <span style="margin-right: 0.75rem; font-size: 1.25rem;">🤖</span>
            <span>AI-powered insights based on your responses</span>
        </div>
        """,
                    unsafe_allow_html=True)

        if st.button("Begin Assessment →", use_container_width=True):
            # Reset test data when starting a new test
            st.session_state.current_page = 0
            st.session_state.mbti_results = {
                "E": 0,
                "I": 0,
                "S": 0,
                "N": 0,
                "T": 0,
                "F": 0,
                "J": 0,
                "P": 0
            }
            st.session_state.test_responses = {}
            st.session_state.view = "mbti_test"
            st.rerun()


# MBTI Test function
def mbti_test():
    render_top_right_button()

    st.title("Personality Assessment")

    # Define test questions organized by pages
    pages = [{
        "title":
        "Your Social Interactions",
        "questions": [{
            "id": "q1",
            "text":
            "I prefer spending time with others rather than being alone.",
            "dimension": "E-I"
        }, {
            "id": "q2",
            "text": "I often take initiative in social situations.",
            "dimension": "E-I"
        }, {
            "id": "q3",
            "text":
            "I feel energized after spending time with a group of people.",
            "dimension": "E-I"
        }, {
            "id": "q4",
            "text":
            "I prefer to think out loud rather than reflect internally.",
            "dimension": "E-I"
        }, {
            "id": "q5",
            "text": "I find it easy to approach and talk to strangers.",
            "dimension": "E-I"
        }]
    }, {
        "title":
        "Your Information Processing",
        "questions": [{
            "id": "q6",
            "text":
            "I focus more on possibilities and the future than on concrete details.",
            "dimension": "S-N"
        }, {
            "id": "q7",
            "text": "I enjoy theoretical or abstract concepts.",
            "dimension": "S-N"
        }, {
            "id": "q8",
            "text":
            "I often notice patterns and connections that others miss.",
            "dimension": "S-N"
        }, {
            "id": "q9",
            "text": "I prefer innovation over following established methods.",
            "dimension": "S-N"
        }, {
            "id": "q10",
            "text":
            "I'm more interested in exploring ideas than practical applications.",
            "dimension": "S-N"
        }]
    }, {
        "title":
        "Your Decision Making",
        "questions": [{
            "id": "q11",
            "text": "I prioritize harmony and cooperation in decision making.",
            "dimension": "T-F"
        }, {
            "id": "q12",
            "text": "I consider how decisions will affect people's feelings.",
            "dimension": "T-F"
        }, {
            "id": "q13",
            "text":
            "I trust my emotional responses when making important choices.",
            "dimension": "T-F"
        }, {
            "id": "q14",
            "text": "I value empathy more than logic in resolving conflicts.",
            "dimension": "T-F"
        }, {
            "id": "q15",
            "text":
            "I'm motivated by a desire to help others fulfill their potential.",
            "dimension": "T-F"
        }]
    }, {
        "title":
        "Your Lifestyle Preferences",
        "questions": [{
            "id": "q16",
            "text":
            "I prefer to plan activities in advance rather than be spontaneous.",
            "dimension": "J-P"
        }, {
            "id": "q17",
            "text": "I like to have clear expectations and guidelines.",
            "dimension": "J-P"
        }, {
            "id": "q18",
            "text":
            "I find satisfaction in completing tasks and checking them off my list.",
            "dimension": "J-P"
        }, {
            "id": "q19",
            "text": "I prefer environments that are orderly and structured.",
            "dimension": "J-P"
        }, {
            "id": "q20",
            "text": "I feel anxious when plans change at the last minute.",
            "dimension": "J-P"
        }]
    }]

    current_page = pages[st.session_state.current_page]

    # Display progress bar
    progress = (st.session_state.current_page) / (len(pages))
    st.progress(progress)

    # Display page title
    st.subheader(current_page["title"])

    # Display questions for current page
    for question in current_page["questions"]:
        response = st.slider(question["text"],
                             min_value=1,
                             max_value=5,
                             value=st.session_state.test_responses.get(
                                 question["id"], 3),
                             key=f"slider_{question['id']}",
                             help="1 = Strongly Disagree, 5 = Strongly Agree")

        # Save response
        st.session_state.test_responses[question["id"]] = response

        # Update MBTI results based on response
        dimension = question["dimension"]
        if dimension == "E-I":
            if response > 3:
                st.session_state.mbti_results["E"] += 1
            elif response < 3:
                st.session_state.mbti_results["I"] += 1
        elif dimension == "S-N":
            if response > 3:
                st.session_state.mbti_results["N"] += 1
            elif response < 3:
                st.session_state.mbti_results["S"] += 1
        elif dimension == "T-F":
            if response > 3:
                st.session_state.mbti_results["F"] += 1
            elif response < 3:
                st.session_state.mbti_results["T"] += 1
        elif dimension == "J-P":
            if response > 3:
                st.session_state.mbti_results["J"] += 1
            elif response < 3:
                st.session_state.mbti_results["P"] += 1

    # Navigation buttons
    col1, col2 = st.columns(2)

    with col1:
        if st.session_state.current_page > 0:
            if st.button("← Previous", use_container_width=True):
                st.session_state.current_page -= 1
                st.rerun()

    with col2:
        if st.session_state.current_page < len(pages) - 1:
            if st.button("Next →", use_container_width=True):
                st.session_state.current_page += 1
                st.rerun()
        else:
            # Final page - add challenge question
            st.subheader("Your Current Challenge")
            challenge = st.text_area(
                "What is the next challenge you need to solve today?",
                value=st.session_state.get("challenge", ""),
                height=150,
                placeholder="Describe the challenge you're facing...")
            st.session_state.challenge = challenge

            if st.button("Submit Results", use_container_width=True):
                if not challenge:
                    st.error(
                        "Please describe your current challenge before submitting."
                    )
                else:
                    # Determine MBTI type
                    mbti_type = ""
                    mbti_type += "E" if st.session_state.mbti_results[
                        "E"] >= st.session_state.mbti_results["I"] else "I"
                    mbti_type += "N" if st.session_state.mbti_results[
                        "N"] >= st.session_state.mbti_results["S"] else "S"
                    mbti_type += "F" if st.session_state.mbti_results[
                        "F"] >= st.session_state.mbti_results["T"] else "T"
                    mbti_type += "J" if st.session_state.mbti_results[
                        "J"] >= st.session_state.mbti_results["P"] else "P"

                    st.session_state.personality_type = mbti_type
                    st.session_state.problem_statement = challenge

                    # Move to loading screen
                    st.session_state.view = "loading"
                    st.rerun()


# Loading Screen
def loading_screen():
    render_top_right_button()

    st.markdown("""
    <div style="text-align: center; padding: 3rem 0;">
        <div style="display: inline-flex; align-items: center; padding: 0.5rem 1rem; font-weight: 600; font-size: 0.875rem; 
                    box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05); border-radius: 0.375rem; color: white; 
                    background-color: #3B82F6; transition: ease-in-out 150ms; cursor: not-allowed;">
            <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Processing your responses...
        </div>
        <p style="margin-top: 1rem; color: #4B5563;">Our AI is analyzing your personality traits and generating personalized insights.</p>
    </div>
    """,
                unsafe_allow_html=True)

    # Simulate processing time
    time.sleep(2)

    # Generate mock results (in a real app, this would come from an API)
    mbti_type = st.session_state.personality_type
    challenge = st.session_state.problem_statement

    # Mock personality descriptions
    descriptions = {
        "INTJ": "INTJ - The Architect - Strategic, innovative, and private",
        "INTP": "INTP - The Logician - Analytical, objective, and curious",
        "ENTJ": "ENTJ - The Commander - Decisive, efficient, and structured",
        "ENTP":
        "ENTP - The Debater - Quick-thinking, outspoken, and innovative",
        "INFJ": "INFJ - The Advocate - Insightful, principled, and idealistic",
        "INFP":
        "INFP - The Mediator - Compassionate, creative, and introspective",
        "ENFJ":
        "ENFJ - The Protagonist - Charismatic, empathetic, and inspiring",
        "ENFP": "ENFP - The Campaigner - Enthusiastic, creative, and sociable",
        "ISTJ":
        "ISTJ - The Logistician - Practical, detail-oriented, and reliable",
        "ISFJ": "ISFJ - The Defender - Dedicated, warm, and conscientious",
        "ESTJ": "ESTJ - The Executive - Organized, practical, and direct",
        "ESFJ":
        "ESFJ - The Consul - Supportive, organized, and people-oriented",
        "ISTP": "ISTP - The Virtuoso - Practical, logical, and adaptable",
        "ISFP": "ISFP - The Adventurer - Flexible, artistic, and sensitive",
        "ESTP": "ESTP - The Entrepreneur - Energetic, perceptive, and bold",
        "ESFP":
        "ESFP - The Entertainer - Spontaneous, energetic, and enthusiastic"
    }

    # Generate strengths based on type and challenge
    strengths_by_type = {
        "INTJ": [
            "Strategic thinking and long-term planning",
            "Ability to see patterns and connections",
            "Independent problem-solving"
        ],
        "INTP": [
            "Analytical approach to challenges",
            "Creative thinking outside conventional boundaries",
            "Ability to identify logical inconsistencies"
        ],
        "ENTJ": [
            "Natural leadership in difficult situations",
            "Efficiency in organizing resources", "Direct communication style"
        ],
        "ENTP": [
            "Innovative approach to problem-solving",
            "Adaptability to changing circumstances",
            "Enthusiasm for intellectual challenges"
        ],
        "INFJ": [
            "Deep insight into people's motivations",
            "Long-term vision and planning",
            "Strong personal values as guidance"
        ],
        "INFP": [
            "Strong empathy and understanding",
            "Creative approach to personal challenges",
            "Alignment with personal values"
        ],
        "ENFJ": [
            "Natural ability to inspire others",
            "Empathetic understanding of people's needs",
            "Organized approach to helping others"
        ],
        "ENFP": [
            "Enthusiasm and positive energy", "Creative problem-solving",
            "Ability to see possibilities"
        ],
        "ISTJ": [
            "Methodical approach to challenges",
            "Attention to important details", "Reliability and follow-through"
        ],
        "ISFJ": [
            "Practical support and assistance",
            "Detailed memory of what works", "Dedication to completing tasks"
        ],
        "ESTJ": [
            "Practical organization of resources",
            "Clear communication of expectations",
            "Efficiency in implementing solutions"
        ],
        "ESFJ": [
            "Strong awareness of others' needs", "Practical help and support",
            "Organization of social resources"
        ],
        "ISTP": [
            "Practical hands-on problem solving",
            "Adaptability to immediate needs",
            "Efficiency with technical challenges"
        ],
        "ISFP": [
            "Adaptability to changing situations", "Practical creativity",
            "Living in the present moment"
        ],
        "ESTP": [
            "Quick reaction to immediate problems",
            "Practical negotiation skills", "Energy for hands-on solutions"
        ],
        "ESFP": [
            "Enthusiasm and positive approach", "Practical help in the moment",
            "Social connections and resources"
        ]
    }

    # Generate weaknesses based on type and challenge
    weaknesses_by_type = {
        "INTJ": [
            "May overlook emotional aspects of the situation",
            "Can be overly critical of others' approaches",
            "Might struggle with short-term adaptability"
        ],
        "INTP": [
            "May get lost in theoretical possibilities",
            "Can struggle with practical implementation",
            "Might overlook emotional considerations"
        ],
        "ENTJ": [
            "May be too directive or controlling",
            "Can overlook emotional impacts",
            "Might be impatient with slower processes"
        ],
        "ENTP": [
            "May leave projects unfinished", "Can overlook important details",
            "Might struggle with routine aspects"
        ],
        "INFJ": [
            "May have unrealistically high expectations",
            "Can take criticism too personally",
            "Might struggle with practical details"
        ],
        "INFP": [
            "May avoid necessary conflict",
            "Can struggle with practical implementation",
            "Might be too idealistic"
        ],
        "ENFJ": [
            "May take on too much responsibility", "Can neglect own needs",
            "Might be overly sensitive to criticism"
        ],
        "ENFP": [
            "May struggle with follow-through", "Can be easily distracted",
            "Might avoid necessary details"
        ],
        "ISTJ": [
            "May resist necessary changes", "Can be inflexible in approach",
            "Might miss creative possibilities"
        ],
        "ISFJ": [
            "May avoid necessary conflict",
            "Can take on too much responsibility",
            "Might struggle with assertiveness"
        ],
        "ESTJ": [
            "May be too focused on rules and procedures", "Can be inflexible",
            "Might overlook emotional considerations"
        ],
        "ESFJ": [
            "May be too concerned with others' approval",
            "Can neglect own needs", "Might avoid necessary conflict"
        ],
        "ISTP": [
            "May focus too much on immediate solutions",
            "Can be impatient with theory", "Might avoid long-term planning"
        ],
        "ISFP": [
            "May avoid necessary conflict",
            "Can struggle with long-term planning",
            "Might be too focused on the present"
        ],
        "ESTP": [
            "May focus too much on immediate results",
            "Can be impatient with planning", "Might take unnecessary risks"
        ],
        "ESFP": [
            "May avoid difficult but necessary tasks",
            "Can be distracted by social opportunities",
            "Might struggle with long-term planning"
        ]
    }

    # Generate traits to develop
    traits_by_type = [{
        "trait":
        "Strategic Patience",
        "explanation":
        f"As a {mbti_type}, you tend to focus on quick solutions. Developing strategic patience will help you consider long-term implications before acting.",
        "action_steps":
        "Practice waiting 24 hours before making important decisions. Use this time to consider potential long-term consequences."
    }, {
        "trait":
        "Emotional Awareness",
        "explanation":
        f"Your {mbti_type} personality excels at logical analysis but may overlook emotional factors. Developing this trait will help you navigate interpersonal aspects of your challenge.",
        "action_steps":
        "Start a daily emotion journal. Identify and name your feelings about your current challenge and consider how emotions might be influencing others involved."
    }, {
        "trait":
        "Practical Implementation",
        "explanation":
        f"While your {mbti_type} type gives you visionary strengths, turning ideas into concrete action steps can be challenging. This trait will help bridge the gap between theory and practice.",
        "action_steps":
        "Break down your challenge into small, specific tasks with deadlines. Focus on completing one small step each day."
    }]

    # Create results object
    results = {
        "personalityType":
        mbti_type,
        "description":
        descriptions.get(mbti_type,
                         f"{mbti_type} - Analytical and thoughtful"),
        "strengths":
        json.dumps(
            random.sample(
                strengths_by_type.get(mbti_type, strengths_by_type["INTJ"]),
                3)),
        "weaknesses":
        json.dumps(
            random.sample(
                weaknesses_by_type.get(mbti_type, weaknesses_by_type["INTJ"]),
                3)),
        "traits":
        json.dumps(traits_by_type)
    }

    st.session_state.personality_results = results
    st.session_state.view = "results"
    st.rerun()


# Get welcome message for a session
def get_welcome_message(session_id):
    try:
        # Send a simple greeting to trigger the welcome message
        r = requests.post(
            API,
            json={
                "message": "Hello",
                "session_id": session_id
            },
            headers={"Authorization": f"Bearer {st.session_state.token}"},
            timeout=30)
        r.raise_for_status()

        data = r.json()
        if "response" in data:
            return data["response"]
        else:
            return "Welcome to your personality coaching session. How can I help you today?"
    except Exception as e:
        st.error(f"Failed to get welcome message: {e}")
        return "Welcome to your personality coaching session. How can I help you today?"


# Results View
def results_view():
    render_top_right_button()

    results = st.session_state.personality_results

    # Parse the personality type and description
    personality_type = results.get("personalityType", "Unknown")
    description = results.get("description", "")

    # Split the description if it contains separators
    parts = description.split(" - ")
    type_name = parts[1] if len(parts) > 1 else ""
    type_desc = parts[2] if len(parts) > 2 else ""

    # Display personality type header
    st.title(f"{personality_type}")
    st.subheader(type_name)
    st.write(type_desc)

    st.markdown("---")

    # Strengths & Weaknesses section
    st.subheader("Strengths & Potential Challenges")

    col1, col2 = st.columns(2)

    # Parse strengths
    with col1:
        st.markdown("**Strengths:**")
        try:
            strengths = json.loads(results.get("strengths", "[]"))
            for strength in strengths:
                st.markdown(f"- ✅ {strength}")
        except:
            st.write(results.get("strengths", "No strengths data available"))

    # Parse weaknesses
    with col2:
        st.markdown("**Potential Challenges:**")
        try:
            weaknesses = json.loads(results.get("weaknesses", "[]"))
            for weakness in weaknesses:
                st.markdown(f"- ❌ {weakness}")
        except:
            st.write(results.get("weaknesses", "No challenges data available"))

    st.markdown("---")

    # Traits to Develop section
    st.subheader("Traits to Develop")

    try:
        traits = json.loads(results.get("traits", "[]"))
        for trait in traits:
            st.markdown(f"**{trait.get('trait', 'Unnamed Trait')}**")
            st.write(trait.get("explanation", ""))
            with st.expander("Action Steps"):
                st.write(trait.get("action_steps", ""))
    except:
        st.write(results.get("traits", "No traits data available"))

    st.markdown("---")

    # Begin Chat button or Register/Login prompt
    if st.session_state.logged:
        # If user is already logged in, update their profile with new personality results
        try:
            update_url = f"{base_url}/api/profile"
            r = requests.put(
                update_url,
                json={
                    "personality_type": personality_type,
                    "problem_statement": st.session_state.problem_statement,
                    "personality_results": results
                },
                headers={"Authorization": f"Bearer {st.session_state.token}"},
                timeout=10)
            r.raise_for_status()

            # Update session state
            st.session_state.personality_type = personality_type
        except Exception as e:
            st.error(
                f"Failed to update profile with new personality results: {e}")

        if st.button("💬 Begin Chat with Your Personalality coach Gandalf",
                     use_container_width=True):
            # Create a new session with the updated personality type
            try:
                session_url = f"{base_url}/api/sessions/new"
                r = requests.post(session_url,
                                  json={
                                      "session_name":
                                      "New Chat",
                                      "personality_type":
                                      personality_type,
                                      "problem_statement":
                                      st.session_state.problem_statement
                                  },
                                  headers={
                                      "Authorization":
                                      f"Bearer {st.session_state.token}"
                                  },
                                  timeout=10)
                r.raise_for_status()
                data = r.json()

                # Set the current session
                st.session_state.current_session_id = data["session_id"]
                st.session_state.messages = []

                # Reload sessions
                load_sessions()

                # Go to chat view
                st.session_state.view = "chat"
                st.rerun()
            except Exception as e:
                st.error(f"Failed to create new chat session: {e}")
                st.session_state.view = "chat"
                st.rerun()
    else:
        st.info(
            "Register or login to chat with your personality coach Gandalf")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Register", use_container_width=True):
                st.session_state.view = "register"
                st.rerun()
        with col2:
            if st.button("Login", use_container_width=True):
                st.session_state.view = "login"
                st.rerun()


# Registration function
def register_view():
    render_top_right_button()

    st.title("Create Your Account")

    # Display personality type from MBTI test
    if st.session_state.personality_type:
        st.info(f"Your MBTI type: {st.session_state.personality_type}")

    username = st.text_input("Choose Username")
    password = st.text_input("Choose Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Create Account", use_container_width=True):
            if not username or not password:
                st.error("Username and password are required")
            elif password != confirm_password:
                st.error("Passwords do not match")
            else:
                try:
                    register_url = f"{base_url}/api/register"
                    r = requests.post(
                        register_url,
                        json={
                            "username":
                            username,
                            "password":
                            password,
                            "personality_type":
                            st.session_state.personality_type,
                            "problem_statement":
                            st.session_state.get("problem_statement", ""),
                            "personality_results":
                            st.session_state.
                            personality_results  # Include full results
                        },
                        timeout=10)
                    r.raise_for_status()

                    st.success("Registration successful! You can now log in.")

                    # Auto-login after registration
                    login_url = f"{base_url}/api/login"
                    r = requests.post(login_url,
                                      json={
                                          "username": username,
                                          "password": password
                                      },
                                      timeout=10)
                    r.raise_for_status()
                    data = r.json()

                    # Store authentication data
                    st.session_state.token = data["token"]
                    st.session_state.user_id = data["user_id"]
                    st.session_state.user = username
                    st.session_state.logged = True

                    # Load sessions
                    load_sessions()

                    # Go to chat view
                    st.session_state.view = "chat"
                    st.rerun()

                except Exception as e:
                    st.error(f"Registration failed: {e}")

    with col2:
        if st.button("Already have an account? Log in",
                     use_container_width=True):
            st.session_state.view = "login"
            st.rerun()


# Login function
def login_view():
    render_top_right_button()

    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Login",
                     use_container_width=True) and username and password:
            try:
                login_url = f"{base_url}/api/login"
                r = requests.post(login_url,
                                  json={
                                      "username": username,
                                      "password": password
                                  },
                                  timeout=10)
                r.raise_for_status()
                data = r.json()

                # Store authentication data
                st.session_state.token = data["token"]
                st.session_state.user_id = data["user_id"]
                st.session_state.user = username
                st.session_state.personality_type = data.get(
                    "personality_type", "INTJ")
                st.session_state.logged = True

                # Load sessions
                load_sessions()

                # Go to chat view
                st.session_state.view = "chat"
                st.rerun()

            except Exception as e:
                st.error(f"Login failed: {e}")

    with col2:
        if st.button("Take Personality Test", use_container_width=True):
            st.session_state.view = "intro"
            st.rerun()


# Load user's chat sessions
def load_sessions():
    try:
        sessions_url = f"{base_url}/api/sessions"
        r = requests.get(
            sessions_url,
            headers={"Authorization": f"Bearer {st.session_state.token}"},
            timeout=10)
        r.raise_for_status()
        data = r.json()
        st.session_state.sessions = data.get("sessions", [])
    except Exception as e:
        st.error(f"Failed to load chat sessions: {e}")


# Get or create a chat session
def get_or_create_session():
    # Try to get existing sessions
    if not st.session_state.sessions:
        load_sessions()

    # If there are existing sessions, use the first one
    if st.session_state.sessions:
        return st.session_state.sessions[0]["_id"]

    # Otherwise create a new session
    try:
        session_url = f"{base_url}/api/sessions/new"
        r = requests.post(
            session_url,
            json={
                "session_name": "New Chat",
                "personality_type": st.session_state.personality_type,
                "problem_statement":
                st.session_state.get("problem_statement", "")
            },
            headers={"Authorization": f"Bearer {st.session_state.token}"},
            timeout=10)
        r.raise_for_status()
        data = r.json()

        # Reload sessions
        load_sessions()

        return data["session_id"]
    except Exception as e:
        st.error(f"Failed to create chat session: {e}")
        return None


# Load chat history for a specific session
def load_chat_history(session_id):
    try:
        session_url = f"{base_url}/api/sessions/{session_id}"
        r = requests.get(
            session_url,
            headers={"Authorization": f"Bearer {st.session_state.token}"},
            timeout=10)
        r.raise_for_status()
        data = r.json()
        return data["session"]["messages"]
    except Exception as e:
        st.error(f"Failed to load chat history: {e}")
        return []


# Create a new chat session
def create_new_session():
    try:
        session_url = f"{base_url}/api/sessions/new"
        r = requests.post(
            session_url,
            json={
                "session_name": "New Chat",
                "personality_type": st.session_state.personality_type,
                "problem_statement":
                st.session_state.get("problem_statement", "")
            },
            headers={"Authorization": f"Bearer {st.session_state.token}"},
            timeout=10)
        r.raise_for_status()
        data = r.json()

        # Update current session
        st.session_state.current_session_id = data["session_id"]
        st.session_state.messages = [
        ]  # Clear messages so welcome message will be triggered

        # Reload sessions
        load_sessions()

        st.rerun()
    except Exception as e:
        st.error(f"Failed to create new session: {e}")


# End current chat session (summarize and rename)
def end_current_session():
    if not st.session_state.current_session_id:
        return

    try:
        end_url = f"{base_url}/api/sessions/{st.session_state.current_session_id}/end"
        r = requests.post(
            end_url,
            headers={"Authorization": f"Bearer {st.session_state.token}"},
            timeout=10)
        r.raise_for_status()
        data = r.json()

        # Show summary
        st.success(
            f"Chat summarized as: {''.join(data['summary'].split()[:-2])}")

        # Reload sessions
        load_sessions()

        # Create new session
        create_new_session()
    except Exception as e:
        st.error(f"Failed to end session: {e}")


# Delete a chat session
def delete_session(session_id):
    try:
        delete_url = f"{base_url}/api/sessions/{session_id}"
        r = requests.delete(
            delete_url,
            headers={"Authorization": f"Bearer {st.session_state.token}"},
            timeout=10)
        r.raise_for_status()

        # If the deleted session is the current one, clear it
        if st.session_state.current_session_id == session_id:
            st.session_state.current_session_id = None
            st.session_state.messages = []

        # Reload sessions
        load_sessions()

        st.rerun()
    except Exception as e:
        st.error(f"Failed to delete session: {e}")


# User profile view
def profile_view():
    render_top_right_button()

    st.title("User Profile")

    try:
        # Get current profile
        profile_url = f"{base_url}/api/profile"
        r = requests.get(
            profile_url,
            headers={"Authorization": f"Bearer {st.session_state.token}"},
            timeout=10)
        r.raise_for_status()
        profile = r.json()

        # Get available MBTI types
        mbti_url = f"{base_url}/api/mbti/types"
        r = requests.get(mbti_url, timeout=10)
        r.raise_for_status()
        mbti_types = r.json().get("types", [])

        # Display current profile in a card
        st.markdown('<div class="profile-card">', unsafe_allow_html=True)

        # Username and personality type
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div style="display: flex; align-items: center; margin-bottom: 15px;">
                <div style="background-color: #f0f2f6; border-radius: 50%; width: 40px; height: 40px; 
                            display: flex; align-items: center; justify-content: center; margin-right: 15px;">
                    <span style="font-size: 20px;">👤</span>
                </div>
                <div>
                    <p style="margin: 0; color: #888; font-size: 14px;">Username</p>
                    <p style="margin: 0; font-weight: 600; font-size: 18px;">{profile.get('username', 'Unknown')}</p>
                </div>
            </div>
            """,
                        unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div style="display: flex; align-items: center; margin-bottom: 15px;">
                <div style="background-color: #f0f2f6; border-radius: 50%; width: 40px; height: 40px; 
                            display: flex; align-items: center; justify-content: center; margin-right: 15px;">
                    <span style="font-size: 20px;">🧠</span>
                </div>
                <div>
                    <p style="margin: 0; color: #888; font-size: 14px;">Personality Type</p>
                    <p style="margin: 0; font-weight: 600; font-size: 18px;">{profile.get('personality_type', 'Unknown')}</p>
                </div>
            </div>
            """,
                        unsafe_allow_html=True)

        # Problem statement
        st.markdown(f"""
        <div style="margin-top: 10px;">
            <p style="margin: 0; color: #888; font-size: 14px;">Current Challenge</p>
            <p style="margin: 0; font-size: 16px;">{profile.get('problem_statement', 'No challenge specified')}</p>
        </div>
        """,
                    unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # Display personality results if available
        if profile.get("personality_results"):
            st.subheader("Your Personality Profile")

            results = profile.get("personality_results")

            # Create a card for personality type description
            st.markdown('<div class="personality-card">',
                        unsafe_allow_html=True)

            # Display personality type with badge
            personality_type = results.get(
                "personalityType", profile.get("personality_type", "Unknown"))
            description = results.get("description", "")

            # Split the description if it contains separators
            parts = description.split(" - ")
            type_name = parts[1] if len(parts) > 1 else ""
            type_desc = parts[2] if len(parts) > 2 else ""

            st.markdown(
                f'<div class="personality-badge">Your Personality Type</div>',
                unsafe_allow_html=True)
            st.markdown(f"### {personality_type} - {type_name}")
            st.write(type_desc)

            st.markdown('</div>', unsafe_allow_html=True)

            # Display strengths and weaknesses
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### Strengths")
                try:
                    strengths = json.loads(results.get("strengths", "[]"))
                    for strength in strengths:
                        st.markdown(f"- ✅ {strength}")
                except:
                    st.write(
                        results.get("strengths",
                                    "No strengths data available"))

            with col2:
                st.markdown("#### Potential Challenges")
                try:
                    weaknesses = json.loads(results.get("weaknesses", "[]"))
                    for weakness in weaknesses:
                        st.markdown(f"- ❌ {weakness}")
                except:
                    st.write(
                        results.get("weaknesses",
                                    "No challenges data available"))

            # Display traits to develop
            st.markdown("#### Traits to Develop")
            try:
                traits = json.loads(results.get("traits", "[]"))
                for trait in traits:
                    with st.expander(trait.get("trait", "Unnamed Trait")):
                        st.write(trait.get("explanation", ""))
                        st.markdown("**Action Steps:**")
                        st.write(trait.get("action_steps", ""))
            except:
                st.write(results.get("traits", "No traits data available"))
        else:
            st.info(
                "You haven't taken the personality test yet. Take the test to see your full personality profile."
            )
            if st.button("Take Personality Test"):
                st.session_state.view = "intro"
                st.rerun()

        # Form for updating profile
        st.subheader("Update Profile")

        # MBTI type selection
        current_type = profile.get("personality_type", "INTJ")
        new_type = st.selectbox("MBTI Personality Type",
                                mbti_types,
                                index=mbti_types.index(current_type)
                                if current_type in mbti_types else 0)

        # Problem statement
        current_problem = profile.get("problem_statement", "")
        new_problem = st.text_area("What's your main concern or problem?",
                                   value=current_problem)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Update Profile", use_container_width=True):
                try:
                    update_url = f"{base_url}/api/profile"
                    r = requests.put(update_url,
                                     json={
                                         "personality_type": new_type,
                                         "problem_statement": new_problem
                                     },
                                     headers={
                                         "Authorization":
                                         f"Bearer {st.session_state.token}"
                                     },
                                     timeout=10)
                    r.raise_for_status()

                    # Update session state
                    st.session_state.personality_type = new_type

                    st.success("Profile updated successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to update profile: {e}")

        with col2:
            if st.button("Back to Chat", use_container_width=True):
                st.session_state.view = "chat"
                st.rerun()

    except Exception as e:
        st.error(f"Failed to load profile: {e}")

        if st.button("Back to Chat"):
            st.session_state.view = "chat"
            st.rerun()


import re


def format_response(text):
    # Remove all citation markers [number]
    cleaned_text = re.sub(r'\[\d+\]', '', text)

    idx = cleaned_text.rfind('.')
    return cleaned_text[:idx + 1] if idx != -1 else cleaned_text

    # # Split the text by lines to preserve structure
    # lines = cleaned_text.split('\n')
    # formatted_lines = []

    # for line in lines:
    #     # Process each line to ensure it ends with complete sentences
    #     if line.strip():  # Skip empty lines
    #         # Check if the line ends with proper sentence punctuation
    #         if not re.search(r'[.!?]$', line.strip()):
    #             # Find the last complete sentence in this line
    #             sentence_ends = list(re.finditer(r'[.!?](?:\s|$)', line))
    #             if sentence_ends:
    #                 # Keep only up to the last complete sentence
    #                 last_end = sentence_ends[-1].end()
    #                 line = line[:last_end]

    #         # Only add non-empty lines after processing
    #         if line.strip():
    #             formatted_lines.append(line)

    # # Join the lines back preserving the original structure
    # formatted_text = '\n'.join(formatted_lines)

    # Wrap in HTML with consistent font size and preserve whitespace
    # html_output = f'<div style="font-size:16px; white-space: pre-wrap;">{formatted_text}</div>'

    # return html_output


# To use this in your Streamlit app, modify your chat_view function:
def display_formatted_message(message):
    role = message["role"]
    content = message["content"]

    if role == "user":
        st.chat_message("user").write(content)
    else:
        # Format assistant responses
        formatted_content = format_response(content)
        st.chat_message("assistant").markdown(formatted_content,
                                              unsafe_allow_html=True)


# Then in your chat_view function, replace:
# st.chat_message("user" if role == "user" else "assistant").write(content)
# with:
# display_formatted_message(message)


# Main chat interface
def chat_view():

    render_top_right_button()

    # Set up the layout with sidebar
    with st.sidebar:
        st.title("Chat Sessions")

        # User info and profile button
        # st.write(f"Logged in as: {st.session_state.user}")
        st.write(f"Personality Type: {st.session_state.personality_type}")

        if st.button("View/Edit Profile"):
            st.session_state.view = "profile"
            st.rerun()

        # New chat button
        if st.button("New Chat"):
            create_new_session()

        # End current chat button
        if st.button("End Current Chat"):
            end_current_session()

        # Display chat sessions
        st.subheader("Your Conversations")
        for session in st.session_state.sessions:
            col1, col2 = st.columns([4, 1])
            with col1:
                if st.button(session.get("session_name", "Unnamed"),
                             key=f"session_{session['_id']}"):
                    st.session_state.current_session_id = session["_id"]
                    st.session_state.messages = load_chat_history(
                        session["_id"])
                    st.rerun()
            with col2:
                if st.button("🗑️", key=f"delete_{session['_id']}"):
                    delete_session(session["_id"])

    # Main chat area
    st.title("GandalfBot")

    # Get or create a session if none is selected
    if not st.session_state.current_session_id:
        session_id = get_or_create_session()
        if session_id:
            st.session_state.current_session_id = session_id
            st.session_state.messages = load_chat_history(session_id)

    # If this is a new session with no messages, send an initial greeting
    if not st.session_state.messages:
        try:
            # Send an initial message to trigger the welcome message
            r = requests.post(
                API,
                json={
                    "message": "Hello",
                    "session_id": st.session_state.current_session_id
                },
                headers={"Authorization": f"Bearer {st.session_state.token}"},
                timeout=30)
            r.raise_for_status()

            data = r.json()
            if "response" in data:
                # Display welcome message
                welcome_message = data["response"]
                st.chat_message("assistant").write(welcome_message)

                # Update session state with welcome message
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": welcome_message
                })
            else:
                st.error("Failed to get welcome message")
        except Exception as e:
            st.error(f"Failed to get welcome message: {e}")

    # Display chat history
    else:
        for message in st.session_state.messages:
            role = message["role"]
            content = message["content"]
            # st.chat_message("user" if role == "user" else "assistant").write(
            #     content)
            display_formatted_message(message)

    # Chat input with disabled state during response generation
    if prompt := st.chat_input("Type your message here...",
                               disabled=st.session_state.waiting_for_response):
        # Set waiting flag
        st.session_state.waiting_for_response = True

        # Add user message to UI and session state
        st.chat_message("user").write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        try:
            # Send to backend
            r = requests.post(
                API,
                json={
                    "message": prompt,
                    "session_id": st.session_state.current_session_id
                },
                headers={"Authorization": f"Bearer {st.session_state.token}"},
                timeout=30)
            r.raise_for_status()

            data = r.json()
            if "response" not in data:
                st.error(
                    f"❌ JSON missing expected key:\n\n{json.dumps(data, indent=2)}"
                )
                st.session_state.waiting_for_response = False
                return

            # Display assistant response
            assistant_reply = data["response"]
            st.chat_message("assistant").write(assistant_reply)

            # Update session state with assistant response
            st.session_state.messages.append({
                "role": "assistant",
                "content": assistant_reply
            })

        except JSONDecodeError:
            st.error(
                f"❌ Invalid JSON returned (status {r.status_code}):\n\n{r.text}"
            )
        except Exception as e:
            st.error(f"❌ Request failed: {e}")
        finally:
            # Reset waiting flag
            st.session_state.waiting_for_response = False
            # Force a rerun to update the UI
            st.rerun()


# Main app logic
def main():
    if st.session_state.view == "intro":
        intro_screen()
    elif st.session_state.view == "mbti_test":
        mbti_test()
    elif st.session_state.view == "loading":
        loading_screen()
    elif st.session_state.view == "results":
        results_view()
    elif st.session_state.view == "register":
        register_view()
    elif st.session_state.view == "login":
        login_view()
    elif st.session_state.view == "profile":
        profile_view()
    elif st.session_state.view == "chat":
        chat_view()
    else:
        st.error("Unknown view")
        st.session_state.view = "intro"
        st.rerun()


# Fixed footer at bottom
footer = """
<style>
.footer {
    position: fixed;
    bottom: 0;
    # width: 100%;
    text-align: center;
    padding: 10px;
    # background-color: #f0f2f6;
    # border-top: 1px solid #e6e6e6;
    font-size: 14px;
    z-index: 9999;
}
.footer a {
    text-decoration: none;
    color: red;
    font-weight: bold;
    text-align: center
}
</style>

<div class="footer">
    <a href='https://www.apa.org/topics/crisis-hotlines' target='_blank'>
        Crisis Hotline
    </a>
</div>
"""

st.markdown(footer, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
