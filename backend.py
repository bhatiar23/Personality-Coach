from flask import Flask, request, jsonify
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig
from flask_cors import CORS
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
import bcrypt
import jwt
from datetime import datetime, timedelta
import os
from pyngrok import ngrok
import json
from huggingface_hub import login
import random

import logging
from datetime import datetime


# Use your API key for login to use huggingface
api_key = "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"

# Perform login
login(token=api_key)

print("Logged in to Hugging Face with provided API key.")

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configure MongoDB
app.config["MONGO_URI"] = "mongodb+srv://bhatiar:rmDVy59P6WoogZLo@artist-search-cluster.2zmat.mongodb.net/chat_db?retryWrites=true&w=majority&appName=artist-search-cluster"
mongo = PyMongo(app)
db = mongo.db
supporters = db.supporters

@app.route('/api/health', methods=['GET'])
def health_check():
    try:
        # Test MongoDB connection
        mongo.db.command('ping')
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return jsonify({
        "status": "ok",
        "mongodb": db_status,
        "timestamp": datetime.now().isoformat()
    })

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'b0b682577f2c7c6e7f1c8e0797545edd821c6b3a7c5b22ef74965d50cd2b8b5b')

# # Model Loading
# MODEL_NAME = "sugilee/DeepSeek-R1-Distill-Llama-8B-MentalHealth"

# print("Loading model...")
# tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
# model = AutoModelForCausalLM.from_pretrained(
#     MODEL_NAME,
#     device_map="auto",                     # auto‑map layers across GPU/CPU
#     load_in_8bit=True,                     # 8‑bit quantization
#     llm_int8_enable_fp32_cpu_offload=True, # offload fp32 weights to CPU
#     torch_dtype=torch.float16
# )
# gen_config = GenerationConfig(
#     temperature=0.7,
#     top_p=0.9,
#     max_new_tokens=256,
#     do_sample=True
# )
# print("Model loaded!")

# Add Perplexity API client setup
from openai import OpenAI
import os

# Get API key from environment variable
PERPLEXITY_API_KEY = "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"
perplexity_client = OpenAI(
    api_key=PERPLEXITY_API_KEY,
    base_url="https://api.perplexity.ai"
)

# Load MBTI data
mbti_data = []
try:
    with open('MBTI.json', 'r') as f:
        mbti_data = json.load(f)
except FileNotFoundError:
    print("Warning: MBTI.json file not found. MBTI functionality will be limited.")
except json.JSONDecodeError:
    print("Warning: MBTI.json contains invalid JSON. MBTI functionality will be limited.")

# MBTI descriptions for supporter personas
mbti_descriptions = {
    "INTJ": "The Architect - Strategic, innovative, and private. I excel at analyzing complex problems and creating long-term plans.",
    "INTP": "The Logician - Analytical, objective, and curious. I can help you explore ideas and find logical solutions to your challenges.",
    "ENTJ": "The Commander - Decisive, efficient, and structured. I'll help you organize your thoughts and create actionable plans.",
    "ENTP": "The Debater - Quick-thinking, outspoken, and innovative. I'll challenge your assumptions and help you see new possibilities.",
    "INFJ": "The Advocate - Insightful, principled, and idealistic. I can help you find meaning and purpose in your challenges.",
    "INFP": "The Mediator - Compassionate, creative, and introspective. I'll help you explore your feelings and align with your values.",
    "ENFJ": "The Protagonist - Charismatic, empathetic, and inspiring. I'll motivate you to overcome obstacles and reach your potential.",
    "ENFP": "The Campaigner - Enthusiastic, creative, and sociable. I'll bring energy and fresh perspectives to your situation.",
    "ISTJ": "The Logistician - Practical, detail-oriented, and reliable. I'll help you create structured approaches to your challenges.",
    "ISFJ": "The Defender - Dedicated, warm, and conscientious. I'll provide steady support and practical help for your needs.",
    "ESTJ": "The Executive - Organized, practical, and direct. I'll help you implement efficient solutions to your problems.",
    "ESFJ": "The Consul - Supportive, organized, and people-oriented. I'll help you navigate social dynamics and practical concerns.",
    "ISTP": "The Virtuoso - Practical, logical, and adaptable. I can help you troubleshoot problems and find hands-on solutions.",
    "ISFP": "The Adventurer - Flexible, artistic, and sensitive. I'll help you express yourself and find creative approaches.",
    "ESTP": "The Entrepreneur - Energetic, perceptive, and bold. I'll help you take action and seize opportunities.",
    "ESFP": "The Entertainer - Spontaneous, energetic, and enthusiastic. I'll bring positivity and practical enjoyment to your journey."
}

# Helper Functions
def generate_response(prompt: str) -> str:
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    outputs = model.generate(
        **inputs,
        generation_config=gen_config
    )
    full = tokenizer.decode(outputs[0], skip_special_tokens=True)
    # Split on the last assistant tag and return only what comes after it
    return full.split("### Assistant:")[-1].strip()

def get_mbti_description(mbti_type):
    for item in mbti_data:
        if item.get("type") == mbti_type:
            return item.get("description", [])
    return []

