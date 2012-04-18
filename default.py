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

import sys
import re
import urllib
import urllib2
import os
import time

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from xml.dom.minidom import parse, parseString
from threading import Thread

import sabnzbd
import utils
import nfo
import strm
import xbmcplayer
import nfo2home
import strm2lib
import nzb as m_nzb

__settings__ = xbmcaddon.Addon(id='plugin.program.pneumatic')
__language__ = __settings__.getLocalizedString
__icon__ = __settings__.getAddonInfo("icon")

SABNZBD = sabnzbd.Sabnzbd(__settings__.getSetting("sabnzbd_ip"),
        __settings__.getSetting("sabnzbd_port"),__settings__.getSetting("sabnzbd_key"),
        __settings__.getSetting("sabnzbd_user"), __settings__.getSetting("sabnzbd_pass"),
        __settings__.getSetting("sabnzbd_cat"))
INCOMPLETE_FOLDER = unicode(__settings__.getSetting("sabnzbd_incomplete"), 'utf-8')

NZB_FOLDER = __settings__.getSetting("nzb_folder")
SAVE_NZB = (__settings__.getSetting("save_nzb").lower() == "true")
NZB_CACHE = __settings__.getSetting("nzb_cache")
IS_SAB_LOCAL = (__settings__.getSetting("is_sab_local").lower() == "true")

AUTO_PLAY = (__settings__.getSetting("auto_play").lower() == "true")

MODE_PLAY = "play"
MODE_DOWNLOAD = "download"
MODE_LIST_PLAY = "list_play"
MODE_AUTO_PLAY = "auto_play"
MODE_DELETE = "delete"
MODE_REPAIR = "repair"
MODE_INCOMPLETE = "incomplete"
MODE_INCOMPLETE_LIST = "incomplete_list"
MODE_STRM = "strm"
MODE_SAVE_STRM = "save_strm"
MODE_LOCAL = "local"
MODE_LOCAL_LIST_TOP = "local_list_top"
MODE_LOCAL_LIST = "local_list"
MODE_ADD_LOCAL = "add_local"
MODE_DEL_LOCAL = "del_local"

def add_posts(info_labels, url, mode, thumb='', fanart='', folder=True):
    listitem=xbmcgui.ListItem(info_labels['title'], iconImage="DefaultVideo.png", thumbnailImage=thumb)
    listitem.setInfo(type="Video", infoLabels=info_labels)
    listitem.setProperty("Fanart_Image", fanart)
    xurl = "%s?mode=%s" % (sys.argv[0],mode)
    xurl = xurl + url
    listitem.setPath(xurl)
    if mode == MODE_INCOMPLETE_LIST:
        cm = []
        cm_url_delete = sys.argv[0] + '?' + "mode=delete&incomplete=True" + url
        cm.append(("Delete" , "XBMC.RunPlugin(%s)" % (cm_url_delete)))
        cm_url_delete_all = sys.argv[0] + '?' + "mode=delete&delete_all=True&incomplete=True" + url
        cm.append(("Delete all inactive" , "XBMC.RunPlugin(%s)" % (cm_url_delete_all)))
        listitem.addContextMenuItems(cm, replaceItems=True)
    if mode == MODE_LOCAL_LIST_TOP:
        cm = []
        cm_url_add_local = sys.argv[0] + '?' + "mode=add_local"
        cm.append(("Add folder" , "XBMC.RunPlugin(%s)" % (cm_url_add_local)))
        cm_url_delete_local = sys.argv[0] + '?' + "mode=del_local" + url
        cm.append(("Remove folder" , "XBMC.RunPlugin(%s)" % (cm_url_delete_local)))
        listitem.addContextMenuItems(cm, replaceItems=True)
    return xbmcplugin.addDirectoryItem(handle=HANDLE, url=xurl, listitem=listitem, isFolder=folder)
    
