import React, { useState, useEffect } from "react";
import axios from "axios";
import Sidebar from "../components/Sidebar";
import Header from "../components/Header";

function ApiKeysPage() {
  const [apiKeys, setApiKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch the API keys from the backend
  useEffect(() => {
    const fetchApiKeys = async () => {
      try {
        const bearer_token = localStorage.getItem("bearer_token");
        if (!bearer_token) {
          setError("No bearer token found.");
          setLoading(false);
          return;
        }

        const response = await axios.get("http://localhost:8000/users/api-keys", {
          headers: {
            Authorization: `Bearer ${bearer_token}`, // Include the token if needed
          },
        });

        setApiKeys([{
          key: response.data.api_token, // Store only the key
          name: response.data.user_name,  // Add user_name
          createdBy: response.data.fname // Add fname
        }]);

      } catch (err) {
        setError(err.response?.data?.detail || "Failed to fetch API keys");
      } finally {
        setLoading(false);
      }
    };

    fetchApiKeys();
  }, []);

  // Regenerate a new API key (POST request to backend)
  const regenerateApiKey = async () => {
    try {
      const bearer_token = localStorage.getItem("bearer_token");
      if (!bearer_token) {
        setError("No bearer token found.");
        return;
      }

      const response = await axios.post(
        "http://localhost:8000/regenerate-token/",
        {},
        {
          headers: {
            Authorization: `Bearer ${bearer_token}`, // Include the token if needed
          },
        }
      );

      const newKey = response.data.new_api_token;
      setApiKeys([{key: newKey, name: apiKeys[0].name, createdBy: apiKeys[0].createdBy }]);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to regenerate API key");
    }
  };

  return (
    <div className="flex bg-zinc-900 text-white h-screen">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <Header title="API Keys" />

        
        {/* Content Area */}
        <main className="flex-1 p-6 overflow-auto">
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-2xl font-bold">API Keys</h1>
            <button
              onClick={regenerateApiKey}
              className="bg-emerald-800 text-white py-1 px-4 rounded hover:bg-emerald-600"
            >
              Regenerate
            </button>
          </div>

          {/* Display error if any */}
          {error && <div className="text-red-500 mb-4">{error}</div>}

          {/* Display loading state */}
          {loading ? (
            <div className="text-gray-300">Loading API keys...</div>
          ) : (
            <table className="w-full bg-neutral-800 text-white rounded-md overflow-hidden">
              <thead>
                <tr className="bg-neutral-800 text-left">
                  <th className="px-4 py-2">Name</th>
                  <th className="px-4 py-2">Secret Key</th>
                  <th className="px-4 py-2">Created By</th>
                </tr>
              </thead>
              <tbody>
                {apiKeys.map((key, index) => (
                  <tr
                    key={index}
                    className="hover:bg-gray-600"
                  >
                    <td className="px-4 py-2">{`${key.name}'s key`}</td>
                    <td className="px-4 py-2">{key.key}</td>
                    <td className="px-4 py-2">{key.createdBy}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </main>
      </div>
    </div>
  );
}

export default ApiKeysPage;