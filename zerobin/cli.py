#!/usr/bin/env python3


"""
    Main script including runserver and delete-paste.
"""

import sys
import re
import os

import zerobin

from zerobin.utils import (
    settings,
    SettingsValidationError,
    ensure_app_context,
    hash_password,
)
from zerobin.routes import get_app
from zerobin.paste import Paste


from bottle import run

import clize


def runserver(
    *,
    host="",
    port="",
    config_dir="",
    data_dir="",
    debug=None,
    version=False,
    server="paste",
):
    if version:
        print("0bin V%s" % settings.VERSION)
        sys.exit(0)

    try:
        updated_settings, app = get_app(
            debug=debug, config_dir=config_dir, data_dir=data_dir,
        )
    except SettingsValidationError as err:
        print("Configuration error: %s" % err, file=sys.stderr)
        sys.exit(1)

    updated_settings.HOST = host or os.environ.get(
        "ZEROBIN_HOST", updated_settings.HOST
    )
    updated_settings.PORT = port or os.environ.get(
        "ZEROBIN_PORT", updated_settings.PORT
    )

    if updated_settings.DEBUG:
        print(
            f"Admin URL for dev: http://{updated_settings.HOST}:{updated_settings.PORT}{settings.ADMIN_URL}"
        )
        print()
        run(
            app,
            host=updated_settings.HOST,
            port=updated_settings.PORT,
            reloader=True,
            server=server,
        )
    else:
        run(app, host=settings.HOST, port=updated_settings.PORT, server=server)


# The regex parse the url and separate the paste's id from the decription key
# After the '/paste/' part, there is several caracters, identified as
# the uuid of the paste. Followed by a '#', the decryption key of the paste.
paste_url = re.compile("/paste/(?P<paste_id>.*)#(?P<key>.*)")


def unpack_paste(paste):
    """Take either the ID or the URL of a paste, and return its ID"""

    try_url = paste_url.search(paste)

    if try_url:
        return try_url.group("paste_id")
    return paste


def delete_paste(*pastes, quiet=False):
    """
    Remove pastes, given its ID or its URL

    quiet: Don't print anything

    pastes: List of pastes, given by ID or URL
    """

    for paste_uuid in map(unpack_paste, pastes):
        try:
            Paste.load(paste_uuid).delete()

            if not quiet:
                print("Paste {} is removed".format(paste_uuid))

        except ValueError:
            if not quiet:
                print("Paste {} doesn't exist".format(paste_uuid))


def infos():
    """ Print the route to the 0bin admin.

    The admin route is generated by zerobin so that bots won't easily
    bruteforce it. To get the full URL, simply preppend your website domain
    name to it.

    E.G:

    If this command prints:

         "/admin/f1cc3972a4b933c734b37906940cf69886161492ee4eb7c1faff5d7b5e92efb8"

    Then the admin url is:

        "http://yourdomain.com/admin/f1cc3972a4b933c734b37906940cf69886161492ee4eb7c1faff5d7b5e92efb8"

    Adapt "http" and "yourdomain.com" to your configuration.

    In debug mode, the dev server will print the url when starting.

    """

    ensure_app_context()
    print(f"Zerobin version: {zerobin.__version__}")
    print(f"Admin URL (to moderate pastes): {settings.ADMIN_URL}")
    print(f"Data dir (pastes and counter): {settings.DATA_DIR}")
    print(
        f"Config dir (config file, secret key, admin password and custom views): {settings.CONFIG_DIR}"
    )
    print(
        f"Static files dir (to configure apache, nging, etc.): {settings.STATIC_FILES_ROOT}"
    )


def set_admin_password(password):
    """ Set the password for the admin

    It will be stored as a scrypt hash in a file in the var dir.

    """

    ensure_app_context()
    settings.ADMIN_PASSWORD_FILE.write_bytes(hash_password(password))


def main():
    subcommands = [runserver, delete_paste, infos, set_admin_password]
    subcommand_names = [
        clize.util.name_py2cli(name)
        for name in clize.util.dict_from_names(subcommands).keys()
    ]
    if len(sys.argv) < 2 or sys.argv[1] not in subcommand_names:
        sys.argv.insert(1, subcommand_names[0])
    clize.run(runserver, delete_paste, infos, set_admin_password)

