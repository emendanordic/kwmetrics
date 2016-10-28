# **************************************************************************************************
#  Emenda Nordic AB.
#
# Disclaimer: Please note that this software or software component is released by Emenda Nordic AB
# on a non-proprietary basis for commercial or non-commercial use with no warranty. Emenda Nordic AB
# will not be liable for any damage or loss caused by the use of this software. Redistribution is
# only allowed with prior consent.
#
# **************************************************************************************************

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
