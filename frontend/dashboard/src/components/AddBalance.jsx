import React, { useState } from "react";

const AddBalanceModal = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [amount, setAmount] = useState(50);
  const [currentBalance, setCurrentBalance] = useState(1); // Example balance

  const handleCheckout = () => {
    // Add your Stripe integration logic here
    console.log("Redirecting to Stripe...");
    setIsOpen(false);
  };

  return (
    <>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(true)}
        className="bg-green-500 px-4 py-2 rounded text-white mt-2"
      >
        Add to Balance
      </button>

      {/* Modal */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-gray-800 text-white rounded-lg shadow-lg w-96 p-6">
            {/* Modal Header */}
            <div className="text-lg font-semibold mb-4">Add to your balance</div>
            <p className="text-sm mb-4">
              You'll be redirected to Stripe to complete your purchase.
            </p>

            {/* Amount Selection */}
            <div className="flex space-x-2 mb-4">
              {[5, 25, 50, 100].map((value) => (
                <button
                  key={value}
                  className={`px-4 py-2 rounded ${
                    amount === value
                      ? "bg-blue-500 text-white"
                      : "bg-gray-700 hover:bg-gray-600"
                  }`}
                  onClick={() => setAmount(value)}
                >
                  ${value}
                </button>
              ))}
              <input
                type="number"
                className="bg-gray-700 text-white px-4 py-2 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Custom"
                value={amount}
                onChange={(e) => setAmount(Number(e.target.value))}
              />
            </div>

            {/* Balance Display */}
            <div className="text-sm mb-4">
              Balance after purchase:{" "}
              <span className="font-semibold">${currentBalance + amount}</span>
            </div>

            {/* Buttons */}
            <div className="flex justify-end space-x-4">
              <button
                onClick={handleCheckout}
                className="bg-blue-500 px-4 py-2 rounded text-white hover:bg-blue-600"
              >
                Checkout
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="bg-gray-700 px-4 py-2 rounded text-white hover:bg-gray-600"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default AddBalanceModal;
