import unittest,tempfile,pathlib,json,unittest.mock as mock
import study_service as s,local_app,learning_service
class StudyTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();root=pathlib.Path(self.temp.name)
  self.patches=[mock.patch.object(s,'DB',root/'study.sqlite'),mock.patch.object(local_app,'DATA',root),mock.patch.object(learning_service,'DB',root/'learning.sqlite')]
  for p in self.patches:p.start()
  self.p1=s.save_paper(dict(title='Baseline paper',authors='A',source='https://example.org/a',summary='Initial abstract'))
  self.p2=s.save_paper(dict(title='New solution',authors='B'))
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  __import__("gc").collect();self.temp.cleanup()
 def course(self,name='Test course'):return s.save_record('course',dict(name=name,goal='Explain methods'))
 def test_course_types_keep_existing_directions_and_partial_updates(self):
  for course_type in s.COURSE_TYPES:
   course=s.save_record('course',dict(name=course_type,courseType=course_type,category='Agent',subcategory='CV 应用'))
   updated=s.save_record('course',dict(id=course['id'],revision=course['revision'],goal='Updated'))
   self.assertEqual((updated['courseType'],updated['category'],updated['subcategory']),(course_type,'Agent','CV 应用'))
  with self.assertRaises(ValueError):s.save_record('course',dict(name='Invalid',courseType='other'))
 def test_legacy_courses_are_research_without_rewriting_saved_content(self):
  legacy=dict(id='legacy-course',name='Existing',category='LLM',subcategory='对齐',revision=7,units=['论文阅读'])
  body=json.dumps(legacy,ensure_ascii=False)
  with s.connection() as c:c.execute('INSERT INTO records VALUES(?,?,?,0)',('course',legacy['id'],body))
  course=s.state()['courses'][0]
  self.assertEqual(course,dict(legacy,courseType='research'))
  with s.connection() as c:self.assertEqual(c.execute('SELECT body FROM records WHERE id=?',(legacy['id'],)).fetchone()[0],body)
  s.archive(dict(kind='course',id=legacy['id']))
  self.assertEqual(s.state()['archivedCourses'][0]['courseType'],'research')

 def test_custom_course_categories_persist_without_courses_and_are_type_scoped(self):
  a=s.save_course_category(dict(courseType='foundation',name='  自定义方向  '))
  self.assertEqual(a['name'],'自定义方向')
  self.assertEqual(a,s.save_course_category(dict(courseType='foundation',name='自定义方向')))
  b=s.save_course_category(dict(courseType='self',name='自定义方向'))
  self.assertNotEqual(a['id'],b['id'])
  child=s.save_course_category(dict(courseType='foundation',name='子方向',parent='自定义方向'))
  data=s.state()
  self.assertEqual(len(data['courseCategories']),3)
  self.assertFalse(data['courses'])
  self.assertEqual(child['parent'],'自定义方向')
 def test_custom_course_subcategories_use_existing_course_parents_and_validate(self):
  course=s.save_record('course',dict(name='Existing course',courseType='research',category='原有方向',subcategory='保留'))
  s.save_course_category(dict(courseType='research',name='新子类',parent='原有方向'))
  self.assertEqual(s.state()['courses'][0],course)
  for payload in [dict(courseType='research',name='子类',parent='不存在'),dict(courseType='self',name='子类',parent='原有方向'),dict(courseType='invalid',name='分类'),dict(courseType='self',name=' '),dict(courseType='self',name='x'*101)]:
   with self.assertRaises(ValueError):s.save_course_category(payload)

 def test_course_lesson_plans_persist_and_validate_unit(self):
  a=s.save_record('course',dict(name='Teaching preparation',units=['Lesson 1'],lessonPlans={'Lesson 1':'Goal\nDemo\nDeliverable'}))
  self.assertEqual(s.state()['courses'][0]['lessonPlans']['Lesson 1'],'Goal\nDemo\nDeliverable')
  with self.assertRaises(ValueError):s.save_record('course',dict(a,lessonPlans={'Missing lesson':'Invalid'}))
  with self.assertRaises(ValueError):s.save_record('course',dict(a,lessonPlans={'Lesson 1':42}))
  updated=s.save_record('course',dict(id=a['id'],revision=a['revision'],goal='Revised'))
  self.assertEqual(updated['lessonPlans'],a['lessonPlans'])
 def test_course_innovations_persist_and_validate(self):
  a=s.save_record('course',dict(name='Research course',innovationQ1='Mechanism and transfer',innovationQ2='Scoped reproducible study',materialFolder='local-data/course-materials/example'))
  updated=s.save_record('course',dict(id=a['id'],revision=a['revision'],goal='Updated goal'))
  self.assertEqual(updated['innovationQ1'],a['innovationQ1'])
  self.assertEqual(updated['innovationQ2'],a['innovationQ2'])
  self.assertEqual(updated['materialFolder'],a['materialFolder'])
  with self.assertRaises(ValueError):s.save_record('course',dict(updated,innovationQ1=['Invalid type']))
 def test_course_material_access_is_scoped(self):
  a=self.course();b=self.course('Other course');root=pathlib.Path(self.temp.name)
  materials=root/'local-data'/'course-materials';materials.mkdir(parents=True)
  (materials/'poster.jpg').write_bytes(b'poster')
  manifest=materials/'source-manifest.json'
  manifest.write_text(json.dumps([dict(courseId=a['id'],sourceNumber=1,storedPath='poster.jpg')]),encoding='utf-8')
  with mock.patch.object(s,'ROOT',root):
   self.assertEqual(s.course_poster(a['id'],1),b'poster')
   self.assertEqual(s.course_materials(b['id'])['items'],[])
   with self.assertRaises(ValueError):s.course_poster(b['id'],1)
   manifest.write_text(json.dumps([dict(courseId=a['id'],sourceNumber=1,storedPath='../outside.jpg')]),encoding='utf-8')
   with self.assertRaises(ValueError):s.course_poster(a['id'],1)
 def test_innovation_tasks_are_independent_and_survive_course_edits(self):
  projects=[dict(id='idea-a',tier='q1',title='Hypothesis A',tasks={}),dict(id='idea-b',tier='q2',title='Hypothesis B',tasks={})]
  course=s.save_record('course',dict(name='Task research',innovationProjects=projects))
  edited=course['innovationProjects'];edited[0]['tasks']['problem']={'status':'done','notes':'Inputs, outputs and evidence'}
  updated=s.save_record('course',dict(id=course['id'],revision=course['revision'],innovationProjects=edited))
  self.assertEqual(updated['innovationProjects'][0]['tasks']['problem']['status'],'done')
  self.assertEqual(updated['innovationProjects'][1]['tasks']['problem']['status'],'todo')
  renamed=s.save_record('course',dict(id=course['id'],revision=updated['revision'],name='Renamed course'))
  self.assertEqual(renamed['innovationProjects'],updated['innovationProjects'])
  with self.assertRaises(ValueError):s.save_record('course',dict(id=course['id'],revision=course['revision'],innovationProjects=projects))
 def test_foundation_and_paper_guides_preserve_personal_work(self):
  a=s.save_record('course',dict(name='Learning guide',innovationProjects=[dict(id='study-a',tier='q1',title='Research',tasks={'foundations':{'status':'doing','notes':'My notes','guide':'Concepts and worked examples'},'related':{'status':'todo','notes':'Paper comparisons','guide':'Primary paper links'}})]))
  idea=a['innovationProjects'][0];self.assertEqual(len(idea['tasks']),9)
  idea['tasks']['foundations']['notes']='Updated personal notes'
  b=s.save_record('course',dict(id=a['id'],revision=a['revision'],innovationProjects=[idea]))
  self.assertEqual(b['innovationProjects'][0]['tasks']['foundations']['guide'],'Concepts and worked examples')
  self.assertEqual(b['innovationProjects'][0]['tasks']['related']['notes'],'Paper comparisons')
  self.assertEqual(b['innovationProjects'][0]['tasks']['foundations']['status'],'doing')
  idea['tasks']['foundations']['guide']=[]
  with self.assertRaises(ValueError):s.save_record('course',dict(id=b['id'],revision=b['revision'],innovationProjects=[idea]))
 def test_innovation_tasks_reject_invalid_payloads(self):
  for projects in [[dict(id='a',tier='q3',title='Bad')],[dict(id='a',tier='q1',title='Bad',tasks={'unknown':{}})],[dict(id='a',tier='q1',title='Bad',tasks={'problem':{'status':'invented'}})],[dict(id='a',tier='q1',title='First'),dict(id='a',tier='q2',title='Second')]]:
   with self.assertRaises(ValueError):s.save_record('course',dict(name='Invalid research',innovationProjects=projects))
 def test_courses_resources_duplicate_and_shared(self):
  a=self.course();b=self.course('Other');data=dict(courseId=a['id'],unit='论文阅读',resourceKind='paper',resourceId=self.p1['id'])
  first=s.add_link(data);again=s.add_link(data);self.assertEqual(first['id'],again['id']);self.assertTrue(again['alreadyExists'])
  s.add_link(dict(data,courseId=b['id']));self.assertEqual(len(s.state()['links']),2)
  with self.assertRaises(ValueError):s.save_record('course',dict(a,units=['基础知识']))
 def test_archive_restore_and_revision(self):
  a=self.course();s.archive(dict(kind='course',id=a['id']));self.assertFalse(s.state()['courses']);self.assertEqual(len(s.state()['archivedCourses']),1)
  with self.assertRaises(ValueError):s.add_link(dict(courseId=a['id'],unit='论文阅读',resourceKind='paper',resourceId=self.p1['id']))
  s.archive(dict(kind='course',id=a['id'],restore=True));s.save_record('course',dict(a,goal='Updated'))
  with self.assertRaises(ValueError):s.save_record('course',a)
 def test_comparison_distinct_and_notes(self):
  with self.assertRaises(ValueError):s.save_record('comparison',dict(name='Bad',paperIds=[self.p1['id']]*2))
  c=s.save_record('comparison',dict(name='Two methods',paperIds=[self.p1['id'],self.p2['id']],rows={self.p1['id']:{'method':'Baseline'}}))
  self.assertEqual(c['rows'][self.p1['id']]['method'],'Baseline');s.archive(dict(kind='comparison',id=c['id']));self.assertEqual(len(s.state()['archivedComparisons']),1)
 def test_manual_queue_date_dedup_remove_restore(self):
  data=dict(date='2026-10-21',paperId=self.p1['id'],reason='Chosen intentionally');s.add_queue(data);s.add_queue(data);self.assertEqual(len(s.state(data['date'])['queue']),1);self.assertEqual(s.state('2026-10-22')['queue'][0]['carriedFrom'],'2026-10-21')
  s.remove_queue(data);self.assertFalse(s.state(data['date'])['queue']);s.remove_queue(dict(data,restore=True));self.assertEqual(s.state(data['date'])['queue'][0]['reason'],data['reason'])
  p=s.save_paper(dict(self.p1,summary='Updated abstract'));self.assertEqual(s.resolve('paper',p['id'])['summary'],'Updated abstract')
  with self.assertRaises(ValueError):s.save_paper(dict(title='Unsafe',pdf='javascript:alert(1)'))
 def test_tasks_and_module_link(self):
  definitions=json.loads((s.ROOT/'web'/'paper-task-definitions.json').read_text(encoding='utf-8'));self.assertEqual(len(definitions),21)
  task=s.task_detail(self.p1['id'],'minimal-run');self.assertIn('日志',task['detail']);self.assertNotIn('paper',task)
  a=self.course();m=learning_service.list_modules()[0];link=s.add_link(dict(courseId=a['id'],unit='基础知识',resourceKind='module',resourceId=m['id']));self.assertEqual(link['resourceKind'],'module')
  with self.assertRaises(ValueError):s.task_detail(self.p1['id'],'missing')
if __name__=='__main__':unittest.main()

