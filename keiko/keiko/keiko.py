"""Keiko report generation module."""

import csv
import os
import shutil
import subprocess
import tempfile
from logging import getLogger
from pathlib import Path
from typing import Dict, Set, Tuple

from jinja2 import Environment, FileSystemLoader, select_autoescape

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
    with Path(template.filename).open(encoding="utf-8") as template_file:
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
    with tempfile.TemporaryDirectory() as directory:
        logger.info(
            "Temporary folder created. [report_id=%s] [template=%s] [directory=%s]",
            report_id,
            template_name,
            directory,
        )

        # copy assets
        shutil.copytree(settings.assets_folder, directory, dirs_exist_ok=True)
        logger.info("Assets copied. [report_id=%s] [template=%s]", report_id, template_name)

        output_file = settings.reports_folder / report_id

        # tex file
        tex_output_file_path = output_file.with_suffix(".keiko.tex")
        pdf_output_file_path = output_file.with_suffix(".keiko.pdf")

        preprocessed_tex_path = Path(directory).joinpath(f"{report_id}.keiko.tex")
        preprocessed_tex_path.write_text(out_document)

        # if debug is enabled copy preprocessed tex file and input data
        if debug or settings.debug:
            shutil.copyfile(
                preprocessed_tex_path,
                tex_output_file_path,
            )

            json_output_file_path = output_file.with_suffix(".keiko.json")
            json_output_file_path.write_text(report_data.json(indent=4))

        # run pdflatex
        cmd = [
            "pdflatex",
            "-synctex=1",
            "-interaction=nonstopmode",
            preprocessed_tex_path.as_posix(),
        ]
        env = {**os.environ, "TEXMFVAR": directory}
        for i in (1, 2):
            output = subprocess.run(cmd, cwd=directory, env=env, capture_output=True, check=False)
            logger.info(
                "pdflatex [run=%d] [report_id=%s] [template=%s] [command=%s]",
                i,
                report_id,
                template_name,
                " ".join(cmd),
            )
            if output.returncode:
                logger.error("stdout: %s", output.stdout.decode("utf-8"))
                logger.error("stderr: %s", output.stderr.decode("utf-8"))
                raise Exception("Error in pdflatex run %d", i)
            else:
                logger.debug(output.stdout.decode("utf-8"))
                logger.debug(output.stderr.decode("utf-8"))

        # copy result back to output folder
        shutil.copyfile(
            preprocessed_tex_path.with_suffix(".pdf"),
            pdf_output_file_path,
        )
        logger.info(
            "Report copied to reports folder. [report_id=%s] [template=%s] [output_file=%s]",
            report_id,
            template_name,
            pdf_output_file_path,
        )

    # ...tempfiles are deleted automatically when leaving the context


def read_glossary(glossary: str, settings: Settings) -> Dict[str, Tuple[str, str]]:
    """Read a glossary CSV file and return a dictionary of entries."""
    glossary_entries = {}
    glossary_file_path = settings.glossaries_folder / glossary
    with glossary_file_path.open(encoding="utf-8") as glossary_file:
        csvreader = csv.reader(glossary_file)
        # skip header
        _ = next(csvreader)
        for row in csvreader:
            # only allow words with baretext representation
            bare_word = baretext(row[0])
            if bare_word != "":
                glossary_entries[baretext(row[0])] = row[0], row[1]
    return glossary_entries
