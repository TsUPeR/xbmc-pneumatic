import urllib
import urllib2
import xbmc
from xml.dom.minidom import parse, parseString
import post_form

class Sabnzbd:
    def __init__ (self, ip, port, apikey, username = None, password = None, category = None):
        self.ip = ip
        self.port = port
        self.apikey = apikey
        self.baseurl = "http://" + self.ip + ":" + self.port + "/api?apikey=" + apikey
        if username and password:
            password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
            url = "http://" + self.ip + ":" + self.port
            password_manager.add_password(None, url, username, password)
            authhandler = urllib2.HTTPBasicAuthHandler(password_manager)
            opener = urllib2.build_opener(authhandler)
            urllib2.install_opener(opener)
        self.category = category
            
    def addurl(self, nzb, nzbname, **kwargs):
        category = kwargs.get('category', None)
        priority = kwargs.get('priority', None)
        url = "%s&mode=addurl&name=%s&nzbname=%s" % \
              (self.baseurl, urllib.quote_plus(nzb),urllib.quote_plus(nzbname))
        if priority:
            url = "%s&priority=%s" % (url, priority)
        if category:
            url = "%s&cat=%s" % (url, category)
        elif self.category:
            url = "%s&cat=%s" % (url, self.category)
        responseMessage = self._sabResponse(url)
        return responseMessage

    def add_local(self, path, **kwargs):
        category = kwargs.get('category', None)
        priority = kwargs.get('priority', None)
        url = "%s&mode=addlocalfile&name=%s" % \
              (self.baseurl, urllib.quote_plus(path))
        if priority:
            url = "%s&priority=%s" % (url, priority)
        if category:
            url = "%s&cat=%s" % (url, category)
        elif self.category:
            url = "%s&cat=%s" % (url, self.category)
        responseMessage = self._sabResponse(url)
        return responseMessage
        
    def add_file(self, path, **kwargs):
        url = "%s&mode=addfile" % self.baseurl
        responseMessage = post_form.post(path, self.apikey, url, **kwargs)
        return responseMessage

    def pause(self, nzbname='', id=''):
        url = self.baseurl + "&mode=pause"
        if nzbname:
            sab_nzo_id = self.nzo_id(nzbname)
            url = self.baseurl + "&mode=queue&name=pause&value=" + str(sab_nzo_id)
        if id:
            url = self.baseurl + "&mode=queue&name=pause&value=" + str(id)
        responseMessage = self._sabResponse(url)
        return responseMessage

    def resume(self, nzbname='', id=''):
        url = self.baseurl + "&mode=pause"
        if nzbname:
            sab_nzo_id = self.nzo_id(nzbname)
            url = self.baseurl + "&mode=queue&name=resume&value=" + str(sab_nzo_id)
        if id:
            url = self.baseurl + "&mode=queue&name=resume&value=" + str(id)
        responseMessage = self._sabResponse(url)
        return responseMessage

    def delete_queue(self, nzbname='', id=''):
        if nzbname:
            sab_nzo_id = self.nzo_id(nzbname)
            url = self.baseurl + "&mode=queue&name=delete&del_files=1value=" + str(sab_nzo_id)
            responseMessage = self._sabResponse(url)
        elif id:
            url = self.baseurl + "&mode=queue&name=delete&del_files=1&value=" + str(id)
            responseMessage = self._sabResponse(url)
        else:
            responseMessage = "no name or id for delete queue provided"
        return responseMessage

    def delete_history(self, nzbname='', id=''):
        if nzbname:
            sab_nzo_id = self.nzo_id_history(nzbname)
            # TODO if nothing found
            url = self.baseurl + "&mode=history&name=delete&del_files=1&value=" + str(sab_nzo_id)
            responseMessage = self._sabResponse(url)
        elif id:
            url = self.baseurl + "&mode=history&name=delete&del_files=1&value=" + str(id)
            responseMessage = self._sabResponse(url)
        else:
            responseMessage = "no name or id for delete history provided"
        return responseMessage 

    def postProcess(self, value=0, nzbname='',id=''):
        if not value in range(0,3):
            value = 0
        if nzbname:
            sab_nzo_id = self.nzo_id(nzbname)
            url = self.baseurl + "&mode=change_opts&value=" + str(sab_nzo_id) + "&value2=" + str(value)
            responseMessage = self._sabResponse(url)
        elif id:
            url = self.baseurl + "&mode=change_opts&value=" + str(id) + "&value2=" + str(value)
            responseMessage = self._sabResponse(url)
        else:
            responseMessage = "no name or id for post process provided"
        return responseMessage

    def switch(self, value=0, nzbname='',id=''):
        if not value in range(0,100):
            value = 0
        if nzbname:
            sab_nzo_id = self.nzo_id(nzbname)
            url = self.baseurl + "&mode=switch&value=" + str(sab_nzo_id) + "&value2=" + str(value)
            responseMessage = self._sabResponse(url)
        elif id:
            url = self.baseurl + "&mode=switch&value=" + str(id) + "&value2=" + str(value)
            responseMessage = self._sabResponse(url)
        else:
            responseMessage = "no name or id for job switch provided"
        if "0" or "-1 1" in responseMessage:
            responseMessage = "ok"
        return responseMessage

    def repair(self, nzbname='',id=''):
        if nzbname:
            sab_nzo_id = self.nzo_id(nzbname)
            url = self.baseurl + "&mode=retry&value=" + str(sab_nzo_id)
            responseMessage = self._sabResponse(url)
        elif id:
            url = self.baseurl + "&mode=retry&value=" + str(id)
            responseMessage = self._sabResponse(url)
        else:
            responseMessage = "no name or id for repair provided"
        return responseMessage 
        
    def setStreaming(self, nzbname='',id=''):
        if (not id) and nzbname:
            id = self.nzo_id(nzbname)
        if id:
            ppMessage = self.postProcess(0,'',id)
            switchMessage = self.switch(0,'',id)
            if "ok" in (ppMessage and switchMessage):
                responseMessage = "ok"
            else:
                responseMessage = "failed setStreaming"
        else:
            responseMessage = "no name or id for setStreaming provided"
        return responseMessage

    def _sabResponse(self, url):
        try:
            req = urllib2.Request(url)
            response = urllib2.urlopen(req)
        except:
            responseMessage = "unable to load url: " + url
        else:
            log = response.read()
            response.close()
            if "ok" in log:
                responseMessage = 'ok'
            else:
                responseMessage = log
                xbmc.log("plugin.program.pneumatic SABnzbd message: %s" % log)
                xbmc.log("plugin.program.pneumatic SABnzbd from url: %s" % url)
        return responseMessage
        
    def nzo_id(self, nzbname):
        url = self.baseurl + "&mode=queue&start=0&limit=50&output=xml"
        doc = _load_xml(url)
        sab_nzo_id = None
        if doc:
            if doc.getElementsByTagName("slot"):
                for slot in doc.getElementsByTagName("slot"):
                    filename = get_node_value(slot, "filename")
                    if filename.lower() == nzbname.lower():
                        sab_nzo_id  = get_node_value(slot, "nzo_id")
        return sab_nzo_id

    def nzf_id(self, sab_nzo_id, name):
        url = self.baseurl + "&mode=get_files&output=xml&value=" + str(sab_nzo_id)
        doc = _load_xml(url)
        sab_nzf_id = None
        if doc:
            if doc.getElementsByTagName("file"):
                for file in doc.getElementsByTagName("file"):
                    filename = get_node_value(file, "filename")
                    status = get_node_value(file, "status")
                    if filename.lower() == name.lower() and status == "active":
                        sab_nzf_id  = get_node_value(file, "nzf_id")
        return sab_nzf_id

    def nzf_id_list(self, sab_nzo_id, file_list):
        url = self.baseurl + "&mode=get_files&output=xml&value=" + str(sab_nzo_id)
        doc = _load_xml(url)
        sab_nzf_id_list = []
        file_nzf = dict()
        if doc:
            if doc.getElementsByTagName("file"):
                for file in doc.getElementsByTagName("file"):
                    filename = get_node_value(file, "filename")
                    status = get_node_value(file, "status")
                    if status == "active":
                        file_nzf[filename] = get_node_value(file, "nzf_id")
        for filename in file_list:
            try:
                sab_nzf_id_list.append(file_nzf[filename])
            except:
                xbmc.log("plugin.program.pneumatic: unable to find sab_nzf_id for: " + filename)
        return sab_nzf_id_list

    def nzo_id_history(self, nzbname):
        start = 0
        limit = 20
        noofslots = 21
        sab_nzo_id = None
        while limit <= noofslots and not sab_nzo_id:
            url = self.baseurl + "&mode=history&start=" +str(start) + "&limit=" + str(limit) + "&output=xml"
            doc = _load_xml(url)
            if doc:
                history = doc.getElementsByTagName("history")
                noofslots = int(get_node_value(history[0], "noofslots"))
                if doc.getElementsByTagName("slot"):
                    for slot in doc.getElementsByTagName("slot"):
                        filename = get_node_value(slot, "name")
                        if filename == nzbname:
                            sab_nzo_id  = get_node_value(slot, "nzo_id")
                start = limit + 1
                limit = limit + 20
            else:
                limit = 1
                noofslots = 0                
        return sab_nzo_id

    def nzo_id_history_list(self, nzbname_list):
        start = 0
        limit = 20
        noofslots = 21
        sab_nzo_id = None
        while limit <= noofslots and not sab_nzo_id:
            url = self.baseurl + "&mode=history&start=" +str(start) + "&limit=" + str(limit) + "&output=xml"
            doc = _load_xml(url)
            if doc:
                history = doc.getElementsByTagName("history")
                noofslots = int(get_node_value(history[0], "noofslots"))
                if doc.getElementsByTagName("slot"):
                    for slot in doc.getElementsByTagName("slot"):
                        filename = get_node_value(slot, "name")
                        for row in nzbname_list:
                            if filename == row[0]:
                                sab_nzo_id = get_node_value(slot, "nzo_id")
                                row[1] = sab_nzo_id
                start = limit + 1
                limit = limit + 20
            else:
                limit = 1
                noofslots = 0
        return nzbname_list

    def file_list(self, id=''):
        url = self.baseurl + "&mode=get_files&output=xml&value=" + str(id)
        doc = _load_xml(url)
        file_list = []
        if doc:
            if doc.getElementsByTagName("file"):
                for file in doc.getElementsByTagName("file"):
                    status = get_node_value(file, "status")
                    if status == "active":
                        row = []
                        filename = get_node_value(file, "filename")
                        row.append(filename)
                        bytes = get_node_value(file, "bytes")
                        bytes = int(bytes.replace(".00",""))
                        row.append(bytes)
                        file_list.append(row)
        return file_list

    def file_list_position(self, sab_nzo_id, sab_nzf_id, position):
        action = { -1 : 'Delete',
                    0 : 'Top',
                    1 : 'Up',
                    2 : 'Down',
                    3 : 'Bottom'}
        url = "http://" + self.ip + ":" + self.port + "/sabnzbd/nzb/" + sab_nzo_id + "/bulk_operation?session=" \
              + self.apikey + "&action_key=" + action[position]
        for nzf_id in sab_nzf_id:
            url = url + "&" + nzf_id + "=on"
        try:
            req = urllib2.Request(url)
            response = urllib2.urlopen(req)
        except:
            xbmc.log("plugin.program.pneumatic: unable to load url: " + url)
            xbmc.executebuiltin('Notification("Pneumatic","SABnzbd failed moving file to top of queue")')
            return None
        response.close()
        return

    def category_list(self):
        url = self.baseurl + "&mode=get_config&section=categories&output=xml"
        doc = _load_xml(url)
        category_list = []
        if doc:
            if doc.getElementsByTagName("category"):
                for category in doc.getElementsByTagName("category"):
                    category = get_node_value(category, "name")
                    category_list.append(category)
        return category_list

    def misc_settings_dict(self):
        url = self.baseurl + "&mode=get_config&section=misc&output=xml"
        doc = _load_xml(url)
        settings_dict = dict()
        if doc:
            if doc.getElementsByTagName("misc"):
                for misc in doc.getElementsByTagName("misc")[0].childNodes:
                    try:
                        settings_dict[misc.tagName] = misc.firstChild.data
                    except:
                        pass
        return settings_dict

    def setup_streaming(self):
        # 1. test the connection
        # 2. check allow_streaming
        # 3. set allow streaming if missing
        url = self.baseurl + "&mode=version&output=xml"
        try:
            req = urllib2.Request(url)
            response = urllib2.urlopen(req)
        except:
            xbmc.log("plugin.program.pneumatic: unable to conncet to SABnzbd: " + url)
            return "ip"
        xml = response.read()
        response.close()
        url = self.baseurl + "&mode=get_config&section=misc&keyword=allow_streaming&output=xml"
        doc = _load_xml(url)
        if doc.getElementsByTagName("result"):
            return "apikey"
        allow_streaming = "0"
        if doc.getElementsByTagName("misc"):
            allow_streaming = get_node_value(doc.getElementsByTagName("misc")[0], "allow_streaming")
        if not allow_streaming == "1":
            url = self.baseurl + "&mode=set_config&section=misc&keyword=allow_streaming&value=1"
            _load_xml(url)
            return "restart"
        return "ok"