def build_personality_prompt(personality_type, problem_statement=None):
    mbti_commands = get_mbti_description(personality_type)
    if not mbti_commands:
        return "You are a helpful assistant. Answer concisely and accurately."

    # Extract personality description from the first command
    personality_desc = mbti_commands[0] if mbti_commands else ""

    # Build a system prompt that incorporates the personality and problem
    system_prompt = f"""You are an AI assistant with an {personality_type} personality type.
{personality_desc}

# Your goal is to help the user with their questions and concerns."""

    if problem_statement:
        system_prompt += f"\n\nThe user has shared this specific concern: {problem_statement}"

    return system_prompt

def build_prompt_with_supporter(history, new_msg, personality_type, problem_statement=None, supporter=None):
    """
    Build a prompt that includes supporter context for more personalized responses
    """
    # Start with basic personality prompt
    system_prompt = build_personality_prompt(personality_type, problem_statement)

    # Add supporter context if available
    if supporter:
        supporter_context = f"""
You are now embodying the personality of {supporter.get('name')}, a {supporter.get('age_group')} {supporter.get('gender')} who works as a {supporter.get('occupation')}.
You have an {supporter.get('personality_type')} personality type.

Your expertise includes: {', '.join(supporter.get('expertise_keywords', [])[:5])}
Your communication style: {mbti_descriptions.get(supporter.get('personality_type', 'INTJ')).split(' - ')[1]}

When responding, maintain this persona consistently. Speak as if you are this specific individual with these traits and expertise.
"""
        system_prompt = f"{system_prompt}\n\n{supporter_context}"

    # Build the full prompt
    parts = [f"### System: {system_prompt}"]

    for msg in history[-5:]:
        role = "Human" if msg["role"] == "user" else "Assistant"
        parts.append(f"### {role}: {msg['content']}")

    parts.append(f"### Human: {new_msg}")
    parts.append("### Assistant:")
    return "\n".join(parts)

def calculate_compatibility_score(supporter, problem_statement, user_age, user_gender, user_emotional_state):
    """
    Calculate compatibility score between a supporter and a user based on problem statement and demographics
    """
    score = 0

    # 1. Check if supporter's expertise matches problem keywords
    expertise_keywords = supporter.get("expertise_keywords", [])
    for keyword in expertise_keywords:
        if keyword.lower() in problem_statement.lower():
            score += 10

    # 2. Age compatibility (supporters may have age ranges they work best with)
    supporter_min_age = supporter.get("min_age_affinity", 0)
    supporter_max_age = supporter.get("max_age_affinity", 100)
    if supporter_min_age <= user_age <= supporter_max_age:
        score += 5

    # 3. Gender compatibility (some users may prefer same-gender supporters)
    if supporter.get("gender") == user_gender:
        score += 3

    # 4. Emotional state compatibility
    emotional_strengths = supporter.get("emotional_strengths", [])
    if user_emotional_state in emotional_strengths:
        score += 8

    # 5. MBTI-specific scoring (certain types may be better for specific emotional states)
    mbti_type = supporter.get("personality_type")

    # Feelers (F) get bonus points for emotional support
    if "F" in mbti_type and user_emotional_state in ["anxious", "sad", "overwhelmed"]:
        score += 5

    # Thinkers (T) get bonus points for logical problem-solving
    if "T" in mbti_type and user_emotional_state in ["confused", "indecisive", "frustrated"]:
        score += 5

    # Judgers (J) get bonus points for structure and organization
    if "J" in mbti_type and "organization" in problem_statement.lower():
        score += 5

    # Perceivers (P) get bonus points for flexibility and adaptability
    if "P" in mbti_type and "change" in problem_statement.lower():
        score += 5

    return score

def find_compatible_supporter(seeker_mbti, problem_statement, user_age, user_gender, user_emotional_state):
    """
    Find the most compatible supporter for a user based on MBTI type and other factors
    """
    # Comprehensive MBTI compatibility mapping
    compatibility_map = {
        "INTJ": ["ENFP", "ENTP", "INFJ", "ENTJ"],
        "INTP": ["ENTJ", "ENFJ", "INFP", "ENTP"],
        "ENTJ": ["INFP", "INTP", "ENFJ", "INTJ"],
        "ENTP": ["INFJ", "INTJ", "ENFP", "INTP"],
        "INFJ": ["ENTP", "ENFP", "INTJ", "INFP"],
        "INFP": ["ENTJ", "ENFJ", "INFJ", "INTP"],
        "ENFJ": ["INFP", "ISFP", "INTP", "ENTJ"],
        "ENFP": ["INTJ", "INFJ", "ENTP", "ISFJ"],
        "ISTJ": ["ESFP", "ESTP", "ISFJ", "ESTJ"],
        "ISFJ": ["ESFP", "ENFP", "ISTJ", "ESTJ"],
        "ESTJ": ["ISFP", "ISTP", "ISTJ", "ESFJ"],
        "ESFJ": ["ISFP", "ISTP", "ESTJ", "ISFJ"],
        "ISTP": ["ESFJ", "ESTJ", "ISFP", "ESTP"],
        "ISFP": ["ENFJ", "ESFJ", "ESTJ", "ISTP"],
        "ESTP": ["ISFJ", "ISTJ", "ISTP", "ESFP"],
        "ESFP": ["ISTJ", "ISFJ", "ESTP", "ESFJ"]
    }

    # Get all supporters from the database
    all_supporters = list(supporters.find({}))

    if not all_supporters:
        # If no supporters in database, return None and handle this case elsewhere
        return None

    # Get compatible types for the seeker
    compatible_types = compatibility_map.get(seeker_mbti, [])

    # If no direct compatibility found, use a default approach
    if not compatible_types:
        # For thinkers (T), match with feelers (F) and vice versa
        if "T" in seeker_mbti:
            compatible_types = [mbti for mbti in [s["personality_type"] for s in all_supporters] if "F" in mbti]
        else:
            compatible_types = [mbti for mbti in [s["personality_type"] for s in all_supporters] if "T" in mbti]

    # Filter supporters by compatible MBTI types
    compatible_supporters = [s for s in all_supporters if s["personality_type"] in compatible_types]

    # If no compatible supporters found, use all supporters
    if not compatible_supporters:
        compatible_supporters = all_supporters

    # Select the best supporter based on problem statement and demographics
    best_supporter = None
    highest_score = -1

    for supporter in compatible_supporters:
        score = calculate_compatibility_score(
            supporter,
            problem_statement,
            user_age,
            user_gender,
            user_emotional_state
        )

        if score > highest_score:
            highest_score = score
            best_supporter = supporter

    # If still no match found, return a default supporter (ENFJ is often good for counseling)
    if not best_supporter:
        default_type = "ENFJ"
        default_supporter = next((s for s in all_supporters if s["personality_type"] == default_type), None)
        if not default_supporter:
            default_supporter = all_supporters[0]  # Just take the first one if no ENFJ
        return default_supporter

    return best_supporter

