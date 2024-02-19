# Keiko
***KAT's PDF report engine***

Keiko works by preprocessing a LateX template and then compiling it to a PDF. Preprocessing is done with
[Jinja2](https://jinja.palletsprojects.com/en/3.1.x/).

Report input data is currently strictly typed and enforced by Pydantic models. This is done for now to avoid
dependencies with other parts of KAT, allowing decoupling and independent development of reports.

## Installation requirements
Install Python requirements with pip in a [venv](https://docs.python.org/3/library/venv.html):
```bash
python3 -m pip install -r requirements.txt
```

Make sure `pdflatex` is installed and added to `$PATH`, because Keiko invokes
`pdflatex -synctex=1 -interaction=nonstopmode {filename}` as a shell subprocess to compile the report.

_Recommended LateX distro for report developers: [MikTex](https://docs.miktex.org/manual/installing.html)_

## File system permissions
Keiko needs to be able to write to the `reports` directory, which should be created before running Keiko.
The location of this folder is configurable with the environment variable `KEIKO_REPORTS_FOLDER`.
If you are running Keiko as a non-root user, make sure that this directory is writable by the user.

Keiko creates a temporary directory for each report, which is deleted after the report is compiled. This directory is
created with Python's [tempfile module](https://docs.python.org/3/library/tempfile.html). This should by default work
fine without any additional configuration.

## Running the API
Start API with:
```bash
uvicorn keiko.app:api
```

And browse to [http://localhost:8000/docs](http://localhost:8000/docs) to see the API documentation. Reports can be
generated using the /reports endpoint. The examples of this endpoint are seeded with the sample.json files found in each
template directory.

After submitting the report request, the report id is immediately returned, while asynchronous processing of the LateX
template is started. After the report is generated, the PDF is available at `/reports/<id>.keiko.pdf`.

## Logging
Keiko logging can be configured through by supplying a `logging.json`, relative to the current working directory of the
process. See [logging.json](logging.json) for an example.

## Building a new template
Create a new directory in the `templates` directory, with the following files:
- `template.tex`: the template file
- `model.json`: the Python Pydantic model, describing the shape of the report input data
- `sample.json`: a sample input data file, this will be automatically shown in the API documentation

As an example, look into the `templates/dns` directory.

## Generating a report
There are two ways to generate a report:
- Using the API and the API examples
- Using the command line

## Testing a report with command line
To speed up debugging and development, a command line interface is provided to test a report without the API.
```bash
python3 -m keiko.cli templates/dns/sample.json
```
