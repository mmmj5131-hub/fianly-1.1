import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';
import { PROPERTY } from '../constants/testIds';
import { ChevronLeft, ChevronRight, Home, DollarSign, Ruler, BedDouble, Upload, Phone, User } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STEPS = [
  { title: 'المعلومات الأساسية', icon: Home },
  { title: 'الأبعاد', icon: Ruler },
  { title: 'التفاصيل الداخلية', icon: BedDouble },
  { title: 'معلومات التواصل', icon: Phone },
  { title: 'رفع الصور', icon: Upload },
];

export const AddProperty = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [uploadingImage, setUploadingImage] = useState(false);

  const [formData, setFormData] = useState({
    total_area: '',
    price: '',
    front_width: '',
    length: '',
    bedrooms: '',
    bathrooms: '',
    owner_name: '',
    owner_phone: '',
    images: [],
    status: 'available',
  });

  const handleNext = () => {
    setError('');
    if (currentStep === 0) {
      if (!formData.total_area || !formData.price) {
        setError('يرجى إدخال جميع الحقول');
        return;
      }
    }
    if (currentStep === 1) {
      if (!formData.front_width || !formData.length) {
        setError('يرجى إدخال جميع الحقول');
        return;
      }
    }
    if (currentStep === 2) {
      if (!formData.bedrooms || !formData.bathrooms) {
        setError('يرجى إدخال جميع الحقول');
        return;
      }
    }
    if (currentStep === 3) {
      if (!formData.owner_name || !formData.owner_phone) {
        setError('يرجى إدخال جميع الحقول');
        return;
      }
    }
    if (currentStep < STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handlePrev = () => {
    setError('');
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleImageUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploadingImage(true);
    setError('');

    try {
      const formDataUpload = new FormData();
      formDataUpload.append('file', file);

      const { data } = await axios.post(`${API}/upload`, formDataUpload, {
        withCredentials: true,
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setFormData({
        ...formData,
        images: [...formData.images, `${process.env.REACT_APP_BACKEND_URL}${data.url}`],
      });
    } catch (err) {
      setError('خطأ في رفع الصورة');
    } finally {
      setUploadingImage(false);
    }
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError('');

    try {
      const payload = {
        total_area: parseFloat(formData.total_area),
        price: parseFloat(formData.price),
        front_width: parseFloat(formData.front_width),
        length: parseFloat(formData.length),
        bedrooms: parseInt(formData.bedrooms),
        bathrooms: parseInt(formData.bathrooms),
        owner_name: formData.owner_name,
        owner_phone: formData.owner_phone,
        images: formData.images,
        status: formData.status,
      };

      await axios.post(`${API}/properties`, payload, { withCredentials: true });
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'حدث خطأ أثناء إضافة العقار');
    } finally {
      setLoading(false);
    }
  };

  const renderStep = () => {
    const StepIcon = STEPS[currentStep].icon;

    switch (currentStep) {
      case 0:
        return (
          <div className="space-y-8">
            <div className="text-center mb-8">
              <StepIcon className="w-20 h-20 text-[#1A5632] mx-auto mb-4" />
              <h2 className="text-4xl font-extrabold text-[#0A1F13]">
                {STEPS[currentStep].title}
              </h2>
            </div>
            <div>
              <label className="block text-2xl font-extrabold text-[#0A1F13] mb-3">
                <Home className="inline-block w-8 h-8 ml-2" />
                المساحة الكلية (متر مربع)
              </label>
              <input
                data-testid={PROPERTY.totalAreaInput}
                type="number"
                value={formData.total_area}
                onChange={(e) => setFormData({ ...formData, total_area: e.target.value })}
                className="w-full min-h-[64px] text-2xl p-4 rounded-xl border-2 border-[#D2CFC9] focus:border-[#1A5632] focus:ring-4 focus:ring-[#1A5632]/20 outline-none font-semibold"
                placeholder="مثال: 200"
              />
            </div>
            <div>
              <label className="block text-2xl font-extrabold text-[#0A1F13] mb-3">
                <DollarSign className="inline-block w-8 h-8 ml-2" />
                السعر (دينار عراقي)
              </label>
              <input
                data-testid={PROPERTY.priceInput}
                type="number"
                value={formData.price}
                onChange={(e) => setFormData({ ...formData, price: e.target.value })}
                className="w-full min-h-[64px] text-2xl p-4 rounded-xl border-2 border-[#D2CFC9] focus:border-[#1A5632] focus:ring-4 focus:ring-[#1A5632]/20 outline-none font-semibold"
                placeholder="مثال: 500000"
              />
            </div>
          </div>
        );

      case 1:
        return (
          <div className="space-y-8">
            <div className="text-center mb-8">
              <StepIcon className="w-20 h-20 text-[#1A5632] mx-auto mb-4" />
              <h2 className="text-4xl font-extrabold text-[#0A1F13]">
                {STEPS[currentStep].title}
              </h2>
            </div>
            <div>
              <label className="block text-2xl font-extrabold text-[#0A1F13] mb-3">
                <Ruler className="inline-block w-8 h-8 ml-2" />
                مساحة الواجهة (متر)
              </label>
              <input
                data-testid={PROPERTY.frontWidthInput}
                type="number"
                value={formData.front_width}
                onChange={(e) => setFormData({ ...formData, front_width: e.target.value })}
                className="w-full min-h-[64px] text-2xl p-4 rounded-xl border-2 border-[#D2CFC9] focus:border-[#1A5632] focus:ring-4 focus:ring-[#1A5632]/20 outline-none font-semibold"
                placeholder="مثال: 10"
              />
            </div>
            <div>
              <label className="block text-2xl font-extrabold text-[#0A1F13] mb-3">
                <Ruler className="inline-block w-8 h-8 ml-2" />
                الطول (متر)
              </label>
              <input
                data-testid={PROPERTY.lengthInput}
                type="number"
                value={formData.length}
                onChange={(e) => setFormData({ ...formData, length: e.target.value })}
                className="w-full min-h-[64px] text-2xl p-4 rounded-xl border-2 border-[#D2CFC9] focus:border-[#1A5632] focus:ring-4 focus:ring-[#1A5632]/20 outline-none font-semibold"
                placeholder="مثال: 20"
              />
            </div>
          </div>
        );

      case 2:
        return (
          <div className="space-y-8">
            <div className="text-center mb-8">
              <StepIcon className="w-20 h-20 text-[#1A5632] mx-auto mb-4" />
              <h2 className="text-4xl font-extrabold text-[#0A1F13]">
                {STEPS[currentStep].title}
              </h2>
            </div>
            <div>
              <label className="block text-2xl font-extrabold text-[#0A1F13] mb-3">
                <BedDouble className="inline-block w-8 h-8 ml-2" />
                عدد الغرف
              </label>
              <input
                data-testid={PROPERTY.bedroomsInput}
                type="number"
                value={formData.bedrooms}
                onChange={(e) => setFormData({ ...formData, bedrooms: e.target.value })}
                className="w-full min-h-[64px] text-2xl p-4 rounded-xl border-2 border-[#D2CFC9] focus:border-[#1A5632] focus:ring-4 focus:ring-[#1A5632]/20 outline-none font-semibold"
                placeholder="مثال: 3"
              />
            </div>
            <div>
              <label className="block text-2xl font-extrabold text-[#0A1F13] mb-3">
                <BedDouble className="inline-block w-8 h-8 ml-2" />
                عدد الحمامات
              </label>
              <input
                data-testid={PROPERTY.bathroomsInput}
                type="number"
                value={formData.bathrooms}
                onChange={(e) => setFormData({ ...formData, bathrooms: e.target.value })}
                className="w-full min-h-[64px] text-2xl p-4 rounded-xl border-2 border-[#D2CFC9] focus:border-[#1A5632] focus:ring-4 focus:ring-[#1A5632]/20 outline-none font-semibold"
                placeholder="مثال: 2"
              />
            </div>
          </div>
        );

      case 3:
        return (
          <div className="space-y-8">
            <div className="text-center mb-8">
              <StepIcon className="w-20 h-20 text-[#1A5632] mx-auto mb-4" />
              <h2 className="text-4xl font-extrabold text-[#0A1F13]">
                {STEPS[currentStep].title}
              </h2>
            </div>
            <div>
              <label className="block text-2xl font-extrabold text-[#0A1F13] mb-3">
                <User className="inline-block w-8 h-8 ml-2" />
                اسم مالك العقار
              </label>
              <input
                data-testid="property-owner-name-input"
                type="text"
                value={formData.owner_name}
                onChange={(e) => setFormData({ ...formData, owner_name: e.target.value })}
                className="w-full min-h-[64px] text-2xl p-4 rounded-xl border-2 border-[#D2CFC9] focus:border-[#1A5632] focus:ring-4 focus:ring-[#1A5632]/20 outline-none font-semibold"
                placeholder="مثال: محمد أحمد"
              />
            </div>
            <div>
              <label className="block text-2xl font-extrabold text-[#0A1F13] mb-3">
                <Phone className="inline-block w-8 h-8 ml-2" />
                رقم هاتف مالك العقار
              </label>
              <input
                data-testid={PROPERTY.ownerPhoneInput}
                type="tel"
                value={formData.owner_phone}
                onChange={(e) => setFormData({ ...formData, owner_phone: e.target.value })}
                className="w-full min-h-[64px] text-2xl p-4 rounded-xl border-2 border-[#D2CFC9] focus:border-[#1A5632] focus:ring-4 focus:ring-[#1A5632]/20 outline-none font-semibold"
                placeholder="مثال: 0501234567"
              />
            </div>
          </div>
        );

      case 4:
        return (
          <div className="space-y-8">
            <div className="text-center mb-8">
              <StepIcon className="w-20 h-20 text-[#1A5632] mx-auto mb-4" />
              <h2 className="text-4xl font-extrabold text-[#0A1F13]">
                {STEPS[currentStep].title}
              </h2>
              <p className="text-xl font-semibold text-[#2B4736] mt-4">
                (اختياري)
              </p>
            </div>
            <div>
              <label
                htmlFor="image-upload"
                data-testid={PROPERTY.imageUpload}
                className="w-full min-h-[72px] bg-[#1A5632] text-white rounded-2xl flex items-center justify-center gap-4 hover:bg-[#0F3820] transition-colors cursor-pointer text-2xl font-black"
              >
                <Upload className="w-10 h-10" />
                {uploadingImage ? 'جاري الرفع...' : 'رفع صورة'}
              </label>
              <input
                id="image-upload"
                type="file"
                accept="image/*"
                onChange={handleImageUpload}
                className="hidden"
                disabled={uploadingImage}
              />
            </div>
            {formData.images.length > 0 && (
              <div className="grid grid-cols-2 gap-4">
                {formData.images.map((img, idx) => (
                  <img
                    key={idx}
                    src={img}
                    alt={`صورة ${idx + 1}`}
                    className="w-full h-40 object-cover rounded-xl border-2 border-[#D2CFC9]"
                  />
                ))}
              </div>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-[#F9F6F0] p-4 sm:p-8" dir="rtl">
      <div className="max-w-2xl mx-auto">
        {/* Progress Bar */}
        <div className="mb-8">
          <div className="flex justify-between mb-4">
            {STEPS.map((step, idx) => (
              <div
                key={idx}
                className={`flex-1 h-3 rounded-full mx-1 ${
                  idx <= currentStep ? 'bg-[#1A5632]' : 'bg-[#D2CFC9]'
                }`}
              />
            ))}
          </div>
          <p className="text-center text-2xl font-bold text-[#2B4736]">
            الخطوة {currentStep + 1} من {STEPS.length}
          </p>
        </div>

        {/* Form Card */}
        <div className="bg-white border-2 border-[#D2CFC9] rounded-3xl p-8 sm:p-12 shadow-sm">
          {error && (
            <div className="mb-6 p-6 bg-red-50 border-2 border-red-500 rounded-2xl">
              <p className="text-xl font-bold text-red-700">{error}</p>
            </div>
          )}

          {renderStep()}

          {/* Navigation Buttons */}
          <div className="mt-8 flex gap-4">
            {currentStep > 0 && (
              <button
                data-testid={PROPERTY.prevButton}
                onClick={handlePrev}
                className="flex-1 min-h-[72px] bg-transparent border-4 border-[#1A5632] text-[#1A5632] rounded-2xl flex items-center justify-center gap-3 hover:bg-[#1A5632] hover:text-white transition-colors text-2xl font-black"
              >
                <ChevronRight className="w-10 h-10" />
                السابق
              </button>
            )}
            {currentStep < STEPS.length - 1 ? (
              <button
                data-testid={PROPERTY.nextButton}
                onClick={handleNext}
                className="flex-1 min-h-[72px] bg-[#1A5632] text-white rounded-2xl flex items-center justify-center gap-3 hover:bg-[#0F3820] transition-colors shadow-[0_8px_0_#0F3820] active:translate-y-2 active:shadow-[0_0px_0_#0F3820] text-2xl font-black"
              >
                التالي
                <ChevronLeft className="w-10 h-10" />
              </button>
            ) : (
              <button
                data-testid={PROPERTY.submitButton}
                onClick={handleSubmit}
                disabled={loading}
                className="flex-1 min-h-[72px] bg-[#1A5632] text-white rounded-2xl flex items-center justify-center gap-3 hover:bg-[#0F3820] transition-colors shadow-[0_8px_0_#0F3820] active:translate-y-2 active:shadow-[0_0px_0_#0F3820] text-2xl font-black disabled:opacity-50"
              >
                {loading ? 'جاري الحفظ...' : 'حفظ العقار'}
              </button>
            )}
          </div>

          <button
            onClick={() => navigate('/dashboard')}
            className="w-full mt-6 text-xl font-bold text-[#1A5632] hover:text-[#0F3820] underline"
          >
            إلغاء والعودة
          </button>
        </div>
      </div>
    </div>
  );
};
