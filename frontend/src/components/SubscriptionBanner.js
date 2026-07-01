import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { AlertTriangle, XCircle, MessageCircle } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const WHATSAPP_BASE = 'https://wa.me/7760307768';

export const useSubscriptionStatus = () => {
  const { user } = useAuth();
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    if (!user) {
      setLoading(false);
      return;
    }
    axios
      .get(`${API}/subscriptions/status`, { withCredentials: true })
      .then((res) => {
        if (mounted) setStatus(res.data);
      })
      .catch(() => {})
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [user]);

  return { status, loading };
};

export const SubscriptionBanner = () => {
  const { user } = useAuth();
  const { status } = useSubscriptionStatus();

  // Admin never sees banners
  if (!user || user.role === 'admin' || !status) return null;

  const whatsappUrl = `${WHATSAPP_BASE}?text=${encodeURIComponent(
    'اود بتجديد الاشتراك'
  )}`;

  if (status.status === 'expired') {
    return (
      <div
        data-testid="subscription-banner-expired"
        className="w-full bg-red-100 border-4 border-red-600 rounded-2xl p-4 sm:p-5 mb-4 flex flex-col sm:flex-row items-center justify-between gap-3"
        dir="rtl"
      >
        <div className="flex items-center gap-3">
          <XCircle className="w-10 h-10 text-red-700 flex-shrink-0" />
          <p className="text-lg sm:text-xl font-black text-red-900">
            انتهى اشتراكك — تواصل معنا للتجديد
          </p>
        </div>
        <a
          data-testid="subscription-banner-cta"
          href={whatsappUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="min-h-[48px] px-6 bg-[#25D366] text-white rounded-2xl flex items-center gap-2 hover:bg-[#128C7E] transition-colors text-lg font-black shadow-md"
        >
          <MessageCircle className="w-6 h-6" />
          اشترك الآن
        </a>
      </div>
    );
  }

  if (status.status === 'warning') {
    return (
      <div
        data-testid="subscription-banner-warning"
        className="w-full bg-yellow-100 border-4 border-yellow-500 rounded-2xl p-4 sm:p-5 mb-4 flex flex-col sm:flex-row items-center justify-between gap-3"
        dir="rtl"
      >
        <div className="flex items-center gap-3">
          <AlertTriangle className="w-10 h-10 text-yellow-700 flex-shrink-0" />
          <p className="text-lg sm:text-xl font-black text-yellow-900">
            اشتراكك ينتهي خلال {status.days_remaining} أيام
          </p>
        </div>
        <a
          data-testid="subscription-banner-cta"
          href={whatsappUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="min-h-[48px] px-6 bg-[#25D366] text-white rounded-2xl flex items-center gap-2 hover:bg-[#128C7E] transition-colors text-lg font-black shadow-md"
        >
          <MessageCircle className="w-6 h-6" />
          جدّد الآن
        </a>
      </div>
    );
  }

  return null;
};