def generate_supporter_personas():
    """
    Generate and store 64 supporter personas in the database (16 MBTI types × 4 variations)
    """
    # Check if supporters already exist in the database
    if supporters.count_documents({}) >= 64:
        print("Supporter personas already exist in the database.")
        return

    # MBTI types
    mbti_types = [
        "INTJ", "INTP", "ENTJ", "ENTP",
        "INFJ", "INFP", "ENFJ", "ENFP",
        "ISTJ", "ISFJ", "ESTJ", "ESFJ",
        "ISTP", "ISFP", "ESTP", "ESFP"
    ]

    # Age groups
    age_groups = [
        {"min": 18, "max": 30, "label": "young adult"},
        {"min": 31, "max": 45, "label": "adult"},
        {"min": 46, "max": 60, "label": "middle-aged"},
        {"min": 61, "max": 100, "label": "senior"}
    ]

    # Genders
    genders = ["male", "female", "non-binary", "other"]

    # Occupations by MBTI type (common occupations for each type)
    occupations = {
        "INTJ": ["Scientist", "Strategic Planner", "Systems Analyst", "Research Specialist"],
        "INTP": ["Professor", "Software Developer", "Researcher", "Philosopher"],
        "ENTJ": ["Executive", "Business Consultant", "Lawyer", "Project Manager"],
        "ENTP": ["Entrepreneur", "Creative Director", "Marketing Strategist", "Inventor"],
        "INFJ": ["Counselor", "Therapist", "Writer", "Life Coach"],
        "INFP": ["Poet", "Writer", "Psychologist", "Social Worker"],
        "ENFJ": ["Teacher", "HR Manager", "Motivational Speaker", "Non-profit Director"],
        "ENFP": ["Creative Coach", "Journalist", "Performer", "Social Advocate"],
        "ISTJ": ["Accountant", "Logistics Manager", "Quality Assurance Specialist", "Military Officer"],
        "ISFJ": ["Nurse", "Elementary Teacher", "Administrative Assistant", "Social Worker"],
        "ESTJ": ["Manager", "Police Officer", "Judge", "Financial Planner"],
        "ESFJ": ["Healthcare Worker", "Office Manager", "Event Planner", "Sales Representative"],
        "ISTP": ["Engineer", "Mechanic", "Pilot", "Technical Specialist"],
        "ISFP": ["Artist", "Designer", "Musician", "Veterinarian"],
        "ESTP": ["Entrepreneur", "Sales Executive", "Sports Coach", "Emergency Responder"],
        "ESFP": ["Event Coordinator", "Travel Agent", "Personal Trainer", "Entertainer"]
    }

    # Emotional strengths by MBTI type
    emotional_strengths = {
        "INTJ": ["confused", "indecisive", "frustrated", "overwhelmed"],
        "INTP": ["confused", "indecisive", "curious", "frustrated"],
        "ENTJ": ["frustrated", "determined", "ambitious", "stressed"],
        "ENTP": ["bored", "curious", "excited", "frustrated"],
        "INFJ": ["anxious", "sad", "overwhelmed", "confused"],
        "INFP": ["sad", "anxious", "hopeful", "inspired"],
        "ENFJ": ["overwhelmed", "concerned", "hopeful", "empathetic"],
        "ENFP": ["excited", "anxious", "inspired", "restless"],
        "ISTJ": ["frustrated", "concerned", "determined", "overwhelmed"],
        "ISFJ": ["worried", "anxious", "caring", "overwhelmed"],
        "ESTJ": ["frustrated", "determined", "impatient", "stressed"],
        "ESFJ": ["worried", "caring", "anxious", "hopeful"],
        "ISTP": ["bored", "curious", "indifferent", "calm"],
        "ISFP": ["sad", "inspired", "peaceful", "anxious"],
        "ESTP": ["bored", "excited", "restless", "enthusiastic"],
        "ESFP": ["excited", "enthusiastic", "restless", "anxious"]
    }

    # Generate 64 supporter personas (16 MBTI types × 4 variations)
    personas = []

    for mbti_type in mbti_types:
        for i in range(4):
            age_group = age_groups[i]
            gender = genders[i]
            occupation = occupations[mbti_type][i]

            # Create a unique name based on type and variation
            first_names_male = ["James", "Michael", "Robert", "David", "John", "William", "Richard", "Thomas", "Daniel", "Matthew"]
            first_names_female = ["Mary", "Jennifer", "Linda", "Patricia", "Elizabeth", "Susan", "Jessica", "Sarah", "Karen", "Nancy"]
            first_names_nb = ["Alex", "Jordan", "Taylor", "Casey", "Riley", "Avery", "Quinn", "Skyler", "Morgan", "Dakota"]

            if gender == "male":
                first_name = first_names_male[hash(mbti_type + str(i)) % len(first_names_male)]
            elif gender == "female":
                first_name = first_names_female[hash(mbti_type + str(i)) % len(first_names_female)]
            else:
                first_name = first_names_nb[hash(mbti_type + str(i)) % len(first_names_nb)]

            last_names = ["Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor"]
            last_name = last_names[hash(mbti_type + str(i) + gender) % len(last_names)]

            name = f"{first_name} {last_name}"

            # Create expertise keywords based on MBTI type and occupation
            expertise_keywords = []

            # Add keywords based on MBTI dimensions
            if "I" in mbti_type:
                expertise_keywords.extend(["reflection", "deep thinking", "independence"])
            if "E" in mbti_type:
                expertise_keywords.extend(["social skills", "networking", "communication"])
            if "N" in mbti_type:
                expertise_keywords.extend(["innovation", "big picture", "future planning"])
            if "S" in mbti_type:
                expertise_keywords.extend(["practical advice", "details", "present focus"])
            if "T" in mbti_type:
                expertise_keywords.extend(["logical analysis", "objective thinking", "efficiency"])
            if "F" in mbti_type:
                expertise_keywords.extend(["emotional support", "values alignment", "harmony"])
            if "J" in mbti_type:
                expertise_keywords.extend(["organization", "structure", "planning"])
            if "P" in mbti_type:
                expertise_keywords.extend(["flexibility", "adaptability", "spontaneity"])

            # Add occupation-specific keywords
            if "Therapist" in occupation or "Counselor" in occupation or "Coach" in occupation:
                expertise_keywords.extend(["mental health", "personal growth", "emotional well-being"])
            if "Manager" in occupation or "Executive" in occupation or "Director" in occupation:
                expertise_keywords.extend(["leadership", "management", "career development"])
            if "Teacher" in occupation or "Professor" in occupation:
                expertise_keywords.extend(["learning", "education", "skill development"])
            if "Engineer" in occupation or "Developer" in occupation or "Analyst" in occupation:
                expertise_keywords.extend(["problem-solving", "technical challenges", "systems thinking"])

            # Create a persona description
            base_description = mbti_descriptions[mbti_type]
            age_description = f"As a {age_group['label']}, I understand the challenges of your life stage."
            occupation_description = f"My background as a {occupation} gives me insight into {', '.join(expertise_keywords[:3])}."

            description = f"{base_description} {age_description} {occupation_description}"

            # Create the supporter persona
            persona = {
                "name": name,
                "personality_type": mbti_type,
                "gender": gender,
                "age_group": age_group["label"],
                "min_age_affinity": max(18, age_group["min"] - 10),
                "max_age_affinity": min(100, age_group["max"] + 10),
                "occupation": occupation,
                "description": description,
                "expertise_keywords": expertise_keywords,
                "emotional_strengths": emotional_strengths[mbti_type],
                "greeting": f"Hi! I'm {name}, a {age_group['label']} {occupation} with an {mbti_type} personality type. {base_description.split(' - ')[1]} I'm here to help you with your challenges related to {', '.join(expertise_keywords[:3])}."
            }

            personas.append(persona)

    # Insert all personas into the database
    if personas:
        supporters.insert_many(personas)
        print(f"Successfully generated and stored {len(personas)} supporter personas.")


