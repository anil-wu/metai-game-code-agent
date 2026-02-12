import unittest

import phaser_agent.tools.project as project_tools


class TestEnsureProjectSoftware(unittest.TestCase):
    def test_returns_existing_software_by_name(self):
        calls = []

        def fake_api_request(method, path, token=None, query=None, body=None):
            calls.append((method, path, query, body))
            if method == "GET" and path == "/api/v1/projects/1/softwares":
                return {
                    "status": "success",
                    "status_code": 200,
                    "data": {
                        "list": [
                            {"id": 10, "projectId": 1, "name": "demo", "description": "", "templateId": 1, "technologyStack": "x", "status": "active", "createdBy": 1, "createdAt": "t", "updatedAt": "t"}
                        ]
                    },
                }
            raise AssertionError(f"Unexpected call: {method} {path}")

        original = project_tools._api_request
        project_tools._api_request = fake_api_request
        try:
            result = project_tools.ensure_project_software(project_id=1, name="demo")
        finally:
            project_tools._api_request = original

        self.assertEqual(result["status"], "success")
        self.assertFalse(result["created"])
        self.assertEqual(result["software"]["id"], 10)
        self.assertEqual(len(calls), 1)

    def test_creates_software_when_missing(self):
        calls = []

        def fake_api_request(method, path, token=None, query=None, body=None):
            calls.append((method, path, query, body))
            if method == "GET" and path == "/api/v1/projects/1/softwares":
                return {"status": "success", "status_code": 200, "data": {"list": []}}
            if method == "POST" and path == "/api/v1/projects/1/softwares":
                return {"status": "success", "status_code": 200, "data": {"softwareId": 11, "projectId": 1, "name": body.get("name")}}
            raise AssertionError(f"Unexpected call: {method} {path}")

        original = project_tools._api_request
        project_tools._api_request = fake_api_request
        try:
            result = project_tools.ensure_project_software(
                project_id=1,
                name="demo",
                description=None,
                template_id=2,
                technology_stack=None,
            )
        finally:
            project_tools._api_request = original

        self.assertEqual(result["status"], "success")
        self.assertTrue(result["created"])
        self.assertEqual(result["software"]["softwareId"], 11)

        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0], "GET")
        self.assertEqual(calls[1][0], "POST")
        self.assertEqual(calls[1][3]["technologyStack"], "game engine is phaser")
        self.assertEqual(calls[1][3]["templateId"], 2)

