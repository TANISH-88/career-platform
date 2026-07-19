"use client";
import { useState } from "react";

export default function PredictForm({ values, setValues }) {
  const [result, setResult] = useState("");

  function handleChange(key, value) {
    setValues({ ...values, [key]: value });
  }

  async function handlePredict() {
    const entries = Object.values(values);

    if (entries.length !== 14 || entries.some(v => v === "")) {
      setResult("No input provided");
      return;
    }

    const finalValues = entries.map(Number);

    try {
      const response = await fetch("http://127.0.0.1:8000/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ values: finalValues })
      });

      const data = await response.json();
      setResult(data.predicted_role || "Prediction failed");
    } catch (err) {
      console.error(err);
      setResult("API Error");
    }
  }

  return (
    <div className="text-center mt-10">
      <button
        onClick={handlePredict}
        className="px-6 py-3 bg-black text-white rounded-lg text-lg"
      >
        Predict
      </button>

      <p className="mt-4 text-xl font-semibold">
        {result || "No input provided"}
      </p>
    </div>
  );
}