def generate_welcome_message(agent_type, personality_type, problem_statement):
    """
    Generate a personalized welcome message based on agent type and user info
    """
    logger.info(f"Generating welcome message for agent: {agent_type}, personality: {personality_type}")

    base_welcome = f"Hello! I'm your personal coach matched to your {personality_type} personality type. "

    if agent_type == "empathetic_coach":
        message = base_welcome + "I focus on understanding your feelings and helping you explore possibilities. I'm here to support your personal growth journey."
    elif agent_type == "analytical_coach":
        message = base_welcome + "I specialize in logical analysis and strategic thinking. I'll help you break down complex problems into manageable steps."
    elif agent_type == "practical_support_coach":
        message = base_welcome + "I provide practical, hands-on guidance. I'll help you find concrete solutions to your challenges."
    elif agent_type == "structured_coach":
        message = base_welcome + "I offer structured approaches and clear frameworks. I'll help you create organized plans to achieve your goals."
    else:
        message = base_welcome + "I'm here to help you with your challenges and goals."

    # Add problem statement acknowledgment if available
    if problem_statement:
        message += f"\n\nI see you're working on: '{problem_statement}'. Let's tackle this together."

    message += "\n\nHow can I help you today?"

    logger.info(f"Generated welcome message: {message[:50]}...")
    return message


