# Data and code for Veronica Porubsky, et al., *Ten best practices for making reproducible biochemical models*, Cell Systems, 2020

This Git repository contains data and code used in the paper Veronica Porubsky, Arthur Goldberg, Anand Rampadarath, David Nickerson, Jonathan Karr, and Herbert Sauro, *Ten best practices for making reproducible biochemical models*, Cell Systems, 2020.

[//]: # (Todo: add exact paper reference; check table number and name.)
[//]: # (Todo: add exact paper reference.)


## Overview
This Git repository contains code and data that were used to create Table 2, Standards and tools ordered by estimated influence.
Reproduce the table by following the instructions below.

## Prerequisites

Running this software requires the following prerequisites:

1. pip
1. Git
1. Python 3
1. An account to the Google Search API with provided by [SerpApi](https://serpapi.com/). As of April, 2020, [free developer trials](https://serpapi.com/#pricing) are available. The 5,000 searches allowed by a trial will be amply sufficient to run this software.
1. Optionally, an [NCBI account](https://www.ncbi.nlm.nih.gov/account/), which will speed up the program.

## Instructions

Clone this repository.

Change directory to `paper_cell_sys__guidelines_4_repro_models_2020`.
Create a file named `keys.py`.
Define a variable called `SERP_API_KEY` in `keys.py` equal to the API key provided by [SerpApi](https://serpapi.com/manage-api-key).
Optionally, create an NCBI API key, and define a variable called `NCBI_API_KEY` in the `keys.py` file equal to it.

Run this Python program to reproduce the table's data:

    eval_tool_n_standard_import.py

The table will be reproduced in two formats.
A LaTeX version is provided in `evaluated_standards.tex`.
A `tsv` version is provided in `evaluated_standards.tsv`.

## Questions or feedback

Contact [Arthur Goldberg](mailto:Arthur_dot_Goldberg@mssm.edu).
