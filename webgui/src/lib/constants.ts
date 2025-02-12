const baseUrl = new URL("http://localhost:8000");
export const API_BASE: string = `${ baseUrl.origin }/api`;
export const WS_URL: string = `ws://${ baseUrl.host }/ws`;
