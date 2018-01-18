#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Python motu client
#
# Motu, a high efficient, robust and Standard compliant Web Server for Geographic
#  Data Dissemination.
# 
#  http://cls-motu.sourceforge.net/
# 
#  (C) Copyright 2009-2010, by CLS (Collecte Localisation Satellites) -
#  http://www.cls.fr - and Contributors
# 
# 
#  This library is free software; you can redistribute it and/or modify it
#  under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation; either version 2.1 of the License, or
#  (at your option) any later version.
# 
#  This library is distributed in the hope that it will be useful, but
#  WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
#  or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
#  License for more details.
# 
#  You should have received a copy of the GNU Lesser General Public License
#  along with this library; if not, write to the Free Software Foundation,
#  Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

import argparse
import configparser
import traceback
import platform
import sys
import os
import datetime
import logging
import logging.config

# Import project libraries
from motu import utils_log
from motu import motu_api

# The necessary required version of Python interpreter
REQUIRED_VERSION = (3, 5)

# error code to use when exiting after exception catch
ERROR_CODE_EXIT = 1

# the config file to load from
CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
DEFAULT_CFG_FILE = os.path.join(CURRENT_PATH, "motu-client-python.ini")
DEFAULT_LOG_CFG_FILE = os.path.join(CURRENT_PATH, "log.ini")

# Section of the config file to use
SECTION = "Main"


def get_client_version():
    """Return the version (as a string) of this client.
    
    The value is automatically set by the maven processing build, so don't 
    touch it unless you know what you are doing."""
    return motu_api.get_client_version()


def get_client_artefact():
    """Return the artifact identifier (as a string) of this client.
    
    The value is automatically set by the maven processing build, so don't 
    touch it unless you know what you are doing."""
    return motu_api.get_client_artefact()


def load_options(config_file, argv):
    # create option parser
    parser = argparse.ArgumentParser()

    # add available options
    parser.add_argument('--quiet', '-q',
                        help="prevent any output in stdout",
                        action='store_const',
                        const=logging.WARN,
                        dest='log_level')

    parser.add_argument('--verbose',
                        help="print information in stdout",
                        action='store_const',
                        const=logging.DEBUG,
                        dest='log_level')

    parser.add_argument('--noisy',
                        help="print more information (traces) in stdout",
                        action='store_const',
                        const=utils_log.TRACE_LEVEL,
                        dest='log_level')

    parser.add_argument('--user', '-u', type=str,
                        help="the user name (string)")

    parser.add_argument('--pwd', '-p', type=str,
                        help="the user password (string)")

    parser.add_argument('--auth-mode', type=str,
                        default=motu_api.AUTHENTICATION_MODE_CAS,
                        help="the authentication mode: '" + motu_api.AUTHENTICATION_MODE_NONE +
                             "' (for no authentication),'" + motu_api.AUTHENTICATION_MODE_BASIC +
                             "' (for basic authentication), or'" + motu_api.AUTHENTICATION_MODE_CAS +
                             "' (for Central Authentication Service) [default: %default]")

    parser.add_argument('--proxy-server', type=str,
                        help="the proxy server (url)")

    parser.add_argument('--proxy-user', type=str,
                        help="the proxy user (string)")

    parser.add_argument('--proxy-pwd', type=str,
                        help="the proxy password (string)")

    parser.add_argument('--motu', '-m', type=str,
                        help="the motu server to use (url)")

    parser.add_argument('--service-id', '-s', type=str,
                        help="The service identifier (string)")

    parser.add_argument('--product-id', '-d', type=str,
                        help="The product (data set) to download (string)")

    parser.add_argument('--date-min', '-t', type=str,
                        help="The min date with optional hour resolution "
                             "(string following format YYYY-MM-DD [HH:MM:SS])")

    parser.add_argument('--date-max', '-T', type=str,
                        help="The max date with optional hour resolution "
                             "(string following format YYYY-MM-DD [HH:MM:SS])")

    parser.add_argument('--latitude-min', '-y', type=float,
                        help="The min latitude (float in the interval [-90 ; 90])")

    parser.add_argument('--latitude-max', '-Y', type=float,
                        help="The max latitude (float in the interval [-90 ; 90])")

    parser.add_argument('--longitude-min', '-x', type=float,
                        help="The min longitude (float in the interval [-180 ; 180])")

    parser.add_argument('--longitude-max', '-X', type=float,
                        help="The max longitude (float in the interval [-180 ; 180])")

    parser.add_argument('--depth-min', '-z', type=str,
                        help="The min depth (float in the interval [0 ; 2e31] or string'Surface')")

    parser.add_argument('--depth-max', '-Z', type=str,
                        help="The max depth (float in the interval [0 ; 2e31] or string 'Surface')")

    parser.add_argument('--variables', '-v',
                        help="The variables (list of strings)",
                        dest="variable",
                        nargs="*",
                        type=str)

    parser.add_argument('--sync-mode', '-S',
                        help="Sets the download mode to synchronous (not recommended)",
                        action='store_true',
                        dest='sync')

    parser.add_argument('--describe-product', '-D',
                        help="Get all updated information on a dataset. Output is in XML format",
                        action='store_true',
                        dest='describe')

    parser.add_argument('--size',
                        help="Get the size of an extraction. Output is in XML format",
                        action='store_true',
                        dest='size')

    parser.add_argument('--out-dir', '-o', type=str,
                        help="The output dir where result (download file) is written (string). "
                             "If it starts with 'console', behaviour is the same as with --console-mode. ",
                        default=".")

    parser.add_argument('--out-name', '-f', type=str,
                        help="The output file name (string)",
                        default="data_{}.nc".format(datetime.date.today().isoformat()))

    parser.add_argument('--block-size', type=int,
                        help="The block used to download file (integer expressing bytes)",
                        default="65536")

    parser.add_argument('--socket-timeout', type=float,
                        help="Set a timeout on blocking socket operations (float expressing seconds)")
    parser.add_argument('--user-agent', type=str,
                        help="Set the identification string (user-agent) for HTTP requests. "
                             "By default this value is 'Python-urllib/x.x' "
                             "(where x.x is the version of the python interpreter)")

    parser.add_argument('--outputWritten', type=str,
                        help="Optional parameter used to set the format of the file "
                             "returned by the download request: netcdf or netcdf4. "
                             "If not set, netcdf is used.")

    parser.add_argument('--console-mode',
                        help="Optional parameter used to display result on stdout, "
                             "either URL path to download extraction file, or the XML "
                             "content of getSize or describeProduct requests.",
                        action='store_true',
                        dest='console_mode')

    # set default values by picking from the configuration file
    default_values = {}
    config = configparser.ConfigParser()
    config.read([config_file])
    default_values.update(dict(config.items(SECTION)))
    if default_values.get("variable"):
        default_values["variable"] = [v.strip() for v in default_values["variable"].split(",")]
    parser.set_defaults(**default_values)

    options = parser.parse_args(argv)
    if options.date_min is None and options.date_max is None:
        options.date_min = datetime.date.today().isoformat()
        options.date_max = (datetime.date.today() + datetime.timedelta(days=9)).isoformat()
    return options


