""" Estimate relative influence of tools and standards in Ten best practices for making reproducible biochemical models

:Author: Arthur Goldberg <Arthur.Goldberg@mssm.edu>
:Date: 2020-04-21
:Copyright: 2020, Karr Lab
:License: MIT
"""
from openpyxl import load_workbook
from pprint import pprint
from serpapi.google_scholar_search_results import GoogleScholarSearchResults
import ast
import bibtexparser
import collections
import collections
import datetime
import keys
import re
import requests
import subprocess
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET


BIBLIOGRAPHY = 'paper_cell_sys__guidelines_4_repro_models_2020.bib'
CURATED_STANDARDS_FILE = 'curated_standards.xlsx'
SURVEY_RESPONSES_FILE = 'paper_2018_curr_opin_sys_biol/survey_responses-edited2.xlsx'
OUTPUT_LATEX_TABLE_FILE = 'evaluated_standards.tex'
TOOL_EMAIL = 'tool=mssm_citation_research&email=Arthur.Goldberg%40mssm.edu'
EUTILS = 'eutils.ncbi.nlm.nih.gov/entrez/eutils'
NCBI_ELINK_TEMPLATE = (f"https://{EUTILS}/elink.fcgi?dbfrom=pubmed&linkname=pubmed_pmc_ref"
                       f"s&id={{}}&{TOOL_EMAIL}")
NCBI_ESEARCH_TEMPLATE = f"https://{EUTILS}/esearch.fcgi?db=pubmed&term={{}}"
ESUMMARY_TEMPLATE = f"https://{EUTILS}/esummary.fcgi?db=pubmed&id={{}}&retmode=json&{TOOL_EMAIL}"


class GoogleScholar(object):

    # To use SerpApi, create an account, get your private API key, create a keys.py file on the Python PATH, assign
    #   SERP_API_KEY = 'your private API key'
    # in keys.py. Keep keys.py secure.
    SERP_API_KEY = keys.SERP_API_KEY

    @staticmethod
    def get_gs_results(title, mock=False):
        # get num citations, publication year, and title from GS
        if mock:
            # test version of get_gs_results, which avoids using billable searches
            return '', len(title), 2000 + len(title)/10, []

        errors = []
        pub_year = None
        client = GoogleScholarSearchResults({"q": title, "serp_api_key": GoogleScholar.SERP_API_KEY})
        data = client.get_json()
        summary = data['organic_results'][0]['publication_info']['summary']
        PUB_YEAR_RE = '(\d\d\d\d)'
        match = re.search(PUB_YEAR_RE, summary)
        if match is None:
            errors.append(f"cannot get year for {title}")
        else:
            pub_year = int(match.group(1))
        num_citations = data['organic_results'][0]["inline_links"]["cited_by"]["total"]
        gs_title = data['organic_results'][0]["title"]
        return gs_title, num_citations, pub_year, errors


class NCBIUtils(object):

    SLEEP_TIME = 2.0
    NCBI_API_KEY = None
    # see https://ncbiinsights.ncbi.nlm.nih.gov/2017/11/02/new-api-keys-for-the-e-utilities/
    if hasattr(keys, 'NCBI_API_KEY'):
        NCBI_API_KEY = keys.NCBI_API_KEY
        SLEEP_TIME = 0.1

    @staticmethod
    def add_key(url):
        if NCBIUtils.NCBI_API_KEY:
            return url + f'&api_key={NCBIUtils.NCBI_API_KEY}'
        return url

    @staticmethod
    def get_pm_id(title):
        """ Get PubMed ID for a title from the PutMed service, if possible """
        url = NCBI_ESEARCH_TEMPLATE.format(urllib.parse.quote(title))
        url = NCBIUtils.add_key(url)
        errors = []
        time.sleep(NCBIUtils.SLEEP_TIME)
        response = requests.get(url)
        if response.status_code != requests.codes.ok:
            errors.append(f"NCBI_ESEARCH_TEMPLATE request error {response.status_code} for title '{title}'")
            return None, errors
        root = ET.fromstring(response.text)
        pm_ids = [int(id.text) for id in root.iter('Id')]
        if len(pm_ids) == 0:
            return None, None
        if len(pm_ids) == 1:
            return pm_ids[0], None
        elif 1 < len(pm_ids):
            for pm_id in pm_ids:
                _, pm_title, errors = NCBIUtils.get_pub_metadata(pm_id)
                if errors:
                    return None, errors
                # ignore case in match
                if pm_title.casefold() == title.casefold():
                    return pm_id, None
            return None, None

    @staticmethod
    def get_num_citations(pm_id):
        url = NCBI_ELINK_TEMPLATE.format(pm_id)
        url = NCBIUtils.add_key(url)
        errors = []
        time.sleep(NCBIUtils.SLEEP_TIME)
        response = requests.get(url)
        if response.status_code != requests.codes.ok:
            errors.append(f"request error {response.status_code} for pmc_id {pmc_id}")
            return None, errors
        return NCBIUtils.get_num_citations_from_xml(response.text), None

    @staticmethod
    def get_num_citations_from_xml(xml_string):
        root = ET.fromstring(xml_string)
        num_citations = len(list(root.iter('Id'))) - 1
        return num_citations

    @staticmethod
    def get_pub_metadata(pm_id):
        # get publication year
        url = ESUMMARY_TEMPLATE.format(pm_id)
        errors = []
        time.sleep(NCBIUtils.SLEEP_TIME)
        response = requests.get(url)
        if response.status_code != requests.codes.ok:
            errors.append(f"request error {response.status_code} for pm_id {pm_id}")
            return (None, errors)
        resp_dict = dict(ast.literal_eval(response.text))
        pubdate = resp_dict["result"][str(pm_id)]["pubdate"]
        PUB_YEAR_RE = "(\d+)"
        match = re.search(PUB_YEAR_RE, pubdate)
        if match is None:
            errors.append(f"year not found in '{pubdate}' for {pm_id}")
        else:
            pub_year = int(match.group(1))
        # get title
        title = resp_dict["result"][str(pm_id)]["title"][:-1]
        return pub_year, title, errors


