import React, { useEffect, useState } from 'react';
import { Line } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, LineElement, PointElement, Title, Tooltip, Legend } from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, LineElement, PointElement, Title, Tooltip, Legend);

const UsageDashboard = () => {
    const [usageData, setUsageData] = useState([]);
    
    useEffect(() => {
        // Fetch the usage data from your FastAPI backend
        fetch('/usage_dashboard')
            .then(response => response.json())
            .then(data => {
                setUsageData(data.usage_data);
            })
            .catch(err => console.error("Error fetching data:", err));
    }, []);

    const chartData = {
        labels: usageData.map(item => item.model),
        datasets: [
            {
                label: 'Token Usage (Total Tokens)',
                data: usageData.map(item => item.total_tokens),
                borderColor: 'rgba(75,192,192,1)',
                backgroundColor: 'rgba(75,192,192,0.2)',
                fill: true,
            },
            {
                label: 'Spending',
                data: usageData.map(item => item.total_spending),
                borderColor: 'rgba(255,99,132,1)',
                backgroundColor: 'rgba(255,99,132,0.2)',
                fill: false,
            },
        ],
    };

    return (
        <div>
            <h2>Usage Dashboard</h2>
            <Line data={chartData} />
        </div>
    );
};

export default UsageDashboard;
