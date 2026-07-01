import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { AUTH } from '../constants/testIds';
import { Building, Phone, Mail, Lock, User, Briefcase } from 'lucide-react';

function formatApiErrorDetail(detail) {
  if (detail == null) return 'حدث خطأ ما. يرجى المحاولة مرة أخرى.';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail))
    return detail
      .map((e) => (e && typeof e.msg === 'string' ? e.msg : JSON.stringify(e)))
      .filter(Boolean)
      .join(' ');
  if (detail && typeof detail.msg === 'string') return detail.msg;
  return String(detail);
}

export const AuthPage = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [officeName, setOfficeName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isLogin) {
        await login(identifier, password);
      } else {
        await register(name, identifier, password, officeName);
      }
      navigate('/dashboard');
    } catch (err) {
      setError(formatApiErrorDetail(err.response?.data?.detail) || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 sm:p-8" dir="rtl">
      <div className="w-full max-w-2xl">
        {/* Logo/Header */}
        <div className="text-center mb-12">
          <div className="flex justify-center mb-6">
            <Building className="w-24 h-24 text-[#1A5632]" />
          </div>
          <h1 className="text-5xl sm:text-6xl font-black text-[#0A1F13] mb-4">
            عقاراتي
          </h1>
          <p className="text-2xl font-semibold text-[#2B4736]">
            منصة عقارية سهلة الاستخدام
          </p>
        </div>

        {/* Form Card */}
        <div className="bg-white border-2 border-[#D2CFC9] rounded-3xl p-8 sm:p-12 shadow-sm">
          <h2 className="text-4xl font-extrabold text-[#0A1F13] mb-8 text-center">
            {isLogin ? 'تسجيل الدخول' : 'إنشاء حساب جديد'}
          </h2>

          {error && (
            <div className="mb-6 p-6 bg-red-50 border-2 border-red-500 rounded-2xl">
              <p className="text-xl font-bold text-red-700">{error}</p>
            </div>
          )}

          <form
            data-testid={isLogin ? AUTH.loginForm : AUTH.registerForm}
            onSubmit={handleSubmit}
            className="space-y-6"
          >
            {!isLogin && (
              <div>
                <label className="block text-2xl font-extrabold text-[#0A1F13] mb-3">
                  <User className="inline-block w-8 h-8 ml-2" />
                  الاسم الكامل
                </label>
                <input
                  data-testid={AUTH.nameInput}
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  className="w-full min-h-[64px] text-2xl p-4 rounded-xl border-2 border-[#D2CFC9] focus:border-[#1A5632] focus:ring-4 focus:ring-[#1A5632]/20 outline-none font-semibold"
                  placeholder="أدخل اسمك الكامل"
                />
              </div>
            )}

            <div>
              <label className="block text-2xl font-extrabold text-[#0A1F13] mb-3">
                <div className="flex items-center gap-2">
                  <Phone className="w-8 h-8" />
                  <span>/</span>
                  <Mail className="w-8 h-8" />
                </div>
                رقم الهاتف أو البريد الإلكتروني
              </label>
              <input
                data-testid={AUTH.identifierInput}
                type="text"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                required
                className="w-full min-h-[64px] text-2xl p-4 rounded-xl border-2 border-[#D2CFC9] focus:border-[#1A5632] focus:ring-4 focus:ring-[#1A5632]/20 outline-none font-semibold"
                placeholder="مثال: 0501234567 أو email@example.com"
              />
            </div>

            <div>
              <label className="block text-2xl font-extrabold text-[#0A1F13] mb-3">
                <Lock className="inline-block w-8 h-8 ml-2" />
                كلمة المرور
              </label>
              <input
                data-testid={AUTH.passwordInput}
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full min-h-[64px] text-2xl p-4 rounded-xl border-2 border-[#D2CFC9] focus:border-[#1A5632] focus:ring-4 focus:ring-[#1A5632]/20 outline-none font-semibold"
                placeholder="أدخل كلمة المرور"
              />
            </div>

            {!isLogin && (
              <div>
                <label className="block text-2xl font-extrabold text-[#0A1F13] mb-3">
                  <Briefcase className="inline-block w-8 h-8 ml-2" />
                  اسم المكتب العقاري (اختياري)
                </label>
                <input
                  data-testid={AUTH.officeNameInput}
                  type="text"
                  value={officeName}
                  onChange={(e) => setOfficeName(e.target.value)}
                  className="w-full min-h-[64px] text-2xl p-4 rounded-xl border-2 border-[#D2CFC9] focus:border-[#1A5632] focus:ring-4 focus:ring-[#1A5632]/20 outline-none font-semibold"
                  placeholder="اسم المكتب إن وجد"
                />
              </div>
            )}

            <button
              data-testid={isLogin ? AUTH.loginButton : AUTH.registerButton}
              type="submit"
              disabled={loading}
              className="w-full min-h-[72px] bg-[#1A5632] text-white rounded-2xl flex items-center justify-center gap-4 hover:bg-[#0F3820] transition-colors shadow-[0_8px_0_#0F3820] active:translate-y-2 active:shadow-[0_0px_0_#0F3820] text-2xl sm:text-3xl font-black disabled:opacity-50"
            >
              {loading ? 'جاري التحميل...' : isLogin ? 'تسجيل الدخول' : 'إنشاء حساب'}
            </button>
          </form>

          <div className="mt-8 text-center">
            <button
              data-testid={isLogin ? AUTH.switchToRegister : AUTH.switchToLogin}
              onClick={() => {
                setIsLogin(!isLogin);
                setError('');
              }}
              className="text-xl font-bold text-[#1A5632] hover:text-[#0F3820] underline"
            >
              {isLogin ? 'ليس لديك حساب؟ سجل الآن' : 'لديك حساب؟ سجل دخولك'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
