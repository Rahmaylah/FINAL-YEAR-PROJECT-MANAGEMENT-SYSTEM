import React, { useContext, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import axios from '../services/axiosConfig';
import '../styles/Dashboard.css';
import nitLogo from '../assets/nit.png';

function StudentDashboard() {
  const { user, logout } = useContext(AuthContext);
  const navigate = useNavigate();
  const [mentor, setMentor] = useState(null);
  const [mentorExpanded, setMentorExpanded] = useState(false);
  const [project, setProject] = useState(null);
  const [presentationResults, setPresentationResults] = useState([]);
  const [presentationDetails, setPresentationDetails] = useState({});
  const [presentationCriteria, setPresentationCriteria] = useState({});
  const [projectTypes, setProjectTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [passwordMessage, setPasswordMessage] = useState('');
  const [profile, setProfile] = useState({
    first_name: '',
    middle_name: '',
    last_name: '',
    email: '',
    username: '',
    role: ''
  });
  const [profileDraft, setProfileDraft] = useState({ middle_name: '', email: '' });
  const [profileExpanded, setProfileExpanded] = useState(false);
  const [presentationsExpanded, setPresentationsExpanded] = useState(false);
  const [projectDocumentsExpanded, setProjectDocumentsExpanded] = useState(false);
  const [showDocumentForm, setShowDocumentForm] = useState(false);
  const [documentUploadName, setDocumentUploadName] = useState('');
  const [documentUploadDescription, setDocumentUploadDescription] = useState('');
  const [documentUploadFile, setDocumentUploadFile] = useState(null);
  const [documentUploadLoading, setDocumentUploadLoading] = useState(false);
  const [documentUploadMessage, setDocumentUploadMessage] = useState('');
  const [editingProfile, setEditingProfile] = useState(false);
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileMessage, setProfileMessage] = useState('');

  // Similar projects states
  const [similarProjects, setSimilarProjects] = useState([]);
  const [similarProjectsExpanded, setSimilarProjectsExpanded] = useState(false);
  const [loadingSimilar, setLoadingSimilar] = useState(false);
  const [similarError, setSimilarError] = useState('');
  const [duplicateCheckLoading, setDuplicateCheckLoading] = useState(false);

  // Criteria details expanded state
  const [expandedResultDetails, setExpandedResultDetails] = useState({});

  // Form state for editing
  const [formData, setFormData] = useState({
    title: '',
    project_type: '',
    main_objective: '',
    specific_objectives: '',
    project_description: '',
    implementation_details: ''
  });

  // Image error fallback
  const [imageError, setImageError] = useState(false);

  // Fetch project types from database
  useEffect(() => {
    const fetchProjectTypes = async () => {
      try {
        const response = await axios.get('/api/project-types/');
        setProjectTypes(response.data.results || response.data);
      } catch (error) {
        console.error('Error fetching project types:', error);
      }
    };
    fetchProjectTypes();
  }, []);

  useEffect(() => {
    if (!user) return;

    setProfile({
      first_name: user.first_name || '',
      middle_name: user.middle_name || '',
      last_name: user.last_name || '',
      email: user.email || '',
      username: user.username || '',
      role: user.role || ''
    });
    setProfileDraft({
      middle_name: user.middle_name || '',
      email: user.email || ''
    });
  }, [user]);

  // ============================================================
  // FETCH PROJECT WITH INDIVIDUAL API CALL FOR FRESH DATA
  // ============================================================
  const fetchFreshProjectData = async () => {
    try {
      const projectsResponse = await axios.get('/api/projects/');
      console.log('🔍 === PROJECTS API RESPONSE ===');
      console.log('Results:', projectsResponse.data.results);

      if (projectsResponse.data.results && projectsResponse.data.results.length > 0) {
        const projectData = projectsResponse.data.results[0];
        
        // ====== FETCH INDIVIDUAL PROJECT FOR FRESH DATA ======
        const individualResponse = await axios.get(`/api/projects/${projectData.id}/`);
        console.log('📌 Individual Project Response:', individualResponse.data);
        console.log('💬 mentor_comment from individual:', individualResponse.data.mentor_comment);
        
        return individualResponse.data;
      }
      return null;
    } catch (error) {
      console.error('Error fetching fresh project data:', error);
      return null;
    }
  };

  // Fetch projects and mentor info
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        // ====== FETCH FRESH PROJECT DATA ======
        const freshProjectData = await fetchFreshProjectData();

        if (freshProjectData) {
          console.log('📌 === SETTING PROJECT WITH FRESH DATA ===');
          console.log('💬 mentor_comment:', freshProjectData.mentor_comment);
          setProject(freshProjectData);
          
          // Initialize form with existing project data
          setFormData({
            title: freshProjectData.title || '',
            project_type: freshProjectData.project_type?.id || freshProjectData.project_type || '',
            main_objective: freshProjectData.main_objective || '',
            specific_objectives: freshProjectData.specific_objectives?.join('--') || '',
            project_description: freshProjectData.project_description || '',
            implementation_details: freshProjectData.implementation_details || ''
          });
        } else {
          console.log('⚠️ No project found for this student');
          setProject(null);
          // Reset form for new project
          setFormData({
            title: '',
            project_type: '',
            main_objective: '',
            specific_objectives: '',
            project_description: '',
            implementation_details: ''
          });
          // Clear similar projects if no project
          setSimilarProjects([]);
          setSimilarError('');
          setSimilarProjectsExpanded(false);
        }

        // Set mentor info from user - using mentor_info if available
        if (user?.mentor_info) {
          setMentor(user.mentor_info);
        } else if (user?.mentor) {
          // If only mentor ID is available, fetch the mentor details
          try {
            const mentorResponse = await axios.get(`/api/users/${user.mentor}/`);
            setMentor(mentorResponse.data);
          } catch (err) {
            console.error('Error fetching mentor details:', err);
            setMentor(null);
          }
        } else {
          setMentor(null);
        }

        // Fetch presentation results with details
        try {
          const resultResponse = await axios.get('/api/presentation-results/', {
            params: { student: user.id }
          });
          const results = resultResponse.data.results || resultResponse.data || [];
          
          // Fetch presentation details and criteria for each result
          const resultsWithDetails = [];
          const presDetails = {};
          const presCriteria = {};

          for (const result of results) {
            // Fetch presentation details
            try {
              const presResponse = await axios.get(`/api/presentations/${result.presentation}/`);
              presDetails[result.presentation] = presResponse.data;
              
              // Fetch criteria for this presentation
              try {
                const criteriaResponse = await axios.get(`/api/presentation-criteria/?presentation=${result.presentation}`);
                const criteria = criteriaResponse.data.results || criteriaResponse.data || [];
                presCriteria[result.presentation] = criteria;
              } catch (critErr) {
                console.error('Error fetching criteria:', critErr);
                presCriteria[result.presentation] = [];
              }
            } catch (presErr) {
              console.error('Error fetching presentation details:', presErr);
            }
            
            resultsWithDetails.push(result);
          }

          setPresentationDetails(presDetails);
          setPresentationCriteria(presCriteria);
          
          const sortedResults = [...resultsWithDetails].sort((a, b) => {
            const aDate = a.created_at ? new Date(a.created_at).getTime() : 0;
            const bDate = b.created_at ? new Date(b.created_at).getTime() : 0;
            return aDate - bDate;
          });
          setPresentationResults(sortedResults);
        } catch (error) {
          console.error('Error fetching presentation results:', error);
          setPresentationResults([]);
        }
      } catch (error) {
        console.error('Error fetching data:', error);
      } finally {
        setLoading(false);
      }
    };

    if (user) {
      fetchData();
    }
  }, [user]);

  // Function to fetch similar projects using duplicate-flags endpoint
  const fetchSimilarProjects = async () => {
    // Only fetch if project exists
    if (!project || !project.id) {
      setSimilarProjects([]);
      setSimilarError('No project to compare');
      setSimilarProjectsExpanded(false);
      return;
    }

    setLoadingSimilar(true);
    setSimilarError('');
    setSimilarProjects([]);

    try {
      const flagsResponse = await axios.get(`/api/duplicate-flags/?project=${project.id}`);

      let flags = [];
      if (flagsResponse.data.results) {
        flags = flagsResponse.data.results;
      } else if (Array.isArray(flagsResponse.data)) {
        flags = flagsResponse.data;
      }

      if (flags.length === 0) {
        setSimilarProjects([]);
        setSimilarError('No similar projects found');
        setSimilarProjectsExpanded(true);
        setLoadingSimilar(false);
        return;
      }

      const similarProjectsData = [];
      for (const flag of flags) {
        try {
          const projectResponse = await axios.get(`/api/projects/${flag.similar_project}/`);
          const projectData = projectResponse.data;
          
          let mentorName = 'N/A';
          let mentorComment = null;
          
          // Check if project has mentor_info
          if (projectData.mentor_info) {
            mentorName = `${projectData.mentor_info.first_name || ''} ${projectData.mentor_info.last_name || ''}`.trim() || 'Mentor';
          }
          
          // Check for mentor comment from flag or project data
          if (flag.mentor_comment) {
            mentorComment = flag.mentor_comment;
          } else if (projectData.mentor_comment) {
            mentorComment = projectData.mentor_comment;
          }

          let authorName = 'Unknown';
          if (projectData.author_name) {
            authorName = projectData.author_name;
          } else if (projectData.student_name) {
            authorName = projectData.student_name;
          } else if (projectData.user) {
            // If user is an object, get name
            if (typeof projectData.user === 'object' && projectData.user !== null) {
              const userObj = projectData.user;
              const nameParts = [userObj.first_name || '', userObj.middle_name || '', userObj.last_name || ''];
              authorName = nameParts.filter(Boolean).join(' ') || userObj.username || 'Unknown';
            } else {
              authorName = String(projectData.user);
            }
          }

          similarProjectsData.push({
            id: projectData.id,
            title: projectData.title || 'Untitled Project',
            description: projectData.project_description || projectData.description || '',
            author_name: authorName,
            mentor: mentorName,
            mentor_comment: mentorComment,
            similarity_score: flag.similarity_score ? `${(flag.similarity_score * 100).toFixed(1)}%` : 'N/A',
            status: projectData.status || 'N/A',
            flag_id: flag.id,
            reviewed: flag.reviewed || false,
            year: projectData.year || 'N/A',
            project_type_name: projectData.project_type_name || projectData.project_type?.name || 'N/A'
          });
        } catch (err) {
          // Handle 404 gracefully - project might be deleted or inaccessible
          if (err.response && err.response.status === 404) {
            console.warn(`⚠️ Project ${flag.similar_project} not found, skipping...`);
          } else {
            console.error(`Error fetching project ${flag.similar_project}:`, err);
          }
        }
      }

      setSimilarProjects(similarProjectsData);
      if (similarProjectsData.length === 0) {
        setSimilarError('Could not load similar projects');
      }
      setSimilarProjectsExpanded(true);
    } catch (error) {
      console.error('Error fetching similar projects:', error);
      if (error.response) {
        if (error.response.status === 404) {
          setSimilarError('Similar projects endpoint not found');
        } else if (error.response.status === 403) {
          setSimilarError('You do not have permission to view similar projects');
        } else {
          setSimilarError(`Error: ${error.response.status} - ${error.response.statusText}`);
        }
      } else if (error.request) {
        setSimilarError('Network error. Please check your connection.');
      } else {
        setSimilarError('An unexpected error occurred');
      }
      setSimilarProjects([]);
    } finally {
      setLoadingSimilar(false);
    }
  };

  // ============================================================
  // Force duplicate check function
  // ============================================================
  const handleForceDuplicateCheck = async () => {
    if (!project || !project.id) {
      alert('⚠️ Please save your project first.');
      return;
    }

    setDuplicateCheckLoading(true);
    try {
      const response = await axios.post(`/api/projects/${project.id}/duplicate_check/`);
      console.log('Duplicate check result:', response.data);
      
      // Refresh project data to get updated status
      const freshData = await fetchFreshProjectData();
      if (freshData) {
        setProject(freshData);
      }
      
      alert('✅ Duplicate check completed successfully!');
      
      // Refresh similar projects
      await fetchSimilarProjects();
    } catch (error) {
      console.error('Error checking duplicates:', error);
      alert('❌ Error checking duplicates. Please try again.');
    } finally {
      setDuplicateCheckLoading(false);
    }
  };

  // Toggle expanded details for a presentation result
  const toggleResultDetails = (resultId) => {
    setExpandedResultDetails(prev => ({
      ...prev,
      [resultId]: !prev[resultId]
    }));
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleProfileDraftChange = (event) => {
    const { name, value } = event.target;
    setProfileDraft((prev) => ({ ...prev, [name]: value }));
  };

  const handleSaveProfile = async () => {
    if (!user || !user.id) return;
    setProfileSaving(true);
    setProfileMessage('');

    try {
      const response = await axios.patch(`/api/users/${user.id}/`, profileDraft);
      setProfile((prev) => ({ ...prev, ...response.data }));
      setProfileDraft({
        middle_name: response.data.middle_name || '',
        email: response.data.email || ''
      });
      setEditingProfile(false);
      setProfileMessage('✅ Profile updated successfully.');
      localStorage.setItem('user', JSON.stringify({ ...user, ...response.data }));
    } catch (error) {
      console.error('Error saving profile:', error);
      setProfileMessage('❌ Unable to update profile. Please try again.');
    } finally {
      setProfileSaving(false);
    }
  };

  const handlePasswordChange = (event) => {
    const { name, value } = event.target;
    setPasswordData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSavePassword = async () => {
    if (!user || !user.id) return;
    setPasswordSaving(true);
    setPasswordMessage('');

    if (passwordData.new_password !== passwordData.confirm_password) {
      setPasswordMessage('❌ New passwords do not match.');
      setPasswordSaving(false);
      return;
    }

    if (passwordData.new_password.length < 8) {
      setPasswordMessage('❌ New password must be at least 8 characters long.');
      setPasswordSaving(false);
      return;
    }

    try {
      const response = await axios.post('/api/users/set_password/', {
        current_password: passwordData.current_password,
        new_password: passwordData.new_password
      });
      setPasswordMessage('✅ Password changed successfully.');
      setPasswordData({
        current_password: '',
        new_password: '',
        confirm_password: ''
      });
    } catch (error) {
      console.error('Error changing password:', error);
      if (error.response && error.response.data) {
        if (error.response.data.error) {
          setPasswordMessage(`❌ ${error.response.data.error}`);
        } else if (error.response.data.detail) {
          setPasswordMessage(`❌ ${error.response.data.detail}`);
        } else {
          setPasswordMessage('❌ Unable to change password. Please try again.');
        }
      } else if (error.message) {
        setPasswordMessage(`❌ Network error: ${error.message}`);
      } else {
        setPasswordMessage('❌ Unable to change password. Please try again.');
      }
    } finally {
      setPasswordSaving(false);
    }
  };

  const handleEditClick = () => {
    setIsEditing(true);
  };

  const handleCancel = () => {
    setIsEditing(false);
    if (project) {
      setFormData({
        title: project.title || '',
        project_type: project.project_type?.id || project.project_type || '',
        main_objective: project.main_objective || '',
        specific_objectives: project.specific_objectives?.join('--') || '',
        project_description: project.project_description || '',
        implementation_details: project.implementation_details || ''
      });
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSave = async () => {
    try {
      const specificObjArray = formData.specific_objectives
        ? formData.specific_objectives.split('--').map(obj => obj.trim()).filter(obj => obj)
        : [];

      const projectData = {
        title: formData.title,
        project_type: formData.project_type || null,
        main_objective: formData.main_objective,
        specific_objectives: specificObjArray,
        project_description: formData.project_description,
        implementation_details: formData.implementation_details,
        year: new Date().getFullYear(),
        status: 'proposed'
      };

      let response;
      if (project && project.id) {
        response = await axios.put(`/api/projects/${project.id}/`, projectData);
      } else {
        response = await axios.post('/api/projects/', projectData);
      }

      setProject(response.data);
      setIsEditing(false);
      alert('✅ Project saved successfully!');
      
      // Refresh similar projects after save
      if (response.data.id) {
        setTimeout(() => {
          fetchSimilarProjects();
        }, 1000);
      }
    } catch (error) {
      console.error('Error saving project:', error);
      alert('❌ Error saving project. Please try again.');
    }
  };

  const resetDocumentForm = () => {
    setDocumentUploadName('');
    setDocumentUploadDescription('');
    setDocumentUploadFile(null);
    setDocumentUploadMessage('');
  };

  const handleOpenDocumentForm = () => {
    resetDocumentForm();
    setShowDocumentForm(true);
  };

  const handleCloseDocumentForm = () => {
    setShowDocumentForm(false);
    resetDocumentForm();
  };

  const handleDocumentFileChange = (event) => {
    const file = event.target.files[0];
    if (file) {
      const fileType = file.type;
      const fileExtension = file.name.split('.').pop().toLowerCase();
      
      if (fileType !== 'application/pdf' && fileExtension !== 'pdf') {
        setDocumentUploadMessage('❌ Only PDF files are allowed. Please select a PDF document.');
        setDocumentUploadFile(null);
        event.target.value = '';
        return;
      }
      
      const maxSize = 10 * 1024 * 1024;
      if (file.size > maxSize) {
        setDocumentUploadMessage(`❌ File size (${(file.size / (1024 * 1024)).toFixed(2)}MB) exceeds the maximum limit of 10MB.`);
        setDocumentUploadFile(null);
        event.target.value = '';
        return;
      }
      
      setDocumentUploadFile(file);
      setDocumentUploadMessage('');
    }
  };

  const handleUploadDocument = async () => {
    if (!project || !project.id) {
      setDocumentUploadMessage('❌ Please save your project before uploading a document.');
      return;
    }

    if (!documentUploadFile) {
      setDocumentUploadMessage('❌ Please select a PDF file to upload.');
      return;
    }

    const fileType = documentUploadFile.type;
    const fileExtension = documentUploadFile.name.split('.').pop().toLowerCase();
    
    if (fileType !== 'application/pdf' && fileExtension !== 'pdf') {
      setDocumentUploadMessage('❌ Only PDF files are allowed.');
      return;
    }

    const maxSize = 10 * 1024 * 1024;
    if (documentUploadFile.size > maxSize) {
      setDocumentUploadMessage(`❌ File size exceeds the maximum limit of 10MB. Current file: ${(documentUploadFile.size / (1024 * 1024)).toFixed(2)}MB`);
      return;
    }

    setDocumentUploadLoading(true);
    setDocumentUploadMessage('');

    try {
      const formData = new FormData();
      formData.append('name', documentUploadName.trim() || documentUploadFile.name);
      formData.append('description', documentUploadDescription);
      formData.append('file', documentUploadFile);

      const response = await axios.post(`/api/projects/${project.id}/upload_document/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      setProject((prev) => prev ? {
        ...prev,
        documents: [...(prev.documents || []), response.data]
      } : prev);
      setDocumentUploadMessage('✅ Document uploaded successfully.');
      setTimeout(() => {
        handleCloseDocumentForm();
      }, 1500);
    } catch (error) {
      console.error('Error uploading document:', error);
      setDocumentUploadMessage('❌ Unable to upload document. Please try again.');
    } finally {
      setDocumentUploadLoading(false);
    }
  };

  // Calculate total marks from criteria scores
  const calculateTotalFromCriteria = (result) => {
    if (!result.criteria_scores || result.criteria_scores.length === 0) {
      return result.marks || 'N/A';
    }
    
    let total = 0;
    let totalWeight = 0;
    
    result.criteria_scores.forEach(cs => {
      if (cs.score !== null && cs.score !== undefined) {
        const normalizedScore = (cs.score / cs.criteria_max_score) * 100;
        total += normalizedScore * cs.criteria_weight;
        totalWeight += cs.criteria_weight;
      }
    });
    
    if (totalWeight > 0) {
      return (total / totalWeight).toFixed(2);
    }
    return result.marks || 'N/A';
  };

  return (
    <div className="dashboard-container student-dashboard">
      {/* App Bar */}
      <nav className="navbar navbar-expand-lg navbar-light bg-white fixed-top">
        <div className="container-fluid">
          <span className="navbar-brand d-flex align-items-center">
            {!imageError ? (
              <img 
                src={nitLogo} 
                alt="NIT Logo" 
                style={{ width: 40, height: 40, marginRight: 8 }}
                onError={() => setImageError(true)}
              />
            ) : (
              <span style={{ 
                width: 40, height: 40, marginRight: 8, 
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                background: '#0d6efd', color: 'white', borderRadius: '4px',
                fontWeight: 'bold', fontSize: '14px'
              }}>NIT</span>
            )}
            <span>FYPMS Portal</span>
          </span>
          <div className="dropdown ms-auto" style={{ cursor: 'pointer' }}>
            <div
              style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
              onClick={() => setShowUserMenu((prev) => !prev)}
              id="userMenuButton"
              aria-expanded={showUserMenu}
            >
              <span style={{ fontSize: '1rem', color: '#333' }}>
                {profile?.username || user?.username || 'Student'}
              </span>
              <span style={{ fontSize: '0.8rem', color: '#666', transform: showUserMenu ? 'rotate(180deg)' : 'rotate(90deg)', transition: 'transform 0.3s ease', display: 'inline-block' }}>
                Λ
              </span>
            </div>
            <ul className={`dropdown-menu ${showUserMenu ? 'show' : ''}`} style={{ minWidth: '140px', position: 'fixed', right: '0', top: '70px', marginRight: '10px', padding: '5px 0' }} aria-labelledby="userMenuButton">
              <li>
                <button className="dropdown-item" style={{ fontSize: '0.9rem', padding: '5px 10px' }} onClick={() => { setProfileExpanded(true); setShowUserMenu(false); }}>
                  Profile
                </button>
              </li>
              <li>
                <button className="dropdown-item" style={{ fontSize: '0.9rem', padding: '5px 10px' }} onClick={() => { setShowChangePassword(true); setShowUserMenu(false); setPasswordMessage(''); }}>
                  Change Password
                </button>
              </li>
              <li><hr className="dropdown-divider" style={{ margin: '4px 0' }} /></li>
              <li>
                <button className="dropdown-item" style={{ fontSize: '0.9rem', padding: '5px 10px' }} onClick={handleLogout}>
                  Logout
                </button>
              </li>
            </ul>
          </div>
        </div>
      </nav>

      <div className="container mt-2" style={{ paddingTop: '10px' }}>
        {/* Card 1: Mentor Information */}
        <div className="card dashboard-card mb-4">
          <div className="card-body">
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              cursor: mentor ? 'pointer' : 'default'
            }} onClick={() => mentor && setMentorExpanded(!mentorExpanded)}>
              <div style={{ display: 'flex', alignItems: 'baseline', flexWrap: 'wrap', gap: '8px' }}>
                <h5 className="card-title" style={{ marginBottom: 0 }}>
                  👨‍🏫 Mentor: {loading ? 'Loading...' : mentor ? `${mentor.first_name} ${mentor.last_name}` : 'Not assigned'}
                </h5>
                {mentor && <small className="text-muted d-block d-md-inline">{mentor.email}</small>}
              </div>
              {mentor && (
                <span style={{
                  fontSize: '1.0em',
                  color: '#474d53',
                  transform: mentorExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                  transition: 'transform 0.1s ease'
                }}>
                  ▶
                </span>
              )}
            </div>

            {mentorExpanded && mentor && (
              <>
                <div>                  
                  {mentor?.students && mentor.students.length > 0 && (
                    <>
                      <hr />
                      <h6><strong>👥 Fellow mentees:</strong></h6>
                      <ul className="list-group list-group-flush">
                        {mentor.students
                          .filter(student => student.id !== user?.id)
                          .map(student => (
                          <li key={student.id} className="list-group-item d-flex justify-content-between align-items-center">
                            <div>
                              <strong>Fullname: {student.first_name} {student.last_name}</strong><br />
                              <strong>Registration Number: {student.registration_number}</strong>
                              <small className="text-muted d-block d-md-inline ms-md-2">{student.email}</small>
                            </div>
                          </li>
                        ))}
                      </ul>
                    </>
                  )}
                </div>
              </>
            )}
          </div>
        </div>

        {/* Card 2: Project Information */}
        <div className="card dashboard-card">
          <div className="card-body">
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginBottom: '20px', flexWrap: 'wrap' }}>
              {/* Duplicate Check Button - Only show if project exists */}
              {project && project.id && (
                <button 
                  className="btn btn-outline-warning"
                  onClick={handleForceDuplicateCheck}
                  disabled={duplicateCheckLoading}
                >
                  {duplicateCheckLoading ? '⏳ Checking...' : '🔍 Check Duplicates'}
                </button>
              )}
              
              {isEditing ? (
                <>
                  <button className="btn btn-success" onClick={handleSave}>
                    💾 Save
                  </button>
                  <button className="btn btn-secondary" onClick={handleCancel}>
                    ✕ Cancel
                  </button>
                </>
              ) : (
                <button
                  className={`btn ${project ? 'btn-primary' : 'btn-success'}`}
                  onClick={handleEditClick}
                >
                  {project ? '✏️ Edit project' : '➕ Add project'}
                </button>
              )}
            </div>

            {isEditing ? (
              <form>
                <div className="mb-3">
                  <label className="form-label"><strong>Project Title</strong></label>
                  <input
                    type="text"
                    className="form-control"
                    name="title"
                    value={formData.title}
                    onChange={handleInputChange}
                    placeholder="Enter project title"
                  />
                </div>

                <div className="mb-3">
                  <label className="form-label"><strong>Project Type</strong></label>
                  <select
                    className="form-select"
                    name="project_type"
                    value={formData.project_type}
                    onChange={handleInputChange}
                  >
                    <option value="">Select a project type</option>
                    {projectTypes.map((type) => (
                      <option key={type.id} value={type.id}>
                        {type.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="mb-3">
                  <label className="form-label"><strong>Main Objective</strong></label>
                  <textarea
                    className="form-control"
                    name="main_objective"
                    value={formData.main_objective}
                    onChange={handleInputChange}
                    rows="2"
                    placeholder="Enter main objective"
                  />
                </div>

                <div className="mb-3">
                  <label className="form-label"><strong>Specific Objectives</strong></label>
                  <textarea
                    className="form-control"
                    name="specific_objectives"
                    value={formData.specific_objectives}
                    onChange={handleInputChange}
                    rows="3"
                    placeholder="Enter objectives separated by -- (double hyphen)"
                  />
                  <small className="text-muted">Separate each objective with -- (double hyphen)</small>
                </div>

                <div className="mb-3">
                  <label className="form-label"><strong>Project Description</strong></label>
                  <textarea
                    className="form-control"
                    name="project_description"
                    value={formData.project_description}
                    onChange={handleInputChange}
                    rows="3"
                    placeholder="Enter project description"
                  />
                </div>

                <div className="mb-3">
                  <label className="form-label"><strong>Implementation Details</strong></label>
                  <textarea
                    className="form-control"
                    name="implementation_details"
                    value={formData.implementation_details}
                    onChange={handleInputChange}
                    rows="3"
                    placeholder="Enter implementation details"
                  />
                </div>
              </form>
            ) : project ? (
              <div>
                <div className="mb-3">
                  <h5><strong>📌 Title: {project.title}</strong></h5>
                </div>

                <div className="mb-2">
                  <label className="form-label"><strong>Project Type:</strong></label>
                  <p>{project.project_type_name || project.project_type?.name || project.project_type || 'Not specified'}</p>
                </div>

                <div className="mb-2">
                  <label className="form-label"><strong>Main Objective:</strong></label>
                  <p>{project.main_objective || 'Not specified'}</p>
                </div>

                <div className="mb-2">
                  <label className="form-label"><strong>Specific Objectives:</strong></label>
                  {project.specific_objectives && project.specific_objectives.length > 0 ? (
                    <ul>
                      {project.specific_objectives.map((obj, idx) => (
                        <li key={idx}>{obj}</li>
                      ))}
                    </ul>
                  ) : (
                    <p>Not specified</p>
                  )}
                </div>

                <div className="mb-2">
                  <label className="form-label"><strong>Project Description:</strong></label>
                  <p>{project.project_description || 'Not specified'}</p>
                </div>

                <div className="mb-2">
                  <label className="form-label"><strong>Implementation Details:</strong></label>
                  <p>{project.implementation_details || 'Not specified'}</p>
                </div>

                {/* ====== STATUS NA MENTOR COMMENT ====== */}
                <div className="mb-2">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                    <label className="form-label"><strong>Status: </strong></label>                  
                    <span className={`badge ${project.status === 'approved' ? 'bg-success' : project.status === 'rejected' ? 'bg-danger' : project.status === 'completed' ? 'bg-info' : 'bg-secondary'}`}>
                      {project.status}
                    </span>
                    {project.is_flagged_duplicate && (
                      <span className="badge bg-warning text-dark">⚠️ Flagged as Duplicate</span>
                    )}
                  </div>
                  
                  {/* ====== DEBUGGING CONSOLE.LOG ====== */}
                  {console.log('🔍 === RENDERING MENTOR COMMENT ===')}
                  {console.log('🔍 project.mentor_comment value:', project.mentor_comment)}
                  {console.log('🔍 project.mentor_comment type:', typeof project.mentor_comment)}
                  {console.log('🔍 Is it truthy?', !!project.mentor_comment)}
                  {console.log('🔍 Is it not empty?', project.mentor_comment && project.mentor_comment.trim() !== '')}
                  
                  {/* ====== MENTOR COMMENT - Inaonyeshwa hapa chini ya status ====== */}
                  {project.mentor_comment && project.mentor_comment.trim() !== '' && (
                    <div className="mt-3 p-3 bg-light rounded border-start border-primary border-4">
                      <strong>💬 Mentor Comment:</strong>
                      <p className="mb-0 mt-1" style={{ whiteSpace: 'pre-wrap' }}>{project.mentor_comment}</p>
                    </div>
                  )}
                </div>
                {/* ====== END STATUS NA MENTOR COMMENT ====== */}
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '40px 0' }}>
                <h5>📝 No Project Submitted Yet</h5>
                <p>Click the "Add Project" button above to submit your first project.</p>
              </div>
            )}
          </div>
        </div>

        {/* Card 3: Similar Projects */}
        {project && (
          <div className="card dashboard-card mt-4">
            <div className="card-body">
              <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center', 
                cursor: 'pointer' 
              }} 
              onClick={() => {
                if (!similarProjectsExpanded) {
                  fetchSimilarProjects();
                } else {
                  setSimilarProjectsExpanded(false);
                }
              }}>
                <h5>🔍 Similar Projects</h5>
                <div className="d-flex align-items-center gap-2">
                  {similarProjectsExpanded && similarProjects.length > 0 && (
                    <span className="badge bg-info">{similarProjects.length} found</span>
                  )}
                  <span style={{
                    fontSize: '1.0em',
                    color: '#474d53',
                    transform: similarProjectsExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                    transition: 'transform 0.1s ease'
                  }}>
                    ▶
                  </span>
                </div>
              </div>
              
              {similarProjectsExpanded && (
                <div className="mt-3">
                  {loadingSimilar ? (
                    <div className="text-center py-4">
                      <div className="spinner-border text-primary" role="status">
                        <span className="visually-hidden">Loading...</span>
                      </div>
                      <p className="mt-2 text-muted">Searching for similar projects...</p>
                    </div>
                  ) : similarProjects.length > 0 ? (
                    similarProjects.map((simProject) => (
                      <div key={simProject.id} className="card mb-3 shadow-sm border-start border-primary border-4">
                        <div className="card-body py-3 px-3">
                          <div className="d-flex justify-content-between align-items-start flex-wrap">
                            <h6 className="card-title mb-1">{simProject.title}</h6>
                            <span className="badge bg-primary">{simProject.similarity_score}</span>
                          </div>
                          
                          <div className="mb-2">
                            <small className="text-muted">
                              👤 Author: {simProject.author_name || 'Unknown'} | 
                              📅 Year: {simProject.year || 'N/A'} | 
                              📂 {simProject.project_type_name}
                            </small>
                          </div>
                          
                          {simProject.description && (
                            <p className="mb-2 small text-muted">
                              {simProject.description.length > 200 
                                ? `${simProject.description.substring(0, 200)}...` 
                                : simProject.description}
                            </p>
                          )}
                          
                          {/* Show mentor name if available */}
                          {simProject.mentor && simProject.mentor !== 'N/A' && (
                            <div className="mt-1">
                              <small className="text-muted">👨‍🏫 Mentor: {simProject.mentor}</small>
                            </div>
                          )}
                          
                          <div className="mt-2">
                            <span className={`badge ${simProject.status === 'approved' ? 'bg-success' : simProject.status === 'completed' ? 'bg-info' : 'bg-secondary'}`}>
                              Status: {simProject.status}
                            </span>
                            {simProject.reviewed && (
                              <span className="badge bg-warning text-dark ms-2">✓ Reviewed</span>
                            )}
                          </div>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-4">
                      <p className="text-muted">
                        {similarError || 'No similar projects found'}
                      </p>
                      <button 
                        className="btn btn-sm btn-outline-primary mt-2"
                        onClick={fetchSimilarProjects}
                        disabled={loadingSimilar}
                      >
                        {loadingSimilar ? 'Loading...' : '🔄 Try Again'}
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Card 4: Presentations with Criteria */}
        {(project || (presentationResults && presentationResults.length > 0)) && (
          <div className="card dashboard-card mt-4">
            <div className="card-body">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: presentationResults && presentationResults.length > 0 ? 'pointer' : 'default' }} onClick={() => presentationResults && presentationResults.length > 0 && setPresentationsExpanded(prev => !prev)}>
                <h5>📊 Presentations & Grades</h5>
                {presentationResults && presentationResults.length > 0 && (
                  <span style={{
                    fontSize: '1.0em',
                    color: '#474d53',
                    transform: presentationsExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                    transition: 'transform 0.1s ease'
                  }}>
                    ▶
                  </span>
                )}
              </div>
              {presentationsExpanded && (
                <div className="mt-3">
                  {presentationResults && presentationResults.length > 0 ? (
                    presentationResults.map((result) => {
                      const presDetail = presentationDetails[result.presentation];
                      const criteria = presentationCriteria[result.presentation] || [];
                      const isExpanded = expandedResultDetails[result.id] || false;
                      const totalMarks = calculateTotalFromCriteria(result);
                      
                      return (
                        <div key={result.id} className="card mb-3 shadow-sm">
                          <div className="card-body py-3 px-3">
                            {/* Header */}
                            <div className="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-2">
                              <div>
                                <h6 className="card-title mb-1">
                                  {result.presentation_name || `Presentation ${result.presentation}`}
                                </h6>
                                {presDetail && (
                                  <small className="text-muted">
                                    📅 {presDetail.presentation_date ? new Date(presDetail.presentation_date).toLocaleDateString() : 'Date TBD'}
                                  </small>
                                )}
                                {result.project_title && (
                                  <small className="text-muted d-block">{result.project_title}</small>
                                )}
                              </div>
                              <div className="d-flex flex-wrap gap-2 align-items-center">
                                <div className="d-flex flex-column align-items-center">
                                  <small className="badge bg-light text-dark border" style={{
                                    color: (result.marks !== null && result.presentation_pass_marks !== null && !Number.isNaN(parseFloat(result.marks)) && !Number.isNaN(parseFloat(result.presentation_pass_marks)) && parseFloat(result.marks) < parseFloat(result.presentation_pass_marks))
                                      ? '#dc3545'
                                      : (result.marks !== null && result.presentation_pass_marks !== null && !Number.isNaN(parseFloat(result.marks)) && !Number.isNaN(parseFloat(result.presentation_pass_marks)) && parseFloat(result.marks) >= parseFloat(result.presentation_pass_marks))
                                        ? '#198754'
                                        : '#212529'
                                  }}>
                                    📊 Total: {totalMarks}
                                  </small>
                                </div>
                                <div className="d-flex flex-column align-items-center">
                                  <small className="badge bg-light text-dark border">
                                    Pass: {result.presentation_pass_marks ?? 'N/A'}
                                  </small>
                                </div>
                                <div className="d-flex flex-column align-items-center">
                                  <small className="badge bg-light text-dark border">Max: {result.presentation_total_marks ?? 'N/A'}</small>
                                </div>
                                {/* Toggle details button */}
                                {criteria.length > 0 && (
                                  <button 
                                    className="btn btn-sm btn-outline-info"
                                    onClick={() => toggleResultDetails(result.id)}
                                  >
                                    {isExpanded ? '▲ Hide Details' : '▼ View Criteria'}
                                  </button>
                                )}
                              </div>
                            </div>

                            {/* Overall comment */}
                            {result.comment ? (
                              <p className="mb-1 text-muted small" style={{ lineHeight: 1.4 }}>
                                <em>📝 {result.comment}</em>
                              </p>
                            ) : null}

                            <p className="mb-0 small" style={{ fontSize: '0.75rem', color: '#000000' }}>
                              {result.created_at ? <em>📅 {new Date(result.created_at).toLocaleDateString()}</em> : 'Date unavailable'}
                              {result.reviewer_name && <span className="ms-2">👤 {result.reviewer_name}</span>}
                            </p>

                            {/* Expanded criteria details */}
                            {isExpanded && criteria.length > 0 && (
                              <div className="mt-3 border-top pt-3">
                                <h6 className="mb-2">📋 Criteria Breakdown</h6>
                                <div className="table-responsive">
                                  <table className="table table-sm table-striped">
                                    <thead>
                                      <tr>
                                        <th>Criteria</th>
                                        <th>Score</th>
                                        <th>Max</th>
                                        <th>Comment</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {criteria.map((c) => {
                                        // Find the score for this criteria
                                        const scoreObj = result.criteria_scores?.find(cs => cs.criteria === c.id);
                                        const score = scoreObj?.score;
                                        const comment = scoreObj?.comment;
                                        const selectedOption = scoreObj?.selected_option;
                                        
                                        // Find the option label if selected
                                        let optionLabel = null;
                                        if (selectedOption && c.options) {
                                          const option = c.options.find(o => o.label === selectedOption);
                                          if (option) {
                                            optionLabel = `${option.label} (${option.value} pts)`;
                                          }
                                        }
                                        
                                        return (
                                          <tr key={c.id}>
                                            <td>
                                              <strong>{c.name}</strong>
                                              {c.options && c.options.length > 0 && (
                                                <span className="badge bg-info ms-1">Dropdown</span>
                                              )}
                                              <div className="small text-muted">{c.description}</div>
                                            </td>
                                            <td>
                                              {score !== null && score !== undefined ? (
                                                <span className="fw-bold">
                                                  {score}
                                                  {selectedOption && (
                                                    <div className="small text-muted">({selectedOption})</div>
                                                  )}
                                                  {optionLabel && (
                                                    <div className="small text-muted">✓ {optionLabel}</div>
                                                  )}
                                                </span>
                                              ) : (
                                                <span className="text-muted">Not graded</span>
                                              )}
                                            </td>
                                            <td>{c.max_score}</td>
                                            <td>{comment || '-'}</td>
                                          </tr>
                                        );
                                      })}
                                    </tbody>
                                    <tfoot>
                                      <tr className="table-active">
                                        <td><strong>Total</strong></td>
                                        <td><strong>{totalMarks}</strong></td>
                                        <td><strong>{result.presentation_total_marks || 'N/A'}</strong></td>
                                        <td></td>
                                      </tr>
                                    </tfoot>
                                  </table>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <p className="text-muted">No presentation results available yet.</p>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Card 5: Project Documents */}
        <div className="card dashboard-card mt-4">
          <div className="card-body">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }} onClick={() => setProjectDocumentsExpanded(prev => !prev)}>
              <h5>📄 Project Documents</h5>
              <span style={{
                fontSize: '1.0em',
                color: '#474d53',
                transform: projectDocumentsExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                transition: 'transform 0.1s ease'
              }}>
                ▶
              </span>
            </div>
            {projectDocumentsExpanded && (
              <div className="mt-3">
                {project ? (
                  <>
                    {project.documents && project.documents.length > 0 ? (
                      <div className="list-group mb-3">
                        {project.documents.map((doc) => (
                          <div key={doc.id} className="list-group-item d-flex justify-content-between align-items-start flex-column flex-md-row gap-2">
                            <div>
                              <div><strong>{doc.name || 'Untitled document'}</strong></div>
                              <div className="small text-muted">{doc.description || 'No description provided.'}</div>
                              {doc.file ? (
                                <a href={doc.file} target="_blank" rel="noreferrer" className="text-primary">📎 View file</a>
                              ) : null}
                            </div>
                            <div className="small text-muted" style={{ minWidth: '120px', textAlign: 'right' }}>
                              {doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleDateString() : ''}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-muted">No project document uploaded.</p>
                    )}
                    <button className="btn btn-primary" onClick={handleOpenDocumentForm}>
                      📤 Add Document (PDF only)
                    </button>
                  </>
                ) : (
                  <>
                    <p className="text-muted">No project document uploaded.</p>
                    <button className="btn btn-secondary" disabled>
                      Add Document (PDF only)
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        </div>

        {showDocumentForm && (
          <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            zIndex: 2000
          }} onClick={handleCloseDocumentForm}>
            <div style={{
              backgroundColor: 'white',
              borderRadius: '8px',
              padding: '25px',
              width: '90%',
              maxWidth: '520px',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)'
            }} onClick={(e) => e.stopPropagation()}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
                <h5 style={{ margin: 0 }}>📤 Upload Project Document</h5>
                <button style={{ background: 'none', border: 'none', fontSize: '1.5em', cursor: 'pointer' }} onClick={handleCloseDocumentForm}>
                  ✕
                </button>
              </div>

              <div className="mb-3">
                <label className="form-label"><strong>Document Name</strong></label>
                <input
                  type="text"
                  className="form-control"
                  value={documentUploadName}
                  onChange={(e) => setDocumentUploadName(e.target.value)}
                  placeholder="Enter a name for the document"
                />
              </div>

              <div className="mb-3">
                <label className="form-label"><strong>Description</strong></label>
                <textarea
                  className="form-control"
                  rows="3"
                  value={documentUploadDescription}
                  onChange={(e) => setDocumentUploadDescription(e.target.value)}
                  placeholder="Optional description"
                />
              </div>

              <div className="mb-3">
                <label className="form-label"><strong>📄 File (PDF only, Max 10MB)</strong></label>
                <input
                  type="file"
                  className="form-control"
                  onChange={handleDocumentFileChange}
                  accept=".pdf"
                />
                {documentUploadFile && (
                  <small className="text-muted d-block mt-1">
                    📄 {documentUploadFile.name} ({(documentUploadFile.size / (1024 * 1024)).toFixed(2)} MB / 10 MB)
                  </small>
                )}
                <small className="text-muted d-block mt-1">
                  ⚠️ Only PDF files are accepted. Maximum file size: 10MB
                </small>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button className="btn btn-secondary" onClick={handleCloseDocumentForm} disabled={documentUploadLoading}>
                  Cancel
                </button>
                <button className="btn btn-primary" onClick={handleUploadDocument} disabled={documentUploadLoading}>
                  {documentUploadLoading ? 'Uploading...' : 'Upload Document'}
                </button>
              </div>
              {documentUploadMessage && (
                <p className={`mt-3 ${documentUploadMessage.includes('✅') ? 'text-success' : 'text-danger'}`}>
                  {documentUploadMessage}
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Profile Modal */}
      {profileExpanded && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 2000
        }} onClick={() => setProfileExpanded(false)}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '8px',
            padding: '30px',
            width: '90%',
            maxWidth: '500px',
            boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
          }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h5 style={{ margin: 0 }}>👤 Personal Profile</h5>
              <button style={{ background: 'none', border: 'none', fontSize: '1.5em', cursor: 'pointer' }} onClick={() => setProfileExpanded(false)}>
                ✕
              </button>
            </div>
            <hr />
            <div>
              <p><strong>Username:</strong> {profile.username || 'N/A'}</p>
              <p><strong>Role:</strong> {profile.role || 'N/A'}</p>
              <p><strong>First Name:</strong> {profile.first_name || 'N/A'}</p>
              <p><strong>Last Name:</strong> {profile.last_name || 'N/A'}</p>
              <div className="mb-3">
                <label className="form-label">Middle Name</label>
                <input
                  type="text"
                  name="middle_name"
                  className="form-control"
                  value={profileDraft.middle_name}
                  onChange={handleProfileDraftChange}
                  disabled={!editingProfile}
                />
              </div>
              <div className="mb-3">
                <label className="form-label">Email Address</label>
                <input
                  type="email"
                  name="email"
                  className="form-control"
                  value={profileDraft.email}
                  onChange={handleProfileDraftChange}
                  disabled={!editingProfile}
                />
              </div>
              {editingProfile ? (
                <div className="d-flex gap-2">
                  <button className="btn btn-primary" onClick={handleSaveProfile} disabled={profileSaving}>
                    {profileSaving ? 'Saving...' : 'Save Changes'}
                  </button>
                  <button
                    className="btn btn-outline-secondary"
                    onClick={() => {
                      setEditingProfile(false);
                      setProfileDraft({
                        middle_name: profile.middle_name || '',
                        email: profile.email || ''
                      });
                    }}
                    disabled={profileSaving}
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button className="btn btn-secondary" onClick={() => setEditingProfile(true)}>
                  Edit Details
                </button>
              )}
              {profileMessage && <p className={`mt-3 ${profileMessage.includes('✅') ? 'text-success' : 'text-danger'}`}>{profileMessage}</p>}
            </div>
          </div>
        </div>
      )}

      {/* Change Password Modal */}
      {showChangePassword && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000
        }} onClick={() => setShowChangePassword(false)}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '8px',
            padding: '30px',
            width: '90%',
            maxWidth: '500px',
            boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
          }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h5 style={{ margin: 0 }}>🔑 Change Password</h5>
              <button style={{ background: 'none', border: 'none', fontSize: '1.5em', cursor: 'pointer' }} onClick={() => setShowChangePassword(false)}>
                ✕
              </button>
            </div>
            <hr />
            <div>
              <div className="mb-3">
                <label className="form-label">Current Password</label>
                <input
                  type="password"
                  name="current_password"
                  className="form-control"
                  value={passwordData.current_password}
                  onChange={handlePasswordChange}
                  placeholder="Enter current password"
                />
              </div>
              <div className="mb-3">
                <label className="form-label">New Password</label>
                <input
                  type="password"
                  name="new_password"
                  className="form-control"
                  value={passwordData.new_password}
                  onChange={handlePasswordChange}
                  placeholder="Enter new password"
                />
              </div>
              <div className="mb-3">
                <label className="form-label">Confirm New Password</label>
                <input
                  type="password"
                  name="confirm_password"
                  className="form-control"
                  value={passwordData.confirm_password}
                  onChange={handlePasswordChange}
                  placeholder="Confirm new password"
                />
              </div>
              <div className="d-flex gap-2">
                <button className="btn btn-primary" onClick={handleSavePassword} disabled={passwordSaving}>
                  {passwordSaving ? 'Changing...' : 'Change Password'}
                </button>
                <button
                  className="btn btn-outline-secondary"
                  onClick={() => {
                    setShowChangePassword(false);
                    setPasswordData({
                      current_password: '',
                      new_password: '',
                      confirm_password: ''
                    });
                    setPasswordMessage('');
                  }}
                  disabled={passwordSaving}
                >
                  Cancel
                </button>
              </div>
              {passwordMessage && (
                <p className={`mt-3 ${passwordMessage.includes('✅') ? 'text-success' : 'text-danger'}`}>
                  {passwordMessage}
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default StudentDashboard;