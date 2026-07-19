'use client'
import { motion } from 'framer-motion'

export default function Hero() {
  return (
    <section className="py-20 flex flex-col items-center justify-center text-center px-4">
      <motion.h1
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7 }}
        className="text-5xl font-bold mb-6"
      >
        Predict Your Future With Confidence
      </motion.h1>

      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5, duration: 0.7 }}
        className="text-xl text-gray-600 max-w-2xl"
      >
        Enter 15+ features and get intelligent predictions instantly.
      </motion.p>
    </section>
  )
}
