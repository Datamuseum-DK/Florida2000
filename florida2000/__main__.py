#!/usr/bin/env python3
#
# BSD 2-Clause License
#
# SPDX-License-Identifier: BSD-2-Clause
#
# Copyright (c) 2020-2025, Poul-Henning Kamp
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

'''
   main function for command line use
   ==================================
'''

import sys

from . import florida2000

def main(argv):
    ''' Expects arguments to be pairs of front+back images '''

    argv.pop(0)
    for i in range(0, len(argv), 2):
        f = florida2000.PunchedCard(argv[i],  front=True,) # debug_image="/tmp/_f.png")
        f.write_crd()
        b = florida2000.PunchedCard(argv[i+1], front=False,) # debug_image="/tmp/_b.png")
        b.write_crd()
        t = f.utf8()
        if not t.isprintable():
            t = "<<binary>>"
        if f.values != b.values:
            print("bad ", [t.ljust(80)], argv[i], argv[i+1])
            for i in f.dump():
                print("# fs " + i)
            for i in b.dump():
                print("# bs " + i)
        else:
            print("good", t.ljust(80), argv[i], argv[i+1])

if __name__ == "__main__":
    main(sys.argv)
