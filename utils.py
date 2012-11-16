"""
 Copyright (c) 2010, 2011, 2012 Popeye

 Permission is hereby granted, free of charge, to any person
 obtaining a copy of this software and associated documentation
 files (the "Software"), to deal in the Software without
 restriction, including without limitation the rights to use,
 copy, modify, merge, publish, distribute, sublicense, and/or sell
 copies of the Software, and to permit persons to whom the
 Software is furnished to do so, subject to the following
 conditions:

 The above copyright notice and this permission notice shall be
 included in all copies or substantial portions of the Software.

 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
 OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
 HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
 WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 OTHER DEALINGS IN THE SOFTWARE.
"""

import re
import os
import htmlentitydefs
import urllib
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import time
import math
import shutil

import rarfile



RE_PART_X = r'(\S*?\.part\d{1,3}\.rar)'
RE_PART01_X = '(\S*?\.part0{0,2}1\.rar)'
RE_R_X = r'(\S*?\.[rs]\d{2,3})'
RE_RAR_X = r'(\S*?\.rar)'
RE_PART = '\.part\d{2,3}\.rar$'
RE_PART01 = '\.part0{1,2}1\.rar$'
RE_R = '\.[rs]\d{2,3}$'
RE_MOVIE = '\.avi$|\.mkv$|\.iso$|\.img$'
# https://github.com/sabnzbd/sabnzbd/blob/develop/sabnzbd/constants.py#L142
RE_SAMPLE = r'((^|[\W_])sample\d*[\W_])|(-s\.)'
RE_MKV = '\.mkv$|\.mp4$'
RE_HTML = '&(\w+?);'

RAR_HEADER = "Rar!\x1a\x07\x00"
RAR_MIN_SIZE = 10485760

def write_fake(file_list, folder):
    for filebasename in file_list:
        filename = join(folder, filebasename)
        if not exists(filename):
            result = write(filename, 'Rar!\x1a\x07')
            if not result:
                log("Failed writing fake rar %s" % filename)
        else:
            if size(filename) == 7:
                delete(filename)
                filename_one = join(folder, (filebasename + ".1"))
                if exists(filename_one):
                    rename(filename_one, filename)
    return

def remove_fake(file_list, folder):
    for filebasename in file_list:
        filename = join(folder, filebasename)
        filename_one = join(folder, (filebasename + ".1"))
        if exists(filename):
            if size(filename) == 7:
                delete(filename)
                filename_one = join(folder, (filebasename + ".1"))
                if exists(filename_one):
                    rename(filename_one, filename)
    return

def sorted_rar_nzf_file_list(nzf_list):
    file_list = []
    if len(nzf_list) > 0:
        for nzf in nzf_list:
            partrar = re.findall(RE_PART, nzf.filename)
            rrar = re.findall(RE_R, nzf.filename)
            if ((nzf.filename.endswith(".rar") and not partrar) or partrar or rrar):
                file_list.append(nzf)
            else:
                partrar_x = re.search(RE_PART_X, nzf.filename)
                rrar_x = re.search(RE_R_X, nzf.filename)
                rarrar_x = re.search(RE_RAR_X, nzf.filename)
                out = None
                if (rarrar_x and not partrar_x):
                    out = rarrar_x.group(1)
                elif partrar_x:
                    out = partrar_x.group(1)
                elif rrar_x:
                    out = rrar_x.group(1)
                if out is not None:
                    nzf.filename = out
                    file_list.append(nzf)
        if len(file_list) > 1:
            file_list.sort(key=lambda x: x.filename)
    return file_list

def sorted_multi_arch_nzf_list(nzf_list):
    file_list = []
    for nzf in nzf_list:
        partrar_x = re.findall(RE_PART_X, nzf.filename)
        part01rar_x = re.findall(RE_PART01_X, nzf.filename)
        rarrar_x = re.search(RE_RAR_X, nzf.filename)
        # No small sub archives
        if ((rarrar_x and not partrar_x) or part01rar_x) and nzf.bytes > RAR_MIN_SIZE:
            file_list.append(nzf)
    if len(file_list) > 1:
        file_list.sort(key=lambda x: x.filename)
    return file_list

def nzf_diff_list(list_a, list_b):
    nzf_list = list(set(list_a)-set(list_b))
    nzf_list.sort(key=lambda x: x.filename)
    return nzf_list

