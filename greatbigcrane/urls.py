"""
Copyright 2010 Jason Chu, Dusty Phillips, and Phil Schalm

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin
admin.autodiscover()

handler500 # Pyflakes

urlpatterns = patterns('',
    url('^$', 'project.views.index', name="dashboard_url"),
    url('^about/$', 'project.views.about', name="about_url"),
    (r'^notifications/', include('notifications.urls')),
    (r'^projects/', include('project.urls')),
    (r'^recipes/', include('recipes.urls')),
    (r'^preferences/', include('preferences.urls')),
    (r'^jobs/', include('job_queue.urls')),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve',
         {'document_root': settings.MEDIA_ROOT}),
    )
