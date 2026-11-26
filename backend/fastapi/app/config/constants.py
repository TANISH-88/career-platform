TECHNICAL_FEATURES: list[str] = [
    'Computer Architecture',
    'Programming Skills',
    'Project Management',
    'Communication skills',
]

PERSONALITY_FEATURES: list[str] = [
    'Openness',
    'Conscientousness',
    'Extraversion',
    'Agreeableness',
    'Emotional_Range',
    'Conversation',
    'Openness to Change',
    'Hedonism',
    'Self-enhancement',
    'Self-transcendence',
]

# Class order must match sklearn LabelEncoder on the training target.
ROLE_MAPPING: dict[int, str] = {
    0: 'AI ML Specialist',
    1: 'API Specialist',
    2: 'Application Support Engineer',
    3: 'Business Analyst',
    4: 'Customer Service Executive',
    5: 'Cyber Security Specialist',
    6: 'Database Administrator',
    7: 'Graphics Designer',
    8: 'Hardware Engineer',
    9: 'Helpdesk Engineer',
    10: 'Information Security Specialist',
    11: 'Networking Engineer',
    12: 'Project Manager',
    13: 'Software Developer',
    14: 'Software Tester',
    15: 'Technical Writer',
}

# --- Phase 2 additions ---
GEMINI_MODEL: str = "gemini-3.5-flash-lite"
MAX_RESUME_BYTES: int = 5 * 1024 * 1024   # 5 MB
MAX_RESUME_VERSIONS_PER_WORKSPACE: int = 10

# --- Scale normalization constants ---
UI_MIN: float = 1.0
UI_MAX: float = 10.0

TECH_MIN: float = 0.0
TECH_MAX: float = 6.0

PERSONALITY_MIN: float = 0.0
PERSONALITY_MAX: float = 1.0