def summarize_conversation(messages):
    if not messages:
        return "New Chat"

    # Limit the conversation to the last 10 messages to avoid token limits
    recent_messages = messages[-10:] if len(messages) > 10 else messages
    
    # Create a prompt for summarization
    conversation = "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent_messages])
    
    try:
        # Use Perplexity API for summarization
        response = perplexity_client.chat.completions.create(
            model="sonar",  # Use the same model as your chat
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes conversations into short, descriptive titles."},
                {"role": "user", "content": f"Please summarize the following conversation into a concise title (max 6 words):\n\n{conversation}"}
            ],
            temperature=0.7,
            max_tokens=50
        )
        
        summary = response.choices[0].message.content.strip()
        
        # Remove any quotes that might be in the response
        summary = summary.replace('"', '').replace("'", "")
        
        # Limit to 50 characters
        return summary[:50] if summary else "Chat Session"
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        return "Chat Session"




# Authentication Middleware
def token_required(f):
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({"error": "Token missing"}), 401
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            user = mongo.db.users.find_one({'_id': ObjectId(data['user_id'])})
            if not user:
                return jsonify({"error": "User not found"}), 401
            return f(user, *args, **kwargs)
        except Exception as e:
            return jsonify({"error": f"Invalid token: {str(e)}"}), 401
    decorated.__name__ = f.__name__
    return decorated


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agent_matching.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("agent_matching")

# Middleware function to log requests
def log_request_middleware(app):
    @app.before_request
    def log_request_info():
        logger.info(f"Request path: {request.path}, Method: {request.method}")
        if request.is_json:
            logger.info(f"Request JSON: {request.get_json()}")

    @app.after_request
    def log_response_info(response):
        logger.info(f"Response status: {response.status_code}")
        return response


# User Routes
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data.get('username') or not data.get('password'):
        return jsonify({"error": "Username/password required"}), 400

    if mongo.db.users.find_one({"username": data['username']}):
        return jsonify({"error": "Username exists"}), 400

    # Get personality type and problem statement if provided
    personality_type = data.get('personality_type', 'INTJ')  # Default to INTJ if not provided
    problem_statement = data.get('problem_statement', None)

    # Get demographic information
    age = data.get('age', 30)  # Default age
    gender = data.get('gender', 'other')  # Default gender
    emotional_state = data.get('emotional_state', 'neutral')  # Default emotional state

    hashed = bcrypt.hashpw(data['password'].encode(), bcrypt.gensalt())
    user_id = mongo.db.users.insert_one({
        "username": data['username'],
        "password": hashed,
        "personality_type": personality_type,
        "problem_statement": problem_statement,
        "age": age,
        "gender": gender,
        "emotional_state": emotional_state,
        "created_at": datetime.now()
    }).inserted_id

    # Generate supporter personas if they don't exist
    generate_supporter_personas()

    # Find a compatible supporter
    compatible_supporter = find_compatible_supporter(
        personality_type,
        problem_statement or "",
        age,
        gender,
        emotional_state
    )

    supporter_id = None
    if compatible_supporter:
        supporter_id = str(compatible_supporter.get('_id'))

    # Create initial chat session with matched supporter
    mongo.db.chat_sessions.insert_one({
        "user_id": str(user_id),
        "session_name": "First Chat",
        "personality_type": personality_type,
        "problem_statement": problem_statement,
        "supporter_id": supporter_id,
        "messages": [],
        "created_at": datetime.now()
    })

    return jsonify({
        "message": "User created",
        "personality_type": personality_type,
        "supporter_id": supporter_id
    }), 201

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()

        # Validate input
        if not data or not data.get('username') or not data.get('password'):
            return jsonify({"error": "Username and password are required"}), 400

        username = data.get('username')
        password = data.get('password')

        # Find user in database
        try:
            user = mongo.db.users.find_one({"username": username})
        except Exception as e:
            print(f"Database error: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": "Database connection error"}), 500

        # Check password
        try:
            if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password']):
                return jsonify({"error": "Invalid username or password"}), 401
        except Exception as e:
            print(f"Password verification error: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": "Authentication error"}), 500

        # Generate JWT token
        try:
            token = jwt.encode({
                'user_id': str(user['_id']),
                'username': user['username'],
                'exp': datetime.utcnow() + timedelta(days=1)
            }, SECRET_KEY, algorithm='HS256')
        except Exception as e:
            print(f"Token generation error: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": "Token generation error"}), 500

        return jsonify({
            "token": token,
            "user_id": str(user['_id']),
            "username": user['username'],
            "personality_type": user.get('personality_type', 'INTJ')
        }), 200
    except Exception as e:
        print(f"Unexpected error in login: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Server error"}), 500

# User Profile Routes
@app.route('/api/profile', methods=['GET'])
@token_required
def get_profile(user):
    return jsonify({
        "username": user['username'],
        "personality_type": user.get('personality_type', 'INTJ'),
        "problem_statement": user.get('problem_statement', None),
        "age": user.get('age', 30),
        "gender": user.get('gender', 'other'),
        "emotional_state": user.get('emotional_state', 'neutral')
    })

