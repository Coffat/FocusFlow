const target = process.env.BACKEND_URL || 'http://localhost:8000';

module.exports = {
  '/api': {
    target: target,
    secure: false,
    changeOrigin: true
  }
};
