def test_login_redirect(client):
    # Testing that protected route redirects to login
    response = client.get('/dashboard')
    assert response.status_code == 302
    assert b'/login' in response.data

def test_signup_page(client):
    response = client.get('/signup')
    assert response.status_code == 200
    assert b'Sign Up' in response.data

def test_login_page(client):
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Login' in response.data
