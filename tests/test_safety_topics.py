import unittest
from safety_topics import safety_topics
class SafetyTests(unittest.TestCase):
 def test_memory_and_injection_are_multi_label_with_title_evidence_first(self):
  tags=safety_topics({'title':'Memory Poisoning in LLM Agents','summary':'Prompt injection and guardrails are evaluated.'})
  self.assertEqual(tags[0]['name'],'记忆与 RAG 投毒');self.assertEqual(tags[0]['field'],'title')
  self.assertIn('提示注入与间接注入',[t['name'] for t in tags])
 def test_generic_agent_or_object_detection_is_not_assumed_to_be_security(self):
  self.assertEqual(safety_topics({'title':'Agent planning for object detection','summary':'An efficient framework.'}),[])
 def test_alignment_and_tool_security(self):
  self.assertEqual(safety_topics({'title':'Agentic misalignment evaluation'})[0]['name'],'对齐、欺骗与可控性')
  self.assertEqual(safety_topics({'title':'MCP security and tool poisoning'})[0]['name'],'工具、MCP 与权限安全')
if __name__=='__main__':unittest.main()
