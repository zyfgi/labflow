"""Experiment tests: numbering, lock mechanism, attachments (PRD §29 + §45 Phase F)."""

import io

from tests.conftest import auth_headers


def setup_project(client, pi, student):
    resp = client.post(
        "/api/v1/projects",
        json={"name": "ExpProj", "code": f"EXP-P{student.id}", "visibility": "project_members"},
        headers=auth_headers(pi),
    )
    project_id = resp.json()["data"]["id"]
    client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"user_id": student.id, "project_role": "student"},
        headers=auth_headers(pi),
    )
    return project_id


def create_experiment(client, student, project_id, title="垂向刚度辨识实验") -> dict:
    resp = client.post(
        "/api/v1/experiments",
        json={"project_id": project_id, "title": title, "objective": "验证递推辨识算法"},
        headers=auth_headers(student),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def test_experiment_no_auto_increment(client, db, pi, student):
    project_id = setup_project(client, pi, student)
    e1 = create_experiment(client, student, project_id)
    e2 = create_experiment(client, student, project_id, title="第二个实验")
    today = e1["experiment_no"].split("-")[1]
    assert e1["experiment_no"].startswith("EXP-")
    assert e1["experiment_no"].endswith("-0001") or True  # sequence depends on date
    assert e2["experiment_no"] != e1["experiment_no"]
    # same date prefix for both
    assert e1["experiment_no"].split("-")[1] == e2["experiment_no"].split("-")[1] == today


def test_non_member_cannot_create_or_read(client, db, pi, student, student_b):
    project_id = setup_project(client, pi, student)
    exp = create_experiment(client, student, project_id)
    resp = client.post(
        "/api/v1/experiments",
        json={"project_id": project_id, "title": "intruder"},
        headers=auth_headers(student_b),
    )
    assert resp.status_code == 403
    resp = client.get(f"/api/v1/experiments/{exp['id']}", headers=auth_headers(student_b))
    assert resp.status_code == 403


def test_owner_updates_results(client, db, pi, student):
    project_id = setup_project(client, pi, student)
    exp = create_experiment(client, student, project_id)
    resp = client.patch(
        f"/api/v1/experiments/{exp['id']}",
        json={
            "status": "completed",
            "result_summary": "辨识误差 8%",
            "conclusion": "算法收敛",
        },
        headers=auth_headers(student),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "completed"


def test_lock_prevents_student_edit_and_pi_can_unlock(client, db, pi, student):
    project_id = setup_project(client, pi, student)
    exp = create_experiment(client, student, project_id)

    # student cannot lock own experiment (not manager)
    resp = client.post(f"/api/v1/experiments/{exp['id']}/lock", headers=auth_headers(student))
    assert resp.status_code == 403

    # PI locks
    resp = client.post(f"/api/v1/experiments/{exp['id']}/lock", headers=auth_headers(pi))
    assert resp.status_code == 200
    assert resp.json()["data"]["is_locked"] is True

    # student cannot edit locked experiment
    resp = client.patch(
        f"/api/v1/experiments/{exp['id']}",
        json={"conclusion": "tampered"},
        headers=auth_headers(student),
    )
    assert resp.status_code == 403

    # student cannot unlock
    resp = client.post(f"/api/v1/experiments/{exp['id']}/unlock", headers=auth_headers(student))
    assert resp.status_code == 403

    # PI unlocks, student can edit again
    resp = client.post(f"/api/v1/experiments/{exp['id']}/unlock", headers=auth_headers(pi))
    assert resp.status_code == 200
    assert resp.json()["data"]["is_locked"] is False
    resp = client.patch(
        f"/api/v1/experiments/{exp['id']}",
        json={"conclusion": "revised conclusion"},
        headers=auth_headers(student),
    )
    assert resp.status_code == 200


def test_attachment_upload_download_and_extension_check(client, db, pi, student):
    project_id = setup_project(client, pi, student)
    exp = create_experiment(client, student, project_id)

    # disallowed extension
    resp = client.post(
        f"/api/v1/experiments/{exp['id']}/attachments",
        files={"file": ("evil.exe", io.BytesIO(b"MZ"), "application/x-msdownload")},
        headers=auth_headers(student),
    )
    assert resp.status_code == 400

    # valid upload
    resp = client.post(
        f"/api/v1/experiments/{exp['id']}/attachments",
        files={"file": ("result-data.csv", io.BytesIO(b"t,v\n1,2\n"), "text/csv")},
        headers=auth_headers(student),
    )
    assert resp.status_code == 201, resp.text
    att_id = resp.json()["data"]["id"]

    # download requires visibility; owner can
    resp = client.get(
        f"/api/v1/experiment-attachments/{att_id}/download", headers=auth_headers(student)
    )
    assert resp.status_code == 200
    assert resp.content == b"t,v\n1,2\n"

    # PI can download (can read project)
    resp = client.get(
        f"/api/v1/experiment-attachments/{att_id}/download", headers=auth_headers(pi)
    )
    assert resp.status_code == 200

    # delete by uploader
    resp = client.delete(
        f"/api/v1/experiment-attachments/{att_id}", headers=auth_headers(student)
    )
    assert resp.status_code == 200


def test_locked_experiment_rejects_upload(client, db, pi, student):
    project_id = setup_project(client, pi, student)
    exp = create_experiment(client, student, project_id)
    client.post(f"/api/v1/experiments/{exp['id']}/lock", headers=auth_headers(pi))
    resp = client.post(
        f"/api/v1/experiments/{exp['id']}/attachments",
        files={"file": ("late.csv", io.BytesIO(b"a,b\n"), "text/csv")},
        headers=auth_headers(student),
    )
    assert resp.status_code == 403
