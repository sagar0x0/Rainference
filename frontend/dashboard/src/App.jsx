//App.jsx
import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import HomePage from "./pages/HomePage";
import ApiKeysPage from "./pages/ApiKeysPage";
import BillingPage from "./pages/BillingPage";
import SuccessPage from "./pages/SuccessPage";
import UsagePage from "./pages/UsagePage";
import ModelsPage from "./pages/ModelsPage.jsx";
import AnalyticsPage from "./pages/AnalyticsPage.jsx";
import SettingsPage from "./pages/SettingsPage.jsx";
import HelpPage from "./pages/HelpPage.jsx";

function App() {
  return (
    <Router>
      <Routes>
        {/* Landing Page - default route */}
        <Route path="/" element={<LandingPage />} />

        {/* Login Page */}
        <Route path="/login" element={<LoginPage />} />

        {/* Dashboard with nested routes */}
        <Route path="/dashboard/home" element={<HomePage />} />
        <Route path="/dashboard/api-keys" element={<ApiKeysPage />} />
        <Route path="/dashboard/billing" element={<BillingPage />} />
        <Route path="/dashboard/success" element={<SuccessPage />} />
        <Route path="/dashboard/usage" element={<UsagePage />} />
        <Route path="/dashboard/models" element={<ModelsPage />} />
        <Route path="/dashboard/analytics" element={<AnalyticsPage />} />
        <Route path="/dashboard/settings" element={<SettingsPage />} />
        <Route path="/dashboard/help" element={<HelpPage />} />
      </Routes>
    </Router>
  );
}

export default App;