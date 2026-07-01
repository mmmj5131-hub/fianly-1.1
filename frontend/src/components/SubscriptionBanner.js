import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { AlertTriangle, XCircle, MessageCircle, X } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const WHATSAPP_BASE = 'https://wa.me/7760307768';
const NUDGE_SESSION_KEY = 'sub_nudge_shown_v1';

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

// Auto-nudge modal: shows once per session when days_remaining <= 3 (and still active)
export const SubscriptionNudgeModal = () => {
  const { user } = useAuth();
  const { status } = useSubscriptionStatus();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!user || user.role === 'admin' || !status) return;
    if (typeof window === 'undefined') return;
    const alreadyShown = sessionStorage.getItem(NUDGE_SESSION_KEY);
    if (alreadyShown) return;
    // Trigger on 3 days or less remaining (excluding fully expired handled by red banner)
    if (
      status.has_active &&
      status.days_remaining !== null &&
      status.days_remaining <= 3
    ) {
      setOpen(true);
      sessionStorage.setItem(NUDGE_SESSION_KEY, '1');
    }
  }, [user, status]);

  if (!open || !status) return null;

  const whatsappUrl = `${WHATSAPP_BASE}?text=${encodeURIComponent(
    'اود بتجديد الاشتراك'
  )}`;

  return (
    <div
      data-testid="subscription-nudge-modal"
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      dir="rtl"
      onClick={() => setOpen(false)}
    >
      <div
        className="bg-white rounded-3xl max-w-md w-full p-6 sm:p-8 border-4 border-yellow-500 shadow-2xl relative"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          data-testid="subscription-nudge-close"
          onClick={() => setOpen(false)}
          className="absolute top-3 left-3 w-10 h-10 rounded-full bg-[#F9F6F0] hover:bg-[#E8E4DC] flex items-center justify-center transition-colors"
          aria-label="إغلاق"
        >
          <X className="w-6 h-6 text-[#0A1F13]" />
        </button>
        <div className="flex flex-col items-center text-center gap-4">
          <div className="w-20 h-20 rounded-full bg-yellow-100 flex items-center justify-center">
            <AlertTriangle className="w-12 h-12 text-yellow-600" />
          </div>
          <h2 className="text-2xl sm:text-3xl font-black text-[#0A1F13]">
            اشتراكك على وشك الانتهاء
          </h2>
          <p className="text-lg sm:text-xl font-bold text-[#2B4736]">
            يتبقى{' '}
            <span
              className="text-3xl font-black text-red-700"
              data-testid="nudge-days-remaining"
            >
              {status.days_remaining}
            </span>{' '}
            {status.days_remaining === 1 ? 'يوم فقط' : 'أيام فقط'} على انتهاء اشتراكك.
            <br />
            جدّد الآن لتفادي انقطاع الخدمة.
          </p>
          <a
            data-testid="subscription-nudge-cta"
            href={whatsappUrl}
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => setOpen(false)}
            className="w-full min-h-[60px] bg-[#25D366] text-white rounded-2xl flex items-center justify-center gap-3 hover:bg-[#128C7E] transition-colors text-xl font-black shadow-md"
          >
            <MessageCircle className="w-7 h-7" />
            جدّد عبر واتساب
          </a>
          <button
            onClick={() => setOpen(false)}
            className="text-base font-bold text-[#6B7A70] hover:text-[#0A1F13] underline"
          >
            تذكيري لاحقاً
          </button>
        </div>
      </div>
    </div>
  );
};
