import unittest
from agent_topics import agent_topics,agent_feed_paper,is_biology_paper
class AgentTests(unittest.TestCase):
 def test_title_specific_category_precedes_abstract_generic_category(self):
  tags=agent_topics({'title':'Coding Agents for Software Engineering','summary':'Multi-agent planning benchmark with memory','topics':['Agent']})
  self.assertEqual(tags[0]['name'],'代码与软件智能体');self.assertEqual(tags[0]['field'],'title')
 def test_non_agent_detection_not_reclassified(self):
  self.assertEqual(agent_topics({'title':'Object detection benchmark','topics':['Object Detection']}),[])
 def test_robot_and_general_agent(self):
  self.assertEqual(agent_topics({'title':'Embodied robot agents for navigation'})[0]['name'],'具身机器人与导航')
  self.assertEqual(agent_topics({'title':'An agent approach','topics':['Agent']})[0]['name'],'智能体综合')
 def test_biology_excluded_without_changing_original(self):
  p={'title':'What Transfers Across Protein Pockets? Experience Reuse in Molecular Optimization for Structure-Based Drug Design','topics':['Agent'],'summary':'Agent experience reuse'}
  self.assertTrue(is_biology_paper(p));self.assertIsNone(agent_feed_paper(p));self.assertEqual(agent_topics(p),[]);self.assertEqual(p['topics'],['Agent'])
 def test_ecology_agent_simulation_is_excluded(self):
  self.assertIsNone(agent_feed_paper({'title':'Stochastic predator-prey compartment model','topics':['Agent']}))
 def test_biology_keeps_other_research_memberships(self):
  p={'title':'Medical agents for object detection','topics':['Agent','Object Detection']}
  self.assertEqual(agent_feed_paper(p)['topics'],['Object Detection'])
 def test_incidental_biology_mention_not_excluded(self):
  p={'title':'Tool agents for code repair','summary':'Unlike drug discovery, code repair requires tests.','topics':['Agent']}
  self.assertIs(agent_feed_paper(p),p)
if __name__=='__main__':unittest.main()
