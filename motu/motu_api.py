#! /usr/bin/env python
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

# import urlparse # WARNING : The urlparse module is renamed to urllib.parse
from urllib.parse import urlparse, quote_plus
from io import StringIO
import os
import re
import datetime
import time
import socket
from math import ceil
from xml.dom import minidom

# Import project libraries
from . import utils_log
from . import utils_unit
from . import utils_stream
from . import utils_http
from . import utils_messages
from . import utils_cas
from . import utils_collection
from . import stop_watch
import logging

# constant for authentication modes
AUTHENTICATION_MODE_NONE = 'none'
AUTHENTICATION_MODE_BASIC = 'basic'
AUTHENTICATION_MODE_CAS = 'cas'

# constant for date time string format
DATETIME_FORMAT = "%Y-%m-%d% %H:%M:%S"


def get_client_version():
    """Return the version (as a string) of this client.
    
    The value is automatically set by the maven processing build, so don't 
    touch it unless you know what you are doing."""
    return '1.4.0-01.12.2017'


def get_client_artefact():
    """Return the artifact identifier (as a string) of this client.
    
    The value is automatically set by the maven processing build, so don't 
    touch it unless you know what you are doing."""
    return 'motu-client-python'


def build_params(_options):
    """Function that builds the query string for Motu according to the given options"""
    # temporal = ''
    # geographic = ''
    # vertical = ''
    # other_opt = ''
    log = logging.getLogger("motu_api")
    """
    Build the main url to connect to
    """
    query_options = utils_collection.ListMultimap()

    # describeProduct in XML format (sync) / productDownload (sync/async)
    if _options.describe:
        query_options.insert(action='describeProduct',
                             service=_options.service_id,
                             product=_options.product_id
                             )
    elif _options.size:
        query_options.insert(action='getSize',
                             service=_options.service_id,
                             product=_options.product_id
                             )
    else:
        # synchronous/asynchronous mode
        if _options.sync:
            log.info('Synchronous mode set')
            query_options.insert(action='productdownload',
                                 scriptVersion=quote_plus(get_client_version()),
                                 mode='console',
                                 service=_options.service_id,
                                 product=_options.product_id
                                 )
        else:
            log.info('Asynchronous mode set')
            query_options.insert(action='productdownload',
                                 scriptVersion=quote_plus(get_client_version()),
                                 mode='status',
                                 service=_options.service_id,
                                 product=_options.product_id
                                 )

    # geographical parameters
    if _options.extraction_geographic:
        query_options.insert(x_lo=_options.longitude_min,
                             x_hi=_options.longitude_max,
                             y_lo=_options.latitude_min,
                             y_hi=_options.latitude_max
                             )

    if _options.extraction_vertical:
        query_options.insert(z_lo=_options.depth_min,
                             z_hi=_options.depth_max
                             )

    if _options.extraction_output:
        query_options.insert(output=_options.outputWritten)
    else:
        query_options.insert(output="netcdf")

    if _options.extraction_temporal:
        # date are strings, and they are send to Motu "as is". If not, we convert them into string
        if _options.date_min is not None or _options.date_min is not None:
            date_min = _options.date_min
            if not isinstance(date_min, str):
                date_min = date_min.strftime(DATETIME_FORMAT)
            query_options.insert(t_lo=date_min)

        if _options.date_max is not None or _options.date_max is not None:
            date_max = _options.date_max
            if not isinstance(date_max, str):
                date_max = date_max.strftime(DATETIME_FORMAT)
            query_options.insert(t_hi=date_max)

    variable = _options.variable
    if variable is not None:
        for i, opt in enumerate(variable):
            query_options.insert(variable=opt)

    if _options.console_mode or _options.out_dir.startswith("console"):
        query_options.insert(mode="console")

    return utils_http.encode(query_options)


