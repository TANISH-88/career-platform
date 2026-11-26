"use client";

import Link from "next/link";
import { useState } from "react";
import Features from "./components/Features";
import Hero from "./components/Hero";
import ResumeUpload from "./components/ResumeUpload";
import { useAuth } from "./components/AuthContext";
import { ORDERED_SKILL_KEYS } from "../lib/continuePopupLogic.mjs";

export default function Home() {
  const [values, setValues] = useState({});
  const [result, setResult] = useState("");
  const { isAuthenticated } = useAuth();

  async function testPrediction() {
    // Build array in correct order
    const finalValues = ORDERED_SKILL_KEYS.map((key) => {
      const rawValue = values[key];
      return rawValue === "" || rawValue === undefined ? NaN : Number(rawValue);
    });

    // Check missing values
    if (finalValues.some((v) => !Number.isFinite(v))) {
      setResult("Enter a number for every field");
      return;
    }

    try {
      // Anonymous prediction remains unauthenticated and stateless via same-origin proxy
      const response = await fetch("/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ values: finalValues }),
      });

      const data = await response.json();
      setResult(response.ok ? data.predicted_role : data.detail || "Prediction failed");
    } catch {
      setResult("Connection error: backend server is unreachable");
    }
  }

  return (
    <div>
      <Hero />
      <Features values={values} setValues={setValues} />
      <ResumeUpload onApplyScores={(mapped) => setValues((prev) => ({ ...prev, ...mapped }))} />

      <div className="text-center mt-10 pb-16">
        <button
          onClick={testPrediction}
          className="px-6 py-3 bg-black text-white rounded-lg text-lg"
        >
          Predict
        </button>

        <p className="mt-4 text-xl font-semibold">
          {result || "No input provided"}
        </p>

        <p className="mt-3 text-sm text-gray-500">
          {isAuthenticated ? (
            <>
              Anonymous quick prediction above. Want to save history?{" "}
              <Link href="/workspaces" className="font-semibold text-indigo-600 hover:underline">
                Open a workspace
              </Link>
              .
            </>
          ) : (
            <>
              Sign in or{" "}
              <Link href="/register" className="font-semibold text-indigo-600 hover:underline">
                create an account
              </Link>{" "}
              to save predictions in workspaces.
            </>
          )}
        </p>
      </div>
    </div>
  );
}
