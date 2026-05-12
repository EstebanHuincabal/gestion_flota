/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#4F46E5',
          light: '#EEF2FF',
        },
        accent: {
          DEFAULT: '#7C3AED',
        },
        slate: {
          950: '#020617',
          50: '#F8FAFC',
          900: '#0F172A',
          500: '#64748B',
          200: '#E2E8F0',
        },
        success: {
          bg: '#ECFDF5',
          text: '#059669',
        },
        danger: {
          bg: '#FFF1F2',
          text: '#E11D48',
        },
        warning: {
          bg: '#FFFBEB',
          text: '#D97706',
        }
      },
      backgroundImage: {
        'accent-gradient': 'linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)',
      }
    },
  },
  plugins: [],
}