class Biblio(object):
    def __init__(self, filename):
        self.filename = filename
        with open(filename) as bibtex_file:
            self.bib_database = bibtexparser.load(bibtex_file)

    def get_entry_key(self, title):
        """ Get the bibliography key for a title """
        for citation in self.bib_database.entries:
            if citation['title'] == title:
                return citation['ID']


class CuratedStandards(object):

    # curated standard keys
    STANDARD = 'Standard / tool'
    TYPE = 'Type'
    TITLE = 'Title'
    BIB_KEY = 'bib_key'
    PUB_YEAR = 'pub_year'
    PM_ID = 'PM_id'
    PM_CITATIONS = 'PM_citations'
    GS_CITATIONS = 'GS_citations'
    SURVEY_ADOPTION_RATE = 'survey_adoption_rate'

    def __init__(self, filename, biblio):
        self.filename = filename
        self.biblio = biblio
        self.curated_standards = self.spreadsheet_into_dicts(filename)

    @staticmethod
    def spreadsheet_into_dicts(filename):
        """ Read first worksheet in an Excel workbook with column headers into a list of dictionaries
        """
        workbook = load_workbook(filename, data_only=True)
        worksheet = workbook.active
        field_names = [col_name_cell.value for col_name_cell in worksheet[1]]
        records = []
        for row in worksheet.iter_rows(min_row=2):
            new_record = {}
            for field_name, cell in zip(field_names, row):
                new_record[field_name] = cell.value
            records.append(new_record)
        return records

    def check_all_titles(self):
        titles = self.read_curated_standards_column(self.TITLE)
        missing = set()
        for title in titles:
            if not self.biblio.get_entry_key(title):
                missing.add(title)
        if missing:
            print('Missing titles:', missing, file=sys.stderr)
        else:
            print(f"All {len(titles)} title(s) found in '{self.biblio.filename}'.")

    def read_curated_standards_column(self, col_name):
        entries = []
        for curated_standard in self.curated_standards:
            if col_name in curated_standard:
                entries.append(curated_standard[col_name])
        return entries

    def enrich_with_pm_ids(self):
        missing_ids = []
        for curated_standard in self.curated_standards:
            title = curated_standard[self.TITLE]
            pm_id, errors = NCBIUtils.get_pm_id(curated_standard[self.TITLE])
            if pm_id is not None:
                curated_standard[self.PM_ID] = pm_id
            elif errors is None:
                missing_ids.append((title, 'no error'))
            else:
                missing_ids.append((title, errors))
        if missing_ids:
            print('Titles missing PM citations:', file=sys.stderr)
            pprint(missing_ids, stream=sys.stderr)
        else:
            print('All references have PM ids.')

    def enrich_with_num_pm_citations(self):
        missing_pm_cites = []
        for curated_standard in self.curated_standards:
            if self.PM_ID in curated_standard:
                pm_id = curated_standard[self.PM_ID]
                num_citations, errors = NCBIUtils.get_num_citations(pm_id)
                if num_citations is not None:
                    curated_standard[self.PM_CITATIONS] = num_citations
                else:
                    title = curated_standard[self.TITLE]
                    missing_pm_cites.append(title)
        if missing_pm_cites:
            print('Titles missing PM citations:', file=sys.stderr)
            pprint(missing_pm_cites, file=sys.stderr)
        else:
            print('All references with PM ids have PM citations.')

    def enrich_with_bib_key(self):
        missing_bib_keys = []
        for curated_standard in self.curated_standards:
            title = curated_standard[self.TITLE]
            entry_key = self.biblio.get_entry_key(title)
            if entry_key is not None:
                curated_standard[self.BIB_KEY] = entry_key
            else:
                missing_bib_keys.append(title)
        if missing_bib_keys:
            print('Titles missing bib key:', file=sys.stderr)
            pprint(missing_bib_keys, stream=sys.stderr)
        else:
            print('All references have bibliography keys.')

    def enrich_with_gs_data(self):
        missing_gs_data = []
        for curated_standard in self.curated_standards:
            title = curated_standard[self.TITLE]
            gs_title, num_citations, pub_date, errors = GoogleScholar.get_gs_results(title)
            if num_citations is None or pub_date is None or errors:
                missing_gs_data.append((title, errors))
            else:
                curated_standard[self.GS_CITATIONS] = num_citations
                curated_standard[self.PUB_YEAR] = pub_date
        if missing_gs_data:
            print('Titles not found on Google Scholar:', file=sys.stderr)
            pprint(missing_gs_data, stream=sys.stderr)
        else:
            print('All references found on Google Scholar.')

    def enrich_with_survey_data(self):
        survey = collections.defaultdict(list)
        for response in self.spreadsheet_into_dicts(SURVEY_RESPONSES_FILE):
            for col_name, value in response.items():
                survey[col_name].append(value)
        questions = \
            ['If you use models in your research, which tools do you most frequently use to build and/or simulate models?',
             'If you use models in your research, which resources do you most frequently use to distribute models?',
             'If you use models in your research, which languages do you most frequently use to represent models?']
        adoption = {}
        # number of subjects answering each question
        num_answers = collections.defaultdict(int)
        for question in questions:
            adoption[question] = collections.defaultdict(int)
            for responses in survey[question]:
                if responses:
                    num_answers[question] += 1
                    for tool in responses.split(';'):
                        # adoption is the number of uses of each tool, by question
                        adoption[question][tool] += 1
        fractional_adoption = {}
        for question in adoption:
            for tool, count in adoption[question].items():
                # some tools are responses to multiple questions; take the largest fractional adoption
                fractional_adoption[tool] = max(count/num_answers[question],
                                                fractional_adoption.get(tool, 0))
        for curated_standard in self.curated_standards:
            if curated_standard[self.STANDARD] in fractional_adoption:
                curated_standard[self.SURVEY_ADOPTION_RATE] = fractional_adoption[curated_standard[self.STANDARD]]
        print('Survey data incorporated.')

    @staticmethod
    def year_fraction(date):
        # from https://stackoverflow.com/a/36949905
        start = datetime.date(date.year, 1, 1).toordinal()
        year_length = datetime.date(date.year+1, 1, 1).toordinal() - start
        return date.year + float(date.toordinal() - start) / year_length

    @staticmethod
    def drop_columns(row, cols_to_drop):
        new_row = []
        for entry, drop in zip(row, cols_to_drop):
            if not drop:
                new_row.append(entry)
        return new_row

    LATEX_PACKAGES_AND_COMMANDS = r"""
% packages & commands used by "Standards and tools ordered by estimated influence" table
\usepackage{booktabs}
\usepackage{array}
\usepackage{longtable}
\usepackage{import}
% see: https://tex.stackexchange.com/a/119561
\newcolumntype{R}[1]{>{\raggedleft\arraybackslash}p{#1}}
\newcolumntype{L}[1]{>{\raggedright\arraybackslash}p{#1}}
"""
    def generate_latex_table(self, columns_to_drop=None):
        # columns: standard, type, title with reference, year published, PM citations / year, GS citations / year
        # columns_to_drop contains true values for columns to remove from the table
        columns = (self.STANDARD,
                   'Type of standard / tool',
                   'Most cited paper',
                   'Paper year',
                   'PubMed (cites / yr)',
                   'Scholar (cites / yr)',
                   r'Use in survey (\%)')

        column_alignments = ('L{2.2cm}',
                             'L{4cm}',
                             'L{1cm}',
                             'L{0.8cm}',
                             'R{1.1cm}',
                             'R{1cm}',
                             'R{1cm}')
        small_columns = (1,
                         1,
                         0,
                         1,
                         1,
                         1,
                         1)
        n_columns = len(columns)
        current_year = self.year_fraction(datetime.datetime.today())
        rows = []
        for curated_standard in self.curated_standards:

            row = [''] * n_columns
            row[0] = curated_standard[self.STANDARD]
            row[1] = curated_standard[self.TYPE]
            row[2] = fr"\cite{{{curated_standard[self.BIB_KEY]}}}"

            if self.PUB_YEAR in curated_standard:
                row[3] = str(curated_standard[self.PUB_YEAR])
                age = current_year - curated_standard[self.PUB_YEAR]
                if age <= 0:
                    print(f"age ({age}) of '{curated_standard[self.TITLE]}' <= 0", file=sys.stderr)
                    continue

                # compute PM citations / year
                if self.PM_CITATIONS in curated_standard:

                    PM_cites_per_year = curated_standard[self.PM_CITATIONS] / age
                    row[4] = f"{PM_cites_per_year:.1f}"

                # compute GS citations / year
                if self.GS_CITATIONS in curated_standard:

                    GS_cites_per_year = curated_standard[self.GS_CITATIONS] / age
                    row[5] = f"{GS_cites_per_year:.1f}"

                if self.SURVEY_ADOPTION_RATE in curated_standard:
                    pct_adoption = curated_standard[self.SURVEY_ADOPTION_RATE] * 100.
                    row[6] = f"{pct_adoption:.1f}"

            rows.append(row)

        # sort rows by decreasing Google Scholar citations
        rows.sort(key=lambda curated_std: float(curated_std[5]), reverse=True)

        tmp_rows = []
        for row in rows:
            sized_row = []
            for shrink, entry in zip(small_columns, row):
                if shrink:
                    entry = fr"\small{{{entry}}}"
                sized_row.append(entry)
            tmp_rows.append(sized_row)
        rows = tmp_rows

        CAPTION = r"""Standards and tools ordered by estimated influence.
The standards and tools recommended in this paper are ordered by their annual citation rates for their
primary publications, as measured by Google Scholar.
To provide a measure of influence focused on biomedical research PubMed citations per year are shown when available.
The Type column categorizes each tool by its overall purpose.\\
\\
Reproducible methods were used to obtain these data.
Two hand-curated tables were input: a list of the standards and tools containing the titles of the primary publications, and a LaTeX bibliography containing the papers.
Each paper's publication year and Google Scholar citation counts were obtained via a Google Scholar API.
PubMed citation counts were obtained via the PubMed API \cite{sayers2010general}.
These analyses can be reproduced by executing a single command.
The hand-curated tables and source code for this analysis are available at \cite{GoldbergReproToolsAnalysis}."""

        END_OF_LINE = r'\\' + '\n'
        HLINE = r'\hline' + '\n'
        TOPRULE = r'\toprule' + '\n'
        MIDRULE = r'\midrule' + '\n'

        TABLE_START = '\n' + r'\begin{longtable}'
        TABLE_END = r'\bottomrule\end{longtable}' + '\n'
        table = [TABLE_START]
        if columns_to_drop:
            column_alignments = drop_columns(column_alignments, columns_to_drop)
        table.append('{' + ''.join(column_alignments) + '}\n')
        table.append(fr"\caption{{{CAPTION}}}\\" + '\n')
        if columns_to_drop:
            columns = drop_columns(columns, columns_to_drop)
        small_columns = [fr"\scriptsize{{{col}}}" for col in columns]

        header = []
        header.append(TOPRULE)
        header.append(' &'.join([fr"\textbf{{{col}}}" for col in small_columns]))
        header.append(r'\\' + '\n')

        table.append('% header for first page\n')
        table.extend(header)
        table.append(r'\endfirsthead' + '\n')

        table.append('% same header for subsequent pages\n')
        table.extend(header)
        table.append(MIDRULE)
        table.append(r'\endhead' + '\n')

        for row in rows:
            if columns_to_drop:
                row = drop_columns(row, columns_to_drop)
            table.append(MIDRULE)
            table.append(' &'.join(row))
            table.append(END_OF_LINE)

        table.append(TABLE_END)
        complete_table = ''.join(table)
        return complete_table

    def output_latex_table(self, filename=OUTPUT_LATEX_TABLE_FILE, columns_to_drop=None):
        with open(filename, 'w') as latex_table:
            latex_table.write(self.generate_latex_table(columns_to_drop=columns_to_drop))


def prepare():
    # git clone https://github.com/KarrLab/paper_2018_curr_opin_sys_biol.git
    result = subprocess.run(['git', 'clone', 'https://github.com/KarrLab/paper_2018_curr_opin_sys_biol.git'],
                            stdout=subprocess.PIPE)
    if "Cloning into 'paper_2018_curr_opin_sys_biol'" not in result.output:
        pass
    # test that keys.py exists and contains SERP_API_KEY


def main():
    biblio = Biblio(BIBLIOGRAPHY)
    curated_standards = CuratedStandards(CURATED_STANDARDS_FILE, biblio)
    curated_standards.check_all_titles()
    curated_standards.enrich_with_bib_key()
    curated_standards.enrich_with_survey_data()
    curated_standards.enrich_with_gs_data()
    curated_standards.enrich_with_pm_ids()
    curated_standards.enrich_with_num_pm_citations()
    curated_standards.output_latex_table()

if __name__ == '__main__':
    main()
