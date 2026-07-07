from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from accounts.models import User
from projects.models import Project, ProjectUser


class PresentationResultApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.mentor = User.objects.create_user(
            username='mentor1',
            password='mentor-pass',
            email='mentor@example.com',
            role='mentor'
        )

        self.student = User.objects.create_user(
            username='student1',
            password='student-pass',
            email='student@example.com',
            role='student',
            registration_number='S001',
            mentor=self.mentor
        )

        self.project = Project.objects.create(
            user=self.student,
            title='Test Project',
            year=2026
        )
        ProjectUser.objects.get_or_create(project=self.project, user=self.student, role='lead')

        self.mentor_token = Token.objects.create(user=self.mentor)
        self.student_token = Token.objects.create(user=self.student)

    def test_mentor_can_add_review_and_student_can_view_it(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.mentor_token.key}')

        presentation_response = self.client.post('/api/presentations/', {
            'project': self.project.id,
            'name': 'Final Presentation',
            'presentation_date': '2026-06-15'
        }, format='json')
        self.assertEqual(presentation_response.status_code, 201)
        presentation_id = presentation_response.data['id']

        review_response = self.client.post('/api/presentation-results/', {
            'presentation': presentation_id,
            'student': self.student.id,
            'project': self.project.id,
            'comment': 'Strong research and clear results.',
            'marks': 92.5
        }, format='json')
        self.assertEqual(review_response.status_code, 201)
        self.assertEqual(review_response.data['marks'], 92.5)
        self.assertEqual(review_response.data['comment'], 'Strong research and clear results.')
        self.assertEqual(review_response.data['reviewer'], self.mentor.id)

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.student_token.key}')
        project_response = self.client.get(f'/api/projects/{self.project.id}/')
        self.assertEqual(project_response.status_code, 200)
        results = project_response.data.get('presentation_results', [])
        self.assertEqual(len(results), 1)
        result_data = results[0]
        self.assertEqual(result_data['presentation'], presentation_id)
        self.assertEqual(result_data['student'], self.student.id)
        self.assertEqual(result_data['comment'], 'Strong research and clear results.')
        self.assertEqual(result_data['marks'], 92.5)
        self.assertEqual(result_data['reviewer'], self.mentor.id)