def list_dir(folder):
    file_list = []
    for filename in listdir_files(folder):
        row = []
        row.append(filename)
        bytes = size(join(folder,filename))
        row.append(bytes)
        file_list.append(row)
    return file_list

def dir_to_nzf_list(folder, sabnzbd):
    nzf_list = []
    file_list = list_dir(folder)
    for filename, bytes in file_list:
        nzf = sabnzbd.Nzf(filename=filename, bytes=bytes)
        nzf_list.append(nzf)
    return nzf_list

def dir_exists(folder, nzo_id):
    if exists(folder):
        if len(listdir_files(folder)) == 0 and nzo_id is None:
            # Clean out a failed SABnzbd folder removal
            rmdir(folder)
            log('Removed empty incomplete folder %s' % folder)
            return False
        return True
    else:
        return False

def rar_filenames(folder, file):
    log("rar_filenames: folder: %s file: %s" % (folder, file))
    filepath = join(folder, file)
    USERDATA_PATH = xbmc.translatePath(xbmcaddon.Addon(id='plugin.program.pneumatic').getAddonInfo("profile"))
    temp_path = os.path.join(USERDATA_PATH, 'temp.rar')
    # clean out potential old temp file
    delete(temp_path)
    # read only 1024 bytes of the remote rar
    buffer = read(filepath, 1024)
    # write it local for rar inspection 
    fd_out = open(temp_path,'wb')
    fd_out.write(buffer)
    fd_out.close()
    rf = rarfile.RarFile(temp_path)
    delete(temp_path)
    movie_file_list = rf.namelist()
    for f in rf.infolist():
        if f.compress_type != 48:
            log("Compressed rar %s" % filepath)
            xbmc.executebuiltin('Notification("Pneumatic","Compressed rar!!!")')
    return movie_file_list

def is_movie_mkv(movie_list):
    mkv = False
    for movie in movie_list:
        if re.search(RE_MKV, movie, re.IGNORECASE):
            mkv = True
    return mkv

def no_sample_list(movie_list):
    outList = movie_list[:]
    for i in range(len(movie_list)):
        match = re.search(RE_SAMPLE, movie_list[i], re.IGNORECASE)
        if match:
            outList.remove(movie_list[i])
    if len(outList) == 0:
        # We return sample if it's the only file left 
        outList.append(movie_list[0])
    return outList
  
def rarpath_fixer(folder, file):
    filepath = os.path.join(folder, file)
    filepath = quote(filepath)
    filepath = filepath.replace(".","%2e")
    filepath = filepath.replace("-","%2d")
    filepath = filepath.replace(":","%3a")
    filepath = filepath.replace("\\","%5c")
    filepath = filepath.replace("/","%2f")
    return filepath
    
# FROM plugin.video.youtube.beta  -- converts the request url passed on by xbmc to our plugin into a dict  
def get_parameters(parameterString):
    commands = {}
    splitCommands = parameterString[parameterString.find('?')+1:].split('&')
    for command in splitCommands: 
        if (len(command) > 0):
            splitCommand = command.split('=')
            name = splitCommand[0]
            value = splitCommand[1]
            commands[name] = value  
    return commands

def sort_filename(filename_list):
    outList = filename_list[:]
    if len(filename_list) == 1:
        return outList
    else:
        for i in range(len(filename_list)):
            match = re.search(RE_MOVIE, filename_list[i], re.IGNORECASE)
            if not match:
                outList.remove(filename_list[i])
        if len(outList) == 0:
            outList.append(filename_list[0])
        return outList

def descape_entity(m, defs=htmlentitydefs.entitydefs):
    # callback: translate one entity to its ISO Latin value
    try:
        return defs[m.group(1)]
    except KeyError:
        return m.group(0) # use as is

def descape(string):
    pattern = re.compile(RE_HTML)
    return pattern.sub(descape_entity, string)

def pass_setup_test(result, incomplete):
    pass_test = True
    if result == "ip":
        error = "Wrong ip-number or port"
    if result == "apikey":
        error = "Wrong API key"
    if result == "restart":
        error = "Please restart SABnzbd, allow_streaming"
    if not result == "ok":
        xbmcgui.Dialog().ok('Pneumatic - SABnzbd error:', error)
        pass_test = False
    filename = ['plugin.program.pneumatic.test.rar']
    if not incomplete:
            pass_test = False
            xbmcgui.Dialog().ok('Pneumatic', 'No incomplete folder configured')
    try:
        write_fake(filename, incomplete)
    except:
        pass_test = False
        xbmcgui.Dialog().ok('Pneumatic - failed to write test file', 'in incomplete folder')
    try:
        remove_fake(filename, incomplete)
    except:
        pass_test = False
        xbmcgui.Dialog().ok('Pneumatic - failed to remove test file', 'in incomplete folder')
    return pass_test
    
