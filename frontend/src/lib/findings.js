import { violationMeta } from './violations';

// Turn violations into display rows, numbering repeats ("rider 1", "rider 2")
export const toFindings = (violations = []) => {
  const list = violations.map((v) => (typeof v === 'string' ? { type: v, confidence: NaN } : v));
  const totals = {};
  list.forEach((v) => { totals[v.type] = (totals[v.type] || 0) + 1; });
  const seen = {};
  return list
    .map((v) => {
      seen[v.type] = (seen[v.type] || 0) + 1;
      let detail = '';
      if (totals[v.type] > 1) {
        detail = v.type === 'Helmet Non Compliance' ? `rider ${seen[v.type]}` : `#${seen[v.type]}`;
      }
      return {
        key: `${v.type}-${seen[v.type]}`,
        name: violationMeta(v.type).name,
        detail,
        confidence: v.confidence,
      };
    })
    .sort((a, b) => (b.confidence || 0) - (a.confidence || 0));
};