def is_nzb_home(params):
    get = params.get
    nzb = utils.unquote_plus(get("nzb"))
    nzbname = utils.unquote_plus(get("nzbname"))
    folder = os.path.join(INCOMPLETE_FOLDER, nzbname)
    iscanceled = False
    type = get('type', 'addurl')
    sab_nzo_id = SABNZBD.nzo_id(nzbname)
    # if not os.path.exists(folder):
    if not utils.dir_exists(folder, sab_nzo_id):
        progressDialog = xbmcgui.DialogProgress()
        progressDialog.create('Pneumatic', 'Sending request to SABnzbd')
        category = get_category()
        if type == 'addurl':
            type, nzb = nzb_cache(type, nzb, nzbname)
        # SABnzbd and URI should be latin-1 encoded
        if type == 'addurl':
            response = SABNZBD.addurl(nzb.encode('latin-1'), nzbname, category=category)
        elif type == 'add_local':
            response = SABNZBD.add_local(nzb.encode('latin-1'), category=category)
        elif type == 'add_file':
            response = SABNZBD.add_file(nzb.encode('latin-1'), category=category)
        if "ok" in response:
            progressDialog.update(0, 'Request to SABnzbd succeeded', 'waiting for nzb download')
            seconds = 0
            while not (sab_nzo_id and os.path.exists(folder)):
                sab_nzo_id = SABNZBD.nzo_id(nzbname)
                label = str(seconds) + " seconds"
                progressDialog.update(0, 'Request to SABnzbd succeeded', 'waiting for nzb download', label)
                if progressDialog.iscanceled():
                    # Fix for hang when playing .strm
                    time.sleep(1)
                    xbmc.Player().stop()
                    #SABnzbd uses nzb url as name until it has downloaded the nzb file
                    #Trying to delete both the queue and history
                    pause = SABNZBD.pause(nzb,'')
                    time.sleep(3)
                    delete_msg = SABNZBD.delete_queue(nzb,'')
                    if not "ok" in delete_msg:
                        xbmc.log(delete_msg)
                        delete_msg = SABNZBD.delete_history(nzb,'')
                        if not "ok" in delete_msg:
                            xbmc.log(delete_msg)
                    iscanceled = True
                    break
                time.sleep(1)
                seconds += 1
            if not iscanceled:
                switch = SABNZBD.switch(0,nzbname, '')
                if not "ok" in switch:
                    xbmc.log(switch)
                    progressDialog.update(0, 'Failed to prioritize the nzb!')
                    time.sleep(2)
                # Dont add meta data for local nzb's
                if type == 'addurl':
                    t = Thread(target=save_nfo, args=(folder,))
                    t.start()
                return True, sab_nzo_id
            else:
                return False, sab_nzo_id
        else:
            xbmc.log(response)
            # Fix for hang when playing .strm
            xbmc.Player().stop()            
            notification("Request to SABnzbd failed!")
            return False, sab_nzo_id
    else:
        switch = SABNZBD.switch(0,nzbname, '')
        if not "ok" in switch:
            xbmc.log(switch)
            notification("Failed to prioritize the nzb!")
        # TODO make sure there is also a NZB in the queue
        return True, sab_nzo_id

def nzb_cache(type, nzb, nzbname):
    nzb_path = os.path.join(NZB_CACHE, '%s%s' % (nzbname, '.nzb'))
    if os.path.exists(nzb_path):
        nzb = nzb_path
        if IS_SAB_LOCAL:
            type = 'add_local'
        else:
            type = 'add_file'
        xbmc.log("Pneumatic loading %s from cache" % nzb)
    return type, nzb

def save_nfo(folder):
    nfo2home.save_nfo(__settings__, folder)
    return

