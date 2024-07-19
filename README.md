# Backblaze B2 Listener

The Backblaze B2 Listener, "B2listen" for short, allows you to forward Backblaze B2 Event Notifications to a service listening on a local URL. B2listen uses Cloudflare's free [Quick Tunnels](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/) feature, running an instance of [cloudflared](https://github.com/cloudflare/cloudflared) to generate a random subdomain on `trycloudflare.com` and proxy traffic from that URL to the local endpoint. B2listen can modify an existing Event Notification rule to use the `trycloudflre.com` URL or create a new, temporary, rule to do so.

Note: the Event Notifications feature is currently in private preview. For information about enabling this feature, see [Automate Your Data Workflows With Backblaze B2 Event Notifications](https://www.backblaze.com/blog/announcing-event-notifications/).

## Prerequisites

You need a Backblaze B2 Account that is enabled for Event Notifications, a Backblaze B2 Bucket, and an Application Key

Follow these instructions, as necessary:

* [Create a Backblaze B2 Account](https://www.backblaze.com/sign-up/cloud-storage).
* [Join the waiting list for the Event Notifications private preview](https://www.surveymonkey.com/r/ZL2X68S).
* [Create a Backblaze B2 Bucket](https://www.backblaze.com/docs/cloud-storage-create-and-manage-buckets).
* [Create an Application Key](https://www.backblaze.com/docs/cloud-storage-create-and-manage-app-keys#create-an-app-key) with access to the bucket you wish to use. The application key must have the `readBucketNotifications` and `writeBucketNotifications` capabilities.
  > If Event Notifications is enabled for your account then you can create a suitable application key using the Backblaze web UI. You cannot use application keys created before Event Notifications was enabled for your account with B2listen. 

Be sure to copy the application key as soon as you create it, as you will not be able to retrieve it later!

You will also need a local service to receive, and optionally act on, event notification messages. If you are experimenting with B2listen and don't have a suitable service, you can use the included `server.py` app to receive and display incoming messages. By default, `server.py` listens on port 8080 of the `localhost` interface:

```console
python3 server.py
INFO:root:Starting httpd on localhost:8080...
```

## Configuration

You must set environment variables containing your Backblaze B2 application key and its ID: `B2_APPLICATION_KEY` and `B2_APPLICATION_KEY_ID` respectively. You can set these in the environment, in a `.env` file, or on the Docker command-line.

This repo includes a template file, `.env.template`. Copy it to `.env`, then edit it as follows:
```dotenv
B2_APPLICATION_KEY_ID=Your-Application-Key-ID
B2_APPLICATION_KEY=Your-Application-Key
```

When you're done, .env should look like this:
```dotenv
B2_APPLICATION_KEY_ID=004qlekmvpwemrt000000009e
B2_APPLICATION_KEY=K004JEKEUTGLKEJFKLRJHTKLVCNWURM
```

Note: do not use quotes in the `.env` file. Docker does not recognize quoted variable values, and will include the quotes in the values of the variables.

## Usage

The most convenient way to use B2listen is via Docker, but you can also run the Python app directly.

In either case, you can run B2listen with the `--help` argument to show top level usage information, and specify a command for more detail. For example, in Docker:

```console
% docker run superpat7/b2listen --help                                  
usage: b2listen.py [-h] [--loglevel {debug,info,warn,error,critical}]
                   [--cloudflared-command CLOUDFLARED_COMMAND]
                   {listen,cleanup} ...

Deliver Event Notifications for a given bucket to a local service.

For more details on one command:

b2listen.py <command> --help
...
% docker run superpat7/b2listen listen --help
usage: b2listen.py listen [-h] [--url URL] [--rule-name RULE_NAME]
                          [--event-types [EVENT_TYPES ...]] [--prefix PREFIX]
                          [--custom-headers [CUSTOM_HEADERS ...]]
                          [--signing-secret SIGNING_SECRET]
                          [--cloudflared-loglevel {debug,info,warn,error,fatal}]
                          bucket-name
...
```

## Running B2listen in Docker

The Docker image, `superpat7/b2listen`, bundles the `cloudflare` executable with the B2listen Python application and the Python runtime. The image supports the `linux/amd64` and `linux/arm64` platforms, so it will run well on either Intel/AMD or Apple Silicon CPUs.

You can pass your application key and its ID to the Docker run command using the `--env-file` argument and your `.env` file, as shown below, or by setting a `--env` argument for each value.

To create a new, temporary, event notification rule and proxy event notification messages to a local service, use the `listen` command and, minimally, specify your bucket name. For example:

```shell
% docker run --env-file .env superpat7/b2listen listen metadaddy-tester
INFO:b2listen:Tunnel URL: https://alfred-dakota-vbulletin-comfort.trycloudflare.com
INFO:b2listen:Creating rule with name "--autocreated-b2listen-2024-07-22-22-18-03-448423--"
INFO:b2listen:Registered tunnel connection connIndex=0 connection=b7ebd606-8da5-4273-af3d-472ec741887c event=0 ip=198.41.200.13 location=sjc08 protocol=quic
INFO:b2listen:Ready to deliver events to http://host.docker.internal:8080
```

> At present, the B2listen Docker image is located in the [`superpat7/b2listen`](https://hub.docker.com/r/superpat7/b2listen) repository. We plan to move it to a more 'official' location in the near future.

By default, if B2listen detects that it is running in Docker, then the default local service URL is http://host.docker.internal:8080. Otherwise, the default is http://localhost:8080.

> Note: `host.docker.internal` is a special hostname that resolves to the Docker host. You cannot use a hostname such as `localhost` or `127.0.0.1` when B2listen is running in Docker, as these will resolve to the Docker container's own network interface.

Most of the examples shown in this document are run from Docker.

You can also run B2listen outside Docker; see the [instructions below](running-b2listen-outside-docker).

## Event Notification Messages

If you upload a file to (or delete, or hide a file in) your Backblaze B2 Bucket, B2 sends an event notification message as an HTTP POST with JSON-formatted payload to the `trycloudflare.com` URL shown in B2listen's output. `cloudflared` then forwards the message to the local service URL. For example, if you were running the included `server.py` app to receive and display incoming messages, you would see output similar to this:

```console
% python3 server.py     
INFO:root:Starting httpd on localhost:8080...

INFO:root:POST request,
Path: /
Headers:
Host: formatting-quiz-hurt-anatomy.trycloudflare.com
User-Agent: B2/EventNotifications
Content-Length: 628
Accept-Encoding: gzip
Cdn-Loop: cloudflare; subreqs=1
Cf-Connecting-Ip: 2605:72c0:503:42::c19
Cf-Ew-Via: 15
Cf-Ipcountry: US
Cf-Ray: 8a774edd503f1643-SJC
Cf-Visitor: {"scheme":"https"}
Cf-Warp-Tag-Id: 565bc4b4-53cb-4730-a969-aadf5dfe3303
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
      "bucketName": "metadaddy-tester",
      "eventId": "547d65a102a5be92b07ec200d3a95cfe06248b02ee6f656e016609b25bf8cd59",
      "eventTimestamp": 1721691964421,
      "eventType": "b2:ObjectCreated:Upload",
      "eventVersion": 1,
      "matchedRuleName": "--autocreated-b2listen-2024-07-22-23-45-44-108863--",
      "objectName": "images/raw/smiley.png",
      "objectSize": 23889,
      "objectVersionId": "4_z21a5bf29a395fc7f84dd0c1b_f106fce3586b4ff73_d20240722_m234600_c004_v0402017_t0007_u01721691960668"
    }
  ]
}

127.0.0.1 - - [22/Jul/2024 16:46:05] "POST / HTTP/1.1" 200 -
```

## B2listen Command-Line Arguments

You can override the default service URL via the `--url` argument. For example, if your local service is running on port 9999 on the Docker host: 

```shell
% docker run --env-file .env superpat7/b2listen listen metadaddy-tester --url host.docker.internal:9999
INFO:b2listen:Tunnel URL: https://within-weight-ensemble-wanting.trycloudflare.com
INFO:b2listen:Creating rule with name "--autocreated-b2listen-2024-07-22-22-41-03-388021--"
INFO:b2listen:Registered tunnel connection connIndex=0 connection=04662c35-60ab-438c-b50c-86e9ec50ccf3 event=0 ip=198.41.192.167 location=sjc06 protocol=quic
INFO:b2listen:Ready to deliver events to host.docker.internal:9999
```

As mentioned above, B2listen can either use an existing [event notification rule](https://www.backblaze.com/docs/en/cloud-storage-event-notifications-reference-guide?highlight=event%20notifications#event-notification-rules) or create a new, temporary, rule.

### Creating a Temporary Event Notification Rule

By default, on startup, B2listen creates a new, temporary, rule with the following settings:

* Name with the form `--autocreated-b2listen-yyyy-MM-dd-HH-mm-ss-SSSSSS--`, for example, `--autocreated-b2listen-2024-07-22-14-52-19-118384--`
* All [event types](https://www.backblaze.com/docs/en/cloud-storage-event-notifications-reference-guide?highlight=event%20notifications#event-types) selected (`b2:ObjectCreated:*`, `b2:ObjectDeleted:*`, and `b2:HideMarkerCreated:*`)
* No prefix
* URL set to the `trycloudflare.com` endpoint, for example, `https://positions-guestbook-genius-enormous.trycloudflare.com`
* No custom headers
* No signing secret

You can use the [B2 Command-Line Tool](https://www.backblaze.com/docs/cloud-storage-command-line-tools) to inspect the temporary rule, if you wish:

```console
% b2 bucket notification-rule list b2://metadaddy-tester          
FeaturePreviewWarning: Event Notifications feature is in "Private Preview" state and may change without notice. See https://www.backblaze.com/blog/announcing-event-notifications/ for details.
Notification rules for b2://metadaddy-tester/ :
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
% docker run --env-file .env superpat7/b2listen listen metadaddy-tester --url host.docker.internal:8000 \
    --event-types 'b2:ObjectCreated:*' --prefix 'images/raw' --custom-header 'X-Source: B2' \
    --signing-secret 01234567890123456789012345678901
INFO:root:Tunnel URL: https://realize-pj-reasons-pasta.trycloudflare.com
...
```

Note that the temporary rule's configuration cannot overlap with an existing rule. That is, prefixes for rules covering the same event types in the same bucket must be disjoint. The prefixes `images` and `images/raw` overlap, since an object with a name such as `images/raw/kitten.png` matched both prefixes, but the prefixes `images/raw` and `images/thumbnails` are disjoint, since there is no object name that matches both prefixes. 

If you ran the above command in the presence of an existing rule with event type `b2:ObjectCreated:*` and prefix `images`, you would receive an error message:

```console
% docker run --env-file .env superpat7/b2listen listen metadaddy-tester --url host.docker.internal:8000 \
    --event-types 'b2:ObjectCreated:*' --prefix 'images/raw' --custom-header 'X-Source: B2' \
    --signing-secret 01234567890123456789012345678901
INFO:b2listen:Tunnel URL: https://knight-boxing-discipline-commitment.trycloudflare.com
INFO:b2listen:Creating rule with name "--autocreated-b2listen-2024-07-22-15-38-57-094644--"
CRITICAL:b2listen:Error setting event notification rule: More than one event notification rule has overlapping prefixes (images),(images/raw) for the same event type: b2:ObjectCreated:*
```

When B2listen exits, it deletes the temporary rule that it created.

### Using an Existing Event Notification Rule

As an alternative to creating a temporary event notification rule, you can specify the name of an existing rule:

```shell
% docker run --env-file superpat7/b2listen listen metadaddy-tester --url host.docker.internal:8000 --rule-name new-image-created
INFO:root:Tunnel URL: https://larger-interracial-william-validity.trycloudflare.com
...
```

On startup, B2listen will replace the URL in the existing rule with the `trycloudflare.com` URL. On exiting, B2listen will restore the original URL to the rule.

## Cleanup

In some circumstances, B2listen may not delete the temporary rule when exiting. If this happens, the next time you run B2listen, you will see an error message:

```console
% docker run --env-file .env superpat7/b2listen listen metadaddy-tester
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

In these circumstances, you can run B2listen with the `cleanup` command to delete the temporary rule and terminate any orphan `cloudflared` processes.

In Docker:

```console
% docker run --env-file .env superpat7/b2listen cleanup metadaddy-tester      
INFO:root:Deleting rule "--autocreated-b2listen-2024-07-22-16-09-39-909265--"
INFO:root:Could not find any processes with --autocreated-b2listen- in the command line
```

Outside Docker:

```console
% python b2listen.py cleanup metadaddy-tester
INFO:root:Deleting rule "--autocreated-b2listen-2024-07-22-16-09-39-909265--"
INFO:b2listen:Killing process 3313 with command line "cloudflared --no-autoupdate tunnel --url http://localhost:8080 --loglevel info --label --autocreated-b2listen-2024-07-22-16-09-39-909265--"
```

## Running B2listen Outside Docker

You can also run the Python app directly from the command-line if you wish. You will need Python 3.11 or higher.

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

Create a `.env` file as described in the [Configuration](#configuration) section above.

You can now run any of the above commands using `python b2listen.py` instead of `docker run --env-file .env superpat7/b2listen`. For example:

```console
% python b2listen.py listen metadaddy-tester
INFO:b2listen:Tunnel URL: https://cnn-studies-assistance-cdna.trycloudflare.com
INFO:b2listen:Creating rule with name "--autocreated-b2listen-2024-07-22-16-07-16-083231--"
INFO:b2listen:Registered tunnel connection connIndex=0 connection=810f4914-12ec-4a08-a4fd-764478ca1e4a event=0 ip=198.41.192.77 location=sjc01 protocol=quic
INFO:b2listen:Ready to deliver events to http://localhost:8080
```

As mentioned above, when running outside Docker, the default event service URL is `http://localhost:8080`.

## Troubleshooting

You can use the `--loglevel` argument to set B2listen's logging level to one of `debug`, `info`, `warn`, `error`, or `critical`. Setting the logging level to `debug` shows much more detail, including the JSON representation of the temporary rule and all of the output from `cloudflared`:

```console
% docker run --env-file .env superpat7/b2listen --loglevel debug listen metadaddy-tester
DEBUG:b2listen:Application Key ID = 00415f935cf4dcb0000000473
DEBUG:b2listen:Application Key = K004***************************
DEBUG:b2listen:Application Key = K004H61HZk7+QcbmtLzHrLcWz3UQCfU - DANGER!!!
DEBUG:b2listen:Authorized for access to metadaddy-tester
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

```
