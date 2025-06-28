{/* not using rn */}
import React from "react";
import Sidebar from "../components/Sidebar";
import Header from "../components/Header";
import { Outlet } from "react-router-dom";  // Import Outlet for nested routing


function Dashboard() {
  return (
    <div className="flex min-h-screen bg-zinc-900 text-white">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        <Header />
        <main className="p-6">
          {/* Render nested routes here */}
          <Outlet />  {/* Nested routes will render inside here */}
        </main>
      </div>
    </div>
  );
}

export default Dashboard;
