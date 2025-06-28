import React, { useEffect, useState } from 'react';
import axios from 'axios';
import Sidebar from "../components/Sidebar";
import Header from "../components/Header";

const SettingsPage = () => {
  const [userInfo, setUserInfo] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Async function to fetch user info
    const fetchUserInfo = async () => {
      try {
        const bearer_token = localStorage.getItem("bearer_token");
        if (!bearer_token) {
          setError("No bearer token found.");
          return;
        }

        const response = await axios.get("http://localhost:8000/users/info", {
          headers: {
            Authorization: `Bearer ${bearer_token}`,
          },
        });

        // If successful, update user info state
        setUserInfo(response.data);
      } catch (err) {
        // Handle errors
        setError(err.response ? err.response.data.detail : "Something went wrong.");
      }
    };

    // Call the fetch function
    fetchUserInfo();
  }, []);

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-red-500">{error}</p>
      </div>
    );
  }

  if (!userInfo) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <Sidebar />

      <div className="flex-1 flex flex-col">
        {/* Header */}
        <Header />

        {/* Settings Content */}
        <div className="flex-grow p-6 bg-zinc-900">
          <h1 className="text-2xl font-bold mb-4 text-white">User Settings</h1>
          <div className="bg-neutral-800 p-6 rounded-lg shadow-md">
            <h2 className="text-xl font-semibold mb-2 text-white">User Info</h2>
            <div className="space-y-4">
              <div>
                <span className="font-medium text-white">Email:</span>
                <p className="text-white" >{userInfo.email}</p>
              </div>
              <div>
                <span className="font-medium text-white">Name:</span>
                <p className="text-white">{userInfo.name}</p>
              </div>
              <div>
                <span className="font-medium text-white">User ID:</span>
                <p className="text-white">{userInfo.userId}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;

