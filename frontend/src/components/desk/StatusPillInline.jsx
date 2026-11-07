import React from 'react';
import { challanStatus } from '../../lib/violations';

// Lower-case status words for use inside a sentence ("is needs review" reads wrong, so use phrasing)
const PHRASES = {
  REVIEW_REQUIRED: 'waiting for review',
  PENDING: 'pending',
  GENERATED: 'ready to issue',
  ISSUED: 'issued',
  PAID: 'paid',
  DISPUTED: 'disputed',
};

export default function StatusPillInline({ status }) {
  return <strong>{PHRASES[status] || challanStatus(status).label.toLowerCase()}</strong>;
}