def pre_play(nzbname, **kwargs):
    mode = kwargs.get('mode', None)
    sab_nzo_id = kwargs.get('nzo', None)
    iscanceled = False
    folder = os.path.join(INCOMPLETE_FOLDER, nzbname)
    folder_one = folder + '.1'
    if os.path.exists(folder_one):
        folder = folder_one
    sab_file_list = []
    multi_arch_list = []
    if sab_nzo_id is None:
        sab_nzo_id_history = SABNZBD.nzo_id_history(nzbname)
        nzf_list = utils.dir_to_nzf_list(folder, sabnzbd)
    else:
        nzo = sabnzbd.Nzo(SABNZBD, sab_nzo_id)
        nzf_list = nzo.nzf_list()
        sab_nzo_id_history = None
    sorted_nzf_list = utils.sorted_rar_nzf_file_list(nzf_list)
    # TODO
    # If we cant find any rars in the queue, we have to wait for SAB
    # and then guess the names...
    # if len(nzf_list) == 0:
        # iscanceled = get_nzf(folder, sab_nzo_id, None)
    multi_arch_nzf_list = utils.sorted_multi_arch_nzf_list(sorted_nzf_list)
    # Loop though all multi archives and add file to the 
    play_list = []
    clean_sorted_nzf_list = utils.nzf_diff_list(sorted_nzf_list, multi_arch_nzf_list)
    for nzf in multi_arch_nzf_list:
        if sab_nzo_id is not None:
            t = Thread(target=nzf_to_bottom, args=(sab_nzo_id, nzf_list, sorted_nzf_list,))
            t.start()
            iscanceled = get_nzf(folder, sab_nzo_id, nzf)
        if iscanceled:
            break
        else:
            if sab_nzo_id:
                set_streaming(sab_nzo_id)
            # TODO is this needed?
            # time.sleep(1)
            # RAR ANALYSYS #
            in_rar_file_list = utils.rar_filenames(folder, nzf.filename)
            movie_list = utils.sort_filename(in_rar_file_list)
            # Make sure we have a movie
            if not (len(movie_list) >= 1):
                notification("Not a movie!")
                break
            # Who needs sample?
            movie_no_sample_list = utils.no_sample_list(movie_list)
            # If auto play is enabled we skip samples in the play_list
            if AUTO_PLAY and mode is not MODE_INCOMPLETE_LIST:
                for movie_file in movie_no_sample_list:
                    play_list.append(nzf.filename)
                    play_list.append(movie_file)
            else:
                for movie_file in movie_list:
                    play_list.append(nzf.filename)
                    play_list.append(movie_file)
            # If the movie is a .mkv or .mp4 we need the last rar
            if utils.is_movie_mkv(movie_list) and sab_nzo_id:
                # If we have a sample or other file, the second rar is also needed..
                if len(in_rar_file_list) > 1:
                    second_nzf = clean_sorted_nzf_list[1]
                    iscanceled = get_nzf(folder, sab_nzo_id, second_nzf)
                last_nzf = clean_sorted_nzf_list[-1]
                iscanceled =  get_nzf(folder, sab_nzo_id, last_nzf)
                if iscanceled: 
                    break 
    if iscanceled:
        return
    else:
        rar_file_list = [x.filename for x in sorted_nzf_list]
        if (len(rar_file_list) >= 1):
            if AUTO_PLAY and ( mode is None or mode is MODE_STRM):
                video_params = dict()
                if not mode:
                    video_params['mode'] = MODE_AUTO_PLAY
                else:
                    video_params['mode'] = MODE_STRM
                video_params['play_list'] = utils.quote_plus(';'.join(play_list))
                video_params['file_list'] = utils.quote_plus(';'.join(rar_file_list))
                video_params['folder'] = utils.quote_plus(folder)
                return play_video(video_params)   
            else:
                return playlist_item(play_list, rar_file_list, folder, sab_nzo_id, sab_nzo_id_history)
        else:
            notification("No rar\'s in the NZB!!")
            return

def set_streaming(sab_nzo_id):
    # Set the post process to 0 = skip will cause SABnzbd to fail the job. requires streaming_allowed = 1 in sabnzbd.ini (6.x)
    setstreaming = SABNZBD.setStreaming('', sab_nzo_id)
    if not "ok" in setstreaming:
        xbmc.log(setstreaming)
        notification('Post process request to SABnzbd failed!')
        time.sleep(1)
    return

def playlist_item(play_list, rar_file_list, folder, sab_nzo_id, sab_nzo_id_history):
    new_play_list = play_list[:]
    for arch_rar, movie_file in zip(play_list[0::2], play_list[1::2]):
        info = nfo.ReadNfoLabels(folder)
        xurl = "%s?mode=%s" % (sys.argv[0],MODE_LIST_PLAY)
        url = (xurl + "&nzoid=" + str(sab_nzo_id) + "&nzoidhistory=" + str(sab_nzo_id_history)) +\
              "&play_list=" + utils.quote_plus(';'.join(new_play_list)) + "&folder=" + utils.quote_plus(folder) +\
              "&file_list=" + utils.quote_plus(';'.join(rar_file_list))
        new_play_list.remove(arch_rar)
        new_play_list.remove(movie_file)
        item = xbmcgui.ListItem(movie_file, iconImage='DefaultVideo.png', thumbnailImage=info.thumbnail)
        item.setInfo(type="Video", infoLabels=info.info_labels)
        item.setProperty("Fanart_Image", info.fanart)
        item.setPath(url)
        isfolder = False
        # item.setProperty("IsPlayable", "true")
        cm = []
        if sab_nzo_id_history:
            cm_url_repair = sys.argv[0] + '?' + "mode=repair" + "&nzoidhistory=" + str(sab_nzo_id_history) + "&folder=" + utils.quote_plus(folder)
            cm.append(("Repair" , "XBMC.RunPlugin(%s)" % (cm_url_repair)))
        cm_url_delete = sys.argv[0] + '?' + "mode=delete" + "&nzoid=" + str(sab_nzo_id) + "&nzoidhistory=" + str(sab_nzo_id_history) + "&folder=" + utils.quote_plus(folder)
        cm.append(("Delete" , "XBMC.RunPlugin(%s)" % (cm_url_delete)))
        item.addContextMenuItems(cm, replaceItems=True)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=item, isFolder=isfolder)
    xbmcplugin.setContent(HANDLE, 'movies')
    xbmcplugin.endOfDirectory(HANDLE, succeeded=True, cacheToDisc=True)
    return

