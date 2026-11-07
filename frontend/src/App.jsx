import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useParams } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import DashboardOverview from './pages/DashboardOverview';
import Analytics from './pages/Analytics';
import VideoProcessor from './pages/VideoProcessor';
import ImageProcessor from './pages/ImageProcessor';
import EnforcementCenter from './pages/EnforcementCenter';
import ChallanExplorer from './pages/ChallanExplorer';
import ChallanDetails from './pages/ChallanDetails';
import EvidenceExplorer from './pages/EvidenceExplorer';
import EvidenceDetails from './pages/EvidenceDetails';
// The QR code on challan PDFs points to /verify/challan/:id
function VerifyChallan() {
  const { id } = useParams();
  return <Navigate to={`/challan/${id}`} replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen overflow-hidden" style={{ background: 'var(--vd-ground)' }}>
        <Sidebar />
        <main className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<DashboardOverview />} />
            <Route path="/evidence" element={<EvidenceExplorer />} />
            <Route path="/evidence/:id" element={<EvidenceDetails />} />
            <Route path="/image" element={<ImageProcessor />} />
            <Route path="/video" element={<VideoProcessor />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/enforcement" element={<EnforcementCenter />} />
            <Route path="/challans" element={<ChallanExplorer />} />
            <Route path="/challan/:id" element={<ChallanDetails />} />
            <Route path="/verify/challan/:id" element={<VerifyChallan />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
