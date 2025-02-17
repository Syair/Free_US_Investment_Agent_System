import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Box, Typography, CircularProgress } from '@mui/material';
import { useQuery } from 'react-query';
import axios from 'axios';

interface PortfolioData {
  timestamp: string;
  portfolio_value: number;
  cash: number;
  stock_value: number;
}

interface ChartData extends PortfolioData {
  date: string;
}

export default function PortfolioChart() {
  const { data, isLoading, error } = useQuery<PortfolioData[]>(
    'portfolioHistory',
    async () => {
      const response = await axios.get('/api/trading-results');
      return response.data;
    },
    {
      refetchInterval: 5000,
    }
  );

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography color="error">
          Error loading portfolio data. Please try again later.
        </Typography>
      </Box>
    );
  }

  if (!data || data.length === 0) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography>No portfolio data available</Typography>
      </Box>
    );
  }

  const chartData: ChartData[] = data.map((item) => ({
    ...item,
    date: new Date(item.timestamp).toLocaleDateString(),
  }));

  return (
    <Box sx={{ width: '100%', height: 400 }}>
      <Typography variant="h6" gutterBottom>
        Portfolio Performance
      </Typography>
      <ResponsiveContainer>
        <LineChart
          data={chartData}
          margin={{
            top: 5,
            right: 30,
            left: 20,
            bottom: 5,
          }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line
            type="monotone"
            dataKey="portfolio_value"
            name="Total Value"
            stroke="#8884d8"
            activeDot={{ r: 8 }}
          />
          <Line
            type="monotone"
            dataKey="cash"
            name="Cash"
            stroke="#82ca9d"
          />
          <Line
            type="monotone"
            dataKey="stock_value"
            name="Stock Value"
            stroke="#ffc658"
          />
        </LineChart>
      </ResponsiveContainer>
    </Box>
  );
}
