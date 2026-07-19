'use client'
import { motion } from 'framer-motion'
import Tilt from 'react-parallax-tilt'

const corr_features = [
  { name: 'Computer Architecture', key: 'computer_architecture', detail: 'Understanding processors, memory and hardware.' },
  { name: 'Programming Skills', key: 'programming_skills', detail: 'Ability to code and solve problems.' },
  { name: 'Project Management', key: 'project_management', detail: 'Handling tasks, planning, and deadlines.' },
  { name: 'Communication Skills', key: 'communication_skills', detail: 'Speaking, writing, teamwork ability.' },
]

const other_features = [
  { name: 'Openness', key: 'openness', detail: 'Creativity and open-mindedness.' },
  { name: 'Conscientousness', key: 'conscientousness', detail: 'Discipline and responsibility.' },
  { name: 'Extraversion', key: 'extraversion', detail: 'Social energy and interaction.' },
  { name: 'Agreeableness', key: 'agreeableness', detail: 'Cooperation and empathy.' },
  { name: 'Emotional Range', key: 'emotional_range', detail: 'Stability during stress.' },
  { name: 'Conversation', key: 'conversation', detail: 'Depth and clarity in communication.' },
  { name: 'Openness to Change', key: 'openness_change', detail: 'Acceptance of new ideas.' },
  { name: 'Hedonism', key: 'hedonism', detail: 'Preference for comfort and enjoyment.' },
  { name: 'Self-enhancement', key: 'self_enhancement', detail: 'Ambition and self-growth mindset.' },
  { name: 'Self-transcendence', key: 'self_transcendence', detail: 'Purpose, meaning, and values.' },
]

export default function Features({ values, setValues }) {
  const all = [...corr_features, ...other_features] // total 14

  return (
    <div className="py-10 px-10 relative">
      <h2 className="text-4xl font-bold text-center mb-14">Features</h2>

      <div className="grid md:grid-cols-2 gap-10 max-w-5xl mx-auto">

        {all.map((f, i) => (
          <Tilt
            key={i}
            tiltMaxAngleX={12}
            tiltMaxAngleY={12}
            glareEnable
            glareMaxOpacity={0.1}
            transitionSpeed={900}
          >
            <motion.div
              initial={{ opacity: 0, y: 25 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: i * 0.05 }}
              whileHover={{ scale: 1.05 }}
              className="p-6 border rounded-xl bg-white shadow-md hover:shadow-xl transition-all"
            >
              <h3 className="text-xl font-bold mb-2">{f.name}</h3>
              <p className="text-sm text-gray-600 mb-3">{f.detail}</p>

              <label className="text-sm font-semibold text-indigo-600">
                Enter value (1–10)
              </label>

              <input
                type="number"
                min="1"
                max="10"
                value={values[f.key] || ""}
                onChange={(e) =>
                  setValues({ ...values, [f.key]: e.target.value })
                }
                className="mt-2 w-full p-2 border rounded-lg"
              />
            </motion.div>
          </Tilt>
        ))}

      </div>
    </div>
  )
}
