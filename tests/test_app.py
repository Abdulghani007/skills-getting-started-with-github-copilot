"""
Tests for the Mergington High School API

Tests cover:
- Getting activities
- Signing up for activities
- Unregistering from activities
- Error handling for invalid inputs
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add the src directory to the path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    # Store original state
    from app import activities
    original_state = {
        activity: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for activity, details in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for activity, details in activities.items():
        details["participants"] = original_state[activity]["participants"].copy()


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_success(self, client):
        """Test successfully retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert "Soccer Team" in data
        assert "Basketball Club" in data
        assert "Art Club" in data
        
    def test_get_activities_has_required_fields(self, client):
        """Test that activities have all required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)
            
    def test_get_activities_initial_participants(self, client):
        """Test that activities have initial participants"""
        response = client.get("/activities")
        data = response.json()
        
        # Soccer Team should have initial participants
        assert len(data["Soccer Team"]["participants"]) > 0


class TestSignup:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client, reset_activities):
        """Test successfully signing up for an activity"""
        response = client.post(
            "/activities/Soccer Team/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "test@mergington.edu" in data["message"]
        assert "Soccer Team" in data["message"]
        
    def test_signup_adds_participant(self, client, reset_activities):
        """Test that signup actually adds the participant to the list"""
        email = "newstudent@mergington.edu"
        
        # Check that email is not already in the list
        response = client.get("/activities")
        initial_participants = response.json()["Soccer Team"]["participants"].copy()
        assert email not in initial_participants
        
        # Sign up
        client.post(f"/activities/Soccer Team/signup?email={email}")
        
        # Check that email is now in the list
        response = client.get("/activities")
        assert email in response.json()["Soccer Team"]["participants"]
        assert len(response.json()["Soccer Team"]["participants"]) == len(initial_participants) + 1
        
    def test_signup_duplicate_email(self, client, reset_activities):
        """Test that signing up twice with same email fails"""
        email = "liam@mergington.edu"  # Already in Soccer Team
        
        response = client.post(
            f"/activities/Soccer Team/signup?email={email}"
        )
        assert response.status_code == 400
        
        data = response.json()
        assert "already signed up" in data["detail"].lower()
        
    def test_signup_invalid_activity(self, client):
        """Test signing up for non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "not found" in data["detail"].lower()
        
    def test_signup_multiple_activities(self, client, reset_activities):
        """Test that a student can sign up for multiple activities"""
        email = "multiactivity@mergington.edu"
        
        # Sign up for Soccer Team
        response1 = client.post(
            f"/activities/Soccer Team/signup?email={email}"
        )
        assert response1.status_code == 200
        
        # Sign up for Basketball Club
        response2 = client.post(
            f"/activities/Basketball Club/signup?email={email}"
        )
        assert response2.status_code == 200
        
        # Verify both signups worked
        response = client.get("/activities")
        data = response.json()
        assert email in data["Soccer Team"]["participants"]
        assert email in data["Basketball Club"]["participants"]


class TestUnregister:
    """Tests for POST /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client, reset_activities):
        """Test successfully unregistering from an activity"""
        email = "liam@mergington.edu"  # Already in Soccer Team
        
        # Verify email is in the list
        response = client.get("/activities")
        assert email in response.json()["Soccer Team"]["participants"]
        
        # Unregister
        response = client.post(
            f"/activities/Soccer Team/unregister?email={email}"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert "Unregistered" in data["message"]
        
    def test_unregister_removes_participant(self, client, reset_activities):
        """Test that unregister actually removes the participant"""
        email = "liam@mergington.edu"
        
        # Sign up first
        client.post(f"/activities/Soccer Team/signup?email=newsignup@mergington.edu")
        
        response = client.get("/activities")
        initial_count = len(response.json()["Soccer Team"]["participants"])
        
        # Unregister
        client.post(f"/activities/Soccer Team/unregister?email=newsignup@mergington.edu")
        
        # Check count decreased
        response = client.get("/activities")
        assert len(response.json()["Soccer Team"]["participants"]) == initial_count - 1
        assert "newsignup@mergington.edu" not in response.json()["Soccer Team"]["participants"]
        
    def test_unregister_not_registered(self, client):
        """Test unregistering someone who is not registered"""
        email = "notregistered@mergington.edu"
        
        response = client.post(
            f"/activities/Soccer Team/unregister?email={email}"
        )
        assert response.status_code == 400
        
        data = response.json()
        assert "not registered" in data["detail"].lower()
        
    def test_unregister_invalid_activity(self, client):
        """Test unregistering from non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Club/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "not found" in data["detail"].lower()
        
    def test_unregister_and_rejoin(self, client, reset_activities):
        """Test that a student can unregister and then sign up again"""
        email = "rejoin@mergington.edu"
        
        # Sign up
        response1 = client.post(
            f"/activities/Soccer Team/signup?email={email}"
        )
        assert response1.status_code == 200
        
        # Unregister
        response2 = client.post(
            f"/activities/Soccer Team/unregister?email={email}"
        )
        assert response2.status_code == 200
        
        # Sign up again
        response3 = client.post(
            f"/activities/Soccer Team/signup?email={email}"
        )
        assert response3.status_code == 200
        
        # Verify they are registered
        response = client.get("/activities")
        assert email in response.json()["Soccer Team"]["participants"]


class TestIntegration:
    """Integration tests combining multiple operations"""
    
    def test_full_signup_unregister_flow(self, client, reset_activities):
        """Test complete flow: signup -> verify -> unregister -> verify"""
        email = "integration@mergington.edu"
        activity = "Art Club"
        
        # Get initial count
        response = client.get("/activities")
        initial_count = len(response.json()[activity]["participants"])
        
        # Sign up
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200
        
        # Verify signup
        response = client.get("/activities")
        assert email in response.json()[activity]["participants"]
        assert len(response.json()[activity]["participants"]) == initial_count + 1
        
        # Unregister
        response = client.post(f"/activities/{activity}/unregister?email={email}")
        assert response.status_code == 200
        
        # Verify unregister
        response = client.get("/activities")
        assert email not in response.json()[activity]["participants"]
        assert len(response.json()[activity]["participants"]) == initial_count
