# **************************************************************************************************
#  Emenda Nordic AB.
#
# Disclaimer: Please note that this software or software component is released by Emenda Nordic AB
# on a non-proprietary basis for commercial or non-commercial use with no warranty. Emenda Nordic AB
# will not be liable for any damage or loss caused by the use of this software. Redistribution is
# only allowed with prior consent.
#
# **************************************************************************************************

import argparse, csv, logging, os, re, sys
from collections import namedtuple

import kwconstants as KW_CONST

# namedtuples used to store entries from the Klocwork .dat files
Entity = namedtuple("Entity", "id name dep_id file_name")
MetricKind = namedtuple("MetricKind", "id ref description")
Metric = namedtuple("Metric", "id metric_id value")
File = namedtuple("File", "id path")
Attribute = namedtuple("Attribute", "id attribute value")

# used to store mapped .dat data
EntityMetrics = namedtuple("EntityMetrics", "name metrics")
FuncOrClassMetricKey = namedtuple("FuncOrClassMetricKey", "file_id loc_id")

parser = argparse.ArgumentParser(description='Klocwork Metrics Reporting Script.')
parser.add_argument('--tables-dir', required=True,
    help='Location of the Klocwork tables directory.')
parser.add_argument('--metrics-report', required=False, default='metrics.csv',
    help='Specify a report file for software metrics detected by Klocwork. \
    Requires a list of Klocwork metrics which can be provided using the \
    --metrics-ref argument')
parser.add_argument('--metrics-ref', required=True,
    help='Specify a list of metrics to report')
parser.add_argument('--verbose', required=False, dest='verbose',
    action='store_true', help='Provide verbose output')

def main():
    args = parser.parse_args()
    logLevel = logging.INFO
    if args.verbose:
        logLevel = logging.DEBUG
    logging.basicConfig(level=logLevel,
        format='%(levelname)s:%(asctime)s %(message)s',
        datefmt='%Y/%m/%d %H:%M:%S')
    logger = logging.getLogger('kwmetrics')
    kwmetrics = KwMetrics(logger, args.tables_dir, args.metrics_report, args.metrics_ref)
    try:
        kwmetrics.generate_report()
    except SystemExit as e:
        logger.error(e)
        sys.exit(1)


