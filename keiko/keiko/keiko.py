"""Keiko report generation module."""

import csv
import os
import shutil
import subprocess
import tempfile
from logging import getLogger
from pathlib import Path
from typing import Set, Tuple, Dict

from jinja2 import Environment, select_autoescape, FileSystemLoader

from keiko.base_models import DataShapeBase
from keiko.settings import Settings
from keiko.templates import get_data_shape

logger = getLogger(__name__)

DATA_SHAPE_CLASS_NAME = "DataShape"


def baretext(input_: str) -> str:
    """Remove non-alphanumeric characters from a string."""
    return "".join(filter(str.isalnum, input_)).lower()


def generate_report(
    template_name: str,
    report_data: DataShapeBase,
    glossary: str,
    report_id: str,
    debug: bool,
    settings: Settings,
) -> None:
    """Generate a preprocessed LateX file from a template, a JSON data file and a glossary CSV file."""
    # load data shape and validate
    data_shape_class = get_data_shape(template_name, settings)
    data = data_shape_class.parse_obj(report_data.dict())
    logger.info(
        "Data shape validation successful. [report_id=%s] [template=%s]",
        report_id,
        template_name,
    )

    # build glossary
    glossary_entries = read_glossary(glossary, settings)
    logger.info("Glossary loaded. [report_id=%s] [glossary=%s]", report_id, glossary)

    # init jinja2 template
    env = Environment(
        loader=FileSystemLoader(settings.templates_folder),
        autoescape=select_autoescape(),
        variable_start_string="@@{",
        variable_end_string="}@@",
    )
    template = env.get_template(f"{template_name}/template.tex")

    if not template.filename:
        logger.error(
            "Template file not found. [report_id=%s] [template=%s]",
            report_id,
            template_name,
        )
        return

    # read template and find used glossary entries
    found_entries: Set[str] = set()
    with open(template.filename, encoding="utf-8") as template_file:
        for line in template_file:
            for word in line.split():
                bare_word = baretext(word)
                if bare_word in glossary_entries:
                    found_entries.add(bare_word)

    context = data.dict()

    # build and merge glossary
    glossary_items = []
    for bare_word in sorted(found_entries):
        term, description = glossary_entries[bare_word]
        glossary_items.append((term, description))
    context["glossary_items"] = glossary_items

    # render template
    out_document = template.render(**context)
    logger.info("Template rendered. [report_id=%s] [template=%s]", report_id, template_name)

    # create temp folder
    with tempfile.TemporaryDirectory() as tmp_dirname:
        logger.info(
            "Temporary folder created. [report_id=%s] [template=%s] [tmp_dirname=%s]",
            report_id,
            template_name,
            tmp_dirname,
        )

        # copy assets
        shutil.copytree(settings.assets_folder, tmp_dirname, dirs_exist_ok=True)
        logger.info("Assets copied. [report_id=%s] [template=%s]", report_id, template_name)

        # tex file
        tex_output_file_name = report_id + ".keiko.tex"
        pdf_output_file_name = report_id + ".keiko.pdf"

        preprocessed_tex = Path(tmp_dirname) / tex_output_file_name
        preprocessed_tex.write_text(out_document)

        # copy preprocessed tex file if debug is enabled
        if debug or settings.debug:
            shutil.copyfile(
                Path(tmp_dirname) / tex_output_file_name,
                Path(settings.reports_folder) / tex_output_file_name,
            )

        # run pdflatex
        cmd = [
            "pdflatex",
            "-synctex=1",
            "-interaction=nonstopmode",
            tex_output_file_name,
        ]
        env = {**os.environ, "TEXMFVAR": tmp_dirname}
        for i in range(2):
            output = subprocess.run(cmd, cwd=tmp_dirname, env=env, capture_output=True, check=False)
            logger.info(
                "pdflatex [run=%d] [report_id=%s] [template=%s] [command=%s]",
                i,
                report_id,
                template_name,
                " ".join(cmd),
            )
            if output.returncode:
                logger.error(output.stdout.decode("utf-8"))
                logger.error(output.stderr.decode("utf-8"))
                raise Exception("Error in pdflatex run %d", i)
            else:
                logger.debug(output.stdout.decode("utf-8"))
                logger.debug(output.stderr.decode("utf-8"))

        # copy result back to output folder
        Path(settings.reports_folder).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(
            Path(tmp_dirname) / pdf_output_file_name,
            Path(settings.reports_folder) / pdf_output_file_name,
        )
        logger.info(
            "Report copied to reports folder. [report_id=%s] [template=%s] [output_file=%s]",
            report_id,
            template_name,
            Path(settings.reports_folder) / pdf_output_file_name,
        )

    # ...tempfiles are deleted automatically when leaving the context


def read_glossary(glossary: str, settings: Settings) -> Dict[str, Tuple[str, str]]:
    """Read a glossary CSV file and return a dictionary of entries."""
    glossary_entries = {}
    glossary_file_path = Path(settings.glossaries_folder) / glossary
    with open(glossary_file_path, encoding="utf-8") as glossary_file:
        csvreader = csv.reader(glossary_file)
        # skip header
        _ = next(csvreader)
        for row in csvreader:
            # only allow words with baretext representation
            bare_word = baretext(row[0])
            if bare_word != "":
                glossary_entries[baretext(row[0])] = (row[0], row[1])
    return glossary_entries
