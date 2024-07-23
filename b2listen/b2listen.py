import argparse
import datetime
import json
import logging
import os
import re
import subprocess
import traceback
import warnings
from importlib import metadata
from pathlib import Path
from typing import List, Callable, Dict

import psutil
from b2sdk.v2 import AuthInfoCache, B2Api, Bucket, InMemoryAccountInfo, NotificationRule
from b2sdk.v2.exception import BadRequest, NonExistentBucket
from dotenv import load_dotenv

from b2listen.server import Server

logging.basicConfig()
logger = logging.getLogger('b2listen')

DEFAULT_PORT = 8080
SIGNING_SECRET_LENGTH = 32
EVENT_NOTIFICATION_RULE_PREFIX = '--autocreated-b2listen-'

NAME = 'b2listen'


def version(_args: argparse.Namespace):
    v = metadata.version(NAME)
    print(f'{NAME} version {v}')


# From https://stackoverflow.com/a/73564246/33905
def in_docker():
    mountinfo = Path('/proc/self/mountinfo')
    return Path('/.dockerenv').is_file() or (mountinfo.is_file() and 'docker' in mountinfo.read_text())


DEFAULT_HOST = 'host.docker.internal' if in_docker() else 'localhost'


def exit_with_error(message: str, exc_info=None):
    if logger.isEnabledFor(logging.DEBUG):
        if not exc_info:
            # Get a stack trace, since we weren't passed an exception
            stacktrace = traceback.extract_stack()
            # Pop the last frame, so it leads to the error, rather than here
            stacktrace.pop()
            # Add it to the error message
            message += f'\n{"".join(traceback.format_list(stacktrace))}'
    else:
        # Suppress stack trace, even if we have an exception
        exc_info = None

    logger.critical(message, exc_info=exc_info)
    exit(1)


def check_and_get_env_vars(env_vars: List[str]) -> List[str]:
    values = []
    notset = []
    for env_var in env_vars:
        if env_var in os.environ:
            values.append(os.environ[env_var])
        else:
            notset.append(env_var)

    if len(notset) > 0:
        if len(notset) == 1:
            message = f'You must set the {notset} environment variable'
        else:
            notset_vars = f'{", ".join(notset[:-1])} and {notset[-1]}'
            message = f'You must set the {notset_vars} environment variables'

        exit_with_error(message)
    return values


def create_rule(b2bucket: Bucket, url: str, name: str, args: argparse.Namespace):
    custom_headers = parse_custom_headers(args.custom_headers)

    new_rule: NotificationRule = {
        'eventTypes': args.event_types,
        'isEnabled': True,
        'name': name,
        'objectNamePrefix': args.prefix,
        'targetConfiguration': {
            'targetType': 'webhook',
            'url': url,
            'customHeaders': custom_headers,
            'hmacSha256SigningSecret': args.signing_secret
        }
    }

    # Suppress FeaturePreviewWarning for Event Notifications
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        old_rules = b2bucket.get_notification_rules()
        new_rules = old_rules + [new_rule]
        try:
            logger.info(f'Creating rule with name "{name}"')
            logger.debug(f'Rule is {json.dumps(new_rule, indent=2)}')
            # Suppress warnings about incompatible types - NotificationRule != NotificationRuleResponse
            # noinspection PyTypeChecker
            b2bucket.set_notification_rules(new_rules)
        except BadRequest as e:
            found = False
            if e.message.startswith('More than one event notification rule has overlapping prefixes'):
                for rule in old_rules:
                    if rule['name'].startswith(EVENT_NOTIFICATION_RULE_PREFIX):
                        found = True
                        break

            if found:
                exit_with_error('Error creating event notification rule - an overlapping rule already exists.\n\n'
                                'Either another instance of this app is running, or the app was terminated and '
                                'failed to clean up. You can run the app again with the "cleanup" command and '
                                'your bucket name.\n', exc_info=e)
            else:
                exit_with_error(f'Error setting event notification rule: {e.message}', exc_info=e)


