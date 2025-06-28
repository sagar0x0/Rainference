import React from "react";
import Sidebar from "../components/Sidebar";
import Header from "../components/Header";
import HomePageContent from "../components/HomePageContent";



function HomePage() {
  return (
    <div className="flex min-h-screen bg-zinc-900 text-white">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        <Header />
        <main className="p-6">
          <HomePageContent />
        </main>
      </div>
    </div>
  );
}

export default HomePage;