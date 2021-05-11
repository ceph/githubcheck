import os.path
import re

from collections import namedtuple

from .annotation import AnnotationLevel, Annotation


class Parser:
    def __init__(self, base_dir, title):
        self.title = title
        # build finished with problems, 2 warnings.
        # or
        # succeeded
        self.succeed_re = r'build succeeded'
        self.problem_re = r'build finished with problems'
        base_dir = os.path.abspath(base_dir)
        # ... /<path>/doc/foo.rst:108: WARNING: something goes wrong!
        # ... /<path>/doc/foo.rst:108:<confval>:4: WARNING: something goes wrong!
        warning_re1 = (f'{base_dir}/'
                       r'(?P<path>[^:]+):'
                       r'(?P<lineno>\d+):\S*\s'
                       r'(?P<level>WARNING|ERROR):\s'
                       r'(?P<message>.+)$')
        self.warning_re1 = re.compile(warning_re1)
        # ... /<path>/doc/foo.rst: WARNING: something goes wrong!
        warning_re2 = (f'{base_dir}/'
                       r'(?P<path>[^:]+):\s'
                       r'(?P<level>WARNING|ERROR):\s'
                       r'(?P<message>.+)$')
        self.warning_re2 = re.compile(warning_re2)
        self.summary = None

    def _parse_level(self, level):
        if level == 'WARNING':
            return AnnotationLevel.WARNING
        elif level == 'ERROR':
            return AnnotationLevel.FAILURE
        else:
            return AnnotationLevel.NOTICE

    def _match_with_re1(self, line):
        matched = self.warning_re1.search(line)
        if matched is None:
            return None
        path = matched.group('path')
        lineno = int(matched.group('lineno'))
        level = matched.group('level')
        message = matched.group('message')
        return Annotation(path,
                          lineno, lineno,
                          self._parse_level(level),
                          message,
                          None, None,
                          title=self.title,
                          raw_details=line)

    def _match_with_re2(self, line):
        matched = self.warning_re2.search(line)
        if matched is None:
            return None
        path = matched.group('path')
        level = matched.group('level')
        message = matched.group('message')
        return Annotation(path,
                          0, 0,
                          self._parse_level(level),
                          message,
                          None, None,
                          title=self.title,
                          raw_details=line)

    def scan(self, output):
        last_line = None
        for line in output:
            annotation = self._match_with_re1(line)
            if annotation is not None:
                yield annotation
                continue
            annotation = self._match_with_re2(line)
            if annotation is not None:
                yield annotation
                continue
            last_line = line
        if re.match(self.succeed_re, last_line):
            self.conclusion = 'success'
        elif re.match(self.problem_re, last_line):
            self.conclusion = 'failure'
        else:
            self.conclusion = 'failure'
        self.summary = last_line
