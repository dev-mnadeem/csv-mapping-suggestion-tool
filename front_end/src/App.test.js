import React from 'react';
import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App';

const TRANSFORMS = [
  { name: 'identity', description: 'Copy the value unchanged', options: [] },
  { name: 'to_integer', description: 'Parse a number', options: [] },
];

const SUGGESTION = {
  run_id: 1,
  suggester: 'local',
  duration_ms: 2,
  source: {
    filename: 'employee_policies.csv',
    encoding: 'utf-8-sig',
    delimiter: ',',
    row_count: 12,
    truncated: false,
    columns: [
      {
        name: 'Monthly_Premium',
        index: 0,
        inferred_type: 'decimal',
        row_count: 12,
        non_empty_count: 12,
        distinct_count: 3,
        sample_values: ['100.0'],
      },
    ],
  },
  target: {
    filename: 'target_schema.csv',
    encoding: 'utf-8-sig',
    delimiter: ',',
    row_count: 3,
    truncated: false,
    columns: [
      {
        name: 'Premium',
        index: 0,
        inferred_type: 'integer',
        row_count: 3,
        non_empty_count: 3,
        distinct_count: 3,
        sample_values: ['100'],
      },
    ],
  },
  suggestions: [
    {
      target_column: 'Premium',
      best: {
        source_column: 'Monthly_Premium',
        confidence: 0.65,
        rationale: "column names share most of their words, values need 'to_integer'",
        transform: 'to_integer',
        transform_options: {},
        signals: {},
      },
      alternatives: [],
    },
  ],
  warnings: [],
};

function jsonResponse(body) {
  return Promise.resolve({ ok: true, json: () => Promise.resolve(body) });
}

beforeEach(() => {
  global.fetch = jest.fn((url) => {
    if (String(url).includes('/api/transforms')) {
      return jsonResponse(TRANSFORMS);
    }
    return jsonResponse(SUGGESTION);
  });
});

afterEach(() => {
  jest.resetAllMocks();
});

function csvFile(name) {
  return new File(['a,b\n1,2\n'], name, { type: 'text/csv' });
}

async function renderApp() {
  await act(async () => {
    render(<App />);
  });
}

test('the suggest button stays disabled until both files are chosen', async () => {
  await renderApp();
  const button = screen.getByRole('button', { name: /suggest mapping/i });
  expect(button).toBeDisabled();

  await userEvent.upload(screen.getByTestId('input-file'), csvFile('source.csv'));
  expect(button).toBeDisabled();

  await userEvent.upload(screen.getByTestId('target-file'), csvFile('target.csv'));
  await waitFor(() => expect(button).toBeEnabled());
});

test('the suggested mapping is shown with its column names and confidence', async () => {
  await renderApp();
  await userEvent.upload(screen.getByTestId('input-file'), csvFile('source.csv'));
  await userEvent.upload(screen.getByTestId('target-file'), csvFile('target.csv'));
  await userEvent.click(screen.getByRole('button', { name: /suggest mapping/i }));

  expect(await screen.findByText('Premium')).toBeInTheDocument();
  expect(screen.getByText('65%')).toBeInTheDocument();
  expect(screen.getByText(/1 of 1 target columns matched/i)).toBeInTheDocument();
  expect(
    screen.getByRole('combobox', { name: /source for Premium/i })
  ).toHaveTextContent('Monthly_Premium');
});

test('an unreachable API is reported instead of failing silently', async () => {
  global.fetch = jest.fn(() => Promise.reject(new Error('offline')));
  await renderApp();
  expect(await screen.findByText(/API is not reachable/i)).toBeInTheDocument();
});
