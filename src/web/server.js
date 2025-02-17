const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;
const PYTHON_API_URL = 'http://localhost:8000';

// Enable CORS
app.use(cors());

// Parse JSON bodies
app.use(express.json());

// Serve static files from the React app
app.use(express.static(path.join(__dirname, 'frontend/dist')));

// Proxy all /api requests to Python backend
app.use('/api', createProxyMiddleware({
  target: PYTHON_API_URL,
  changeOrigin: true,
  pathRewrite: {
    '^/api': '/api', // no rewrite needed since paths match
  },
}));

// Handle React routing, return all requests to React app
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'frontend/dist/index.html'));
});

app.listen(PORT, () => {
  console.log(`Node.js server is running on port ${PORT}`);
  console.log(`Proxying API requests to Python backend at ${PYTHON_API_URL}`);
});
