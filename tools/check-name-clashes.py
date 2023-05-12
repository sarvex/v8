#!/usr/bin/env python
# Copyright 2014 the V8 project authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import js2c
import os
import re
import sys

FILENAME = "src/runtime/runtime.h"
LISTHEAD = re.compile(r"#define\s+(\w+LIST\w*)\((\w+)\)")
LISTBODY = re.compile(r".*\\$")


class Function(object):
  def __init__(self, match):
    self.name = match.group(1).strip()

def ListMacroRe(list):
  macro = LISTHEAD.match(list[0]).group(2)
  re_string = "\s*%s\((\w+)" % macro
  return re.compile(re_string)


def FindLists(filename):
  lists = []
  current_list = []
  mode = "SEARCHING"
  with open(filename, "r") as f:
    for line in f:
      if mode == "SEARCHING":
        if match := LISTHEAD.match(line):
          mode = "APPENDING"
          current_list.append(line)
      else:
        current_list.append(line)
        match = LISTBODY.match(line)
        if not match:
          mode = "SEARCHING"
          lists.append(current_list)
          current_list = []
  return lists


# Detects runtime functions by parsing FILENAME.
def FindRuntimeFunctions():
  functions = []
  lists = FindLists(FILENAME)
  for list in lists:
    function_re = ListMacroRe(list)
    for line in list:
      if match := function_re.match(line):
        functions.append(Function(match))
  return functions


class Builtin(object):
  def __init__(self, match):
    self.name = match.group(1)


def FindJSNatives():
  PATH = "src"
  fileslist = []
  for (root, dirs, files) in os.walk(PATH):
    fileslist.extend(os.path.join(root, f) for f in files if f.endswith(".js"))
  natives = []
  regexp = re.compile("^function (\w+)\s*\((.*?)\) {")
  matches = 0
  for filename in fileslist:
    with open(filename, "r") as f:
      file_contents = f.read()
    file_contents = js2c.ExpandInlineMacros(file_contents)
    lines = file_contents.split("\n")
    partial_line = ""
    for line in lines:
      if line.startswith("function") and '{' not in line:
        partial_line += line.rstrip()
        continue
      if partial_line:
        partial_line += f" {line.strip()}"
        if '{' not in line:
          continue
        line = partial_line
        partial_line = ""
      if match := regexp.match(line):
        natives.append(Builtin(match))
  return natives


def Main():
  functions = FindRuntimeFunctions()
  natives = FindJSNatives()
  errors = 0
  runtime_map = {f.name: 1 for f in functions}
  for b in natives:
    if b.name in runtime_map:
      print(f"JS_Native/Runtime_Function name clash: {b.name}")
      errors += 1

  if errors > 0:
    return 1
  print("Runtime/Natives name clashes: checked %d/%d functions, all good." %
        (len(functions), len(natives)))
  return 0


if __name__ == "__main__":
  sys.exit(Main())
