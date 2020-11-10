from motu_utils.motu_api import execute_request
import optparse
from configparser import ConfigParser
import os
import logging
import datetime

CFG_FILE = '~/motuclient/motuclient-python.ini'
LOG_CFG_FILE = './motu_utils/cfg/log.ini'

SECTION = 'Main'

SERVICE = "BLKSEA_ANALYSIS_FORECAST_PHYS_007_001-TDS"
PRODUCTS_FORMAT = "sv03-bs-cmcc-{variable}-an-fc-{flag}"
VARIABLES = ("cur", "mld", "sal", "ssh", "tem")


def load_options():
    """load options to handle"""

    _options = None

    # create option parser
    parser = optparse.OptionParser(version="0.0" + ' v' + "1")

    # create config parser
    conf_parser = ConfigParser()
    conf_parser.read(os.path.expanduser(CFG_FILE))

    # add available options
    parser.add_option('--quiet', '-q',
                      help="prevent any output in stdout",
                      action='store_const',
                      const=logging.WARN,
                      dest='log_level')

    parser.add_option('--verbose',
                       help="print information in stdout",
                       action='store_const',
                       const=logging.DEBUG,
                       dest='log_level')

    parser.add_option( '--date-min', '-t',
                       help = "The min date with optional hour resolution (string following format YYYY-MM-DD [HH:MM:SS])")

    parser.add_option( '--date-max', '-T',
                       help = "The max date with optional hour resolution (string following format YYYY-MM-DD [HH:MM:SS])",
                       default = datetime.date.today().isoformat())

    parser.add_option( '--latitude-min', '-y',
                       type = 'float',
                       help = "The min latitude (float in the interval [-90 ; 90])")

    parser.add_option( '--latitude-max', '-Y',
                       type = 'float',
                       help = "The max latitude (float in the interval [-90 ; 90])")

    parser.add_option( '--longitude-min', '-x',
                       type = 'float',
                       help = "The min longitude (float in the interval [-180 ; 180])")

    parser.add_option( '--longitude-max', '-X',
                       type = 'float',
                       help = "The max longitude (float in the interval [-180 ; 180])")

    parser.add_option( '--depth-min', '-z',
                       type = 'string',
                       help = "The min depth (float in the interval [0 ; 2e31] or string 'Surface')")

    parser.add_option( '--depth-max', '-Z',
                       type = 'string',
                       help = "The max depth (float in the interval [0 ; 2e31] or string 'Surface')")

    parser.add_option( '--sync-mode', '-S',
                       help = "Sets the download mode to synchronous (not recommended)",
                       action='store_true',
                       dest='sync')

    parser.add_option( '--describe-product', '-D',
                       help = "Get all updated information on a dataset. Output is in XML format",
                       action='store_true',
                       dest='describe')

    parser.add_option( '--size',
                       help = "Get the size of an extraction. Output is in XML format",
                       action='store_true',
                       dest='size')

    parser.add_option( '--out-dir', '-o',
                       help = "The output dir where result (download file) is written (string). If it starts with 'console', behaviour is the same as with --console-mode. ",
                       default=".")

    parser.add_option( '--out-name', '-f',
                       help = "The output file name (string)",
                       default="data.nc")

    parser.add_option( '--block-size',
                       type = 'int',
                       help = "The block used to download file (integer expressing bytes)",
                       default="65536")

    parser.add_option( '--socket-timeout',
                       type = 'float',
                       help = "Set a timeout on blocking socket operations (float expressing seconds)")
    parser.add_option( '--user-agent',
                       help = "Set the identification string (user-agent) for HTTP requests. By default this value is 'Python-urllib/x.x' (where x.x is the version of the python interpreter)")

    parser.add_option( '--outputWritten',
                       help = "Optional parameter used to set the format of the file returned by the download request: netcdf or netcdf4. If not set, netcdf is used.")

    parser.add_option( '--console-mode',
                       help = "Optional parameter used to display result on stdout, either URL path to download extraction file, or the XML content of getSize or describeProduct requests.",
                       action='store_true',
                       dest='console_mode')


    # set default values by picking from the configuration file
    default_values = {}
    default_variables = []
    for option in parser.option_list:
        if (option.dest != None) and conf_parser.has_option(SECTION, option.dest):
            if option.dest == "variable":
                variablesInCfgFile = conf_parser.get(SECTION, option.dest)
                if (not variablesInCfgFile is None) and variablesInCfgFile.strip():
                    allVariablesArray = variablesInCfgFile.split(",")
                    default_variables = default_variables + allVariablesArray
                    default_values[option.dest] = default_variables
            else:
                default_values[option.dest] = conf_parser.get(SECTION, option.dest)
    
    parser.set_defaults( **default_values )

    return parser.parse_args()


def main(daily=True):
    flag = "d" if daily else "h"
    options, _ = load_options()
    execute_request(options)

    for variable in VARIABLES:
        product_id = PRODUCTS_FORMAT.format(variable=variable, flag=flag)


if __name__ == '__main__':
    main()
