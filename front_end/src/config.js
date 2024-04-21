// The API base URL is the only deployment-specific value in the bundle.
// No credentials live here: the browser never talks to a model provider,
// it talks to this project's own API, which holds any key server-side.
export const API_BASE_URL =
  process.env.REACT_APP_API_URL || 'http://localhost:7241';

export const CONFIDENCE_BANDS = [
  { min: 0.8, label: 'strong', color: 'success' },
  { min: 0.55, label: 'likely', color: 'info' },
  { min: 0.0, label: 'review', color: 'warning' },
];

export function bandFor(confidence) {
  return CONFIDENCE_BANDS.find((band) => confidence >= band.min);
}
