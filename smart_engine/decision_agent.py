"""
decision_agent.py – TypeSafe AI (Jev / System 1) decision client with deterministic offline fallbacks.
"""
import os

try:
    from typesafe_sdk import TypeSafeClient, Choice, Noul
    HAS_TYPESAFE = True
except ImportError:
    HAS_TYPESAFE = False

class JevDecisionAgent:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("TYPESAFE_API_KEY")

    def decide_action(self, state, criteria, instructions="Which option should be selected to proceed?"):
        """
        Submits a typed Choice decision question to Jev.
        Falls back to local heuristic if offline or unconfigured.
        """
        if HAS_TYPESAFE and self.api_key:
            try:
                with TypeSafeClient(api_key=self.api_key) as client:
                    response = client.system_one(
                        state=state,
                        questions={
                            "target_action": Choice(
                                instructions=instructions,
                                criteria=criteria
                            )
                        }
                    )
                    choice_ans = response.answers["target_action"]
                    return {
                        "choice": choice_ans.choice,
                        "confidence": getattr(choice_ans, "confidence", 1.0),
                        "is_fallback": False
                    }
            except Exception as e:
                print(f"[!] Jev decision call error ({e}), falling back to heuristic...")

        # Deterministic offline heuristic fallback
        return self._heuristic_fallback(criteria, instructions)

    def check_condition(self, state, instructions):
        """
        Submits a boolean Noul question to Jev.
        """
        if HAS_TYPESAFE and self.api_key:
            try:
                with TypeSafeClient(api_key=self.api_key) as client:
                    response = client.system_one(
                        state=state,
                        questions={
                            "condition": Noul(instructions=instructions)
                        }
                    )
                    ans = response.answers["condition"]
                    return getattr(ans, "noul", 0.5) > 0.6
            except Exception:
                pass

        # Fallback keyword match
        return any(k in str(state).lower() for k in ["doubt", "tolerance", "warning", "revalidate"])

    @staticmethod
    def _heuristic_fallback(criteria, instructions):
        keys = list(criteria.keys())
        if not keys:
            return {"choice": None, "confidence": 0.0, "is_fallback": True}

        # Priorities for common decisions:
        # 1. Secondary confirmation popup: pick Submit / OK / Yes
        for target in ["submit", "btn_submit", "button1", "yes", "ok", "confirm"]:
            for k in keys:
                desc = str(criteria[k]).lower()
                if target in k.lower() or target in desc:
                    return {"choice": k, "confidence": 0.95, "is_fallback": True}

        # 2. Revalidation screen: pick 'readings are correct'
        for k in keys:
            desc = str(criteria[k]).lower()
            if "correct" in desc or "report" in desc:
                return {"choice": k, "confidence": 0.95, "is_fallback": True}

        # 3. Default to first option
        return {"choice": keys[0], "confidence": 0.5, "is_fallback": True}
