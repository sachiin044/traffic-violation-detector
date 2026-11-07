import { AUTO_THRESHOLD, REVIEW_THRESHOLD } from './violations';

const NUMBER_WORDS = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine'];

export const pct = (value) => (Number.isFinite(value) ? `${Math.round(value * 100)}%` : '—');

// Like pct, but adds a decimal when rounding would push a score across a
// challan threshold (0.849 shows as 84.9%, not a misleading 85%)
export const pctExact = (value) => {
  if (!Number.isFinite(value)) return '—';
  const rounded = Math.round(value * 100) / 100;
  const crosses = [REVIEW_THRESHOLD, AUTO_THRESHOLD].some((t) => (value < t) !== (rounded < t));
  return crosses ? `${(Math.floor(value * 1000) / 10).toFixed(1)}%` : `${Math.round(value * 100)}%`;
};

const toDate = (iso) => {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d;
};

// "7 Nov, 9:43 pm"
export const formatTime = (iso) => {
  const d = toDate(iso);
  if (!d) return '—';
  return d.toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' });
};

// "7 Nov 2026, 9:43 pm"
export const formatDateTime = (iso) => {
  const d = toDate(iso);
  if (!d) return '—';
  return d.toLocaleString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit' });
};

// "7 Nov"
export const formatDay = (isoDate) => {
  const d = toDate(isoDate && isoDate.length === 10 ? `${isoDate}T00:00:00` : isoDate);
  if (!d) return isoDate || '—';
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
};

export const formatDuration = (ms) => {
  if (!Number.isFinite(ms)) return '—';
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${Math.round(ms)} ms`;
};

export const formatBytes = (bytes) => {
  if (!bytes) return '';
  return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.round(bytes / 1024)} KB`;
};

export const formatNumber = (n) => (Number.isFinite(n) ? n.toLocaleString('en-IN') : '—');

export const inr = (n) => (Number.isFinite(Number(n)) ? `₹${Number(n).toLocaleString('en-IN')}` : '—');

export const plural = (n, one, many) => (n === 1 ? one : many);

export const countWord = (n) => (n >= 0 && n < NUMBER_WORDS.length ? NUMBER_WORDS[n] : String(n));

// Show Indian plates the way they're printed: "CH 01 AR 7148", "22 BH 1234 AA"
export const formatPlate = (raw) => {
  if (!raw) return '';
  const plate = String(raw).replace(/[^A-Z0-9]/gi, '').toUpperCase();
  const bh = plate.match(/^(\d{2})(BH)(\d{4})([A-Z]{1,2})$/);
  if (bh) return bh.slice(1).join(' ');
  const std = plate.match(/^([A-Z]{2})(\d{1,2})([A-Z]{0,3})(\d{1,4})$/);
  if (std) return std.slice(1).filter(Boolean).join(' ');
  return plate;
};

export const errorMessage = (err, fallback = 'Something went wrong.') => {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (err?.response?.status === 404) return 'Not found. It may have been removed.';
  if (err?.code === 'ERR_NETWORK') return 'The API at port 8000 is not responding. Start the backend and try again.';
  return err?.message || fallback;
};
