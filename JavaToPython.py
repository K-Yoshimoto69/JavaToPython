#!/usr/bin/env python3
"""
Java ソースを Python に近い形へ変換する CLI。

用法:
  JavaToPython <入力.java> <出力.py>

※ 複雑な Java 構文は javalang 利用時でも完全には写せません。
  javalang を入れる場合: python -m pip install javalang
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable


def _try_javalang(java_text: str) -> str | None:
    try:
        import javalang
        import javalang.tree as jtree
    except ImportError:
        return None

    try:
        tree = javalang.parse.parse(java_text)
    except javalang.parser.JavaSyntaxError:
        return None

    AnnotationDeclaration = getattr(jtree, "AnnotationDeclaration", None)
    ClassDeclaration = getattr(jtree, "ClassDeclaration", None)
    ConstructorDeclaration = getattr(jtree, "ConstructorDeclaration", None)
    EnumDeclaration = getattr(jtree, "EnumDeclaration", None)
    FieldDeclaration = getattr(jtree, "FieldDeclaration", None)
    InterfaceDeclaration = getattr(jtree, "InterfaceDeclaration", None)
    MethodDeclaration = getattr(jtree, "MethodDeclaration", None)

    lines: list[str] = []
    pkg = getattr(tree.package, "name", None) if tree.package else None
    if pkg:
        lines.append(f"# Java package: {pkg}")
        lines.append("")

    for imp in tree.imports or []:
        wc = getattr(imp, "wildcard", False)
        suffix = ".*" if wc else ""
        lines.append(f"# import {imp.path}{suffix}")

    if tree.imports:
        lines.append("")

    type_decl = getattr(tree, "types", None) or []

    def modifiers_list(mods: Iterable[str] | None) -> list[str]:
        return [str(x) for x in (mods or []) if x]

    def primitive_to_py(name: str) -> str:
        return {
            "void": "None",
            "int": "int",
            "long": "int",
            "short": "int",
            "byte": "int",
            "char": "str",
            "boolean": "bool",
            "float": "float",
            "double": "float",
        }.get(name, name)

    def type_hint(node) -> str:
        if node is None:
            return "Any"
        q = getattr(node, "qualified_name", None)
        if q:
            head = str(q).split("<", 1)[0].split("[", 1)[0].strip()
            return primitive_to_py(head)
        nm_inner = getattr(node, "name", None)
        if nm_inner is not None:
            dim = getattr(node, "dimensions", None) or ()
            base = primitive_to_py(str(nm_inner))
            if len(dim) > 0:
                base += " | list[Any]"
            return base
        return "Any"

    lines.append("from typing import Any, Optional")

    lines.append("")
    lines.append("__all__: list[str] = []")

    def emit_class_body(outer_nm: str, bodies) -> None:
        for mb in bodies or []:
            if AnnotationDeclaration is not None and isinstance(mb, AnnotationDeclaration):
                lines.append("")
                inner = getattr(mb, "name", "Annotation")
                lines.append(f"    # @interface / annotation をスキップ: {inner}")
                continue

            if EnumDeclaration is not None and isinstance(mb, EnumDeclaration):
                inner = getattr(mb, "name", "?")
                lines.append("")
                lines.append(f"    # enum は未対応: {inner}")
                continue

            if ClassDeclaration is not None and isinstance(mb, ClassDeclaration) and getattr(mb, "name", "") != outer_nm:
                inner = getattr(mb, "name", "Inner")
                lines.append("")
                lines.append(f"    class {inner}:")
                lines.append(f'        """nested Java class {inner} (stub)."""')
                lines.append("        ...")
                continue

            if FieldDeclaration is not None and isinstance(mb, FieldDeclaration):
                ftype = type_hint(mb.type)
                decl = getattr(mb, "declarators", None) or getattr(mb, "fragments", None) or []
                for frag_item in decl:
                    fn = getattr(frag_item, "name", "?")
                    init = getattr(frag_item, "initializer", None)
                    if init is not None:
                        lines.append(f"    {fn}: {ftype} = ...  # TODO: initializer")
                    else:
                        lines.append(f"    {fn}: Optional[{ftype}] = None")
                continue

            if MethodDeclaration is not None and isinstance(mb, MethodDeclaration):
                mods_m = modifiers_list(getattr(mb, "modifiers", None))
                mods_txt = ", ".join(mods_m) if mods_m else ""
                mname = mb.name
                rt = type_hint(mb.return_type)

                plist: list[str] = []
                for p in getattr(mb, "parameters", None) or []:
                    pn = getattr(p, "name", "arg")
                    pt = type_hint(getattr(p, "type", None))
                    plist.append(f"{pn}: {pt}")

                is_static = "static" in mods_m
                sig: str
                if is_static:
                    lines.append("    @staticmethod")
                    sig = ", ".join(plist)
                else:
                    sig = ", ".join(["self"] + plist)

                if mods_txt:
                    lines.append(f"    def {mname}({sig}) -> {rt}:  # {mods_txt}")
                else:
                    lines.append(f"    def {mname}({sig}) -> {rt}:")

                b = getattr(mb, "body", None)
                if b is None:
                    lines.append('        """abstract / no body"""')
                    lines.append("        ...")
                else:
                    lines.append(
                        "        # TODO: メソッド本体は手で移植してください（Java と Python の実行モデルが異なるため）"
                    )
                    lines.append("        ...")
                continue

            if ConstructorDeclaration is not None and isinstance(mb, ConstructorDeclaration):
                plist_p = []
                for p in getattr(mb, "parameters", None) or []:
                    pn_p = getattr(p, "name", "arg")
                    pt_p = type_hint(getattr(p, "type", None))
                    plist_p.append(f"{pn_p}: {pt_p}")
                sig_c = ", ".join(["self"] + plist_p)
                lines.append(f"    def __init__({sig_c}) -> None:")
                lines.append("        # TODO: コンストラクタ本体")
                lines.append("        ...")
                continue

            lines.append("")
            lines.append(f"    # 未処理メンバー: {type(mb).__name__}")

    for t in type_decl:
        nm = getattr(t, "name", "JavaType")
        if AnnotationDeclaration is not None and isinstance(t, AnnotationDeclaration):
            lines.append("")
            lines.append(f"# Annotation {nm} はスキップ")
            continue

        if EnumDeclaration is not None and isinstance(t, EnumDeclaration):
            lines.append("")
            lines.append(f"# enum {nm} は未対応（必要なら別途モデル化）")
            continue

        if InterfaceDeclaration is not None and isinstance(t, InterfaceDeclaration):
            lines.append("")
            lines.append(f"class {nm}:")
            lines.append(f'    """Java interface {nm}."""')
            emit_class_body(nm, getattr(t, "body", None))
            lines.append("")
            lines.append(f"__all__.append('{nm}')")
            continue

        if ClassDeclaration is None or not isinstance(t, ClassDeclaration):
            lines.append("")
            lines.append(f"# 未対応の型宣言 ({type(t).__name__}): {nm}")
            continue

        mods = modifiers_list(getattr(t, "modifiers", None))
        mod_txt = ", ".join(mods) if mods else ""
        lines.append("")
        if mod_txt:
            lines.append(f"# Java modifiers: {mod_txt}")

        superclass = getattr(t, "extends", None)
        ext_txt = ""
        if superclass:
            ext_name = getattr(superclass, "name", None)
            if isinstance(ext_name, tuple):
                ext_name = "".join(ext_name)
            elif ext_name is None:
                ext_name = str(superclass)
            ext_txt = f"({ext_name})"

        lines.append(f"class {nm}{ext_txt}:")
        lines.append(f'    """Converted from Java class {nm}."""')

        bodies = getattr(t, "body", None) or []
        emit_class_body(nm, bodies)

        lines.append("")
        lines.append(f"__all__.append('{nm}')")

    return "\n".join(lines) + "\n"


def _fallback_convert(java_text: str) -> str:
    """javalang なしまたはパース失敗時の単純置換。"""
    s = java_text
    lines_out: list[str] = []
    lines_out.append("# -*- coding: utf-8 -*-")
    lines_out.append('"""Javaからの単純トランスファー（ヒューリスティック）。手直し前提。')
    pkg_m = re.search(r"^\s*package\s+([\w.$]+)\s*;", s, re.MULTILINE)
    if pkg_m:
        lines_out.append("")
        lines_out.append(f"Original package: {pkg_m.group(1)}")
        s = re.sub(r"^\s*package\s+[\w.$]+\s*;\s*", "", s, flags=re.MULTILINE)

    lines_out.append('"""')
    lines_out.append("")

    if pkg_m:
        lines_out.append(f"# was: package {pkg_m.group(1)}")

    for im in re.finditer(r'^\s*import\s+(static\s+)?([\w$.]+)(\.\*)?\s*;', s, re.MULTILINE):
        lines_out.append(
            "# import "
            f"{'static ' if im.group(1) else ''}{im.group(2)}{'*' if im.group(3) else ''}"
        )

    lines_out.append("")
    s = re.sub(r"^\s*import\s+([\w\s.$*]+);\s*", "", s, flags=re.MULTILINE)

    s = re.sub(r"/\*.*?\*/", "", s, flags=re.DOTALL)
    s = re.sub(r"^\s*//.*$", "", s, flags=re.MULTILINE)

    pub_class = re.search(r"\bclass\s+(\w+)", re.sub(r"\bpublic\b|\bfinal\b|\babstract\b", " ", s))
    cn = pub_class.group(1) if pub_class else "JavaModule"

    lines_out.append(f"class {cn}:")
    lines_out.append(
        '    """自動生成クラスシェル（元ソース行はコメント）。メソッドは手で移植してください。""'
    )

    for line in s.strip().splitlines():
        ln = line.rstrip()
        if ln.strip():
            lines_out.append("    # " + ln)

    lines_out.append("")
    lines_out.append(f"__all__ = ['{cn}']")

    return "\n".join(lines_out).rstrip() + "\n"


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(
        prog="JavaToPython",
        description="引数1: Javaファイル、引数2: 変換後のPythonファイルへ書き込みます。",
    )
    p.add_argument("java_file", type=Path, help=".java の入力ファイル")
    p.add_argument("python_file", type=Path, help="出力先 .py のパス")

    ns = p.parse_args(argv)

    jp: Path = ns.java_file.resolve()
    out: Path = ns.python_file.resolve()

    if not jp.is_file():
        print(f"エラー: 入力が見つかりません: {jp}", file=sys.stderr)
        return 1

    try:
        text = jp.read_text(encoding="utf-8")
    except OSError as e:
        print(f"エラー: 読み込み失敗: {e}", file=sys.stderr)
        return 1

    converted = _try_javalang(text)
    if converted is None:
        converted = _fallback_convert(text)

    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(converted, encoding="utf-8", newline="\n")
    except OSError as e:
        print(f"エラー: 書き込み失敗: {e}", file=sys.stderr)
        return 1

    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
