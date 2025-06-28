import React, { useState, useEffect } from "react";
import axios from "axios";
import { IoCopyOutline } from "react-icons/io5";

function HomePageContent() {
  const [apiKey, setApiKey] = useState("your-api-access-token");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchApiKey = async () => {
      try {
        const bearerToken = localStorage.getItem("bearer_token");
        if (!bearerToken) {
          setError("No bearer token found.");
          setLoading(false);
          return;
        }

        const response = await axios.get("http://localhost:8000/users/api-keys", {
          headers: {
            Authorization: `Bearer ${bearerToken}`,
          },
        });

        setApiKey(response.data.api_token); // Update with fetched API key
      } catch (err) {
        setError(err.response?.data?.detail || "Failed to fetch API key");
      } finally {
        setLoading(false);
      }
    };

    fetchApiKey();
  }, []);

  const handleCopyCode = () => {
    const code = `curl -N https://api.rainference.ai/v1/chat/completions \\
-H "Content-Type: application/json" \\
-H "Authorization: ${apiKey}" \\
-d '{
  "model": "meta-llama/llama-3.1-8b-instruct/fp-8",
  "messages": [
    { "role": "system", "content": "You are a helpful assistant." },
    { "role": "user", "content": "Rennaissance of the intelligent being?" }
  ],
  "stream": true
}'`;
    navigator.clipboard.writeText(code);
    alert("Code copied to clipboard!");
  };

  if (loading) {
    return <p>Loading API key...</p>;
  }

  if (error) {
    return <p className="text-red-500">Error: {error}</p>;
  }

  return (
    <section className="w-full max-w-7xl mx-auto">
      <h2 className="text-xl font-bold mb-4">Get started with InferenceAI</h2>
      <p className="mb-4">
        Run the command below to get started with your generated API key.
      </p>
      <div className="relative bg-neutral-800 p-4 rounded text-sm overflow-auto break-all">
        {/* Copy Button */}
        <button
          onClick={handleCopyCode}
          className="absolute top-2 right-2 bg-black hover:bg-gray-800 text-gray-400 py-1 px-1 rounded flex items-center justify-center"
          aria-label="Copy Code"
        >
          <IoCopyOutline className="h-5 w-5" />
        </button>
        <pre>
          <code>
          {`curl -N https://api.rainference.com/v1/chat/completions \\
-H "Content-Type: application/json" \\
-H "Authorization: `}
            <span className="font-bold text-blue-500">{apiKey}</span>
            {`" \\
-d '{
  "model": "meta-llama/llama-3.1-8b-instruct/fp-8",
  "prompt": "Rennaissance of the intelligent being?",
  "stream": "True",
  "max_tokens" : 50,
  "temperature" : 0.2
}'`}
        </code>
      </pre>
    </div>
  </section>
  );
}

export default HomePageContent;
