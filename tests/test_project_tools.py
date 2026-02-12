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


if __name__ == "__main__":
    unittest.main()
