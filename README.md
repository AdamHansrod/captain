## What is it?

Captain is an API that can be used to start and stop a [slug](https://devcenter.heroku.com/articles/slug-compiler) on a cluser of nodes.
Captain aims to dogfood itself, meaning it can be deployed and managed by itself after an initial bootstrap.

## Why did we write it?

In an environment where slugs are the deployment method Docker or LXC become an implementation detail.
Captain abstracts away the need to talk a low level API and replaces it with a simpler slug specific API.

## How do we run it?

The recomended way to run captain is as a slug using captan but it can be run standalone, which is also the easiest way to bootstrap it as a slug. Something like [Flynns slugbuilder](https://github.com/flynn-archive/slugrunner) can be used to build slugs.
At a minimum it needs envrionments of `DOCKER_NODES` set to a comma separated list of the http uris for Docker on each app server, `SLUG_RUNNER_COMMAND` set to `"start web"`, `SLUG_RUNNER_IMAGE` set to `"flynn/slugrunner"` and `PORT` set to the port to listen on.

## The API

Running instances:
```
$ curl captain.service/instances/
[
    {
        "app": "random-backend", 
        "environment": {
            "HMRC_CONFIG": "", 
            "JAVA_OPTS": "-Xmx256m -Xms256m"
        }, 
        "id": "888f02560d34f36333fc17692eb27a4c4f9e2b1e2cc50724846cd83bec0a4450", 
        "node": "app-1", 
        "port": 49490, 
        "slots": 2, 
        "version": "57"
    }, 
    {
        "app": "random-frontend", 
        "environment": {
            "BACKEND": "random-backend",
            "DEBUG": "true",
            "JAVA_OPTS": "-Xmx256m -Xms256m"
        }, 
        "id": "884ffeaf8d85b6438c9eef1216aa3e12a5cd090f895be81cdac7408c32189608", 
        "node": "app-2", 
        "port": 49489,
        "slots": 2, 
        "version": "47"
    }
]
```

Stop an instance
```
$ curl -XDELETE captain.service/instances/884ffeaf8d85b6438c9eef1216aa3e12a5cd090f895be81cdac7408c32189608
```

Start an instance
```
$ curl -H "Content-Type: application/json" -d '
{
    "app": "random-frontend", 
    "environment": {
        "BACKEND": "random-backend",
        "DEBUG": "false",
        "JAVA_OPTS": "-Xmx256m -Xms256m"
    }, 
    "node": "app-2", 
    "slots": 2, 
    "version": "47"
}' captain.service/instances/
```

Check how many free slots each node in your cluster has
```
$ curl captain.service/nodes/
[
    {
        "id": "app-2", 
        "slots": {
            "free": 32, 
            "total": 110, 
            "used": 78
        }
    }, 
    {
        "id": "app-1", 
        "slots": {
            "free": 22, 
            "total": 110, 
            "used": 88
        }
    }
]
```
Captain will return an over capacity error when deploying to a full app server.

## Working on Captain

To install a venv and run tests easily:

```
$ ./jenkins.sh
```

To setup the venv:

```
$ virtualenv captain-venv
$ source captain-venv/bin/activate
```

To run the tests (After completing the above setup):

```
$ nosetests --with-xunit --xunit-file=target/nosetests.xml --with-xcover \
    --xcoverage-file=target/coverage/coverage.xml --cover-package=captain \
    --cover-erase --cover-html-dir=target/coverage --cover-html
```
