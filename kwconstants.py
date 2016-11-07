# MIT License
#
# Copyright (c) 2016 Emenda Nordic
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


# the following "constants" are indeces to the various .dat files containing
# metrics for the Klocwork analysis. Required files are:
#   - metric_kind.dat
#   - metric.dat
#   - file.dat
#   - entity.dat
#   - attribute.dat
METRIC_KIND_DAT_ID = 0
METRIC_KIND_DAT_REF = 1
METRIC_KIND_DAT_DESCRIPTION = 2

METRIC_DAT_LOC_ID = 0
METRIC_DAT_ID = 1
METRIC_DAT_VALUE = 2

FILE_DAT_LOC_ID = 0
FILE_DAT_PATH = 1

ENTITY_DAT_LOC_ID = 0
ENTITY_DAT_NAME = 3
ENTITY_DAT_DEP_ID = 4
ENTITY_DAT_FILE = 5

ATTRIBUTE_DAT_LOC_ID = 0
ATTRIBUTE_DAT_ATTRIBUTE = 1
ATTRIBUTE_DAT_VALUE = 2

# used for column names in CSV writing
CSV_COLUMN_FILE = "File"
CSV_COLUMN_FUNCTION = "Function"
CSV_COLUMN_CLASS = "Class"

RE_MATCH_METRIC_REFS = '([A-Z]+[0-9]*)'
