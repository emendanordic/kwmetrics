# **************************************************************************************************
#  Emenda Nordic AB.
#
# Disclaimer: Please note that this software or software component is released by Emenda Nordic AB
# on a non-proprietary basis for commercial or non-commercial use with no warranty. Emenda Nordic AB
# will not be liable for any damage or loss caused by the use of this software. Redistribution is
# only allowed with prior consent.
#
# **************************************************************************************************

import argparse, csv, logging, os, sys
from collections import namedtuple

import kwconstants as KWLP_CONST

# namedtuples used to store entries from the Klocwork .dat files
MetricId = namedtuple("MetricId", "loc_id metric_id")
Entity = namedtuple("Entity", "id name dep_id file_name")
MetricKind = namedtuple("MetricKind", "id ref description")
Metric = namedtuple("Metric", "id metric_id value")
File = namedtuple("File", "id path")
Attribute = namedtuple("Attribute", "id attribute value")

# used to store mapped .dat data
FileMetrics = namedtuple("FileMetrics", "file_path funcs classes metrics")
FuncMetrics = namedtuple("FuncMetrics", "name metrics")
ClassMetrics = namedtuple("ClassMetrics", "name metrics")

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

        # main "database" of information storing all FileMetrics which contains
        # FuncMetrics and ClassMetrics.
        self.file_metrics_db = dict()

        self.metric_kind_dict = dict()
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
        title = [KWLP_CONST.CSV_COLUMN_FILE]
        if self.has_func_metrics: title.append(KWLP_CONST.CSV_COLUMN_FUNCTION)
        if self.has_class_metrics: title.append(KWLP_CONST.CSV_COLUMN_CLASS)
        title += self.metrics_ref
        data = []
        self.logger.debug("Appending title {0}".format(title))
        data.append(title)
        for file_metric in self.file_metrics_db.values():
            col = [file_metric.file_path]
            if self.has_func_metrics: col.append("")
            if self.has_class_metrics: col.append("")

            col += self.get_csv_metric_values(file_metric.metrics)

            self.logger.debug("Appending column {0}".format(col))
            data.append(col)
            for func_metric in file_metric.funcs.values():
                col = [file_metric.file_path, func_metric.name]
                if self.has_class_metrics: col.append("")
                col += self.get_csv_metric_values(func_metric.metrics)
                self.logger.debug("Appending column {0}".format(col))
                data.append(col)

            for class_metric in file_metric.classes.values():
                col = [file_metric.file_path]
                if self.has_func_metrics: col.append("")
                col.append(class_metric.name)
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
        metric_values = [""] * len(self.metrics_ref)
        for metric in metrics:
            index = self.metrics_ref_ids.index(metric.metric_id)
            metric_values[index] = metric.value
        return metric_values

    # primary function for processing dictionaries containing metrics data from
    # .dat files.
    def process_metrics(self):
        self.logger.debug("Started process metrics .dat files")
        # metric_dat stores a list of metrics for each unique entity listed in
        # the metric.dat file
        for metrics in self.metric_dict.values():
            # for each entity/location id
            for metric in metrics:
                # for each metric reported for that entity/location id...
                # find out what type it is, and which file it exists in
                if metric.id in self.attribute_dict:
                    attr = self.attribute_dict[metric.id]
                    # exclude system header metrics
                    if 'header-location' in attr.attribute and 'system' in attr.value:
                        self.logger.debug("Skipping metric attribute {0} \
                            because it is flagged as a system include"
                            .format(str(attr)))
                        # ignore sys include and continue the loop
                        continue
                # else we have a file or func that we care about
                file_id = self.get_file_id_from_loc_id(metric.id)
                file_path = self.file_dict[file_id]
                # get existing file_metric from the dictionary db, or create
                # one
                file_metric = self.file_metrics_db.setdefault(
                    file_id, FileMetrics(file_path=file_path, funcs=dict(),
                    classes=dict(), metrics=[])
                )
                # if the metric entity/location id is the same as the the id
                # for the file it exists in, then it is the file...
                if file_id == metric.id:
                    self.logger.debug("Metric {0} flagged as a file-level \
                        metric".format(str(metric)))
                    # append the mertic for the file
                    file_metric.metrics.append(metric)
                else:
                    name = self.entity_dict[metric.id].name
                    # the entity is a func/class
                    if metric.id in self.attribute_dict:
                        self.logger.debug("Metric {0} flagged as a function-level \
                            metric".format(str(metric)))
                        self.has_func_metrics = True
                        file_metric.funcs.setdefault(
                            metric.id, FuncMetrics(name=name, metrics=[])
                        ).metrics.append(metric)
                    else:
                        self.logger.debug("Metric {0} flagged as a class-level \
                            metric".format(str(metric)))
                        self.has_class_metrics = True
                        file_metric.classes.setdefault(
                            metric.id, ClassMetrics(name=name, metrics=[])
                        ).metrics.append(metric)
        self.logger.debug("Metrics processing complete")

    # go through provided metric references and get the metric reference ids
    # used by Klocwork to reference metrics
    def get_metric_ids(self):
        for i in self.metrics_ref:
            if not i in self.metric_kind_dict:
                sys.exit('Could not find metrics ref {0}'.format(i))
            self.metrics_ref_ids.append(self.metric_kind_dict[i].id)

    # given an entity/location id, get the file id for where it exists
    def get_file_id_from_loc_id(self, loc_id):
        return self.entity_dict[loc_id].file_name

    # below functions parse the numerous .dat files and populate the dictionaries
    # used to contain the metrics data. These dictionaries are later processed
    # to calculate & report the metric values per file/function/class
    def parse_metric_kinds_dat(self):
        with open(self.metric_kind_dat, 'r') as f:
            for line in [l.strip().split(';') for l in f]:
                self.metric_kind_dict[line[KWLP_CONST.METRIC_KIND_DAT_REF]] = MetricKind(id=line[KWLP_CONST.METRIC_KIND_DAT_ID],
                ref=line[KWLP_CONST.METRIC_KIND_DAT_REF], description=line[KWLP_CONST.METRIC_KIND_DAT_DESCRIPTION])

    def parse_metric_dat(self):
        with open(self.metric_dat, 'r') as f:
            for line in [l.strip().split(';') for l in f]:
                if line[KWLP_CONST.METRIC_DAT_ID] in self.metrics_ref_ids:
                    self.metric_dict.setdefault(
                        line[KWLP_CONST.METRIC_DAT_ID], []).append(
                            Metric(id=line[KWLP_CONST.METRIC_DAT_LOC_ID] , metric_id=line[KWLP_CONST.METRIC_DAT_ID],
                            value=line[KWLP_CONST.METRIC_DAT_VALUE]))

    def parse_file_dat(self):
        with open(self.file_dat, 'r') as f:
            for line in [l.strip().split(';') for l in f]:
                self.file_dict[line[KWLP_CONST.FILE_DAT_LOC_ID]] = line[KWLP_CONST.FILE_DAT_PATH]

    def parse_entity_dat(self):
        with open(self.entity_dat, 'r') as f:
            for line in [l.strip().split(';') for l in f]:
                self.entity_dict[line[KWLP_CONST.ENTITY_DAT_LOC_ID]] = Entity(line[KWLP_CONST.ENTITY_DAT_LOC_ID],
                line[KWLP_CONST.ENTITY_DAT_NAME], line[KWLP_CONST.ENTITY_DAT_DEP_ID], line[KWLP_CONST.ENTITY_DAT_FILE])

    def parse_attribute_dat(self):
        with open(self.attribute_dat, 'r') as f:
            for line in [l.strip().split(';') for l in f]:
                attribute = self.attribute_dict.setdefault(
                    line[KWLP_CONST.ATTRIBUTE_DAT_LOC_ID],
                    Attribute(line[KWLP_CONST.ATTRIBUTE_DAT_LOC_ID], [], []))
                attribute.attribute.append(line[KWLP_CONST.ATTRIBUTE_DAT_ATTRIBUTE])
                attribute.value.append(line[KWLP_CONST.ATTRIBUTE_DAT_VALUE])


    def validate_metrics_dat_files(self):
        if not (os.path.exists(self.metric_dat) and
            os.path.exists(self.metric_kind_dat) and
            os.path.exists(self.file_dat) and
            os.path.exists(self.entity_dat) and
            os.path.exists(self.attribute_dat)):
            sys.exit("Could not find .dat files in {0}".format(self.tables_dir))

if __name__ == "__main__":
    main()