def modify_rule(b2bucket: Bucket, url: str, name: str) -> str:
    # Suppress FeaturePreviewWarning for Event Notifications
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rules = b2bucket.get_notification_rules()
        rule = next((rule for rule in rules if rule['name'] == name), None)
        if not rule:
            exit_with_error(f'Cannot find rule "{name}"')
        old_url = rule['targetConfiguration']['url']
        rule['targetConfiguration']['url'] = url

        try:
            # Suppress warnings about incompatible types - NotificationRule != NotificationRuleResponse
            # noinspection PyTypeChecker
            b2bucket.set_notification_rules(rules)
            logger.info(f'Modified rule with name "{name}"')
            logger.info(f'Old URL was {old_url}; new URL is {url}')
            logger.debug(f'Rule is {json.dumps(rule, indent=2)}')
        except BadRequest as e:
            exit_with_error(f'Error setting event notification rule {e.message}', exc_info=e)
        return old_url


def delete_rule(b2bucket: Bucket, name: str):
    # Suppress FeaturePreviewWarning for Event Notifications
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        logger.info(f'Deleting rule with name "{name}"')
        old_rules = b2bucket.get_notification_rules()
        new_rules = [rule for rule in old_rules if rule['name'] != name]
        if len(new_rules) == len(old_rules):
            logger.warning(f'Could not find rule "{name}" - did you delete it manually?')
        else:
            # Suppress warnings about incompatible types - NotificationRule != NotificationRuleResponse
            # noinspection PyTypeChecker
            b2bucket.set_notification_rules(new_rules)


def validate_signing_secret(s: str) -> str:
    if len(s) == SIGNING_SECRET_LENGTH and s.isalnum():
        return s
    raise argparse.ArgumentTypeError("Signing secret must be 32 alphanumeric characters")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog=NAME,
        description='Deliver Event Notifications for a given bucket to a local service.\n\n'
                    'For more details on one command:\n\n'
                    f'{NAME} <command> --help',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--loglevel', type=str, choices=['debug', 'info', 'warn', 'error', 'critical'],
                        required=False, default='info',
                        help='Application logging level. (default: "info")')
    parser.add_argument('--cloudflared-command', type=str, required=False, default='cloudflared',
                        help='Command to run for cloudflared. (default: "cloudflared")')

    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument('bucket_name', type=str, metavar='bucket-name',
                               help='Name of the bucket')

    subparsers = parser.add_subparsers(help='Sub-command help', dest='cmd', required=True)

    parser_listen = subparsers.add_parser(
        'listen',
        help='Listen for event notifications and deliver them to a local webserver.\n\n'
             'You can use an existing Event Notification rule or specify the configuration '
             'of a new, temporary rule.',
        parents=[common_parser])

    group = parser_listen.add_mutually_exclusive_group(required=True)
    group.add_argument('--url', type=str,
                       help=f'Local webserver URL, for example: "http://localhost:8080")')
    group.add_argument('--run-server', action='store_true',
                       help=f'Run the embedded HTTP server')

    use_existing = parser_listen.add_argument_group(description='To use an existing Event Notification rule:')
    use_existing.add_argument('--rule-name', type=str, required=False,
                              help='Name of an existing event notification rule.')

    create_temporary = parser_listen.add_argument_group(description='To create a temporary Event Notification rule:')
    create_temporary.add_argument('--event-types', type=str, nargs='*',
                                  default=['b2:ObjectCreated:*', 'b2:ObjectDeleted:*', 'b2:HideMarkerCreated:*'],
                                  help='Event type(s)')
    create_temporary.add_argument('--prefix', type=str, required=False, default='',
                                  help='Object name prefix. For example, "images/pets"')
    create_temporary.add_argument('--custom-headers', type=str, required=False, nargs='*',
                                  help='One or more custom headers in the form '
                                       'X-My-First-Header:red X-My-Second-Header:blue')
    create_temporary.add_argument('--signing-secret', type=validate_signing_secret, required=False,
                                  help='A 32-character secret that is used to sign the webhook invocation payload '
                                       'using the HMAC SHA-256 algorithm')

    parser_listen.add_argument('--cloudflared-loglevel', type=str,
                               choices=['debug', 'info', 'warn', 'error', 'fatal'], required=False, default='info',
                               help='cloudflared logging level. (default: "info")')

    _parser_cleanup = subparsers.add_parser(
        'cleanup',
        help='Remove event notification rules and kill cloudflared processes left over from previous invocations',
        parents=[common_parser]
    )

    _parser_version = subparsers.add_parser(
        'version',
        help='Show the version number'
    )

    args = parser.parse_args()

    # Remove default for event types, so we can tell if the user explicitly set it
    create_temporary.set_defaults(event_types=None)

    user_set_args = parser.parse_args()

    if (args.cmd == 'listen'
            and args.rule_name
            and (user_set_args.event_types or args.prefix or args.custom_headers or args.signing_secret)):
        exit_with_error(f'You cannot specify an existing rule name and configuration for a temporary rule')
    return args


