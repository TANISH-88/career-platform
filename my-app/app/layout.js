import "./globals.css";
import { AuthProvider } from "./components/AuthContext";
import ContinuePopup from "./components/ContinuePopup";
import Navbar from "./components/Navbar";

export const metadata = {
  title: "FuturePredict",
  description: "Prediction Website",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        {/* 🌈 Beautiful Gradient Background */}
        <div className="fixed inset-0 -z-10 overflow-hidden">
          <div className="absolute w-[600px] h-[600px] bg-purple-300 rounded-full blur-3xl opacity-30 animate-pulse-slow top-[-100px] left-[-100px]"></div>
          <div className="absolute w-[500px] h-[500px] bg-pink-200 rounded-full blur-3xl opacity-30 animate-pulse-slower bottom-[-100px] right-[-120px]"></div>
        </div>

        <AuthProvider>
          <Navbar />
          {children}
          <ContinuePopup />
        </AuthProvider>
      </body>
    </html>
  );
}