class KwMetrics:
    def __init__(self, logger, tables_dir, metrics_report, metrics_ref):
        logger.debug("Initialising KwMetrics class")
        self.logger = logger
        self.tables_dir = tables_dir
        self.metrics_report = metrics_report
        self.metrics_ref = metrics_ref.strip().split(',')
        self.metrics_ref_ids = [] # to store ids of wanted metrics
        self.has_func_metrics = False
        self.has_class_metrics = False

        # create regular expression pattern
        self.p_regexp_metric_refs = re.compile(KW_CONST.RE_MATCH_METRIC_REFS)

        # main "database" of information storing all FileMetrics which contains
        # FuncMetrics and ClassMetrics.
        self.file_metrics_db = dict()
        self.func_metrics_db = dict()
        self.class_metrics_db = dict()

        self.metric_kind_dict = dict()
        self.metric_id_to_ref_dict = dict()
        self.metric_ref_to_id_dict = dict()
        self.metric_dict = dict()
        self.file_dict = dict()
        self.entity_dict = dict()
        self.attribute_dict = dict()

        # create paths to files
        self.metric_dat = os.path.join(self.tables_dir, 'metric.dat')
        self.metric_kind_dat = os.path.join(self.tables_dir, 'metric_kind.dat')
        self.file_dat = os.path.join(self.tables_dir, 'file.dat')
        self.entity_dat = os.path.join(self.tables_dir, 'entity.dat')
        self.attribute_dat = os.path.join(self.tables_dir, 'attribute.dat')
        self.logger.debug("Initialisation of KwMetrics complete")

    def generate_report(self):
        self.logger.info("Starting metrics report generation")
        self.validate_metrics_dat_files()
        self.parse_metric_kinds_dat()
        self.get_metric_ids() # needs to be done before we parse the metrics
        self.parse_metric_dat()
        self.parse_file_dat()
        self.parse_entity_dat()
        self.parse_attribute_dat()

        self.process_metrics()

        self.write_to_csv()
        self.logger.info("Metrics report generation complete")

    def write_to_csv(self):
        self.logger.info("Writing to CSV file {0}".format(self.metrics_report))
        title = [KW_CONST.CSV_COLUMN_FILE]
        if self.func_metrics_db: title.append(KW_CONST.CSV_COLUMN_FUNCTION)
        if self.class_metrics_db: title.append(KW_CONST.CSV_COLUMN_CLASS)
        title += self.metrics_ref
        data = []
        self.logger.debug("Appending title {0}".format(title))
        data.append(title)
        for file_id, file_metric in self.file_metrics_db.iteritems():
            col = [file_metric.name]
            if self.func_metrics_db: col.append('')
            if self.class_metrics_db: col.append('')
            col += self.get_csv_metric_values(file_metric.metrics)
            self.logger.debug("Appending column {0}".format(col))
            data.append(col)
            func_metrics = [metrics for key, metrics \
                    in self.func_metrics_db.iteritems() if key.file_id==file_id]
            class_metrics = [metrics for key, metrics \
                    in self.class_metrics_db.iteritems() if key.file_id==file_id]
            for func_metric in func_metrics:
                col = [file_metric.name, func_metric.name]
                if self.class_metrics_db: col.append('')
                if self.class_metrics_db: col.append(KW_CONST.CSV_COLUMN_CLASS)
                col += self.get_csv_metric_values(func_metric.metrics)
                self.logger.debug("Appending column {0}".format(col))
                data.append(col)
            for class_metric in class_metrics:
                col = [file_metric.name, class_metric.name]
                if self.func_metrics_db: col.append('')
                if self.class_metrics_db: col.append(KW_CONST.CSV_COLUMN_CLASS)
                col += self.get_csv_metric_values(class_metric.metrics)
                self.logger.debug("Appending column {0}".format(col))
                data.append(col)

        self.logger.debug("Opening CSV file {0} for writing".format(self.metrics_report))
        # only compatible with v2.x
        with open(self.metrics_report, 'wb') as fp:
            a = csv.writer(fp, delimiter=';')
            self.logger.debug("Writing CSV data...")
            a.writerows(data)
        self.logger.info("CSV report successfully created")

    def get_csv_metric_values(self, metrics):
        metric_values = []
        for metric in self.metrics_ref:
            metric_values.append(metrics[metric])
        return metric_values

    # primary function for processing dictionaries containing metrics data from
    # .dat files.
    def process_metrics(self):
        self.logger.info("Started processing metrics")
        # metric_dat stores a list of metrics for each unique entity listed in
        # the metric.dat file
        for loc_id, loc_metrics_dict in self.metric_dict.iteritems():
            # find out what type it is, and which file it exists in
            if loc_id in self.attribute_dict:
                attr = self.attribute_dict[loc_id]
                # exclude system header metrics
                if 'header-location' in attr.attribute and 'system' in attr.value:
                    self.logger.debug("Skipping metric attribute {0} \
                        because it is flagged as a system include"
                        .format(str(attr)))
                    # ignore sys include and continue the loop
                    continue
            # else we have a file or func that we care about
            file_id = self.get_file_id_from_loc_id(loc_id)
            file_path = self.file_dict[file_id]
            metric_level_dict = dict()

            if file_id == loc_id:
                # file-level metric so get existing file_metric from the
                # dictionary db, or create one
                metric_level_dict = self.file_metrics_db.setdefault(
                    loc_id, EntityMetrics(name=file_path, metrics=dict())
                )
            else:
                name = self.entity_dict[loc_id].name
                key = FuncOrClassMetricKey(file_id=file_id, loc_id=loc_id)
                # the entity is a func/class
                if loc_id in self.attribute_dict:
                    self.logger.debug("Entity {0} flagged as a function-level \
                        metric".format(str(loc_id)))
                    metric_level_dict = self.func_metrics_db.setdefault(
                        key, EntityMetrics(name=name, metrics=dict()))
                else:
                    self.logger.debug("Entity {0} flagged as a class-level \
                        metric".format(str(loc_id)))
                    metric_level_dict = self.class_metrics_db.setdefault(
                        key, EntityMetrics(name=name, metrics=dict()))

            p_replace_metric_kinds = re.compile('|'.join(loc_metrics_dict.keys()))
            for metric_ref in self.metrics_ref:
                # replace all metric kinds with values
                result = self.p_regexp_metric_refs.sub(
                    lambda x: loc_metrics_dict[x.group()] \
                        if x.group() in loc_metrics_dict else '0',
                        metric_ref
                )
                metric_level_dict.metrics[metric_ref] = eval(result)
        self.logger.info("Processing metrics complete")

    # go through provided metric references and get the metric reference ids
    # used by Klocwork to reference metrics
    def get_metric_ids(self):
        # self.metrics_ref might contain mathematic sums, so extract needed
        # metrics from these
        for i in self.metrics_ref:
            for j in self.p_regexp_metric_refs.findall(i):
                # if not i in self.metric_kind_dict:
                #     sys.exit('Could not find metrics ref {0}'.format(i))
                # self.metrics_ref_ids.append(self.metric_kind_dict[i].id)
                if not j in self.metric_ref_to_id_dict:
                    sys.exit('Could not find metrics ref {0}'.format(j))
                # make sure we do not add metrics multiple times
                m_id = self.metric_ref_to_id_dict[j]
                if not m_id in self.metrics_ref_ids:
                    self.metrics_ref_ids.append(m_id)

    # given an entity/location id, get the file id for where it exists
    def get_file_id_from_loc_id(self, loc_id):
        return self.entity_dict[loc_id].file_name

    # below functions parse the numerous .dat files and populate the dictionaries
    # used to contain the metrics data. These dictionaries are later processed
    # to calculate & report the metric values per file/function/class
    def parse_metric_kinds_dat(self):
        with open(self.metric_kind_dat, 'r') as f:
            for line in [l.strip().split(';') for l in f]:
                # self.metric_kind_dict[line[KW_CONST.METRIC_KIND_DAT_REF]] = MetricKind(id=line[KW_CONST.METRIC_KIND_DAT_ID],
                # ref=line[KW_CONST.METRIC_KIND_DAT_REF], description=line[KW_CONST.METRIC_KIND_DAT_DESCRIPTION])
                self.metric_id_to_ref_dict[line[KW_CONST.METRIC_KIND_DAT_ID]] = \
                    line[KW_CONST.METRIC_KIND_DAT_REF]
                self.metric_ref_to_id_dict[line[KW_CONST.METRIC_KIND_DAT_REF]] = \
                    line[KW_CONST.METRIC_KIND_DAT_ID]

    def parse_metric_dat(self):
        with open(self.metric_dat, 'r') as f:
            for line in [l.strip().split(';') for l in f]:
                if line[KW_CONST.METRIC_DAT_ID] in self.metrics_ref_ids:
                    # metric_dict is keyed by entity/location id of metrics
                    loc_metrics_dict = self.metric_dict.setdefault(
                        line[KW_CONST.METRIC_DAT_LOC_ID], dict())

                    metric_kind = self.metric_id_to_ref_dict[line[KW_CONST.METRIC_DAT_ID]]
                    # store by metric_kind string, e.g. CYCLOMATIC
                    loc_metrics_dict[metric_kind] = line[KW_CONST.METRIC_DAT_VALUE]

    def parse_file_dat(self):
        with open(self.file_dat, 'r') as f:
            for line in [l.strip().split(';') for l in f]:
                self.file_dict[line[KW_CONST.FILE_DAT_LOC_ID]] = line[KW_CONST.FILE_DAT_PATH]

    def parse_entity_dat(self):
        with open(self.entity_dat, 'r') as f:
            for line in [l.strip().split(';') for l in f]:
                self.entity_dict[line[KW_CONST.ENTITY_DAT_LOC_ID]] = Entity(line[KW_CONST.ENTITY_DAT_LOC_ID],
                line[KW_CONST.ENTITY_DAT_NAME], line[KW_CONST.ENTITY_DAT_DEP_ID], line[KW_CONST.ENTITY_DAT_FILE])

    def parse_attribute_dat(self):
        with open(self.attribute_dat, 'r') as f:
            for line in [l.strip().split(';') for l in f]:
                attribute = self.attribute_dict.setdefault(
                    line[KW_CONST.ATTRIBUTE_DAT_LOC_ID],
                    Attribute(line[KW_CONST.ATTRIBUTE_DAT_LOC_ID], [], []))
                attribute.attribute.append(line[KW_CONST.ATTRIBUTE_DAT_ATTRIBUTE])
                attribute.value.append(line[KW_CONST.ATTRIBUTE_DAT_VALUE])


    def validate_metrics_dat_files(self):
        if not (os.path.exists(self.metric_dat) and
            os.path.exists(self.metric_kind_dat) and
            os.path.exists(self.file_dat) and
            os.path.exists(self.entity_dat) and
            os.path.exists(self.attribute_dat)):
            sys.exit("Could not find .dat files in {0}".format(self.tables_dir))

if __name__ == "__main__":
    main()
