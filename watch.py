#!/bin/env python3

from ctypes import c_double, c_wchar_p
import importlib
import importlib.util
import inotify.adapters
import inotify.constants
import multiprocessing as mp
import os
from pathlib import Path
import signal
import time
import traceback
import sys

def inotify_work(parent_pid: int, script_path: mp.Value, script_update_time):
	i = inotify.adapters.InotifyTree("./solutions", inotify.constants.IN_MODIFY | inotify.constants.IN_ATTRIB)
	prev_update = (Path("/"), 0)
	for (*_, path, filename) in i.event_gen(yield_nones=False):
		path = Path(path) / filename
		if path.suffix != ".py":
			continue
		update = (path, path.stat().st_mtime)
		if update == prev_update:
			continue
		prev_update = update
		script_path.value = str(update[0])
		script_update_time.value = update[1]
		os.kill(parent_pid, signal.SIGUSR1)


class ModifiedScriptException(Exception):
	...

is_processing = False

def on_script_updated(signum, stack):
	"""
	Interrupt if we are currently processing a script.
	"""
	global is_processing
	if is_processing:
		is_processing = False
		raise ModifiedScriptException()


def run_solution(path: Path):
	try:
		rel_path = path.absolute().relative_to(Path.cwd())
		assert rel_path.parts[0] == "solutions"
	except Exception as e:
		print("Invalid script path...")
		return
	try:
		spec = importlib.util.spec_from_file_location("solution", rel_path)
		solution = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(solution)
	except Exception as e:
		print(traceback.format_exc())


def main():
	global is_processing

	# Signal handling
	signal.signal(signal.SIGUSR1, on_script_updated)

	# Inotify Process
	manager = mp.Manager()
	script_path = manager.Value(c_wchar_p, "")
	script_update_time = manager.Value(c_double, 0.0)
	inotify_process = mp.Process(target=inotify_work, args=[os.getpid(), script_path, script_update_time])
	inotify_process.start()

	# If given a file, touch it to trigger an inotify event.
	if len(sys.argv) > 1:
		script_path.value = sys.argv[1]
		script_update_time.value = Path(sys.argv[1]).stat().st_mtime

	last_update_time = 0.0
	try:
		while True:
			if script_update_time.value <= last_update_time:
				continue
			try:
				t = script_update_time.value
				path = script_path.value
				is_processing = True
				os.system("clear")
				run_solution(Path(path))
				is_processing = False
				last_update_time = t
			except ModifiedScriptException:
				...
	except KeyboardInterrupt:
		pass
	inotify_process.kill()


if __name__ == "__main__":
	main()
