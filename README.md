# pyacddb
![License](https://img.shields.io/badge/license-MIT-green.svg)

## What is this
`pyacddb` is a Python package designed for parsing and extracting data from ACDSee-generated XML files. 
Such files have headers like `<ACDDB Version="1.20.0">` and store metadata about digital assets. 
`pyacddb` performs streamlined data manipulation and analysis. It extracts, normalize, and analyze metadata from their ACDSee digital asset management system.

## Installation

Follow these steps to install `pyacddb` using Poetry, ensuring seamless management of dependencies:

1. Install Poetry if it's not already set up on your system. You can find installation instructions on the [Poetry website](https://python-poetry.org/docs/).

2. Clone the `pyacddb` repository:

```bash
git clone https://github.com/yourusername/pyacddb.git
cd pyacddb
poetry install
```

## Usage
To get started with `pyacddb`, here's a simple guide:

```py
from pyacddb.core import extract_keywords

# Specify the path to your ACDSee XML file
xml_file_path = 'path/to/your/data.xml'

# Define the list of keywords (XML tags) you are interested in
keywords = ["Name", "Folder", "FileType", "ImageType", "DBDate", "Caption", "Author"]

# Extract the data into a DataFrame, filtering by your specified keywords
data_df = extract_keywords(xml_file_path, keywords)

# Save the DataFrame to a CSV file for further use or analysis
data_df.to_csv("filtered_output_data.csv", encoding="utf-8-sig")
```


## Features
- Tailored parsing of ACDSee-generated XML files, ensuring accurate metadata extraction.
- Data normalization includes handling special characters
- Utilizes Pandas for efficient data storage and manipulation, catering to diverse data analysis needs.


## License
`pyacddb` is open-sourced software licensed under the MIT License. For more details, see the LICENSE file.