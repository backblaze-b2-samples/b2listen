# Backblaze B2 Listener

The Backblaze B2 Listener, "B2listen" for short, allows you to forward Backblaze B2 Event Notifications to a service listening on a local URL. B2listen uses Cloudflare's free [Quick Tunnels](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/) feature, running an instance of [cloudflared](https://github.com/cloudflare/cloudflared) to generate a random subdomain on `trycloudflare.com` and proxy traffic from that URL to the local endpoint. B2listen can modify an existing Event Notification rule to use the `trycloudflre.com` URL or create a new, temporary, rule to do so.

Note: the Event Notifications feature is currently in public preview. For information about enabling this feature, see [Automate Your Data Workflows With Backblaze B2 Event Notifications](https://www.backblaze.com/blog/announcing-event-notifications/).

## Prerequisites

You need a Backblaze B2 Account that is enabled for Event Notifications, a Backblaze B2 Bucket, and an Application Key

Follow these instructions, as necessary:

* [Create a Backblaze B2 Account](https://www.backblaze.com/sign-up/cloud-storage).
* [Join the waiting list for the Event Notifications private preview](https://www.surveymonkey.com/r/ZL2X68S).
* [Create a Backblaze B2 Bucket](https://www.backblaze.com/docs/cloud-storage-create-and-manage-buckets).
* [Create an Application Key](https://www.backblaze.com/docs/cloud-storage-create-and-manage-app-keys#create-an-app-key) with access to the bucket you wish to use. The application key must have the `readBucketNotifications` and `writeBucketNotifications` capabilities.
  > If Event Notifications is enabled for your account then you can create a suitable application key using the Backblaze web UI. You cannot use application keys created before Event Notifications was enabled for your account with B2listen. 

Be sure to copy the application key as soon as you create it, as you will not be able to retrieve it later!

You will also need a local service to receive, and optionally act on, event notification messages. If you are experimenting with B2listen and don't have a suitable service, you can activate B2listen's [embedded HTTP server](#running-the-embedded-http-server) to receive and display incoming messages.

Optionally, if you wish to deliver events to multiple local services, you can use B2listen with the [Backblaze B2 Event Broker](https://github.com/backblaze-b2-samples/b2-event-broker); see [below](#using-b2listen-with-the-backblaze-b2-event-broker) for details.

## Configuration

You must set environment variables containing your Backblaze B2 application key and its ID: `B2_APPLICATION_KEY` and `B2_APPLICATION_KEY_ID` respectively. You can set these in the environment, in a `.env` file, or on the Docker command-line.

This repo includes a template file, `.env.template`. You can copy it to `.env`, then edit it as follows:
```dotenv
B2_APPLICATION_KEY_ID=Your-Application-Key-ID
B2_APPLICATION_KEY=Your-Application-Key
```

When you're done, .env should look like this:
```dotenv
B2_APPLICATION_KEY_ID=004qlekmvpwemrt000000009e
B2_APPLICATION_KEY=K004JEKEUTGLKEJFKLRJHTKLVCNWURM
```

If you are using B2listen with the Backblaze B2 Event Broker, you will also need to configure an environment variable, `SIGNING_SECRET`, containing the shared signing secret. This must be the same as the signing secret in your Event Notifications rule(s).

Note: do not use quotes in the `.env` file. Docker does not recognize quoted variable values, and will include the quotes in the values of the variables.

## Usage

The most convenient way to use B2listen is via Docker, but you can also run the Python app directly.

In either case, you can run B2listen with the `--help` argument to show top level usage information, and specify a command for more detail. For example, in Docker:

```console
% docker run ghcr.io/backblaze-b2-samples/b2listen:latest --help                                  
usage: b2listen.py [-h] [--loglevel {debug,info,warn,error,critical}]
                   [--cloudflared-command CLOUDFLARED_COMMAND]
                   {listen,cleanup,version} ...

Deliver Event Notifications for a given bucket to a local service.

For more details on one command:

b2listen.py <command> --help
...

% python -m b2listen listen --help
usage: b2listen listen [-h] (--url URL | --run-server) [--rule-name RULE_NAME]
                       [--event-types [EVENT_TYPES ...]] [--prefix PREFIX]
                       [--custom-headers [CUSTOM_HEADERS ...]]
                       [--signing-secret SIGNING_SECRET]
                       [--cloudflared-loglevel {debug,info,warn,error,fatal}]
                       bucket-name
...
```

## Running B2listen in Docker

The Docker image, `ghcr.io/backblaze-b2-samples/b2listen`, bundles the `cloudflare` executable with the B2listen Python application and the Python runtime. The image supports the `linux/amd64` and `linux/arm64` platforms, so it will run on Docker hosts with either Intel/AMD or Apple Silicon CPUs.

You can pass your application key and its ID to the Docker run command using the `--env-file` argument and your `.env` file, as shown below, or by setting a `--env` argument for each value.

To create a new, temporary, event notification rule and proxy event notification messages to a local service listening on port 8080 on the Docker host, use the `listen` command, specify your bucket name, and set `--url` argument to http://host.docker.internal:8080.

> Note: `host.docker.internal` is a special hostname that resolves to the Docker host. If you use a hostname such as `localhost` or `127.0.0.1` when B2listen is running in Docker, it will resolve to the Docker container's own network interface.

```console
% docker run --env-file .env ghcr.io/backblaze-b2-samples/b2listen listen my-bucket \
    --url http://host.docker.internal:8080
INFO:b2listen:Tunnel URL: https://alfred-dakota-vbulletin-comfort.trycloudflare.com
INFO:b2listen:Creating rule with name "--autocreated-b2listen-2024-07-22-22-18-03-448423--"
INFO:b2listen:Registered tunnel connection connIndex=0 connection=b7ebd606-8da5-4273-af3d-472ec741887c event=0 ip=198.41.200.13 location=sjc08 protocol=quic
INFO:b2listen:Ready to deliver events to http://host.docker.internal:8080
```

Most of the examples shown in this document are run from Docker.

> You can create a short image tag as an alias for `ghcr.io/backblaze-b2-samples/b2listen`. For example:
> ```console
> % docker tag ghcr.io/backblaze-b2-samples/b2listen:latest b2listen
> ```
> Now you can use the shorter tag when running B2listen, for example:
> ```console
> % docker run --env-file .env b2listen listen --run-server my-bucket
> ```
> Note, though, that the tag refers to a specific image ID. If you pull a new version of B2listen, you will need to remove and recreate the tag if you want it to refer to the new version:
> ```console
> % docker pull ghcr.io/backblaze-b2-samples/b2listen:latest
> latest: Pulling from backblaze-b2-samples/b2listen
> 1561eceef0e7: Download complete
> 96ab28538562: Download complete
> 0b24de0f619a: Download complete
> ...
> Status: Downloaded newer image for ghcr.io/backblaze-b2-samples/b2listen:latest
> ghcr.io/backblaze-b2-samples/b2listen:latest
> % docker image rm b2listen                              
> Untagged: b2listen:latest
> % docker tag ghcr.io/backblaze-b2-samples/b2listen:latest b2listen
> ```
> 
> For clarity, this README uses the full tag.

You can also run B2listen outside Docker; see the [instructions below](#running-b2listen-outside-docker).

## Event Notification Messages

B2listen configures `cloudflared` to generate a random subdomain on `trycloudflare.com` (shown in B2listen's output) and forward messages from that endpoint to the local service URL.
When you upload a file to (or delete, or hide a file in) your Backblaze B2 Bucket, B2 sends an event notification message as an HTTP POST with JSON-formatted payload the `trycloudflare.com` URL, and `cloudflared` forwards the message to the local service URL.

## Running the Embedded HTTP Server

You can run B2listen's embedded HTTP server by passing the `--run-server` argument to the `listen` command. B2listen starts a simple HTTP server on an available port and uses its interface and port to build the local service URL:

```console
% docker run --env-file .env ghcr.io/backblaze-b2-samples/b2listen listen \
    --run-server my-bucket
INFO:b2listen.server:Starting HTTP server on 127.0.0.1:50427
INFO:b2listen:Tunnel URL: https://workforce-help-experiences-peak.trycloudflare.com
INFO:b2listen:Creating rule with name "--autocreated-b2listen-2024-07-22-22-07-32-503587--"
INFO:b2listen:Registered tunnel connection connIndex=0 connection=3812cef5-14e5-4e23-8ff7-776571db5522 event=0 ip=198.41.200.113 location=sjc07 protocol=quic
INFO:b2listen:Ready to deliver events to http://127.0.0.1:50427
...
```

The embedded HTTP server prints incoming event notification messages:

```console
...
INFO:b2listen.server:POST request,
Path: /
Headers:
Host: few-pastor-champion-netscape.trycloudflare.com
User-Agent: B2/EventNotifications
Content-Length: 628
Accept-Encoding: gzip
Cdn-Loop: cloudflare; subreqs=1
Cf-Connecting-Ip: 2605:72c0:503:42::c19
Cf-Ew-Via: 15
Cf-Ipcountry: US
Cf-Ray: 8a792e6e20de16a2-SJC
Cf-Visitor: {"scheme":"https"}
Cf-Warp-Tag-Id: b54b5e36-304f-4179-9666-b3a784237fb5
Cf-Worker: trycloudflare.com
Connection: keep-alive
Content-Type: application/json; charset=UTF-8
X-Forwarded-For: 2605:72c0:503:42::c19
X-Forwarded-Proto: https


Body:
{
  "events": [
    {
      "accountId": "15f935cf4dcb",
      "bucketId": "21a5bf29a395fc7f84dd0c1b",
      "bucketName": "my-bucket",
      "eventId": "19f154fa574c68f60ea362f8e2a4272a63aefc094889d8985740c93d2710dcbe",
      "eventTimestamp": 1721711606884,
      "eventType": "b2:ObjectCreated:Upload",
      "eventVersion": 1,
      "matchedRuleName": "--autocreated-b2listen-2024-07-22-22-13-20-312502--",
      "objectName": "images/raw/smiley.png",
      "objectSize": 23889,
      "objectVersionId": "4_z21a5bf29a395fc7f84dd0c1b_f102737ab881484be_d20240723_m051326_c004_v0402010_t0003_u01721711606612"
    }
  ]
}

127.0.0.1 - - [22/Jul/2024 22:13:28] "POST / HTTP/1.1" 200 -
```

## Creating a Temporary Event Notification Rule

By default, on startup, B2listen creates a new, temporary, rule with the following settings:

* Name with the form `--autocreated-b2listen-yyyy-MM-dd-HH-mm-ss-SSSSSS--`, for example, `--autocreated-b2listen-2024-07-22-14-52-19-118384--`
* All [event types](https://www.backblaze.com/docs/en/cloud-storage-event-notifications-reference-guide?highlight=event%20notifications#event-types) selected (`b2:ObjectCreated:*`, `b2:ObjectDeleted:*`, and `b2:HideMarkerCreated:*`)
* No prefix
* URL set to the `trycloudflare.com` endpoint, for example, `https://positions-guestbook-genius-enormous.trycloudflare.com`
* No custom headers
* No signing secret

You can use the [B2 Command-Line Tool](https://www.backblaze.com/docs/cloud-storage-command-line-tools) to inspect the temporary rule while B2listen is running:

```console
% b2 bucket notification-rule list b2://my-bucket          
FeaturePreviewWarning: Event Notifications feature is in "Private Preview" state and may change without notice. See https://www.backblaze.com/blog/announcing-event-notifications/ for details.
Notification rules for b2://my-bucket/ :
- name: --autocreated-b2listen-2024-07-22-22-41-03-388021--
  eventTypes: 
    - b2:HideMarkerCreated:*
    - b2:ObjectCreated:*
    - b2:ObjectDeleted:*
  isEnabled: true
  isSuspended: false
  objectNamePrefix: ''
  suspensionReason: ''
  targetConfiguration: 
    customHeaders: null
    hmacSha256SigningSecret: null
    targetType: webhook
    url: https://within-weight-ensemble-wanting.trycloudflare.com
```

> Note: you must use [version 3.19.0](https://github.com/Backblaze/B2_Command_Line_Tool/blob/master/CHANGELOG.md#3190---2024-04-15) or higher of the B2 Command-Line Tool to be able to manipulate event notification rules.

You can customize the temporary event notification rule's configuration via B2listen's command-line arguments. For example, to configure a temporary rule to match all 'object created' events with an object name prefix of `images/raw`, set the custom header `X-Source: B2` on event notification messages and sign messages with the signing secret `01234567890123456789012345678901`, you would use the following command-line:

```console
% docker run --env-file .env ghcr.io/backblaze-b2-samples/b2listen listen my-bucket \
    --url http://host.docker.internal:8000 \
    --event-types 'b2:ObjectCreated:*' --prefix 'images/raw' --custom-header 'X-Source: B2' \
    --signing-secret 01234567890123456789012345678901
INFO:root:Tunnel URL: https://realize-pj-reasons-pasta.trycloudflare.com
...
```

Note that the temporary rule's configuration cannot overlap with an existing rule. That is, prefixes for rules covering the same event types in the same bucket must be disjoint. The prefixes `images` and `images/raw` overlap, since an object with a name such as `images/raw/kitten.png` matched both prefixes, but the prefixes `images/raw` and `images/thumbnails` are disjoint, since there is no object name that matches both prefixes. 

If you ran the above command in the presence of an existing rule with event type `b2:ObjectCreated:*` and prefix `images`, you would receive an error message:

```console
% docker run --env-file .env ghcr.io/backblaze-b2-samples/b2listen listen my-bucket \
    --url http://host.docker.internal:8000 --event-types 'b2:ObjectCreated:*' \
    --prefix 'images/raw' --custom-header 'X-Source: B2'
INFO:b2listen:Tunnel URL: https://knight-boxing-discipline-commitment.trycloudflare.com
INFO:b2listen:Creating rule with name "--autocreated-b2listen-2024-07-22-15-38-57-094644--"
CRITICAL:b2listen:Error setting event notification rule: More than one event notification rule has overlapping prefixes (images),(images/raw) for the same event type: b2:ObjectCreated:*
```

## Using B2listen with the Backblaze B2 Event Broker

You can use B2listen with the [Backblaze B2 Event Broker](https://github.com/backblaze-b2-samples/b2-event-broker) to forward Backblaze B2 Event Notifications to multiple services listening on local URLs. Use the `--event-broker-url` argument to specify the event broker URL and, optionally, `--poll-interval` to specify the interval with which B2listen will poll the event broker to check that its subscription is active.

```console
% docker run --env-file .env ghcr.io/backblaze-b2-samples/b2listen listen my-bucket \
--rule-name my-event-rule --event-broker-url https://event-broker.acme.workers.dev \
--url http://host.docker.internal:8000 --poll-interval 10
```

The event broker receives event notification messages from Backblaze B2 and forwards them to subscribing instances of B2listen. B2listen subscribes for messages when it starts up and unsubscribes when it shuts down. If the event broker cannot successfully forward an incoming message to a subscriber, it will retry after 1, 2, 4, and 8 seconds, then, if the message could not be forwarded, terminate that subscription.

To handle situations when B2listen is temporarily offline, for example, if its VM is paused, B2 listen will periodically poll the event broker to check that its subscription is active. If B2listen determines that its subscription had been terminated, then it checks that the local service is still accessible, and, if so, creates a new subscription. If the local service is not accessible, then B2 listen displays a suitable message and tries again later:

```
INFO:subscription:Subscribed to metadaddy-tester/allEvents/04545928-b5ae-4189-b3b8-b299f3a8714d
...
WARNING:subscription:Subscription is no longer active, and client is not responding. Will try again in 30 seconds
INFO:subscription:Subscription is no longer active, but client is awake. Resubscribing.
INFO:subscription:Subscribed to metadaddy-tester/allEvents/9a26a8c6-807a-40c2-b6d4-8463895d9849
```

## Terminating B2listen

Press Ctrl-C to terminate B2listen. When B2listen exits, it deletes the temporary rule, if it created one:

```console
...
^CINFO:b2listen:Stopping cloudflared
INFO:b2listen:Deleting rule with name "--autocreated-b2listen-2024-07-23-05-59-12-711296--"
```

## Using an Existing Event Notification Rule

As an alternative to creating a temporary event notification rule, you can specify the name of an existing rule. On startup, B2listen will replace the URL in the existing rule with the `trycloudflare.com` URL.

```console
% docker run --env-file ghcr.io/backblaze-b2-samples/b2listen listen my-bucket \
    --url host.docker.internal:8000 --rule-name new-image-created
INFO:root:Tunnel URL: https://larger-interracial-william-validity.trycloudflare.com
INFO:b2listen:Modified rule with name "new-image-created"
INFO:b2listen:Old URL was https://webhook.example.com/events; new URL is https://newton-motivated-fresh-op.trycloudflare.com
...
```

On exiting, B2listen will restore the original URL to the rule.

```console
^CINFO:b2listen:Stopping cloudflared
INFO:b2listen:Modified rule with name "new-image-created"
INFO:b2listen:Old URL was https://newton-motivated-fresh-op.trycloudflare.com; new URL is https://webhook.example.com/events
```

## Cleanup

In some circumstances, B2listen may not delete the temporary rule when exiting. If this happens, the next time you run B2listen, you will see an error message:

```console
% docker run --env-file .env ghcr.io/backblaze-b2-samples/b2listen listen my-bucket \
    --url host.docker.internal:8000
INFO:b2listen:Tunnel URL: https://pulse-equity-lyric-premiere.trycloudflare.com
INFO:b2listen:Creating rule with name "--autocreated-b2listen-2024-07-22-16-10-39-480080--"
CRITICAL:b2listen:Error creating event notification rule - an overlapping rule already exists.

Either another instance of this app is running, or the app was terminated and failed to clean up. You can run the app again with the "cleanup" command and your bucket name.
```

If you are running B2listen outside Docker, you may also see one or more instances of `cloudflared` still running:

```console
% ps | grep cloudflared | grep -v grep
3313 ttys011    0:00.38 cloudflared --no-autoupdate tunnel --url http://localhost:8080 --loglevel info --label --autocreated-b2listen-2024-07-22-16-09-39-909265--
```

In these circumstances, you can run B2listen with the `cleanup` command to delete any temporary rules and terminate any orphan `cloudflared` processes.

In Docker:

```console
% docker run --env-file .env ghcr.io/backblaze-b2-samples/b2listen cleanup my-bucket      
INFO:root:Deleting rule "--autocreated-b2listen-2024-07-22-16-09-39-909265--"
INFO:root:Could not find any processes with --autocreated-b2listen- in the command line
```

Outside Docker (see below):

```console
% python -m b2listen cleanup my-bucket
INFO:root:Deleting rule "--autocreated-b2listen-2024-07-22-16-09-39-909265--"
INFO:b2listen:Killing process 3313 with command line "cloudflared --no-autoupdate tunnel --url http://localhost:8080 --loglevel info --label --autocreated-b2listen-2024-07-22-16-09-39-909265--"
```

## Show the B2listen Version Number

Use the `version` command to show the version number:

```console
% docker run ghcr.io/backblaze-b2-samples/b2listen version
b2listen version 1.0.0
```

## Running B2listen Outside Docker

You can also run the Python app directly from the command-line if you wish. You will need Python 3.10 or higher, and you must [install `cloudflared`](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) on your machine.

First, clone this repository to your machine:

```console
% git clone git@github.com:backblaze-b2-samples/b2listen.git
Cloning into 'b2listen'...
...
% cd b2listen
```

It's good practice to create a Python virtual environment to encapsulate dependencies:

```console
% python3 -m venv .venv
% source .venv/bin/activate
```

Now you can install the Python dependencies:

```console
% pip install -r requirements.txt
% pip install -r requirements.txt    
Collecting b2sdk==2.4.1
  Downloading b2sdk-2.4.1-py3-none-any.whl (279 kB)
...
Installing collected packages: logfury, urllib3, typing-extensions, python-dotenv, psutil, idna, charset-normalizer, certifi, annotated_types, requests, b2sdk
Successfully installed annotated_types-0.7.0 b2sdk-2.4.1 certifi-2024.7.4 charset-normalizer-3.3.2 idna-3.7 logfury-1.0.1 psutil-6.0.0 python-dotenv-1.0.1 requests-2.32.3 typing-extensions-4.12.2 urllib3-2.2.2
```

You also need to install `b2listen` in editable mode:

```console
% pip install -e .
```

Create a `.env` file as described in the [Configuration](#configuration) section above. The Python app will automatically load the `.env` file.

You can now run any of the above commands using `python -m b2listen` instead of `docker run --env-file .env ghcr.io/backblaze-b2-samples/b2listen`. For example:

```console
% python -m b2listen listen my-bucket --url http://localhost:8080
INFO:b2listen:Tunnel URL: https://cnn-studies-assistance-cdna.trycloudflare.com
INFO:b2listen:Creating rule with name "--autocreated-b2listen-2024-07-22-16-07-16-083231--"
INFO:b2listen:Registered tunnel connection connIndex=0 connection=810f4914-12ec-4a08-a4fd-764478ca1e4a event=0 ip=198.41.192.77 location=sjc01 protocol=quic
INFO:b2listen:Ready to deliver events to http://localhost:8080
```

If `cloudflared` is not on the path, you can specify its location with the `--cloudflared-command` argument:

```console
% python -m b2listen --cloudflared-command /path/to/my/cloudflared listen my-bucket \
    --url http://localhost:8080
...
```

## Troubleshooting

You can use the `--loglevel` argument to set B2listen's logging level to one of `debug`, `info`, `warn`, `error`, or `critical`. Setting the logging level to `debug` shows much more detail, including the JSON representation of the temporary rule and all of the output from `cloudflared`:

```console
% docker run --env-file .env ghcr.io/backblaze-b2-samples/b2listen --loglevel debug \
    listen my-bucket --url host.docker.internal:8080
DEBUG:b2listen:Application Key ID = 00415f935cf4dcb0000000473
DEBUG:b2listen:Application Key = K004***************************
DEBUG:b2listen:Authorized for access to my-bucket
DEBUG:b2listen:2024-07-22T23:28:50Z INF Thank you for trying Cloudflare Tunnel. Doing so, without a Cloudflare account, is a quick way to experiment and try it out. However, be aware that these account-less Tunnels have no uptime guarantee. If you intend to use Tunnels in production you should use a pre-created named tunnel by following: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps
DEBUG:b2listen:2024-07-22T23:28:50Z INF Requesting new quick Tunnel on trycloudflare.com...
DEBUG:b2listen:2024-07-22T23:28:51Z INF +--------------------------------------------------------------------------------------------+
DEBUG:b2listen:2024-07-22T23:28:51Z INF |  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):  |
DEBUG:b2listen:2024-07-22T23:28:51Z INF |  https://genre-mirrors-jaguar-dimensions.trycloudflare.com                                 |
INFO:b2listen:Tunnel URL: https://genre-mirrors-jaguar-dimensions.trycloudflare.com
INFO:b2listen:Creating rule with name "--autocreated-b2listen-2024-07-22-23-28-50-499240--"
DEBUG:b2listen:Rule is {
  "eventTypes": [
    "b2:ObjectCreated:*",
    "b2:ObjectDeleted:*",
    "b2:HideMarkerCreated:*"
  ],
  "isEnabled": true,
  "name": "--autocreated-b2listen-2024-07-22-23-28-50-499240--",
  "objectNamePrefix": "",
  "targetConfiguration": {
    "targetType": "webhook",
    "url": "https://genre-mirrors-jaguar-dimensions.trycloudflare.com",
    "customHeaders": null,
    "hmacSha256SigningSecret": null
  }
}
DEBUG:b2listen:2024-07-22T23:28:51Z INF +--------------------------------------------------------------------------------------------+
DEBUG:b2listen:2024-07-22T23:28:51Z INF Cannot determine default configuration path. No file [config.yml config.yaml] in [~/.cloudflared ~/.cloudflare-warp ~/cloudflare-warp /etc/cloudflared /usr/local/etc/cloudflared]
DEBUG:b2listen:2024-07-22T23:28:51Z INF Version 2024.6.1
DEBUG:b2listen:2024-07-22T23:28:51Z INF GOOS: linux, GOVersion: go1.22.2-devel-cf, GoArch: arm64
DEBUG:b2listen:2024-07-22T23:28:51Z INF Settings: map[ha-connections:1 label:--autocreated-b2listen-2024-07-22-23-28-50-499240-- loglevel:info no-autoupdate:true protocol:quic url:http://host.docker.internal:8080]
DEBUG:b2listen:2024-07-22T23:28:51Z INF Generated Connector ID: 8242bdee-8c70-4d99-9f18-000394214f29
DEBUG:b2listen:2024-07-22T23:28:52Z INF Initial protocol quic
DEBUG:b2listen:2024-07-22T23:28:52Z INF ICMP proxy will use 172.17.0.2 as source for IPv4
DEBUG:b2listen:2024-07-22T23:28:52Z INF ICMP proxy will use ::1 in zone lo as source for IPv6
DEBUG:b2listen:2024-07-22T23:28:52Z INF Starting metrics server on 127.0.0.1:38987/metrics
DEBUG:b2listen:2024/07/22 23:28:52 failed to sufficiently increase receive buffer size (was: 208 kiB, wanted: 7168 kiB, got: 416 kiB). See https://github.com/quic-go/quic-go/wiki/UDP-Buffer-Sizes for details.
DEBUG:b2listen:2024-07-22T23:28:52Z INF Registered tunnel connection connIndex=0 connection=b997647c-6e56-47a8-854d-fdb59a0d6c1e event=0 ip=198.41.192.167 location=sjc01 protocol=quic
INFO:b2listen:Registered tunnel connection connIndex=0 connection=b997647c-6e56-47a8-854d-fdb59a0d6c1e event=0 ip=198.41.192.167 location=sjc01 protocol=quic
INFO:b2listen:Ready to deliver events to http://host.docker.internal:8080
```

Setting logging level to `debug` will also show a detailed stack trace for all errors. For example:

```console
% docker run --env-file .env ghcr.io/backblaze-b2-samples/b2listen --loglevel debug \
    listen --url host.docker.internal:8080 bad-bucket
DEBUG:b2listen:Application Key ID = 00415f935cf4dcb0000000472
DEBUG:b2listen:Application Key = K004***************************
DEBUG:b2listen:Authorized for access to all buckets
CRITICAL:b2listen:Bucket "bad-bucket" does not exist
Traceback (most recent call last):
  File "/app/b2listen/b2listen.py", line 454, in main
    commands[args.cmd](args)
  File "/app/b2listen/b2listen.py", line 333, in listen
    b2bucket: Bucket = b2_api.get_bucket_by_name(args.bucket_name)
  File "/usr/local/lib/python3.10/site-packages/b2sdk/_internal/api.py", line 380, in get_bucket_by_name
    raise NonExistentBucket(bucket_name)
b2sdk._internal.exception.NonExistentBucket: No such bucket: bad-bucket
```