def short_string(input):
    chars = len(input)
    if chars < 52:
        return input
    else:
        output = input[0:33] + "...  ..." + input[(chars-11):(chars)]
        return output

def wait_for_rar_label(nzo, nzf, time_then):
    if nzf is None:
        mb = 1
        mbleft = 0
    else:
        mb = nzf.mb
        mbleft = nzf.mbleft
    s = time.time() - time_then
    if mbleft > 0:
        percent = math.floor(((mb-mbleft)/mb)*100)
    else:
        percent = 100
    if nzo.is_in_queue:
        label = "%.0fs | %.2fMB | %sB/s | Total ETA: %s" % (s, mbleft, nzo.speed, nzo.timeleft)
    else:
        label = "This item is missing from the SABnzb queue"
    return int(percent), label

def notification(label, icon):
    xbmc.executebuiltin('Notification("Pneumatic", "%s", 500, %s)' % (label, icon))
    
def quote(name):
    if isinstance(name, unicode):
        return urllib.quote(name.encode('utf-8'))
    else:
        return urllib.quote(name)

def quote_plus(name):
    if isinstance(name, unicode):
        return urllib.quote_plus(name.encode('utf-8'))
    else:
        return urllib.quote_plus(name)

def unquote(name):
    if isinstance(name, unicode):
        return urllib.unquote(name)
    else:
        return unicode(urllib.unquote(name), 'utf-8')

def unquote_plus(name):
    if isinstance(name, unicode):
        return urllib.unquote_plus(name)
    else:
        return unicode(urllib.unquote_plus(name), 'utf-8')

def join(path1, path2):
    path = os.path.join(path1, path2)
    return xbmc.validatePath(path)

def read(file, bytes=None):
    fd = xbmcvfs.File(file)
    if bytes is not None:
        buffer = fd.read(bytes)
    else:
        buffer = fd.read()
    fd.close()
    return buffer

def seek(file, pos, where):
    # where in a file to seek from[0 begining, 1 current , 2 end possition]
    fd = xbmcvfs.File(file)
    result = fd.seek(pos, where)
    fd.close()
    return result

def size(file):
    fd = xbmcvfs.File(file)
    size_out = fd.size()
    fd.close()
    return size_out

def write(file, buffer):
    fd = xbmcvfs.File(file, 'w')
    result = fd.write(buffer)
    fd.close()
    return result

def copy(source, target):
    return xbmcvfs.copy(source, target)

def delete(file):
    return xbmcvfs.delete(file)

def exists(path):
    # path is a file or folder
    return xbmcvfs.exists(path)

def listdir(path):
    dirs, files = xbmcvfs.listdir(path)
    return dirs, files

def listdir_dirs(path):
    dirs, files = xbmcvfs.listdir(path)
    return dirs

def listdir_files(path):
    dirs, files = xbmcvfs.listdir(path)
    return files

def mkdir(path):
    return xbmcvfs.mkdir(path)

def mkdirs(path):
    # Will create all folders in path if needed
    return xbmcvfs.mkdirs(path)

def rename(file, name):
    return xbmcvfs.rename(file, name)

def rmdir(path):
    return xbmcvfs.rmdir(path)

def log(txt, level=xbmc.LOGDEBUG):
    # Modified from http://forum.xbmc.org/showthread.php?tid=144677
    # Log admits both unicode strings and str encoded with "utf-8" (or ascii). will fail with other str encodings.
    if txt is not None:
        if isinstance (txt,str):
            txt = txt.decode("utf-8") #if it is str we assume it's "utf-8" encoded.
                                  #will fail if called with other encodings (latin, etc) BE ADVISED!
        # At this point we are sure txt is a unicode string.
        # I reencode to utf-8 because in many xbmc versions log doesn't admit unicode.
        message = u'plugin.program.pneumatic: %s' % txt
        xbmc.log(msg=message.encode("utf-8"), level=level)