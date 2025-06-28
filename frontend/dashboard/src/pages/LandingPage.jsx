import React from "react";
import { useNavigate } from "react-router-dom";

function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen bg-black text-white">
      {/* Sidebar */}
      <aside className="w-1/2 bg-gray-900 flex flex-col justify-center items-center">
        <h1 className="text-4xl font-bold mb-6">Rainference</h1>
        <p className="text-lg text-gray-400 px-6 text-center">
          Advanced AI inference at your fingertips. Simplify AI integrations.
        </p>
      </aside>

      {/* Authentication Section */}
      <div className="flex-1 flex flex-col justify-center items-center">
        <h2 className="text-2xl font-bold mb-4">Welcome!</h2>
        <button
          onClick={() => navigate("/login")}
          className="bg-gray-800 px-6 py-3 rounded text-white hover:bg-gray-700"
        >
          Get Started
        </button>
      </div>
    </div>
  );
}

export default LandingPage;
