import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

export default function DoctorDashboard() {
  const navigate = useNavigate();
  const [loggedIn, setLoggedIn] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  
  const [queue, setQueue] = useState([]);
  const [selectedReview, setSelectedReview] = useState(null);
  
  const [doctorNotes, setDoctorNotes] = useState('');
  const [editedResponse, setEditedResponse] = useState('');

  const [chatHistory, setChatHistory] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const res = await axios.post('/api/doctor/login', { username, password });
      if (res.data.success) {
        setLoggedIn(true);
        fetchQueue();
      }
    } catch (err) {
      alert("Invalid credentials");
    }
  };

  const fetchQueue = async () => {
    try {
      const res = await axios.get('/api/doctor/queue?status=pending');
      setQueue(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    if (loggedIn) {
      fetchQueue();
      const interval = setInterval(fetchQueue, 10000);
      return () => clearInterval(interval);
    }
  }, [loggedIn]);

  const selectReview = (rev) => {
    setSelectedReview(rev);
    setEditedResponse(rev.ai_response);
    setDoctorNotes('');
    setChatHistory([]);
    setChatInput('');
  };

  const handleAskPdf = async (e) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userMsg = { role: 'user', content: chatInput };
    setChatHistory(prev => [...prev, userMsg]);
    setChatInput('');
    setChatLoading(true);

    try {
      const res = await axios.post('/api/doctor/ask_pdf', {
        session_id: selectedReview.session_id,
        question: userMsg.content
      });
      const aiMsg = { role: 'ai', content: res.data.answer };
      setChatHistory(prev => [...prev, aiMsg]);
    } catch (err) {
      console.error(err);
      setChatHistory(prev => [...prev, { role: 'ai', content: 'Error: Could not process query.' }]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleAction = async (action) => {
    try {
      await axios.post('/api/doctor/action', {
        review_id: selectedReview.review_id,
        action: action,
        finalized_response: editedResponse,
        doctor_username: username,
        doctor_notes: doctorNotes
      });
      alert(`Consultation ${action}d successfully.`);
      setSelectedReview(null);
      fetchQueue();
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  if (!loggedIn) {
    return (
      <div>
        <div className="topbar">
          <button className="back-btn" onClick={() => navigate('/')}>&larr; Back</button>
          <div className="brand">MediChat</div>
        </div>
        
        <div className="page-header" style={{ textAlign: 'center' }}>
          <h1 className="display-font">Doctor Access</h1>
        </div>

        <div className="form-container" style={{ margin: '0 auto' }}>
          <form onSubmit={handleLogin}>
            <div className="form-group">
              <label>System Username</label>
              <input type="text" value={username} onChange={e => setUsername(e.target.value)} required />
            </div>
            <div className="form-group">
              <label>Passcode</label>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)} required />
            </div>
            <button type="submit" className="btn-primary" style={{ width: '100%' }}>Authenticate</button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="topbar">
        <button className="back-btn" onClick={() => { setLoggedIn(false); navigate('/'); }}>Disconnect</button>
        <div className="brand">System: DR_{username.toUpperCase()}</div>
      </div>

      <div className="layout-grid" style={{ paddingTop: '4rem' }}>
        <div>
          <h2 className="display-font" style={{ marginBottom: '2rem' }}>Queue [{queue.length}]</h2>
          
          {queue.length === 0 ? (
            <div className="data-card" style={{ opacity: 0.5 }}>
              No active queries in queue.
            </div>
          ) : (
            queue.map(rev => (
              <div 
                key={rev.review_id} 
                className="data-card"
                style={{ 
                  cursor: 'pointer', 
                  borderColor: selectedReview?.review_id === rev.review_id ? 'var(--accent-blue)' : 'var(--border-subtle)',
                  transition: 'all 0.3s'
                }}
                onClick={() => selectReview(rev)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <strong className="display-font" style={{ fontSize: '1.2rem' }}>{rev.patient_name}</strong>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontFamily: 'Space Grotesk' }}>
                      TS: {new Date(rev.created_at).toISOString()}
                    </div>
                  </div>
                  <span className="data-tag pending">Pending</span>
                </div>
              </div>
            ))
          )}
        </div>

        <div>
          {selectedReview ? (
            <div className="data-card" style={{ background: 'var(--bg-base)' }}>
              <h3 className="display-font" style={{ fontSize: '1.5rem', marginBottom: '2rem', color: 'var(--text-main)' }}>Validation Interface</h3>
              
              <div className="form-group">
                <label>Patient Context</label>
                <div style={{ background: 'var(--bg-surface)', padding: '1rem', border: '1px solid var(--border-subtle)' }}>
                  {selectedReview.patient_name}
                </div>
              </div>
              
              <div className="form-group">
                <label>Input Symptomatology</label>
                <div style={{ background: 'var(--bg-surface)', padding: '1rem', border: '1px solid var(--border-subtle)' }}>
                  {selectedReview.complaint}
                </div>
              </div>

              {selectedReview.pdf_files && selectedReview.pdf_files.length > 0 && (
                <div className="form-group">
                  <label>Attached Medical Documents</label>
                  <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                    {selectedReview.pdf_files.map((pdf, idx) => (
                      <a 
                        key={idx}
                        href={`/api/patient/download_pdf/${selectedReview.session_id}/${pdf}`}
                        target="_blank"
                        rel="noreferrer"
                        className="data-tag"
                        style={{ color: 'var(--accent-blue)', textDecoration: 'none', border: '1px solid var(--accent-blue)' }}
                      >
                        📄 Download {pdf}
                      </a>
                    ))}
                  </div>

                  {/* Document Q&A Panel */}
                  <div style={{ marginTop: '1.5rem', background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '4px' }}>
                    <div style={{ padding: '0.8rem 1rem', borderBottom: '1px solid var(--border-subtle)', background: 'rgba(255,255,255,0.02)' }}>
                      <strong style={{ fontSize: '0.9rem', color: 'var(--text-main)' }}>Document Q&A Assistant</strong>
                    </div>
                    
                    <div style={{ padding: '1rem', maxHeight: '200px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                      {chatHistory.length === 0 ? (
                        <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', fontStyle: 'italic' }}>
                          Ask a specific question about the attached documents...
                        </div>
                      ) : (
                        chatHistory.map((msg, idx) => (
                          <div key={idx} style={{ textAlign: msg.role === 'user' ? 'right' : 'left' }}>
                            <div style={{ 
                              display: 'inline-block', 
                              padding: '0.6rem 1rem', 
                              borderRadius: '4px',
                              fontSize: '0.9rem',
                              background: msg.role === 'user' ? 'var(--accent-blue)' : 'rgba(255,255,255,0.05)',
                              color: msg.role === 'user' ? '#000' : 'var(--text-main)',
                              maxWidth: '80%'
                            }}>
                              {msg.content}
                            </div>
                          </div>
                        ))
                      )}
                      {chatLoading && <div style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>Analyzing document...</div>}
                    </div>

                    <form onSubmit={handleAskPdf} style={{ display: 'flex', borderTop: '1px solid var(--border-subtle)' }}>
                      <input 
                        type="text" 
                        value={chatInput} 
                        onChange={e => setChatInput(e.target.value)} 
                        placeholder="e.g. What is the patient's HbA1c level?"
                        style={{ flex: 1, border: 'none', background: 'transparent', padding: '1rem', outline: 'none', color: 'var(--text-main)' }}
                      />
                      <button type="submit" style={{ padding: '0 1.5rem', background: 'transparent', border: 'none', color: 'var(--accent-blue)', cursor: 'pointer', fontWeight: 'bold' }}>
                        Ask
                      </button>
                    </form>
                  </div>
                </div>
              )}

              {selectedReview.images && selectedReview.images.length > 0 && (
                <div className="form-group">
                  <label>Attached Imagery</label>
                  <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                    {selectedReview.images.map((img, idx) => (
                      <img 
                        key={idx} 
                        src={`data:${img.mime_type};base64,${img.data}`} 
                        alt="Patient Upload" 
                        style={{ maxWidth: '300px', maxHeight: '300px', border: '1px solid var(--border-subtle)', borderRadius: '4px' }} 
                      />
                    ))}
                  </div>
                </div>
              )}

              <div className="form-group">
                <label>AI Draft Output (Editable)</label>
                <textarea 
                  style={{ height: '350px' }}
                  value={editedResponse}
                  onChange={e => setEditedResponse(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Doctor Appended Notes</label>
                <textarea 
                  style={{ height: '100px' }}
                  value={doctorNotes}
                  onChange={e => setDoctorNotes(e.target.value)}
                  placeholder="Internal notes or patient-facing additions..."
                />
              </div>

              <div style={{ display: 'flex', gap: '1rem', marginTop: '2rem' }}>
                <button 
                  className="btn-primary" 
                  onClick={() => handleAction('approve')}
                  style={{ flex: 1 }}
                >
                  Authorize
                </button>
                <button 
                  className="btn-outline" 
                  onClick={() => handleAction('reject')}
                  style={{ flex: 1, padding: '1rem', cursor: 'pointer' }}
                >
                  Reject
                </button>
              </div>
            </div>
          ) : (
            <div className="data-card" style={{ opacity: 0.5 }}>
              Select a node from the queue to initialize validation protocol.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
