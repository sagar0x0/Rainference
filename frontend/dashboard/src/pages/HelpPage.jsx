import React, { useState } from 'react';
// need to setup backend
const HelpPage = () => {
  const [issue, setIssue] = useState('');
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Basic validation
    if (!email || !message) {
      alert('Please provide an email and a message.');
      return;
    }

    // Example for sending data to a backend or email service
    try {
      // For now, just simulate a successful form submission
      setSuccessMessage('Your complaint has been sent successfully!');

      // Here you would send the email, e.g., using a backend API or email service like SendGrid
      // fetch('/api/send-email', { method: 'POST', body: JSON.stringify({ email, message }) })

      // Reset form fields
      setEmail('');
      setMessage('');
    } catch (error) {
      console.error('Error sending complaint:', error);
      alert('Something went wrong. Please try again later.');
    }
  };

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold text-center mb-6">Help / Complaint Page</h1>
      
      {successMessage && (
        <div className="bg-green-100 text-green-800 p-4 rounded-md mb-6">
          {successMessage}
        </div>
      )}

      <form onSubmit={handleSubmit} className="bg-white p-6 shadow-md rounded-lg">
        <div className="mb-4">
          <label htmlFor="email" className="block text-sm font-semibold text-gray-700">Your Email</label>
          <input
            type="email"
            id="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full p-3 mt-2 border border-gray-300 rounded-md"
            placeholder="Your email address"
            required
          />
        </div>

        <div className="mb-4">
          <label htmlFor="message" className="block text-sm font-semibold text-gray-700">Your Complaint</label>
          <textarea
            id="message"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            className="w-full p-3 mt-2 border border-gray-300 rounded-md"
            rows="5"
            placeholder="Describe your issue..."
            required
          ></textarea>
        </div>

        <button
          type="submit"
          className="w-full bg-blue-600 text-white py-3 rounded-md hover:bg-blue-700"
        >
          Submit Complaint
        </button>
      </form>
    </div>
  );
};

export default HelpPage;
