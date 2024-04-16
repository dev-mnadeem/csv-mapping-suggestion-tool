import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
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
      {
        name: 'Policy_No',
        index: 1,
        inferred_type: 'text',
        row_count: 12,
        non_empty_count: 12,
        distinct_count: 12,
        sample_values: ['AB-12345'],
      },
      {
        name: 'Department',
        index: 2,
        inferred_type: 'text',
        row_count: 12,
        non_empty_count: 12,
        distinct_count: 3,
        sample_values: ['Finance'],
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
      alternatives: [
        {
          source_column: 'Policy_No',
          confidence: 0.2,
          rationale: 'weak match on name and type (20% similar)',
          transform: 'identity',
          transform_options: {},
          signals: {},
        },
      ],
    },
  ],
  warnings: [],
};

const HEALTH = {
  status: 'ok',
  version: '1.0.0',
  suggester: 'local',
  llm_configured: false,
  max_upload_bytes: 5242880,
  max_rows: 50000,
};

function jsonResponse(body) {
  return Promise.resolve({ ok: true, json: () => Promise.resolve(body) });
}

beforeEach(() => {
  global.fetch = vi.fn((url) => {
    if (String(url).includes('/api/transforms')) {
      return jsonResponse(TRANSFORMS);
    }
    if (String(url).includes('/api/health')) {
      return jsonResponse(HEALTH);
    }
    return jsonResponse(SUGGESTION);
  });
});

afterEach(() => {
  vi.restoreAllMocks();
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
  global.fetch = vi.fn(() => Promise.reject(new Error('offline')));
  await renderApp();
  expect(await screen.findByText(/API is not reachable/i)).toBeInTheDocument();
  expect(screen.getByText('API offline')).toBeInTheDocument();
});

test('the header names the matcher the API is running', async () => {
  await renderApp();
  expect(await screen.findByText('local matcher · v1.0.0')).toBeInTheDocument();
});

test('step 2 explains itself before any file is chosen', async () => {
  await renderApp();
  expect(screen.getByText(/Choose both files and the suggested mapping appears here/)).toBeInTheDocument();
});

async function suggestFromTwoFiles() {
  await renderApp();
  await userEvent.upload(screen.getByTestId('input-file'), csvFile('source.csv'));
  await userEvent.upload(screen.getByTestId('target-file'), csvFile('target.csv'));
  await userEvent.click(screen.getByRole('button', { name: /suggest mapping/i }));
  await screen.findByRole('combobox', { name: /source for Premium/i });
}

async function pickSource(name) {
  await userEvent.click(screen.getByRole('combobox', { name: /source for Premium/i }));
  await userEvent.click(within(screen.getByRole('listbox')).getByRole('option', { name }));
}

test('choosing a scored alternative shows that pairing\'s own score and transform', async () => {
  await suggestFromTwoFiles();
  await pickSource('Policy_No');

  expect(screen.getByText('20%')).toBeInTheDocument();
  expect(screen.queryByText('65%')).not.toBeInTheDocument();
  expect(screen.getByRole('combobox', { name: /transform for Premium/i })).toHaveTextContent(
    'identity'
  );
});

test('choosing a column the matcher never scored is marked as not scored', async () => {
  await suggestFromTwoFiles();
  await pickSource('Department');

  expect(screen.getByText('not scored')).toBeInTheDocument();
  expect(screen.getByText('chosen by hand')).toBeInTheDocument();
});

test('replacing the source file drops the plan that was suggested for the old one', async () => {
  await suggestFromTwoFiles();
  await userEvent.upload(screen.getByTestId('input-file'), csvFile('other.csv'));

  expect(screen.queryByRole('combobox', { name: /source for Premium/i })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: /suggest mapping/i })).toBeEnabled();
});
