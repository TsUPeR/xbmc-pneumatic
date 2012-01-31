Pneumatic
=========
Pneumatic is a NZB engine add-on for [XBMC](http://www.xbmc.org) Eden.
It uses [SABnzbd](http://www.sabnzbd.org) as backbone.

API
===

Pneumatic has a set of API's for other add-on's to use.

BASE
----
plugin://plugin.program.pneumatic/

PLAY
----
?mode=play&nzb=_url.encoded.nzb.http.path_&nzbname=_url.encoded.output.name_

DOWNLOAD
--------
?mode=download&nzb=_url.encoded.nzb.http.path_&nzbname=_url.encoded.output.name_

INCOMPLETE
----------
?mode=incomplete

SAVE .STRM
----------
?mode=save_strm&nzb=_url.encoded.nzb.http.path_&nzbname=_url.encoded.output.name_

STRM
----
?mode=strm&nzb=_url.encoded.nzb.http.path_&nzbname=_url.encoded.output.name_