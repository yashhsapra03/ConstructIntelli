from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'

def test_analyze_rejects_empty_input():
    response = client.post('/api/analyze', data={'description': '', 'project_data': '{}'})
    assert response.status_code == 422

def test_analyze_demo_text():
    response = client.post('/api/analyze', data={'description': 'A crack is visible near the beam', 'project_data': '{"floor": 2}'})
    assert response.status_code == 200
    body = response.json()
    assert body['mode'] in ('demo', 'ai')
    assert isinstance(body['findings'], list)
    assert body['disclaimer']

def test_plan_validation_and_result():
    response = client.post('/api/plan', json={'project_name': 'Demo house', 'area_sqft': 1200, 'floors': 2, 'quality': 'standard', 'currency': 'INR'})
    assert response.status_code == 200
    body = response.json()
    assert body['estimated_cost'] > 0
    assert len(body['material_estimates']) >= 3

def test_valuation():
    response = client.post('/api/valuation', json={'location': 'Indore', 'area_sqft': 1000, 'rate_per_sqft': 3500, 'age_years': 5, 'condition': 'good'})
    assert response.status_code == 200
    assert response.json()['indicative_value'] > 0

def test_analyze_rejects_invalid_project_json():
    response = client.post('/api/analyze', data={'description': 'site note', 'project_data': '{bad json}'})
    assert response.status_code == 422

def test_analyze_rejects_non_image_upload():
    response = client.post('/api/analyze', data={'description': 'review this'}, files={'image': ('notes.txt', b'not an image', 'text/plain')})
    assert response.status_code == 415

def test_analyze_rejects_empty_image():
    response = client.post('/api/analyze', data={'description': 'review this'}, files={'image': ('empty.png', b'', 'image/png')})
    assert response.status_code == 422