def check_options(_options):
    """function that checks the given options for coherency."""

    # Check Mandatory Options
    if (_options.auth_mode != AUTHENTICATION_MODE_NONE and
            _options.auth_mode != AUTHENTICATION_MODE_BASIC and
            _options.auth_mode != AUTHENTICATION_MODE_CAS):
        raise Exception(utils_messages.get_external_messages()['motu-client.exception.option.invalid'] % (
            _options.auth_mode, 'auth-mode',
            [AUTHENTICATION_MODE_NONE, AUTHENTICATION_MODE_BASIC, AUTHENTICATION_MODE_CAS]))

    # if authentication mode is set we check both user & password presence
    if (_options.user is None and
            _options.auth_mode != AUTHENTICATION_MODE_NONE):
        raise Exception(utils_messages.get_external_messages()['motu-client.exception.option.mandatory.user'] % (
            'user', _options.auth_mode))

    # check that if a user is set, a password should be set also
    if (_options.pwd is None and
            _options.user is not None):
        raise Exception(utils_messages.get_external_messages()['motu-client.exception.option.mandatory.password'] % (
            'pwd', _options.user))

        # check that if a user is set, an authentication mode should also be set
    if (_options.user is not None and
            _options.auth_mode == AUTHENTICATION_MODE_NONE):
        raise Exception(utils_messages.get_external_messages()['motu-client.exception.option.mandatory.mode'] % (
            AUTHENTICATION_MODE_NONE, 'auth-mode', _options.user))

    # those following parameters are required
    if _options.motu is None:
        raise Exception(utils_messages.get_external_messages()['motu-client.exception.option.mandatory'] % 'motu')

    if _options.service_id is None:
        raise Exception(utils_messages.get_external_messages()['motu-client.exception.option.mandatory'] % 'service-id')

    if _options.product_id is None:
        raise Exception(utils_messages.get_external_messages()['motu-client.exception.option.mandatory'] % 'product-id')

    if _options.out_dir is None:
        raise Exception(utils_messages.get_external_messages()['motu-client.exception.option.mandatory'] % 'out-dir')

    out_dir = _options.out_dir
    if not out_dir.startswith("console"):
        # check directory existence
        if not os.path.exists(out_dir):
            raise Exception(
                utils_messages.get_external_messages()['motu-client.exception.option.outdir-notexist'] % out_dir)
        # check whether directory is writable or not
        if not os.access(out_dir, os.W_OK):
            raise Exception(
                utils_messages.get_external_messages()['motu-client.exception.option.outdir-notwritable'] % out_dir)

        if _options.out_name is None:
            raise Exception(
                utils_messages.get_external_messages()['motu-client.exception.option.mandatory'] % 'out-name')

    # Check PROXY Options
    _options.proxy = False
    if (_options.proxy_server is not None) and (len(_options.proxy_server) != 0):
        _options.proxy = True
        # check that proxy server is a valid url
        url = _options.proxy_server
        p = re.compile('^(ftp|http|https):\/\/(\w+:{0,1}\w*@)?(\S+)(:[0-9]+)?(\/|\/([\w#!:.?+=&%@!\-\/]))?')
        m = p.match(url)

        if not m:
            raise Exception(
                utils_messages.get_external_messages()['motu-client.exception.option.not-url'] % ('proxy-server', url))
        # check that if proxy-user is defined then proxy-pwd shall be also, and reciprocally.
        if (_options.proxy_user is not None) != (_options.proxy_pwd is not None):
            raise Exception(utils_messages.get_external_messages()['motu-client.exception.option.linked'] % (
                'proxy-user', 'proxy-name'))

    # Check VERTICAL Options
    _options.extraction_vertical = False
    if _options.depth_min is not None or _options.depth_max is not None:
        _options.extraction_vertical = True

    # Check TEMPORAL  Options
    _options.extraction_temporal = False
    if _options.date_min is not None or _options.date_max is not None:
        _options.extraction_temporal = True

    # Check OUTPUT Options
    _options.extraction_output = False
    if _options.outputWritten is not None:
        _options.extraction_output = True

    # Check GEOGRAPHIC Options
    _options.extraction_geographic = False
    if _options.latitude_min is not None or _options.latitude_max is not None or _options.longitude_min is not None or\
            _options.longitude_max is not None:
        _options.extraction_geographic = True
        if _options.latitude_min is None:
            raise Exception(
                utils_messages.get_external_messages()['motu-client.exception.option.geographic-box'] % 'latitude_min')

        if _options.latitude_max is None:
            raise Exception(
                utils_messages.get_external_messages()['motu-client.exception.option.geographic-box'] % 'latitude_max')

        if _options.longitude_min is None:
            raise Exception(
                utils_messages.get_external_messages()['motu-client.exception.option.geographic-box'] % 'longitude_min')

        if _options.longitude_max is None:
            raise Exception(
                utils_messages.get_external_messages()['motu-client.exception.option.geographic-box'] % 'longitude_max')

        temp_value = float(_options.latitude_min)
        if temp_value < -90 or temp_value > 90:
            raise Exception(utils_messages.get_external_messages()['motu-client.exception.option.out-of-range'] % (
                'latitude_min', str(temp_value)))
        temp_value = float(_options.latitude_max)
        if temp_value < -90 or temp_value > 90:
            raise Exception(utils_messages.get_external_messages()['motu-client.exception.option.out-of-range'] % (
                'latitude_max', str(temp_value)))
        temp_value = float(_options.longitude_min)
        temp_value = normalize_longitude(temp_value)
        if temp_value < -180 or temp_value > 180:
            raise Exception(utils_messages.get_external_messages()['motu-client.exception.option.out-of-range'] % (
                'logitude_min', str(temp_value)))
        temp_value = float(_options.longitude_max)
        temp_value = normalize_longitude(temp_value)
        if temp_value < -180 or temp_value > 180:
            raise Exception(utils_messages.get_external_messages()['motu-client.exception.option.out-of-range'] % (
                'longitude_max', str(temp_value)))


