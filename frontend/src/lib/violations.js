// Single source of truth for violation, vehicle and challan vocabulary.

// Same thresholds the backend uses in engine/challan.py
export const REVIEW_THRESHOLD = 0.7;
export const AUTO_THRESHOLD = 0.85;

// Fixed order = fixed chart colour. Colours are a validated categorical palette
// (colour-blind safe on white); a colour always follows the violation, never its rank.
export const VIOLATIONS = [
  { type: 'Helmet Non Compliance', key: 'helmet', name: 'No helmet', color: '#2a78d6' },
  { type: 'Triple Riding', key: 'triple_riding', name: 'Triple riding', color: '#eb6834' },
  { type: 'Seatbelt Non Compliance', key: 'seatbelt', name: 'No seatbelt', color: '#1baf7a' },
  { type: 'Red Light Violation', key: 'red_light', name: 'Red light jumped', color: '#eda100' },
  { type: 'Illegal Parking', key: 'illegal_parking', name: 'Illegal parking', color: '#e87ba4' },
  { type: 'Wrong Side Driving', key: 'wrong_side', name: 'Wrong side driving', color: '#008300' },
];

const BY_TYPE = Object.fromEntries(VIOLATIONS.map((v) => [v.type, v]));
const BY_KEY = Object.fromEntries(VIOLATIONS.map((v) => [v.key, v]));

export const violationMeta = (typeOrKey) =>
  BY_TYPE[typeOrKey] || BY_KEY[typeOrKey] || { type: typeOrKey, key: typeOrKey, name: typeOrKey, color: '#8a939d' };

export const violationName = (typeOrKey) => violationMeta(typeOrKey).name;

const VEHICLE_NAMES = {
  motorcycle: 'Motorcycle',
  bicycle: 'Bicycle',
  car: 'Car',
  heavy_vehicle: 'Bus or truck',
  autorickshaw: 'Autorickshaw',
  scene: 'Whole scene',
  unknown: 'Vehicle',
};

export const vehicleName = (type) =>
  VEHICLE_NAMES[type] || (type ? type.charAt(0).toUpperCase() + type.slice(1).replace(/_/g, ' ') : 'Vehicle');

// Challan workflow, in order
export const CHALLAN_STATUSES = [
  { value: 'REVIEW_REQUIRED', label: 'Needs review', tone: 'amber' },
  { value: 'GENERATED', label: 'Ready to issue', tone: 'blue' },
  { value: 'ISSUED', label: 'Issued', tone: 'muted' },
  { value: 'PAID', label: 'Paid', tone: 'green' },
  { value: 'DISPUTED', label: 'Disputed', tone: 'red' },
  { value: 'PENDING', label: 'Pending', tone: 'muted' },
];

export const challanStatus = (value) =>
  CHALLAN_STATUSES.find((s) => s.value === value) || { value, label: value || 'Unknown', tone: 'muted' };

export const thresholdLevel = (confidence) => {
  if (confidence >= AUTO_THRESHOLD) return 'auto';
  if (confidence >= REVIEW_THRESHOLD) return 'review';
  return 'below';
};

export const THRESHOLD_COPY = {
  auto: 'Meets the auto-challan threshold',
  review: 'Meets the review threshold',
  below: 'Below the challan threshold',
};
