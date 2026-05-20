import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  darkMode: 'media',
  theme: {
    extend: {
      fontSize: {
        sm: ['14px', '20px'], // compact-density base
      },
      spacing: {
        card: '16px', // compact card padding (vs default 24px)
      },
    },
  },
  plugins: [],
}
export default config
