// Proxy backend routes to Django.
// BACKEND_HOST defaults to localhost (direct ng serve on host);
// docker-compose.override.yml sets it to the Docker service name "webserver".
const backendHost = process.env.BACKEND_HOST || 'localhost'
const backendUrl = `http://${backendHost}:8000`

module.exports = {
  '/api':      { target: backendUrl, secure: false, changeOrigin: false },
  '/accounts': { target: backendUrl, secure: false, changeOrigin: false },
  '/admin':    { target: backendUrl, secure: false, changeOrigin: false },
  '/static':   { target: backendUrl, secure: false, changeOrigin: false },
  '/media':    { target: backendUrl, secure: false, changeOrigin: false },
  '/ws':       { target: backendUrl, secure: false, changeOrigin: false, ws: true },
}
