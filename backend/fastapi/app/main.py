import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np
import pandas as pd
import joblib

# Load Models
scaler = joblib.load("scaler.pkl")
pca = joblib.load("pca.pkl")
frf_model = joblib.load("frf.pkl")

# Feature Names
corr_features = [
    'Computer Architecture', 'Programming Skills', 'Project Management', 'Communication skills'
]

other_features = [
    'Openness', 'Conscientousness', 'Extraversion', 'Agreeableness',
    'Emotional_Range', 'Conversation', 'Openness to Change', 'Hedonism',
    'Self-enhancement', 'Self-transcendence'
]

role_mapping = {
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
    15: 'Graphics Designer'
}

# FastAPI App
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Input Model for API
class UserInput(BaseModel):
    values: list  # 14 numbers

@app.get("/")
def home():
    return {"message": "Backend running"}

@app.post("/predict")
def predict_career(data: UserInput):

    # Convert input → dataframe
    sample_input = np.array([data.values])
    sample_df = pd.DataFrame(sample_input, columns=corr_features + other_features)

    # Scaling
    scaled_corr = scaler.transform(sample_df[corr_features])
    pca_corr = pca.transform(scaled_corr)

    # Add PCA features
    sample_df = sample_df.drop(columns=corr_features)
    sample_df[['PCA_1', 'PCA_2']] = pca_corr

    # Predict
    predicted_index = frf_model.predict(sample_df)[0]
    predicted_role = role_mapping[predicted_index]

    return {"predicted_role": predicted_role}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)