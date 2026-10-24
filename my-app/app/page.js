"use client";

import { useState } from "react";
import Features from "./components/Features";
import ResumeUpload from "./components/ResumeUpload";

export default function Home() {
  const [values, setValues] = useState({});
  const [result, setResult] = useState("");

  const orderedKeys = [
    "computer_architecture",
    "programming_skills",
    "project_management",
    "communication_skills",
    "openness",
    "conscientiousness",
    "extraversion",
    "agreeableness",
    "emotional_range",
    "conversation",
    "openness_change",
    "hedonism",
    "self_enhancement",
    "self_transcendence",
  ];

  async function testPrediction() {
    // Build array in correct order
    const finalValues = orderedKeys.map((key) => {
      const rawValue = values[key];
      return rawValue === "" || rawValue === undefined ? NaN : Number(rawValue);
    });

    // Check missing values
    if (finalValues.some((v) => !Number.isFinite(v))) {
      setResult("Enter a number for every field");
      return;
    }

    const response = await fetch("http://127.0.0.1:8000/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ values: finalValues }),
    });

    const data = await response.json();
    setResult(response.ok ? data.predicted_role : data.detail || "Prediction failed");
  }

  return (
    <div>
      <Features values={values} setValues={setValues} />
      <ResumeUpload />

      <div className="text-center mt-10">
        <button
          onClick={testPrediction}
          className="px-6 py-3 bg-black text-white rounded-lg text-lg"
        >
          Predict
        </button>

        <p className="mt-4 text-xl font-semibold">
          {result || "No input provided"}
        </p>
      </div>
    </div>
  );
}
