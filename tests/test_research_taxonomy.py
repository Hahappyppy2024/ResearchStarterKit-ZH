import unittest
import research_taxonomy as shared
import conference_catalog as catalog
import topics_service

class SharedTaxonomyTests(unittest.TestCase):
    def test_explainability_parent_and_shared_children(self):
        root=next(r for r in shared.DATA['roots'] if r['id']=='interpretability')
        self.assertEqual(root['name'],'模型可解释性')
        p={'title':'Mechanistic Interpretability with Sparse Autoencoders','summary':''}
        hits=shared.research_topics(p)
        self.assertEqual(hits[0]['parentName'],'模型可解释性')
        self.assertEqual(set(catalog.classify_paper(p)),{tuple(h['id'].split(':')) for h in hits})
    def test_world_models_are_independent_of_reinforcement_learning(self):
        root=next(r for r in shared.DATA['roots'] if r['id']=='world-models')
        self.assertEqual(root['name'],'世界模型')
        self.assertFalse(any(s['id']=='world' for r in shared.DATA['roots'] if r['id']=='rl' for s in r['subtopics']))
        hits=shared.research_topics({'title':'World Models for Robot Planning'})
        self.assertTrue(any(h['parentId']=='world-models' for h in hits))
        self.assertEqual(shared.canonical_topic_id('rl:world'),'world-models')

    def test_existing_categories_retained(self):
        roots={r['id']:r for r in shared.DATA['roots']}
        self.assertTrue({'agents','vision','safety','language','software'}<=roots.keys())
        names={s['name'] for r in roots.values() for s in r['subtopics']}
        self.assertTrue({'多智能体协作','军事场景目标检测与识别','视频生成','提示注入与间接注入'}<=names)
    def test_research_query_is_available(self):
        self.assertIn('模型可解释性',dict(topics_service.BUILTINS))
    def test_guard_prevents_detection_details_on_unrelated_paper(self):
        hits=shared.research_topics({'title':'Lightweight Language Models','summary':''})
        self.assertNotIn('实时轻量化与边缘部署',{h['name'] for h in hits})

if __name__=='__main__':unittest.main()