@app.route('/api/profile', methods=['PUT'])
@token_required
def update_profile(user):
    data = request.get_json()

    # Update user profile
    updates = {}
    if 'personality_type' in data:
        updates['personality_type'] = data['personality_type']
    if 'problem_statement' in data:
        updates['problem_statement'] = data['problem_statement']
    if 'age' in data:
        updates['age'] = data['age']
    if 'gender' in data:
        updates['gender'] = data['gender']
    if 'emotional_state' in data:
        updates['emotional_state'] = data['emotional_state']

    if updates:
        mongo.db.users.update_one(
            {"_id": user['_id']},
            {"$set": updates}
        )

    return jsonify({"message": "Profile updated successfully"})

# Chat Session Routes
@app.route('/api/sessions', methods=['GET'])
@token_required
def get_sessions(user):
    user_id = str(user['_id'])

    # Get all chat sessions for the user
    sessions = list(mongo.db.chat_sessions.find(
        {"user_id": user_id},
        {"messages": 0}  # Exclude messages for performance
    ).sort("created_at", -1))  # Sort by newest first

    # Convert ObjectId to string for JSON serialization
    for session in sessions:
        session['_id'] = str(session['_id'])
        if 'supporter_id' in session and session['supporter_id']:
            session['supporter_id'] = str(session['supporter_id'])

    return jsonify({"sessions": sessions})



@app.route('/api/sessions/new', methods=['POST'])
@token_required
def create_session(user):
    data = request.get_json()
    session_name = data.get('session_name', 'New Chat')
    
    # Always pull the latest user data from the database
    current_user = mongo.db.users.find_one({"_id": user["_id"]})
    
    # Get personality type and problem statement from current user data
    personality_type = current_user.get('personality_type', 'INTJ')
    problem_statement = current_user.get('problem_statement', '')
    
    logger.info(f"Creating new session for user {current_user['username']} with personality type: {personality_type}")
    
    # Match agent based on personality type
    agent_type = match_agent_to_personality(personality_type)
    logger.info(f"Matched agent type: {agent_type} for personality: {personality_type}")
    
    # Create session with agent information
    session_id = mongo.db.chat_sessions.insert_one({
        "user_id": str(current_user['_id']),
        "session_name": session_name,
        "personality_type": personality_type,
        "problem_statement": problem_statement,
        "agent_type": agent_type,
        "messages": [],
        "created_at": datetime.now(),
        "matching_verified": True
    }).inserted_id
    
    logger.info(f"Session created with ID: {session_id}")
    
    return jsonify({
        "session_id": str(session_id), 
        "agent_type": agent_type,
        "personality_type": personality_type,
        "problem_statement": problem_statement
    })



def match_agent_to_personality(personality_type):
    """
    Match personality type to appropriate agent type
    """
    # Implement your matching logic here
    # Example matching logic based on personality dimensions

    # Extract dimensions
    is_introvert = personality_type.startswith('I')
    is_intuitive = 'N' in personality_type
    is_feeling = 'F' in personality_type
    is_perceiving = 'P' in personality_type

    logger.info(f"Personality dimensions - Introvert: {is_introvert}, Intuitive: {is_intuitive}, Feeling: {is_feeling}, Perceiving: {is_perceiving}")

    # Match based on dimensions
    if is_feeling and is_intuitive:
        agent_type = "empathetic_coach"
    elif not is_feeling and is_intuitive:
        agent_type = "analytical_coach"
    elif is_feeling and not is_intuitive:
        agent_type = "practical_support_coach"
    else:
        agent_type = "structured_coach"

    logger.info(f"Selected agent type: {agent_type} for personality type: {personality_type}")
    return agent_type




@app.route('/api/sessions/<session_id>', methods=['GET'])
@token_required
def get_session(user, session_id):
    user_id = str(user['_id'])

    # Get the chat session
    session = mongo.db.chat_sessions.find_one({
        "_id": ObjectId(session_id),
        "user_id": user_id
    })

    if not session:
        return jsonify({"error": "Session not found"}), 404

    # Convert ObjectId to string for JSON serialization
    session['_id'] = str(session['_id'])
    if 'supporter_id' in session and session['supporter_id']:
        session['supporter_id'] = str(session['supporter_id'])

    return jsonify({"session": session})

@app.route('/api/sessions/<session_id>/rename', methods=['PUT'])
@token_required
def rename_session(user, session_id):
    data = request.get_json()
    user_id = str(user['_id'])
    new_name = data.get('session_name')

    if not new_name:
        return jsonify({"error": "Session name is required"}), 400

    # Update the session name
    result = mongo.db.chat_sessions.update_one(
        {"_id": ObjectId(session_id), "user_id": user_id},
        {"$set": {"session_name": new_name}}
    )

    if result.matched_count == 0:
        return jsonify({"error": "Session not found"}), 404

    return jsonify({"message": "Session renamed successfully"})

@app.route('/api/sessions/<session_id>', methods=['DELETE'])
@token_required
def delete_session(user, session_id):
    user_id = str(user['_id'])

    # Delete the session
    result = mongo.db.chat_sessions.delete_one({
        "_id": ObjectId(session_id),
        "user_id": user_id
    })

    if result.deleted_count == 0:
        return jsonify({"error": "Session not found"}), 404

    return jsonify({"message": "Session deleted successfully"})

