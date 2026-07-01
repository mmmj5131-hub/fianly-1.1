import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Home, CheckCircle, Key, Plus, CreditCard, Shield } from 'lucide-react';

export const BottomNav = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();

  const items = [
    { path: '/dashboard', label: 'متاح', icon: Home, testid: 'nav-available' },
    { path: '/sold', label: 'مباع', icon: CheckCircle, testid: 'nav-sold' },
    { path: '/rented', label: 'مؤجر', icon: Key, testid: 'nav-rented' },
    { path: '/add-property', label: 'إضافة', icon: Plus, testid: 'nav-add' },
    { path: '/subscriptions', label: 'اشتراك', icon: CreditCard, testid: 'nav-subscriptions' },
  ];

  if (user?.role === 'admin') {
    items.push({ path: '/admin', label: 'إدارة', icon: Shield, testid: 'nav-admin' });
  }

  const isActive = (path) => {
    if (path === '/dashboard') return location.pathname === '/dashboard';
    return location.pathname.startsWith(path);
  };

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 bg-white border-t-4 border-[#1A5632] shadow-[0_-4px_12px_rgba(0,0,0,0.08)] z-40 md:hidden"
      dir="rtl"
      data-testid="bottom-nav"
    >
      <div className="flex justify-around items-stretch">
        {items.map((item) => {
          const Icon = item.icon;
          const active = isActive(item.path);
          return (
            <button
              key={item.path}
              data-testid={item.testid}
              onClick={() => navigate(item.path)}
              className={`flex-1 min-h-[72px] flex flex-col items-center justify-center gap-1 py-2 px-1 transition-colors ${
                active ? 'text-[#1A5632] bg-[#F9F6F0]' : 'text-[#6B7A70]'
              }`}
            >
              <Icon className={`${active ? 'w-8 h-8' : 'w-7 h-7'}`} strokeWidth={active ? 2.5 : 2} />
              <span className={`text-sm font-extrabold ${active ? 'text-[#1A5632]' : 'text-[#2B4736]'}`}>
                {item.label}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};
