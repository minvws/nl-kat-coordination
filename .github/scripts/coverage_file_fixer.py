#!/usr/bin/env python
import argparse
import xml.etree.ElementTree as etree
from pathlib import Path


def path_prefixer(file: Path, prefix: Path) -> None:
    xml = file.read_text()
    root = etree.fromstring(xml)
    for element in root.findall(".//*[@filename]"):
        element.set("filename", prefix.joinpath(element.get("filename")).as_posix())
    file.write_text(etree.tostring(root).decode())


def main():
    parser = argparse.ArgumentParser(description="Prefix paths in coverage.xml files")
    parser.add_argument("file", type=Path, help="Path to the coverage.xml file.")
    parser.add_argument("prefix", type=Path, help="Path to prefix the filenames with.")
    args = parser.parse_args()
    path_prefixer(Path(args.file), Path(args.prefix))


if __name__ == "__main__":
    main()