def check_version():
    """Utility function that checks the required version of the python interpreter
    is available. Raise an exception if not."""

    global REQUIRED_VERSION
    cur_version = sys.version_info
    if (cur_version[0] > REQUIRED_VERSION[0] or
            cur_version[0] == REQUIRED_VERSION[0] and
            cur_version[1] >= REQUIRED_VERSION[1]):
        return
    else:
        raise Exception("This tool uses python 2.7 or greater. You version is %s. " % str(cur_version))


# ===============================================================================
# The Main function
# ===============================================================================

if __name__ == '__main__':
    check_version()
    start_time = datetime.datetime.now()

    # create config parser
    conf_parser = argparse.ArgumentParser(
        description=__doc__,  # printed with -h/--help
        # Don't mess with format of description
        formatter_class=argparse.RawDescriptionHelpFormatter,
        # Turn off help, so we print all options in response to -h
        add_help=False
    )
    conf_parser.add_argument("-cfg", "--config-file",
                             help="Specify config file",
                             default=DEFAULT_CFG_FILE,
                             metavar="config_file")
    conf_parser.add_argument("-log_cfg", "--log-config-file",
                             help="Specify logging config file",
                             default=DEFAULT_LOG_CFG_FILE,
                             metavar="log_config_file")
    config_args, remaining_argv = conf_parser.parse_known_args()

    # first initialize the logger
    logging.addLevelName(utils_log.TRACE_LEVEL, 'TRACE')
    logging.config.fileConfig(os.path.join(os.path.dirname(__file__), config_args.log_config_file))
    log = logging.getLogger("motu-client-python")

    logging.getLogger().setLevel(logging.INFO)
    try:
        # we prepare options we want
        _options = load_options(config_args.config_file, remaining_argv)

        if _options.log_level is not None:
            logging.getLogger().setLevel(int(_options.log_level))

        motu_api.execute_request(_options)
    except Exception as e:
        print(e)
        log.error("Execution failed: %s", e)
        if hasattr(e, 'reason'):
            log.info(' . reason: %s', e.reason)
        if hasattr(e, 'code'):
            log.info(' . code  %s: ', e.code)
        if hasattr(e, 'read'):
            log.log(utils_log.TRACE_LEVEL, ' . detail:\n%s', e.read())

        log.debug('-' * 60)
        log.debug("Stack trace exception is detailed herafter:")
        exc_type, exc_value, exc_tb = sys.exc_info()
        x = traceback.format_exception(exc_type, exc_value, exc_tb)
        for stack in x:
            log.debug(' . %s', stack.replace('\n', ''))
        log.debug('-' * 60)
        log.log(utils_log.TRACE_LEVEL, 'System info is provided hereafter:')
        system, node, release, version, machine, processor = platform.uname()
        log.log(utils_log.TRACE_LEVEL, ' . system   : %s', system)
        log.log(utils_log.TRACE_LEVEL, ' . node     : %s', node)
        log.log(utils_log.TRACE_LEVEL, ' . release  : %s', release)
        log.log(utils_log.TRACE_LEVEL, ' . version  : %s', version)
        log.log(utils_log.TRACE_LEVEL, ' . machine  : %s', machine)
        log.log(utils_log.TRACE_LEVEL, ' . processor: %s', processor)
        log.log(utils_log.TRACE_LEVEL, ' . python   : %s', sys.version)
        log.log(utils_log.TRACE_LEVEL, ' . client   : %s', get_client_version())
        log.log(utils_log.TRACE_LEVEL, '-' * 60)

        sys.exit(ERROR_CODE_EXIT)

    finally:
        log.debug("Elapsed time : %s", str(datetime.datetime.now() - start_time))
