#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2009-2010:
#    Gabes Jean, naparuba@gmail.com
#    Gerhard Lausser, Gerhard.Lausser@consol.de
#
# This file is part of Shinken.
#
# Shinken is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Shinken is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Shinken.  If not, see <http://www.gnu.org/licenses/>.


#
# This file is used to test host- and service-downtimes.
#

import os
import sys
import time
import random

from shinken.comment import Comment

from test_livestatus import TestConfig, unittest

from mock_livestatus import mock_livestatus_handle_request


sys.setcheckinterval(10000)


@mock_livestatus_handle_request
class TestConfigAuth(TestConfig):
    def setUp(self):
        self.setup_with_file('etc/shinken_livestatus_authuser.cfg')
        Comment.id = 1
        self.testid = str(os.getpid() + random.randint(1, 1000))
        self.init_livestatus()
        print "Cleaning old broks?"
        self.sched.conf.skip_initial_broks = False
        self.sched.brokers['Default-Broker'] = {'broks' : {}, 'has_full_broks' : False}
        self.sched.fill_initial_broks('Default-Broker')

        self.update_broker()
        self.nagios_path = None
        self.livestatus_path = None
        self.nagios_config = None
        # add use_aggressive_host_checking so we can mix exit codes 1 and 2
        # but still get DOWN state
        host = self.sched.hosts.find_by_name("dbsrv1")
        host.__class__.use_aggressive_host_checking = 1


    """
dbsrv1  adm(adm1,adm2,adm3)
    app_db_oracle_check_connect    oradba(oradba1,oradba2) cc(cc1,cc2,cc3)
    app_db_oracle_check_alertlog   oradba(oradba1,oradba2)

dbsrv2  adm(adm1,adm2,adm3)
    app_db_oracle_check_connect    oradba(oradba1,oradba2) cc(cc1,cc2,cc3)
    app_db_oracle_check_alertlog   oradba(oradba1,oradba2)

dbsrv3  adm(adm1,adm2,adm3) oradba(oradba1,oradba2)
    app_db_oracle_check_connect    oradba(oradba1,oradba2) cc(cc1,cc2,cc3)
    app_db_oracle_check_alertlog   oradba(oradba1,oradba2)

dbsrv4  adm(adm1,adm2,adm3) mydba(mydba1,mydba2)
    app_db_mysql_check_connect     mydba(mydba1,mydba2) cc(cc1,cc2,cc3)
    app_db_mysql_check_alertlog    mydba(mydba1,mydba2)

dbsrv5  adm(adm1,adm2,adm3) mydba(mydba1,mydba2)
    app_db_mysql_check_connect     mydba(mydba1,mydba2) cc(cc1,cc2,cc3)
    app_db_mysql_check_alertlog    mydba(mydba1,mydba2)

www1    adm(adm1,adm2,adm3) web(web1,web2)
    app_web_apache_check_http      web(web1,web2) cc(cc1,cc2,cc3)
    app_web_apache_check_errorlog  web(web1,web2)

www2    adm(adm1,adm2,adm3) web(web1,web2) winadm(bill,steve)
    app_web_apache_check_http      web(web1,web2) cc(cc1,cc2,cc3)
    app_web_apache_check_errorlog  web(web1,web2)
    os_windows_check_autosvc
    """

    def test_host_itersorted(self):
        self.print_header()
        now = time.time()
        objlist = []
        for host in self.sched.hosts:
            objlist.append([host, 0, 'UP'])
        for service in self.sched.services:
            objlist.append([service, 0, 'OK'])
        self.scheduler_loop(1, objlist)

        self.update_broker()
        #self.livestatus_broker.datamgr.rg.all_done_linking(1)
        print "rg is", self.livestatus_broker.datamgr.rg.hosts._id_contact_heap
        allhosts = sorted([h.get_full_name() for h in self.livestatus_broker.datamgr.rg.hosts.__itersorted__()])
        print allhosts
        self.assertEqual(["dbsrv1", "dbsrv2", "dbsrv3", "dbsrv4", "dbsrv5", "www1", "www2"], allhosts )
        hint = {"target": 0, "authuser": "oradba1"}
        orahosts = sorted([h.get_full_name() for h in self.livestatus_broker.datamgr.rg.hosts.__itersorted__(hint)])
        print orahosts
        self.assertEqual([u"dbsrv3"], orahosts )
        hint = {"target": 0, "authuser": "mydba2"}
        myhosts = sorted([h.get_full_name() for h in self.livestatus_broker.datamgr.rg.hosts.__itersorted__(hint)])
        print myhosts
        self.assertEqual(["dbsrv4", "dbsrv5"], myhosts )
        print "rg is", self.livestatus_broker.datamgr.rg.services
        print "rg is", self.livestatus_broker.datamgr.rg.services._id_contact_heap
        # unknown user
        hint = {"target": 0, "authuser": "adm0"}
        admservices = sorted([s.get_full_name() for s in self.livestatus_broker.datamgr.rg.services.__itersorted__(hint)])
        self.assertEqual(0, len(admservices) )
        # known user which is a contact to all hosts
        hint = {"target": 0, "authuser": "adm1"}
        admservices = sorted([s.get_full_name() for s in self.livestatus_broker.datamgr.rg.services.__itersorted__(hint)])
        self.assertEqual(15, len(admservices) ) #all services
        hint = {"target": 0, "authuser": "bill"} # bill->www2->windows
        print "rg is", self.livestatus_broker.datamgr.rg.hostgroups._id_contact_heap
        winhosts = sorted([s.get_name() for s in self.livestatus_broker.datamgr.rg.hostgroups.__itersorted__(hint)])
        print winhosts
        self.assertEqual(["windows"], winhosts )
        print "rg is", self.livestatus_broker.datamgr.rg.hostgroups
        self.livestatus_broker.datamgr.rg.group_authorization_strict = False
        self.livestatus_broker.datamgr.rg.all_done_linking(1)
        print "==================================================="
        #print "rg is", self.livestatus_broker.datamgr.rg.hostgroups._id_contact_heap
        for contact in sorted(self.livestatus_broker.datamgr.rg.hostgroups._id_contact_heap.keys()):
            print "%-10s %s" % (contact, self.livestatus_broker.datamgr.rg.hostgroups._id_contact_heap[contact])
        self.livestatus_broker.datamgr.rg.group_authorization_strict = True
        self.livestatus_broker.datamgr.rg.all_done_linking(1)
        #print "rg is", self.livestatus_broker.datamgr.rg.hostgroups._id_contact_heap
        for contact in sorted(self.livestatus_broker.datamgr.rg.hostgroups._id_contact_heap.keys()):
            print "%-10s %s" % (contact, self.livestatus_broker.datamgr.rg.hostgroups._id_contact_heap[contact])

    def test_host_authorization(self):
        self.print_header()
        now = time.time()
        objlist = []
        for host in self.sched.hosts:
            objlist.append([host, 0, 'UP'])
        for service in self.sched.services:
            objlist.append([service, 0, 'OK'])
        self.scheduler_loop(1, objlist)
        self.update_broker()
        request = """GET hosts
AuthUser: oradba1
Columns: name
OutputFormat: python
KeepAlive: on
"""
        # test_host_0/1
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        pyresponse = eval(response)
        self.assertEqual(1, len(pyresponse) )
        self.assert_("dbsrv3" in [h[0] for h in pyresponse])

        request = """GET hosts
AuthUser: bill
Columns: name
OutputFormat: python
KeepAlive: on
"""
        # only windows
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        pyresponse = eval(response)
        self.assertEqual(3, len(pyresponse) )
        self.assert_("dbsrv3" in [h[0] for h in pyresponse])
        self.assert_("dbsrv5" in [h[0] for h in pyresponse])
        self.assert_("www2" in [h[0] for h in pyresponse])

    def test_service_authorization_loose(self):
        self.print_header()
        now = time.time()
        objlist = []
        for host in self.sched.hosts:
            objlist.append([host, 0, 'UP'])
        for service in self.sched.services:
            objlist.append([service, 0, 'OK'])
        self.scheduler_loop(1, objlist)
        self.update_broker()
        request = """GET hosts
AuthUser: bill
Columns: name services
Filter: name = www2
OutputFormat: python
KeepAlive: on
"""
        # all because bill is host contact (via cgroup winadm), 2xapp_web, 1xos_windows
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print "rg is", self.livestatus_broker.datamgr.rg.services._id_contact_heap["bill"]
        print response
        pyresponse = eval(response)
        print pyresponse
        self.assertEqual(3, len(pyresponse[0][1]) )
        self.assert_("app_web_apache_check_http" in pyresponse[0][1])
        self.assert_("app_web_apache_check_errorlog" in pyresponse[0][1])
        self.assert_("os_windows_check_autosvc" in pyresponse[0][1])

        request = """GET hosts
AuthUser: bill
Columns: name services
Filter: name = www1
OutputFormat: python
KeepAlive: on
"""
        # none because bill is neither host contact nor service contact
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        pyresponse = eval(response)
        self.assertEqual(0, len(pyresponse) )

        request = """GET hosts
AuthUser: cc1
Columns: name services
Filter: name = www2
OutputFormat: python
KeepAlive: on
"""
        # 1 because cc1 is direct contact for 1 service, app_web_apache_check_http
        # controlcenter guys are allowed to restart a webserver, nothing else
        # BUT: this query is a hosts-table-query. cc1 has no access to www2
        # Therefore, the result is empty (confirmed with mk-livestatus)
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        pyresponse = eval(response)
        print pyresponse
        self.assertEqual(0, len(pyresponse) )

        request = """GET services
AuthUser: cc1
Columns: description
Filter: host_name = www2
OutputFormat: python
KeepAlive: on
"""
        # 1 because cc1 is direct contact for 1 service, app_web_apache_check_http
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        pyresponse = eval(response)
        print pyresponse
        self.assertEqual(1, len(pyresponse[0]) )
        self.assert_("app_web_apache_check_http" in pyresponse[0][0])

        request = """GET services
AuthUser: cc1
Columns: description
OutputFormat: python
KeepAlive: on
"""
        # cc1 is contact for 7 services
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        pyresponse = eval(response)
        print pyresponse
        self.assertEqual(7, len(pyresponse) )

    def test_service_authorization_strict(self):
        self.print_header()
        now = time.time()
        objlist = []
        for host in self.sched.hosts:
            objlist.append([host, 0, 'UP'])
        for service in self.sched.services:
            objlist.append([service, 0, 'OK'])
        self.scheduler_loop(1, objlist)
        self.update_broker()
        self.livestatus_broker.datamgr.rg.service_authorization_strict = True
        self.livestatus_broker.datamgr.rg.all_done_linking(0)
        request = """GET hosts
AuthUser: bill
Columns: name services
Filter: name = www2
OutputFormat: python
KeepAlive: on
"""
        # at a first glance, nothing because bill is only host contact, not a contact to any service
        # BUT www2/os_windows_check_autosvc has no dedicated contacts, so it inherits host contacts
        # BUUUHUUTT this is a host query. bill is a contact of this host. so we get the full list
        # of services. not really consistent, but confirmed with mk-livestatus.
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        pyresponse = eval(response)
        print pyresponse
        #for contact in sorted(self.livestatus_broker.datamgr.rg.hostgroups._id_contact_heap.keys()):
        #    print "%-10s %s" % (contact, self.livestatus_broker.datamgr.rg.hosts._id_contact_heap[contact])
        #    here we see in fact, that bill is only contact to www2/os_windows_check_autosvc
        #    print "%-10s %s" % (contact, self.livestatus_broker.datamgr.rg.services._id_contact_heap[contact])
        self.assertEqual(3, len(pyresponse[0][1]) )
        self.assert_("app_web_apache_check_http" in pyresponse[0][1])
        self.assert_("app_web_apache_check_errorlog" in pyresponse[0][1])
        self.assert_("os_windows_check_autosvc" in pyresponse[0][1])

        request = """GET services
AuthUser: bill
Columns: description
Filter: host_name = www2
OutputFormat: python
KeepAlive: on
"""
        # now send a service query. this time we get only one service because bill is only
        # a contact for this service (even not as a contact-attribute in the service definition
        # but by service-with-no-contact-attribute-iherits-from-host)
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        pyresponse = eval(response)
        print pyresponse
        self.assertEqual(1, len(pyresponse[0]) )
        self.assert_("os_windows_check_autosvc" in pyresponse[0][0])

        request = """GET hosts
AuthUser: bill
Columns: name services
Filter: name = www1
OutputFormat: python
KeepAlive: on
"""
        # none because bill is neither host contact nor service contact
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        pyresponse = eval(response)
        self.assertEqual(0, len(pyresponse) )

        request = """GET hosts
AuthUser: cc1
Columns: name services
Filter: name = www2
OutputFormat: python
KeepAlive: on
"""
        # 1 because cc1 is direct contact for 1 service, app_web_apache_check_http
        # controlcenter guys are allowed to restart a webserver, nothing else
        # BUT: this query is a hosts-table-query. cc1 has no access to www2
        # Therefore, the result is empty (confirmed with mk-livestatus)
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        pyresponse = eval(response)
        print pyresponse
        self.assertEqual(0, len(pyresponse) )

        request = """GET services
AuthUser: cc1
Columns: description
Filter: host_name = www2
OutputFormat: python
KeepAlive: on
"""
        # 1 because cc1 is direct contact for 1 service, app_web_apache_check_http
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        pyresponse = eval(response)
        print pyresponse
        self.assertEqual(1, len(pyresponse[0]) )
        self.assert_("app_web_apache_check_http" in pyresponse[0][0])

        request = """GET services
AuthUser: cc1
Columns: description
OutputFormat: python
KeepAlive: on
"""
        # cc1 is contact for 7 services
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        pyresponse = eval(response)
        print pyresponse
        self.assertEqual(7, len(pyresponse) )

        request = """GET services
AuthUser: adm1
Columns: description
OutputFormat: python
KeepAlive: on
"""
        # adm1 is only host contact. it is never mentioned in a service definition
        # only www2/os_windows_check_autosvc inherits adm1 via host
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        pyresponse = eval(response)
        print pyresponse
        self.assertEqual(1, len(pyresponse) )

    def test_group_authorization_strict(self):
        self.print_header()
        now = time.time()
        objlist = []
        for host in self.sched.hosts:
            objlist.append([host, 0, 'UP'])
        for service in self.sched.services:
            objlist.append([service, 0, 'OK'])
        self.scheduler_loop(1, objlist)
        self.update_broker()
        #self.livestatus_broker.datamgr.rg.group_authorization_strict = False
        #self.livestatus_broker.datamgr.rg.all_done_linking(0)
        print "hosts/hostgroups"
        for contact in sorted(self.livestatus_broker.datamgr.rg.hostgroups._id_contact_heap.keys()):
            print "%-10s %s" % (contact, self.livestatus_broker.datamgr.rg.hosts._id_contact_heap[contact])
            print "%-10s %s" % (contact, self.livestatus_broker.datamgr.rg.hostgroups._id_contact_heap[contact])
        print "services/servicegroups"
        for contact in sorted(self.livestatus_broker.datamgr.rg.servicegroups._id_contact_heap.keys()):
            print "%-10s %s" % (contact, self.livestatus_broker.datamgr.rg.services._id_contact_heap[contact])
            print "%-10s %s" % (contact, self.livestatus_broker.datamgr.rg.servicegroups._id_contact_heap[contact])
        request = """GET hostgroups
AuthUser: bill
Columns: name members
OutputFormat: python
KeepAlive: on
"""
        # bill is contact for all hosts in the windows group
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        pyresponse = eval(response)
        self.assertEqual(1, len(pyresponse) )
        self.assertEqual("windows", pyresponse[0][0] )
        request = """GET hostgroups
AuthUser: web1
Columns: name members
OutputFormat: python
KeepAlive: on
"""
        # web1 is contact for www1 and www2, so web
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        pyresponse = eval(response)
        self.assertEqual(1, len(pyresponse) )
        self.assertEqual("web", pyresponse[0][0] )
        request = """GET hostgroups
AuthUser: adm1
Columns: name members
OutputFormat: python
KeepAlive: on
"""
        # every host has adm1 as contact, so every hostgroup must appear here
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        pyresponse = eval(response)
        self.assertEqual(6, len(pyresponse) )

        print "now check servicesbygroup"
        request = """GET servicesbygroup
Columns: servicegroup_name host_name service_description
AuthUser: oradba1
OutputFormat: python
"""
        expect = """oracle;dbsrv1;app_db_oracle_check_alertlog
oracle;dbsrv1;app_db_oracle_check_connect
oracle;dbsrv2;app_db_oracle_check_alertlog
oracle;dbsrv2;app_db_oracle_check_connect
oracle;dbsrv3;app_db_oracle_check_alertlog
oracle;dbsrv3;app_db_oracle_check_connect
"""
        #response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        # assert len 6

        request = """GET hostsbygroup
Columns:  hostgroup_name host_name
OutputFormat: python
AuthUser: web1
"""
        # hostsbygroup is not so strict like hostgroups (we get no answer to hostgroups)
        expect = """
all;www1
all;www2
linux;www1
web;www1
web;www2
windows;www2
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response

        request = """GET servicesbyhostgroup
