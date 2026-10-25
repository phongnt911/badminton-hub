import subprocess, sys, json
p = subprocess.run([sys.executable, '-m', 'unittest', 'tests/test_v5b_runner_flaws.py'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
print(json.dumps({'returncode': p.returncode, 'isolated_process_group': True, 'output': p.stdout.decode()}))
