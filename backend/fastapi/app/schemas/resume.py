from pydantic import BaseModel, Field


class ResumeExtraction(BaseModel):
    """
    Structured output schema for the Gemini API call.
    Field order mirrors TECHNICAL_FEATURES + PERSONALITY_FEATURES from app/config/constants.py.
    All fields are constrained to [1.0, 10.0] as a first-pass guard; the server-side clamp
    in ResumeParser is the authoritative enforcement layer.
    """
    # Technical features
    computer_architecture: float = Field(ge=1.0, le=10.0)
    programming_skills:    float = Field(ge=1.0, le=10.0)
    project_management:    float = Field(ge=1.0, le=10.0)
    communication_skills:  float = Field(ge=1.0, le=10.0)
    # Personality features
    openness:              float = Field(ge=1.0, le=10.0)
    conscientiousness:     float = Field(ge=1.0, le=10.0)
    extraversion:          float = Field(ge=1.0, le=10.0)
    agreeableness:         float = Field(ge=1.0, le=10.0)
    emotional_range:       float = Field(ge=1.0, le=10.0)
    conversation:          float = Field(ge=1.0, le=10.0)
    openness_change:       float = Field(ge=1.0, le=10.0)
    hedonism:              float = Field(ge=1.0, le=10.0)
    self_enhancement:      float = Field(ge=1.0, le=10.0)
    self_transcendence:    float = Field(ge=1.0, le=10.0)


class ParsedResumeResponse(BaseModel):
    """
    Route response model — 14 float values keyed to match page.js orderedKeys.
    No Field constraints here; the server-side clamp in ResumeParser is the
    authoritative guard before this model is populated.
    """
    computer_architecture: float
    programming_skills:    float
    project_management:    float
    communication_skills:  float
    openness:              float
    conscientiousness:     float
    extraversion:          float
    agreeableness:         float
    emotional_range:       float
    conversation:          float
    openness_change:       float
    hedonism:              float
    self_enhancement:      float
    self_transcendence:    float
