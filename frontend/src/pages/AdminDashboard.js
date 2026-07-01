import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';
import { ADMIN } from '../constants/testIds';
import {
  Building2,
  Home,
  CheckCircle,
  Key,
  Briefcase,
  ArrowRight,
  AlertTriangle,
  CreditCard,
  Calendar,
} from 'lucide-react';
import { BottomNav } from '../components/BottomNav';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const AdminDashboard = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [offices, setOffices] = useState([]);
  const [expiringSubs, setExpiringSubs] = useState([]);
  const [allSubs, setAllSubs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user?.role !== 'admin') {
      navigate('/dashboard');
      return;
    }
    const fetchData = async () => {
      try {
        const [statsRes, officesRes, expiringRes, subsRes] = await Promise.all([
          axios.get(`${API}/admin/stats`, { withCredentials: true }),
          axios.get(`${API}/admin/offices`, { withCredentials: true }),
          axios.get(`${API}/admin/subscriptions/expiring`, { withCredentials: true }),
          axios.get(`${API}/admin/subscriptions`, { withCredentials: true }),
        ]);
        setStats(statsRes.data);
        setOffices(officesRes.data);
        setExpiringSubs(expiringRes.data);
        setAllSubs(subsRes.data);
      } catch (error) {
        console.error('Error fetching admin data:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [user, navigate]);

  const formatDate = (iso) => {
    const d = new Date(iso);
    return d.toLocaleDateString('ar-EG', { year: 'numeric', month: 'long', day: 'numeric' });
  };

  const daysLeft = (iso) => {
    const d = new Date(iso);
    const now = new Date();
    return Math.ceil((d - now) / (1000 * 60 * 60 * 24));
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F9F6F0] flex items-center justify-center" dir="rtl">
        <p className="text-3xl font-bold text-[#2B4736]">جاري التحميل...</p>
      </div>
    );
  }

  return (
    <div
      className="min-h-screen bg-[#F9F6F0] p-4 sm:p-8 pb-28 md:pb-8"
      dir="rtl"
      data-testid={ADMIN.dashboard}
    >
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <div className="bg-white border-2 border-[#D2CFC9] rounded-3xl p-6 flex items-center justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-3xl sm:text-5xl font-black text-[#0A1F13] mb-2">لوحة المدير</h1>
            <p className="text-xl sm:text-2xl font-bold text-[#2B4736]">مرحباً {user?.name}</p>
          </div>
          <button
            onClick={() => navigate('/dashboard')}
            className="min-h-[56px] px-6 bg-[#1A5632] text-white rounded-2xl flex items-center gap-3 hover:bg-[#0F3820] transition-colors text-lg sm:text-xl font-black"
          >
            <ArrowRight className="w-7 h-7" />
            عودة للوحة الرئيسية
          </button>
        </div>
      </div>

      {/* Expiring Subscriptions Alert */}
      {expiringSubs.length > 0 && (
        <div className="max-w-7xl mx-auto mb-8">
          <div className="bg-yellow-50 border-4 border-yellow-500 rounded-3xl p-6">
            <div className="flex items-center gap-4 mb-4">
              <AlertTriangle className="w-12 h-12 text-yellow-700" />
              <h3 className="text-2xl sm:text-3xl font-black text-yellow-900">
                اشتراكات تنتهي قريباً ({expiringSubs.length})
              </h3>
            </div>
            <div className="space-y-3" data-testid="expiring-subscriptions-list">
              {expiringSubs.map((sub) => (
                <div
                  key={sub.id}
                  className="bg-white border-2 border-yellow-300 rounded-2xl p-4 flex items-center justify-between flex-wrap gap-3"
                >
                  <div>
                    <p className="text-xl font-extrabold text-[#0A1F13]">
                      {sub.office_name || sub.user_name}
                    </p>
                    <p className="text-lg font-bold text-[#6B7A70]">{sub.user_name}</p>
                  </div>
                  <div className="text-left">
                    <p className="text-lg font-bold text-[#2B4736]">ينتهي في</p>
                    <p className="text-xl font-black text-yellow-800">
                      {formatDate(sub.end_date)}
                    </p>
                    <p className="text-base font-bold text-red-700">
                      {daysLeft(sub.end_date)} يوم متبقي
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Stats Grid - clickable */}
      <div className="max-w-7xl mx-auto mb-8">
        <h2 className="text-3xl sm:text-4xl font-extrabold text-[#0A1F13] mb-6">
          إحصائيات العقارات
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          <button
            data-testid={ADMIN.totalPropertiesCard}
            onClick={() => navigate('/dashboard')}
            className="bg-white border-2 border-[#D2CFC9] rounded-3xl p-8 shadow-sm text-right hover:border-[#1A5632] hover:shadow-lg transition-all cursor-pointer"
          >
            <div className="flex items-center justify-between mb-4">
              <Building2 className="w-12 h-12 text-[#1A5632]" />
              <span className="text-5xl font-black text-[#0A1F13]">
                {stats?.total_properties || 0}
              </span>
            </div>
            <h3 className="text-2xl font-bold text-[#2B4736]">إجمالي العقارات</h3>
          </button>

          <button
            data-testid={ADMIN.availableCard}
            onClick={() => navigate('/dashboard')}
            className="bg-white border-2 border-[#D2CFC9] rounded-3xl p-8 shadow-sm text-right hover:border-green-600 hover:shadow-lg transition-all cursor-pointer"
          >
            <div className="flex items-center justify-between mb-4">
              <Home className="w-12 h-12 text-green-600" />
              <span className="text-5xl font-black text-green-600">{stats?.available || 0}</span>
            </div>
            <h3 className="text-2xl font-bold text-[#2B4736]">عقارات متاحة</h3>
          </button>

          <button
            data-testid={ADMIN.soldCard}
            onClick={() => navigate('/sold')}
            className="bg-white border-2 border-[#D2CFC9] rounded-3xl p-8 shadow-sm text-right hover:border-red-600 hover:shadow-lg transition-all cursor-pointer"
          >
            <div className="flex items-center justify-between mb-4">
              <CheckCircle className="w-12 h-12 text-red-600" />
              <span className="text-5xl font-black text-red-600">{stats?.sold || 0}</span>
            </div>
            <h3 className="text-2xl font-bold text-[#2B4736]">عقارات مباعة</h3>
          </button>

          <button
            data-testid={ADMIN.rentedCard}
            onClick={() => navigate('/rented')}
            className="bg-white border-2 border-[#D2CFC9] rounded-3xl p-8 shadow-sm text-right hover:border-yellow-600 hover:shadow-lg transition-all cursor-pointer"
          >
            <div className="flex items-center justify-between mb-4">
              <Key className="w-12 h-12 text-yellow-600" />
              <span className="text-5xl font-black text-yellow-600">{stats?.rented || 0}</span>
            </div>
            <h3 className="text-2xl font-bold text-[#2B4736]">عقارات مؤجرة</h3>
          </button>

          <div
            data-testid={ADMIN.officesCard}
            className="bg-white border-2 border-[#D2CFC9] rounded-3xl p-8 shadow-sm"
          >
            <div className="flex items-center justify-between mb-4">
              <Briefcase className="w-12 h-12 text-[#D95D39]" />
              <span className="text-5xl font-black text-[#D95D39]">{stats?.total_offices || 0}</span>
            </div>
            <h3 className="text-2xl font-bold text-[#2B4736]">عدد المكاتب</h3>
          </div>

          <div
            data-testid="admin-expiring-soon-card"
            className="bg-white border-2 border-[#D2CFC9] rounded-3xl p-8 shadow-sm"
          >
            <div className="flex items-center justify-between mb-4">
              <AlertTriangle className="w-12 h-12 text-yellow-600" />
              <span className="text-5xl font-black text-yellow-700">
                {stats?.expiring_soon || 0}
              </span>
            </div>
            <h3 className="text-2xl font-bold text-[#2B4736]">اشتراكات تنتهي قريباً</h3>
          </div>
        </div>
      </div>

      {/* All Subscriptions */}
      <div className="max-w-7xl mx-auto mb-8">
        <h2 className="text-3xl sm:text-4xl font-extrabold text-[#0A1F13] mb-6 flex items-center gap-3">
          <CreditCard className="w-10 h-10 text-[#D95D39]" />
          جميع الاشتراكات ({allSubs.length})
        </h2>
        {allSubs.length === 0 ? (
          <div className="bg-white border-2 border-[#D2CFC9] rounded-3xl p-12 text-center">
            <p className="text-2xl font-bold text-[#2B4736]">لا توجد اشتراكات</p>
          </div>
        ) : (
          <div className="space-y-3" data-testid="admin-all-subscriptions">
            {allSubs.slice(0, 10).map((sub) => (
              <div
                key={sub.id}
                className="bg-white border-2 border-[#D2CFC9] rounded-2xl p-5 flex items-center justify-between flex-wrap gap-3"
              >
                <div className="flex items-center gap-3">
                  <Calendar className="w-10 h-10 text-[#1A5632]" />
                  <div>
                    <p className="text-xl font-extrabold text-[#0A1F13]">{sub.user_name}</p>
                    <p className="text-base font-bold text-[#6B7A70]">
                      {sub.office_name || 'بدون مكتب'} •{' '}
                      {sub.plan_type === 'monthly'
                        ? 'شهري'
                        : sub.plan_type === 'quarterly'
                        ? 'ثلاثة أشهر'
                        : 'سنوي'}
                    </p>
                  </div>
                </div>
                <div className="text-left">
                  <p className="text-lg font-black text-[#0A1F13]">
                    {sub.amount.toLocaleString('ar-EG')} د.ع
                  </p>
                  <span
                    className={`inline-block px-3 py-1 rounded-xl text-base font-bold ${
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

      {/* Offices */}
      <div className="max-w-7xl mx-auto">
        <h2 className="text-3xl sm:text-4xl font-extrabold text-[#0A1F13] mb-6">
          قائمة المكاتب العقارية
        </h2>
        {offices.length === 0 ? (
          <div className="bg-white border-2 border-[#D2CFC9] rounded-3xl p-12 text-center">
            <Briefcase className="w-24 h-24 text-[#6B7A70] mx-auto mb-6" />
            <p className="text-2xl sm:text-3xl font-bold text-[#2B4736]">لا توجد مكاتب مسجلة</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {offices.map((office, idx) => (
              <div
                key={idx}
                className="bg-white border-2 border-[#D2CFC9] rounded-3xl p-8 shadow-sm"
              >
                <div className="flex items-center gap-4 mb-4">
                  <Briefcase className="w-10 h-10 text-[#1A5632]" />
                  <h3 className="text-2xl sm:text-3xl font-extrabold text-[#0A1F13]">
                    {office.office_name}
                  </h3>
                </div>
                <p className="text-xl font-bold text-[#2B4736] mb-3">
                  عدد الموظفين: {office.agent_count}
                </p>
                <div className="pt-3 border-t-2 border-[#D2CFC9]">
                  <p className="text-base font-semibold text-[#6B7A70] mb-2">
                    قائمة الموظفين:
                  </p>
                  <ul className="space-y-1">
                    {office.agents.map((agent, agentIdx) => (
                      <li key={agentIdx} className="text-lg font-semibold text-[#2B4736]">
                        • {agent.name}
                      </li>
                    ))}
                  </ul>
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
