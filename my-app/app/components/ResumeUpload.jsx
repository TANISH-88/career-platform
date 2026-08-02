"use client";

import { useState } from "react";

const scoreFields = [
  ["Computer Architecture", "computer_architecture"],
  ["Programming Skills", "programming_skills"],
  ["Project Management", "project_management"],
  ["Communication Skills", "communication_skills"],
  ["Openness", "openness"],
  ["Conscientiousness", "conscientiousness"],
  ["Extraversion", "extraversion"],
  ["Agreeableness", "agreeableness"],
  ["Emotional Range", "emotional_range"],
  ["Conversation", "conversation"],
  ["Openness Change", "openness_change"],
  ["Hedonism", "hedonism"],
  ["Self-Enhancement", "self_enhancement"],
  ["Self-Transcendence", "self_transcendence"],
];

export default function ResumeUpload() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("Upload a PDF or DOCX resume to score it.");
  const [result, setResult] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleUpload() {
    if (!file) {
      setStatus("Choose a PDF or DOCX file first.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setIsSubmitting(true);
    setStatus("Parsing resume...");
    setResult(null);

    try {
      const response = await fetch("http://127.0.0.1:8000/parse-resume", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();

      if (!response.ok) {
        setStatus(data.detail || "Resume parsing failed.");
        return;
      }

      setResult(data);
      setStatus("Resume parsed successfully.");
    } catch (error) {
      console.error(error);
      setStatus("Resume API error.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="px-6 py-12">
      <div className="mx-auto max-w-5xl rounded-3xl border border-gray-200 bg-white/80 p-8 shadow-2xl backdrop-blur">
        <div className="flex flex-col gap-3">
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-indigo-600">
            Resume Scan
          </p>
          <h2 className="text-3xl font-bold text-gray-900">Score a resume before predicting a role</h2>
          <p className="max-w-2xl text-sm text-gray-600">
            Upload a PDF or DOCX file and the backend will extract text, call Gemini, and return
            the 14 skill scores used by the prediction pipeline.
          </p>
        </div>

        <div className="mt-8 grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
          <label className="flex flex-col gap-2 text-sm font-semibold text-gray-800">
            Resume file
            <input
              type="file"
              accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              className="block w-full rounded-2xl border border-dashed border-gray-300 bg-gray-50 px-4 py-3 text-sm text-gray-700 file:mr-4 file:rounded-xl file:border-0 file:bg-black file:px-4 file:py-2 file:text-white hover:border-gray-400"
            />
          </label>

          <button
            type="button"
            onClick={handleUpload}
            disabled={isSubmitting}
            className="rounded-2xl bg-black px-6 py-3 text-sm font-semibold text-white transition disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? "Parsing..." : "Parse resume"}
          </button>
        </div>

        <p className="mt-4 text-sm text-gray-600">{status}</p>

        {result ? (
          <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {scoreFields.map(([label, key]) => (
              <div key={key} className="rounded-2xl border border-gray-200 bg-gray-50 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.3em] text-gray-500">{label}</p>
                <p className="mt-2 text-2xl font-bold text-gray-900">{Number(result[key]).toFixed(1)}</p>
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </section>
  );
}
