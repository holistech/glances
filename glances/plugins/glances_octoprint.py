# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2020 Sören Gebbert <soerengebbert@holistech.de>
#
# Glances is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Glances is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""
Octoprint device state plugin
"""
import requests
import yaml
from pathlib import Path
import os
import datetime

from glances.config import Config
from glances.plugins.glances_plugin import GlancesPlugin


class Plugin(GlancesPlugin):
    """
    Glances' simple octorpint status plugin.

    Be aware that the octoprint server must be available and the API key must be provided
    to this plugin. By default the url is set to: http://0.0.0.0:5000 and the API key will
    be read from the octoprint configuration file from the users home directory.
    """

    def __init__(self, args=None, config=None, stats_init_value=[]):
        super(Plugin, self).__init__(args=args, config=config)
        self.display_curse = True
        self.host = "http://0.0.0.0"
        self.port = 5000
        self.api_key = None

        home = str(Path.home())
        # Get host, port and api_key from the config file
        conf = Config()
        if conf.has_section("octoprint"):
            self.host = conf.get_value(section="octoprint", option="host", default="http://0.0.0.0")
            self.port = conf.get_value(section="octoprint", option="port", default="5000")
            self.api_key = conf.get_value(section="octoprint", option="api_key", default=None)

        if not self.api_key:
            # Read API key from the local octoprint config
            path = os.path.join(home, ".octoprint", "config.yaml")
            if os.path.isfile(path):
                with open(path, "r") as config_file:
                    data = yaml.safe_load(config_file)
                    self.api_key = data["api"]["key"]

        if not "http" in self.host:
            self.host = f"http://{self.host}"
        self.printer_url = f"{self.host}:{self.port}/api/printer"
        self.job_url = f"{self.host}:{self.port}/api/job"
        self.headers = {"X-Api-Key": self.api_key}

    @GlancesPlugin._check_decorator
    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update octoprint stats using request and the octopi REST API.
        """

        stats = self.get_init_value()
        try:
            printer = requests.get(url=self.printer_url, headers=self.headers)
            job = requests.get(url=self.job_url, headers=self.headers)
        except Exception as e:
            stats["state"] = "Error"
            stats["error"] = f"Unable to connect: {str(e)}"
            self.stats = stats
            return self.stats

        if printer.status_code != 200:
            stats["state"] = "Error"
            stats["error"] = printer.text
        else:
            job = job.json()
            printer = printer.json()
            stats["estimatedPrintTime"] = job["job"]["estimatedPrintTime"]
            stats["progress_printTime"] = job["progress"]["printTime"]
            stats["progress_printTimeLeft"] = job["progress"]["printTimeLeft"]
            stats["state"] = job["state"]
            stats["temperature"] = printer["temperature"]

        self.stats = stats
        return self.stats

    def update_views(self):
        """Update stats views."""
        # Call the father's method
        super(Plugin, self).update_views()

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist...
        if not self.stats or self.is_disable():
            return ret
        # Max size for the interface name
        name_max_width = max_width - 11
        msg = '{:{width}}'.format(f'OCTOPRINT {self.stats["state"]}', width=name_max_width)
        ret.append(self.curse_add_line(msg, "TITLE"))
        ret.append(self.curse_new_line())

        if "error" in self.stats:
            msg = '{:{width}}'.format(self.stats["error"], width=name_max_width)
            ret.append(self.curse_add_line(msg, "DEFAULT"))
            return ret

        msg = '{:{width}}'.format("Temperature", width=name_max_width)
        ret.append(self.curse_add_line(msg, "DEFAULT"))
        msg = '{:}'.format("actual target")

        name_max_width = max_width - 10
        ret.append(self.curse_add_line(msg, "DEFAULT"))
        ret.append(self.curse_new_line())
        for key in self.stats["temperature"]:
            tool = self.stats["temperature"][key]
            actual = None
            target = None
            if tool["actual"] is not None:
                actual = int(tool["actual"])
            if tool["target"] is not None:
                target = int(tool["target"])
            tool_msg = "{:{width}}".format(key, width=name_max_width)
            ret.append(self.curse_add_line(tool_msg))
            tool_msg = "{actual:>3}°C  {target:>3}°C".format(key=key, actual=str(actual), target=str(target))
            ret.append(self.curse_add_line(tool_msg))
            ret.append(self.curse_new_line())

        name_max_width = max_width - 5
        actual = None
        target = None
        if self.stats["progress_printTime"] is not None:
            actual = int(self.stats["progress_printTime"])
            actual = str(datetime.timedelta(seconds=actual))
        if self.stats["progress_printTimeLeft"] is not None:
            target = int(self.stats["progress_printTimeLeft"])
            target = str(datetime.timedelta(seconds=target))
        msg = '{:{width}}'.format("Time passed:", width=name_max_width)
        ret.append(self.curse_add_line(msg))
        tool_msg = "{actual:>6}".format(actual=str(actual))
        ret.append(self.curse_add_line(tool_msg))
        ret.append(self.curse_new_line())
        msg = '{:{width}}'.format("Time left:", width=name_max_width)
        ret.append(self.curse_add_line(msg))
        tool_msg = "{target:>6}".format(target=str(target))
        ret.append(self.curse_add_line(tool_msg))
        return ret