def get_node_value(parent, name, ns=""):
    if ns:
        return unicode(parent.getElementsByTagNameNS(ns, name)[0].childNodes[0].data.encode('utf-8'), 'utf-8')
    else:
        return unicode(parent.getElementsByTagName(name)[0].childNodes[0].data.encode('utf-8'), 'utf-8')

def _load_xml(url):
    try:
        req = urllib2.Request(url)
        response = urllib2.urlopen(req)
    except:
        xbmc.log("plugin.program.pneumatic: unable to load url: " + url)
        xbmc.executebuiltin('Notification("Pneumatic","SABnzbd down")')
        return None
    xml = response.read()
    response.close()
    try:
        out = parseString(xml)
    except:
        xbmc.log("plugin.program.pneumatic: malformed xml from url: " + url)
        xbmc.executebuiltin('Notification("Pneumatic","SABnzbd malformed xml")')
        return None
    return out

class Nzo:
    def __init__(self, sabnzbd, nzo_id):
        self.sabnzbd = sabnzbd
        self.nzo_id = nzo_id
        self._get_queue()

    def _get_queue(self):
        # Limit to "only" 100 items
        url = "%s&mode=queue&start=0&limit=100&output=xml" % self.sabnzbd.baseurl
        doc = _load_xml(url)
        if doc:
            queue_info = dict()
            queue = doc.getElementsByTagName("queue")
            self.speed = get_node_value(queue[0], "speed")
            slots = doc.getElementsByTagName("slot")
            if slots:
                for slot in slots:
                    if self.nzo_id == get_node_value(slot, "nzo_id"):
                        self.status = get_node_value(slot, "status")
                        self.index = get_node_value(slot, "index")
                        self.eta = get_node_value(slot, "eta")
                        self.missing = get_node_value(slot, "missing")
                        self.avg_age = get_node_value(slot, "avg_age")
                        self.script = get_node_value(slot, "script")
                        self.mb = get_node_value(slot, "mb")
                        self.sizeleft = get_node_value(slot, "sizeleft")
                        self.filename = get_node_value(slot, "filename")
                        self.priority = get_node_value(slot, "priority")
                        self.cat = get_node_value(slot, "cat")
                        self.mbleft = get_node_value(slot, "mbleft")
                        self.timeleft = get_node_value(slot, "timeleft")
                        self.percentage = get_node_value(slot, "percentage")
                        self.unpackopts = get_node_value(slot, "unpackopts")
                        self.size = get_node_value(slot, "size")

    def _get_nzf_list(self):
        out_list = []
        out_dict = dict()
        url = "%s&mode=get_files&output=xml&value=%s" % (self.sabnzbd.baseurl, str(self.nzo_id))
        doc = _load_xml(url)
        if doc:
            files = doc.getElementsByTagName("file")
            if files:
                i = 0
                for file in files:
                    kwargs = dict()
                    kwargs['status'] = get_node_value(file, "status")
                    kwargs['mb'] = float(get_node_value(file, "mb"))
                    kwargs['age'] = get_node_value(file, "age")
                    kwargs['bytes'] = int((get_node_value(file, "bytes")).replace(".00",""))
                    kwargs['filename'] = get_node_value(file, "filename")
                    kwargs['mbleft'] = float(get_node_value(file, "mbleft"))
                    if kwargs['status'] == "active":
                        kwargs['nzf_id'] = get_node_value(file, "nzf_id")
                    kwargs['id'] = int(get_node_value(file, "id"))
                    nzf = Nzf(**kwargs)
                    out_list.append(nzf)
                    out_dict[kwargs['filename']] = i
                    i+= 1
        return out_list, out_dict

    def nzf_list(self):
        try:
            nzf_list, nzf_dict = self._get_nzf_list()
            return nzf_list
        except:
            return None

    def get_nzf(self, name):
        try:
            nzf_list, nzf_dict = self._get_nzf_list()
            return nzf_list[nzf_dict[name]]
        except:
            return None

    def get_nzf_id(self, nzf_id):
        nzf_list, nzf_dict = self._get_nzf_list()
        out = None
        for nzf in nzf_list:
            if nzf_id == nzf.nzf_id:
                out = nzf
                break
        return out

class Nzf:
    def __init__(self, **kwargs):
        self.status = kwargs.get('status')
        self.mb = kwargs.get('mb')
        self.age = kwargs.get('age')
        self.bytes = kwargs.get('bytes')
        self.filename = kwargs.get('filename')
        self.subject = kwargs.get('subject', self.filename)
        self.mbleft = kwargs.get('mbleft')
        self.nzf_id = kwargs.get('nzf_id', None)
        self.id = kwargs.get('id')
