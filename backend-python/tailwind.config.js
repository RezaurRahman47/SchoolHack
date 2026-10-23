/** Tailwind config — rebuild CSS with: npx tailwindcss@3 -c tailwind.config.js -i app/static/src.css -o app/static/tailwind.css --minify */
module.exports = {
  content: ['./app/templates/**/*.html'],
  theme: { extend: {
    fontFamily: { sans: ['Inter', 'system-ui', 'sans-serif'], display: ['"Space Grotesk"', 'Inter', 'sans-serif'] },
    colors: { ink: { 900: '#0f1b2d', 800: '#16263f', 700: '#22375a' }, reagent: { 400: '#2dd4bf', 500: '#14b8a6', 600: '#0d9488' },
              pass: '#16a34a', fail: '#dc2626', amberx: '#f59e0b' } } },
};
