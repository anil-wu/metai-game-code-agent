
import unittest
from google.adk.models import LiteLlm
from phaser_agent.agents.planner_agent import create_planner_agent

class TestPlannerAgent(unittest.TestCase):
    def test_planner_agent_config(self):
        agent = create_planner_agent(
            model=LiteLlm(model="test"),
            description="test planner",
            instruction="Read artifacts/spec.txt then write artifacts/plan.txt",
        )
        self.assertEqual(agent.name, "planner_agent")
        self.assertIn("spec.txt", agent.instruction)
        self.assertIn("plan.txt", agent.instruction)
        
        # Check tools
        tool_names = [t.__name__ for t in agent.tools]
        self.assertIn("write_file", tool_names)
        self.assertIn("read_file", tool_names)

if __name__ == '__main__':
    unittest.main()
