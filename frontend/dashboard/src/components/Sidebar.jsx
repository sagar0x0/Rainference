// components/Sidebar.jsx
import React from "react";
import {
  HomeIcon,
  ChartBarIcon,
  KeyIcon,
  DocumentTextIcon,
  CogIcon,
  ArrowTrendingUpIcon,
  QuestionMarkCircleIcon,
  CreditCardIcon,
} from "@heroicons/react/24/outline";
import { RiRobot3Line } from "react-icons/ri";
import { useLocation } from "react-router-dom"; // Import useLocation for active link highlighting

const menuItems = [
  { 
    name: "Home", 
    icon: HomeIcon, 
    href: "/dashboard/home" // Updated to use real routes
  },
  { 
    name: "Usage", 
    icon: ChartBarIcon, 
    href: "/dashboard/usage"
  },
  { 
    name: "API Keys", 
    icon: KeyIcon, 
    href: "/dashboard/api-keys" // Added route to API Keys page
  },
  { 
    name: "Models", 
    icon: RiRobot3Line, 
    href: "/dashboard/models"
  },
  { 
    name: "Docs", 
    icon: DocumentTextIcon, 
    href: "/dashboard/docs"
  },
  { 
    name: "Settings", 
    icon: CogIcon, 
    href: "/dashboard/settings"
  },
  { 
    name: "Analytics", 
    icon: ArrowTrendingUpIcon, 
    href: "/dashboard/analytics"
  },
  { 
    name: "Billing", 
    icon: CreditCardIcon, 
    href: "/dashboard/billing"
  },
  { 
    name: "Help", 
    icon: QuestionMarkCircleIcon, 
    href: "/dashboard/help"
  },
];

function Sidebar() {
  const location = useLocation(); // Get the current route location

  return (
    <div className="w-64 bg-black text-white flex flex-col h-screen">
      <div className="p-6 text-2xl font-bold">Rainference</div>
      
      <nav className="flex-grow">
        {menuItems.map((item) => {
          const IconComponent = item.icon;
          const isActive = location.pathname === item.href; // Check if the current path matches the item href

          return (
            <a
              key={item.name}
              href={item.href}
              className={`flex items-center p-4 hover:bg-gray-700 ${isActive ? "bg-grey-700" : ""}`}
            >
              <IconComponent className="w-6 h-6 mr-3" />
              <span>{item.name}</span>
            </a>
          );
        })}
      </nav>
      
      
    </div>
  );
}

export default Sidebar;
