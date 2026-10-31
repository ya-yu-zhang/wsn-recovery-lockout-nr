from pathlib import Path
import os,subprocess,sys,json,hashlib
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parent
TOOLS=PROJECT.parent/'build_tools';NS=PROJECT/'ns3_vendor/ns-allinone-3.44/ns-3.44'
env=os.environ.copy();env['PYTHONPATH']=str(TOOLS);env['TMPDIR']=str(ROOT/'build_tmp');Path(env['TMPDIR']).mkdir(exist_ok=True)
cmake=str(TOOLS/'cmake/data/bin/cmake');ninja=str(TOOLS/'bin/ninja')
cmd=[cmake,'-S',str(NS),'-B',str(NS/'cmake-cache'),'-G','Ninja','-DCMAKE_MAKE_PROGRAM='+ninja,'-DCMAKE_BUILD_TYPE=release','-DNS3_ENABLED_MODULES=lr-wpan','-DNS3_EXAMPLES=OFF','-DNS3_TESTS=OFF','-DNS3_PYTHON_BINDINGS=OFF','-DNS3_PRECOMPILE_HEADERS=OFF','-DNS3_CCACHE=OFF','-DNS3_WARNINGS_AS_ERRORS=OFF','-DCMAKE_CXX_FLAGS=-pipe','-DCMAKE_C_FLAGS=-pipe']
subprocess.run(cmd,env=env,check=True)
first=subprocess.run([cmake,'--build',str(NS/'cmake-cache'),'-j','4'],env=env)
empty=[p for p in(NS/'cmake-cache').rglob('*.o')if not p.stat().st_size]
if empty:
    for p in empty:p.unlink()
    subprocess.run([cmake,'--build',str(NS/'cmake-cache'),'-j','1'],env=env,check=True)
elif first.returncode:raise RuntimeError('Native build failed; inspect retained log')
assert not[p for p in(NS/'cmake-cache').rglob('*.o')if not p.stat().st_size]
sys.path.insert(0,str(ROOT/'engine'));from run_closed_loop import compile_driver
binary=compile_driver();record={'ns3':'3.44','git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=NS,text=True).strip(),'empty_objects_rebuilt':len(empty),'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'python':sys.version,'runtime_LLM_calls':0}
(ROOT/'environment.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)