def check_bucket_allowed(b2_api: B2Api, bucket_name: str):
    allowed = b2_api.account_info.get_allowed()
    allowed_bucket_name = allowed['bucketName']

    logger.debug(f'Authorized for access to {allowed_bucket_name if allowed_bucket_name else "all buckets"}')
    if allowed_bucket_name and allowed_bucket_name != bucket_name:
        application_key = b2_api.account_info.get_application_key()
        exit_with_error(f'Application key {application_key} is not authorized for {bucket_name}')


def authorize_b2() -> B2Api:
    application_key_id, application_key = check_and_get_env_vars(['B2_APPLICATION_KEY_ID', 'B2_APPLICATION_KEY'])
    logger.debug(f'Application Key ID = {application_key_id}')
    # First 4 chars of application key are the cluster - not secret, and helpful for debugging!
    logger.debug(f'Application Key = {application_key[:4] + ("*" * 27)}')

    info = InMemoryAccountInfo()
    b2_api = B2Api(info, cache=AuthInfoCache(info))
    b2_api.authorize_account("production", application_key_id, application_key)

    return b2_api


def run_cloudflared(command: str, loglevel: str, service_url: str, label: str, url_handler: Callable[[str], None],
                    exit_handler: Callable[[], None]):
    cmd = [command,
           '--no-autoupdate',
           'tunnel',
           '--url', service_url,
           '--loglevel', loglevel,
           '--label', label]
    process = None
    found_url = False
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
            text=True
        )

        url_line_regex = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\sINF\s\|\s+(https://[a-z0-9.\-]+)\s+\|$')
        reg_tunnel_regex = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\sINF\s(Registered tunnel connection .+)$')
        while True:
            line = process.stderr.readline().strip()
            logger.debug(line)
            if not found_url:
                match = url_line_regex.match(line)
                if match:
                    tunnel_url = match.group(1)
                    logger.info(f'Tunnel URL: {tunnel_url}')
                    url_handler(tunnel_url)
                    found_url = True
            else:
                match = reg_tunnel_regex.match(line)
                if match:
                    reg_line = match.group(1)
                    logger.info(reg_line)
                    logger.info(f'Ready to deliver events to {service_url}')

    except KeyboardInterrupt:
        # Catch KeyboardInterrupt so we don't print a stack trace on exit
        pass

    finally:
        if process:
            logger.info('Stopping cloudflared')
            process.kill()
        if exit_handler:
            exit_handler()


def listen(args: argparse.Namespace):
    if args.run_server:
        http_server = Server(interface='localhost', port=0, daemon=True)
        http_server.start()
        service_url = f'http://{http_server.interface}:{http_server.port}'
    else:
        service_url = args.url

    b2_api: B2Api = authorize_b2()

    check_bucket_allowed(b2_api, args.bucket_name)

    b2bucket: Bucket = b2_api.get_bucket_by_name(args.bucket_name)

    # Label for cloudflared, used as name for temporary rule
    # 2020-03-20T14:28:23.382748 -> 2020-03-20-14-28-23-382748
    timestamp = (datetime.datetime.now().isoformat()
                 .replace(':', '-')
                 .replace('T', '-')
                 .replace('.', '-'))
    label = f'{EVENT_NOTIFICATION_RULE_PREFIX}{timestamp}--'

    # Did the user specify a rule name?
    if args.rule_name:
        # Yes - modify an existing rule
        # We need to remember the old URL to restore it on exit
        old_url: str | None = None

        def url_handler(url):
            nonlocal old_url
            old_url = modify_rule(b2bucket, url, args.rule_name)

        def exit_handler():
            nonlocal old_url
            modify_rule(b2bucket, old_url, args.rule_name)
    else:
        # No - create a temporary rule using the label as its name
        def url_handler(url):
            create_rule(b2bucket, url, label, args)

        def exit_handler():
            delete_rule(b2bucket, label)

    run_cloudflared(args.cloudflared_command, args.cloudflared_loglevel, service_url, label, url_handler, exit_handler)


def parse_custom_headers(custom_headers_arg: List[str] | None) -> List[Dict[str, str]] | None:
    """
    Parse user-supplied list of custom headers into the form used by Event Notification rules
    :param custom_headers_arg: List of custom headers in the form 'Header-Name:header_value'
    :return: List of custom header dicts in the form {'name': 'Header-Name', 'value': 'header_value'}
    """
    if not custom_headers_arg:
        return None

    custom_headers = []
    for header in custom_headers_arg:
        parts = header.split(':', 1)
        if len(parts) != 2:
            exit_with_error(f'Bad custom header: {header}')
        custom_headers.append({'name': parts[0].strip(), 'value': parts[1].strip()})
    return custom_headers


def cleanup_processes(cloudflared_command: str):
    killed_count = 0
    for process in psutil.process_iter():
        try:
            cmdline = process.cmdline()
        except psutil.AccessDenied:
            # psutil.process_iter() will return all processes, including those for which we do not have permission to
            # get their command-line, so we need to catch the AccessDenied exception and just continue processing
            continue
        except psutil.NoSuchProcess:
            # Processes can die between process_iter() finding them and getting their command line
            continue
        if (len(cmdline) > 0 and
                cmdline[0] == cloudflared_command and
                len([x for x in cmdline if x.startswith(EVENT_NOTIFICATION_RULE_PREFIX)]) > 0):
            logger.info(f'Killing process {process.pid} with command line "{" ".join(cmdline)}"')
            process.kill()
            killed_count += 1
    if killed_count == 0:
        logger.info(f'Could not find any processes with {EVENT_NOTIFICATION_RULE_PREFIX} in the command line')


# Suppress warnings about incompatible types
# noinspection PyTypeChecker
def cleanup_rules(b2bucket: Bucket):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        old_rules = b2bucket.get_notification_rules()
        new_rules = []
        for rule in old_rules:
            if rule['name'].startswith(EVENT_NOTIFICATION_RULE_PREFIX):
                logger.info(f'Deleting rule "{rule["name"]}"')
            else:
                new_rules.append(rule)
        if len(new_rules) == len(old_rules):
            logger.info(f'No rules to cleanup (prefix is "{EVENT_NOTIFICATION_RULE_PREFIX}").')
        else:
            b2bucket.set_notification_rules(new_rules)


def cleanup(args: argparse.Namespace):
    b2_api: B2Api = authorize_b2()

    check_bucket_allowed(b2_api, args.bucket_name)

    b2bucket: Bucket = b2_api.get_bucket_by_name(args.bucket_name)

    cleanup_rules(b2bucket)
    cleanup_processes(args.cloudflared_command)


# Map command names to functions
commands = {
    'listen': listen,
    'cleanup': cleanup,
    'version': version
}


def main():
    global commands

    args = parse_args()

    logger.setLevel(args.loglevel.upper())

    load_dotenv()

    try:
        commands[args.cmd](args)
    except NonExistentBucket as e:
        exit_with_error(f'Bucket "{args.bucket_name}" does not exist', exc_info=e)
