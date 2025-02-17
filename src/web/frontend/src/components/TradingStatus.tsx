import React from 'react';
import {
  Box,
  Typography,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  Divider,
} from '@mui/material';
import { useQuery } from 'react-query';
import axios from 'axios';

interface TradingResult {
  status: string;
  result: {
    decision: string;
    reasoning?: string;
    portfolio: {
      cash: number;
      stock: number;
    };
  };
  parameters: {
    ticker: string;
    start_date: string;
    end_date: string;
    initial_capital: number;
  };
}

export default function TradingStatus() {
  const { data, isLoading, error } = useQuery<TradingResult>(
    'tradingStatus',
    async () => {
      const response = await axios.get('/api/trading-status');
      return response.data;
    },
    {
      refetchInterval: 5000, // Refresh every 5 seconds
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
          Error loading trading status. Please try again later.
        </Typography>
      </Box>
    );
  }

  if (!data) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography>No active trading session</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Trading Status
      </Typography>
      <List>
        <ListItem>
          <ListItemText
            primary="Status"
            secondary={data.status}
          />
        </ListItem>
        <Divider />
        <ListItem>
          <ListItemText
            primary="Current Position"
            secondary={`Cash: $${data.result.portfolio.cash.toFixed(2)} | Stock: ${
              data.result.portfolio.stock
            } shares`}
          />
        </ListItem>
        <Divider />
        <ListItem>
          <ListItemText
            primary="Latest Decision"
            secondary={data.result.decision}
          />
        </ListItem>
        {data.result.reasoning && (
          <>
            <Divider />
            <ListItem>
              <ListItemText
                primary="Reasoning"
                secondary={data.result.reasoning}
              />
            </ListItem>
          </>
        )}
        <Divider />
        <ListItem>
          <ListItemText
            primary="Trading Parameters"
            secondary={`${data.parameters.ticker} | ${data.parameters.start_date} to ${data.parameters.end_date}`}
          />
        </ListItem>
      </List>
    </Box>
  );
}