def get_nzf(folder, sab_nzo_id, nzf):
    if sab_nzo_id is not None:
        if nzf.status.lower() == 'active':
            SABNZBD.file_list_position(sab_nzo_id, [nzf.nzf_id], 0)
        return wait_for_nzf(folder, sab_nzo_id, nzf)
    else:
        return False

def wait_for_nzf(folder, sab_nzo_id, nzf):
    iscanceled = False
    is_rar_found = False
    # If rar exist we skip dialogs
    some_rar = os.path.join(folder, nzf.filename)
    if os.path.exists(some_rar):
        is_rar_found = True
    if not is_rar_found:
        progressDialog = xbmcgui.DialogProgress()
        progressDialog.create('Pneumatic', 'Request to SABnzbd succeeded, waiting for ', utils.short_string(nzf.filename))
        time_now = time.time()
        while not is_rar_found:
            time.sleep(1)
            if os.path.exists(some_rar):
                # TODO Look for optimization
                # Wait until the file is written to disk before proceeding
                size_now = int(nzf.bytes)
                size_later = 0
                while (size_now != size_later) or (size_now == 0) or (size_later == 0):
                    size_now = os.stat(some_rar).st_size
                    if size_now != size_later:
                        time.sleep(0.5)
                        size_later = os.stat(some_rar).st_size
                is_rar_found = True
                break
            nzo = sabnzbd.Nzo(SABNZBD, sab_nzo_id)
            m_nzf = nzo.get_nzf_id(nzf.nzf_id)
            percent, label = utils.wait_for_rar_label(nzo, m_nzf, time_now)
            progressDialog.update(percent, 'Request to SABnzbd succeeded, waiting for', utils.short_string(nzf.filename), label)
            if progressDialog.iscanceled():
                dialog = xbmcgui.Dialog()
                ret = dialog.select('What do you want to do?', ['Delete job', 'Just download'])
                # Fix for hang when playing .strm
                xbmc.Player().stop()
                xbmc.executebuiltin('Dialog.Close(all, true)')
                if ret == 0:
                    pause = SABNZBD.pause('',sab_nzo_id)
                    time.sleep(3)
                    delete_ = SABNZBD.delete_queue('',sab_nzo_id)
                    if not "ok" in delete_:
                        xbmc.log(delete_)
                        notification("Deleting failed")
                    else:
                        notification("Deleting succeeded") 
                elif ret == 1:
                    notification("Downloading")
                return True
    return iscanceled

def nzf_to_bottom(sab_nzo_id, nzf_list, sorted_nzf_list):
    diff_list = list(set([nzf.nzf_id for nzf in nzf_list if nzf.nzf_id is not None])-set([nzf.nzf_id for nzf in sorted_nzf_list if nzf.nzf_id is not None]))
    SABNZBD.file_list_position(sab_nzo_id, diff_list, 3)
    return

def list_movie(params):
    get = params.get
    mode = get("mode")
    file_list = utils.unquote_plus(get("file_list")).split(";")
    play_list = utils.unquote_plus(get("play_list")).split(";")
    folder = get("folder")
    folder = utils.unquote_plus(folder)
    sab_nzo_id = get("nzoid")
    sab_nzo_id_history = get("nzoidhistory")
    return playlist_item(play_list, file_list, folder, sab_nzo_id, sab_nzo_id_history)

def list_incomplete(params):
    nzbname = utils.unquote_plus(params.get("nzbname"))
    sab_nzo_id = utils.unquote_plus(params.get("nzoid"))
    pre_play(nzbname, mode=MODE_INCOMPLETE_LIST, nzo=sab_nzo_id)

