import io
import pytest
from app import create_app, db
from app.models import Student, User, Department, Batch
from flask_jwt_extended import create_access_token, get_csrf_token


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_student_profile_and_uploads(app, client):
    with app.app_context():
        student = Student.query.first()
        if not student:
            pytest.skip("No student in database")

        token = create_access_token(
            identity=str(student.user_id),
            additional_claims={"role": "STUDENT"},
        )
        csrf = get_csrf_token(token)
        client.set_cookie("access_token_cookie", token)
        client.set_cookie("csrf_access_token", csrf)
        headers = {"X-CSRF-TOKEN": csrf}

        # 1. GET /api/student/profile
        res = client.get("/api/student/profile", headers=headers)
        assert res.status_code == 200
        data = res.get_json()["data"]
        assert data["student_id"] == student.student_id
        assert "father_name" in data
        assert "photo_url" in data
        assert "signature_url" in data

        # 2. Strict size check: Photo > 50 KB must fail
        oversized_photo = b"x" * (55 * 1024)
        res_large = client.post(
            "/api/student/upload-photo",
            data={"file": (io.BytesIO(oversized_photo), "test.jpg")},
            content_type="multipart/form-data",
            headers=headers,
        )
        assert res_large.status_code == 400
        assert "50 KB" in res_large.get_json()["message"]

        # 3. Valid photo < 50 KB must succeed
        valid_photo = b"GIF89a" + b"p" * 2048
        res_photo = client.post(
            "/api/student/upload-photo",
            data={"file": (io.BytesIO(valid_photo), "ppsize.jpg")},
            content_type="multipart/form-data",
            headers=headers,
        )
        assert res_photo.status_code == 200
        assert res_photo.get_json()["success"] is True
        assert "/uploads/photos/" in res_photo.get_json()["photo_url"]

        # 4. Strict size check: Signature > 50 KB must fail
        oversized_sig = b"s" * (60 * 1024)
        res_large_sig = client.post(
            "/api/student/upload-signature",
            data={"file": (io.BytesIO(oversized_sig), "sig.png")},
            content_type="multipart/form-data",
            headers=headers,
        )
        assert res_large_sig.status_code == 400
        assert "50 KB" in res_large_sig.get_json()["message"]

        # 5. Valid signature < 50 KB must succeed
        valid_sig = b"PNG..." + b"s" * 1024
        res_sig = client.post(
            "/api/student/upload-signature",
            data={"file": (io.BytesIO(valid_sig), "signature.png")},
            content_type="multipart/form-data",
            headers=headers,
        )
        assert res_sig.status_code == 200
        assert res_sig.get_json()["success"] is True
        assert "/uploads/signatures/" in res_sig.get_json()["signature_url"]

        # 6. PATCH /api/student/profile
        update_payload = {
            "father_name": "Rajesh Kumar",
            "mother_name": "Meena Devi",
            "phone": "9876543210",
            "blood_group": "O+",
            "gender": "Male",
            "address": "123 University Road",
            "city": "Patna",
            "state": "Bihar",
            "pin_code": "800001",
            "country": "India",
        }
        res_patch = client.patch(
            "/api/student/profile",
            json=update_payload,
            headers=headers,
        )
        assert res_patch.status_code == 200
        updated = res_patch.get_json()["data"]
        assert updated["father_name"] == "Rajesh Kumar"
        assert updated["mother_name"] == "Meena Devi"
        assert updated["blood_group"] == "O+"
        assert updated["city"] == "Patna"
