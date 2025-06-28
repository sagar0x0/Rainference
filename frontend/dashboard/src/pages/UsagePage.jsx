import React, { useEffect, useState } from 'react';
import { Line } from 'react-chartjs-2';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    LineElement,
    PointElement,
    Title,
    Tooltip,
    Legend,
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, LineElement, PointElement, Title, Tooltip, Legend);

const UsageDashboard = () => {
    const [usageData, setUsageData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchData = async () => {
            const token = localStorage.getItem("bearer_token");

            try {
                const response = await fetch('http://localhost:8000/usage_dashboard', {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                    },
                });

                if (!response.ok) throw new Error("Failed to fetch usage data.");

                const data = await response.json();
                setUsageData(data.usage_data || []);
            } catch (err) {
                console.error("Error fetching data:", err);
                setError(err.message || "Unknown error");
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    const chartData = {
        labels: (usageData || []).map(item => item.model),
        datasets: [
            {
                label: 'Token Usage (Total Tokens)',
                data: (usageData || []).map(item => item.total_tokens),
                borderColor: 'rgb(2, 3, 3)',
                backgroundColor: 'rgba(75,192,192,0.2)',
                fill: true,
            },
            {
                label: 'Spending',
                data: (usageData || []).map(item => item.total_spending),
                borderColor: 'rgba(255,99,132,1)',
                backgroundColor: 'rgba(255,99,132,0.2)',
                fill: false,
            },
        ],
    };

    if (loading) return <p>Loading...</p>;
    if (error) return <p>Error: {error}</p>;

    return (
        <div>
            <h2>Usage Dashboard</h2>
            <Line data={chartData} />
        </div>
    );
};

export default UsageDashboard;

