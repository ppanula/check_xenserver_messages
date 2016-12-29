#!/usr/bin/python

#
# Check system alert messages from pool/host
# Requirements: XenServer 6.2.0 as priorities on older XenServers are not defined properly
# 
# (c) 2013-2015 Pekka Panula / Sofor Oy
# License: BSD
# Version: 1.0.1
# Dated: 10.11.2015
# -v1.0.1: fixed session logout
#
# Example command line: ./check_xenserver_messages.py -H hostname -p password -l root
# 
# Nagios command define:
# set $USER26$ under resource.cfg, its xenserver password
# 
# 	define command {
# 		command_name    check_xenserver_messages
# 		command_line    $USER1$/check_xenserver_messages.py -H $HOSTADDRESS$ -p "$USER26$"
# 	}
#
# Message priorities, XenServer v6.2.0 and forward:
# Prio Name                   Description
# 1    Data-loss imminent     Take action now or your data may be permanently lost (e.g. corrupted)
# 2    Service-loss imminent  Take action now or some service(s) may fail (e.g. host / VM crash)
# 3    Service degraded       Take action now or some service may suffer (e.g. NIC bond degraded without HA)
# 4    Service recovered      Notice that something just improved (e.g. NIC bond repaired
# 5    Informational          More day-to-day stuff (e.g. VM started, suspended, shutdown, rebooted etc).
# 

import os
import datetime
from distutils.version import LooseVersion
# from dateutil import parser

# Entire program wrapped in try/except so that we can send exit code 3 to nagios on any error
try:

    import XenAPI
    import sys

    from optparse import OptionParser

    #Parse command line options
    #Python's standard option parser won't do what I want, so I'm subclassing it.
    #firstly, nagios wants exit code three if the options are bad
    #secondly, we want 'required options', which the option parser thinks is an oxymoron.
    #I on the other hand don't want to give defaults for the host and password, because nagios is difficult to set up correctly,
    #and the effect of that may be to hide a problem.
    class MyOptionParser(OptionParser):
        def error(self,msg):
            print msg
            try:
               os._exit(3)
            except:
               pass

        #stolen from python library reference, add required option check
        def check_required(self, opt):
            option=self.get_option(opt)
            if getattr(self.values, option.dest) is None:
                self.error("%s option not supplied" % option)

    optparser = MyOptionParser(description="Nagios plugin to check whether there are XenServer system alert messages")

    optparser.add_option("-H", "--hostname", dest="hostname", help="name of pool master")
    optparser.add_option("-l", "--login-name", default="root", dest="username", help="name to log in as (usually root)")
    optparser.add_option("-p", "--password", dest="password", help="password")

    (options, args) = optparser.parse_args()

    #abort if host and password weren't specified explicitly on the command line
    optparser.check_required("-H")
    optparser.check_required("-p")


    # NOT USED: filter only newer than: last 12 hours
    # newer_than = datetime.datetime.now() - datetime.timedelta(hours = 12)

    #get a session. set host_is_slave true if we need to redirect to a new master
    host_is_slave=False
    try:
        session=XenAPI.Session('https://'+options.hostname)
        session.login_with_password(options.username, options.password)
    except XenAPI.Failure, e:
        if e.details[0]=='HOST_IS_SLAVE':
            session=XenAPI.Session('https://'+e.details[1])
            session.login_with_password(options.username, options.password)
            host_is_slave=True
        else:
            raise

    sx=session.xenapi

    # Check XenServer version
    this_host    = sx.session.get_this_host(session._session)
    soft_version = sx.host.get_software_version(this_host)
    # host_rec  = sx.host.get_record(this_host)

    # exit if XenServer version < 6.2.0
    if LooseVersion(soft_version['product_version']) < LooseVersion('6.2.0'):
        print "ERROR - XenServer version (",soft_version['product_version'],") too old. Upgrade atleast to XenServer 6.2.0."
	try:
		os._exit(3)
	except:
		pass

    # Get messages
    messages=sx.message.get_all_records()

    # get all messages that have priority 3 or lower, 3 = degrated, 2 = service loss imminent, 1 = data loss imminent
    # WARNING: priorities are ONLY valid with XenServer 6.2 and newer!
    messages_with_sev=[msg for (ref,msg) in messages.iteritems() if (int(msg['priority'])<=3)]

    # logout
    session.xenapi.session.logout()

    if messages_with_sev:
	exitcode=2
	print "CRITICAL - There is system alert messages! Count: %s | alert_count=%s" % (len(messages_with_sev),len(messages_with_sev))
	for msg in messages_with_sev:
		print msg['timestamp'],"Priority:",msg['priority'],", name:",msg['name'],"body:",msg['body']
    else:
	print "OK - No System alert messages|alert_count=0"
	exitcode=0

except Exception, e:
    print "ERROR - Unexpected Exception [", str(e), "]"
    sys.exit(3) #Nagios wants error 3 if anything weird happens

sys.exit(exitcode)
