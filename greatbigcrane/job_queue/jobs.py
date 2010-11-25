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
import zmq
import json
import subprocess
from project.models import Project
from preferences.models import Preference
from notifications.models import Notification
from buildout_manage.parser import buildout_parse

addr = 'tcp://127.0.0.1:5555'

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect(addr)

def queue_job(command, **kwargs):
    '''Run the given command on the job queue, passing it any arguments as kwargs.'''
    serialized = make_job_string(command, **kwargs)
    send_job(serialized)

def send_job(serialized):
    socket.send(serialized)
    assert socket.recv() == "ACK"

def make_job_string(command, **kwargs):
    assert command in command_map
    kwargs.update(command=command)
    return json.dumps(kwargs)

def command(command_name):
    "Decorator that marks a function as a queuable command."
    def wrap(function):
        command_map[command_name] = function
        return function
    return wrap

command_map = {}

# Create the actual commands here. Use command decorator to keep the map up to date
@command("BOOTSTRAP")
def bootstrap(project_id):
    '''Run the bootstrap process inside the given project's base directory.'''
    project = Project.objects.get(id=project_id)
    print("running bootstrap %s" % project.name)

    project.prep_project()

    process = subprocess.Popen("python bootstrap.py", cwd=project.base_directory,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

    response = process.communicate()[0]

    Notification.objects.create(status="success" if not process.returncode else "error",
            summary="Bootstrapping '%s' %s" % (
                project.name, "success" if not process.returncode else "error"),
            message=response,
            project=project)

@command("BUILDOUT")
def buildout(project_id):
    """Run the buildout process in the given project's base directory."""
    project = Project.objects.get(id=project_id)
    print("running buildout %s" % project.name)
    Notification.objects.create(status="general",
            summary="Buildout '%s' started" % (project.name),
            message="Buildout for '%s' project has started" % (project.name),
            project=project)
    process = subprocess.Popen("bin/buildout", cwd=project.base_directory,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

    response = process.communicate()[0]

    Notification.objects.create(status="success" if not process.returncode else "error",
            summary="Buildouting '%s' %s" % (
                project.name, "success" if not process.returncode else "error"),
            message=response,
            project=project)

@command("TEST")
def test_buildout(project_id):
    """Run the test command in the buildout project's base directory.
    Tries to do some intelligent guessing about how tests should be run."""
    project = Project.objects.get(id=project_id)
    print("running tests for %s" % project.name)

    test_binaries = []

    # FIXME: HOLY NESTED CONDITIONALS, BATMAN
    # figure out what test commands to run
    if project.project_type == "buildout":
        bc = buildout_parse(project.buildout_filename())

        parts = bc['buildout']['parts']
        if not isinstance(parts, list):
            parts = [parts]

        # We get to do some detection in this one
        # First look for django test
        for section, values in bc.iteritems():
            if section in parts:
                if values.get('recipe') == 'djangorecipe':
                    # Django, we know what's going on
                    if 'test' in values:
                        test_script = 'test'
                        if 'testrunner' in values:
                            test_script = values['testrunner']
                        test_binaries.append('bin/' + test_script)
                    else:
                        test_script = section
                        if 'control-script' in values:
                            test_script = values['control-script']
                        test_binaries.append('bin/' + test_script + ' test')
                elif values.get('recipe') == 'zc.recipe.testrunner':
                    test_script = section
                    if 'script' in values:
                        test_script = values['control-script']
                    test_binaries.append('bin/' + test_script)
    elif project.project_type == "pip":
        # FIXME: Do you use windows and this command failed? Patches welcome.
        command = "source %s ; %s" % (
                os.path.join(project.pipproject.virtualenv_path, 'bin',
                    'activate'),
                project.pipproject.test_command)
        test_binaries.append(command)

    # Run the test commands
    errors = False
    responses = []
    try:
        Notification.objects.create(status="general",
                summary="Testing of '%s' started" % (project.name),
                message="Testing for '%s' project has started" % (project.name),
                project=project)
        for binary in test_binaries:
            process = subprocess.Popen(binary, cwd=project.base_directory,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

            responses.append(process.communicate()[0])
            errors = errors or process.returncode != 0

        # Make the output a little nicer when you run multiple test suites

        message = []
        for test_command, response in zip(test_binaries, responses):
            com_length = len(test_command)+1
            response_set = []
            response_set.append('='*com_length)
            response_set.append('\n')
            response_set.append(test_command)
            response_set.append(':')
            response_set.append('\n')
            response_set.append('='*com_length)
            response_set.append('\n')
            response_set.append(response)
            message.append(''.join(response_set))
    except Exception:
        project.test_status = False
        project.save
        raise

    Notification.objects.create(status="success" if not errors else "error",
            summary="Testing '%s' %s" % (
                project.name, "success" if not errors else "error"),
            message=('\n\n'+'*'*50+'\n\n').join(message),
            project=project,
            rerun_job=make_job_string("TEST", project_id=project_id),
            notification_type="TEST",
            )
    project.test_status = not errors
    project.save()

@command("GITCLONE")
def clone_repo(project_id):
    """clone a git repo into the directory if it does not exist."""
    from greatbigcrane.job_queue.jobs import queue_job
    project = Project.objects.get(id=project_id)
    print("cloning repo for %s" % project.name)

    if os.path.exists(project.base_directory):
        Notification.objects.create(status="general",
                summary="Cloning '%s' %s" % (
                    project.name, "not necessary"),
                message="Repo not cloned because directory already exists",
                project=project)
    else:
        process = subprocess.Popen('git clone "%s" "%s"' % (project.git_repo, project.base_directory), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

        response = process.communicate()[0]

        Notification.objects.create(status="success" if not process.returncode else "error",
                summary="Cloning '%s' %s" % (
                    project.name, "success" if not process.returncode else "error"),
                message=response,
                project=project,
                notification_type="GITCLONE",
                )

    if project.project_type == "buildout":
        queue_job('BOOTSTRAP', project_id=project_id)

@command("GITPULL")
def pull_repo(project_id):
    """Run git pull in the base directory to update from the default origin"""
    project = Project.objects.get(id=project_id)
    print("pulling repo for %s" % project.name)

    process = subprocess.Popen('git pull', cwd=project.base_directory,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

    response = process.communicate()[0]

    Notification.objects.create(status="success" if not process.returncode else "error",
            summary="Pulling '%s' %s" % (
                project.name, "success" if not process.returncode else "error"),
            message=response,
            project=project)

# Django commands
@command("SYNCDB")
def syncdb(project_id):
    """run django syncdb in the project directory"""
    project = Project.objects.get(id=project_id)
    print("running syncdb for %s" % project.name)

    process = subprocess.Popen('bin/django syncdb --noinput', cwd=project.base_directory,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

    response = process.communicate()[0]

    Notification.objects.create(status="success" if not process.returncode else "error",
            summary="Syncdb '%s' %s" % (
                project.name, "success" if not process.returncode else "error"),
            message=response,
            project=project)

@command("STARTAPP")
def startapp(project_id, app_name):
    """Start a new app in the django project"""
    project = Project.objects.get(id=project_id)
    print("running startapp %s for %s" % (app_name, project.name))

    process = subprocess.Popen('bin/django startapp %s' % app_name,
            cwd=project.base_directory, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, shell=True)

    response = process.communicate()[0]

    Notification.objects.create(status="success" if not process.returncode else "error",
            summary="Startapp %s '%s' %s" % (
                app_name, project.name, "success" if not process.returncode else "error"),
            message=response,
            project=project)

@command("MIGRATE")
def migrate(project_id):
    """Run south migrate in the project directory."""
    project = Project.objects.get(id=project_id)
    print("running migrate for %s" % project.name)

    process = subprocess.Popen('bin/django migrate', cwd=project.base_directory,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

    response = process.communicate()[0]

    Notification.objects.create(status="success" if not process.returncode else "error",
            summary="Migrate '%s' %s" % (
                project.name, "success" if not process.returncode else "error"),
            message=response,
            project=project)

@command("EDIT")
def edit(project_id):
    """Open the user's favourite editor"""
    project = Project.objects.get(id=project_id)
    print("running edit for %s" % project.name)

    terminal_path = Preference.objects.get_preference("terminal_path")
    editor_path = Preference.objects.get_preference("editor_path")
    command = editor_path + ' buildout.cfg'

    if terminal_path:
        if '#s' in terminal_path:
            command = terminal_path.replace('#s', editor_path)
    process = subprocess.Popen(command + ' &', cwd=project.base_directory,
        shell=True, close_fds=True)

    process.communicate()

@command("VIRTUALENV")
def virtualenv(project_id):
    """Run virtualenv in the project directory"""
    project = Project.objects.get(id=project_id, pipproject__isnull=False)
    print "Running virtualenv for %s" % project.name

    process = subprocess.Popen('virtualenv --no-site-packages %s' % (
        project.pipproject.virtualenv_path), cwd=project.base_directory,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

    response = process.communicate()[0]

    Notification.objects.create(status="success" if not process.returncode else "error",
            summary="Virtualenv '%s' %s" % (
                project.name, "success" if not process.returncode else "error"),
            message=response,
            project=project)

@command("PIPINSTALL")
def virtualenv(project_id):
    """Run pip install in the project directory"""
    project = Project.objects.get(id=project_id, pipproject__isnull=False)
    print "Running pip install for %s" % project.name

    command = "source %s ; pip install -r requirements.txt" % (
            os.path.join(project.pipproject.virtualenv_path, 'bin', 'activate'))

    process = subprocess.Popen(command, cwd=project.base_directory,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

    response = process.communicate()[0]

    Notification.objects.create(status="success" if not process.returncode else "error",
            summary="pip install '%s' %s" % (
                project.name, "success" if not process.returncode else "error"),
            message=response,
            project=project)