def normalize_longitude(lon):
    if lon > 180:
        while lon > 180:
            lon -= 360
    elif lon < -180:
        while lon < -180:
            lon += 360
    return lon


def total_seconds(td):
    return total_milliseconds(td) / 10 ** 3


def total_milliseconds(td):
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10 ** 6) / 10 ** 3


def get_url_config(_options, data=None):
    # prepare arguments    
    kargs = {}
    # proxy
    if _options.proxy:
        # proxyUrl = _options.proxy_server.partition(':')
        proxy_url = urlparse(_options.proxy_server)
        kargs['proxy'] = {"scheme": proxy_url.scheme,
                          "netloc": proxy_url.netloc}
        if _options.proxy_user is not None:
            kargs['proxy']['user'] = _options.proxy_user
            kargs['proxy']['password'] = _options.proxy_pwd
    # authentication
    if _options.auth_mode == AUTHENTICATION_MODE_BASIC:
        kargs['authentication'] = {'mode': 'basic',
                                   'user': _options.user,
                                   'password': _options.pwd}
    # headers
    kargs['headers'] = {"X-Client-Id": get_client_artefact(),
                        "X-Client-Version": quote_plus(get_client_version())}
    # data
    if data is not None:
        kargs['data'] = data

    return kargs


def get_request_url(dl_url, server, **options):
    """ Get the request url."""
    log = logging.getLogger("motu_api")
    stop_wa = stop_watch.local_thread_stop_watch()
    start_time = datetime.datetime.now()
    stop_wa.start('get_request')
    log.info("Requesting file to download (this can take a while)...")

    # Get request id        
    m = utils_http.open_url(dl_url, **options)
    response_str = m.read()
    dom = minidom.parseString(response_str)
    node = dom.getElementsByTagName('statusModeResponse')[0]
    status = node.getAttribute('status')
    if status == "2":
        msg = node.getAttribute('msg')
        log.error(msg)
        get_req_url = None
    else:
        request_id = node.getAttribute('requestId')
        # Get request url
        get_req_url = server + '?action=getreqstatus&requestid=' + request_id

    stop_wa.stop('get_request')

    return get_req_url