class TestEnsureSoftwareManifest(unittest.TestCase):
    def test_returns_existing_manifest_when_has_record(self):
        calls = []

        def fake_api_request(method, path, token=None, query=None, body=None):
            calls.append((method, path, query, body))
            if method == "GET" and path == "/api/v1/projects/1/software_manifests":
                self.assertEqual(query, {"software_ids": "10"})
                return {
                    "status": "success",
                    "status_code": 200,
                    "data": {
                        "list": [
                            {
                                "softwareId": 10,
                                "hasRecord": True,
                                "manifestId": 1,
                                "manifestFileId": 2,
                                "manifestFileVersionId": 3,
                                "versionDescription": "v1",
                                "createdBy": 1,
                                "createdAt": "t",
                            }
                        ]
                    },
                }
            raise AssertionError(f"Unexpected call: {method} {path}")

        original = project_tools._api_request
        project_tools._api_request = fake_api_request
        try:
            result = project_tools.ensure_software_manifest(
                project_id=1,
                software_id=10,
                manifest_file_id=2,
                manifest_file_version_id=3,
            )
        finally:
            project_tools._api_request = original

        self.assertEqual(result["status"], "success")
        self.assertFalse(result["created"])
        self.assertEqual(result["manifest"]["manifestId"], 1)
        self.assertEqual(len(calls), 1)

    def test_creates_manifest_when_missing_record(self):
        calls = []

        def fake_api_request(method, path, token=None, query=None, body=None):
            calls.append((method, path, query, body))
            if method == "GET" and path == "/api/v1/projects/1/software_manifests":
                return {
                    "status": "success",
                    "status_code": 200,
                    "data": {
                        "list": [
                            {
                                "softwareId": 10,
                                "hasRecord": False,
                                "manifestId": 0,
                                "manifestFileId": 0,
                                "manifestFileVersionId": 0,
                                "versionDescription": "",
                                "createdBy": 0,
                                "createdAt": "",
                            }
                        ]
                    },
                }
            if method == "POST" and path == "/api/v1/software-manifests":
                self.assertEqual(
                    body,
                    {
                        "projectId": 1,
                        "softwareId": 10,
                        "manifestFileId": 200,
                        "manifestFileVersionId": 300,
                        "versionDescription": "init",
                    },
                )
                return {
                    "status": "success",
                    "status_code": 200,
                    "data": {
                        "manifestId": 5,
                        "projectId": 1,
                        "softwareId": 10,
                        "manifestFileId": 200,
                        "manifestFileVersionId": 300,
                        "versionDescription": "init",
                    },
                }
            raise AssertionError(f"Unexpected call: {method} {path}")

        original = project_tools._api_request
        project_tools._api_request = fake_api_request
        try:
            result = project_tools.ensure_software_manifest(
                project_id=1,
                software_id=10,
                manifest_file_id=200,
                manifest_file_version_id=300,
                version_description="init",
            )
        finally:
            project_tools._api_request = original

        self.assertEqual(result["status"], "success")
        self.assertTrue(result["created"])
        self.assertEqual(result["manifest"]["manifestId"], 5)
        self.assertEqual(len(calls), 2)

    def test_creates_new_manifest_when_version_changed(self):
        calls = []

        def fake_api_request(method, path, token=None, query=None, body=None):
            calls.append((method, path, query, body))
            if method == "GET" and path == "/api/v1/projects/1/software_manifests":
                return {
                    "status": "success",
                    "status_code": 200,
                    "data": {
                        "list": [
                            {
                                "softwareId": 10,
                                "hasRecord": True,
                                "manifestId": 1,
                                "manifestFileId": 2,
                                "manifestFileVersionId": 3,
                                "versionDescription": "old",
                                "createdBy": 1,
                                "createdAt": "t",
                            }
                        ]
                    },
                }
            if method == "POST" and path == "/api/v1/software-manifests":
                self.assertEqual(
                    body,
                    {
                        "projectId": 1,
                        "softwareId": 10,
                        "manifestFileId": 2,
                        "manifestFileVersionId": 99,
                        "versionDescription": "new",
                    },
                )
                return {"status": "success", "status_code": 200, "data": {"manifestId": 2}}
            raise AssertionError(f"Unexpected call: {method} {path}")

        original = project_tools._api_request
        project_tools._api_request = fake_api_request
        try:
            result = project_tools.ensure_software_manifest(
                project_id=1,
                software_id=10,
                manifest_file_id=2,
                manifest_file_version_id=99,
                version_description="new",
            )
        finally:
            project_tools._api_request = original

        self.assertEqual(result["status"], "success")
        self.assertTrue(result["created"])
        self.assertEqual(result["manifest"]["manifestId"], 2)
        self.assertEqual(len(calls), 2)

class TestUploadSoftwareManifestJson(unittest.TestCase):
    def test_uploads_content_via_preupload_and_put(self):
        calls = []

        def fake_api_request(method, path, token=None, query=None, body=None):
            calls.append((method, path, query, body))
            if method == "POST" and path == "/api/v1/files/preupload":
                self.assertEqual(body["projectId"], 1)
                self.assertEqual(body["name"], "software_manifest.json")
                self.assertEqual(body["fileCategory"], "text")
                self.assertEqual(body["fileFormat"], "json")
                self.assertEqual(body["contentType"], "application/json")
                self.assertEqual(body["sizeBytes"], len(b'{"ok":true}'))
                self.assertTrue(isinstance(body["hash"], str) and len(body["hash"]) > 0)
                return {
                    "status": "success",
                    "status_code": 200,
                    "data": {
                        "uploadUrl": "https://example.com/upload",
                        "fileId": 10,
                        "versionId": 20,
                        "versionNumber": 2,
                        "contentType": "application/json",
                    },
                }
            raise AssertionError(f"Unexpected call: {method} {path}")

        def fake_put(upload_url, data, content_type):
            self.assertEqual(upload_url, "https://example.com/upload")
            self.assertEqual(data, b'{"ok":true}')
            self.assertEqual(content_type, "application/json")
            return {"status": "success", "status_code": 200}

        original_api = project_tools._api_request
        original_put = project_tools._upload_bytes_to_signed_url
        project_tools._api_request = fake_api_request
        project_tools._upload_bytes_to_signed_url = fake_put
        try:
            result = project_tools.upload_software_manifest_json(
                project_id=1,
                manifest_json='{"ok":true}',
            )
        finally:
            project_tools._api_request = original_api
            project_tools._upload_bytes_to_signed_url = original_put

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["file_id"], 10)
        self.assertEqual(result["file_version_id"], 20)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
