# encoding: utf-8
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

import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding unique constraint on 'Project', fields ['base_directory']
        db.create_unique('project_project', ['base_directory'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Project', fields ['base_directory']
        db.delete_unique('project_project', ['base_directory'])


    models = {
        'project.project': {
            'Meta': {'object_name': 'Project'},
            'base_directory': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '512'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'git_repo': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '512', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        }
    }

    complete_apps = ['project']
