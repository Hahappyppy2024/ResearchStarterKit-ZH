"""Focused regression checks for the full source distribution."""
import os,pathlib,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];APP=ROOT/'sites/mist-blue-lotus/app'
os.chdir(APP);sys.path.insert(0,str(APP));(APP/'local-data').mkdir(exist_ok=True)
suite=unittest.TestSuite()
for name in ['test_paper_uploads','test_research_pond','test_research_taxonomy','test_problem_comparison','test_theme_distribution','test_paper_pdf','test_project_papers','test_study','test_lineage','test_workspace_content','test_daily_paper_statistics']:
 suite.addTests(unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=name+'.py'))
result=unittest.TextTestRunner(verbosity=1).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
