import { API_BASE_URL } from '../config';

async function unwrap(response) {
  if (response.ok) {
    return response;
  }
  let detail = `Request failed with status ${response.status}`;
  try {
    const body = await response.json();
    detail = body.detail || detail;
  } catch (error) {
    // A non-JSON error body is not worth reporting over the status code.
  }
  throw new Error(detail);
}

export async function fetchTransforms() {
  const response = await unwrap(await fetch(`${API_BASE_URL}/api/transforms`));
  return response.json();
}

export async function suggestMapping(inputFile, targetFile) {
  const form = new FormData();
  form.append('input_table', inputFile);
  form.append('target_table', targetFile);
  const response = await unwrap(
    await fetch(`${API_BASE_URL}/api/mappings/suggest`, {
      method: 'POST',
      body: form,
    })
  );
  return response.json();
}

function planForm(inputFile, mappings) {
  const form = new FormData();
  form.append('input_table', inputFile);
  form.append('plan', JSON.stringify({ mappings }));
  return form;
}

export async function applyMapping(inputFile, mappings, limit = 25) {
  const response = await unwrap(
    await fetch(`${API_BASE_URL}/api/mappings/apply?limit=${limit}`, {
      method: 'POST',
      body: planForm(inputFile, mappings),
    })
  );
  return response.json();
}

export async function downloadMapped(inputFile, mappings) {
  const response = await unwrap(
    await fetch(`${API_BASE_URL}/api/mappings/apply?download=true`, {
      method: 'POST',
      body: planForm(inputFile, mappings),
    })
  );
  return response.blob();
}
