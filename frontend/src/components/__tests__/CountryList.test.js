import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import CountryList from '../CountryList';
import * as api from '../../services/api';

jest.mock('../../services/api');

describe('CountryList', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  const mockCountries = [
    {
      id: 1,
      name: 'Testland',
      iso_code: 'TST',
      tier: 'mixed_rural_urban',
      estimated_population: 1000000,
      area_sq_km: 50000,
      num_regions: 5,
      num_districts: 20,
      locked: false,
    },
  ];

  test('renders countries and delete button', async () => {
    api.listCountries.mockResolvedValue({ data: mockCountries });

    render(<CountryList onSelect={jest.fn()} onCountryDeleted={jest.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Testland')).toBeInTheDocument();
    });

    expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument();
  });

  test('calls deleteCountry and refreshes when delete is confirmed', async () => {
    window.confirm = jest.fn(() => true);
    api.listCountries
      .mockResolvedValueOnce({ data: mockCountries })
      .mockResolvedValueOnce({ data: [] });
    api.deleteCountry.mockResolvedValue({ status: 204 });

    const onCountryDeleted = jest.fn();
    render(<CountryList onSelect={jest.fn()} onCountryDeleted={onCountryDeleted} />);

    await waitFor(() => {
      expect(screen.getByText('Testland')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /delete/i }));

    await waitFor(() => {
      expect(api.deleteCountry).toHaveBeenCalledWith(1);
    });

    expect(onCountryDeleted).toHaveBeenCalled();
  });

  test('does not delete when confirmation is cancelled', async () => {
    window.confirm = jest.fn(() => false);
    api.listCountries.mockResolvedValue({ data: mockCountries });

    render(<CountryList onSelect={jest.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Testland')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /delete/i }));

    expect(api.deleteCountry).not.toHaveBeenCalled();
  });
});