@app.route('/api/sessions/<session_id>/end', methods=['POST'])
@token_required
def end_session(user, session_id):
    user_id = str(user['_id'])

    # Get the session
    session = mongo.db.chat_sessions.find_one({
        "_id": ObjectId(session_id),
        "user_id": user_id
    })

    if not session:
        return jsonify({"error": "Session not found"}), 404

    # Generate a summary title for the conversation
    messages = session.get('messages', [])
    summary = summarize_conversation(messages)

    # Update the session name with the summary
    mongo.db.chat_sessions.update_one(
        {"_id": ObjectId(session_id)},
        {"$set": {"session_name": summary}}
    )

    return jsonify({
        "message": "Session ended and summarized",
        "summary": summary
    })

# Supporter Route
@app.route('/api/supporter/<supporter_id>', methods=['GET'])
@token_required
def get_supporter(user, supporter_id):
    try:
        supporter = supporters.find_one({"_id": ObjectId(supporter_id)})
        if not supporter:
            return jsonify({"error": "Supporter not found"}), 404

        # Convert ObjectId to string for JSON serialization
        supporter['_id'] = str(supporter['_id'])

        return jsonify({"supporter": supporter})
    except Exception as e:
        return jsonify({"error": f"Error retrieving supporter: {str(e)}"}), 500




@app.route('/api/chat', methods=['POST'])
@token_required
def chat(user):
    data = request.get_json()
    message = data.get('message')
    session_id = data.get('session_id')
    
    if not session_id:
        return jsonify({"error": "Session ID required"}), 400
    
    # Get session information
    session = mongo.db.chat_sessions.find_one({"_id": ObjectId(session_id)})
    if not session:
        return jsonify({"error": "Session not found"}), 404
    
    # Get the most current user data
    current_user = mongo.db.users.find_one({"_id": user["_id"]})
    
    # Check if this is the first message in the session
    is_first_message = len(session.get('messages', [])) == 0
    logger.info(f"Processing message for session {session_id}, is first message: {is_first_message}")
    
    # If first message, generate welcome message using CURRENT user data
    if is_first_message:
        # Use the most recent personality type and problem statement
        personality_type = current_user.get('personality_type', 'INTJ')
        problem_statement = current_user.get('problem_statement', '')
        
        # Update session with current data
        mongo.db.chat_sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {
                "personality_type": personality_type,
                "problem_statement": problem_statement
            }}
        )
        
        # Re-match agent type based on current personality
        agent_type = match_agent_to_personality(personality_type)
        
        # Update session with new agent type
        mongo.db.chat_sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"agent_type": agent_type}}
        )
        
        logger.info(f"Updated session with current data. Personality: {personality_type}, Agent: {agent_type}")
        
        # Generate welcome message with current data
        welcome_message = generate_welcome_message(agent_type, personality_type, problem_statement)
        
        # Store welcome message in session
        mongo.db.chat_sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$push": {"messages": {"role": "assistant", "content": welcome_message, "timestamp": datetime.now()}}}
        )
        
        # If the user's first message is just a greeting, respond with welcome message only
        greeting_patterns = ["hi", "hello", "hey", "greetings", "start", "begin"]
        if message.lower() in greeting_patterns or message.lower().startswith(tuple(greeting_patterns)):
            logger.info("User sent greeting, responding with welcome message only")
            return jsonify({"response": welcome_message})
    
    # Rest of the chat logic remains the same...



    # Process the user message
    logger.info(f"Processing user message: {message[:50]}...")

    # Store user message
    mongo.db.chat_sessions.update_one(
        {"_id": ObjectId(session_id)},
        {"$push": {"messages": {"role": "user", "content": message, "timestamp": datetime.now()}}}
    )

    # Generate response based on personality type and agent type
    personality_type = session.get('personality_type', user.get('personality_type', 'INTJ'))
    agent_type = session.get('agent_type', match_agent_to_personality(personality_type))

    # Log the agent matching verification
    logger.info(f"Generating response using agent: {agent_type} for personality: {personality_type}")

    # Call your AI model to generate a response
    try:
        response = generate_ai_response(message, personality_type, agent_type, session)

        # Store assistant response
        mongo.db.chat_sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$push": {"messages": {"role": "assistant", "content": response, "timestamp": datetime.now()}}}
        )

        logger.info(f"Generated response: {response[:50]}...")
        return jsonify({"response": response})
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        return jsonify({"error": "Failed to generate response"}), 500

def generate_ai_response(message, personality_type, agent_type, session):
    """
    Generate AI response based on user message, personality type, and agent type
    """
    logger.info(f"Generating AI response for message: '{message[:30]}...'")
    logger.info(f"Using personality type: {personality_type}, agent type: {agent_type}")

    # Get conversation history
    conversation_history = session.get('messages', [])
    history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-5:]])
    logger.info(f"Using conversation history: {history_text[:100]}...")

    # Prepare prompt for the AI model
    system_prompt = get_agent_system_prompt(agent_type, personality_type)
    logger.info(f"Using system prompt: {system_prompt[:100]}...")

    try:
        # Call your AI model (example using OpenAI)
        # response = openai.ChatCompletion.create(
        #     model="gpt-4",
        #     messages=[
        #         {"role": "system", "content": system_prompt},
        #         {"role": "user", "content": f"Conversation history:\n{history_text}\n\nUser message: {message}"}
        #     ],
        #     temperature=0.7,
        #     max_tokens=500
        # )

        response = perplexity_client.chat.completions.create(
            model="sonar",  # Choose the model that fits your needs
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Conversation history:\n{history_text}\n\nUser message: {message}"}
            ],
            temperature=0.7,
            max_tokens=500
        )


        ai_response = response.choices[0].message.content
        logger.info(f"AI generated response: {ai_response[:100]}...")

        # Log token usage for monitoring
        logger.info(f"Token usage - Prompt: {response.usage.prompt_tokens}, Completion: {response.usage.completion_tokens}")

        return ai_response
    except Exception as e:
        logger.error(f"Error in AI response generation: {str(e)}")
        raise


