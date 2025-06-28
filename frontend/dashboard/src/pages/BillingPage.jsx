import React, { useState, useEffect } from "react";
import { loadStripe } from "@stripe/stripe-js";
import { Elements, CardElement, useElements, useStripe } from "@stripe/react-stripe-js";
import axios from "axios";
import Sidebar from "../components/Sidebar";
import Header from "../components/Header";

// Set your Stripe public key here
const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY);


const PaymentForm = () => {
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [paymentStatus, setPaymentStatus] = useState("");
  const [amount, setAmount] = useState(1000); // Example: amount in cents (1000 = $10)
  const [balance, setBalance] = useState(1.00); // Example balance
  const [billingHistory, setBillingHistory] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false); // State for modal visibility
  const [customAmount, setCustomAmount] = useState(50); // Amount for adding balance
  
  const stripe = useStripe();
  const elements = useElements();

  // Fetch balance and billing history
  useEffect(() => {
    const fetchBillingData = async () => {
    try {
        const bearer_token = localStorage.getItem("bearer_token");
        if (!bearer_token) {
        setError("No bearer token found.");
        return;
        }

        const response = await axios.get("http://localhost:8000/get-billing-data", {
        headers: {
            Authorization: `Bearer ${bearer_token}`,
        },
        });

        setBalance(response.data.balance);
        setBillingHistory(response.data.billingHistory || []);  // Default to empty array if missing
    } catch (error) {
        console.error("Error fetching billing data:", error);
        setError("Error fetching billing data.");
    }
    };

    fetchBillingData(); // Call the function on component mount
    }, []); // Empty dependency array ensures this runs only once when the component mounts



  // Create Payment Intent for manual flow
  const createPaymentIntent = async () => {
    try {
      const response = await axios.post("http://localhost:8000/create-payment-intent", {
        amount,
      });
      setPaymentStatus(response.data.clientSecret);
    } catch (error) {
      console.error("Error creating payment intent:", error);
    }
  };

  // New hosted checkout flow
  const createCheckoutSession = async (amountToCharge) => {
    try {
      const bearer_token = localStorage.getItem("bearer_token");
      if (!bearer_token) {
        setError("No bearer token found.");
        return;
      }

      const response = await fetch("http://localhost:8000/create-checkout-session", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${bearer_token}`,
        },
        body: JSON.stringify({
            amount: amountToCharge * 100, // Convert dollars to cents, // Amount in cents
        }),
      });

      const session = await response.json();
      window.location.href = session.checkout_url; // Redirect to Stripe checkout page
    } catch (error) {
      console.error("Error creating checkout session:", error);
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    
    if (!stripe || !elements) {
      return; // Ensure stripe and elements are loaded before proceeding
    }
  
    setIsProcessing(true);
    setPaymentStatus("");
  
    // Confirm the payment using Stripe's client secret
    const { error, paymentIntent } = await stripe.confirmCardPayment(
      paymentStatus.clientSecret,
      {
        payment_method: {
          card: elements.getElement(CardElement),
        },
      }
    );
  
    if (error) {
      setPaymentStatus(error.message);
    } else {
      setPaymentStatus("Payment successful!");
      // Handle success (update user's balance, backend API call, etc.)
    }
    setIsProcessing(false);
  };
  

  return (
    <div className="flex bg-zinc-900 text-white h-screen">
      {/* Sidebar */}
      <Sidebar /> {/* Keep the Sidebar Component */}

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <Header title="Billing" /> {/* Keep the Header Component */}

        {/* Content Area */}
        <main className="flex-1 p-6 overflow-auto relative">
          <div className="bg-zinc-900 p-6 rounded-lg shadow-lg space-y-6 relative">    
            {/* Billing Title at top left */}
            <div className="text-2xl font-bold absolute top-1 left-6">
            Billing
            </div>

            
            <div className="flex flex-col mb-1 pb-1 border-b border-gray-700">
            {/* Current Balance */}
            <div className="flex flex-col mb-1">
                <h2 className="text-xl font-semibold">Current Balance</h2>
                <p className="text-4xl font-bold mt-2">${balance}</p>
            </div>

            {/* Add to Balance and View Pricing */}
            <div className="flex justify-between mb-4">
                <button 
                    onClick={() => setIsModalOpen(true)} 
                    className="bg-green-500 px-4 py-2 rounded text-white mt-2">
                Add to Balance
                </button>
                <button className="bg-blue-500 px-4 py-2 rounded text-white ">
                View Pricing
                </button>
            </div>
            </div>

            {/* Payment Methods */}
            <div className="mb-6 border-b border-gray-700 pb-6">
                <h3 className="text-lg font-semibold">Payment Methods</h3>
                <button 
                    onClick={createCheckoutSession} 
                className="bg-gray-700 px-4 py-1 rounded text-white mt-4"  // Added mt-4 for margin-top
                >
                    Go to Stripe
                </button>
            </div>

            {/* Billing History */}
            <div className="border-b border-gray-700 pb-6">
              <h3 className="text-lg font-semibold">Billing History</h3>
              <ul className="mt-4 space-y-2">
                {billingHistory.length === 0 ? (
                  <li>No billing history.</li>
                ) : (
                  billingHistory.map((entry, index) => (
                    <li key={index} className="text-sm text-gray-400">
                      {entry.date} - ${entry.amount} - {entry.status}
                    </li>
                  ))
                )}
              </ul>
            </div>
          </div>
        </main>
      </div>

    {/* Modal */}
    {isModalOpen && (
        <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-50">
          <div className="bg-gray-800 text-white rounded-lg shadow-lg w-111 p-6">
            <h3 className="text-lg font-semibold mb-4">Add to Balance</h3>
            <p className="text-sm mb-4">
              You'll be redirected to Stripe to complete your payment.
            </p>
            <div className="flex space-x-2 mb-4">
              {[5, 25, 50, 100].map((value) => (
                <button
                  key={value}
                  className={`px-4 py-2 rounded ${
                    customAmount === value
                      ? "bg-blue-500 text-white"
                      : "bg-gray-700 hover:bg-gray-600"
                  }`}
                  onClick={() => setCustomAmount(value)}
                >
                  ${value}
                </button>
              ))}
              <input
                type="number"
                className="bg-gray-700 text-white px-4 py-2 rounded focus:outline-none"
                placeholder="Custom"
                value={customAmount}
                onChange={(e) => setCustomAmount(Number(e.target.value))}
              />
            </div>
            <div className="flex justify-end space-x-4">
              <button
                onClick={() => {
                  createCheckoutSession(customAmount);
                  setIsModalOpen(false);
                }}
                className="bg-blue-500 px-4 py-2 rounded text-white hover:bg-blue-600"
              >
                Checkout
              </button>
              <button
                onClick={() => setIsModalOpen(false)}
                className="bg-gray-700 px-4 py-2 rounded text-white hover:bg-gray-600"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>

        )}
    </div>
    );
};

const BillingPage = () => {
  return (
    <Elements stripe={stripePromise}>
      <PaymentForm />
    </Elements>
  );
};

export default BillingPage;