def play_video(params):
    get = params.get
    mode = get("mode")
    file_list = get("file_list")
    file_list = utils.unquote_plus(file_list).split(";")
    play_list = get("play_list")
    play_list = utils.unquote_plus(play_list).split(";")
    folder = get("folder")
    folder = utils.unquote_plus(folder)
    # We might have deleted the path
    if os.path.exists(folder):
        # we trick xbmc to play avi by creating empty rars if the download is only partial
        utils.write_fake(file_list, folder)
        # Prepare potential file stacking
        if (len(play_list) > 2):
            rar = []
            for arch_rar, movie_file in zip(play_list[0::2], play_list[1::2]):
                raruri = "rar://" + utils.rarpath_fixer(folder, arch_rar) + "/" + movie_file
                rar.append(raruri)
                raruri = 'stack://' + ' , '.join(rar)
        else:
            raruri = "rar://" + utils.rarpath_fixer(folder, play_list[0]) + "/" + play_list[1]
        info = nfo.NfoLabels()
        item = xbmcgui.ListItem(info.info_labels['title'], iconImage='DefaultVideo.png', thumbnailImage=info.thumbnail)
        item.setInfo(type="Video", infoLabels=info.info_labels)
        item.setPath(raruri)
        item.setProperty("IsPlayable", "true")
        xbmcplugin.setContent(HANDLE, 'movies')
        wait = 0
        player = xbmcplayer.XBMCPlayer(xbmc.PLAYER_CORE_DVDPLAYER)
        player.sleep(1000)
        if mode == MODE_AUTO_PLAY or mode == MODE_LIST_PLAY:
            player.play( raruri, item )
        else:
            xbmcplugin.setResolvedUrl(handle=HANDLE, succeeded=True, listitem=item)
        removed_fake = False
        while player.is_active:
            player.sleep(500)
            wait+= 1
            if player.is_playing and not removed_fake:
                utils.remove_fake(file_list, folder)
                removed_fake = True
            if player.is_stopped:
                the_end(folder, player.is_stopped)
                player.is_active = False
            elif player.is_ended:
                the_end(folder)
                player.is_active = False
            elif wait >= 6000 and not player.isPlayingVideo():
                notification("Error playing file!")
                break
        if not removed_fake:
            utils.remove_fake(file_list, folder)
    else:
        notification("File deleted")
        time.sleep(1)
        xbmc.executebuiltin("Action(ParentDir)")
    return

def the_end(folder, is_stopped = False):
    nzbname = os.path.basename(folder)
    sab_nzo_id_history = SABNZBD.nzo_id_history(nzbname)
    sab_nzo_id = SABNZBD.nzo_id(nzbname)
    params = dict()
    params['nzoidhistory'] = sab_nzo_id_history
    params['nzoid'] = sab_nzo_id
    params['incomplete'] = True
    params['folder'] = folder
    params['end'] = True
    if sab_nzo_id_history is None:
        the_end_dialog(params,progressing=True, is_stopped=is_stopped)
    elif is_stopped:
        the_end_dialog(params)
    elif (__settings__.getSetting("post_process").lower() == "repair"):
        repair(params)
    elif (__settings__.getSetting("post_process").lower() == "delete"):
        delete(params)
    elif (__settings__.getSetting("post_process").lower() == "ask"):
        the_end_dialog(params)
    return

def the_end_dialog(params, **kwargs):
    dialog = xbmcgui.Dialog()
    if 'is_stopped' in kwargs:
        is_stopped = kwargs['is_stopped']
    else:
        is_stopped = False
    if 'progressing' in kwargs:
        progressing = kwargs['progressing']
    else:
        progressing = False
    if progressing:
        options = ['Delete', 'Just download']
        if is_stopped:
            heading = 'Downloading, what do you want to do?'
        else:
            heading = 'Still downloading, what do you want to do?'
    else:
        heading = 'Download finished, what do you want to do?'
        options = ['Delete', 'Repair']
    ret = dialog.select(heading, options)
    if ret == 0:
        delete(params)
    if ret == 1 and progressing:
        return
    elif ret == 1 and not progressing:
        repair(params)
    return

