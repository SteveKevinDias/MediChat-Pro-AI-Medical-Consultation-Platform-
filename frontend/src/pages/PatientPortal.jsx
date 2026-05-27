import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

export default function PatientPortal() {
  const navigate = useNavigate();
  const [step, setStep] = useState('identify'); // identify, history, consultation, submitted
  const [isLoginMode, setIsLoginMode] = useState(true); // Toggle between Login and Register
  
  const [patientInfo, setPatientInfo] = useState(null);
  const [histReport, setHistReport] = useState(null);
  const [reviewId, setReviewId] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [pastReviews, setPastReviews] = useState([]);

  const [name, setName] = useState('');
  const [dob, setDob] = useState('1990-01-01');
  const [complaint, setComplaint] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploadedPdfs, setUploadedPdfs] = useState([]);
  const [uploadedImages, setUploadedImages] = useState([]);

  const handlePdfUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', sessionId);
    setLoading(true);
    try {
      const res = await axios.post('/api/patient/upload_pdf', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      if (res.data.success) {
        setUploadedPdfs(prev => [...prev, res.data.filename]);
        alert("PDF Uploaded & Indexed Successfully!");
      }
    } catch (err) {
      console.error(err);
      alert("Error uploading PDF");
    } finally {
      setLoading(false);
    }
  };

  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const base64Str = event.target.result.split(',')[1];
      setUploadedImages(prev => [...prev, { data: base64Str, mime_type: file.type }]);
    };
    reader.readAsDataURL(file);
  };

  const handleIdentify = async (e) => {
    e.preventDefault();
    if (!name.trim()) return alert("Please enter your full name.");
    setLoading(true);
    try {
      const res = await axios.post('/api/patient/identify', { name, dob });
      
      // If login mode, maybe warn if it's a new record? Our API auto-creates.
      // But we can just use the is_new flag to inform the UI.
      if (isLoginMode && res.data.is_new) {
        alert("No existing record found. We have created a new patient profile for you.");
      }

      setPatientInfo({ ...res.data, name, dob });
      
      const newSessionId = crypto.randomUUID();
      setSessionId(newSessionId);

      const histRes = await axios.post('/api/ai/history_report', {
        patient_name: name,
        past_summaries: res.data.summaries
      });
      setHistReport(histRes.data.report);

      if (!res.data.is_new) {
        const approvedRes = await axios.get(`/api/patient/approved_reviews/${res.data.patient_id}`);
        setPastReviews(approvedRes.data);
      }
      setStep('history');
    } catch (err) {
      console.error(err);
      alert("Error identifying patient");
    } finally {
      setLoading(false);
    }
  };

  const pollTaskStatus = async (taskId) => {
    while (true) {
      const statusRes = await axios.get(`/api/ai/diagnosis/status/${taskId}`);
      if (statusRes.data.status === 'SUCCESS') {
        return statusRes.data.diagnosis;
      } else if (statusRes.data.status === 'FAILURE') {
        throw new Error("Diagnosis task failed");
      }
      // Wait 2 seconds before polling again
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
  };

  const handleSubmitConsultation = async (e) => {
    e.preventDefault();
    if (!complaint.trim()) return alert("Please describe your symptoms.");
    setLoading(true);
    try {
      const aiRes = await axios.post('/api/ai/diagnosis', {
        patient_name: patientInfo.name,
        past_summaries: patientInfo.summaries,
        current_complaint: complaint,
        session_id: sessionId,
        images: uploadedImages
      });

      const diagnosis = await pollTaskStatus(aiRes.data.task_id);

      const submitRes = await axios.post('/api/patient/consultation', {
        patient_id: patientInfo.patient_id,
        patient_name: patientInfo.name,
        dob: patientInfo.dob,
        session_id: sessionId,
        complaint: complaint,
        ai_response: diagnosis,
        history_report: histReport,
        images: uploadedImages,
        pdf_files: uploadedPdfs
      });

      setReviewId(submitRes.data.review_id);
      setStep('submitted');
    } catch (err) {
      console.error(err);
      alert("Error submitting consultation");
    } finally {
      setLoading(false);
    }
  };

  const renderTopBar = () => (
    <div className="topbar">
      <button className="back-btn" onClick={() => navigate('/')}>&larr; Back</button>
      <div className="brand">MediChat</div>
    </div>
  );

  const renderStepIndicator = () => {
    const steps = ['Identity', 'History', 'Assessment', 'Status'];
    const curIdx = ['identify', 'history', 'consultation', 'submitted'].indexOf(step);
    
    return (
      <div className="steps">
        {steps.map((s, i) => (
          <div key={s} style={{ display: 'flex', alignItems: 'center' }}>
            <div className={`step-item ${i < curIdx ? 'done' : i === curIdx ? 'active' : ''}`}>
              <span>{i < curIdx ? '✓' : `0${i+1}`}</span>
              <span style={{ display: i <= curIdx ? 'block' : 'none' }}>{s}</span>
            </div>
            {i < steps.length - 1 && (
              <div className={`step-separator ${i < curIdx ? 'done' : ''}`} style={{ margin: '0 1rem' }} />
            )}
          </div>
        ))}
      </div>
    );
  };

  return (
    <div>
      {renderTopBar()}
      
      <div className="page-header">
        <h1>Patient Gateway</h1>
        {renderStepIndicator()}
      </div>

      <div className="layout-grid" style={{ paddingTop: 0 }}>
        {step === 'identify' && (
          <div className="form-container">
            <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
              <button 
                className={isLoginMode ? 'btn-primary' : 'btn-outline'} 
                style={{ flex: 1, padding: '0.8rem' }}
                onClick={() => setIsLoginMode(true)}
              >
                Existing Patient
              </button>
              <button 
                className={!isLoginMode ? 'btn-primary' : 'btn-outline'} 
                style={{ flex: 1, padding: '0.8rem' }}
                onClick={() => setIsLoginMode(false)}
              >
                New Patient
              </button>
            </div>

            <h2 className="display-font" style={{ marginBottom: '2rem' }}>
              {isLoginMode ? 'Authenticate Profile' : 'Register New Profile'}
            </h2>
            <form onSubmit={handleIdentify}>
              <div className="form-group">
                <label>Full Name</label>
                <input type="text" value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Priya Sharma" required />
              </div>
              <div className="form-group">
                <label>Date of Birth</label>
                <input type="date" value={dob} onChange={e => setDob(e.target.value)} required />
              </div>
              <button type="submit" className="btn-primary" disabled={loading} style={{ width: '100%' }}>
                {loading ? 'Processing...' : (isLoginMode ? 'Access Records' : 'Create Record & Proceed')}
              </button>
            </form>
          </div>
        )}

        {step === 'history' && (
          <div>
            <div style={{ marginBottom: '2rem' }}>
              <span className="card-tag">Profile Validated</span>
              <h2 className="display-font">{patientInfo?.name}</h2>
              {patientInfo?.is_new ? (
                <div className="data-tag pending" style={{ marginTop: '1rem' }}>New Record Created in Database</div>
              ) : (
                <div className="data-tag" style={{ marginTop: '1rem' }}>Database Records Found: {patientInfo.summaries.length}</div>
              )}
            </div>
            
            <div className="data-card">
              <h3>Synthesized History</h3>
              <div style={{ whiteSpace: 'pre-wrap' }}>{histReport}</div>
            </div>

            {pastReviews.length > 0 && (
              <div className="mt-2">
                <h3 className="display-font" style={{ marginBottom: '1.5rem' }}>Archived Consultations</h3>
                {pastReviews.map((rev, i) => (
                  <div key={i} className="data-card">
                    <div className="data-tag" style={{ marginBottom: '1rem' }}>Verified</div>
                    <div style={{ padding: '1rem', background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', marginBottom: '1rem' }}>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Complaint</span>
                      <p>{rev.complaint}</p>
                    </div>
                    <div style={{ whiteSpace: 'pre-wrap' }}>{rev.finalized_response || rev.ai_response}</div>
                  </div>
                ))}
              </div>
            )}
            
            <button className="btn-primary mt-2" onClick={() => setStep('consultation')}>Proceed to Assessment</button>
          </div>
        )}

        {step === 'consultation' && (
          <div>
            <div className="form-container" style={{ maxWidth: '100%' }}>
              <h2 className="display-font" style={{ marginBottom: '2rem' }}>Input Symptomatology</h2>
              <form onSubmit={handleSubmitConsultation}>
                <div className="form-group">
                  <label>Clinical Description</label>
                  <textarea 
                    rows="8" 
                    placeholder="Provide highly specific symptom details..." 
                    value={complaint}
                    onChange={e => setComplaint(e.target.value)}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Upload Medical PDF (Lab Reports, Context)</label>
                  <input type="file" accept="application/pdf" onChange={handlePdfUpload} />
                  {uploadedPdfs.length > 0 && (
                    <div style={{ marginTop: '0.5rem', fontSize: '0.9rem', color: 'var(--accent-green)' }}>
                      Indexed: {uploadedPdfs.join(', ')}
                    </div>
                  )}
                </div>
                
                <div className="form-group">
                  <label>Upload Image (Rashes, Wounds, X-Rays)</label>
                  <input type="file" accept="image/*" onChange={handleImageUpload} />
                  {uploadedImages.length > 0 && (
                    <div style={{ marginTop: '0.5rem', fontSize: '0.9rem', color: 'var(--accent-green)' }}>
                      Images Ready: {uploadedImages.length}
                    </div>
                  )}
                </div>

                <button type="submit" className="btn-primary" disabled={loading}>
                  {loading ? 'Computing...' : 'Run Diagnostics'}
                </button>
              </form>
            </div>
          </div>
        )}

        {step === 'submitted' && (
          <div>
            <div className="data-card" style={{ borderColor: 'var(--accent-blue)' }}>
              <span className="card-tag">Queue Status</span>
              <h2 className="display-font" style={{ marginBottom: '1rem' }}>Awaiting Validation</h2>
              <p style={{ color: 'var(--text-muted)' }}>
                Diagnostics have been generated and pushed to the Doctor's queue. 
                Pending human-in-the-loop authorization.
              </p>
              <button className="btn-outline" style={{ marginTop: '2rem', padding: '0.5rem 1.5rem', cursor: 'pointer' }} onClick={() => window.location.reload()}>Refresh State</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
