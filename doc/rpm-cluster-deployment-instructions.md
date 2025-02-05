# Deploying Kaltura Clusters

Below are **RPM** based instructions for deploying Kaltura Clusters.    
Refer to the [All-In-One Kaltura Server Installation Guide](https://github.com/kaltura/platform-install-packages/blob/master/doc/install-kaltura-redhat-based.md) for more notes about deploying Kaltura in RPM supported environments.    
Refer to the [Deploying Kaltura Clusters Using Chef](https://github.com/kaltura/platform-install-packages/blob/master/doc/rpm-chef-cluster-deployment.md) for automated Chef based deployments.

### Instructions here are for a cluster with the following members:

* [Load Balancer](#apache-load-balancer)
* [NFS server](#the-nfs-server)
* [MySQL Database](#the-mysql-database)
* [Sphinx Indexing](#the-sphinx-indexing-server)
* [Front servers](#the-front)
* [Batch servers](#the-batch)
* [DWH server](#the-datawarehouse)
* [Nginx VOD server](#nginx-vod-server)
* [Streaming Server](#the-streaming-server)
* [Upgrade Kaltura](#upgrade-kaltura)
* [Platform Monitoring](#platform-monitoring)
* [Backup and Restore](#backup-and-restore-practices)

### Before You Get Started Notes
* If you see a `#` at the beginning of a line, this line should be run as `root`.
* Please review the [frequently answered questions](https://github.com/kaltura/platform-install-packages/blob/master/doc/kaltura-packages-faq.md) document for general help before posting to the forums or issue queue.
* All post-install scripts accept answers-file as parameter, this can used for silent-automatic installs.
* For a cluster install, it is very important to pass an [answer file](https://github.com/kaltura/platform-install-packages/blob/master/doc/kaltura.template.ans) to each script because otherwise, the MySQL 'kaltura' passwd is autogenerated by the installer. This is fine for a standalone server but for a cluster, passwd must be the same on all. 
* [Kaltura Inc.](http://corp.kaltura.com) also provides commercial solutions and services including pro-active platform monitoring, applications, SLA, 24/7 support and professional services. If you're looking for a commercially supported video platform  with integrations to commercial encoders, streaming servers, eCDN, DRM and more - Start a [Free Trial of the Kaltura.com Hosted Platform](http://corp.kaltura.com/free-trial) or learn more about [Kaltura' Commercial OnPrem Edition™](http://corp.kaltura.com/Deployment-Options/Kaltura-On-Prem-Edition). For existing RPM based users, Kaltura offers commercial upgrade options.

##### iptables and ports
Kaltura requires certain ports to be open for proper operation. [See the list of required open ports](https://github.com/kaltura/platform-install-packages/blob/master/doc/kaltura-required-ports.md).   


##### Disable SELinux
This is REQUIRED on all machines, currently Kaltura can't run properly with SELinux.
``` 
setenforce permissive
# To verify SELinux will not revert to enabled next restart:
# Edit /etc/selinux/config
# Set SELINUX=permissive
# Save /etc/selinux/config
```

##### Note about SSL certificates

You can run Kaltura with or without SSL (state the correct protocol and certificates during the installation).  
It is recommended that you use a properly signed certificate and avoid self-signed certificates due to limitations of various browsers in properly loading websites using self-signed certificates.    
You can generate a free valid cert using [http://cert.startcom.org/](http://cert.startcom.org/).    
To verify the validity of your certificate, you can then use [SSLShoper's SSL Check Utility](http://www.sslshopper.com/ssl-checker.html).  

Depending on your certificate, you may also need to set the following directives in `/etc/httpd/conf.d/zzzkaltura.ssl.conf`: 
```
SSLCertificateChainFile
SSLCACertificateFile
```

##### Configure your email server and MTA - REQUIRED
To achieve proper system operation and get email notifications, account activation emails, password changes, etc. all Kaltura machines in your cluster should have a functional email server. This is also ideal for monitoring purposes.   

By default Amazon Web Services (AWS) EC2 machines are blocked from sending email via port 25. For more information see [this thread on AWS forums](https://forums.aws.amazon.com/message.jspa?messageID=317525#317525).  
Two working solutions to the AWS EC2 email limitations are:

* Using SendGrid as your mail service ([setting up ec2 with Sendgrid and postfix](http://www.zoharbabin.com/configure-ssmtp-or-postfix-to-send-email-via-sendgrid-on-centos-6-3-ec2)).
* Using [Amazon's Simple Email Service](http://aws.amazon.com/ses/). 

### Apache Load Balancer

Load balancing is recommended to scale your front and streaming server (e.g. Red5, Wowza) machines.   
To deploy an Apache based load balancer, refer to the [Apache Load Balancer configuration file example](https://github.com/kaltura/platform-install-packages/blob/master/doc/apache_balancer.conf).   
This example config uses the `proxy_balancer_module` and `proxy_module` Apache modules to setup a simple Apache based load balancer (refer to official docs about [proxy_balancer_module](http://httpd.apache.org/docs/2.2/mod/mod_proxy_balancer.html) and [proxy_module](http://httpd.apache.org/docs/2.2/mod/mod_proxy.html) to learn more).    
To configure the load balancer on your environment: 

1. Replace all occurances of `balancer.domain.org` with the desired hostname for the load balanacer (the main end-point your end-users will reach).
1. Replace all occurances of `node0.domain.org` with the first front machine hostname and `node1.domain.org` with the second front machine hostname.    
1. In order to add more front machines to the load balancing poll, simply clone the nodeX.domain.org lines and change to the hostnames of the new front machines and the route.

Note that the port in the example file is 80 (standard HTTP port), feel free to change it if you're using a non-standard port.

### HAProxy Load Balancer

A simpler load balancer called HAProxy can also be configured **instead** of Apache load balancer, after installing it refer to the [configuration file example](https://github.com/kaltura/platform-install-packages/blob/master/doc/haproxy.cfg).
To configure the load balancer on your environment:

1. Replace all occurances of `node0.domain.org` with the first front machine hostname and `node1.domain.org` with the second front machine hostname.
2. In order to add more front machines to the load balancing poll, simply clone the nodeX.domain.org line and change to the hostnames of the new front machines and change the server cookie ID (after the cookie keyword).

If you want to have logging for HAProxy with the sample configuration, add the following lines to the syslog/rsyslog configuration (for rsyslog you can put this in the file /etc/rsyslog.d/haproxy.conf):
```
$ModLoad imudp
$UDPServerRun 514

local0.* -/var/log/haproxy_0.log
local1.* -/var/log/haproxy_1.log
```

And restart syslog/rsyslog:
```
restart rsyslog
```

##### SSL Offloading on a Load Balancer
Load Balancers have the ability to perform SSL offloading (aka [SSL Acceleration](http://en.wikipedia.org/wiki/SSL_Acceleration)). Using SSL offloading can dramatically reduce the load on the systems by only encrypting the communications between the Load Balancer and the public network while communicating on non-encrypted http with the internal network (in Kaltura's case, between the Load Balancer and the front machines).

Kaltura recommends that you utilize offloading. I this case, you will only need to deploy the SSL certificates on your Load Balancer.    
However, if network requirements dictates (noting that this will hurt performance) Kaltura will work just as well with double encryption - But be sure to deploy the SSL certificates on the front machines as well as the load balancer.

##### Self-Balancing Components
The following server roles should not be load-balanced:

* Batch machines are very effective at scaling on themselves, by simply installing more batch servers in your cluster they will seamlessly register against the DB on their own and begin to take jobs independantly.
* Sphinx machines are balanced in the Kaltura application level.
* See below the notes regarding MySQL replication and scaling.

### The NFS server
The NFS is the shared network storage between all machines in the cluster. To learn more about NFS read [this wikipedia article about NFS](http://en.wikipedia.org/wiki/Network_File_System).
```
# yum install nfs-utils-lib ntp
# chkconfig nfs on
# chkconfig ntp on
# service ntpd start
# service rpcbind start
# service nfs start
# mkdir -p /opt/kaltura/web
```
Edit `/etc/exports` to have the desired settings, for example:
`/opt/kaltura/web *(rw,sync,no_root_squash)`

Edit `/etc/idmapd.conf` and add your domain, for example:
`Domain = kaltura.dev`
```
# /etc/init.d/rpcidmapd restart
```

Note that you may choose different NFS settings which is fine so long as:
* the kaltura and apache user are both able to write to this volume
* the kaltura and apache user are both able create files with them as owners. i.e: do not use all_squash as an option.

Then set priviliges accordingly:
```
# groupadd -r kaltura -g7373
# useradd -M -r -u7373 -d /opt/kaltura -s /bin/bash -c "Kaltura server" -g kaltura kaltura
# groupadd -g 48 -r apache
# useradd -r -u 48 -g apache -s /sbin/nologin -d /var/www -c "Apache" apache
# usermod -a -G kaltura apache
# chown -R kaltura.apache /opt/kaltura/web
# chmod 775 /opt/kaltura/web
# exportfs -a
```

Before continuing, run the following test on all front and Batch machines:

```
# yum install telnet
# telnet NFS_HOST 2049
Should return something similar to:
Trying 166.78.104.118...
Connected to kalt-nfs0.
Escape character is '^]'.
```


### The MySQL Database
```
# rpm -Uhv http://installrepo.kaltura.org/releases/kaltura-release.noarch.rpm
# yum install mysql-server kaltura-postinst ntp 
# /opt/kaltura/bin/kaltura-mysql-settings.sh
# mysql_secure_installation
# chkconfig ntp on
# service ntpd start
```
**Make sure to say Y** for the `mysql_secure_installation` install, and follow through all the mysql install questions before continuing further.    
Failing to properly run `mysql_secure_installation` will cause the kaltura mysql user to run without proper permissions to access your mysql DB.    
```
# mysql -uroot -pYOUR_DB_ROOT_PASS
mysql> GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' IDENTIFIED BY 'YOUR_DB_ROOT_PASS' WITH GRANT OPTION;
mysql> FLUSH PRIVILEGES;
```
Note that in the statement above, MySQL is being open for access as root from ALL machines, depending on your setup, you may want to limit it further to allow only members of your Kaltura cluster.
Remote root user should have an access to the mysql DB during the installation of the front and batch servers.
After the Kaltura cluster installation is done, you may want to remove the root access for security reasons, it will not longer be needed for the platform to operate as it will be using the 'kaltura' user to connect this point.
 
Before continuing the deployment, run the following test on all front, Sphinx and Batch machines:

```
# mysql -uroot -hMYSQL_HOST -p 

If the connection fails, you may have a networking issue, run:

# yum install telnet
# telnet MYSQL_HOST 3306
Should return something similar to:
Trying 166.78.104.118...
Connected to kalt-mysql0.
Escape character is '^]'.

If that works, then the block is at the MySQL level and not in the networking, make sure this is resolved before continuing.

```

#### MySQL Replication and Scaling
Scaling MySQL is an art on it's own. There are two aspects to it: Replication (having data live in more than one MySQL server for redundency and read scaling) and setting up read slaves.    

##### MySQL Replication 
To assist with MySQL master-slave replication, please refer to the [`kaltura-mysql-replication-config.sh` script](https://github.com/kaltura/platform-install-packages/blob/master/RPM/scripts/postinst/kaltura-mysql-replication-config.sh).    
To run the replication configuration script, note the following:

* The MySQL server you've installed during the Kaltura setup is your master. 
* After completing the Kaltura setup, simply run `kaltura-mysql-replication-config.sh dbuser dbpass master_db_ip master` from the master machine
* Follow the same instructions above to install every slave machine, and run the following command: `kaltura-mysql-replication-config.sh dbuser dbpass master_db_ip slave`

To read more and learn about MySQL Master-Slave configuration, refer to the official MySQL documentation:  

* [Setting the Replication Master Configuration](https://dev.mysql.com/doc/refman/5.0/en/replication-howto-masterbaseconfig.html)
* [Setting the Replication Slave Configuration](https://dev.mysql.com/doc/refman/5.0/en/replication-howto-slavebaseconfig.html)

##### MySQL Read Scaling 
After configuring your environment MySQL replication, in order to distribute the READ load, you can also configure Kaltura to 'load-balance' MySQL reads between the master and 2 additional slave machines.    
Note that you can only have one machine for writes - this is your master.    
Follow these steps to 'load-balance' READ operations between the MySQL servers:  

* Edit `/opt/kaltura/app/configurations/db.ini`
* Find the following section, this is your MASTER (replace the upper case tokens with real values from your network hosts):

```
propel.connection.hostspec = MASTER_DB_HOST
propel.connection.user = kaltura
propel.connection.password = KALTURA_DB_USER_PASSWORD
propel.connection.dsn = "mysql:host=MASTER_DB_HOST;port=3306;dbname=kaltura;"
```

* The sections that will follow will look the same, but after the key `propel`, you'll notice the numbers 2 and 3. These are the second and third MySQL servers that will be used as SLAVES (replace the upper case tokens with real values from your network hosts):

```
propel2.connection.hostspec = SECOND_DB_HOST
propel2.connection.user = kaltura
propel2.connection.password = KALTURA_DB_USER_PASSWORD
propel2.connection.dsn = "mysql:host=SECOND_DB_HOST;port=3306;dbname=kaltura;"

propel3.connection.hostspec = THIRD_DB_HOST
propel3.connection.user = kaltura
propel3.connection.password = KALTURA_DB_USER_PASSWORD
propel3.connection.dsn = "mysql:host=THIRD_DB_HOST;port=3306;dbname=kaltura;"
```

In addition, you should also set up [query cache](https://github.com/kaltura/platform-install-packages/blob/master/doc/query_cache.md) 

When query cache is enabled, the server intelligently chooses between master / slave. Anything that was not changed recently is read from slave and otherwise from master.


### The Sphinx Indexing Server
```
# rpm -Uhv http://installrepo.kaltura.org/releases/kaltura-release.noarch.rpm
# yum install kaltura-sphinx
# /opt/kaltura/bin/kaltura-sphinx-config.sh
```

It is strongly recommended that you install at least 2 Sphinx nodes for redundancy.

It is recommended that Sphinx will be installed on its own dedicated machine. However, if needed, Sphinx can be coupled with a front machine in low-resources clusters.

After installing the first cluster node, obtain the auto generated file placed under /tmp/kaltura_*.ans, replace relevant values and use it for the installation of the remaining nodes.

### The first Front node

####NOTES: 
0. /opt/kaltura/bin/kaltura-db-config.sh and kaltura-widgets kaltura-html5lib which are installed on the web mount only need to run on the first node.
1. Before starting, make sure the balancer does not direct to the second front node since it's not yet installed.


Front in Kaltura represents the machines hosting the user-facing components, including the Kaltura API, the KMC and Admin Console, MediaSpace and all client-side widgets. 
```
# rpm -Uhv http://installrepo.kaltura.org/releases/kaltura-release.noarch.rpm
# yum install kaltura-postinst
# /opt/kaltura/bin/kaltura-nfs-client-config.sh <NFS host> <domain> <nobody-user> <nobody-group>
# yum install kaltura-front kaltura-widgets kaltura-html5lib kaltura-html5-studio kaltura-clipapp 
# /opt/kaltura/bin/kaltura-front-config.sh
# . /etc/kaltura.d/system.ini
Make certain this call returs 200
# curl -I $SERVICE_URL/api_v3/index.php
Output should be similar to:
HTTP/1.1 200 OK
Date: Sat, 14 Mar 2015 17:59:40 GMT
Server: Apache/2.2.15 (CentOS)
X-Powered-By: PHP/5.3.3
X-Kaltura: cached-dispatcher,cache_v3-baf38b7adced7cbac99d06b983aaf654,0.00048708915710449
Access-Control-Allow-Origin: *
Expires: Sun, 19 Nov 2000 08:52:00 GMT
Cache-Control: no-store, no-cache, must-revalidate, post-check=0, pre-check=0
Pragma: no-cache
Vary: Accept-Encoding
X-Me: $SERVICE_URL
Connection: close
Content-Type: text/xml

# /opt/kaltura/bin/kaltura-db-config.sh <mysql-hostname> <mysql-super-user> <mysql-super-user-passwd> <mysql-port> [upgrade]
```

### Secondary Front nodes
Front in Kaltura represents the machines hosting the user-facing components, including the Kaltura API, the KMC and Admin Console, MediaSpace and all client-side widgets. 
```
# rpm -Uhv http://installrepo.kaltura.org/releases/kaltura-release.noarch.rpm
# yum install kaltura-postinst
# /opt/kaltura/bin/kaltura-nfs-client-config.sh <NFS host> <domain> <nobody-user> <nobody-group>
# yum install kaltura-front kaltura-html5-studio kaltura-clipapp
# /opt/kaltura/bin/kaltura-front-config.sh
```
**NOTE: you can now configure the balancer to have the node in its pull.**

### The Batch node
Batch in Kaltura represents the machines running all async operations. To learn more, read: [Introduction to Kaltura Batch Processes](http://knowledge.kaltura.com/node/230).

It is strongly recommended that you install at least 2 batch nodes for redundancy.

```
# rpm -Uhv http://installrepo.kaltura.org/releases/kaltura-release.noarch.rpm
# yum install kaltura-postinst
# /opt/kaltura/bin/kaltura-nfs-client-config.sh <NFS host> <domain> <nobody-user> <nobody-group>
# yum install kaltura-batch
# /opt/kaltura/bin/kaltura-batch-config.sh
```

#### Note about batch scaling
Adding more batch machines is simple and easy! Due to the distributed architecture of batches in Kaltura, batches are independantly registering themselves against the Kaltura cluster, and independantly assume jobs from the queue.   
In order to scale your system batch capacity, simply install new bacth machines in the cluster.   
When running the `kaltura-batch-config.sh` installer on the batch machine, the installer replaces the config tokens and sets a uniq ID per batch. Then seamlessly, the batch registers against the DB and starts taking available jobs.

### The DataWarehouse
The DWH is Kaltura's Analytics server.
```
# rpm -Uhv http://installrepo.kaltura.org/releases/kaltura-release.noarch.rpm
# yum install kaltura-dwh kaltura-postinst
# /opt/kaltura/bin/kaltura-nfs-client-config.sh <NFS host> <domain> <nobody-user> <nobody-group>
# /opt/kaltura/bin/kaltura-dwh-config.sh
```

### Nginx VOD Server
This is used to achieve on-the-fly repackaging of MP4 files to DASH, HDS, HLS, MSS.

For more info about its features see:
https://github.com/kaltura/nginx-vod-module/

Installation:
```
yum install kaltura-nginx
/opt/kaltura/bin/kaltura-nginx-config.sh
```

Note: Currently, the Nginx VOD module does not support integration with Kaltura over HTTPs, only HTTP is supported. 

### The Streaming Server
To achieve RTMP/t/e playback, Live streaming, webcam recording, and etc. Kaltura requires a streaming server.   
You can use the open source Red5 server which is available as a Kaltura package too, and follow the steps below.   

To install Red5:
```
# rpm -Uhv http://installrepo.kaltura.org/releases/kaltura-release.noarch.rpm
# yum install kaltura-red5 kaltura-postinst
```

* Visit on your browser: `http://your_red5_server_hostname:5080` (This will load Red5's Web Admin)
* Click 'Install a ready-made application'
* Check 'OFLA Demo' and click 'Install'
* Edit `/usr/lib/red5/webapps/oflaDemo/index.html` and replace `localhost` with your actual Red5 hostname or IP
* Test OflaDemo by visiting `http://your_red5_server_hostname:5080/oflaDemo/` and playing the sample videos
* Run: `# /opt/kaltura/bin/kaltura-red5-config.sh`

Kaltura supports commercial encoders and streaming servers too. For more information about commercial alternatives see [Kaltura Commercial OnPrem Edition™](http://corp.kaltura.com/Deployment-Options/Kaltura-On-Prem-Edition).

### Upgrade Kaltura
On the first batch or front node only:
```
## This operates on the DB and hence only needs to be done one. It requires the kaltura-base package and so must be run on a node that has it installed.
# /opt/kaltura/bin/kaltura-db-update.sh
```


On front machines:
```
# kaltura-base-config.sh [/path/to/ans/file]
# kaltura-front-config.sh [/path/to/ans/file]
```

On batch machines:
```
# kaltura-base-config.sh [/path/to/ans/file]
# kaltura-batch-config.sh [/path/to/ans/file]
```

On sphinx machines:
```
# kaltura-base-config.sh [/path/to/ans/file]
# kaltura-sphinx-config.sh [/path/to/ans/file]
```

### Platform Monitoring
Please refer to the [Setting up Kaltura platform monitoring guide](https://github.com/kaltura/platform-install-packages/blob/master/doc/platform-monitors.md).

### Backup and Restore Practices
Backup and restore is quite simple. Make sure that the following is being regularly backed up:

* MySQL dump all Kaltura DBs (`kaltura`, `kaltura_sphinx_log`, `kalturadw`, `kalturadw_bisources`, `kalturadw_ds`, `kalturalog`). You can use the following `mysqldump` command:
`# mysqldump -h$DBHOST -u$DBUSER -p$DBPASSWD -P$DBPORT --routines --single-transaction $TABLE_SCHEMA $TABLE | gzip > $OUT/$TABLE_SCHEMA.$TABLE.sql.gz`
* The `/opt/kaltura/web` directory, which includes all of the platform generated and media files.
* The `/opt/kaltura/app/configurations` directory, which includes all of the platform configuration files.

Then, if needed, to restore the Kaltura server, follow these steps:

* Install the **same version** of Kaltura on a clean machine
* Stop all services
* Copy over the web and configurations directories
* Import the MySQL dump
* Restart all services
* Reindex Sphinx with the following commands: 

```
# rm -f /opt/kaltura/log/sphinx/data/*
# cd /opt/kaltura/app/deployment/base/scripts/
# for i in populateSphinx*;do php $i >/tmp/$.log;done
```
