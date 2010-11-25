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

import os.path
from shutil import copyfile
from django.db import models
from django.core.urlresolvers import reverse
from django.conf import settings
from buildout_manage.parser import buildout_parse

make_choice = lambda x: ([(p,p) for p in x])

class Project(models.Model):
    name = models.CharField(max_length=32)
    base_directory = models.CharField(max_length=512, unique=True)
    git_repo = models.CharField(max_length=512, blank=True, default='')
    description = models.TextField(blank=True,
            help_text="(Markdown syntax is supported)")
    project_type = models.CharField(max_length=9,
            choices=make_choice(["buildout", "pip"]))
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    test_status = models.BooleanField(default=False)
    favourite = models.BooleanField(default=False)

    def get_absolute_url(self):
        return reverse("view_project", args=[self.id])

    def buildout_sections(self):
        '''Return sorted dictionary of buildout sections'''
        sections = self.buildout()
        # You may wonder why I'm returning items. I am too. For unknown
        # reasons, {{project.buildout_sections.items}} does not return a
        # correct value inside templates.
        return sections.items()

    def buildout_filename(self):
        '''Get the filename that holds the buildout configuration.'''
        return os.path.join(self.base_directory, 'buildout.cfg')

    def requirements_filename(self):
        '''Get the filename that holds the pip requirements.'''
        return os.path.join(self.base_directory, 'requirements.txt')

    def buildout(self):
        sections = buildout_parse(self.buildout_filename())
        return sections

    def is_django(self):
        if not self.pipproject:
            sections = self.buildout()
            for name, section in sections.items():
                if 'recipe' in section and section['recipe'] == 'djangorecipe':
                    return True
            return False
        else:
            return 'Django' in self.pipproject.requirements

    def github_url(self):
        '''If our repo is a github repo, provide a link to the
        github page.'''
        github = self.git_repo.find("github.com")
        if github > -1:
            url = self.git_repo[github:].replace(":", "/")
            if url.endswith(".git"):
                url = url[:-4]
            url = "http://%s" % url
        else:
            url = ""
        return url

    def prep_project(self):
        if self.project_type == "buildout":
            self.prep_buildout_project()
        elif self.project_type == "pip":
            self.prep_pip_project()

    def prep_buildout_project(self):
        if not os.path.isdir(self.base_directory):
            os.makedirs(self.base_directory)
        skeleton = [(os.path.join(settings.PROJECT_HOME, "../bootstrap.py"),
                os.path.join(self.base_directory, "bootstrap.py")),
            (os.path.join(settings.PROJECT_HOME, "../base_buildout.cfg"),
                os.path.join(self.base_directory, "buildout.cfg"))]
        for source, dest in skeleton:
            if not os.path.isfile(dest):
                copyfile(source, dest)

    def prep_pip_project(self):
        if not os.path.isdir(self.base_directory):
            os.makedirs(self.base_directory)
        PipProject.objects.create(project=self)

    def __unicode__(self):
        return self.name

# Possibly We could use inheritance here, but I think it would get messy with
# generating forms
class PipProject(models.Model):
    project = models.OneToOneField(Project)
    virtualenv_path = models.CharField(max_length=256,
            help_text="The directory the virtualenv is stored in.",
            default="venv/")
    test_command = models.CharField(max_length=128,
            blank=True,
            help_text="Command to run tests. Eg: py.test, nose, ./run_tests.py")

    @property
    def requirements(self):
        if os.path.exists(self.project.requirements_filename()):
            with open(self.project.requirements_filename()) as req_file:
                return req_file.read()
        return ""


