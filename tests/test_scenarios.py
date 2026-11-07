import base64
import tempfile
import unittest
from pathlib import Path

from thorbench.scenarios import NEEDLE, case_context, case_quick, case_reasoning, case_vision, case_agent


class ScenarioTests(unittest.TestCase):
    def test_reasoning_switches(self):
        self.assertEqual(case_reasoning("off")["chat_template_kwargs"]["enable_thinking"], False)
        self.assertEqual(case_reasoning("low")["reasoning_effort"], "low")
        self.assertEqual(case_quick()["reasoning_effort"], "low")

    def test_context(self):
        payload = case_context(256)
        message = payload["messages"][0]["content"]
        self.assertIn(NEEDLE, message)
        self.assertGreater(len(message), 800)

    def test_agent_shared_prefix_with_changing_tail(self):
        first = case_agent(1024, "testnonce", "first")
        followup = case_agent(1024, "testnonce", "followup")
        self.assertEqual(first["messages"][0], followup["messages"][0])
        self.assertNotEqual(first["messages"][1], followup["messages"][1])
        with self.assertRaises(ValueError):
            case_agent(1024, "testnonce", "invalid")

    def test_vision_image_is_encoded(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "test.png"
            image.write_bytes(b"\x89PNG\r\n\x1a\n")
            payload = case_vision(str(image))
            uri = payload["messages"][0]["content"][1]["image_url"]["url"]
            self.assertEqual(base64.b64decode(uri.split(",", 1)[1]), image.read_bytes())

    def test_vision_rejects_bad_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "test.txt"
            image.write_text("not an image")
            with self.assertRaises(ValueError):
                case_vision(str(image))

if __name__ == "__main__":
    unittest.main()
