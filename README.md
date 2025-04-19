This project is a comprehensive mental health support platform that combines personality assessment with AI-powered coaching. The system is built around the Myers-Briggs Type Indicator (MBTI) framework, providing users with personalized coaching based on their personality type.

## Architecture Overview

The application follows a client-server architecture with:

1. A Flask backend that handles authentication, data processing, and AI integration
2. A Streamlit frontend that provides the user interface
3. MongoDB for data persistence
4. Integration with the Perplexity AI API for generating contextually relevant responses

The backend is exposed via ngrok for development purposes, allowing the Streamlit frontend to communicate with it through RESTful API endpoints.

## Backend Components

### Authentication System

The backend implements a JWT-based authentication system:
- User registration with bcrypt password hashing
- Login with token generation (expiry set to 1 day)
- Token validation middleware (`token_required` decorator)
- Secure API endpoints that require authentication

```python
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'b0b682577f2c7c6e7f1c8e0797545edd821c6b3a7c5b22ef74965d50cd2b8b5b')

@app.route('/api/login', methods=['POST'])
def login():
    # Authentication logic
    token = jwt.encode({
        'user_id': str(user['_id']),
        'username': user['username'],
        'exp': datetime.utcnow() + timedelta(days=1)
    }, SECRET_KEY, algorithm='HS256')
```

### Database Integration

The application uses MongoDB Atlas for cloud database storage:
- User profiles (including personality types and problem statements)
- Chat sessions (with message history)
- Supporter personas (AI coach profiles)


### AI Integration

The system integrates with the Perplexity AI API for generating responses:
```python


The backend also includes code for a Hugging Face model integration (commented out in the code), showing the system's flexibility to use different AI models:
```python
# MODEL_NAME = "sugilee/DeepSeek-R1-Distill-Llama-8B-MentalHealth"
# tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
# model = AutoModelForCausalLM.from_pretrained(
#     MODEL_NAME,
#     device_map="auto",
#     load_in_8bit=True,
#     llm_int8_enable_fp32_cpu_offload=True,
#     torch_dtype=torch.float16
# )
```

### Personality Matching Algorithm

The core of the system is a sophisticated matching algorithm that pairs users with appropriate AI coach personas:

1. **MBTI Compatibility Mapping**: Each personality type has predefined compatible types
   ```python
   compatibility_map = {
       "INTJ": ["ENFP", "ENTP", "INFJ", "ENTJ"],
       "INTP": ["ENTJ", "ENFJ", "INFP", "ENTP"],
       # ... other mappings
   }
   ```

2. **Agent Type Matching**: Maps personality dimensions to coaching styles
   ```python
   def match_agent_to_personality(personality_type):
       # Extract dimensions
       is_introvert = personality_type.startswith('I')
       is_intuitive = 'N' in personality_type
       is_feeling = 'F' in personality_type
       is_perceiving = 'P' in personality_type
       
       # Match based on dimensions
       if is_feeling and is_intuitive:
           agent_type = "empathetic_coach"
       elif not is_feeling and is_intuitive:
           agent_type = "analytical_coach"
       elif is_feeling and not is_intuitive:
           agent_type = "practical_support_coach"
       else:
           agent_type = "structured_coach"
   ```

3. **Compatibility Scoring**: Calculates match scores based on:
   - Expertise keywords matching problem statement
   - Age compatibility
   - Gender preferences
   - Emotional state alignment
   - MBTI-specific scoring (e.g., Feelers get bonus points for emotional support)

### Supporter Persona Generation

The system dynamically generates 64 supporter personas (16 MBTI types × 4 variations) with:
- Unique names and demographics
- Occupation aligned with personality type
- Expertise keywords derived from MBTI dimensions
- Emotional strengths specific to each type
- Personalized greeting messages

### Chat Session Management

The backend provides comprehensive session management:
- Creation of new chat sessions
- Loading and storing message history
- Automatic session summarization using AI
- Session deletion

## Frontend Components

### User Interface

The Streamlit frontend provides a user-friendly interface with:
- Personality assessment test (20 questions across 4 dimensions)
- Results visualization with strengths, weaknesses, and development areas
- Chat interface with message history
- Session management sidebar
- User profile management

### MBTI Assessment

The assessment consists of 20 questions organized into 4 categories:
1. Social Interactions (E-I dimension)
2. Information Processing (S-N dimension)
3. Decision Making (T-F dimension)
4. Lifestyle Preferences (J-P dimension)

Each question is scored on a 5-point scale, and the results determine the user's MBTI type.

### Responsive Design

The frontend includes custom CSS for improved user experience:
- Responsive layout with sidebars and columns
- Styled cards for personality profiles
- Custom buttons and badges
- Loading animations

### Session State Management

Streamlit's session state is used to manage application state:
```python
if "user" not in st.session_state:
    st.session_state.user = ""
if "logged" not in st.session_state:
    st.session_state.logged = False
# ... other state variables
```

## Communication Flow

1. User completes MBTI assessment
2. Results are processed to determine personality type
3. User registers/logs in
4. Backend matches user with appropriate coach persona
5. Chat session is created
6. User messages are sent to backend API
7. AI generates personalized responses
8. Responses are displayed in the chat interface

## Security Features

- Password hashing with bcrypt
- JWT authentication
- MongoDB connection string security
- API key management for AI services
- Hugging Face token authentication

## Logging and Monitoring

The system includes comprehensive logging:
```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agent_matching.log"),
        logging.StreamHandler()
    ]
)
```

Request and response information is logged for debugging and monitoring purposes.

## Deployment

The backend is deployed using ngrok for development:
```python
public_url = ngrok.connect(5000).public_url
print(f" * Ngrok URL: {public_url}")
app.run(host='0.0.0.0', port=5000)
```

The frontend connects to this URL for API communication.

This comprehensive mental health platform combines sophisticated AI, personality psychology, and user-centered design to provide personalized coaching support for users based on their unique personality traits and challenges.