def get_agent_system_prompt(agent_type, personality_type):
    """
    Generate system prompt for the AI based on agent type and personality type
    """
    base_prompt = f"You are a personality coach specialized for {personality_type} personality types. "

    if agent_type == "empathetic_coach":
        prompt = base_prompt + """
        Your communication style is:
        - Warm and empathetic
        - Focused on emotional understanding
        - Supportive of personal growth
        - Encouraging exploration of possibilities

        When responding to the user:
        - Acknowledge their feelings first
        - Use compassionate language
        - Offer insights that align with their values
        - Suggest creative approaches to their challenges
        """

    elif agent_type == "analytical_coach":
        prompt = base_prompt + """
        Your communication style is:
        - Logical and precise
        - Focused on analysis and strategy
        - Direct and efficient
        - Intellectually stimulating

        When responding to the user:
        - Analyze their situation objectively
        - Provide clear, logical frameworks
        - Break down complex problems into components
        - Suggest evidence-based approaches
        """

    elif agent_type == "practical_support_coach":
        prompt = base_prompt + """
        Your communication style is:
        - Practical and down-to-earth
        - Focused on concrete solutions
        - Supportive and reliable
        - Action-oriented

        When responding to the user:
        - Offer tangible, immediate steps
        - Use clear, straightforward language
        - Provide specific examples
        - Focus on what has worked in similar situations
        """

    elif agent_type == "structured_coach":
        prompt = base_prompt + """
        Your communication style is:
        - Organized and methodical
        - Focused on structure and planning
        - Clear and consistent
        - Detail-oriented

        When responding to the user:
        - Help create organized plans
        - Provide step-by-step guidance
        - Emphasize consistency and follow-through
        - Offer frameworks for decision-making
        """

    else:
        prompt = base_prompt + """
        Your communication style is balanced and adaptive to the user's needs.

        When responding to the user:
        - Be supportive and helpful
        - Provide thoughtful guidance
        - Offer practical suggestions
        - Focus on their specific challenges
        """

    logger.info(f"Generated system prompt for agent type: {agent_type}")
    return prompt


@app.route('/api/test-welcome-message', methods=['GET'])
@token_required
def test_welcome_message(user):
    """
    Test endpoint to generate welcome messages for all agent types
    """
    personality_type = user.get('personality_type', 'INTJ')
    problem_statement = user.get('problem_statement', 'Sample problem statement')

    # Generate welcome messages for all agent types
    agent_types = ["empathetic_coach", "analytical_coach", "practical_support_coach", "structured_coach"]
    welcome_messages = {}

    for agent_type in agent_types:
        welcome_messages[agent_type] = generate_welcome_message(agent_type, personality_type, problem_statement)

    # Also include the actual matched agent
    matched_agent = match_agent_to_personality(personality_type)

    return jsonify({
        "personality_type": personality_type,
        "matched_agent_type": matched_agent,
        "problem_statement": problem_statement,
        "welcome_messages": welcome_messages
    })



@app.route('/api/verify-matching', methods=['GET'])
@token_required
def verify_matching(user):
    """
    Endpoint to verify the agent matching process for a user
    """
    # Get user's personality type
    personality_type = user.get('personality_type', 'INTJ')

    # Get user's active sessions
    sessions = list(mongo.db.chat_sessions.find({"user_id": str(user['_id'])}))

    # Verify matching for each session
    verification_results = []
    for session in sessions:
        session_id = str(session['_id'])
        session_agent_type = session.get('agent_type', 'unknown')
        expected_agent_type = match_agent_to_personality(personality_type)

        is_matched_correctly = session_agent_type == expected_agent_type

        verification_results.append({
            "session_id": session_id,
            "personality_type": personality_type,
            "assigned_agent": session_agent_type,
            "expected_agent": expected_agent_type,
            "correctly_matched": is_matched_correctly,
            "messages_count": len(session.get('messages', []))
        })

    # Log verification results
    logger.info(f"Matching verification results for user {user['username']}: {verification_results}")

    return jsonify({
        "username": user['username'],
        "personality_type": personality_type,
        "sessions_verified": len(verification_results),
        "all_correctly_matched": all(result['correctly_matched'] for result in verification_results),
        "verification_details": verification_results
    })




# MBTI Test Routes
@app.route('/api/mbti/types', methods=['GET'])
def get_mbti_types():
    # Return list of all MBTI types
    types = [item.get("type") for item in mbti_data if "type" in item]
    return jsonify({"types": types})

# Main entry point
if __name__ == "__main__":
    public_url = ngrok.connect(5000).public_url
    print(f" * Ngrok URL: {public_url}")
    app.run(host='0.0.0.0', port=5000)