def delete(params):
    get = params.get
    sab_nzo_id = get("nzoid")
    sab_nzo_id_history = get("nzoidhistory")
    sab_nzo_id_history_list = get("nzoidhistory_list")
    if sab_nzo_id_history_list:
        sab_nzo_id_history_list = utils.unquote_plus(sab_nzo_id_history_list).split(";")
    folder = get("folder")
    folder = utils.unquote_plus(folder)
    incomplete = get("incomplete")
    end = get("end")
    delete_all = get("delete_all")
    if delete_all:
        notification("Deleting all incomplete")
    else:
        notification("Deleting %s" % xbmc.translatePath(folder))
    if sab_nzo_id or sab_nzo_id_history:
        delete_ = "ok"
        if sab_nzo_id:
            if not "None" in sab_nzo_id and not delete_all:
                pause = SABNZBD.pause('',sab_nzo_id)
                time.sleep(3)
                if "ok" in pause:
                    delete_ = SABNZBD.delete_queue('',sab_nzo_id)
                else:
                    delete_ = "failed"
        if  sab_nzo_id_history:
            if not "None" in sab_nzo_id_history and not delete_all:
                delete_ = SABNZBD.delete_history('',sab_nzo_id_history)
        if delete_all and sab_nzo_id_history_list:
            for sab_nzo_id_history_item in sab_nzo_id_history_list:
                delete_state = SABNZBD.delete_history('',sab_nzo_id_history_item)
                if delete_state is not delete_:
                    delete_state = "failed"
            delete_ = delete_state
        if not "ok" in delete_:
            xbmc.log(delete_)
            notification("Deleting failed")
    else:
        notification("Deleting failed")
    if end:
        return
    elif incomplete:
        time.sleep(2)
        xbmc.executebuiltin("Container.Refresh")
    else:
        xbmc.executebuiltin("Action(ParentDir)")
    return

def download(params):
    get = params.get
    nzb = utils.unquote_plus(get("nzb"))
    nzbname = utils.unquote_plus(get("nzbname"))
    category = get_category(ask = True)
    addurl = SABNZBD.addurl(nzb, nzbname, category=category)
    progressDialog = xbmcgui.DialogProgress()
    progressDialog.create('Pneumatic', 'Sending request to SABnzbd')
    if "ok" in addurl:
        progressDialog.update(100, 'Request to SABnzbd succeeded')
        time.sleep(2)
    else:
        xbmc.log(addurl)
        progressDialog.update(0, 'Request to SABnzbd failed!')
        time.sleep(2)
    return

def get_category(ask = False):
    if __settings__.getSetting("sabnzbd_cat_ask").lower() == "true":
        ask = True
    if ask:
        dialog = xbmcgui.Dialog()
        category_list = SABNZBD.category_list()
        category_list.remove('*')
        category_list.insert(0, 'Default')
        ret = dialog.select('Select SABnzbd category', category_list)
        if ret == 0:
            category = None
        else:
            category = category_list[ret]
        return category
    else:
        return None

def repair(params):
    get = params.get
    sab_nzo_id_history = get("nzoidhistory")
    end = get("end")
    repair_ = SABNZBD.repair('',sab_nzo_id_history)
    if "ok" in repair_:
        notification("Repair succeeded")
    else:
        xbmc.log(repair_)
        notification("Repair failed")
    if not end:
        xbmc.executebuiltin("Action(ParentDir)")
    return

def incomplete():
    active_nzbname_list = []
    m_nzbname_list = []
    m_row = []
    for folder in os.listdir(INCOMPLETE_FOLDER):
        sab_nzo_id = SABNZBD.nzo_id(folder)
        if not sab_nzo_id:
            m_row.append(folder)
            m_row.append(None)
            m_nzbname_list.append(m_row)
            m_row = []
        else:
            m_row.append(folder)
            m_row.append(sab_nzo_id)
            active_nzbname_list.append(m_row)
            m_row = []
    nzbname_list = SABNZBD.nzo_id_history_list(m_nzbname_list)
    nzoid_history_list = [x[1] for x in nzbname_list if x[1] is not None]
    for row in active_nzbname_list:
        url = "&nzoid=" + str(row[1]) + "&nzbname=" + utils.quote_plus(row[0]) +\
              "&nzoidhistory_list=" + utils.quote_plus(';'.join(nzoid_history_list)) +\
              "&folder=" + utils.quote_plus(row[0])
        info = nfo.ReadNfoLabels(os.path.join(INCOMPLETE_FOLDER, row[0]))
        info.info_labels['title'] = "Active - " + info.info_labels['title']
        add_posts(info.info_labels, url, MODE_INCOMPLETE_LIST, info.thumbnail, info.fanart)
    for row in nzbname_list:
        if row[1]:
            url = "&nzoidhistory=" + str(row[1]) + "&nzbname=" + utils.quote_plus(row[0]) +\
                  "&nzoidhistory_list=" + utils.quote_plus(';'.join(nzoid_history_list)) +\
                  "&folder=" + utils.quote_plus(row[0])
            info = nfo.ReadNfoLabels(os.path.join(INCOMPLETE_FOLDER, row[0]))
            add_posts(info.info_labels, url, MODE_INCOMPLETE_LIST, info.thumbnail, info.fanart)
        else:
            # Clean out a failed SABnzbd folder removal
            utils.dir_exists(os.path.join(INCOMPLETE_FOLDER, row[0]), None)
    xbmcplugin.setContent(HANDLE, 'movies')
    xbmcplugin.endOfDirectory(HANDLE, succeeded=True, cacheToDisc=True)
    return

