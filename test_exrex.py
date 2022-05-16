# -*- coding: utf-8 -*-
import exrex


patterns = [
    "[\\w-]+_[0-9a-zA-Z]+"
]

for pattern in patterns:
    print("Generate [%s] --> %s" % (pattern, exrex.getone(pattern, limit=256) ) )