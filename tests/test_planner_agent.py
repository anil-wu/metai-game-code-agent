
import unittest
from phaser_agent.agents.planner_agent import planner_agent
from phaser_agent.tools.filesystem import write_file, read_file

class TestPlannerAgent(unittest.TestCase):
    def test_planner_agent_config(self):
        self.assertEqual(planner_agent.name, "planner_agent")
        self.assertIn("spec.txt", planner_agent.instruction)
        self.assertIn("plan.txt", planner_agent.instruction)
        
        # Check tools
        tool_names = [t.__name__ for t in planner_agent.tools]
        self.assertIn("write_file", tool_names)
        self.assertIn("read_file", tool_names)

if __name__ == '__main__':
    unittest.main()
