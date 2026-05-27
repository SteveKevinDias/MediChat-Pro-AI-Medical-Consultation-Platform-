import { useNavigate } from 'react-router-dom';

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div>
      <div className="topbar">
        <div className="brand">MediChat</div>
      </div>
      
      <div className="hero-container">
        <div className="hero">
          <h1>
            NEXT-GEN<br />
            MEDICAL <span>INTELLIGENCE</span>
          </h1>
          <p className="hero-subtitle">
            High-performance diagnostic inference driven by human-in-the-loop validation.
          </p>
        </div>
      </div>

      <div className="grid-container">
        <div className="imc-card" onClick={() => navigate('/patient')}>
          <span className="card-tag">Portal 01</span>
          <h2>Patient Portal</h2>
          <p>
            Secure, encrypted access to your medical history. Submit symptomatology data 
            for immediate AI assessment and doctor review.
          </p>
          <div className="arrow-link">
            Initialize <span style={{fontSize: '1.2rem'}}>→</span>
          </div>
        </div>

        <div className="imc-card" onClick={() => navigate('/doctor')}>
          <span className="card-tag">Portal 02</span>
          <h2>Doctor Dashboard</h2>
          <p>
            Access the high-speed review queue. Validate diagnostic inferences, 
            append clinical notes, and authorize finalized reports.
          </p>
          <div className="arrow-link">
            Authenticate <span style={{fontSize: '1.2rem'}}>→</span>
          </div>
        </div>
      </div>
    </div>
  );
}
