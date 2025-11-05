import React from 'react';
import { render, screen } from '@testing-library/react';
import Login from './components/Login'
import AuthContext from './components/AuthContext'

test('renders learn react link', () => {
  render(<Login />);
  render(<AuthContext/>);
  const linkElement = screen.getByText(/learn react/i);
  expect(linkElement).toBeInTheDocument();
});
