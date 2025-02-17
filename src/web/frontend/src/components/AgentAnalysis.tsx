import React from 'react';
import {
  Box,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  CircularProgress,
  Paper,
  Grid,
} from '@mui/material';
import { ExpandMore as ExpandMoreIcon } from '@mui/icons-material';
import { useQuery } from 'react-query';
import axios from 'axios';

interface AgentData {
  agent_name: string;
  analysis: string;
  decision: string;
  confidence: number;
  metrics?: {
    [key: string]: number | string;
  };
}

export default function AgentAnalysis() {
  const { data, isLoading, error } = useQuery<AgentData[]>(
    'agentData',
    async () => {
      const response = await axios.get('/api/agent-data');
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
          Error loading agent data. Please try again later.
        </Typography>
      </Box>
    );
  }

  if (!data || data.length === 0) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography>No agent data available</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ width: '100%' }}>
      <Typography variant="h6" gutterBottom>
        Agent Analysis
      </Typography>
      {data.map((agent) => (
        <Accordion key={agent.agent_name}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Grid container alignItems="center" spacing={2}>
              <Grid item xs={8}>
                <Typography variant="subtitle1">
                  {agent.agent_name.replace(/_/g, ' ').toUpperCase()}
                </Typography>
              </Grid>
              <Grid item xs={4}>
                <Typography variant="body2" color="textSecondary">
                  Confidence: {(agent.confidence * 100).toFixed(1)}%
                </Typography>
              </Grid>
            </Grid>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    Analysis
                  </Typography>
                  <Typography variant="body1">{agent.analysis}</Typography>
                </Paper>
              </Grid>
              <Grid item xs={12}>
                <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    Decision
                  </Typography>
                  <Typography variant="body1">{agent.decision}</Typography>
                </Paper>
              </Grid>
              {agent.metrics && (
                <Grid item xs={12}>
                  <Paper variant="outlined" sx={{ p: 2 }}>
                    <Typography variant="h6" gutterBottom>
                      Metrics
                    </Typography>
                    <Grid container spacing={2}>
                      {Object.entries(agent.metrics).map(([key, value]) => (
                        <Grid item xs={6} sm={4} key={key}>
                          <Typography variant="subtitle2">
                            {key.replace(/_/g, ' ').toUpperCase()}
                          </Typography>
                          <Typography variant="body2">
                            {typeof value === 'number' ? value.toFixed(2) : value}
                          </Typography>
                        </Grid>
                      ))}
                    </Grid>
                  </Paper>
                </Grid>
              )}
            </Grid>
          </AccordionDetails>
        </Accordion>
      ))}
    </Box>
  );
}
