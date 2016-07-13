# Copyright (c) 2016 NTT DATA
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import re

from oslo_log import log as logging
import six.moves.urllib.parse as urlparse

import masakari.conf
from masakari.i18n import _

CONF = masakari.conf.CONF

LOG = logging.getLogger(__name__)


def remove_trailing_version_from_href(href):
    """Removes the api version from the href.

    Given: 'http://www.masakari.com/ha/v1.1'
    Returns: 'http://www.masakari.com/ha'

    Given: 'http://www.masakari.com/v1.1'
    Returns: 'http://www.masakari.com'

    """
    parsed_url = urlparse.urlsplit(href)
    url_parts = parsed_url.path.rsplit('/', 1)

    # NOTE: this should match vX.X or vX
    expression = re.compile(r'^v([0-9]+|[0-9]+\.[0-9]+)(/.*|$)')
    if not expression.match(url_parts.pop()):
        LOG.debug('href %s does not contain version', href)
        raise ValueError(_('href %s does not contain version') % href)

    new_path = url_join(*url_parts)
    parsed_url = list(parsed_url)
    parsed_url[2] = new_path
    return urlparse.urlunsplit(parsed_url)


def url_join(*parts):
    """Convenience method for joining parts of a URL

    Any leading and trailing '/' characters are removed, and the parts joined
    together with '/' as a separator. If last element of 'parts' is an empty
    string, the returned URL will have a trailing slash.
    """
    parts = parts or [""]
    clean_parts = [part.strip("/") for part in parts if part]
    if not parts[-1]:
        # Empty last element should add a trailing slash
        clean_parts.append("")
    return "/".join(clean_parts)


class ViewBuilder(object):
    """Model API responses as dictionaries."""

    def _get_project_id(self, request):
        """Get project id from request url if present or empty string
        otherwise
        """
        project_id = request.environ["masakari.context"].project_id
        if project_id in request.url:
            return project_id
        return ''

    def _get_links(self, request, identifier, collection_name):
        return [
            {
                "rel": "self",
                "href": self._get_href_link(request, identifier,
                                            collection_name),
            },
            {
                "rel": "bookmark",
                "href": self._get_bookmark_link(request,
                                                identifier,
                                                collection_name),
            }
        ]

    def _get_next_link(self, request, identifier, collection_name):
        """Return href string with proper limit and marker params."""
        params = request.params.copy()
        params["marker"] = identifier
        prefix = self._update_masakari_link_prefix(request.application_url)
        url = url_join(prefix,
                       self._get_project_id(request),
                       collection_name)
        return "%s?%s" % (url, urlparse.urlencode(params))

    def _get_href_link(self, request, identifier, collection_name):
        """Return an href string pointing to this object."""
        prefix = self._update_masakari_link_prefix(request.application_url)
        return url_join(prefix,
                        self._get_project_id(request),
                        collection_name,
                        str(identifier))

    def _get_bookmark_link(self, request, identifier, collection_name):
        """Create a URL that refers to a specific resource."""
        base_url = remove_trailing_version_from_href(request.application_url)
        base_url = self._update_masakari_link_prefix(base_url)
        return url_join(base_url,
                        self._get_project_id(request),
                        collection_name,
                        str(identifier))

    def _get_collection_links(self,
                              request,
                              items,
                              collection_name,
                              id_key="uuid"):
        """Retrieve 'next' link, if applicable. This is included if:
        1) 'limit' param is specified and equals the number of items.
        2) 'limit' param is specified but it exceeds CONF.osapi_max_limit,
        in this case the number of items is CONF.osapi_max_limit.
        3) 'limit' param is NOT specified but the number of items is
        CONF.osapi_max_limit.
        """
        links = []
        max_items = min(
            int(request.params.get("limit", CONF.osapi_max_limit)),
            CONF.osapi_max_limit)
        if max_items and max_items == len(items):
            last_item = items[-1]
            if id_key in last_item:
                last_item_id = last_item[id_key]
            elif 'id' in last_item:
                last_item_id = last_item["id"]
            else:
                last_item_id = last_item["flavorid"]
            links.append({
                "rel": "next",
                "href": self._get_next_link(request,
                                            last_item_id,
                                            collection_name),
            })
        return links

    def _update_link_prefix(self, orig_url, prefix):
        if not prefix:
            return orig_url
        url_parts = list(urlparse.urlsplit(orig_url))
        prefix_parts = list(urlparse.urlsplit(prefix))
        url_parts[0:2] = prefix_parts[0:2]
        url_parts[2] = prefix_parts[2] + url_parts[2]
        return urlparse.urlunsplit(url_parts).rstrip('/')

    def _update_masakari_link_prefix(self, orig_url):
        return self._update_link_prefix(orig_url,
                                        CONF.osapi_masakari_link_prefix)
