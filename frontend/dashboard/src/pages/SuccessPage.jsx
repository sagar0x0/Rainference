import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

const SuccessPage = () => {
  const location = useLocation();
  const navigate = useNavigate(); // Use useNavigate instead of useHistory
  const [sessionId, setSessionId] = useState(null);

  useEffect(() => {
    // Get the session_id from the query parameters in the URL
    const params = new URLSearchParams(location.search);
    const session_id = params.get("session_id");
    setSessionId(session_id);
  }, [location]);

  const handleGoToDashboard = () => {
    // Use navigate to redirect to the dashboard page
    navigate("/dashboard/billing");
  };

  return (
    <div style={{ padding: "20px", textAlign: "center" }}>
      <h1>Payment Successful!</h1>
      {sessionId && <p>Your session ID: {sessionId}</p>}
      <p>Your payment was successfully processed, and your tokens have been credited.</p>
      <button
        style={{
          padding: "10px 20px",
          fontSize: "16px",
          backgroundColor: "#007bff",
          color: "white",
          border: "none",
          borderRadius: "4px",
          cursor: "pointer",
        }}
        onClick={handleGoToDashboard}
      >
        Go to Dashboard
      </button>
    </div>
  );
};

export default SuccessPage;
