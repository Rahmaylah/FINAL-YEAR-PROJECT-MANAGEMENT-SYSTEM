import React, { useContext, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from '../services/axiosConfig';
import { AuthContext } from '../context/AuthContext';
import '../styles/Dashboard.css';
import nitLogo from '../assets/nit.png';

const STATUS_OPTIONS = [
  { value: 'proposed', label: 'Proposed' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'completed', label: 'Completed' },
];

function MentorDashboard() {
  const { user, logout } = useContext(AuthContext);
  const navigate = useNavigate();
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
  const [editingProfile, setEditingProfile] = useState(false);
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileMessage, setProfileMessage] = useState('');
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [passwordMessage, setPasswordMessage] = useState('');

  const [mentees, setMentees] = useState([]);
  const [projects, setProjects] = useState([]);
  const [projectUsers, setProjectUsers] = useState([]);
  const [duplicates, setDuplicates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedStudents, setExpandedStudents] = useState(false);
  const [expandedProjects, setExpandedProjects] = useState(false);
  const [expandedPresentations, setExpandedPresentations] = useState(false);
  const [presentations, setPresentations] = useState([]);
  
  // ==================== PRESENTATION CRITERIA STATES ====================
  const [selectedPresentation, setSelectedPresentation] = useState('');
  const [selectedStudent, setSelectedStudent] = useState('');
  const [criteriaList, setCriteriaList] = useState([]);
  const [gradingScores, setGradingScores] = useState({});
  const [gradingResult, setGradingResult] = useState(null);
  const [gradingMessage, setGradingMessage] = useState('');
  const [gradingSaving, setGradingSaving] = useState(false);
  const [loadingCriteria, setLoadingCriteria] = useState(false);
  // ==================== END PRESENTATION CRITERIA STATES ====================

  const [selectedProject, setSelectedProject] = useState(null);
  const [showProjectDetailsModal, setShowProjectDetailsModal] = useState(false);
  const [similarProjects, setSimilarProjects] = useState([]);
  const [loadingSimilar, setLoadingSimilar] = useState(false);
  const [projectSaving, setProjectSaving] = useState(false);
  const [projectMessage, setProjectMessage] = useState('');
  
  // ==================== MENTOR COMMENT STATE ====================
  const [mentorComment, setMentorComment] = useState('');
  const [commentSaving, setCommentSaving] = useState(false);
  const [commentMessage, setCommentMessage] = useState('');
  // ==================== SELECTED STATUS STATE ====================
  const [selectedStatus, setSelectedStatus] = useState('');

  // Image error fallback
  const [imageError, setImageError] = useState(false);

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

  useEffect(() => {
    const fetchData = async () => {
      if (!user || !user.id) return;

      setLoading(true);
      try {
        const menteesResponse = await axios.get('/api/users/', {
          params: {
            mentor: user.id,
            role: 'student'
          }
        });
        const menteesData = menteesResponse.data.results || [];
        setMentees(menteesData);

        // ====== FIX: Log mentees to see if Robby is there ======
        console.log('📋 Mentees from API:', menteesData.map(m => ({ id: m.id, name: `${m.first_name} ${m.last_name}` })));

        const projectsResponse = await axios.get('/api/projects/');
        const projectsData = projectsResponse.data.results || [];
        console.log('📁 All projects from API:', projectsData);

        const projectUsersResponse = await axios.get('/api/project-users/');
        const projectUsersData = projectUsersResponse.data.results || [];
        setProjectUsers(projectUsersData);

        const duplicatesResponse = await axios.get('/api/duplicate-flags/');
        const duplicatesData = duplicatesResponse.data.results || [];
        setDuplicates(duplicatesData);

        const presentationsResponse = await axios.get('/api/presentations/');
        const presentationsData = presentationsResponse.data.results || [];
        setPresentations(presentationsData);

        const menteeIds = menteesData.map((student) => student.id);
        console.log('📋 Mentee IDs:', menteeIds);

        const relatedProjectIds = projectUsersData
          .filter((relation) => menteeIds.includes(relation.user))
          .map((relation) => relation.project);

        const directProjectIds = projectsData
          .filter((project) => {
            if (!project.user) {
              console.log(`⚠️ Project ${project.id} has no user:`, project);
              return false;
            }
            
            let userId = null;
            
            if (typeof project.user === 'number') {
              userId = project.user;
            } else if (typeof project.user === 'object' && project.user !== null) {
              userId = project.user.id;
            } else if (typeof project.user === 'string') {
              userId = parseInt(project.user, 10);
            }
            
            console.log(`🔍 Project ${project.id}: user = ${project.user}, userId = ${userId}`);
            const isMentee = menteeIds.includes(userId);
            console.log(`   Is in menteeIds? ${isMentee}`);
            
            return isMentee;
          })
          .map((project) => project.id);

        console.log('📁 Direct project IDs (raw):', directProjectIds);
        console.log('📁 Related project IDs:', relatedProjectIds);

        const allProjectIds = [...new Set([...relatedProjectIds, ...directProjectIds])];
        console.log('📁 All project IDs for mentor:', allProjectIds);

        const filteredProjects = projectsData.filter((project) => allProjectIds.includes(project.id));
        console.log('📁 Filtered projects:', filteredProjects);

        setProjects(filteredProjects);
      } catch (error) {
        console.error('Error fetching mentor dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [user]);

  // ==================== PRESENTATION CRITERIA FUNCTIONS ====================

  const fetchCriteria = async (presentationId) => {
    if (!presentationId) {
      setCriteriaList([]);
      return [];
    }

    setLoadingCriteria(true);
    try {
      const response = await axios.get('/api/presentation-criteria/?presentation=' + presentationId);
      const criteria = response.data.results || response.data || [];
      setCriteriaList(criteria);
      setLoadingCriteria(false);
      return criteria;
    } catch (error) {
      console.error('Error fetching criteria:', error);
      setCriteriaList([]);
      setLoadingCriteria(false);
      return [];
    }
  };

  const handlePresentationSelect = async (presentationId) => {
    setSelectedPresentation(presentationId);
    setSelectedStudent('');
    setGradingScores({});
    setGradingResult(null);
    setGradingMessage('');
    setCriteriaList([]);

    if (presentationId) {
      await fetchCriteria(presentationId);
    }
  };

  const handleStudentSelect = async (studentId) => {
    setSelectedStudent(studentId);
    setGradingScores({});
    setGradingResult(null);
    setGradingMessage('');

    if (!studentId || !selectedPresentation) return;

    try {
      const response = await axios.get('/api/presentation-results/?presentation=' + selectedPresentation + '&student=' + studentId);
      const results = response.data.results || response.data || [];
      
      if (results.length > 0) {
        const result = results[0];
        setGradingResult(result);
        
        const scoresResponse = await axios.get('/api/presentation-result-criteria/?result=' + result.id);
        const existingScores = scoresResponse.data.results || scoresResponse.data || [];
        
        const scoresMap = {};
        existingScores.forEach(score => {
          scoresMap[score.criteria] = {
            score: score.score,
            selected_option: score.selected_option,
            comment: score.comment || ''
          };
        });
        setGradingScores(scoresMap);
        
        console.log('📋 Loaded existing scores for student:', scoresMap);
      } else {
        setGradingResult(null);
        console.log('📋 No existing result for this student');
      }
    } catch (error) {
      console.error('Error fetching student result:', error);
    }
  };

  const handleScoreChange = (criteriaId, field, value) => {
    setGradingScores(prev => ({
      ...prev,
      [criteriaId]: {
        ...prev[criteriaId],
        [field]: value
      }
    }));
  };

  // ==================== FIXED: SAVE GRADES WITH DB VERIFICATION ====================
  const handleSaveGrades = async () => {
    // ====== VALIDATION ======
    if (!selectedPresentation) {
      setGradingMessage('❌ Please select a presentation.');
      return;
    }

    if (!selectedStudent) {
      setGradingMessage('❌ Please select a student.');
      return;
    }

    if (criteriaList.length === 0) {
      setGradingMessage('❌ No criteria available for this presentation.');
      return;
    }

    // ====== CHECK IF ALL REQUIRED CRITERIA ARE GRADED ======
    const missingCriteria = [];
    let totalMarks = 0;
    let hasScores = false;
    
    for (const criteria of criteriaList) {
      const scoreData = gradingScores[criteria.id] || {};
      const hasScore = scoreData.score !== undefined && scoreData.score !== '' && scoreData.score !== null;
      const hasOption = scoreData.selected_option && scoreData.selected_option !== '';
      
      if (criteria.is_required) {
        if (!hasScore && !hasOption) {
          missingCriteria.push(criteria.name);
        } else {
          hasScores = true;
          if (hasScore) {
            totalMarks += parseFloat(scoreData.score) || 0;
          } else if (hasOption) {
            const option = criteria.options?.find(o => o.label === scoreData.selected_option);
            if (option) {
              totalMarks += parseFloat(option.value) || 0;
            }
          }
        }
      } else {
        if (hasScore || hasOption) {
          hasScores = true;
          if (hasScore) {
            totalMarks += parseFloat(scoreData.score) || 0;
          } else if (hasOption) {
            const option = criteria.options?.find(o => o.label === scoreData.selected_option);
            if (option) {
              totalMarks += parseFloat(option.value) || 0;
            }
          }
        }
      }
    }

    if (missingCriteria.length > 0) {
      setGradingMessage('❌ Please grade all required criteria: ' + missingCriteria.join(', '));
      return;
    }

    if (!hasScores) {
      setGradingMessage('❌ Please enter at least one score.');
      return;
    }

    setGradingSaving(true);
    setGradingMessage('');

    console.log('📊 ===== STARTING SAVE GRADES =====');
    console.log('📊 Student ID:', selectedStudent);
    console.log('📊 Presentation ID:', selectedPresentation);
    console.log('📊 Total Marks:', totalMarks);
    console.log('📊 Criteria Scores:', gradingScores);

    try {
      let resultId = gradingResult?.id;
      
      // If no result exists, create one
      if (!resultId) {
        const studentProject = projects.find(p => 
          p.project_users?.some(pu => pu.user === parseInt(selectedStudent))
        );
        
        console.log('📊 Creating new presentation result...');
        const resultResponse = await axios.post('/api/presentation-results/', {
          presentation: parseInt(selectedPresentation),
          student: parseInt(selectedStudent),
          project: studentProject?.id || null,
          comment: '',
          marks: totalMarks
        });
        resultId = resultResponse.data.id;
        setGradingResult(resultResponse.data);
        console.log('✅ Created result with ID:', resultId);
      } else {
        console.log('📊 Using existing result ID:', resultId);
      }

      // ====== Save EACH criteria score ======
      let savedCount = 0;
      for (const criteria of criteriaList) {
        const scoreData = gradingScores[criteria.id] || {};
        const hasScore = scoreData.score !== undefined && scoreData.score !== '' && scoreData.score !== null;
        const hasOption = scoreData.selected_option && scoreData.selected_option !== '';
        
        if (!hasScore && !hasOption) {
          console.log(`⏭️ Skipping criteria ${criteria.id} (${criteria.name}) - no score`);
          continue;
        }
        
        try {
          const payload = {
            result: resultId,
            criteria: criteria.id,
            score: hasScore ? parseFloat(scoreData.score) : null,
            selected_option: hasOption ? scoreData.selected_option : '',
            comment: scoreData.comment || ''
          };
          
          console.log(`📊 Saving criteria ${criteria.id} (${criteria.name}):`, payload);
          
          try {
            const response = await axios.post('/api/presentation-result-criteria/save_score/', payload);
            savedCount++;
            console.log(`✅ ${response.data.created ? 'Created' : 'Updated'} criteria ${criteria.id} (${criteria.name}) - DB ID: ${response.data.data.id}`);
          } catch (saveError) {
            console.log(`⚠️ save_score failed for criteria ${criteria.id}, using fallback...`);
            
            const existingResponse = await axios.get('/api/presentation-result-criteria/', {
              params: {
                result: resultId,
                criteria: criteria.id
              }
            });
            
            const existing = existingResponse.data.results || existingResponse.data || [];
            
            if (existing.length > 0) {
              const putResponse = await axios.put(`/api/presentation-result-criteria/${existing[0].id}/`, payload);
              savedCount++;
              console.log(`✅ Updated criteria ${criteria.id} (${criteria.name}) via PUT - DB ID: ${putResponse.data.id}`);
            } else {
              const postResponse = await axios.post('/api/presentation-result-criteria/', payload);
              savedCount++;
              console.log(`✅ Created criteria ${criteria.id} (${criteria.name}) via POST - DB ID: ${postResponse.data.id}`);
            }
          }
        } catch (error) {
          console.error(`❌ Error saving criteria ${criteria.id}:`, error);
        }
      }

      console.log(`📊 Saved ${savedCount} out of ${criteriaList.length} criteria`);

      // ====== CALCULATE TOTAL ======
      console.log('📊 Calculating total...');
      await axios.post(`/api/presentation-results/${resultId}/calculate_total/`);
      
      // ====== UPDATE MARKS ======
      console.log('📊 Updating marks to:', totalMarks);
      await axios.patch(`/api/presentation-results/${resultId}/`, {
        marks: totalMarks
      });
      
      // ====== REFRESH DATA ======
      console.log('📊 Refreshing result data...');
      const refreshedResult = await axios.get(`/api/presentation-results/${resultId}/`);
      setGradingResult(refreshedResult.data);
      
      console.log('📊 ===== SAVE COMPLETE =====');
      console.log('📊 Final Result:', refreshedResult.data);
      console.log('📊 Final Marks:', refreshedResult.data.marks);
      console.log('📊 Criteria Total:', refreshedResult.data.criteria_total);
      console.log('📊 Criteria Scores:', refreshedResult.data.criteria_scores);
      
      setGradingMessage(`✅ Grades saved successfully! Total: ${totalMarks} marks (${savedCount} criteria saved)`);
      setTimeout(() => {
        setGradingMessage('');
      }, 4000);
      
    } catch (error) {
      console.error('❌ Error saving grades:', error);
      
      let errorMsg = '❌ Unable to save grades. Please try again.';
      if (error.response) {
        console.error('Response data:', error.response.data);
        if (error.response.data?.error) {
          errorMsg = '❌ ' + error.response.data.error;
        } else if (error.response.data?.detail) {
          errorMsg = '❌ ' + error.response.data.detail;
        } else if (error.response.data && typeof error.response.data === 'object') {
          const errors = Object.values(error.response.data).flat();
          if (errors.length > 0) {
            errorMsg = '❌ ' + errors.join(', ');
          }
        }
      }
      setGradingMessage(errorMsg);
    } finally {
      setGradingSaving(false);
    }
  };

  // ==================== END PRESENTATION CRITERIA FUNCTIONS ====================

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
      const response = await axios.patch('/api/users/' + user.id + '/', profileDraft);
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
      await axios.post('/api/users/set_password/', {
        current_password: passwordData.current_password,
        new_password: passwordData.new_password
      });
      setPasswordMessage('✅ Password changed successfully.');
      setPasswordData({
        current_password: '',
        new_password: '',
        confirm_password: ''
      });
      setShowChangePassword(false);
    } catch (error) {
      console.error('Error changing password:', error);
      if (error.response && error.response.data) {
        if (error.response.data.error) {
          setPasswordMessage('❌ ' + error.response.data.error);
        } else if (error.response.data.detail) {
          setPasswordMessage('❌ ' + error.response.data.detail);
        } else {
          setPasswordMessage('❌ Unable to change password. Please try again.');
        }
      } else if (error.message) {
        setPasswordMessage('❌ Network error: ' + error.message);
      } else {
        setPasswordMessage('❌ Unable to change password. Please try again.');
      }
    } finally {
      setPasswordSaving(false);
    }
  };

  const toggleStudents = () => setExpandedStudents((prev) => !prev);
  const toggleProjects = () => setExpandedProjects((prev) => !prev);
  const togglePresentations = () => setExpandedPresentations((prev) => !prev);

  const getProjectStudents = (projectId) => {
    const fromProjectUsers = projectUsers
      .filter((relation) => relation.project === projectId)
      .map((relation) => relation.user_name);
    
    if (fromProjectUsers.length > 0) {
      return fromProjectUsers;
    }
    
    const project = projects.find(p => p.id === projectId);
    if (project && project.user) {
      const student = mentees.find(m => m.id === project.user);
      if (student) {
        return [`${student.first_name} ${student.last_name}`];
      }
    }
    
    return ['No students assigned'];
  };

  const getProjectDuplicateFlags = (projectId) => (
    duplicates.filter((flag) => flag.project === projectId)
  );

  const formatRegistrationNumbers = (registrationNumbers) => {
    if (!Array.isArray(registrationNumbers) || registrationNumbers.length === 0) {
      return 'Reg: N/A';
    }
    return 'Reg: ' + registrationNumbers.join(', ');
  };

  const openProjectDetails = (project) => {
    const loadProjectDetails = async () => {
      try {
        const response = await axios.get('/api/projects/' + project.id + '/');
        setSelectedProject(response.data);
        setSelectedStatus(response.data.status || 'proposed');
        setMentorComment(response.data.mentor_comment || '');
        setCommentMessage('');
        setProjectMessage('');
      } catch (error) {
        console.error('Error loading project details:', error);
        setSelectedProject(project);
        setSelectedStatus(project.status || 'proposed');
        setMentorComment(project.mentor_comment || '');
      }
    };
    loadProjectDetails();
    setShowProjectDetailsModal(true);
    if (project.is_flagged_duplicate) {
      fetchSimilarProjects(project.id);
    } else {
      setSimilarProjects([]);
    }
  };

  const fetchSimilarProjects = async (projectId) => {
    setLoadingSimilar(true);
    setSimilarProjects([]);
    
    try {
      const response = await axios.get(`/api/projects/${projectId}/similar-all/`);
      
      if (response.data.count === 0 || !response.data.results || response.data.results.length === 0) {
        setSimilarProjects([]);
        setLoadingSimilar(false);
        return;
      }
      
      const formattedProjects = response.data.results.map((item) => ({
        id: item.id,
        title: item.title || 'Untitled',
        similarity_score: item.similarity_score || 0,
        status: item.status || 'proposed',
        year: item.year || 'N/A',
        project_type_name: item.project_type_name || 'N/A',
        reviewed: item.reviewed || false,
        flag_id: item.flag_id,
        author_name: item.author_name || 'Unknown',
        mentor: item.mentor || 'N/A',
        mentor_comment: item.mentor_comment || null,
        description: item.description || '',
        registration_numbers: item.registration_numbers || []
      }));
      
      setSimilarProjects(formattedProjects);
    } catch (error) {
      console.error('Error fetching similar projects:', error);
      setSimilarProjects([]);
    } finally {
      setLoadingSimilar(false);
    }
  };

  const markFlagReviewed = async (flagId) => {
    try {
      await axios.post('/api/duplicate-flags/' + flagId + '/mark_reviewed/');
      setSimilarProjects(prev => prev.map(project =>
        project.flag_id === flagId ? { ...project, reviewed: true } : project
      ));
    } catch (error) {
      console.error('Error marking flag as reviewed:', error);
    }
  };

  const handleSaveCommentAndStatus = async () => {
    if (!selectedProject || !selectedProject.id) {
      setProjectMessage('❌ No project selected.');
      return;
    }

    setProjectSaving(true);
    setCommentSaving(true);
    setProjectMessage('');
    setCommentMessage('');

    try {
      const updates = {};
      let hasChanges = false;

      if (selectedStatus !== selectedProject.status) {
        updates.status = selectedStatus;
        hasChanges = true;
      }

      const currentComment = selectedProject.mentor_comment || '';
      if (mentorComment.trim() !== currentComment.trim()) {
        updates.mentor_comment = mentorComment.trim();
        hasChanges = true;
      }

      if (!hasChanges) {
        setProjectMessage('ℹ️ No changes to save.');
        setCommentMessage('ℹ️ No changes to save.');
        setProjectSaving(false);
        setCommentSaving(false);
        return;
      }

      const response = await axios.patch('/api/projects/' + selectedProject.id + '/', updates);
      
      setProjects((prevProjects) =>
        prevProjects.map((project) =>
          project.id === selectedProject.id ? { 
            ...project, 
            ...response.data 
          } : project
        )
      );
      
      setSelectedProject((prev) => ({ 
        ...prev, 
        ...response.data 
      }));
      
      setSelectedStatus(response.data.status);
      
      if (updates.status) {
        setProjectMessage('✅ Status updated successfully!');
      } else {
        setProjectMessage('✅ Project updated successfully!');
      }
      
      if (updates.mentor_comment !== undefined) {
        setCommentMessage('✅ Comment saved successfully!');
      }

      setTimeout(() => {
        setCommentMessage('');
        setProjectMessage('');
      }, 4000);
      
    } catch (error) {
      console.error('Error saving project updates:', error);
      
      let errorMsg = '❌ Unable to save. Please try again.';
      if (error.response?.data?.error) {
        errorMsg = '❌ ' + error.response.data.error;
      } else if (error.response?.data?.detail) {
        errorMsg = '❌ ' + error.response.data.detail;
      }
      setProjectMessage(errorMsg);
    } finally {
      setProjectSaving(false);
      setCommentSaving(false);
    }
  };

  const flaggedProjects = projects.filter((project) => project.is_flagged_duplicate);
  const normalProjects = projects.filter((project) => !project.is_flagged_duplicate);
  const selectedPresentationDetails = presentations.find(
    (presentation) => String(presentation.id) === String(selectedPresentation)
  );

  return (
    <div className="dashboard-container mentor-dashboard">
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
            <span>FYPMS - Mentor Dashboard</span>
          </span>
          <div className="dropdown ms-auto" style={{ cursor: 'pointer' }}>
            <div
              style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
              onClick={() => setShowUserMenu((prev) => !prev)}
              id="userMenuButton"
              aria-expanded={showUserMenu}
            >
              <span style={{ fontSize: '1rem', color: '#333' }}>
                {profile?.username || profile?.last_name || 'Mentor'}
              </span>
              <span style={{ fontSize: '0.8rem', color: '#666', transform: showUserMenu ? 'rotate(180deg)' : 'rotate(90deg)', transition: 'transform 0.3s ease', display: 'inline-block' }}>Λ</span>
            </div>
            <ul className={"dropdown-menu " + (showUserMenu ? 'show' : '')} style={{ width: '140px', position: 'fixed', right: '0px', top: '70px', marginRight: '10px', padding: '5px 0px' }} aria-labelledby="userMenuButton">
              <li>
                <button className="dropdown-item" style={{ fontSize: '0.9rem', padding: '5px 10px' }} onClick={() => { setProfileExpanded(true); setShowUserMenu(false); }}>
                  Profile
                </button>
              </li>
              <li>
                <button className="dropdown-item" style={{ fontSize: '0.9rem', padding: '5px 10px' }} onClick={() => { setShowChangePassword(true); setShowUserMenu(false); }}>
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
          zIndex: 1000
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
              {profileMessage && <p className={'mt-3 ' + (profileMessage.includes('✅') ? 'text-success' : 'text-danger')}>{profileMessage}</p>}
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
                <p className={'mt-3 ' + (passwordMessage.includes('✅') ? 'text-success' : 'text-danger')}>
                  {passwordMessage}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="container mt-5">
        <div className="welcome-section">
          <h1>
            Welcome back, <span className="role-name">{profile.first_name || profile.username || 'Mentor'}</span>.
          </h1>
          <div className="lead">
            <div className="d-flex flex-column flex-lg-row align-items-start align-items-lg-center gap-2 gap-lg-4">
              <div className="d-flex align-items-center gap-3">
                <span>Mentees: <strong>{mentees.length}</strong></span>
                <span>Projects: <strong>{projects.length}</strong></span>
              </div>
              <span>Flagged duplicates: <strong>{flaggedProjects.length}</strong></span>
            </div>
          </div>
        </div>

        <div className="row mt-2">
          <div className="col-md-12">
            <div className="card dashboard-card">
              <div className="card-body">
                <div
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
                  onClick={toggleStudents}
                >
                  <div>
                    <h5 className="card-title" style={{ marginBottom: 0 }}>👨‍🎓 Mentees</h5>
                    <p className="card-text">View and manage your assigned students</p>
                  </div>
                  <span
                    style={{
                      fontSize: '1.5em',
                      color: '#2a2d30',
                      transform: expandedStudents ? 'rotate(360deg)' : 'rotate(-90deg)',
                      transition: 'transform 0.05s ease'
                    }}
                  >
                    ▼
                  </span>
                </div>

                {expandedStudents && (
                  <>
                    <hr />
                    {loading ? (
                      <p>Loading students...</p>
                    ) : mentees.length > 0 ? (
                      <ul style={{ marginBottom: 0 }}>
                        {mentees.map((student) => (
                          <li key={student.id} className="mb-3">
                            <strong>{student.first_name} {student.middle_name} {student.last_name} - ({student.registration_number})</strong>
                            <br />
                            <small style={{ color: '#666' }}>{student.email}</small>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p>No students assigned yet.</p>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="row mt-2">
          <div className="col-md-12">
            <div className="card dashboard-card">
              <div className="card-body">
                <div
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
                  onClick={toggleProjects}
                >
                  <div>
                    <h5 className="card-title" style={{ marginBottom: 0 }}>📁 Projects</h5>
                    <p className="card-text">Review flagged and normal projects from your students</p>
                  </div>
                  <span
                    style={{
                      fontSize: '1.5em',
                      color: '#2a2d30',
                      transform: expandedProjects ? 'rotate(360deg)' : 'rotate(-90deg)',
                      transition: 'transform 0.05s ease'
                    }}
                  >
                    ▼
                  </span>
                </div>

                {expandedProjects && (
                  <>
                    <hr />
                    {loading ? (
                      <p>Loading projects...</p>
                    ) : projects.length > 0 ? (
                      <>
                        {flaggedProjects.length > 0 ? (
                          <div className="mb-4">
                            <h6>⚠️ Flagged Projects</h6>
                            <div className="list-group">
                              {flaggedProjects.map((project) => (
                                <div
                                  key={project.id}
                                  className="list-group-item"
                                  style={{ cursor: 'pointer' }}
                                  onClick={() => openProjectDetails(project)}
                                >
                                  <div className="d-flex justify-content-between align-items-center">
                                    <div>
                                      <h6>{project.title}</h6>
                                      <p className="mb-1">
                                        <strong>Status:</strong> {project.status} | <strong>Students:</strong>{' '}
                                        {getProjectStudents(project.id).join(', ') || 'No students assigned'}
                                      </p>
                                      {getProjectDuplicateFlags(project.id).length > 0 && (
                                        <p className="mb-1 text-muted">
                                          <strong>Similar to:</strong>{' '}
                                          {getProjectDuplicateFlags(project.id)
                                            .map((flag) => flag.similar_project_title + ' (' + (flag.similarity_score * 100).toFixed(1) + '%) - ' + formatRegistrationNumbers(flag.similar_project_registration_numbers))
                                            .join(', ')}
                                        </p>
                                      )}
                                      <small className="text-muted">
                                        Type: {project.project_type_name || 'N/A'} | Year: {project.year}
                                      </small>
                                    </div>
                                    <i className="bi bi-eye" style={{ fontSize: '1.4em', color: '#007bff' }}></i>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        ) : (
                          <div className="mb-4">
                            <h6>⚠️ Flagged Projects</h6>
                            <p className="text-muted">No flagged projects yet.</p>
                          </div>
                        )}

                        <div>
                          <h6>📋 Unflagged Projects</h6>
                          {normalProjects.length > 0 ? (
                            <div className="list-group">
                              {normalProjects.map((project) => (
                                <div
                                  key={project.id}
                                  className="list-group-item"
                                  style={{ cursor: 'pointer' }}
                                  onClick={() => openProjectDetails(project)}
                                >
                                  <div className="d-flex justify-content-between align-items-center">
                                    <div>
                                      <h6>{project.title}</h6>
                                      <p className="mb-1">
                                        <strong>Status:</strong> {project.status} | <strong>Students:</strong>{' '}
                                        {getProjectStudents(project.id).join(', ') || 'No students assigned'}
                                      </p>
                                      <small className="text-muted">
                                        Type: {project.project_type_name || 'N/A'} | Year: {project.year}
                                      </small>
                                    </div>
                                    <i className="bi bi-eye" style={{ fontSize: '1.4em', color: '#007bff' }}></i>
                                  </div>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <p>No non-flagged projects found.</p>
                          )}
                        </div>
                      </>
                    ) : (
                      <p>No projects found for your students.</p>
                    )}
                    {projectMessage && <p className={'mt-3 ' + (projectMessage.includes('✅') ? 'text-success' : 'text-danger')}>{projectMessage}</p>}
                  </>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* ==================== PRESENTATIONS SECTION WITH CRITERIA ==================== */}
        <div className="row mt-2">
          <div className="col-md-12">
            <div className="card dashboard-card">
              <div className="card-body">
                <div
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
                  onClick={togglePresentations}
                >
                  <div>
                    <h5 className="card-title" style={{ marginBottom: 0 }}>📅 Presentations & Grading</h5>
                    <p className="card-text">Record marks and comments for student presentations</p>
                  </div>
                  <span
                    style={{
                      fontSize: '1.5em',
                      color: '#2a2d30',
                      transform: expandedPresentations ? 'rotate(360deg)' : 'rotate(-90deg)',
                      transition: 'transform 0.05s ease'
                    }}
                  >
                    ▼
                  </span>
                </div>

                {expandedPresentations && (
                  <>
                    <hr />
                    {presentations.length > 0 ? (
                      <div>
                        {/* Select Presentation */}
                        <div className="mb-3">
                          <label className="form-label"><strong>Select Presentation</strong></label>
                          <select
                            className="form-select"
                            value={selectedPresentation}
                            onChange={(e) => handlePresentationSelect(e.target.value)}
                          >
                            <option value="">-- Select a presentation --</option>
                            {presentations.map((presentation) => (
                              <option key={presentation.id} value={presentation.id}>
                                {presentation.name || 'Presentation ' + presentation.id} - {presentation.presentation_date || 'TBD'}
                              </option>
                            ))}
                          </select>
                        </div>

                        {/* Presentation Info */}
                        {selectedPresentationDetails && (
                          <div className="mb-3">
                            <div className="alert alert-info">
                              <strong>Maximum Marks:</strong> {selectedPresentationDetails.total_marks ?? 'N/A'} | 
                              <strong> Pass Marks:</strong> {selectedPresentationDetails.pass_marks ?? 'N/A'}
                              {criteriaList.length > 0 && (
                                <span className="ms-2 badge bg-primary">{criteriaList.length} criteria</span>
                              )}
                              {loadingCriteria && (
                                <span className="ms-2 badge bg-warning">Loading criteria...</span>
                              )}
                            </div>
                          </div>
                        )}

                        {/* Select Student */}
                        <div className="mb-3">
                          <label className="form-label"><strong>Select Student</strong></label>
                          <select
                            className="form-select"
                            value={selectedStudent}
                            onChange={(e) => handleStudentSelect(e.target.value)}
                          >
                            <option value="">-- Select a student --</option>
                            {mentees.map((student) => (
                              <option key={student.id} value={student.id}>
                                {student.first_name} {student.middle_name} {student.last_name}
                              </option>
                            ))}
                          </select>
                        </div>

                        {/* ====== CRITERIA GRADING ====== */}
                        {selectedStudent && selectedPresentation && (
                          <>
                            <hr />
                            <h6 className="mb-3">📋 Grading Criteria for {mentees.find(s => s.id === parseInt(selectedStudent))?.first_name || 'Student'}</h6>

                            {loadingCriteria ? (
                              <div className="text-center py-4">
                                <div className="spinner-border text-primary" role="status">
                                  <span className="visually-hidden">Loading criteria...</span>
                                </div>
                                <p className="mt-2 text-muted">Loading criteria...</p>
                              </div>
                            ) : criteriaList.length > 0 ? (
                              criteriaList
                                .sort((a, b) => a.order - b.order)
                                .map((criteria) => {
                                  const scoreData = gradingScores[criteria.id] || {};
                                  return (
                                    <div key={criteria.id} className="card mb-3">
                                      <div className="card-body">
                                        <div className="d-flex justify-content-between align-items-start flex-wrap">
                                          <div>
                                            <h6 className="mb-1">{criteria.name}</h6>
                                            <small className="text-muted d-block">{criteria.description}</small>
                                            <small className="text-muted">Max: {criteria.max_score} pts</small>
                                            {criteria.options && criteria.options.length > 0 && (
                                              <div className="mt-1 small text-muted">
                                                Options: {criteria.options.map((o, i) => (
                                                  <span key={i} className="badge bg-light text-dark ms-1">
                                                    {o.label} ({o.value} pts)
                                                  </span>
                                                ))}
                                              </div>
                                            )}
                                          </div>
                                          <div style={{ minWidth: '150px' }}>
                                            {criteria.options && criteria.options.length > 0 ? (
                                              <select
                                                className="form-select form-select-sm"
                                                value={scoreData.selected_option || ''}
                                                onChange={(e) => {
                                                  const selected = criteria.options.find(o => o.label === e.target.value);
                                                  handleScoreChange(criteria.id, 'selected_option', e.target.value);
                                                  handleScoreChange(criteria.id, 'score', selected ? selected.value : null);
                                                }}
                                              >
                                                <option value="">Select...</option>
                                                {criteria.options.map((opt, idx) => (
                                                  <option key={idx} value={opt.label}>
                                                    {opt.label} ({opt.value} pts)
                                                  </option>
                                                ))}
                                              </select>
                                            ) : (
                                              <input
                                                type="number"
                                                step="0.5"
                                                className="form-control form-control-sm"
                                                placeholder="Enter marks"
                                                value={scoreData.score || ''}
                                                onChange={(e) => {
                                                  const val = e.target.value ? parseFloat(e.target.value) : '';
                                                  handleScoreChange(criteria.id, 'score', val);
                                                }}
                                              />
                                            )}
                                          </div>
                                        </div>
                                        <div className="mt-2">
                                          <input
                                            type="text"
                                            className="form-control form-control-sm"
                                            placeholder="Comment (optional)"
                                            value={scoreData.comment || ''}
                                            onChange={(e) => handleScoreChange(criteria.id, 'comment', e.target.value)}
                                          />
                                        </div>
                                      </div>
                                    </div>
                                  );
                                })
                            ) : (
                              <div className="alert alert-warning">
                                <p className="mb-0">⚠️ No criteria defined for this presentation. Please contact coordinator.</p>
                              </div>
                            )}

                            {/* ====== SAVE GRADES BUTTON ====== */}
                            {criteriaList.length > 0 && !loadingCriteria && (
                              <div className="d-flex gap-2 mt-3">
                                <button 
                                  className="btn btn-primary" 
                                  onClick={handleSaveGrades} 
                                  disabled={gradingSaving}
                                >
                                  {gradingSaving ? (
                                    <>
                                      <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                                      Saving...
                                    </>
                                  ) : (
                                    '💾 Save Presentation Marks'
                                  )}
                                </button>
                              </div>
                            )}
                            {gradingMessage && <p className={'mt-3 ' + (gradingMessage.includes('✅') ? 'text-success' : 'text-danger')}>{gradingMessage}</p>}
                          </>
                        )}

                        {!selectedStudent && selectedPresentation && (
                          <div className="alert alert-info mt-3">
                            <p className="mb-0">👆 Please select a student to start grading.</p>
                          </div>
                        )}

                        {!selectedPresentation && (
                          <div className="alert alert-info mt-3">
                            <p className="mb-0">👆 Please select a presentation to start grading.</p>
                          </div>
                        )}
                      </div>
                    ) : (
                      <p className="text-muted">No presentations available.</p>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
        {/* ==================== END PRESENTATIONS SECTION ==================== */}
      </div>

      {/* ==================== PROJECT DETAILS MODAL WITH MENTOR COMMENT AND STATUS ==================== */}
      {showProjectDetailsModal && selectedProject && (
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
        }} onClick={() => setShowProjectDetailsModal(false)}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '8px',
            padding: '30px',
            width: '90%',
            maxWidth: '650px',
            maxHeight: '80vh',
            overflow: 'auto',
            boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
          }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h5 style={{ margin: 0 }}>{selectedProject.title}</h5>
              <button style={{ background: 'none', border: 'none', fontSize: '1.5em', cursor: 'pointer' }} onClick={() => setShowProjectDetailsModal(false)}>
                ✕
              </button>
            </div>
            <hr />
            <div>
              {/* Project Details */}
              <div className="mb-3">
                <p><strong>Status:</strong> {selectedProject.status}</p>
                <p><strong>Project Type:</strong> {selectedProject.project_type_name || 'N/A'}</p>
                <p><strong>Year:</strong> {selectedProject.year}</p>
                <p><strong>Students:</strong> {getProjectStudents(selectedProject.id).join(', ') || 'No students assigned'}</p>
              </div>

              <div className="mb-3">
                <p><strong>Main Objective:</strong> {selectedProject.main_objective || 'N/A'}</p>
              </div>

              <div className="mb-3">
                <p><strong>Specific Objectives:</strong></p>
                {Array.isArray(selectedProject.specific_objectives) && selectedProject.specific_objectives.length > 0 ? (
                  <ul>
                    {selectedProject.specific_objectives.map((obj, idx) => (
                      <li key={idx}>{obj}</li>
                    ))}
                  </ul>
                ) : (
                  <p>N/A</p>
                )}
              </div>

              <div className="mb-3">
                <p><strong>Project Description:</strong> {selectedProject.project_description || 'N/A'}</p>
              </div>

              <div className="mb-3">
                <p><strong>Implementation Details:</strong> {selectedProject.implementation_details || 'N/A'}</p>
              </div>

              {/* ============================================================ */}
              {/* ====== MENTOR COMMENT AND STATUS - WITH SAVE BUTTON ====== */}
              {/* ============================================================ */}
              <div className="mb-3 p-3 bg-light rounded border">
                <h6 className="mb-3">✏️ Mentor Review</h6>

                {/* Status Selection */}
                <div className="mb-3">
                  <label className="form-label"><strong>Status</strong></label>
                  <select
                    className="form-select"
                    value={selectedStatus}
                    onChange={(e) => setSelectedStatus(e.target.value)}
                    disabled={projectSaving}
                  >
                    {STATUS_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Mentor Comment Textarea */}
                <div className="mb-3">
                  <label className="form-label"><strong>💬 Mentor Comment</strong></label>
                  <textarea
                    className="form-control"
                    rows="4"
                    value={mentorComment}
                    onChange={(e) => setMentorComment(e.target.value)}
                    placeholder="Enter your feedback or comment about this project..."
                    style={{ resize: 'vertical' }}
                    disabled={commentSaving}
                  />
                  <small className="text-muted">
                    This comment will be visible to the student.
                  </small>
                  {commentMessage && (
                    <p className={'mt-2 ' + (commentMessage.includes('✅') ? 'text-success' : 'text-danger')}>
                      {commentMessage}
                    </p>
                  )}
                </div>

                {/* ====== SAVE BUTTON ====== */}
                <div className="d-flex gap-2">
                  <button 
                    className="btn btn-success" 
                    onClick={handleSaveCommentAndStatus} 
                    disabled={projectSaving || commentSaving}
                  >
                    {projectSaving || commentSaving ? (
                      <>
                        <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                        Saving...
                      </>
                    ) : (
                      '💾 Save Comment & Status'
                    )}
                  </button>
                  <button 
                    className="btn btn-outline-secondary" 
                    onClick={() => {
                      setSelectedStatus(selectedProject.status || 'proposed');
                      setMentorComment(selectedProject.mentor_comment || '');
                      setCommentMessage('');
                      setProjectMessage('');
                    }}
                    disabled={projectSaving || commentSaving}
                  >
                    Reset
                  </button>
                </div>
                {projectMessage && (
                  <p className={'mt-2 ' + (projectMessage.includes('✅') ? 'text-success' : projectMessage.includes('ℹ️') ? 'text-info' : 'text-danger')}>
                    {projectMessage}
                  </p>
                )}
              </div>
              {/* ====== END MENTOR COMMENT AND STATUS ====== */}

              {/* Similar Projects - Only show if flagged */}
              {selectedProject.is_flagged_duplicate && (
                <div className="mb-3">
                  <h6>🔍 Similar Projects</h6>
                  {loadingSimilar ? (
                    <p>Loading similar projects...</p>
                  ) : similarProjects.length > 0 ? (
                    <div className="list-group">
                      {similarProjects.map((similarProject) => (
                        <div key={similarProject.id} className="list-group-item">
                          <div className="d-flex justify-content-between align-items-start">
                            <div className="flex-grow-1">
                              <h6 className="mb-1">{similarProject.title}</h6>
                              <p className="mb-1">
                                <strong>Similarity:</strong> {(similarProject.similarity_score * 100).toFixed(1)}% |
                                <strong> Status:</strong> {similarProject.status} |
                                <strong> Year:</strong> {similarProject.year}
                              </p>
                              <small className="text-muted">
                                Students: {getProjectStudents(similarProject.id).join(', ') || 'No students assigned'}
                              </small>
                              {similarProject.reviewed && (
                                <div className="mt-2">
                                  <span className="badge bg-success">Reviewed</span>
                                </div>
                              )}
                            </div>
                            <div className="d-flex flex-column gap-2">
                              {!similarProject.reviewed && (
                                <button
                                  className="btn btn-sm btn-outline-primary"
                                  onClick={() => markFlagReviewed(similarProject.flag_id)}
                                >
                                  Mark Reviewed
                                </button>
                              )}
                              <button
                                className="btn btn-sm btn-outline-info"
                                onClick={() => {
                                  setShowProjectDetailsModal(false);
                                  setTimeout(() => openProjectDetails(similarProject), 100);
                                }}
                              >
                                View Details
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-muted">No similar projects found.</p>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default MentorDashboard;