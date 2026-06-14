// Environment used only by the Playwright e2e suite (see playwright.config.ts).
//
// The recorded HAR fixtures in e2e/**/requests/*.har capture API/WebSocket
// traffic against http://localhost:8000. The default dev `environment.ts`
// derives the API URL from `document.baseURI` (so the docker dev proxy can
// serve everything same-origin from :4200), which means its requests go to
// :4200 and no longer match the fixtures. Pinning the absolute :8000 host here
// keeps the served app's requests aligned with the HARs so routeFromHAR can
// fulfil them offline.
export const environment = {
  production: false,
  apiBaseUrl: 'http://localhost:8000/api/',
  apiVersion: '10',
  appTitle: 'Paperflow AI',
  tag: 'dev',
  version: 'DEVELOPMENT',
  webSocketHost: 'localhost:8000',
  webSocketProtocol: 'ws:',
  webSocketBaseUrl: '/ws/',
}
