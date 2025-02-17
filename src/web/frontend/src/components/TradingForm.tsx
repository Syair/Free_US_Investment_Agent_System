 import React, { useState } from 'react';
import {
  Box,
  TextField,
  Button,
  Typography,
  Grid,
  FormControlLabel,
  Switch,
} from '@mui/material';
import { useMutation } from 'react-query';
import axios from 'axios';

interface TradingFormData {
  ticker: string;
  startDate: string;
  endDate: string;
  initialCapital: number;
  showReasoning: boolean;
  numOfNews: number;
}

export default function TradingForm() {
  const [formData, setFormData] = useState<TradingFormData>({
    ticker: '',
    startDate: '',
    endDate: '',
    initialCapital: 100000,
    showReasoning: false,
    numOfNews: 5,
  });

  const startTrading = useMutation(
    (data: TradingFormData) =>
      axios.post('/api/start-trading', {
        ticker: data.ticker,
        start_date: data.startDate,
        end_date: data.endDate,
        initial_capital: data.initialCapital,
        show_reasoning: data.showReasoning,
        num_of_news: data.numOfNews,
      }),
    {
      onSuccess: (response) => {
        console.log('Trading started:', response.data);
      },
      onError: (error) => {
        console.error('Error starting trading:', error);
      },
    }
  );

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    startTrading.mutate(formData);
  };

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = event.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ mt: 2 }}>
      <Typography variant="h6" gutterBottom>
        Trading Parameters
      </Typography>
      <Grid container spacing={3}>
        <Grid item xs={12} sm={6}>
          <TextField
            required
            fullWidth
            name="ticker"
            label="Stock Ticker"
            value={formData.ticker}
            onChange={handleChange}
          />
        </Grid>
        <Grid item xs={12} sm={6}>
          <TextField
            fullWidth
            type="number"
            name="initialCapital"
            label="Initial Capital"
            value={formData.initialCapital}
            onChange={handleChange}
          />
        </Grid>
        <Grid item xs={12} sm={6}>
          <TextField
            fullWidth
            type="date"
            name="startDate"
            label="Start Date"
            InputLabelProps={{ shrink: true }}
            value={formData.startDate}
            onChange={handleChange}
          />
        </Grid>
        <Grid item xs={12} sm={6}>
          <TextField
            fullWidth
            type="date"
            name="endDate"
            label="End Date"
            InputLabelProps={{ shrink: true }}
            value={formData.endDate}
            onChange={handleChange}
          />
        </Grid>
        <Grid item xs={12} sm={6}>
          <TextField
            fullWidth
            type="number"
            name="numOfNews"
            label="Number of News Articles"
            value={formData.numOfNews}
            onChange={handleChange}
          />
        </Grid>
        <Grid item xs={12} sm={6}>
          <FormControlLabel
            control={
              <Switch
                name="showReasoning"
                checked={formData.showReasoning}
                onChange={handleChange}
              />
            }
            label="Show Agent Reasoning"
          />
        </Grid>
        <Grid item xs={12}>
          <Button
            type="submit"
            variant="contained"
            color="primary"
            disabled={startTrading.isLoading}
          >
            {startTrading.isLoading ? 'Starting...' : 'Start Trading'}
          </Button>
        </Grid>
      </Grid>
    </Box>
  );
}
