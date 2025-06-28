import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom"; // <-- Import useNavigate
import axios from "axios";

const frontendUrl = import.meta.env.VITE_FRONTEND_URL;
const redirectUri = `${frontendUrl}/login`;

const LoginPage = () => {
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false); // <-- Add loading state
  const navigate = useNavigate(); // <-- Initialize navigate hook

  const handleGitHubLogin = () => {
    // ... (this function is already correct)
    const clientId = import.meta.env.VITE_GITHUB_CLIENT_ID;
    if (!clientId) {
      setError("GitHub Client ID is missing. Please check your configuration.");
      return;
    }
    const githubAuthUrl = `https://github.com/login/oauth/authorize?client_id=${clientId}&scope=user&redirect_uri=${encodeURIComponent(redirectUri)}`;
    window.location.href = githubAuthUrl;
  };

  useEffect(() => {
    const handleGitHubCallback = async (code) => {
      // Prevent re-entry if a request is already in flight
      if (isLoading) return;
      setIsLoading(true); // <-- Set loading to true
      setError(null);

      try {
        const backendUrl = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";
        const { data } = await axios.post(`${backendUrl}/auth/github`, { code });

        localStorage.setItem("bearer_token", data.bearer_token);
        axios.defaults.headers.common["Authorization"] = `Bearer ${data.bearer_token}`;

        // Use navigate for a smooth SPA transition instead of a full page reload
        navigate("/dashboard/home");
      } catch (err) {
        console.error("Error during GitHub authentication:", err.response?.data || err.message);
        setError(err.response?.data?.detail || err.message || "Login failed. Please try again.");
        setIsLoading(false); // <-- Reset loading state on error
      }
    };

    const code = new URLSearchParams(window.location.search).get("code");
    if (code) {
      // VERY IMPORTANT: Clean the URL to prevent the code from being used again on refresh
      window.history.replaceState({}, document.title, "/login");
      handleGitHubCallback(code);
    }
  }, [isLoading, navigate]); // <-- Add dependencies

  return (
    <div className="login-container flex flex-col items-center justify-center min-h-screen bg-gray-100">
      <div className="login-box bg-white p-8 rounded-lg shadow-md">
        <h2 className="text-2xl font-bold mb-6 text-center">Login to InferenceAI</h2>
        <button
          onClick={handleGitHubLogin}
          disabled={isLoading} // <-- Disable button while loading
          className="btn btn-github w-full py-3 bg-black text-white rounded hover:bg-gray-800 transition disabled:bg-gray-500"
        >
          {isLoading ? "Logging in..." : "Login with GitHub"}
        </button>
        {error && (
          <p className="text-red-500 text-sm mt-4 text-center">{error}</p>
        )}
      </div>
    </div>
  );
};

export default LoginPage;
