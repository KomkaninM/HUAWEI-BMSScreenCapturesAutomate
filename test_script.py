import os
import time
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

# Import local modules (Assuming your main server file is named server.py)
# If your file is named differently (e.g., server_3.py), change 'import server' to 'import server_3 as server'
import server 
import config
from capture import capture_screen_local
from scheduler import stop_automated_captures, is_scheduler_running
from utils import parse_schedule_args, parse_single_capture_args


class TestBMSBotUnits(unittest.TestCase):
    """Unit tests for utility functions and screen capture."""

    def test_01_parse_schedule_standard(self):
        """Tests standard interval parsing without starttime."""
        seconds, desc, note, start_time = parse_schedule_args("15m AHU Check")
        self.assertEqual(seconds, 900)
        self.assertEqual(desc, "15 minute(s)")
        self.assertEqual(note, "AHU Check")
        self.assertIsNone(start_time)

    def test_02_parse_schedule_with_starttime(self):
        """Tests parsing with mobile em-dash/en-dash and --starttime."""
        # Test double hyphen
        s, d, n, t = parse_schedule_args("30s Chiller --starttime 18:30:00")
        self.assertEqual(s, 30)
        self.assertEqual(n, "Chiller")
        self.assertIsNotNone(t)
        self.assertEqual(t.hour, 18)
        self.assertEqual(t.minute, 30)

        # Test mobile em-dash (—)
        s2, d2, n2, t2 = parse_schedule_args("1h Generator —starttime 09:00")
        self.assertEqual(s2, 3600)
        self.assertEqual(n2, "Generator")
        self.assertIsNotNone(t2)
        self.assertEqual(t2.hour, 9)

    def test_03_parse_single_capture_args(self):
        """Tests one-off capture command parsing."""
        note, start_time = parse_single_capture_args("TestOneShot --start-time 20:00:00")
        self.assertEqual(note, "TestOneShot")
        self.assertIsNotNone(start_time)
        self.assertEqual(start_time.hour, 20)

        note_imm, start_imm = parse_single_capture_args("Immediate Note")
        self.assertEqual(note_imm, "Immediate Note")
        self.assertIsNone(start_imm)

    def test_04_screen_capture_execution(self):
        """Verifies the MSS screen capture executes quickly and creates a file."""
        t0 = time.time()
        filename, timestamp = capture_screen_local()
        elapsed = time.time() - t0

        filepath = os.path.abspath(os.path.join("screenshots", filename))
        self.assertTrue(os.path.exists(filepath))
        self.assertGreater(os.path.getsize(filepath), 1000)
        print(f"\n  [Capture] Saved {filename} in {elapsed:.3f}s")


class TestBMSBotWebhooks(unittest.TestCase):
    """Integration tests simulating LINE webhook payloads via Flask Test Client."""

    def setUp(self):
        # Set up the Flask test client
        server.app.testing = True
        self.client = server.app.test_client()
        # Ensure scheduler is stopped before each test
        stop_automated_captures()

    def send_webhook(self, text_command: str):
        """Helper to send a mock LINE webhook event to the Flask app."""
        payload = {
            "events": [
                {
                    "type": "message",
                    "replyToken": "dummy_reply_token_123",
                    "source": {
                        "userId": "U_TEST_USER",
                        "groupId": "C_TEST_GROUP",
                    },
                    "message": {
                        "id": "msg_999",
                        "type": "text",
                        "text": text_command,
                    },
                }
            ]
        }
        return self.client.post("/callback", json=payload)

    @patch('line_api.requests.post')
    def test_05_help_command(self, mock_post):
        """Tests the help command returns 200 OK instantly."""
        mock_post.return_value.status_code = 200
        response = self.send_webhook("help")
        self.assertEqual(response.status_code, 200)

    @patch('line_api.requests.post')
    def test_06_check_id_command(self, mock_post):
        """Tests the check-id command."""
        mock_post.return_value.status_code = 200
        response = self.send_webhook("check-id")
        self.assertEqual(response.status_code, 200)

    @patch('line_api.requests.post')
    def test_07_autologout_toggles(self, mock_post):
        """Tests enabling and disabling auto-logout."""
        mock_post.return_value.status_code = 200
        
        res1 = self.send_webhook("enable-autologout")
        self.assertEqual(res1.status_code, 200)
        self.assertTrue(config.ENABLE_AUTO_LOGOUT)

        res2 = self.send_webhook("disable-autologout")
        self.assertEqual(res2.status_code, 200)
        self.assertFalse(config.ENABLE_AUTO_LOGOUT)

    @patch('line_api.requests.post')
    def test_08_start_and_stop_capture(self, mock_post):
        """Tests scheduling a capture task and stopping it."""
        mock_post.return_value.status_code = 200
        
        # Start capture
        res_start = self.send_webhook("start-capture 5m SuiteTest")
        self.assertEqual(res_start.status_code, 200)
        time.sleep(0.5) # Give background thread a moment to register
        self.assertTrue(is_scheduler_running())

        # Stop capture
        res_stop = self.send_webhook("stop-capture")
        self.assertEqual(res_stop.status_code, 200)
        self.assertFalse(is_scheduler_running())

    @patch('line_api.requests.post')
    def test_09_manual_capture(self, mock_post):
        """Tests the manual capture trigger."""
        mock_post.return_value.status_code = 200
        response = self.send_webhook("capture ImmediateTest")
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    print("=" * 65)
    print("🤖 RUNNING BMS AUTOMATION BOT TEST SUITE (FLASK TEST CLIENT)")
    print("=" * 65)
    unittest.main(verbosity=2)