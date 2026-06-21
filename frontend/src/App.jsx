import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import ApplicantDashboard from './pages/applicant/ApplicantDashboard'
import SubmitApplication from './pages/applicant/SubmitApplication'
import TrackApplication from './pages/applicant/TrackApplication'
import UploadDocuments from './pages/applicant/UploadDocuments'
import ApplicationConfirmation from './pages/applicant/ApplicationConfirmation'
import SubmitObjection from './pages/applicant/SubmitObjection'
import StaffDashboard from './pages/staff/StaffDashboard'
import ApplicationManagement from './pages/staff/ApplicationManagement'
import ApplicationDetails from './pages/staff/ApplicationDetails'
import RegistrarReview from './pages/staff/RegistrarReview'
import CertificateIssuance from './pages/staff/CertificateIssuance'
// Student 3 — Surveyor, Map & Analytics
import SurveyorTasks from './pages/surveyor/SurveyorTasks'
import SurveyTaskExecution from './pages/surveyor/SurveyTaskExecution'
import LiveMap from './pages/map/LiveMap'
import AnalyticsDashboard from './pages/analytics/AnalyticsDashboard'
// Auth (Task 26 & 27)
import Login from './pages/auth/Login'
import ProtectedRoute from './components/ProtectedRoute'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public */}
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Navigate to="/login" replace />} />

        {/* Applicant routes */}
        <Route path="/applicant" element={
          <ProtectedRoute allowedRoles={['applicant']}>
            <ApplicantDashboard />
          </ProtectedRoute>
        } />
        <Route path="/applicant/dashboard" element={
          <ProtectedRoute allowedRoles={['applicant']}>
            <ApplicantDashboard />
          </ProtectedRoute>
        } />
        <Route path="/applicant/submit" element={
          <ProtectedRoute allowedRoles={['applicant']}>
            <SubmitApplication />
          </ProtectedRoute>
        } />
        <Route path="/applicant/track" element={
          <ProtectedRoute allowedRoles={['applicant']}>
            <TrackApplication />
          </ProtectedRoute>
        } />
        <Route path="/applicant/track/:id" element={
          <ProtectedRoute allowedRoles={['applicant']}>
            <TrackApplication />
          </ProtectedRoute>
        } />
        <Route path="/applicant/upload-documents" element={
          <ProtectedRoute allowedRoles={['applicant']}>
            <UploadDocuments />
          </ProtectedRoute>
        } />
        <Route path="/applicant/upload" element={<Navigate to="/applicant/upload-documents" replace />} />
        <Route path="/applicant/confirmation" element={
          <ProtectedRoute allowedRoles={['applicant']}>
            <ApplicationConfirmation />
          </ProtectedRoute>
        } />
        <Route path="/applicant/objection" element={
          <ProtectedRoute allowedRoles={['applicant']}>
            <SubmitObjection />
          </ProtectedRoute>
        } />
        <Route path="/applicant/objection/:id" element={
          <ProtectedRoute allowedRoles={['applicant']}>
            <SubmitObjection />
          </ProtectedRoute>
        } />

        {/* Staff routes */}
        <Route path="/staff" element={<Navigate to="/staff/dashboard" replace />} />
        <Route path="/staff/dashboard" element={
          <ProtectedRoute allowedRoles={['staff']}>
            <StaffDashboard />
          </ProtectedRoute>
        } />
        <Route path="/staff/applications" element={
          <ProtectedRoute allowedRoles={['staff']}>
            <ApplicationManagement />
          </ProtectedRoute>
        } />
        <Route path="/staff/applications/:applicationId" element={
          <ProtectedRoute allowedRoles={['staff']}>
            <ApplicationDetails />
          </ProtectedRoute>
        } />
        <Route path="/staff/registrar-review" element={
          <ProtectedRoute allowedRoles={['staff']}>
            <RegistrarReview />
          </ProtectedRoute>
        } />
        <Route path="/staff/registrar-review/:applicationId" element={
          <ProtectedRoute allowedRoles={['staff']}>
            <RegistrarReview />
          </ProtectedRoute>
        } />
        <Route path="/staff/certificates" element={
          <ProtectedRoute allowedRoles={['staff']}>
            <CertificateIssuance />
          </ProtectedRoute>
        } />

        {/* Surveyor routes */}
        <Route path="/surveyor/tasks" element={
          <ProtectedRoute allowedRoles={['surveyor', 'staff']}>
            <SurveyorTasks />
          </ProtectedRoute>
        } />
        <Route path="/surveyor/tasks/:taskId" element={
          <ProtectedRoute allowedRoles={['surveyor', 'staff']}>
            <SurveyTaskExecution />
          </ProtectedRoute>
        } />

        {/* Map route */}
        <Route path="/map/live" element={
          <ProtectedRoute allowedRoles={['staff', 'surveyor', 'manager']}>
            <LiveMap />
          </ProtectedRoute>
        } />
        <Route path="/map" element={<Navigate to="/map/live" replace />} />

        {/* Analytics route */}
        <Route path="/analytics" element={
          <ProtectedRoute allowedRoles={['manager', 'staff']}>
            <AnalyticsDashboard />
          </ProtectedRoute>
        } />
      </Routes>
    </BrowserRouter>
  )
}