def wait_till_finished(reqUrlCAS, **options):
    stop_wa = stop_watch.local_thread_stop_watch()
    start_time = datetime.datetime.now()


def dl_2_file(dl_url, fh, block_size=65535, isADownloadRequest=None, **options):
    """ Download the file with the main url (of Motu) file.
     
    Motu can return an error message in the response stream without setting an
    appropriate http error code. So, in that case, the content-type response is
    checked, and if it is text/plain, we consider this as an error.
    
    dl_url: the complete download url of Motu
    fh: file handler to use to write the downstream"""
    log = logging.getLogger("motu_api")
    stop_wa = stop_watch.local_thread_stop_watch()
    start_time = datetime.datetime.now()
    log.info("Downloading file (this can take a while)...")

    # download file
    temp = None
    if not fh.startswith("console"):
        temp = open(fh, 'w+b')

    try:
        stop_wa.start('processing')

        m = utils_http.open_url(dl_url, **options)
        try:
            # check the real url (after potential redirection) is not a CAS Url scheme
            match = re.search(utils_cas.CAS_URL_PATTERN, m.url)
            if match is not None:
                service, _, _ = dl_url.partition('?')
                redirection, _, _ = m.url.partition('?')
                raise Exception(
                    utils_messages.get_external_messages()['motu-client.exception.authentication.redirected'] % (
                        service, redirection))

            # check that content type is not text/plain
            headers = m.info()
            if "Content-Type" in headers:
                if len(headers['Content-Type']) > 0:
                    if isADownloadRequest:
                        if headers['Content-Type'].startswith('text') or headers['Content-Type'].find('html') != -1:
                            raise Exception(
                                utils_messages.get_external_messages()['motu-client.exception.motu.error'] % m.read())

            log.info('File type: %s' % headers['Content-Type'])
            # check if a content length (size of the file) has been send
            size = -1
            if "Content-Length" in headers:
                try:
                    # it should be an integer
                    size = int(headers["Content-Length"])
                    log.info('File size: %s (%i B)' % (utils_unit.convert_bytes(size), size))
                except Exception as e:
                    size = -1
                    log.warn('File size is not an integer: %s' % headers["Content-Length"])
            elif temp is not None:
                log.warn('File size: %s' % 'unknown')

            processing_time = datetime.datetime.now()
            stop_wa.stop('processing')
            stop_wa.start('downloading')

            # performs the download           
            log.info('Downloading file %s' % os.path.abspath(fh))

            def progress_function(size_read):
                percent = size_read * 100. / size
                log.info("- %s (%.1f%%)", utils_unit.convert_bytes(size).rjust(8), percent)
                td = datetime.datetime.now() - start_time

            def none_function(size_read):
                percent = 100
                log.info("- %s (%.1f%%)", utils_unit.convert_bytes(size).rjust(8), percent)
                td = datetime.datetime.now() - start_time

            if temp is not None:
                read = utils_stream.copy(m, temp, progress_function if size != -1 else none_function, block_size)
            else:
                if isADownloadRequest:
                    # Console mode, only display the NC file URL on stdout
                    read = len(m.url)
                    print(m.url)
                else:
                    output = StringIO()
                    utils_stream.copy(m, output, progress_function if size != -1 else none_function, block_size)
                    read = len(output.getvalue())
                    print(output.getvalue())

            end_time = datetime.datetime.now()
            stop_wa.stop('downloading')

            log.info("Processing  time : %s", str(processing_time - init_time))
            log.info("Downloading time : %s", str(end_time - processing_time))
            log.info("Total time       : %s", str(end_time - init_time))
            log.info("Download rate    : %s/s", utils_unit
                     .convert_bytes((read / total_milliseconds(end_time - start_time)) * 10 ** 3))
        finally:
            m.close()
    finally:
        if temp is not None:
            temp.flush()
            temp.close()

    # raise exception if actual size does not match content-length header
    if temp is not None and size >= 0 and read < size:
        raise Exception(utils_messages.get_external_messages()['motu-client.exception.download.too-short'] %
                        (read, size))


