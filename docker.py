from django_nose.runner import NoseTestSuiteRunner
from django.db import connections
from django.conf import settings

import docker


class DockerRunner(object):
    # maybe subclass in an init after determining if nose or stock django should be used
    def __init__(self, *args, **kwargs):
        if 'django_nose' in settings.INSTALLED_APPS:
            DockerNoseRunner(args, kwargs)
        return None


class DockerNoseRunner(NoseTestSuiteRunner):

    def __init__(self, *args, **kwargs):
        try:
            self.client = docker.Client(base_url='unix://var/tmp/docker.sock')
        except Exception as e:
            print('init error', e)
        return super(NoseTestSuiteRunner, self).__init__(args, kwargs)

    def setup_databases(self):
        for a in connections:
            c = connections[a]

            name = c.settings_dict.get('NAME', 'name')
            password = c.settings_dict.get('PASSWORD', '')
            user = c.settings_dict.get('USER', name)
            port = c.settings_dict.get('PORT', 5432)

            c.settings_dict['PORT'] = port
            c.settings_dict['USER'] = user
            c.settings_dict['PASSWORD'] = password
            c.settings_dict['NAME'] = name

            try:
                self.container = self.client.create_container(
                    image='postgres:9.4',
                    name=name,
                    environment={
                        'POSTGRES_PASSWORD': password,
                        'POSTGRES_USER': user,
                    },
                    host_config=self.client.create_host_config(port_bindings={port: port})
                )
                self.client.start(self.container)
                print('Waiting on database to start...')
                n = 0
                for line in self.client.logs(container=self.container, stream=True):
                    log = line.decode('utf-8')
                    print(log)
                    if 'LOG:  autovacuum launcher started' in log:
                        if n is 1:
                            break
                        n += 1
            except Exception as e:
                print('>>>>>>>>>>>>>>>>>>', e)

            return super(NoseTestSuiteRunner, self).setup_databases()

    def teardown_databases(self, *args, **kwargs):
        super(NoseTestSuiteRunner, self).teardown_databases(*args, **kwargs)
        self.client.stop(self.container)
        self.client.remove_container(self.container)
        return
