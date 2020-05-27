# Data and code for Porubsky and Goldberg, et al., *Best practices for making reproducible biochemical models*, Cell Systems, 2020

This Git repository contains data and code used in the paper Veronica Porubsky, Arthur Goldberg, Anand Rampadarath, David Nickerson, Jonathan Karr, and Herbert Sauro, *Best practices for making reproducible biochemical models*, Cell Systems, 2020.

[//]: # (Todo: add exact paper reference.)


## Overview
This Git repository contains code and data that were used to create Table 2, Influence of standards and tools.
Reproduce the table by following the instructions below.

## Prerequisites

Running this software requires the following prerequisites:

1. pip
1. git
1. Python 3
1. An account to the Google Search API provided by [SerpApi](https://serpapi.com/). As of June, 2020, [free developer trials](https://serpapi.com/#pricing) are available. The 5,000 searches allowed by a trial will be amply sufficient to run this software.
1. Optionally, an [NCBI account](https://www.ncbi.nlm.nih.gov/account/), which will speed up the program.

## Instructions

Clone this repository:

    git clone https://github.com/KarrLab/paper_cell_sys__guidelines_4_repro_models_2020.git

Change directory to `paper_cell_sys__guidelines_4_repro_models_2020`.

Create a file named `keys.py`.
In it define a variable called `SERP_API_KEY` equal to the API key provided by [SerpApi](https://serpapi.com/manage-api-key).
Optionally, create an [NCBI API key](https://ncbiinsights.ncbi.nlm.nih.gov/2017/11/02/new-api-keys-for-the-e-utilities/)
, and define a variable called `NCBI_API_KEY` equal to it `keys.py`.
Be careful to keep `keys.py` secure.

Run a Python program to prepare the computing environment:

    python prepare.py

Run a Python program to reproduce the table's data:

    python eval_tool_n_standard_import.py

The table will be updated in two formats.
A LaTeX version is provided in `evaluated_standards.tex` and a `tsv` version is provided in `evaluated_standards.tsv`.

## Questions or feedback

Contact [Arthur Goldberg](mailto:Arthur_dot_Goldberg@mssm.edu).