def execute_request(_options):
    """
    the main function that submit a request to motu. Available options are:
    
    * Proxy configuration (with eventually user credentials)
      - proxy_server: 'http://my-proxy.site.com:8080'
      - proxy_user  : 'john'
      - proxy_pwd   :'doe'

    * Autorisation mode: 'cas', 'basic', 'none'
      - auth_mode: 'cas'
      
    * User credentials for authentication 'cas' or 'basic'
      - user: 'john'
      - pwd:  'doe'
    
    * Motu service URL
      - motu: 'http://atoll-dev.cls.fr:30080/mis-gateway-servlet/Motu'
    
    * Dataset identifier to download
      - product_id: 'dataset-duacs-global-nrt-madt-merged-h'
    
    * Service identifier to use for retrieving dataset
      - service_id: 'http://purl.org/myocean/ontology/service/database#yourduname'
    
    * Geographic extraction parameters
      - latitude_max :  10.0
      - latitude_min : -10.0
      - longitude_max: -0.333333333369
      - longitude_min:  0.0

    * Vertical extraction parameters
      - depth_max: 1000
      - depth_min: 0
    
    * Temporal extraction parameters, as a datetime instance or a string (format: '%Y-%m-%d %H:%M:%S')
      - date_max: 2010-04-25 12:05:36
      - date_min: 2010-04-25

    * Variable extraction
      - variable: ['variable1','variable2']
      
    * The file name and the directory of the downloaded dataset
      - out_dir : '.'
      - out_name: 'dataset'
      
    * The block size used to perform download
      - block_size: 12001
      
    * The socket timeout configuration
      - socket_timeout: 515

    * The user agent to use when performing http requests
      - user_agent: 'motu-api-client' 

    """
    global init_time

    log = logging.getLogger("motu_api")
    init_time = datetime.datetime.now()
    stop_wa = stop_watch.local_thread_stop_watch()
    stop_wa.start()
    try:
        # at first, we check given options are ok
        check_options(_options)

        # print some trace info about the options set
        log.log(utils_log.TRACE_LEVEL, '-' * 60)

        for option in dir(_options):
            if not option.startswith('_'):
                log.log(utils_log.TRACE_LEVEL, "%s=%s" % (option, getattr(_options, option)))

        log.log(utils_log.TRACE_LEVEL, '-' * 60)

        # start of url to invoke
        url_service = _options.motu

        # parameters of the invoked service
        url_params = build_params(_options)

        url_config = get_url_config(_options)

        # check if question mark is in the url
        question_mark = '?'
        if url_service.endswith(question_mark):
            question_mark = ''
        url = url_service + question_mark + url_params

        if _options.describe or _options.size:
            _options.out_name = _options.out_name.replace('.nc', '.xml')

        # set-up the socket timeout if any
        if _options.socket_timeout is not None:
            log.debug("Setting timeout %s" % _options.socket_timeout)
            socket.setdefaulttimeout(_options.socket_timeout)

        if _options.auth_mode == AUTHENTICATION_MODE_CAS:
            stop_wa.start('authentication')
            # perform authentication before acceding service
            download_url = utils_cas.authenticate_CAS_for_URL(url,
                                                              _options.user,
                                                              _options.pwd,
                                                              **url_config)
            url_service = download_url.split("?")[0]
            stop_wa.stop('authentication')
        else:
            # if none, we do nothing more, in basic, we let the url requester doing the job
            download_url = url

        # create a file for storing downloaded stream
        fh = os.path.join(_options.out_dir, _options.out_name)
        if _options.console_mode:
            fh = "console"

        try:
            # Synchronous mode
            if _options.sync or _options.describe or _options.size:
                is_a_download_request = False
                if not _options.describe and not _options.size:
                    is_a_download_request = True
                dl_2_file(download_url, fh, _options.block_size, is_a_download_request, **url_config)
                log.info("Done")
            # Asynchronous mode
            else:
                stop_wa.start('wait_request')
                request_url = get_request_url(download_url, url_service, **url_config)
                skip = False

                if request_url is not None:
                    # asynchronous mode
                    status = 0
                    dwurl = ""
                    msg = ""

                    while True:
                        if _options.auth_mode == AUTHENTICATION_MODE_CAS:
                            stop_wa.start('authentication')
                            # perform authentication before acceding service
                            request_url_cas = utils_cas.authenticate_CAS_for_URL(request_url,
                                                                                 _options.user,
                                                                                 _options.pwd, **url_config)
                            stop_wa.stop('authentication')
                        else:
                            # if none, we do nothing more, in basic, we let the url requester doing the job
                            request_url_cas = request_url

                        m = utils_http.open_url(request_url_cas, **url_config)
                        motu_reply = m.read()
                        dom = minidom.parseString(motu_reply)

                        for node in dom.getElementsByTagName('statusModeResponse'):
                            status = node.getAttribute('status')
                            dwurl = node.getAttribute('remoteUri')
                            msg = node.getAttribute('msg')

                        # Check status
                        if status == "0" or status == "3":
                            # in progress/pending
                            log.info('Product is not yet available (request in process)')
                            time.sleep(10)
                        else:
                            # finished (error|success)
                            break

                    if status == "2":
                        if msg.startswith("004-7 : The result file size"):
                            import xarray as xr
                            log.info(msg)
                            sizes = re.findall(r"[1-9][0-9]*.[0-9]+MBytes", msg, flags=0)
                            requested_size = float(sizes[0][:-6])
                            allowed_size = float(sizes[1][:-6])
                            parts = int(ceil(requested_size / allowed_size))
                            log.info("Downloading by {} parts.".format(parts))
                            date_min = datetime.datetime.strptime(_options.date_min, '%Y-%m-%d')
                            date_max = datetime.datetime.strptime(_options.date_max, '%Y-%m-%d')
                            date_delta = (date_max - date_min) // parts
                            dates = list()
                            for i in range(parts - 1):
                                dates.append((date_min.strftime('%Y-%m-%d'),
                                              (date_min + date_delta).strftime('%Y-%m-%d')))
                                date_min += date_delta + datetime.timedelta(days=1)
                                log.info("Part {}: {} - {}".format(i + 1, dates[-1][0], dates[-1][1]))
                            dates.append((date_min.strftime('%Y-%m-%d'), date_max.strftime('%Y-%m-%d')))
                            log.info("Part {}: {} - {}".format(parts, dates[-1][0], dates[-1][1]))
                            base_name, extension = os.path.splitext(_options.out_name)
                            # Download each part
                            for i, (dmin, dmax) in enumerate(dates):
                                log.info("Downloading part {}".format(i + 1))
                                _options.out_name = base_name + "_" + str(i) + extension
                                _options.date_min = dmin
                                _options.date_max = dmax
                                execute_request(_options)
                            skip = True
                        else:
                            log.error(msg)
                            raise Exception(msg)
                    elif status == "1":
                        log.info('The product is ready for download')
                        if dwurl != "":
                            dl_2_file(dwurl, fh, _options.block_size, not (_options.describe or _options.size),
                                      **url_config)
                            log.info("Done")
                        else:
                            log.error("Couldn't retrieve file")
                if not skip:
                    stop_wa.stop('wait_request')
        except Exception:
            try:
                if os.path.isfile(fh):
                    os.remove(fh)
            except Exception:
                pass
            raise
    finally:
        stop_wa.stop()
