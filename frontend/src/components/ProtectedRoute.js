import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F9F6F0]" dir="rtl">
        <div className="text-center">
          <div className="w-20 h-20 border-8 border-[#1A5632] border-t-transparent rounded-full animate-spin mx-auto mb-6"></div>
          <p className="text-3xl font-bold text-[#2B4736]">جاري التحميل...</p>
        </div>
      </div>
    );
  }

  if (!user || user === false) {
    return <Navigate to="/auth" replace />;
  }

  return children;
};