Columns: hostgroup_name host_name service_description
AuthUser: oradba1
OutputFormat: csv
"""
        expect = """
all;dbsrv1;app_db_oracle_check_connect
all;dbsrv1;app_db_oracle_check_alertlog
all;dbsrv2;app_db_oracle_check_connect
all;dbsrv2;app_db_oracle_check_alertlog
all;dbsrv3;app_db_oracle_check_connect
all;dbsrv3;app_db_oracle_check_alertlog
linux;dbsrv1;app_db_oracle_check_connect
linux;dbsrv1;app_db_oracle_check_alertlog
linux;dbsrv2;app_db_oracle_check_connect
linux;dbsrv2;app_db_oracle_check_alertlog
oracle;dbsrv1;app_db_oracle_check_connect
oracle;dbsrv1;app_db_oracle_check_alertlog
oracle;dbsrv2;app_db_oracle_check_connect
oracle;dbsrv2;app_db_oracle_check_alertlog
oracle;dbsrv3;app_db_oracle_check_connect
oracle;dbsrv3;app_db_oracle_check_alertlog
windows;dbsrv3;app_db_oracle_check_connect
windows;dbsrv3;app_db_oracle_check_alertlog
"""
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response

    def test_group_authorization_loose(self):
        self.print_header()
        now = time.time()
        objlist = []
        for host in self.sched.hosts:
            objlist.append([host, 0, 'UP'])
        for service in self.sched.services:
            objlist.append([service, 0, 'OK'])
        self.scheduler_loop(1, objlist)
        self.update_broker()
        self.livestatus_broker.datamgr.rg.group_authorization_strict = False
        self.livestatus_broker.datamgr.rg.all_done_linking(0)
        for contact in sorted(self.livestatus_broker.datamgr.rg.hostgroups._id_contact_heap.keys()):
            print "%-10s %s" % (contact, self.livestatus_broker.datamgr.rg.hosts._id_contact_heap[contact])
            print "%-10s %s" % (contact, self.livestatus_broker.datamgr.rg.hostgroups._id_contact_heap[contact])
        request = """GET hostgroups
AuthUser: bill
Columns: name members
OutputFormat: python
KeepAlive: on
"""
        # bill is contact for dbsrv3, dbsrv5, www2 and therefore in oracle, mysql, linux, windows, web and of course all
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        pyresponse = eval(response)
        #self.assertEqual(1, len(pyresponse) )

        request = """GET hostgroups
AuthUser: web1
Columns: name members
OutputFormat: python
KeepAlive: on
"""
        # web1 is contact for www1 and www2, so linux, windows, web and all
        response, keepalive = self.livestatus_broker.livestatus.handle_request(request)
        print response
        pyresponse = eval(response)
        self.assertEqual(4, len(pyresponse) )


if __name__ == '__main__':
    #import cProfile
    command = """unittest.main()"""
    unittest.main()
    #cProfile.runctx( command, globals(), locals(), filename="/tmp/livestatus.profile" )

    #allsuite = unittest.TestLoader.loadTestsFromModule(TestConfig)
    #unittest.TextTestRunner(verbosity=2).run(allsuite)
