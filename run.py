import pathlib,runpy,sys
target=pathlib.Path(__file__).resolve().parent/'sites/mist-blue-lotus/run.py'
sys.path.insert(0,str(target.parent))
runpy.run_path(str(target),run_name='__main__')
