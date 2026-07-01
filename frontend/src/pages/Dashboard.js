import React from 'react';
import { PropertyListPage } from './PropertyListPage';

export const Dashboard = () => {
  return <PropertyListPage status="available" testid="dashboard-page" />;
};

export const SoldProperties = () => {
  return <PropertyListPage status="sold" testid="sold-properties-page" />;
};

export const RentedProperties = () => {
  return <PropertyListPage status="rented" testid="rented-properties-page" />;
};
