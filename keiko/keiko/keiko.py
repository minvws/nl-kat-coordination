"""Keiko report generation module."""

import csv
import os
import shutil
import subprocess
import tempfile
from logging import DEBUG, ERROR, getLogger
from pathlib import Path
from typing import Any, Dict, Set, Tuple

from jinja2 import Environment, FileSystemLoader
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from keiko.base_models import DataShapeBase
from keiko.settings import Settings
from keiko.templates import get_data_shape

logger = getLogger(__name__)
tracer = trace.get_tracer(__name__)

DATA_SHAPE_CLASS_NAME = "DataShape"

LATEX_SPECIAL_CHARS = str.maketrans(
    {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\^{}",
        "\\": r"\textbackslash{}",
        "\n": "\\newline%\n",
        "-": r"{-}",
        "\xA0": "~",  # Non-breaking space
        "[": r"{[}",
        "]": r"{]}",
    }
)


def latex_escape(text: Any) -> str:
    """Escape characters that are special in LaTeX.

    References:
    - https://github.com/JelteF/PyLaTeX/blob/ecc1e6e339a5a7be958c328403517cd547873d7e/pylatex/utils.py#L68-L100
    - http://tex.stackexchange.com/a/34586/43228
    - http://stackoverflow.com/a/16264094/2570866
    """
    if not isinstance(text, str):
        text = str(text)
    return text.translate(LATEX_SPECIAL_CHARS)


def to_text(text: Any) -> str:
    if not isinstance(text, str):
        text = str(text)

    return text.replace("_", " ").capitalize()


def format_object(obj: Any) -> str:
    if isinstance(obj, str):
        return obj.replace("_", " ").capitalize()

    if isinstance(obj, list):
        return ", ".join([format_object(item) for item in obj])

    return obj


def baretext(text: str) -> str:
    """Remove non-alphanumeric characters from a string."""
    return "".join(filter(str.isalnum, text)).lower()


@tracer.start_as_current_span("generate_report")
def generate_report(
    template_name: str,
    report_data: DataShapeBase,
    glossary: str,
    report_id: str,
    debug: bool,
    settings: Settings,
) -> None:
    """Generate a preprocessed LateX file from a template, a JSON data file and a glossary CSV file."""
    current_span = trace.get_current_span()

    # load data shape and validate
    data_shape_class = get_data_shape(template_name, settings)
    data = data_shape_class.parse_obj(report_data.dict())
    current_span.add_event("Data shape validation successful")
    logger.info(
        "Data shape validation successful. [report_id=%s] [template=%s]",
        report_id,
        template_name,
    )

    # build glossary
    glossary_entries = read_glossary(glossary, settings)
    current_span.add_event("Glossary loaded")
    logger.info("Glossary loaded. [report_id=%s] [glossary=%s]", report_id, glossary)

    # init jinja2 template
    env = Environment(
        loader=FileSystemLoader(settings.templates_folder),
        variable_start_string="@@{",
        variable_end_string="}@@",
    )
    env.filters["latex_escape"] = latex_escape
    env.filters["to_text"] = to_text
    env.filters["format_object"] = format_object
    template = env.get_template(f"{template_name}/template.tex")

    if not template.filename:
        logger.error(
            "Template file not found. [report_id=%s] [template=%s]",
            report_id,
            template_name,
        )
        ex = Exception("Template file %s not found", template_name)
        current_span.set_status(Status(StatusCode.ERROR))
        current_span.record_exception(ex)
        raise ex

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
    current_span.add_event("Template rendered")
    logger.info("Template rendered. [report_id=%s] [template=%s]", report_id, template_name)

    # create temp folder
    with tempfile.TemporaryDirectory() as directory:
        current_span.add_event("Temporary folder created")
        logger.info(
            "Temporary folder created. [report_id=%s] [template=%s] [directory=%s]",
            report_id,
            template_name,
            directory,
        )

        # copy assets
        shutil.copytree(settings.assets_folder, directory, dirs_exist_ok=True)
        current_span.add_event("Assets copied")
        logger.info("Assets copied. [report_id=%s] [template=%s]", report_id, template_name)

        output_file = settings.reports_folder / report_id

        # tex file
        tex_output_file_path = output_file.with_suffix(".keiko.tex")
        pdf_output_file_path = output_file.with_suffix(".keiko.pdf")

        preprocessed_tex_path = Path(directory).joinpath(f"{report_id}.keiko.tex")
        preprocessed_tex_path.write_text(out_document)
        current_span.add_event("TeX file written")

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
            "latexmk",
            "-xelatex",
            "-synctex=1",
            "-interaction=nonstopmode",
            preprocessed_tex_path.as_posix(),
        ]
        env = {**os.environ, "TEXMFVAR": directory}

        def log_output(level, output):
            if not logger.isEnabledFor(level):
                return
            # prefix all lines in output
            for line in output.decode("utf-8").splitlines():
                logger.log(level, "latexmk [report_id=%s] output: %s", report_id, line)

        try:
            # capture all output to stdout, so that lines from stdout+stderr are in correct relative order
            output = subprocess.run(
                cmd, cwd=directory, env=env, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
            )
            current_span.add_event("Completed latexmk")
            logger.info(
                "latexmk [report_id=%s] [template=%s] [command=%s]",
                report_id,
                template_name,
                " ".join(cmd),
            )
            log_output(DEBUG, output.stdout)
        except subprocess.CalledProcessError as ex:
            log_output(ERROR, ex.stdout)
            err = Exception("Error in latexmk")
            err.__cause__ = ex
            current_span.set_status(Status(StatusCode.ERROR))
            current_span.record_exception(err)
            raise err

        # copy result back to output folder
        shutil.copyfile(
            preprocessed_tex_path.with_suffix(".pdf"),
            pdf_output_file_path,
        )
        current_span.add_event("Report copied to reports folder")
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
            if bare_word:
                glossary_entries[baretext(row[0])] = row[0], row[1]
    return glossary_entries
