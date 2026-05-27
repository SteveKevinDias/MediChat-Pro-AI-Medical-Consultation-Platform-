import { BrowserRouter as Router, Routes, Route, useNavigate } from 'react-router-dom';
import Landing from './pages/Landing';
import PatientPortal from './pages/PatientPortal';
import DoctorDashboard from './pages/DoctorDashboard';
import './index.css';

function App() {
  return (
    <Router>
      <div className="app-container">
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/patient/*" element={<PatientPortal />} />
          <Route path="/doctor/*" element={<DoctorDashboard />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
