import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { CreditCard, Calendar, CheckCircle, ArrowRight, Star, Crown, Gem, MessageCircle } from 'lucide-react';
import { BottomNav } from '../components/BottomNav';
import { SubscriptionBanner } from '../components/SubscriptionBanner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const WHATSAPP_BASE = 'https://wa.me/7760307768';

const PLAN_ICONS = {
  monthly: Star,
  quarterly: Gem,
  yearly: Crown,
};

const PLAN_COLORS = {
  monthly: 'bg-blue-50 border-blue-300',
  quarterly: 'bg-purple-50 border-purple-300',
  yearly: 'bg-amber-50 border-amber-400',
};

const buildWhatsAppUrl = (planLabel) => {
  const message = `اود بتجديد الاشتراك باقة ${planLabel}`;
  return `${WHATSAPP_BASE}?text=${encodeURIComponent(message)}`;
};

export const Subscriptions = () => {
  const navigate = useNavigate();
  const [plans, setPlans] = useState([]);
  const [mySubs, setMySubs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [plansRes, subsRes] = await Promise.all([
          axios.get(`${API}/subscriptions/plans`, { withCredentials: true }),
          axios.get(`${API}/subscriptions/me`, { withCredentials: true }),
        ]);
        setPlans(plansRes.data);
        setMySubs(subsRes.data);
      } catch (err) {
        setError(err.response?.data?.detail || 'تعذر تحميل البيانات');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const formatDate = (iso) => {
    const d = new Date(iso);
    return d.toLocaleDateString('ar-EG', { year: 'numeric', month: 'long', day: 'numeric' });
  };

  const daysLeft = (iso) => {
    const d = new Date(iso);
    const now = new Date();
    return Math.ceil((d - now) / (1000 * 60 * 60 * 24));
  };

  const activeSub = mySubs.find((s) => s.status === 'active');

  const planLabelFor = (type) => {
    if (type === 'monthly') return 'شهري';
    if (type === 'quarterly') return 'ربع سنوي';
    if (type === 'yearly') return 'سنوي';
    if (type === 'trial') return 'تجربة مجانية';
    return type;
  };

  return (
    <div className="min-h-screen bg-[#F9F6F0] p-4 sm:p-8 pb-28 md:pb-8" dir="rtl" data-testid="subscriptions-page">
      <div className="max-w-5xl mx-auto">
        <SubscriptionBanner />

        {/* Header */}
        <div className="bg-white border-2 border-[#D2CFC9] rounded-3xl p-6 mb-6 flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-4">
            <CreditCard className="w-12 h-12 sm:w-16 sm:h-16 text-[#D95D39]" />
            <h1 className="text-3xl sm:text-4xl font-black text-[#0A1F13]">الاشتراكات</h1>
          </div>
          <button
            data-testid="subscriptions-back"
            onClick={() => navigate('/dashboard')}
            className="min-h-[56px] px-6 bg-transparent border-4 border-[#1A5632] text-[#1A5632] rounded-2xl flex items-center gap-3 hover:bg-[#1A5632] hover:text-white transition-colors text-xl font-black"
          >
            <ArrowRight className="w-7 h-7" />
            عودة
          </button>
        </div>

        {error && (
          <div className="mb-6 p-6 bg-red-50 border-2 border-red-500 rounded-2xl">
            <p className="text-xl font-bold text-red-700">{error}</p>
          </div>
        )}

        {/* Active Subscription Status */}
        {activeSub && (
          <div className="mb-8 bg-green-50 border-4 border-green-500 rounded-3xl p-6">
            <div className="flex items-center gap-4 mb-3">
              <CheckCircle className="w-12 h-12 text-green-600" />
              <h3 className="text-2xl sm:text-3xl font-black text-green-800">لديك اشتراك فعال</h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
              <div>
                <p className="text-lg font-bold text-[#2B4736]">تاريخ الانتهاء</p>
                <p className="text-xl font-black text-[#0A1F13]">{formatDate(activeSub.end_date)}</p>
              </div>
              <div>
                <p className="text-lg font-bold text-[#2B4736]">الأيام المتبقية</p>
                <p
                  className={`text-2xl font-black ${
                    daysLeft(activeSub.end_date) <= 7 ? 'text-red-700' : 'text-green-700'
                  }`}
                  data-testid="active-sub-days-left"
                >
                  {daysLeft(activeSub.end_date)} يوم
                </p>
              </div>
              <div>
                <p className="text-lg font-bold text-[#2B4736]">الباقة</p>
                <p className="text-xl font-black text-[#0A1F13]">{planLabelFor(activeSub.plan_type)}</p>
              </div>
            </div>
          </div>
        )}

        {/* Plans - contact via WhatsApp */}
        <h2 className="text-3xl sm:text-4xl font-black text-[#0A1F13] mb-2">اختر خطة الاشتراك</h2>
        <p className="text-lg sm:text-xl font-bold text-[#2B4736] mb-6">
          اضغط على الباقة المطلوبة وسنتواصل معك عبر واتساب
        </p>

        {loading ? (
          <p className="text-2xl font-bold text-[#2B4736]">جاري التحميل...</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
            {plans.map((plan) => {
              const Icon = PLAN_ICONS[plan.plan_type] || Star;
              const label = plan.label || planLabelFor(plan.plan_type);
              return (
                <a
                  key={plan.plan_type}
                  href={buildWhatsAppUrl(label)}
                  target="_blank"
                  rel="noopener noreferrer"
                  data-testid={`plan-${plan.plan_type}`}
                  className={`${PLAN_COLORS[plan.plan_type] || 'bg-white border-[#D2CFC9]'} border-4 rounded-3xl p-8 shadow-sm flex flex-col hover:shadow-lg hover:-translate-y-1 transition-all cursor-pointer`}
                >
                  <div className="flex items-center gap-3 mb-4">
                    <Icon className="w-12 h-12 text-[#D95D39]" />
                    <h3 className="text-2xl font-black text-[#0A1F13]">{label}</h3>
                  </div>
                  <div className="my-6 flex-1">
                    <p className="text-5xl font-black text-[#0A1F13]">
                      {plan.amount.toLocaleString('ar-EG')}
                    </p>
                    <p className="text-2xl font-bold text-[#2B4736] mt-1">دينار عراقي</p>
                  </div>
                  <div className="mb-6">
                    <div className="flex items-center gap-2 text-xl font-bold text-[#2B4736]">
                      <Calendar className="w-6 h-6" />
                      <span>{plan.days} يوم</span>
                    </div>
                  </div>
                  <div
                    data-testid={`plan-cta-${plan.plan_type}`}
                    className="w-full min-h-[64px] bg-[#25D366] text-white rounded-2xl flex items-center justify-center gap-3 hover:bg-[#128C7E] transition-colors shadow-[0_6px_0_#128C7E] text-xl font-black"
                  >
                    <MessageCircle className="w-7 h-7" />
                    اشترك عبر واتساب
                  </div>
                </a>
              );
            })}
          </div>
        )}

        {/* History */}
        <h2 className="text-3xl font-black text-[#0A1F13] mb-4">سجل الاشتراكات</h2>
        {mySubs.length === 0 ? (
          <div className="bg-white border-2 border-[#D2CFC9] rounded-3xl p-8 text-center">
            <p className="text-2xl font-bold text-[#2B4736]">لا توجد اشتراكات سابقة</p>
          </div>
        ) : (
          <div className="space-y-3" data-testid="subscriptions-history">
            {mySubs.map((sub) => (
              <div
                key={sub.id}
                className="bg-white border-2 border-[#D2CFC9] rounded-2xl p-5 flex items-center justify-between flex-wrap gap-3"
              >
                <div className="flex items-center gap-4">
                  <Calendar className="w-10 h-10 text-[#1A5632]" />
                  <div>
                    <p className="text-xl font-extrabold text-[#0A1F13]">{planLabelFor(sub.plan_type)}</p>
                    <p className="text-lg font-bold text-[#6B7A70]">
                      من {formatDate(sub.start_date)} إلى {formatDate(sub.end_date)}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-xl font-black text-[#0A1F13]">
                    {sub.amount.toLocaleString('ar-EG')} د.ع
                  </span>
                  <span
                    className={`px-4 py-2 rounded-xl text-lg font-bold ${
                      sub.status === 'active'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-gray-200 text-gray-700'
                    }`}
                  >
                    {sub.status === 'active' ? 'فعال' : 'منتهي'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      <BottomNav />
    </div>
  );
};
