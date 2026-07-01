import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';
import { PROPERTY, SEARCH, AUTH } from '../constants/testIds';
import {
  Plus,
  Search,
  Building2,
  DollarSign,
  Bed,
  Bath,
  MapPin,
  LogOut,
  Shield,
  CreditCard,
  CheckCircle,
  Key,
  Home as HomeIcon,
  Menu,
  X,
  User,
} from 'lucide-react';
import { BottomNav } from '../components/BottomNav';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STATUS_CONFIG = {
  available: { label: 'العقارات المتاحة', icon: HomeIcon, color: 'text-green-700', bg: 'bg-green-100' },
  sold: { label: 'العقارات المباعة', icon: CheckCircle, color: 'text-red-700', bg: 'bg-red-100' },
  rented: { label: 'العقارات المؤجرة', icon: Key, color: 'text-yellow-700', bg: 'bg-yellow-100' },
};

export const PropertyListPage = ({ status, testid }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [properties, setProperties] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [menuOpen, setMenuOpen] = useState(false);

  const config = STATUS_CONFIG[status];
  const StatusIcon = config.icon;

  useEffect(() => {
    const fetchProperties = async () => {
      setLoading(true);
      try {
        const { data } = await axios.get(`${API}/properties?status=${status}`, {
          withCredentials: true,
        });
        setProperties(data);
      } catch (error) {
        console.error('Error fetching properties:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchProperties();
  }, [status]);

  const handleLogout = async () => {
    await logout();
    navigate('/auth');
  };

  const filteredProperties = properties.filter((prop) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      prop.total_area.toString().includes(query) ||
      prop.price.toString().includes(query) ||
      prop.bedrooms.toString().includes(query) ||
      (prop.owner_name && prop.owner_name.toLowerCase().includes(query)) ||
      prop.agent_name.toLowerCase().includes(query)
    );
  });

  const statusLabel = { available: 'متاح', sold: 'مباع', rented: 'مؤجر' };
  const statusColor = {
    available: 'bg-green-100 text-green-800',
    sold: 'bg-red-100 text-red-800',
    rented: 'bg-yellow-100 text-yellow-800',
  };

  return (
    <div className="min-h-screen bg-[#F9F6F0] p-4 sm:p-8 pb-28 md:pb-8" dir="rtl" data-testid={testid}>
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-6">
        <div className="bg-white border-2 border-[#D2CFC9] rounded-3xl p-4 sm:p-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3 sm:gap-4 w-full sm:w-auto">
            <Building2 className="w-12 h-12 sm:w-16 sm:h-16 text-[#1A5632] flex-shrink-0" />
            <div className="flex-1">
              <h1 className="text-2xl sm:text-4xl font-black text-[#0A1F13]">عقاري الميسر</h1>
              <p className="text-base sm:text-xl font-bold text-[#2B4736]">مرحباً {user?.name}</p>
            </div>
            {/* Mobile menu toggle */}
            <button
              data-testid="mobile-menu-toggle"
              onClick={() => setMenuOpen(!menuOpen)}
              className="md:hidden bg-[#1A5632] text-white p-3 rounded-2xl"
            >
              {menuOpen ? <X className="w-7 h-7" /> : <Menu className="w-7 h-7" />}
            </button>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex gap-3">
            <button
              data-testid="nav-subscriptions-desktop"
              onClick={() => navigate('/subscriptions')}
              className="min-h-[64px] px-6 bg-[#D95D39] text-white rounded-2xl flex items-center gap-2 hover:bg-[#B84A2A] transition-colors text-lg font-black"
            >
              <CreditCard className="w-7 h-7" />
              اشتراكاتي
            </button>
            {user?.role === 'admin' && (
              <button
                data-testid="nav-admin-desktop"
                onClick={() => navigate('/admin')}
                className="min-h-[64px] px-6 bg-[#1A5632] text-white rounded-2xl flex items-center gap-2 hover:bg-[#0F3820] transition-colors text-lg font-black"
              >
                <Shield className="w-7 h-7" />
                لوحة المدير
              </button>
            )}
            <button
              data-testid={AUTH.logoutButton}
              onClick={handleLogout}
              className="min-h-[64px] px-6 bg-transparent border-4 border-[#1A5632] text-[#1A5632] rounded-2xl flex items-center gap-2 hover:bg-[#1A5632] hover:text-white transition-colors text-lg font-black"
            >
              <LogOut className="w-7 h-7" />
              خروج
            </button>
          </div>

          {/* Mobile Menu Dropdown */}
          {menuOpen && (
            <div className="w-full md:hidden flex flex-col gap-2 pt-2 border-t-2 border-[#D2CFC9]">
              <button
                onClick={() => {
                  navigate('/subscriptions');
                  setMenuOpen(false);
                }}
                className="min-h-[56px] px-6 bg-[#D95D39] text-white rounded-2xl flex items-center justify-center gap-2 text-xl font-black"
              >
                <CreditCard className="w-6 h-6" />
                اشتراكاتي
              </button>
              {user?.role === 'admin' && (
                <button
                  onClick={() => {
                    navigate('/admin');
                    setMenuOpen(false);
                  }}
                  className="min-h-[56px] px-6 bg-[#1A5632] text-white rounded-2xl flex items-center justify-center gap-2 text-xl font-black"
                >
                  <Shield className="w-6 h-6" />
                  لوحة المدير
                </button>
              )}
              <button
                onClick={handleLogout}
                className="min-h-[56px] px-6 bg-transparent border-4 border-[#1A5632] text-[#1A5632] rounded-2xl flex items-center justify-center gap-2 text-xl font-black"
              >
                <LogOut className="w-6 h-6" />
                تسجيل خروج
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Status Filter Tabs (Desktop visible, mobile uses bottom nav) */}
      <div className="max-w-7xl mx-auto mb-6 hidden md:block">
        <div className="bg-white border-2 border-[#D2CFC9] rounded-3xl p-3 flex gap-2">
          <button
            data-testid="filter-available"
            onClick={() => navigate('/dashboard')}
            className={`flex-1 min-h-[60px] rounded-2xl flex items-center justify-center gap-3 text-xl font-black transition-colors ${
              status === 'available'
                ? 'bg-[#1A5632] text-white'
                : 'bg-transparent text-[#2B4736] hover:bg-[#F9F6F0]'
            }`}
          >
            <HomeIcon className="w-7 h-7" />
            المتاحة
          </button>
          <button
            data-testid="filter-sold"
            onClick={() => navigate('/sold')}
            className={`flex-1 min-h-[60px] rounded-2xl flex items-center justify-center gap-3 text-xl font-black transition-colors ${
              status === 'sold'
                ? 'bg-[#1A5632] text-white'
                : 'bg-transparent text-[#2B4736] hover:bg-[#F9F6F0]'
            }`}
          >
            <CheckCircle className="w-7 h-7" />
            المباعة
          </button>
          <button
            data-testid="filter-rented"
            onClick={() => navigate('/rented')}
            className={`flex-1 min-h-[60px] rounded-2xl flex items-center justify-center gap-3 text-xl font-black transition-colors ${
              status === 'rented'
                ? 'bg-[#1A5632] text-white'
                : 'bg-transparent text-[#2B4736] hover:bg-[#F9F6F0]'
            }`}
          >
            <Key className="w-7 h-7" />
            المؤجرة
          </button>
        </div>
      </div>

      {/* Page title */}
      <div className="max-w-7xl mx-auto mb-6">
        <div className={`${config.bg} border-2 border-[#D2CFC9] rounded-3xl p-5 flex items-center gap-4`}>
          <StatusIcon className={`w-12 h-12 ${config.color}`} />
          <h2 className={`text-3xl sm:text-4xl font-black ${config.color}`}>{config.label}</h2>
          <span className="mr-auto text-2xl font-black text-[#2B4736]">
            {filteredProperties.length}
          </span>
        </div>
      </div>

      {/* Search Bar */}
      <div className="max-w-7xl mx-auto mb-6">
        <div className="bg-white border-2 border-[#D2CFC9] rounded-3xl p-4 sm:p-6">
          <div className="flex items-center gap-3 sm:gap-4">
            <Search className="w-8 h-8 sm:w-10 sm:h-10 text-[#2B4736] flex-shrink-0" />
            <input
              data-testid={SEARCH.searchInput}
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="ابحث بالمساحة، السعر، اسم المالك..."
              className="flex-1 min-h-[56px] text-xl sm:text-2xl p-3 sm:p-4 border-2 border-[#D2CFC9] rounded-xl focus:border-[#1A5632] focus:ring-4 focus:ring-[#1A5632]/20 outline-none font-semibold"
            />
          </div>
        </div>
      </div>

      {/* Add Property Button */}
      {status === 'available' && (
        <div className="max-w-7xl mx-auto mb-8">
          <button
            data-testid={PROPERTY.addButton}
            onClick={() => navigate('/add-property')}
            className="w-full min-h-[72px] bg-[#1A5632] text-white rounded-2xl flex items-center justify-center gap-4 hover:bg-[#0F3820] transition-colors shadow-[0_8px_0_#0F3820] active:translate-y-2 active:shadow-[0_0px_0_#0F3820] text-2xl sm:text-3xl font-black"
          >
            <Plus className="w-10 h-10 sm:w-12 sm:h-12" />
            إضافة عقار جديد
          </button>
        </div>
      )}

      {/* Properties Grid */}
      <div className="max-w-7xl mx-auto" data-testid={SEARCH.resultsContainer}>
        {loading ? (
          <div className="text-center py-20">
            <p className="text-3xl font-bold text-[#2B4736]">جاري التحميل...</p>
          </div>
        ) : filteredProperties.length === 0 ? (
          <div className="bg-white border-2 border-[#D2CFC9] rounded-3xl p-12 text-center">
            <Building2 className="w-24 h-24 text-[#6B7A70] mx-auto mb-6" />
            <p className="text-3xl font-bold text-[#2B4736]">لا توجد عقارات في هذه الفئة</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredProperties.map((property) => (
              <div
                key={property.id}
                data-testid={PROPERTY.card}
                className="bg-white border-2 border-[#D2CFC9] rounded-3xl overflow-hidden hover:border-[#1A5632] transition-colors cursor-pointer"
                onClick={() => navigate(`/property/${property.id}`)}
              >
                {property.images && property.images.length > 0 ? (
                  <img src={property.images[0]} alt="عقار" className="w-full h-56 object-cover" />
                ) : (
                  <div className="w-full h-56 bg-[#F9F6F0] flex items-center justify-center">
                    <Building2 className="w-20 h-20 text-[#6B7A70]" />
                  </div>
                )}
                <div className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <DollarSign className="w-8 h-8 text-[#1A5632]" />
                      <span className="text-2xl font-black text-[#0A1F13]">
                        {property.price.toLocaleString('ar-EG')} د.ع
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 mb-3">
                    <MapPin className="w-6 h-6 text-[#2B4736]" />
                    <span className="text-xl font-bold text-[#2B4736]">
                      {property.total_area} متر مربع
                    </span>
                  </div>
                  <div className="flex items-center gap-6 mb-4">
                    <div className="flex items-center gap-2">
                      <Bed className="w-6 h-6 text-[#2B4736]" />
                      <span className="text-xl font-bold">{property.bedrooms}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Bath className="w-6 h-6 text-[#2B4736]" />
                      <span className="text-xl font-bold">{property.bathrooms}</span>
                    </div>
                  </div>
                  {property.owner_name && (
                    <div className="flex items-center gap-2 mb-3">
                      <User className="w-6 h-6 text-[#1A5632]" />
                      <span className="text-lg font-bold text-[#0A1F13]">
                        مالك العقار: {property.owner_name}
                      </span>
                    </div>
                  )}
                  <div className="mt-3">
                    <span
                      className={`inline-block px-4 py-2 rounded-xl text-lg font-bold ${statusColor[property.status]}`}
                    >
                      {statusLabel[property.status]}
                    </span>
                  </div>
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
