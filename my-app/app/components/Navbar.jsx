'use client'
import { motion } from 'framer-motion'


export default function Navbar() {
return (
<motion.nav
initial={{ y: -20, opacity: 0 }}
animate={{ y: 0, opacity: 1 }}
transition={{ duration: 0.5 }}
className="w-full py-5 flex justify-between items-center px-10 border-b"
>
<h1 className="text-2xl font-bold">FuturePredict</h1>
<button className="px-4 py-2 bg-black text-white rounded-lg">Get Started</button>
</motion.nav>
)
}