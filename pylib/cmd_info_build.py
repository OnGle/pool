#!/usr/bin/python
"""Prints source build log for package"""
import re
import sys
import help
import commands

from pool import Pool
import debversion

def fatal(s):
    print >> sys.stderr, "error: " + str(s)
    sys.exit(1)

@help.usage(__doc__)
def usage():
    print >> sys.stderr, "Syntax: %s package[=version]" % sys.argv[0]

def extract_source_name(path):
    def extract_control(path):
        return commands.getoutput("ar -p %s control.tar.gz | zcat | tar -O -xf - control ./control 2>/dev/null" % path)

    def parse_control(contents):
        return dict([ re.split("\s*:\s+", line.strip(), 1)
                      for line in contents.split("\n")
                      if line.strip() and not line.startswith(" ") ])

    fields = parse_control(extract_control(path))
    if 'Source' in fields:
        return fields['Source']

    return None

def pkgcache_list_versions(pool, name):
    versions = [ pkgcache_version
                 for pkgcache_name, pkgcache_version in pool.pkgcache.list()
                 if pkgcache_name == name ]

    for subpool in pool.subpools:
        versions += pkgcache_list_versions(subpool, name)

    return versions

def pkgcache_getpath_newest(pool, name):
    versions = pkgcache_list_versions(pool, name)
    if not versions:
        return None

    versions.sort(debversion.compare)
    version_newest = versions[-1]

    package = pool.fmt_package_id(name, version_newest)
    return pool.getpath_deb(package, build=False)

def binary2source(pool, package):
    """translate package from binary to source"""
    name, version = pool.parse_package_id(package)
    if version:
        path = pool.getpath_deb(package, build=False)
        if not path:
            return None

        source_name = extract_source_name(path)
        if not source_name:
            return package

        return pool.fmt_package_id(source_name, version)

    # no version, extract source from the most recent binary
    path = pkgcache_getpath_newest(pool, name)
    if not path:
        return None
    
    source_name = extract_source_name(path)
    if not source_name:
        return name

    return source_name

def getpath_build_log(package):
    try:
        pool = Pool()
    except Pool.Error, e:
        fatal(e)

    path = pool.getpath_build_log(package)
    if path:
        return path

    # maybe package is a binary name?
    # try mapping it to a source name and trying again
    
    source_package = binary2source(pool, package)
    if source_package:
        path = pool.getpath_build_log(source_package)

    if not path:
        package_desc = `package`
        if source_package:
            package_desc += " (%s)" % source_package
        fatal("no build log for " + package_desc)

    return path

def main():
    args = sys.argv[1:]
    if not args:
        usage()

    package = args[0]
    path = getpath_build_log(package)
    
    for line in file(path).readlines():
        print line,

if __name__ == "__main__":
    main()
