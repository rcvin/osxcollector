# -*- coding: utf-8 -*-
#
# RelatedDomains uses OpenDNS to find domains related to input domains or ips and adds 'osxcollector_related' key when it finds them.
#
from osxcollector.output_filters.base_filters.output_filter import OutputFilter
from osxcollector.output_filters.base_filters.output_filter import run_filter
from osxcollector.output_filters.opendns.api import InvestigateApi
from osxcollector.output_filters.util.blacklist import create_blacklist


class RelatedDomainsFilter(OutputFilter):

    """Uses OpenDNS to find domains related to input domains or ips."""

    def __init__(self, initial_domains=None, initial_ips=None, depth=2, when=None):
        """Finds domains related to domains and IPs passed in.

        Args:
            initial_domains - a list of strings
            initial_ips - a list of strings
            depth - an int. How many generations of related domains to retreive. Passing 1
              means just find the domains related to the initial input. Passing 2 means also find the
              domains related to the domains related to the initial input.
        """
        super(RelatedDomainsFilter, self).__init__()
        self._whitelist = create_blacklist(self.config.get_config('domain_whitelist'))

        self._investigate = InvestigateApi(self.config.get_config('api_key.opendns'))

        self._initial_domains = set(initial_domains) if initial_domains else set()
        self._initial_ips = set(initial_ips) if initial_ips else set()

        self._related_domains = set(initial_domains) if initial_domains else set()

        self._when = when
        self._depth = depth

        self._all_blobs = list()

    def filter_line(self, blob):
        self._all_blobs.append(blob)

        if 'osxcollector_domains' in blob and self._when(blob):
            for domain in blob.get('osxcollector_domains'):
                self._related_domains.add(domain)

        return blob

    def end_of_lines(self):
        domains = self._initial_domains
        ips = self._initial_ips

        depth = self._depth
        while depth > 0:
            domains = self._find_related_domains(domains, ips)
            ips = None

            self._related_domains |= domains
            depth -= 1

        self._related_domains = filter(lambda x: not self._whitelist.match_values(x), list(self._related_domains))

        for blob in self._all_blobs:
            if self._related_domains and 'osxcollector_domains' in blob:
                if any([domain in self._related_domains for domain in blob.get('osxcollector_domains')]):
                    blob.setdefault('osxcollector_related', [])
                    blob['osxcollector_related'].append('domains')

        return self._all_blobs

    def _find_related_domains(self, domains, ips):
        related_domains = set()

        if domains:
            related_domains.update(self._investigate.cooccurrences(domains))

        if ips:
            related_domains.update(self._investigate.rr_history(ips))

        return related_domains


def main():
    run_filter(RelatedDomainsFilter())


if __name__ == "__main__":
    main()
