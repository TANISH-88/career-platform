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

ROLE_MAPPING: dict[int, str] = {
    0: 'Database Administrator',
    1: 'Hardware Engineer',
    2: 'Application Support Engineer',
    3: 'Cyber Security Specialist',
    4: 'Networking Engineer',
    5: 'Software Developer',
    6: 'API Specialist',
    7: 'Project Manager',
    8: 'Information Security Specialist',
    9: 'Technical Writer',
    10: 'AI ML Specialist',
    11: 'Software Tester',
    12: 'Business Analyst',
    13: 'Customer Service Executive',
    14: 'Helpdesk Engineer',
    15: 'Graphics Designer',
}

# --- Phase 2 additions ---
GEMINI_MODEL: str = "gemini-2.5-flash-lite"
MAX_RESUME_BYTES: int = 5 * 1024 * 1024   # 5 MB

# --- Scale normalization constants ---
UI_MIN: float = 1.0
UI_MAX: float = 10.0

TECH_MIN: float = 0.0
TECH_MAX: float = 6.0

PERSONALITY_MIN: float = 0.0
PERSONALITY_MAX: float = 1.0

