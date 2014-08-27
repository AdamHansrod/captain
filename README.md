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

<TABLE>
<TR><TH>Title</TH><TH>Request All Apps</TH></TR>
<TR><TD>URL</TD><TD>/apps/</TD></TR>
<TR><TD>Methods</TD><TD>GET</TD></TR>                            
<TR><TD>URL Params</TD><TD>None</TD></TR>                           
<TR><TD>Request Body</TD><TD>None</TD></TR>                           
<TR><TD>Success Response</TD><TD>Code: 200<BR/>Content-Type: application/json</TD></TR> 
<TR><TD>Error Response</TD><TD>Code: 5XX</TD></TR>                      
<TR><TD>Request Example</TD><TD>Request:<BR/>
                  curl /apps/<BR/>
                  Response:<BR/>
<PRE>{"app name":
  [
    {  "app": "app name",
      "id": "container ID",
      "ip": "docker host IP",
      "node": "docker hostname",
      "port": exposed port,
      "running": boolean,
      "version": "application version"
    }
  ]
}</PRE></TD></TR>
</TABLE>




