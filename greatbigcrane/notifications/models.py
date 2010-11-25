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

from django.db import models
from django.core.urlresolvers import reverse
from project.models import Project

make_choice = lambda x: ([(p,p) for p in x])

class Notification(models.Model):
    status = models.CharField(max_length=15, choices=make_choice([
        "success", "error", "general"]))
    summary = models.CharField(max_length=128)
    message = models.TextField()
    notification_time = models.DateTimeField(auto_now_add=True)
    project = models.ForeignKey(Project, null=True, blank=True, default=None)
    notification_type = models.CharField(max_length=16, blank=True, default='')
    dismissed = models.BooleanField(blank=True, default=False)
    rerun_job = models.CharField(blank=True, max_length=128)

    def get_absolute_url(self):
        return reverse("view_notification", args=[self.id])

    class Meta:
        ordering=["-notification_time"]
