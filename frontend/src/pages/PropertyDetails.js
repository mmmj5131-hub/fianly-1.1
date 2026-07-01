import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';
import { PROPERTY } from '../constants/testIds';
import {
  Building2,
  DollarSign,
  Bed,
  Bath,
  MapPin,
  Ruler,
  Phone,
  User,
  ArrowRight,
  Edit,
  Trash2,
  AlertCircle,
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const PropertyDetails = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [property, setProperty] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [deleting, setDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [currentImageIdx, setCurrentImageIdx] = useState(0);

  useEffect(() => {
    const fetchProperty = async () => {
      try {
        const { data } = await axios.get(`${API}/properties/${id}`, { withCredentials: true });
        setProperty(data);
      } catch (err) {
        setError(err.response?.data?.detail || 'تعذر تحميل تفاصيل العقار');
      } finally {
        setLoading(false);
      }
    };
    fetchProperty();
  }, [id]);

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await axios.delete(`${API}/properties/${id}`, { withCredentials: true });
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'تعذر حذف العقار');
      setDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  const canEditOrDelete =
    user && property && (user.role === 'admin' || user.id === property.agent_id);

  const statusLabel = {
    available: 'متاح',
    sold: 'مباع',
    rented: 'مؤجر',
  };
  const statusColor = {
    available: 'bg-green-100 text-green-800',
    sold: 'bg-red-100 text-red-800',
    rented: 'bg-yellow-100 text-yellow-800',
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F9F6F0] flex items-center justify-center" dir="rtl">
        <div className="text-center">
          <div className="w-20 h-20 border-8 border-[#1A5632] border-t-transparent rounded-full animate-spin mx-auto mb-6"></div>
          <p className="text-3xl font-bold text-[#2B4736]">جاري التحميل...</p>
        </div>
      </div>
    );
  }

  if (error || !property) {
    return (
      <div className="min-h-screen bg-[#F9F6F0] p-4 sm:p-8" dir="rtl">
        <div className="max-w-2xl mx-auto bg-white border-2 border-red-300 rounded-3xl p-12 text-center">
          <AlertCircle className="w-24 h-24 text-red-500 mx-auto mb-6" />
          <p className="text-3xl font-extrabold text-red-700 mb-6">
            {error || 'العقار غير موجود'}
          </p>
          <button
            onClick={() => navigate('/dashboard')}
            className="min-h-[64px] px-8 bg-[#1A5632] text-white rounded-2xl text-xl font-black hover:bg-[#0F3820]"
          >
            العودة للوحة الرئيسية
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      className="min-h-screen bg-[#F9F6F0] p-4 sm:p-8"
      dir="rtl"
      data-testid="property-details-page"
    >
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="bg-white border-2 border-[#D2CFC9] rounded-3xl p-6 mb-6 flex items-center justify-between gap-4 flex-wrap">
          <button
            data-testid="property-back-button"
            onClick={() => navigate('/dashboard')}
            className="min-h-[64px] px-8 bg-transparent border-4 border-[#1A5632] text-[#1A5632] rounded-2xl flex items-center gap-3 hover:bg-[#1A5632] hover:text-white transition-colors text-xl font-black"
          >
            <ArrowRight className="w-8 h-8" />
            عودة
          </button>
          {canEditOrDelete && (
            <div className="flex gap-3">
              <button
                data-testid={PROPERTY.editButton}
                onClick={() => navigate(`/edit-property/${id}`)}
                className="min-h-[64px] px-8 bg-[#D95D39] text-white rounded-2xl flex items-center gap-3 hover:bg-[#B84A2A] transition-colors text-xl font-black"
              >
                <Edit className="w-8 h-8" />
                تعديل
              </button>
              <button
                data-testid={PROPERTY.deleteButton}
                onClick={() => setShowDeleteConfirm(true)}
                className="min-h-[64px] px-8 bg-red-600 text-white rounded-2xl flex items-center gap-3 hover:bg-red-700 transition-colors text-xl font-black"
              >
                <Trash2 className="w-8 h-8" />
                حذف
              </button>
            </div>
          )}
        </div>

        {/* Images Gallery */}
        <div className="bg-white border-2 border-[#D2CFC9] rounded-3xl overflow-hidden mb-6">
          {property.images && property.images.length > 0 ? (
            <>
              <img
                src={property.images[currentImageIdx]}
                alt="عقار"
                className="w-full h-96 object-cover"
                data-testid="property-main-image"
              />
              {property.images.length > 1 && (
                <div className="p-4 flex gap-3 overflow-x-auto">
                  {property.images.map((img, idx) => (
                    <img
                      key={idx}
                      src={img}
                      alt={`صورة ${idx + 1}`}
                      onClick={() => setCurrentImageIdx(idx)}
                      className={`w-24 h-24 object-cover rounded-xl cursor-pointer flex-shrink-0 border-4 ${
                        currentImageIdx === idx ? 'border-[#1A5632]' : 'border-transparent'
                      }`}
                    />
                  ))}
                </div>
              )}
            </>
          ) : (
            <div className="w-full h-96 bg-[#F9F6F0] flex items-center justify-center">
              <Building2 className="w-32 h-32 text-[#6B7A70]" />
            </div>
          )}
        </div>

        {/* Main Info */}
        <div className="bg-white border-2 border-[#D2CFC9] rounded-3xl p-8 mb-6">
          <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
            <div className="flex items-center gap-3">
              <DollarSign className="w-12 h-12 text-[#1A5632]" />
              <span
                className="text-5xl font-black text-[#0A1F13]"
                data-testid="property-detail-price"
              >
                {property.price.toLocaleString('ar-EG')} د.ع
              </span>
            </div>
            <span
              className={`inline-block px-6 py-3 rounded-2xl text-2xl font-extrabold ${statusColor[property.status]}`}
              data-testid="property-detail-status"
            >
              {statusLabel[property.status]}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-[#F9F6F0] rounded-2xl p-6 border-2 border-[#D2CFC9]">
              <div className="flex items-center gap-3 mb-2">
                <MapPin className="w-10 h-10 text-[#1A5632]" />
                <span className="text-2xl font-bold text-[#2B4736]">المحافظة</span>
              </div>
              <p
                className="text-3xl font-black text-[#0A1F13]"
                data-testid="property-detail-governorate"
              >
                {property.governorate || 'غير محدد'}
              </p>
            </div>

            <div className="bg-[#F9F6F0] rounded-2xl p-6 border-2 border-[#D2CFC9]">
              <div className="flex items-center gap-3 mb-2">
                <MapPin className="w-10 h-10 text-[#1A5632]" />
                <span className="text-2xl font-bold text-[#2B4736]">القضاء</span>
              </div>
              <p
                className="text-3xl font-black text-[#0A1F13]"
                data-testid="property-detail-district"
              >
                {property.district || 'غير محدد'}
              </p>
            </div>

            <div className="bg-[#F9F6F0] rounded-2xl p-6 border-2 border-[#D2CFC9]">
              <div className="flex items-center gap-3 mb-2">
                <MapPin className="w-10 h-10 text-[#1A5632]" />
                <span className="text-2xl font-bold text-[#2B4736]">المساحة الكلية</span>
              </div>
              <p
                className="text-3xl font-black text-[#0A1F13]"
                data-testid="property-detail-total-area"
              >
                {property.total_area} متر مربع
              </p>
            </div>

            <div className="bg-[#F9F6F0] rounded-2xl p-6 border-2 border-[#D2CFC9]">
              <div className="flex items-center gap-3 mb-2">
                <Ruler className="w-10 h-10 text-[#1A5632]" />
                <span className="text-2xl font-bold text-[#2B4736]">مساحة الواجهة</span>
              </div>
              <p className="text-3xl font-black text-[#0A1F13]">{property.front_width} متر</p>
            </div>

            <div className="bg-[#F9F6F0] rounded-2xl p-6 border-2 border-[#D2CFC9]">
              <div className="flex items-center gap-3 mb-2">
                <Ruler className="w-10 h-10 text-[#1A5632]" />
                <span className="text-2xl font-bold text-[#2B4736]">الطول</span>
              </div>
              <p className="text-3xl font-black text-[#0A1F13]">{property.length} متر</p>
            </div>

            <div className="bg-[#F9F6F0] rounded-2xl p-6 border-2 border-[#D2CFC9]">
              <div className="flex items-center gap-3 mb-2">
                <Bed className="w-10 h-10 text-[#1A5632]" />
                <span className="text-2xl font-bold text-[#2B4736]">عدد الغرف</span>
              </div>
              <p
                className="text-3xl font-black text-[#0A1F13]"
                data-testid="property-detail-bedrooms"
              >
                {property.bedrooms}
              </p>
            </div>

            <div className="bg-[#F9F6F0] rounded-2xl p-6 border-2 border-[#D2CFC9]">
              <div className="flex items-center gap-3 mb-2">
                <Bath className="w-10 h-10 text-[#1A5632]" />
                <span className="text-2xl font-bold text-[#2B4736]">عدد الحمامات</span>
              </div>
              <p
                className="text-3xl font-black text-[#0A1F13]"
                data-testid="property-detail-bathrooms"
              >
                {property.bathrooms}
              </p>
            </div>

            <div className="bg-[#F9F6F0] rounded-2xl p-6 border-2 border-[#D2CFC9]">
              <div className="flex items-center gap-3 mb-2">
                <User className="w-10 h-10 text-[#1A5632]" />
                <span className="text-2xl font-bold text-[#2B4736]">اسم مالك العقار</span>
              </div>
              <p
                className="text-3xl font-black text-[#0A1F13]"
                data-testid="property-detail-owner-name"
              >
                {property.owner_name || 'غير محدد'}
              </p>
            </div>

            <div className="bg-[#F9F6F0] rounded-2xl p-6 border-2 border-[#D2CFC9]">
              <div className="flex items-center gap-3 mb-2">
                <Phone className="w-10 h-10 text-[#1A5632]" />
                <span className="text-2xl font-bold text-[#2B4736]">رقم المالك</span>
              </div>
              <a
                href={`tel:${property.owner_phone}`}
                className="text-3xl font-black text-[#1A5632] hover:underline"
                data-testid="property-detail-owner-phone"
                dir="ltr"
              >
                {property.owner_phone}
              </a>
            </div>
          </div>
        </div>

        {/* Agent Info */}
        <div className="bg-white border-2 border-[#D2CFC9] rounded-3xl p-8">
          <div className="flex items-center gap-4">
            <User className="w-16 h-16 text-[#1A5632]" />
            <div>
              <p className="text-xl font-bold text-[#6B7A70] mb-1">مُدخل العقار</p>
              <p
                className="text-3xl font-extrabold text-[#0A1F13]"
                data-testid="property-detail-agent-name"
              >
                {property.agent_name}
              </p>
            </div>
          </div>
        </div>

        {/* Delete Confirmation Modal */}
        {showDeleteConfirm && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-3xl p-8 max-w-lg w-full border-4 border-red-300">
              <div className="text-center mb-6">
                <AlertCircle className="w-20 h-20 text-red-500 mx-auto mb-4" />
                <h3 className="text-3xl font-extrabold text-[#0A1F13] mb-3">تأكيد الحذف</h3>
                <p className="text-xl font-bold text-[#2B4736]">
                  هل أنت متأكد من حذف هذا العقار؟ لا يمكن التراجع.
                </p>
              </div>
              <div className="flex gap-4">
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  disabled={deleting}
                  data-testid="property-delete-cancel"
                  className="flex-1 min-h-[64px] bg-transparent border-4 border-[#1A5632] text-[#1A5632] rounded-2xl text-xl font-black hover:bg-[#1A5632] hover:text-white transition-colors"
                >
                  إلغاء
                </button>
                <button
                  onClick={handleDelete}
                  disabled={deleting}
                  data-testid="property-delete-confirm"
                  className="flex-1 min-h-[64px] bg-red-600 text-white rounded-2xl text-xl font-black hover:bg-red-700 transition-colors disabled:opacity-50"
                >
                  {deleting ? 'جاري الحذف...' : 'تأكيد الحذف'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
