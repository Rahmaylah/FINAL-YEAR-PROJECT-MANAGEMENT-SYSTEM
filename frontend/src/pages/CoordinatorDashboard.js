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

function CoordinatorDashboard() {
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

  const [selectedUser, setSelectedUser] = useState(null);
  const [showUserModal, setShowUserModal] = useState(false);
  const [userDraft, setUserDraft] = useState({
    first_name: '',
    middle_name: '',
    last_name: '',
    email: '',
    registration_number: '',
    mentor: null
  });
  const [userPassword, setUserPassword] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [userSaving, setUserSaving] = useState(false);
  const [userPasswordSaving, setUserPasswordSaving] = useState(false);
  const [userMessage, setUserMessage] = useState('');

  const [users, setUsers] = useState([]);
  const [mentees, setMentees] = useState([]);
  const [mentorProjects, setMentorProjects] = useState([]);
  const [projectUsers, setProjectUsers] = useState([]);
  const [projects, setProjects] = useState([]);
  const [duplicates, setDuplicates] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [expandedUsers, setExpandedUsers] = useState(false);
  const [expandedProjects, setExpandedProjects] = useState(false);
  const [expandedDuplicates, setExpandedDuplicates] = useState(false);
  const [expandedMentees, setExpandedMentees] = useState(false);
  const [expandedMentorProjects, setExpandedMentorProjects] = useState(false);
  const [selectedProject, setSelectedProject] = useState(null);
  const [showProjectDetailsModal, setShowProjectDetailsModal] = useState(false);
  const [similarProjects, setSimilarProjects] = useState([]);
  const [loadingSimilar, setLoadingSimilar] = useState(false);
  const [projectSaving, setProjectSaving] = useState(false);
  const [projectMessage, setProjectMessage] = useState('');
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [settingsDraft, setSettingsDraft] = useState({
    duplicate_search_years_back: 3,
    duplicate_similarity_threshold: 0.6,
    duplicate_auto_flag_threshold: 0.8,
    duplicate_algorithm: 'HYBRID',
    duplicate_semantic_weight: 0.7,
    duplicate_lexical_weight: 0.3
  });
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [settingsMessage, setSettingsMessage] = useState('');

  // ==================== PRESENTATION CRITERIA STATES ====================
  const [presentations, setPresentations] = useState([]);
  const [expandedPresentations, setExpandedPresentations] = useState(false);
  const [showPresentationModal, setShowPresentationModal] = useState(false);
  const [selectedPresentation, setSelectedPresentation] = useState(null);
  const [presentationDraft, setPresentationDraft] = useState({
    name: '',
    presentation_date: '',
    total_marks: 15.5,
    pass_marks: 8,
    description: ''
  });
  const [presentationSaving, setPresentationSaving] = useState(false);
  const [presentationMessage, setPresentationMessage] = useState('');

  // Criteria states
  const [criteriaList, setCriteriaList] = useState([]);
  const [expandedCriteria, setExpandedCriteria] = useState({});
  const [showCriteriaModal, setShowCriteriaModal] = useState(false);
  const [editingCriteria, setEditingCriteria] = useState(null);
  const [criteriaDraft, setCriteriaDraft] = useState({
    name: '',
    description: '',
    max_score: 10,
    weight: 1,
    order: 0,
    is_required: true,
    options: []
  });
  const [criteriaSaving, setCriteriaSaving] = useState(false);
  const [criteriaMessage, setCriteriaMessage] = useState('');

  // Result grading states
  const [showGradeModal, setShowGradeModal] = useState(false);
  const [gradingResult, setGradingResult] = useState(null);
  const [gradingScores, setGradingScores] = useState({});
  const [gradingSaving, setGradingSaving] = useState(false);
  const [gradingMessage, setGradingMessage] = useState('');
  const [gradingStudent, setGradingStudent] = useState(null);
  const [selectedPresentationForGrading, setSelectedPresentationForGrading] = useState(null);
  const [presentationStudents, setPresentationStudents] = useState([]);
  // ==================== END PRESENTATION CRITERIA STATES ====================

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
      setLoading(true);
      try {
        // Fetch all users
        const usersResponse = await axios.get('/api/users/');
        const usersData = usersResponse.data.results || [];
        setUsers(usersData);

        // Fetch all projects
        const projectsResponse = await axios.get('/api/projects/');
        const projectsData = projectsResponse.data.results || [];
        setProjects(projectsData);

        // Fetch duplicate flags
        const duplicatesResponse = await axios.get('/api/duplicate-flags/');
        const duplicatesData = duplicatesResponse.data.results || [];
        setDuplicates(duplicatesData);

        // Fetch project users
        const projectUsersResponse = await axios.get('/api/project-users/');
        const projectUsersData = projectUsersResponse.data.results || [];
        setProjectUsers(projectUsersData);

        // Fetch presentations
        const presentationsResponse = await axios.get('/api/presentations/');
        const presentationsData = presentationsResponse.data.results || [];
        setPresentations(presentationsData);

        // Fetch criteria for all presentations
        const criteriaResponse = await axios.get('/api/presentation-criteria/');
        const criteriaData = criteriaResponse.data.results || criteriaResponse.data || [];
        setCriteriaList(criteriaData);

        // Calculate mentees and mentor projects based on current coordinator
        const userMentees = usersData.filter(u => u.role === 'student' && (u.mentor === user.id || (u.mentor_info && u.mentor_info.id === user.id)));
        setMentees(userMentees);

        const menteeIds = userMentees.map((student) => student.id);
        const relatedProjectIds = projectUsersData
          .filter((relation) => menteeIds.includes(relation.user))
          .map((relation) => relation.project);
        const filteredProjectIds = [...new Set(relatedProjectIds)];
        const userMentorProjects = projectsData.filter((project) => filteredProjectIds.includes(project.id));
        setMentorProjects(userMentorProjects);

        const settingsResponse = await axios.get('/api/settings/');
        setSettingsDraft({
          duplicate_search_years_back: settingsResponse.data.duplicate_search_years_back,
          duplicate_similarity_threshold: settingsResponse.data.duplicate_similarity_threshold,
          duplicate_auto_flag_threshold: settingsResponse.data.duplicate_auto_flag_threshold,
          duplicate_algorithm: settingsResponse.data.duplicate_algorithm,
          duplicate_semantic_weight: settingsResponse.data.duplicate_semantic_weight,
          duplicate_lexical_weight: settingsResponse.data.duplicate_lexical_weight
        });

        // Calculate stats
        const totalUsers = usersResponse.data.count || usersData.length;
        const totalProjects = projectsResponse.data.count || projectsData.length;
        const approvedProjects = projectsData.filter(p => p.status === 'approved').length;
        const flaggedDuplicates = duplicatesResponse.data.count || duplicatesData.length;
        const mentors = usersData.filter(u => u.role === 'mentor').length;
        const students = usersData.filter(u => u.role === 'student').length;

        setStats({
          totalUsers,
          totalProjects,
          approvedProjects,
          flaggedDuplicates,
          mentors,
          students
        });

      } catch (error) {
        console.error('Error fetching coordinator dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // ==================== PRESENTATION CRITERIA FUNCTIONS ====================

  // Fetch criteria for a specific presentation
  const fetchCriteria = async (presentationId) => {
    try {
      const response = await axios.get('/api/presentation-criteria/?presentation=' + presentationId);
      const criteria = response.data.results || response.data || [];
      setCriteriaList(prev => {
        const otherCriteria = prev.filter(c => c.presentation !== presentationId);
        return [...otherCriteria, ...criteria];
      });
      setExpandedCriteria(prev => ({ ...prev, [presentationId]: true }));
      return criteria;
    } catch (error) {
      console.error('Error fetching criteria:', error);
      return [];
    }
  };

  // Fetch students for a presentation
  const fetchPresentationStudents = async (presentationId) => {
    try {
      const response = await axios.get('/api/presentation-results/?presentation=' + presentationId);
      const results = response.data.results || response.data || [];
      
      if (results.length === 0) {
        const studentsWithProjects = mentees.filter(m => 
          mentorProjects.some(p => p.project_users?.some(pu => pu.user === m.id))
        );
        setPresentationStudents(studentsWithProjects);
        return studentsWithProjects;
      }
      
      const studentsWithResults = [];
      for (const result of results) {
        try {
          const studentResponse = await axios.get('/api/users/' + result.student + '/');
          studentsWithResults.push({
            ...studentResponse.data,
            result_id: result.id,
            result: result
          });
        } catch (err) {
          console.error('Error fetching student:', err);
        }
      }
      
      setPresentationStudents(studentsWithResults);
      return studentsWithResults;
    } catch (error) {
      console.error('Error fetching presentation students:', error);
      return [];
    }
  };

  // Open presentation modal
  const openPresentationModal = (presentation = null) => {
    setSelectedPresentation(presentation);
    if (presentation) {
      setPresentationDraft({
        name: presentation.name || '',
        presentation_date: presentation.presentation_date || '',
        total_marks: presentation.total_marks || 15.5,
        pass_marks: presentation.pass_marks || 8,
        description: presentation.description || ''
      });
    } else {
      setPresentationDraft({
        name: '',
        presentation_date: '',
        total_marks: 15.5,
        pass_marks: 8,
        description: ''
      });
    }
    setShowPresentationModal(true);
    setPresentationMessage('');
  };

  // Save presentation
  const handleSavePresentation = async () => {
    setPresentationSaving(true);
    setPresentationMessage('');
    try {
      const data = {
        ...presentationDraft,
        total_marks: parseFloat(presentationDraft.total_marks),
        pass_marks: parseFloat(presentationDraft.pass_marks)
      };

      let response;
      if (selectedPresentation) {
        response = await axios.put('/api/presentations/' + selectedPresentation.id + '/', data);
        setPresentations(prev => prev.map(p => p.id === selectedPresentation.id ? response.data : p));
        setPresentationMessage('✅ Presentation updated successfully.');
      } else {
        response = await axios.post('/api/presentations/', data);
        setPresentations(prev => [...prev, response.data]);
        setPresentationMessage('✅ Presentation created successfully.');
      }
      setShowPresentationModal(false);
      const presentationsResponse = await axios.get('/api/presentations/');
      setPresentations(presentationsResponse.data.results || []);
    } catch (error) {
      console.error('Error saving presentation:', error);
      setPresentationMessage('❌ Unable to save presentation. Please try again.');
    } finally {
      setPresentationSaving(false);
    }
  };

  // Delete presentation
  const handleDeletePresentation = async (id) => {
    if (!window.confirm('Are you sure you want to delete this presentation?')) return;
    try {
      await axios.delete('/api/presentations/' + id + '/');
      setPresentations(prev => prev.filter(p => p.id !== id));
      setPresentationMessage('✅ Presentation deleted successfully.');
    } catch (error) {
      console.error('Error deleting presentation:', error);
      setPresentationMessage('❌ Unable to delete presentation.');
    }
  };

  // ====== OPEN CRITERIA MODAL ======
  const openCriteriaModal = (criteria = null, presentationId = null) => {
    console.log('Opening criteria modal...', { criteria, presentationId });
    if (criteria) {
      setEditingCriteria(criteria);
      setCriteriaDraft({
        name: criteria.name || '',
        description: criteria.description || '',
        max_score: criteria.max_score || 10,
        weight: criteria.weight || 1,
        order: criteria.order || 0,
        is_required: criteria.is_required !== undefined ? criteria.is_required : true,
        options: criteria.options || [],
        presentation: criteria.presentation
      });
    } else {
      setEditingCriteria(null);
      setCriteriaDraft({
        name: '',
        description: '',
        max_score: 10,
        weight: 1,
        order: criteriaList.filter(c => c.presentation === presentationId).length,
        is_required: true,
        options: [],
        presentation: presentationId
      });
    }
    setShowCriteriaModal(true);
    setCriteriaMessage('');
  };

  // Save criteria
  const handleSaveCriteria = async () => {
    setCriteriaSaving(true);
    setCriteriaMessage('');
    try {
      const data = {
        ...criteriaDraft,
        max_score: parseFloat(criteriaDraft.max_score),
        weight: parseFloat(criteriaDraft.weight),
        order: parseInt(criteriaDraft.order) || 0
      };

      let response;
      if (editingCriteria) {
        response = await axios.put('/api/presentation-criteria/' + editingCriteria.id + '/', data);
        setCriteriaList(prev => prev.map(c => c.id === editingCriteria.id ? response.data : c));
        setCriteriaMessage('✅ Criteria updated successfully.');
      } else {
        response = await axios.post('/api/presentation-criteria/', data);
        setCriteriaList(prev => [...prev, response.data]);
        setCriteriaMessage('✅ Criteria created successfully.');
      }
      setShowCriteriaModal(false);
      if (data.presentation) {
        await fetchCriteria(data.presentation);
      }
    } catch (error) {
      console.error('Error saving criteria:', error);
      setCriteriaMessage('❌ Unable to save criteria. Please try again.');
    } finally {
      setCriteriaSaving(false);
    }
  };

  // Delete criteria
  const handleDeleteCriteria = async (id) => {
    if (!window.confirm('Are you sure you want to delete this criteria?')) return;
    try {
      const criteria = criteriaList.find(c => c.id === id);
      const presentationId = criteria?.presentation;
      await axios.delete('/api/presentation-criteria/' + id + '/');
      setCriteriaList(prev => prev.filter(c => c.id !== id));
      setCriteriaMessage('✅ Criteria deleted successfully.');
      if (presentationId) {
        await fetchCriteria(presentationId);
      }
    } catch (error) {
      console.error('Error deleting criteria:', error);
      setCriteriaMessage('❌ Unable to delete criteria.');
    }
  };

  // Add option to criteria
  const handleAddOption = () => {
    setCriteriaDraft(prev => ({
      ...prev,
      options: [...prev.options, { label: '', value: 0 }]
    }));
  };

  const handleOptionChange = (index, field, value) => {
    const newOptions = [...criteriaDraft.options];
    if (field === 'value') {
      newOptions[index][field] = parseFloat(value) || 0;
    } else {
      newOptions[index][field] = value;
    }
    setCriteriaDraft(prev => ({ ...prev, options: newOptions }));
  };

  const handleRemoveOption = (index) => {
    setCriteriaDraft(prev => ({
      ...prev,
      options: prev.options.filter((_, i) => i !== index)
    }));
  };

  // Open grading form
  const openGradingForm = async (presentationId) => {
    setSelectedPresentationForGrading(presentationId);
    setGradingStudent(null);
    setGradingScores({});
    setGradingMessage('');
    setGradingResult(null);
    setShowGradeModal(true);

    await fetchCriteria(presentationId);
    await fetchPresentationStudents(presentationId);
  };

  // Handle student selection in grading form
  const handleStudentSelect = async (studentId) => {
    const student = presentationStudents.find(s => s.id === parseInt(studentId));
    if (!student) return;
    
    setGradingStudent(student);
    setGradingScores({});
    setGradingResult(null);

    try {
      const response = await axios.get('/api/presentation-results/?presentation=' + selectedPresentationForGrading + '&student=' + student.id);
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
      }
    } catch (error) {
      console.error('Error fetching student result:', error);
    }
  };

  // Save grades
  const handleSaveStudentGrade = async () => {
    if (!gradingStudent) {
      setGradingMessage('❌ Please select a student first.');
      return;
    }

    setGradingSaving(true);
    setGradingMessage('');

    try {
      let resultId = gradingResult?.id;
      
      if (!resultId) {
        const studentProject = mentorProjects.find(p => 
          p.project_users?.some(pu => pu.user === gradingStudent.id)
        );
        
        const resultResponse = await axios.post('/api/presentation-results/', {
          presentation: selectedPresentationForGrading,
          student: gradingStudent.id,
          project: studentProject?.id || null,
          comment: '',
          marks: null
        });
        resultId = resultResponse.data.id;
        setGradingResult(resultResponse.data);
      }

      const scores = Object.entries(gradingScores).map(([criteriaId, data]) => ({
        criteria_id: parseInt(criteriaId),
        score: data.score !== undefined && data.score !== '' ? parseFloat(data.score) : null,
        selected_option: data.selected_option || '',
        comment: data.comment || ''
      }));

      for (const scoreData of scores) {
        const existingResponse = await axios.get('/api/presentation-result-criteria/?result=' + resultId + '&criteria=' + scoreData.criteria_id);
        const existing = existingResponse.data.results || existingResponse.data || [];
        
        if (existing.length > 0) {
          await axios.put('/api/presentation-result-criteria/' + existing[0].id + '/', {
            result: resultId,
            criteria: scoreData.criteria_id,
            score: scoreData.score,
            selected_option: scoreData.selected_option,
            comment: scoreData.comment
          });
        } else {
          await axios.post('/api/presentation-result-criteria/', {
            result: resultId,
            criteria: scoreData.criteria_id,
            score: scoreData.score,
            selected_option: scoreData.selected_option,
            comment: scoreData.comment
          });
        }
      }

      await axios.post('/api/presentation-results/' + resultId + '/calculate_total/');
      
      setGradingMessage('✅ Grades saved successfully.');
      setTimeout(() => {
        setShowGradeModal(false);
      }, 1500);
    } catch (error) {
      console.error('Error saving grades:', error);
      setGradingMessage('❌ Unable to save grades. Please try again.');
    } finally {
      setGradingSaving(false);
    }
  };

  // Toggle presentations
  const togglePresentations = () => {
    setExpandedPresentations(!expandedPresentations);
    if (!expandedPresentations) {
      const fetchPresentations = async () => {
        try {
          const response = await axios.get('/api/presentations/');
          setPresentations(response.data.results || []);
        } catch (error) {
          console.error('Error fetching presentations:', error);
        }
      };
      fetchPresentations();
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

  const handleSettingsChange = (event) => {
    const { name, value } = event.target;
    const numericFields = new Set([
      'duplicate_search_years_back',
      'duplicate_similarity_threshold',
      'duplicate_auto_flag_threshold',
      'duplicate_semantic_weight',
      'duplicate_lexical_weight'
    ]);

    setSettingsDraft((prev) => ({
      ...prev,
      [name]: numericFields.has(name) ? Number(value) : value
    }));
  };

  const handleSaveSettings = async () => {
    setSettingsSaving(true);
    setSettingsMessage('');
    try {
      const response = await axios.put('/api/settings/', settingsDraft);
      setSettingsDraft({
        duplicate_search_years_back: response.data.duplicate_search_years_back,
        duplicate_similarity_threshold: response.data.duplicate_similarity_threshold,
        duplicate_auto_flag_threshold: response.data.duplicate_auto_flag_threshold,
        duplicate_algorithm: response.data.duplicate_algorithm,
        duplicate_semantic_weight: response.data.duplicate_semantic_weight,
        duplicate_lexical_weight: response.data.duplicate_lexical_weight
      });
      setSettingsMessage('Settings saved successfully.');
    } catch (error) {
      console.error('Error saving settings:', error);
      if (error.response?.data) {
        setSettingsMessage(JSON.stringify(error.response.data));
      } else {
        setSettingsMessage('Unable to save settings. Please try again.');
      }
    } finally {
      setSettingsSaving(false);
    }
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
      setProfileMessage('Profile updated successfully.');
      localStorage.setItem('user', JSON.stringify({ ...user, ...response.data }));
    } catch (error) {
      console.error('Error saving profile:', error);
      setProfileMessage('Unable to update profile. Please try again.');
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
      setPasswordMessage('New passwords do not match.');
      setPasswordSaving(false);
      return;
    }

    try {
      await axios.post('/api/users/' + user.id + '/set_password/', {
        current_password: passwordData.current_password,
        new_password: passwordData.new_password
      });
      setPasswordMessage('Password changed successfully.');
      setPasswordData({
        current_password: '',
        new_password: '',
        confirm_password: ''
      });
      setShowChangePassword(false);
    } catch (error) {
      console.error('Error changing password:', error);
      setPasswordMessage('Unable to change password. Please check your current password.');
    } finally {
      setPasswordSaving(false);
    }
  };

  const openUserModal = (userItem) => {
    setSelectedUser(userItem);
    setShowUserModal(true);
    setUserDraft({
      first_name: userItem.first_name || '',
      middle_name: userItem.middle_name || '',
      last_name: userItem.last_name || '',
      email: userItem.email || '',
      registration_number: userItem.registration_number || '',
      mentor: userItem.mentor || userItem.mentor_info?.id || null
    });
    setUserPassword({ current_password: '', new_password: '', confirm_password: '' });
    setUserMessage('');
  };

  const closeUserModal = () => {
    setSelectedUser(null);
    setShowUserModal(false);
    setUserMessage('');
  };

  const handleUserDraftChange = (event) => {
    const { name, value } = event.target;
    setUserDraft((prev) => ({ ...prev, [name]: value }));
  };

  const handleUserPasswordChange = (event) => {
    const { name, value } = event.target;
    setUserPassword((prev) => ({ ...prev, [name]: value }));
  };

  const handleSaveUser = async () => {
    if (!selectedUser) return;
    
    if (userPassword.new_password || userPassword.confirm_password) {
      if (!userPassword.new_password || !userPassword.confirm_password) {
        setUserMessage('Please fill in both password fields or leave them empty.');
        return;
      }
      if (userPassword.new_password !== userPassword.confirm_password) {
        setUserMessage('New passwords do not match.');
        return;
      }
    }
    
    setUserSaving(true);
    setUserMessage('');
    try {
      const payload = {
        first_name: userDraft.first_name,
        middle_name: userDraft.middle_name,
        last_name: userDraft.last_name,
        email: userDraft.email,
      };
      if (selectedUser.role === 'student') {
        payload.registration_number = userDraft.registration_number;
        payload.mentor = userDraft.mentor || null;
      }

      const response = await axios.patch('/api/users/' + selectedUser.id + '/', payload);
      
      if (userPassword.new_password) {
        if (selectedUser.id === user.id) {
          await axios.post('/api/users/set_password/', {
            current_password: userPassword.current_password || '',
            new_password: userPassword.new_password
          });
        } else {
          await axios.post('/api/users/' + selectedUser.id + '/set_password_by_admin/', {
            new_password: userPassword.new_password
          });
        }
      }
      
      setUsers((prev) => prev.map((u) => (u.id === selectedUser.id ? { ...u, ...response.data } : u)));
      setSelectedUser((prev) => prev ? { ...prev, ...response.data } : prev);
      
      const successMsg = userPassword.new_password 
        ? 'User information and password updated successfully.' 
        : 'User information updated successfully.';
      setUserMessage(successMsg);
      setUserPassword({ current_password: '', new_password: '', confirm_password: '' });
      setTimeout(() => closeUserModal(), 1500);
    } catch (error) {
      console.error('Error updating user:', error);
      setUserMessage('Unable to update user information. Please try again.');
    } finally {
      setUserSaving(false);
    }
  };

  const handleSaveUserPassword = async () => {
    if (!selectedUser) return;
    if (userPassword.new_password !== userPassword.confirm_password) {
      setUserMessage('New passwords do not match.');
      return;
    }
    setUserPasswordSaving(true);
    setUserMessage('');
    try {
      if (selectedUser.id === user.id) {
        await axios.post('/api/users/set_password/', {
          current_password: userPassword.current_password || '',
          new_password: userPassword.new_password
        });
      } else {
        await axios.post('/api/users/' + selectedUser.id + '/set_password_by_admin/', {
          new_password: userPassword.new_password
        });
      }
      setUserMessage('Password changed successfully.');
      setUserPassword({ new_password: '', confirm_password: '' });
    } catch (error) {
      console.error('Error changing user password:', error);
      setUserMessage('Unable to change password. Please try again.');
    } finally {
      setUserPasswordSaving(false);
    }
  };

  const toggleUsers = () => setExpandedUsers(!expandedUsers);
  const toggleProjects = () => setExpandedProjects(!expandedProjects);
  const toggleDuplicates = () => setExpandedDuplicates(!expandedDuplicates);
  const toggleMentees = () => setExpandedMentees(!expandedMentees);
  const toggleMentorProjects = () => setExpandedMentorProjects(!expandedMentorProjects);

  const getProjectStudents = (projectId) => {
    return projectUsers
      .filter((relation) => relation.project === projectId)
      .map((relation) => relation.user_name);
  };

  const openProjectDetails = (project) => {
    setSelectedProject(project);
    setShowProjectDetailsModal(true);

    if (project.is_flagged_duplicate) {
      fetchSimilarProjects(project.id);
    } else {
      setSimilarProjects([]);
    }
  };

  const fetchSimilarProjects = async (projectId) => {
    setLoadingSimilar(true);
    try {
      const response = await axios.get('/api/duplicate-flags/?project=' + projectId);

      let flags = [];
      if (Array.isArray(response.data)) {
        flags = response.data;
      } else if (response.data.results) {
        flags = response.data.results;
      }

      const similarProjectsWithFlags = [];
      for (const flag of flags) {
        try {
          const projectResponse = await axios.get('/api/projects/' + flag.similar_project + '/');
          similarProjectsWithFlags.push({
            ...projectResponse.data,
            similarity_score: flag.similarity_score,
            flag_id: flag.id,
            reviewed: flag.reviewed,
            reviewed_by: flag.reviewed_by,
            reviewed_at: flag.reviewed_at
          });
        } catch (error) {
          console.error('Error fetching project ' + flag.similar_project + ':', error);
        }
      }

      setSimilarProjects(similarProjectsWithFlags);
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
      setDuplicates((prev) =>
        prev.map((flag) => (flag.id === flagId ? { ...flag, reviewed: true } : flag))
      );
      setSimilarProjects((prev) =>
        prev.map((project) =>
          project.flag_id === flagId ? { ...project, reviewed: true } : project
        )
      );
    } catch (error) {
      console.error('Error marking flag as reviewed:', error);
    }
  };

  const handleProjectStatusChange = async (projectId, newStatus) => {
    setProjectSaving(true);
    setProjectMessage('');
    try {
      let response;
      try {
        response = await axios.patch('/api/projects/' + projectId + '/update_status/', { status: newStatus });
      } catch (patchError) {
        response = await axios.patch('/api/projects/' + projectId + '/', { status: newStatus });
      }
      
      setProjects((prevProjects) =>
        prevProjects.map((project) =>
          project.id === projectId ? { ...project, ...response.data } : project
        )
      );
      setSelectedProject((prevProject) =>
        prevProject && prevProject.id === projectId ? { ...prevProject, ...response.data } : prevProject
      );
      setProjectMessage('✅ Project status updated successfully.');
    } catch (error) {
      console.error('Error updating project status:', error);
      setProjectMessage('❌ Unable to update project status. Please try again.');
    } finally {
      setProjectSaving(false);
    }
  };

  const mentors = users.filter((u) => u.role === 'mentor');
  const students = users.filter((u) => u.role === 'student');
  const flaggedProjects = projects.filter((project) => project.is_flagged_duplicate);
  const normalProjects = projects.filter((project) => !project.is_flagged_duplicate);
  const getProjectDuplicateFlags = (projectId) => (
    duplicates.filter((flag) => flag.project === projectId)
  );

  const formatRegistrationNumbers = (registrationNumbers) => {
    if (!Array.isArray(registrationNumbers) || registrationNumbers.length === 0) {
      return 'Reg: N/A';
    }
    return 'Reg: ' + registrationNumbers.join(', ');
  };

  return (
    <div className="dashboard-container admin-dashboard">
      {/* Navbar */}
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
            <span>FYPMS - Coordinator Dashboard</span>
          </span>
          <div className="dropdown ms-auto" style={{ cursor: 'pointer' }}>
            <div
              style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
              onClick={() => setShowUserMenu((prev) => !prev)}
              id="userMenuButton"
              aria-expanded={showUserMenu}
            >
              <span style={{ fontSize: '1rem', color: '#333' }}>
                {profile?.username || profile?.last_name || 'Coordinator'}
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

      <div className="container mt-5">
        {/* Welcome Section */}
        <div className="welcome-section">
          <h1>
            Welcome back, <span className="role-name">{profile.first_name || profile.username || 'Coordinator'}</span>.
          </h1>
          <p className="lead mb-0">View system statistics and analytics</p>

          <hr />
          {loading ? (
            <p>Loading stats...</p>
          ) : (
            <div className="row">
              <div className="col-md-3">
                <div className="card text-center">
                  <div className="card-body">
                    <h3>{stats.totalUsers || 0}</h3>
                    <p>Total Users</p>
                  </div>
                </div>
              </div>
              <div className="col-md-3">
                <div className="card text-center">
                  <div className="card-body">
                    <h3>{stats.totalProjects || 0}</h3>
                    <p>Total Projects</p>
                  </div>
                </div>
              </div>
              <div className="col-md-3">
                <div className="card text-center">
                  <div className="card-body">
                    <h3>{stats.approvedProjects || 0}</h3>
                    <p>Approved Projects</p>
                  </div>
                </div>
              </div>
              <div className="col-md-3">
                <div className="card text-center">
                  <div className="card-body">
                    <h3>{stats.flaggedDuplicates || 0}</h3>
                    <p>Flagged Duplicates</p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="row mt-5">

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
                maxHeight: '80vh',
                overflow: 'auto',
                boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
              }} onClick={(e) => e.stopPropagation()}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                  <h5 style={{ margin: 0 }}>👤 Profile Settings</h5>
                  <button style={{ background: 'none', border: 'none', fontSize: '1.5em', cursor: 'pointer' }} onClick={() => setProfileExpanded(false)}>
                    ✕
                  </button>
                </div>
                <hr />
                <div>
                  <p><strong>Username:</strong> {profile.username || 'N/A'}</p>
                  <p><strong>Role:</strong> {profile.role || 'N/A'}</p>
                  <div className="mb-3">
                    <label className="form-label"><strong>First Name</strong></label>
                    <input
                      type="text"
                      className="form-control"
                      value={profile.first_name || ''}
                      disabled
                    />
                  </div>
                  <div className="mb-3">
                    <label className="form-label"><strong>Last Name</strong></label>
                    <input
                      type="text"
                      className="form-control"
                      value={profile.last_name || ''}
                      disabled
                    />
                  </div>
                  <div className="mb-3">
                    <label className="form-label"><strong>Middle Name</strong></label>
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
                    <label className="form-label"><strong>Email Address</strong></label>
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
                  {profileMessage && <p className={'mt-3 ' + (profileMessage.includes('successfully') ? 'text-success' : 'text-danger')}>{profileMessage}</p>}
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
                maxHeight: '80vh',
                overflow: 'auto',
                boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
              }} onClick={(e) => e.stopPropagation()}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                  <h5 style={{ margin: 0 }}>🔒 Change Password</h5>
                  <button style={{ background: 'none', border: 'none', fontSize: '1.5em', cursor: 'pointer' }} onClick={() => setShowChangePassword(false)}>
                    ✕
                  </button>
                </div>
                <hr />
                <div>
                  <div className="mb-3">
                    <label className="form-label"><strong>Current Password</strong></label>
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
                    <label className="form-label"><strong>New Password</strong></label>
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
                    <label className="form-label"><strong>Confirm New Password</strong></label>
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
                  {passwordMessage && <p className={'mt-3 ' + (passwordMessage.includes('successfully') ? 'text-success' : 'text-danger')}>{passwordMessage}</p>}
                </div>
              </div>
            </div>
          )}

          {/* Users Section */}
          <div className="col-md-12 mb-4">
            <div className="card dashboard-card">
              <div className="card-body">
                <div
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
                  onClick={toggleUsers}
                >
                  <div>
                    <h5 className="card-title" style={{ marginBottom: 0 }}>👥 Manage Users</h5>
                    <p className="card-text">View and manage all system users</p>
                  </div>
                  <span
                    style={{
                      fontSize: '1.5em',
                      color: '#2a2d32',
                      transform: expandedUsers ? 'rotate(0deg)' : 'rotate(-90deg)',
                      transition: 'transform 0.03s ease'
                    }}
                  >
                    ▼
                  </span>
                </div>

                {expandedUsers && (
                  <>
                    <hr />
                    {loading ? (
                      <p>Loading users...</p>
                    ) : (
                      <>
                        <div className="mb-4">
                          <h6>👨‍🏫 Mentors</h6>
                          {mentors.length > 0 ? (
                            <div className="table-responsive">
                              <table className="table table-striped">
                                <thead>
                                  <tr>
                                    <th>Name</th>
                                    <th>Username</th>
                                    <th>Email</th>
                                    <th>Actions</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {mentors.map((mentor) => (
                                    <tr key={mentor.id}>
                                      <td>{mentor.first_name} {mentor.middle_name || ''} {mentor.last_name}</td>
                                      <td>{mentor.username}</td>
                                      <td>{mentor.email}</td>
                                      <td>
                                        <button className="btn btn-sm btn-primary" onClick={() => openUserModal(mentor)}>
                                          ✏️ Edit
                                        </button>
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          ) : (
                            <p>No mentors found.</p>
                          )}
                        </div>

                        <div>
                          <h6>👨‍🎓 Students</h6>
                          {students.length > 0 ? (
                            <div className="table-responsive">
                              <table className="table table-striped">
                                <thead>
                                  <tr>
                                    <th>Name</th>
                                    <th>Username</th>
                                    <th>Email</th>
                                    <th>Registration #</th>
                                    <th>Mentor</th>
                                    <th>Actions</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {students.map((student) => (
                                    <tr key={student.id}>
                                      <td>{student.first_name} {student.middle_name || ''} {student.last_name}</td>
                                      <td>{student.username}</td>
                                      <td>{student.email}</td>
                                      <td>{student.registration_number || 'N/A'}</td>
                                      <td>{student.mentor_info ? student.mentor_info.first_name + ' ' + student.mentor_info.last_name : 'Not assigned'}</td>
                                      <td>
                                        <button className="btn btn-sm btn-primary" onClick={() => openUserModal(student)}>
                                          ✏️ Edit
                                        </button>
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          ) : (
                            <p>No students found.</p>
                          )}
                        </div>
                      </>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* User Modal */}
        {showUserModal && selectedUser && (
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
          }} onClick={closeUserModal}>
            <div style={{
              backgroundColor: 'white',
              borderRadius: '8px',
              padding: '30px',
              width: '90%',
              maxWidth: '600px',
              maxHeight: '90vh',
              overflow: 'auto',
              boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
            }} onClick={(e) => e.stopPropagation()}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <div>
                  <h5 style={{ margin: 0 }}>✏️ Edit User Profile</h5>
                  <small className="text-muted">{selectedUser.username} ({selectedUser.role})</small>
                </div>
                <button style={{ background: 'none', border: 'none', fontSize: '1.5em', cursor: 'pointer' }} onClick={closeUserModal}>
                  ✕
                </button>
              </div>
              <hr />
              <div>
                <div className="mb-3">
                  <label className="form-label"><strong>First Name</strong></label>
                  <input
                    type="text"
                    name="first_name"
                    className="form-control"
                    value={userDraft.first_name}
                    onChange={handleUserDraftChange}
                  />
                </div>
                <div className="mb-3">
                  <label className="form-label"><strong>Middle Name</strong></label>
                  <input
                    type="text"
                    name="middle_name"
                    className="form-control"
                    value={userDraft.middle_name}
                    onChange={handleUserDraftChange}
                  />
                </div>
                <div className="mb-3">
                  <label className="form-label"><strong>Last Name</strong></label>
                  <input
                    type="text"
                    name="last_name"
                    className="form-control"
                    value={userDraft.last_name}
                    onChange={handleUserDraftChange}
                  />
                </div>
                <div className="mb-3">
                  <label className="form-label"><strong>Email</strong></label>
                  <input
                    type="email"
                    name="email"
                    className="form-control"
                    value={userDraft.email}
                    onChange={handleUserDraftChange}
                  />
                </div>
                {selectedUser.role === 'student' && (
                  <>
                    <div className="mb-3">
                      <label className="form-label"><strong>Registration Number</strong></label>
                      <input
                        type="text"
                        name="registration_number"
                        className="form-control"
                        value={userDraft.registration_number}
                        onChange={handleUserDraftChange}
                      />
                    </div>
                    <div className="mb-3">
                      <label className="form-label"><strong>Assigned Mentor</strong></label>
                      <select
                        name="mentor"
                        className="form-select"
                        value={userDraft.mentor || ''}
                        onChange={handleUserDraftChange}
                      >
                        <option value="">No mentor assigned</option>
                        {mentors.map((mentor) => (
                          <option key={mentor.id} value={mentor.id}>
                            {mentor.first_name} {mentor.middle_name || ''} {mentor.last_name}
                          </option>
                        ))}
                      </select>
                    </div>
                  </>
                )}
                <div className="d-flex gap-2 mb-3">
                  <button className="btn btn-primary" onClick={handleSaveUser} disabled={userSaving}>
                    {userSaving ? 'Saving...' : '💾 Save User'}
                  </button>
                  <button className="btn btn-outline-secondary" onClick={closeUserModal} disabled={userSaving}>
                    Cancel
                  </button>
                </div>
                <hr />
                <h6>🔑 Password</h6>
                {selectedUser.id === user.id && (
                  <div className="mb-3">
                    <label className="form-label"><strong>Current Password</strong></label>
                    <input
                      type="password"
                      name="current_password"
                      className="form-control"
                      value={userPassword.current_password || ''}
                      onChange={handleUserPasswordChange}
                    />
                  </div>
                )}
                <div className="mb-3">
                  <label className="form-label"><strong>New Password</strong></label>
                  <input
                    type="password"
                    name="new_password"
                    className="form-control"
                    value={userPassword.new_password}
                    onChange={handleUserPasswordChange}
                  />
                </div>
                <div className="mb-3">
                  <label className="form-label"><strong>Confirm Password</strong></label>
                  <input
                    type="password"
                    name="confirm_password"
                    className="form-control"
                    value={userPassword.confirm_password}
                    onChange={handleUserPasswordChange}
                  />
                </div>
                <div className="d-flex gap-2">
                  <button className="btn btn-secondary" onClick={handleSaveUserPassword} disabled={userPasswordSaving}>
                    {userPasswordSaving ? 'Saving...' : '💾 Save Password'}
                  </button>
                </div>
                {userMessage && <p className={'mt-3 ' + (userMessage.includes('successfully') ? 'text-success' : 'text-danger')}>{userMessage}</p>}
              </div>
            </div>
          </div>
        )}

        {/* ==================== PRESENTATIONS SECTION ==================== */}
        <div className="row mt-4">
          <div className="col-md-12">
            <div className="card dashboard-card">
              <div className="card-body">
                <div
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
                  onClick={togglePresentations}
                >
                  <div>
                    <h5 className="card-title" style={{ marginBottom: 0 }}>📊 Presentation Management</h5>
                    <p className="card-text">Manage presentations, criteria, and grading</p>
                  </div>
                  <div className="d-flex align-items-center gap-2">
                    <button 
                      className="btn btn-sm btn-primary"
                      onClick={(e) => {
                        e.stopPropagation();
                        openPresentationModal(null);
                      }}
                    >
                      + New Presentation
                    </button>
                    <span
                      style={{
                        fontSize: '1.5em',
                        color: '#2a2d30',
                        transform: expandedPresentations ? 'rotate(0deg)' : 'rotate(-90deg)',
                        transition: 'transform 0.05s ease'
                      }}
                    >
                      ▼
                    </span>
                  </div>
                </div>

                {expandedPresentations && (
                  <>
                    <hr />
                    {loading ? (
                      <p>Loading presentations...</p>
                    ) : presentations.length > 0 ? (
                      presentations.map((presentation) => {
                        const presentationCriteria = criteriaList.filter(c => c.presentation === presentation.id);
                        
                        return (
                          <div key={presentation.id} className="card mb-3 shadow-sm">
                            <div className="card-body">
                              <div className="d-flex justify-content-between align-items-start flex-wrap">
                                <div>
                                  <h6 className="mb-1">{presentation.name || 'Presentation ' + presentation.id}</h6>
                                  <small className="text-muted">
                                    📅 {presentation.presentation_date ? new Date(presentation.presentation_date).toLocaleDateString() : 'Date TBD'} | 
                                    Total: {presentation.total_marks} | 
                                    Pass: {presentation.pass_marks}
                                  </small>
                                  <div className="mt-1">
                                    <span className="badge bg-info">{presentationCriteria.length} criteria</span>
                                  </div>
                                </div>
                                <div className="d-flex gap-2 flex-wrap">
                                  <button 
                                    className="btn btn-sm btn-outline-primary"
                                    onClick={() => fetchCriteria(presentation.id)}
                                  >
                                    📋 Criteria
                                  </button>
                                  <button 
                                    className="btn btn-sm btn-success"
                                    onClick={() => openGradingForm(presentation.id)}
                                  >
                                    🎯 Grade Students
                                  </button>
                                  <button 
                                    className="btn btn-sm btn-outline-success"
                                    onClick={() => openPresentationModal(presentation)}
                                  >
                                    ✏️ Edit
                                  </button>
                                  <button 
                                    className="btn btn-sm btn-outline-danger"
                                    onClick={() => handleDeletePresentation(presentation.id)}
                                  >
                                    🗑️ Delete
                                  </button>
                                </div>
                              </div>

                              {/* Display Criteria */}
                              {expandedCriteria[presentation.id] && (
                                <div className="mt-3">
                                  <div className="d-flex justify-content-between align-items-center">
                                    <h6 className="mb-2">📋 Criteria</h6>
                                    <button 
                                      className="btn btn-sm btn-primary"
                                      onClick={() => openCriteriaModal(null, presentation.id)}
                                    >
                                      + Add Criteria
                                    </button>
                                  </div>
                                  {presentationCriteria.length > 0 ? (
                                    <div className="list-group mt-2">
                                      {presentationCriteria
                                        .sort((a, b) => a.order - b.order)
                                        .map((criteria) => (
                                          <div key={criteria.id} className="list-group-item">
                                            <div className="d-flex justify-content-between align-items-center">
                                              <div>
                                                <strong>{criteria.name}</strong>
                                                <span className="badge bg-secondary ms-2">{criteria.max_score} pts</span>
                                                {criteria.options && criteria.options.length > 0 && (
                                                  <span className="badge bg-info ms-2">Dropdown</span>
                                                )}
                                                <div className="small text-muted">{criteria.description}</div>
                                              </div>
                                              <div className="d-flex gap-2">
                                                <button 
                                                  className="btn btn-sm btn-outline-secondary"
                                                  onClick={() => openCriteriaModal(criteria)}
                                                >
                                                  ✏️ Edit
                                                </button>
                                                <button 
                                                  className="btn btn-sm btn-outline-danger"
                                                  onClick={() => handleDeleteCriteria(criteria.id)}
                                                >
                                                  🗑️
                                                </button>
                                              </div>
                                            </div>
                                          </div>
                                        ))}
                                    </div>
                                  ) : (
                                    <p className="text-muted">No criteria defined yet.</p>
                                  )}
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })
                    ) : (
                      <p>No presentations found. Create one!</p>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
        {/* ==================== END PRESENTATIONS SECTION ==================== */}

        {/* Projects Section */}
        <div className="row mt-4">
          <div className="col-md-12">
            <div className="card dashboard-card">
              <div className="card-body">
                <div
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
                  onClick={toggleProjects}
                >
                  <div>
                    <h5 className="card-title" style={{ marginBottom: 0 }}>📋 Unflagged Projects</h5>
                    <p className="card-text">Review and manage projects that are not flagged as duplicates</p>
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
                        <div>
                          <h6>Unflagged Projects</h6>
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
                                        <strong>Status:</strong> {project.status}
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
                      <p>No projects found.</p>
                    )}
                    {projectMessage && <p className="mt-3 text-success">{projectMessage}</p>}
                  </>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Duplicate Review Section */}
        <div className="row mt-4">
          <div className="col-md-12">
            <div className="card dashboard-card">
              <div className="card-body">
                <div
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
                  onClick={toggleDuplicates}
                >
                  <div>
                    <h5 className="card-title" style={{ marginBottom: 0 }}>⚠️ Duplicate Review</h5>
                    <p className="card-text">Review and manage flagged duplicate projects</p>
                  </div>
                  <span
                    style={{
                      fontSize: '1.5em',
                      color: '#2a2d30',
                      transform: expandedDuplicates ? 'rotate(0deg)' : 'rotate(-90deg)',
                      transition: 'transform 0.03s ease'
                    }}
                  >
                    ▼
                  </span>
                </div>

                {expandedDuplicates && (
                  <>
                    <hr />
                    {loading ? (
                      <p>Loading duplicates...</p>
                    ) : flaggedProjects.length > 0 ? (
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
                                  <strong>Status:</strong> {project.status}
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
                    ) : (
                      <p>No flagged duplicates.</p>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Mentees Section */}
        <div className="row mt-4">
          <div className="col-md-12">
            <div className="card dashboard-card">
              <div className="card-body">
                <div
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
                  onClick={toggleMentees}
                >
                  <div>
                    <h5 className="card-title" style={{ marginBottom: 0 }}>👨‍🎓 My Mentees</h5>
                    <p className="card-text">View and manage your assigned students</p>
                  </div>
                  <span
                    style={{
                      fontSize: '1.5em',
                      color: '#2a2d30',
                      transform: expandedMentees ? 'rotate(0deg)' : 'rotate(-90deg)',
                      transition: 'transform 0.05s ease'
                    }}
                  >
                    ▼
                  </span>
                </div>

                {expandedMentees && (
                  <>
                    <hr />
                    {loading ? (
                      <p>Loading students...</p>
                    ) : mentees.length > 0 ? (
                      <ul style={{ marginBottom: 0 }}>
                        {mentees.map((student) => (
                          <li key={student.id} className="mb-3">
                            <strong>{student.first_name} {student.middle_name || ''} {student.last_name}</strong>
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

        {/* Mentee Projects Section */}
        <div className="row mt-4">
          <div className="col-md-12">
            <div className="card dashboard-card">
              <div className="card-body">
                <div
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
                  onClick={toggleMentorProjects}
                >
                  <div>
                    <h5 className="card-title" style={{ marginBottom: 0 }}>📁 My Mentee Projects</h5>
                    <p className="card-text">Review projects from your assigned students</p>
                  </div>
                  <span
                    style={{
                      fontSize: '1.5em',
                      color: '#2a2d30',
                      transform: expandedMentorProjects ? 'rotate(0deg)' : 'rotate(-90deg)',
                      transition: 'transform 0.05s ease'
                    }}
                  >
                    ▼
                  </span>
                </div>

                {expandedMentorProjects && (
                  <>
                    <hr />
                    {loading ? (
                      <p>Loading projects...</p>
                    ) : mentorProjects.length > 0 ? (
                      <div className="list-group">
                        {mentorProjects.map((project) => (
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
                                {project.is_flagged_duplicate && getProjectDuplicateFlags(project.id).length > 0 && (
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
                    ) : (
                      <p>No projects found for your students.</p>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Settings Section */}
        <div className="row mt-4">
          <div className="col-md-6">
            <div className="card dashboard-card">
              <div className="card-body">
                <h5 className="card-title">⚙️ Settings</h5>
                <p className="card-text">Configure system settings and parameters</p>
                <button className="btn btn-secondary" onClick={() => { setShowSettingsModal(true); setSettingsMessage(''); }}>
                  Open Settings
                </button>
              </div>
            </div>
          </div>

          <div className="col-md-6">
            <div className="card dashboard-card">
              <div className="card-body">
                <h5 className="card-title">🔄 Bulk Operations</h5>
                <p className="card-text">Perform bulk operations like mentor assignment and data export</p>
                <button className="btn btn-secondary" disabled>
                  Coming Soon
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ==================== PRESENTATION MODAL ==================== */}
      {showPresentationModal && (
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
        }} onClick={() => setShowPresentationModal(false)}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '8px',
            padding: '30px',
            width: '90%',
            maxWidth: '600px',
            maxHeight: '85vh',
            overflow: 'auto',
            boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
          }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h5 style={{ margin: 0 }}>{selectedPresentation ? '✏️ Edit Presentation' : '➕ New Presentation'}</h5>
              <button style={{ background: 'none', border: 'none', fontSize: '1.5em', cursor: 'pointer' }} onClick={() => setShowPresentationModal(false)}>
                ✕
              </button>
            </div>
            <hr />
            <div>
              <div className="mb-3">
                <label className="form-label"><strong>Name</strong></label>
                <input
                  type="text"
                  className="form-control"
                  value={presentationDraft.name}
                  onChange={(e) => setPresentationDraft({ ...presentationDraft, name: e.target.value })}
                  placeholder="Enter presentation name"
                />
              </div>
              <div className="mb-3">
                <label className="form-label"><strong>Date</strong></label>
                <input
                  type="date"
                  className="form-control"
                  value={presentationDraft.presentation_date}
                  onChange={(e) => setPresentationDraft({ ...presentationDraft, presentation_date: e.target.value })}
                />
              </div>
              <div className="row">
                <div className="col-md-6 mb-3">
                  <label className="form-label"><strong>Total Marks</strong></label>
                  <input
                    type="number"
                    step="0.5"
                    className="form-control"
                    value={presentationDraft.total_marks}
                    onChange={(e) => setPresentationDraft({ ...presentationDraft, total_marks: e.target.value })}
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label className="form-label"><strong>Pass Marks</strong></label>
                  <input
                    type="number"
                    step="0.5"
                    className="form-control"
                    value={presentationDraft.pass_marks}
                    onChange={(e) => setPresentationDraft({ ...presentationDraft, pass_marks: e.target.value })}
                  />
                </div>
              </div>
              <div className="mb-3">
                <label className="form-label"><strong>Description</strong></label>
                <textarea
                  className="form-control"
                  rows="3"
                  value={presentationDraft.description}
                  onChange={(e) => setPresentationDraft({ ...presentationDraft, description: e.target.value })}
                  placeholder="Enter description"
                />
              </div>
              <div className="d-flex gap-2">
                <button className="btn btn-primary" onClick={handleSavePresentation} disabled={presentationSaving}>
                  {presentationSaving ? 'Saving...' : 'Save Presentation'}
                </button>
                <button className="btn btn-outline-secondary" onClick={() => setShowPresentationModal(false)}>
                  Cancel
                </button>
              </div>
              {presentationMessage && <p className={'mt-3 ' + (presentationMessage.includes('✅') ? 'text-success' : 'text-danger')}>{presentationMessage}</p>}
            </div>
          </div>
        </div>
      )}

      {/* ==================== CRITERIA MODAL ==================== */}
      {showCriteriaModal && (
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
        }} onClick={() => setShowCriteriaModal(false)}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '8px',
            padding: '30px',
            width: '90%',
            maxWidth: '600px',
            maxHeight: '85vh',
            overflow: 'auto',
            boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
          }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h5 style={{ margin: 0 }}>{editingCriteria ? '✏️ Edit Criteria' : '➕ New Criteria'}</h5>
              <button style={{ background: 'none', border: 'none', fontSize: '1.5em', cursor: 'pointer' }} onClick={() => setShowCriteriaModal(false)}>
                ✕
              </button>
            </div>
            <hr />
            <div>
              <div className="mb-3">
                <label className="form-label"><strong>Criteria Name</strong></label>
                <input
                  type="text"
                  className="form-control"
                  value={criteriaDraft.name}
                  onChange={(e) => setCriteriaDraft({ ...criteriaDraft, name: e.target.value })}
                  placeholder="e.g., Comment Implementation, Type, Practical Progress"
                />
              </div>
              <div className="mb-3">
                <label className="form-label"><strong>Description</strong></label>
                <textarea
                  className="form-control"
                  rows="2"
                  value={criteriaDraft.description}
                  onChange={(e) => setCriteriaDraft({ ...criteriaDraft, description: e.target.value })}
                  placeholder="Describe the criteria and how to score"
                />
              </div>
              <div className="row">
                <div className="col-md-6 mb-3">
                  <label className="form-label"><strong>Max Score</strong></label>
                  <input
                    type="number"
                    step="0.5"
                    className="form-control"
                    value={criteriaDraft.max_score}
                    onChange={(e) => setCriteriaDraft({ ...criteriaDraft, max_score: e.target.value })}
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label className="form-label"><strong>Weight</strong></label>
                  <input
                    type="number"
                    step="0.1"
                    className="form-control"
                    value={criteriaDraft.weight}
                    onChange={(e) => setCriteriaDraft({ ...criteriaDraft, weight: e.target.value })}
                  />
                </div>
              </div>
              <div className="row">
                <div className="col-md-6 mb-3">
                  <label className="form-label"><strong>Order</strong></label>
                  <input
                    type="number"
                    className="form-control"
                    value={criteriaDraft.order}
                    onChange={(e) => setCriteriaDraft({ ...criteriaDraft, order: e.target.value })}
                  />
                </div>
                <div className="col-md-6 mb-3">
                  <label className="form-label"><strong>Required</strong></label>
                  <select
                    className="form-select"
                    value={criteriaDraft.is_required ? 'true' : 'false'}
                    onChange={(e) => setCriteriaDraft({ ...criteriaDraft, is_required: e.target.value === 'true' })}
                  >
                    <option value="true">Yes</option>
                    <option value="false">No</option>
                  </select>
                </div>
              </div>

              {/* Options for dropdown type criteria */}
              <div className="mb-3">
                <label className="form-label"><strong>Options (for dropdown/select criteria)</strong></label>
                <div className="small text-muted mb-2">Add options like "Embedded", "Web App", "Good progress", etc.</div>
                {criteriaDraft.options.map((option, index) => (
                  <div key={index} className="d-flex gap-2 mb-2 align-items-center">
                    <input
                      type="text"
                      className="form-control"
                      placeholder="Label"
                      value={option.label}
                      onChange={(e) => handleOptionChange(index, 'label', e.target.value)}
                    />
                    <input
                      type="number"
                      step="0.5"
                      className="form-control"
                      placeholder="Value"
                      style={{ width: '100px' }}
                      value={option.value}
                      onChange={(e) => handleOptionChange(index, 'value', e.target.value)}
                    />
                    <button className="btn btn-sm btn-danger" onClick={() => handleRemoveOption(index)}>✕</button>
                  </div>
                ))}
                <button className="btn btn-sm btn-outline-secondary" onClick={handleAddOption}>
                  + Add Option
                </button>
              </div>

              <div className="d-flex gap-2">
                <button className="btn btn-primary" onClick={handleSaveCriteria} disabled={criteriaSaving}>
                  {criteriaSaving ? 'Saving...' : 'Save Criteria'}
                </button>
                <button className="btn btn-outline-secondary" onClick={() => setShowCriteriaModal(false)}>
                  Cancel
                </button>
              </div>
              {criteriaMessage && <p className={'mt-3 ' + (criteriaMessage.includes('✅') ? 'text-success' : 'text-danger')}>{criteriaMessage}</p>}
            </div>
          </div>
        </div>
      )}

      {/* ==================== GRADING MODAL ==================== */}
      {showGradeModal && (
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
        }} onClick={() => setShowGradeModal(false)}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '8px',
            padding: '30px',
            width: '90%',
            maxWidth: '650px',
            maxHeight: '85vh',
            overflow: 'auto',
            boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
          }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h5 style={{ margin: 0 }}>📊 Grade Students</h5>
              <button style={{ background: 'none', border: 'none', fontSize: '1.5em', cursor: 'pointer' }} onClick={() => setShowGradeModal(false)}>
                ✕
              </button>
            </div>
            <hr />

            {(() => {
              const pres = presentations.find(p => p.id === selectedPresentationForGrading);
              return (
                <div className="mb-3">
                  <label className="form-label"><strong>Select Presentation</strong></label>
                  <div className="form-control" style={{ backgroundColor: '#f8f9fa' }}>
                    {pres?.name || 'Presentation ' + selectedPresentationForGrading} - {pres?.presentation_date || 'Date TBD'}
                  </div>
                  <div className="mt-2">
                    <strong>Maximum Marks:</strong> {pres?.total_marks || 'N/A'} | 
                    <strong> Pass Marks:</strong> {pres?.pass_marks || 'N/A'}
                  </div>
                </div>
              );
            })()}

            <div className="mb-3">
              <label className="form-label"><strong>Select Student</strong></label>
              <select 
                className="form-select"
                value={gradingStudent?.id || ''}
                onChange={(e) => handleStudentSelect(e.target.value)}
              >
                <option value="">-- Select Student --</option>
                {presentationStudents.map((student) => (
                  <option key={student.id} value={student.id}>
                    {student.first_name} {student.last_name}
                  </option>
                ))}
              </select>
            </div>

            {gradingStudent && (
              <>
                <hr />
                <h6 className="mb-3">📋 Grading Criteria for {gradingStudent.first_name} {gradingStudent.last_name}</h6>

                {criteriaList.filter(c => c.presentation === selectedPresentationForGrading).length > 0 ? (
                  criteriaList
                    .filter(c => c.presentation === selectedPresentationForGrading)
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
                              </div>
                              <div style={{ minWidth: '150px' }}>
                                {criteria.options && criteria.options.length > 0 ? (
                                  <select
                                    className="form-select form-select-sm"
                                    value={scoreData.selected_option || ''}
                                    onChange={(e) => {
                                      const selected = criteria.options.find(o => o.label === e.target.value);
                                      setGradingScores(prev => ({
                                        ...prev,
                                        [criteria.id]: {
                                          ...prev[criteria.id],
                                          selected_option: e.target.value,
                                          score: selected ? selected.value : null
                                        }
                                      }));
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
                                      setGradingScores(prev => ({
                                        ...prev,
                                        [criteria.id]: {
                                          ...prev[criteria.id],
                                          score: val
                                        }
                                      }));
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
                                onChange={(e) => {
                                  setGradingScores(prev => ({
                                    ...prev,
                                    [criteria.id]: {
                                      ...prev[criteria.id],
                                      comment: e.target.value
                                    }
                                  }));
                                }}
                              />
                            </div>
                          </div>
                        </div>
                      );
                    })
                ) : (
                  <div className="alert alert-warning">
                    <p className="mb-0">⚠️ No criteria defined for this presentation.</p>
                    <button 
                      className="btn btn-sm btn-primary mt-2"
                      onClick={() => {
                        setShowGradeModal(false);
                        openCriteriaModal(null, selectedPresentationForGrading);
                      }}
                    >
                      + Add Criteria Now
                    </button>
                  </div>
                )}

                <div className="d-flex gap-2 mt-3">
                  <button className="btn btn-primary" onClick={handleSaveStudentGrade} disabled={gradingSaving}>
                    {gradingSaving ? 'Saving...' : '💾 Save Presentation Marks'}
                  </button>
                  <button className="btn btn-outline-secondary" onClick={() => setShowGradeModal(false)}>
                    Cancel
                  </button>
                </div>
                {gradingMessage && <p className={'mt-3 ' + (gradingMessage.includes('✅') ? 'text-success' : 'text-danger')}>{gradingMessage}</p>}
              </>
            )}

            {!gradingStudent && (
              <div className="alert alert-info">
                <p className="mb-0">👆 Please select a student to start grading.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Settings Modal */}
      {showSettingsModal && (
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
        }} onClick={() => setShowSettingsModal(false)}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '8px',
            padding: '30px',
            width: '90%',
            maxWidth: '640px',
            maxHeight: '85vh',
            overflow: 'auto',
            boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
          }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h5 style={{ margin: 0 }}>⚙️ System Settings</h5>
              <button style={{ background: 'none', border: 'none', fontSize: '1.5em', cursor: 'pointer' }} onClick={() => setShowSettingsModal(false)}>
                ✕
              </button>
            </div>
            <hr />
            <div className="mb-3">
              <label className="form-label"><strong>Duplicate Algorithm</strong></label>
              <select
                className="form-select"
                name="duplicate_algorithm"
                value={settingsDraft.duplicate_algorithm}
                onChange={handleSettingsChange}
              >
                <option value="HYBRID">Hybrid</option>
                <option value="EMBEDDING">Embedding</option>
                <option value="TFIDF">TF-IDF</option>
              </select>
            </div>
            <div className="mb-3">
              <label className="form-label"><strong>Search Years Back</strong></label>
              <input
                type="number"
                min="1"
                name="duplicate_search_years_back"
                className="form-control"
                value={settingsDraft.duplicate_search_years_back}
                onChange={handleSettingsChange}
              />
            </div>
            <div className="mb-3">
              <label className="form-label"><strong>Similarity Threshold</strong></label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="1"
                name="duplicate_similarity_threshold"
                className="form-control"
                value={settingsDraft.duplicate_similarity_threshold}
                onChange={handleSettingsChange}
              />
            </div>
            <div className="mb-3">
              <label className="form-label"><strong>Auto-Flag Threshold</strong></label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="1"
                name="duplicate_auto_flag_threshold"
                className="form-control"
                value={settingsDraft.duplicate_auto_flag_threshold}
                onChange={handleSettingsChange}
              />
            </div>
            <div className="row">
              <div className="col-md-6 mb-3">
                <label className="form-label"><strong>Semantic Weight</strong></label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  name="duplicate_semantic_weight"
                  className="form-control"
                  value={settingsDraft.duplicate_semantic_weight}
                  onChange={handleSettingsChange}
                  disabled={settingsDraft.duplicate_algorithm !== 'HYBRID'}
                />
              </div>
              <div className="col-md-6 mb-3">
                <label className="form-label"><strong>Lexical Weight</strong></label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  name="duplicate_lexical_weight"
                  className="form-control"
                  value={settingsDraft.duplicate_lexical_weight}
                  onChange={handleSettingsChange}
                  disabled={settingsDraft.duplicate_algorithm !== 'HYBRID'}
                />
              </div>
            </div>
            <div className="d-flex gap-2">
              <button className="btn btn-primary" onClick={handleSaveSettings} disabled={settingsSaving}>
                {settingsSaving ? 'Saving...' : 'Save Settings'}
              </button>
              <button className="btn btn-outline-secondary" onClick={() => setShowSettingsModal(false)} disabled={settingsSaving}>
                Close
              </button>
            </div>
            {settingsMessage && <p className={'mt-3 ' + (settingsMessage.includes('successfully') ? 'text-success' : 'text-danger')}>{settingsMessage}</p>}
          </div>
        </div>
      )}

      {/* Project Details Modal */}
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
            maxWidth: '600px',
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
              <div className="mb-3">
                <p><strong>Status:</strong> {selectedProject.status}</p>
                <p><strong>Project Type:</strong> {selectedProject.project_type_name || 'N/A'}</p>
                <p><strong>Year:</strong> {selectedProject.year}</p>
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

              <div className="mb-3">
                <p><strong>Flagged Duplicate:</strong> {selectedProject.is_flagged_duplicate ? 'Yes' : 'No'}</p>
              </div>

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

              <div className="mb-3">
                <label className="form-label"><strong>Change Status</strong></label>
                <select
                  className="form-select"
                  value={selectedProject.status}
                  onChange={(e) => handleProjectStatusChange(selectedProject.id, e.target.value)}
                  disabled={projectSaving}
                >
                  {STATUS_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              {projectMessage && <p className={'mt-3 ' + (projectMessage.includes('✅') ? 'text-success' : 'text-danger')}>{projectMessage}</p>}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default CoordinatorDashboard;