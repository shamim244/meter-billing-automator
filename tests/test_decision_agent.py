import unittest
from unittest.mock import MagicMock, patch
from smart_engine.decision_agent import JevDecisionAgent

class TestDecisionAgent(unittest.TestCase):
    def setUp(self):
        self.agent = JevDecisionAgent(api_key="test-api-key")

    @patch("smart_engine.decision_agent.TypeSafeClient")
    def test_decide_action_with_mock_client(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client
        mock_res = MagicMock()
        mock_choice = MagicMock()
        mock_choice.choice = "btn_submit"
        mock_choice.confidence = 0.98
        mock_res.answers = {"target_action": mock_choice}
        mock_client.system_one.return_value = mock_res

        state = {"screen": "ScanMeterActivity", "goal": "Acknowledge alert"}
        criteria = {"btn_submit": "Submit button", "btn_cancel": "Cancel button"}
        decision = self.agent.decide_action(state, criteria, instructions="Pick button to proceed")

        self.assertEqual(decision["choice"], "btn_submit")
        self.assertEqual(decision["confidence"], 0.98)

    def test_fallback_when_unconfigured(self):
        # Without API key, falls back to deterministic heuristic without crashing
        agent_offline = JevDecisionAgent(api_key=None)
        state = {"screen": "ScanMeterActivity", "options": ["Cancel", "Submit"]}
        criteria = {"btn_cancel": "Cancel", "btn_submit": "Submit"}
        decision = agent_offline.decide_action(state, criteria, instructions="Submit reading")
        self.assertEqual(decision["choice"], "btn_submit")
        self.assertTrue(decision["is_fallback"])

if __name__ == "__main__":
    unittest.main()
