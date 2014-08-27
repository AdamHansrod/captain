## Simple Usage instructions
To run tests easily:

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

##The API

-------------------------------------------------
 Title            Request All Apps               
----------------- -------------------------------
 URL              /apps/                         

 Methods          GET                            

 URL Params       None                           

 Request Body     None                           

 Success Response Code: 200                      
                  Content-Type: application/json 

 Error Response   Code: 5XX                      

 Request Example  Request:
                  curl /apps/
                  Response:
                  {"<app name>":
                    [
                      {  "app": "<app name>",
                          "id": "<container ID>",
                          "ip": "<docker host IP>",
                          "node": "<docker hostname>",
                          "port": <exposed port>,
                          "running": <boolean>,
                          "version": "<application version>"
                      }
                    ]
                  }
-------------------------------------------------




