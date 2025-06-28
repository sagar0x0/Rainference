// components/Header.jsx
import React from "react";
import { MoonIcon, SunIcon, UserCircleIcon } from "@heroicons/react/24/outline";

function Header() {
  return (
    <header className="p-3 flex justify-between items-center bg-black w-full max-w-screen">
      {/* Empty space instead of title */}
      <div className="text-2xl font-bold" />

      {/* Actions */}
      <div className="flex items-center space-x-4">
      {/* Documentation Button */}
        <button className="bg-gray-950 px-1 py-1 rounded text-gray-300 font-medium hover:font-semibold hover:text-white active:font-bold active:text-white">
        Docs
        </button>
      
        {/* Dark/Light Mode Toggle */}
        <button
          className="bg-gray-950 p-1 rounded-full hover:bg-gray-700"
          aria-label="Toggle Dark/Light Mode"
        >
          <MoonIcon className="h-6 w-6 text-white" />
          {/* Swap the icon to <SunIcon /> for light mode */}
        </button>

        {/* Account Icon */}
        <button
          className="bg-gray-800 p-1 rounded-full hover:bg-gray-700"
          aria-label="Account"
        >
          <UserCircleIcon className="h-6 w-6 text-white" />
        </button>
      </div>
    </header>
  );
}

export default Header;
