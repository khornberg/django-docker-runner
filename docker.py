from django.db import connections
try:
    from django_nose.runner import NoseTestSuiteRunner
except ImportError:
    pass
import docker


class DockerNoseRunner(NoseTestSuiteRunner):

    def __init__(self, *args, **kwargs):
        try:
            self.client = docker.Client(base_url='unix://var/run/docker.sock')
        except Exception as e:
            print('init error', e)
        return super(NoseTestSuiteRunner, self).__init__(args, kwargs)

    def setup_databases(self):
        for a in connections:
            c = connections[a]

            engine = c.settings_dict.get('ENGINE', '')
            if 'postgres' in engine:
                name, password, user, port, host = self.setup_postgres(c)

            c.settings_dict['PORT'] = port
            c.settings_dict['USER'] = user
            c.settings_dict['PASSWORD'] = password
            c.settings_dict['NAME'] = name
            c.settings_dict['HOST'] = host

            return super(NoseTestSuiteRunner, self).setup_databases()

    def teardown_databases(self, *args, **kwargs):
        super(NoseTestSuiteRunner, self).teardown_databases(*args, **kwargs)
        self.client.stop(self.container)
        self.client.remove_container(self.container)
        return

    def setup_postgres(self, connection):
        name = connection.settings_dict.get('NAME', 'postgres-django-docker-runner')
        password = connection.settings_dict.get('PASSWORD', '')
        user = connection.settings_dict.get('USER', name)
        port = connection.settings_dict.get('PORT', 5432)
        port = 5432 if port == '' else port
        host = connection.settings_dict.get('HOST', '127.0.0.1')
        host = '127.0.0.1' if host in ['localhost', ''] else host  # do not use localhost socket
        try:
            self.container = self.client.create_container(
                image='postgres:9.4',
                name='{}_docker'.format(name),
                environment={
                    'POSTGRES_PASSWORD': password,
                    'POSTGRES_USER': user,
                },
                host_config=self.client.create_host_config(port_bindings={port: port})
            )
            self.client.start(self.container)
            print('Starting database...')
            # Hack to know when postgress is actually ready to accept connections
            n = 0
            for line in self.client.logs(container=self.container, stream=True):
                log = line.decode('utf-8')
                # print(log)
                if 'LOG:  autovacuum launcher started' in log:
                    if n is 1:
                        break
                    n += 1
        except Exception as e:
            print('>>>>>>>>>>>>>>>>>>', e)

        return name, password, user, port, host