def local():
    if IS_SAB_LOCAL:
        type = 'add_local'
    else:
        type = 'add_file'
    folder_list = __settings__.getSetting('nzb_folder_list').split(';')
    if len(folder_list) == 1 and len(folder_list[0]) == 0:
        add_posts({'title':'Add folder'}, '', MODE_ADD_LOCAL, '', '', False)
    else:
        for folder in folder_list:
            folder_path = unicode(folder, 'utf-8')
            folder_name = os.path.split(os.path.dirname(folder_path))[1]
            if len(folder_path) > 1:
                url = "&type=" + type + "&folder=" + utils.quote_plus(folder_path)
                add_posts({'title':folder_name}, url, MODE_LOCAL_LIST_TOP, '', '')
    xbmcplugin.setContent(HANDLE, 'movies')
    xbmcplugin.endOfDirectory(HANDLE, succeeded=True, cacheToDisc=True)

def list_local(params):
    top_folder = utils.unquote_plus(params.get("folder"))
    type = utils.unquote_plus(params.get("type"))
    for folder in os.listdir(top_folder):
        folder_path = os.path.join(top_folder, folder)
        if os.path.isdir(folder_path):
            # Check if the folder contains a single nzb and no folders
            nzb_list = []
            folder_list = []
            for name in os.listdir(folder_path):
                name_path = os.path.join(folder_path, name)
                if os.path.isfile(name_path) and os.path.splitext(name_path)[1] == '.nzb':
                    nzb_list.append(name_path)
                elif os.path.isdir(name_path):
                    folder_list.append(name_path)
            # If single nzb allow the folder to be playable and show info
            if len(nzb_list) == 1 and len(folder_list) == 0:
                # Fixing the naming of nzb according to SAB rules
                nzb_name = m_nzb.Nzbname(os.path.basename(nzb_list[0])).final_name
                if folder.lower() == nzb_name.lower():
                    info = nfo.ReadNfoLabels(folder_path)
                    info.info_labels['title'] = info.info_labels['title']
                    url = "&nzbname=" + utils.quote_plus(nzb_name) +\
                          "&nzb=" + utils.quote_plus(nzb_list[0]) + "&type=" + type
                    add_posts(info.info_labels, url, MODE_PLAY, info.thumbnail, info.fanart, False)
                else:
                    url = "&type=" + type + "&folder=" + utils.quote_plus(folder_path)
                    add_posts({'title':folder}, url, MODE_LOCAL_LIST, '', '')
            else:
                url = "&type=" + type + "&folder=" + utils.quote_plus(folder_path)
                add_posts({'title':folder}, url, MODE_LOCAL_LIST, '', '')
        elif os.path.isfile(folder_path) and os.path.splitext(folder)[1] == '.nzb':
            url = "&nzbname=" + utils.quote_plus(m_nzb.Nzbname(folder).final_name) +\
                  "&nzb=" + utils.quote_plus(folder_path) + "&type=" + type
            add_posts({'title':folder}, url, MODE_PLAY, '', '', False)
    xbmcplugin.setContent(HANDLE, 'movies')
    xbmcplugin.endOfDirectory(HANDLE, succeeded=True, cacheToDisc=True)
    return

def add_local():
    dialog = xbmcgui.Dialog()
    nzb_file = dialog.browse(0, 'Pick a folder', 'files')
    # XBMC outputs utf-8
    path = unicode(nzb_file, 'utf-8')
    if not os.path.isdir(path):
        return None
    else:
        folder_list = __settings__.getSetting("nzb_folder_list").split(';')
        folder_list.append(nzb_file)
        new_folder_list = ';'.join(folder_list)
        __settings__.setSetting("nzb_folder_list", new_folder_list)
        xbmc.executebuiltin("Container.Refresh")

