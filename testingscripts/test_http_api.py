#!/usr/bin/env python3
import requests

def test_api_filtering():
    base_url = 'http://localhost:8000'

    # Test different users
    test_users = [
        ('revocajana', 'student'),
        ('JayJr7', 'student'),
        ('saidC', 'coordinator')
    ]

    for username, expected_role in test_users:
        print(f"\n=== Testing {username} ({expected_role}) ===")

        # Create a session to maintain cookies
        session = requests.Session()

        try:
            # Login
            login_data = {'username': username, 'password': 'password'}
            login_response = session.post(f'{base_url}/api/login/', json=login_data)

            print(f"Login status: {login_response.status_code}")
            if login_response.status_code != 200:
                print(f"Login failed: {login_response.text}")
                continue

            # Get user info from login response
            login_data = login_response.json()
            user_info = login_data.get('user', {})
            actual_role = user_info.get('role', 'unknown')
            print(f"Logged in as: {user_info.get('username')} (role: {actual_role})")

            # Fetch projects
            projects_response = session.get(f'{base_url}/api/projects/')

            print(f"Projects API status: {projects_response.status_code}")
            if projects_response.status_code == 200:
                data = projects_response.json()
                projects = data.get('results', data)  # Handle pagination

                print(f"Projects returned: {len(projects)}")
                for project in projects:
                    creator = project.get('user', 'unknown')
                    title = project.get('title', 'untitled')
                    print(f"  - '{title}' (creator: {creator})")
            else:
                print(f"Error fetching projects: {projects_response.text}")

        except Exception as e:
            print(f"Error testing {username}: {e}")

if __name__ == '__main__':
    test_api_filtering()