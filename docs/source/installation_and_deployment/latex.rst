==================================
How do I customize LaTeX reports ?
==================================

The LaTeX reports can be customized in a number of ways. You can customize the current ``bevindingenrapport`` by locating it within the ``keiko`` directory and start making changes to the code.


Styling changes
===============

You can start off by changing the front-page on the report, swap out the ``keiko.png`` with the logo of your organization by adding the image to the ``keiko\assets`` directory and then changing the image in the ``\titlepic``.


.. code-block::

    % Title Page
    \title{ \reporttitle{} }
    \author{ \application{} }
    \titlepic{\includegraphics[width=70mm]{myorganization.png}}

You can change the report title and author by changing the Keiko specific variables, you can change the title of your report or edit the ``\application`` in order to set another author.

.. code-block::

    %KEIKO-specific variables
    \newcommand\application{KEIKO @@{keiko_version}@@}
    \newcommand\reporttitle{Bevindingenrapport voor @@{report_source_type}@@ @@{report_source_value}@@}
    \newcommand\tlp{AMBER}
    \newcommand\tlpbox{\colorbox{black}{\color{orange}TLP:AMBER}}
    %END-KEIKO

The variables which take input from the KAT datamodel are defined as Jinja2 variables, for example: ``@@{report_source_type}@@``.
The model behind the report is defined in ``keiko/templates/bevindingenrapport/model.py`` and this dictates which variables can be used in your reports.

Text colours
************

Want to change the current chapter colours? include the ``\usepackage`` lines at the start of your report and set your desired colours.

.. code-block::

    \usepackage{xcolor}
    \usepackage{sectsty}

    \chapterfont{\color{blue}}  % sets colour of chapters
    \sectionfont{\color{cyan}}  % sets colour of sections

Want to add color to your tables and rows? Add the ``\rowcolor{}`` after the begin of your tables.

.. code-block::

    \bgroup{}
    \def\arraystretch{1.2}
    \section{Totalen}
    \begin{tabular}{ llr }
        \rowcolor{\color{blue}

Readable findings
=================

``@@{finding.ooi}@@`` generates the following string in your reports: ``KAT-WEBSERVER-NO-IPV6—mysubdomain-domain-toplevel``
This can be long and might be hard to read or interpret.
You can change this to ``@@{finding.human_readable}@@`` to generate strings like this: ``KAT-WEBSERVER-NO-IPV6 @ mysubdomain.domain.toplevel``

Changing fonts
==============

You can change your current document font with the inclusion of this code to set it to ``Liberation Serif`` for example. These fonts can be selected by naming a Truetype or Opentype font, which can be listed with ``fc-list`` in the Keiko container.

Additional docs with regards to fontspec can be found at `Texdoc
<https://texdoc.org/serve/fontspec.pdf/0>`__.

.. code-block::

    \usepackage{fontspec}
    \setmainfont{Liberation Serif}

Another option is to manually add your font ``.ttf`` or ``.otf`` file to the ``keiko\assets`` directory, from there you can specify the use of your font file like this:

.. code-block::

    \usepackage{fontspec}
    \setmainfont{trebuc.ttf}
