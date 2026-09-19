// This file can be replaced during build by using the `fileReplacements` array.
// `ng build --configuration production` replaces `environment.ts` with `environment.prod.ts`.
// The list of file replacements can be found in `angular.json`.

export const DEFAULT_APP_TITLE = 'Paperflow AI'

export const environment = {
  production: false,
  apiBaseUrl: document.baseURI + 'api/',
  apiVersion: '10',
  appTitle: DEFAULT_APP_TITLE,
  tag: 'dev',
  version: 'DEVELOPMENT',
  webSocketHost: window.location.host,
  webSocketProtocol: window.location.protocol === 'https:' ? 'wss:' : 'ws:',
  webSocketBaseUrl: '/ws/',
}