def del_local(params):
    folder = utils.unquote_plus(params.get("folder"))
    folder_path = folder.encode('utf-8')
    folder_list = __settings__.getSetting("nzb_folder_list").split(';')
    folder_list.remove(folder_path)
    new_folder_list = ';'.join(folder_list)
    __settings__.setSetting("nzb_folder_list", new_folder_list)
    xbmc.executebuiltin("Container.Refresh")

#From old undertexter.se plugin    
def unikeyboard(default, message):
    keyboard = xbmc.Keyboard(default, message)
    keyboard.doModal()
    if (keyboard.isConfirmed()):
        return keyboard.getText()
    else:
        return ""

def save_strm(nzbname, url):
    strm2lib.save_strm(__settings__, nzbname, url)
    if SAVE_NZB and os.path.exists(NZB_CACHE):
        nzb_path = os.path.join(NZB_CACHE, '%s%s' % (nzbname, '.nzb'))
        m_nzb.save(url, nzb_path)

def add_local_nzb():
    if not os.path.exists(NZB_FOLDER):
        __settings__.openSettings()
        return None
    dialog = xbmcgui.Dialog()
    nzb_file = dialog.browse(1, 'Pick a NZB', 'files', '.nzb', False, False, NZB_FOLDER)
    # XBMC outputs utf-8
    path = unicode(nzb_file, 'utf-8')
    if not os.path.isfile(path):
        return None
    else:
        params = dict()
        # Fixing the naming of nzb according to SAB rules
        params['nzbname'] = m_nzb.Nzbname(os.path.basename(path)).final_name
        params['nzb'] = path
        if IS_SAB_LOCAL:
            params['type'] = 'add_local'
        else:
            params['type'] = 'add_file' 
        return params

def notification(label):
    utils.notification(label, __settings__.getAddonInfo("icon"))

if (__name__ == "__main__" ):
    HANDLE = int(sys.argv[1])
    if not (__settings__.getSetting("firstrun")):
        __settings__.openSettings()
        if utils.pass_setup_test(SABNZBD.setup_streaming(), __settings__.getSetting("sabnzbd_incomplete")):
            __settings__.setSetting("firstrun", '1')
    else:
        if (not sys.argv[2]):
            add_posts({'title':'Incomplete'}, '', MODE_INCOMPLETE)
            add_posts({'title':'Browse local NZB\'s'}, '', MODE_LOCAL, '', '')
            xbmcplugin.setContent(HANDLE, 'movies')
            xbmcplugin.endOfDirectory(HANDLE, succeeded=True, cacheToDisc=True)
        else:
            params = utils.get_parameters(sys.argv[2])
            get = params.get
            if get("mode")== MODE_PLAY:
                is_home, sab_nzo_id = is_nzb_home(params)
                if is_home:
                    nzbname = utils.unquote_plus(get("nzbname"))
                    pre_play(nzbname, nzo=sab_nzo_id)
            if get("mode")== MODE_LIST_PLAY or get("mode")== MODE_AUTO_PLAY:
                play_video(params)
            if get("mode")== MODE_DELETE:
                delete(params)
            if get("mode")== MODE_DOWNLOAD:
                download(params)
            if get("mode")== MODE_REPAIR:
                repair(params)
            if get("mode")== MODE_INCOMPLETE:
                incomplete()
            if get("mode")== MODE_INCOMPLETE_LIST:
                list_incomplete(params)
            if get("mode")== MODE_STRM:
                xbmc.executebuiltin('Dialog.Close(all, true)')
                time.sleep(2)
                is_home, sab_nzo_id = is_nzb_home(params)
                if is_home:
                    nzbname = utils.unquote_plus(get("nzbname"))
                    pre_play(nzbname, mode=MODE_STRM, nzo=sab_nzo_id)
            if get("mode")== MODE_SAVE_STRM:
                nzbname = utils.unquote_plus(get("nzbname"))
                nzb = utils.unquote_plus(get("nzb"))
                t = Thread(target=save_strm, args=(nzbname, nzb,))
                t.start()
            if get("mode")== MODE_LOCAL:
                local()
            if get("mode")== MODE_LOCAL_LIST or get("mode")== MODE_LOCAL_LIST_TOP:
                list_local(params)
            if get("mode")== MODE_ADD_LOCAL:
                add_local()
            if get("mode")== MODE_DEL_LOCAL:
                del_local(params) 
