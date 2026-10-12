import pytest
import httpx

@pytest.mark.asyncio
async def test_complete_employee_task_workflow(async_client: httpx.AsyncClient, setup_test_users):
    # 1. Login as admin_ops
    login_res = await async_client.post('/api/v1/auth/login', json={'email': 'admin_ops@testcorp.com', 'password': 'ValidPassword123!'})
    assert login_res.status_code == 200
    csrf_token = async_client.cookies.get('RG_csrf') or login_res.cookies.get('RG_csrf', '')
    async_client.headers.update({'X-CSRF-Token': csrf_token})

    # 2. Get reporting officers
    officers_res = await async_client.get('/api/v1/tasks/reporting-officers')
    assert officers_res.status_code == 200
    officers = officers_res.json()
    assert len(officers) > 0
    officer = officers[0]

    # 3. Create task
    task_res = await async_client.post('/api/v1/tasks', json={
        'title': 'Automated Test Task Work Order',
        'description': 'Executing automated integration test verification for task management.',
        'priority': 'HIGH',
        'reporting_officer_id': officer['id'],
    })
    assert task_res.status_code == 201
    task = task_res.json()
    task_id = task['id']
    assert task['status'] == 'PENDING'

    # 4. In-Task Chat
    msg_res = await async_client.post(f'/api/v1/tasks/{task_id}/messages', json={
        'message': 'Work is progressing on schedule.'
    })
    assert msg_res.status_code == 200
    assert msg_res.json()['sender_role'] in ['EMPLOYEE', 'SUPER_ADMIN', 'REPORTING_OFFICER']

    # 5. Submit for Review
    sub_res = await async_client.post(f'/api/v1/tasks/{task_id}/submit', json={
        'completion_note': 'Work completed with zero deviations.',
        'completion_evidence': 'Ref #QC-AUTO-100'
    })
    assert sub_res.status_code == 200
    assert sub_res.json()['status'] == 'SUBMITTED_FOR_REVIEW'

    # 6. Admin review and approval
    admin_login = await async_client.post('/api/v1/auth/login', json={'email': 'admin@rgtech.com', 'password': 'admin123'})
    assert admin_login.status_code == 200
    admin_csrf = async_client.cookies.get('RG_csrf') or admin_login.cookies.get('RG_csrf', '')
    async_client.headers.update({'X-CSRF-Token': admin_csrf})

    review_res = await async_client.post(f'/api/v1/tasks/{task_id}/review', json={
        'decision': 'APPROVED',
        'feedback_note': 'Verified and approved by administrator.'
    })
    assert review_res.status_code == 200
    assert review_res.json()['status'] == 'COMPLETED'
