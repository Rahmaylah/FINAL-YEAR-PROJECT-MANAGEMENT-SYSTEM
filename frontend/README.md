# FYPMS Frontend - React Application

This is the React frontend for the Final Year Project Management System (FYPMS).

## Features

- **Role-Based Dashboards**: Separate interfaces for Mentor, Student, and Admin
- **Login Page**: Simple authentication without registration
- **Protected Routes**: Access control based on user roles
- **Bootstrap Styling**: Responsive design with Bootstrap 5
- **Context API**: State management for authentication

## Project Structure

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── pages/
│   │   ├── Login.js              # Login page
│   │   ├── MentorDashboard.js    # Mentor dashboard
│   │   ├── StudentDashboard.js   # Student dashboard
│   │   └── AdminDashboard.js     # Admin dashboard
│   ├── context/
│   │   └── AuthContext.js        # Authentication context
│   ├── styles/
│   │   ├── App.css
│   │   ├── Dashboard.css
│   │   ├── Login.css
│   │   └── index.css
│   ├── App.js                    # Main app component
│   └── index.js                  # Entry point
├── package.json
└── README.md
```

## Setup Instructions

### Prerequisites
- Node.js (v14 or higher)
- npm or yarn

### Installation

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start development server:
```bash
npm start
```

The app will open at `http://localhost:3000`

## Demo Credentials

Use these accounts to test the application:

### Mentor
- **Username**: mentor_john
- **Password**: password

### Student
- **Username**: student_alice
- **Password**: password

### Admin
- **Username**: admin
- **Password**: password

## API Configuration

The frontend connects to Django backend at `http://localhost:8000`

Make sure the Django server is running:
```bash
python3 manage.py runserver
```

## Authentication Flow

1. User enters username/password on login page
2. Credentials sent to `/api-auth/login/` endpoint
3. User profile fetched from `/api/profiles/` endpoint
4. User role (mentor/student/admin) determined
5. User redirected to appropriate dashboard
6. Session maintained via authentication context

## Styling

- **Framework**: Bootstrap 5
- **Approach**: Separate CSS files per component
- **Colors**:
  - Mentor (Primary): #0d6efd (Blue)
  - Student (Success): #198754 (Green)
  - Admin (Danger): #dc3545 (Red)

## Building for Production

```bash
npm run build
```

This creates an optimized build in the `build/` folder.

## Future Enhancements

- [ ] Projects listing and submission
- [ ] Appointment calendar integration
- [ ] Duplicate projects review interface
- [ ] User profile management
- [ ] Search and filtering functionality
- [ ] Email notifications display
- [ ] Analytics and reporting dashboards

## Troubleshooting

### CORS Errors
Ensure Django backend has CORS enabled in settings.py

### Login Issues
- Verify Django server is running on port 8000
- Check network tab in browser DevTools
- Ensure correct credentials from sample data

### Styling Issues
- Clear browser cache
- Delete node_modules and reinstall: `npm install`
- Check that Bootstrap CSS is loaded

## Development Notes

- React Router v6 used for routing
- Axios used for API calls
- Context API for state management (can upgrade to Redux if needed)
- sessionStorage used for authentication persistence
