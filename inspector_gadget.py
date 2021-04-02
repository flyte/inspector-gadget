from importlib import import_module
import ast
import inspect
import re
from types import ModuleType
from typing import Any, List, Optional, Tuple


class NotCached:
    pass


class ModuleMemberPath:
    def __init__(self, path: str):
        self._path = path

        module_path, member_path = re.match(r"([\w\.]+):?(.*)", path).groups()
        self.module_path: str = module_path
        self.member_path: Optional[str] = member_path or None

        self._module = import_module(self.module_path)

        self._parent_members: List[Any] = []

        self._member = None
        if self.member_path is not None:
            member = self.module
            for member_str in self.member_path.split("."):
                self._parent_members.append(member)
                members = inspect.getmembers(member)
                member = dict(members)[member_str]
            self._member = member

    def __str__(self) -> str:
        return self._path

    @property
    def module(self) -> ModuleType:
        return self._module

    @property
    def member(self) -> Any:
        return self._member

    @property
    def parent_members(self) -> List[Any]:
        return self._parent_members


class Visitor(ast.NodeVisitor):
    def __init__(self, search_id):
        super().__init__()
        self.search_id = search_id
        self.result = None

    def generic_visit(self, node):
        try:
            node_id = node.id
        except AttributeError:
            pass
        else:
            if node_id == self.search_id:
                self.result = node
                return
        super().generic_visit(node)


def source(path: str, start_line_regex=None, finish_on_dedent=False) -> str:
    mm_path = ModuleMemberPath(path)

    src_lines, src_lineno = None, None
    if mm_path.member is None:
        src_lines, src_lineno = inspect.getsourcelines(mm_path.module)
    else:
        try:
            src_lines, src_lineno = inspect.getsourcelines(mm_path.member)
        except TypeError:
            for parent in reversed(mm_path.parent_members):
                try:
                    src_lines, src_lineno = inspect.getsourcelines(parent)
                except TypeError:
                    continue

    if src_lines is None:
        raise ValueError(f"Unable to get source for path '{path}'")

    if start_line_regex is not None:
        for i, line in enumerate(src_lines):
            if re.match(start_line_regex, line):
                src_lines = src_lines[i:]
                break

    if finish_on_dedent:
        start_indent = None
        for i, line in enumerate(src_lines):
            if start_indent is None:
                start_indent = len(line) - len(line.lstrip())
                continue
            indent = len(line) - len(line.lstrip())
            if indent < start_indent:
                src_lines = src_lines[:i]

    return "".join(src_lines)