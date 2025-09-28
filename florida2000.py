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
   Read Punched Cards from Scanned Images
   --------------------------------------

   This is a python hack which can read punched cards when we scan them on
   the Sony DR professional scanner we have in Datamuseum.dk.

   Punched cards as we know them are suprisingly loosely standarized and have
   surprising tight mechanical tolerances, which worn out punches do not meet.

   The mechanical standard for the cards is FIPS-13:

      https://nvlpubs.nist.gov/nistpubs/Legacy/FIPS/fipspub13.pdf

   We scan the punched cards with these parameters:

      * 150 dpi
      * greyscale (- or color, both works)
      * width = 100mm (= 590 pixels)
      * height = 200mm (= 1181 pixels)
      * duplex (so we can compare front and back readings)
      * tail-first (to get a clean front edge to work from)

   Images included in Examples/:

      * example_00_*.png - Interestingly complex card
      * example_01_*.png - Card with false hole from dark handwriting
      * example_02_*.png - Card skewed in scanner

   Our scanner scans the background and the holes as black, and
   that is what the code expects.   If your scanner scans background
   and holes as white, you will need to modify the code accordingly.

   Reading punched cards this way can never be perfect, because
   punched cards can be any color, including black and white, and
   you can print anything you want on them with any color of ink.

   If you run into a troublesome card-deck, try scanning it in color,
   then extract the three colors as separate images and see if any
   of them fare better.

   The code goes through these steps:

   1. Find the left and right card-edges down through the image and
      build a "a*y+b" model of them.

   2. Find the center front edge of the card near the bottom of the image.

   3. Use these coordinates to predict where the holes should be in the image

   4. Read the holes in column order, ie: from the bottom of the image moving up

   5. Hunt a few pixels for best contrast for each hole found, and adjust the
      theoretical positions accordingly for the rest of the card.

   6. Convert hole pattern to binary values.

   7. Convert binary values from EBCDIC to UTF8

   Note that not all cards are in EBCDIC, cards could also, and
   some did, contain raw binary data or different character sets.

'''

import sys

import imageio

from scipy import stats

# Getting from a hole-pattern (aka "hollerith code") to text is totally messed up.
#
# Long story short: IBM made up shit as they went along and that did not go well.
#
# See also:
#
#	https://nvlpubs.nist.gov/nistpubs/Legacy/FIPS/fipspub14.pdf
#
# The following table comes from Open-SIMH (Much Appreciated!) and translates
# hollerith code to EBCDIC code, and Python3's built-in support for code-page
# "cp037" can take it from there.
#
# However, the way IBM handled national characters, like the Danish Æ, Ø and Å
# was to simply replace the graphical representation of some "unused" or "little
# used" EBCDIC characters as required, so "cp037" does not get us entirely home.
#
# The Danish substitutions were: #→Æ, @→Ø and $→Å, possibly more, but you will
# have to do that yourself with a string replacement.

HOLLERITH_TO_EBCDIC = {
    0b101100000011: 0x00, 0b100100000001: 0x01, 0b100010000001: 0x02, 0b100001000001: 0x03,
    0b100000100001: 0x04, 0b100000010001: 0x05, 0b100000001001: 0x06, 0b100000000101: 0x07,
    0b100000000011: 0x08, 0b100100000011: 0x09, 0b100010000011: 0x0a, 0b100001000011: 0x0b,
    0b100000100011: 0x0c, 0b100000010011: 0x0d, 0b100000001011: 0x0e, 0b100000000111: 0x0f,
    0b110100000011: 0x10, 0b010100000001: 0x11, 0b010010000001: 0x12, 0b010001000001: 0x13,
    0b010000100001: 0x14, 0b010000010001: 0x15, 0b010000001001: 0x16, 0b010000000101: 0x17,
    0b010000000011: 0x18, 0b010100000011: 0x19, 0b010010000011: 0x1a, 0b010001000011: 0x1b,
    0b010000100011: 0x1c, 0b010000010011: 0x1d, 0b010000001011: 0x1e, 0b010000000111: 0x1f,
    0b011100000011: 0x20, 0b001100000001: 0x21, 0b001010000001: 0x22, 0b001001000001: 0x23,
    0b001000100001: 0x24, 0b001000010001: 0x25, 0b001000001001: 0x26, 0b001000000101: 0x27,
    0b001000000011: 0x28, 0b001100000011: 0x29, 0b001010000011: 0x2a, 0b001001000011: 0x2b,
    0b001000100011: 0x2c, 0b001000010011: 0x2d, 0b001000001011: 0x2e, 0b001000000111: 0x2f,
    0b111100000011: 0x30, 0b000100000001: 0x31, 0b000010000001: 0x32, 0b000001000001: 0x33,
    0b000000100001: 0x34, 0b000000010001: 0x35, 0b000000001001: 0x36, 0b000000000101: 0x37,
    0b000000000011: 0x38, 0b000100000011: 0x39, 0b000010000011: 0x3a, 0b000001000011: 0x3b,
    0b000000100011: 0x3c, 0b000000010011: 0x3d, 0b000000001011: 0x3e, 0b000000000111: 0x3f,
    0b000000000000: 0x40, 0b101100000001: 0x41, 0b101010000001: 0x42, 0b101001000001: 0x43,
    0b101000100001: 0x44, 0b101000010001: 0x45, 0b101000001001: 0x46, 0b101000000101: 0x47,
    0b101000000011: 0x48, 0b100100000010: 0x49, 0b100010000010: 0x4a, 0b100001000010: 0x4b,
    0b100000100010: 0x4c, 0b100000010010: 0x4d, 0b100000001010: 0x4e, 0b100000000110: 0x4f,
    0b100000000000: 0x50, 0b110100000001: 0x51, 0b110010000001: 0x52, 0b110001000001: 0x53,
    0b110000100001: 0x54, 0b110000010001: 0x55, 0b110000001001: 0x56, 0b110000000101: 0x57,
    0b110000000011: 0x58, 0b010100000010: 0x59, 0b010010000010: 0x5a, 0b010001000010: 0x5b,
    0b010000100010: 0x5c, 0b010000010010: 0x5d, 0b010000001010: 0x5e, 0b010000000110: 0x5f,
    0b010000000000: 0x60, 0b001100000000: 0x61, 0b011010000001: 0x62, 0b011001000001: 0x63,
    0b011000100001: 0x64, 0b011000010001: 0x65, 0b011000001001: 0x66, 0b011000000101: 0x67,
    0b011000000011: 0x68, 0b001100000010: 0x69, 0b110000000000: 0x6a, 0b001001000010: 0x6b,
    0b001000100010: 0x6c, 0b001000010010: 0x6d, 0b001000001010: 0x6e, 0b001000000110: 0x6f,
    0b111000000000: 0x70, 0b111100000001: 0x71, 0b111010000001: 0x72, 0b111001000001: 0x73,
    0b111000100001: 0x74, 0b111000010001: 0x75, 0b111000001001: 0x76, 0b111000000101: 0x77,
    0b111000000011: 0x78, 0b000100000010: 0x79, 0b000010000010: 0x7a, 0b000001000010: 0x7b,
    0b000000100010: 0x7c, 0b000000010010: 0x7d, 0b000000001010: 0x7e, 0b000000000110: 0x7f,
    0b101100000010: 0x80, 0b101100000000: 0x81, 0b101010000000: 0x82, 0b101001000000: 0x83,
    0b101000100000: 0x84, 0b101000010000: 0x85, 0b101000001000: 0x86, 0b101000000100: 0x87,
    0b101000000010: 0x88, 0b101000000001: 0x89, 0b101010000010: 0x8a, 0b101001000010: 0x8b,
    0b101000100010: 0x8c, 0b101000010010: 0x8d, 0b101000001010: 0x8e, 0b101000000110: 0x8f,
    0b110100000010: 0x90, 0b110100000000: 0x91, 0b110010000000: 0x92, 0b110001000000: 0x93,
    0b110000100000: 0x94, 0b110000010000: 0x95, 0b110000001000: 0x96, 0b110000000100: 0x97,
    0b110000000010: 0x98, 0b110000000001: 0x99, 0b110010000010: 0x9a, 0b110001000010: 0x9b,
    0b110000100010: 0x9c, 0b110000010010: 0x9d, 0b110000001010: 0x9e, 0b110000000110: 0x9f,
    0b011100000010: 0xa0, 0b011100000000: 0xa1, 0b011010000000: 0xa2, 0b011001000000: 0xa3,
    0b011000100000: 0xa4, 0b011000010000: 0xa5, 0b011000001000: 0xa6, 0b011000000100: 0xa7,
    0b011000000010: 0xa8, 0b011000000001: 0xa9, 0b011010000010: 0xaa, 0b011001000010: 0xab,
    0b011000100010: 0xac, 0b011000010010: 0xad, 0b011000001010: 0xae, 0b011000000110: 0xaf,
    0b111100000010: 0xb0, 0b111100000000: 0xb1, 0b111010000000: 0xb2, 0b111001000000: 0xb3,
    0b111000100000: 0xb4, 0b111000010000: 0xb5, 0b111000001000: 0xb6, 0b111000000100: 0xb7,
    0b111000000010: 0xb8, 0b111000000001: 0xb9, 0b111010000010: 0xba, 0b111001000010: 0xbb,
    0b111000100010: 0xbc, 0b111000010010: 0xbd, 0b111000001010: 0xbe, 0b111000000110: 0xbf,
    0b101000000000: 0xc0, 0b100100000000: 0xc1, 0b100010000000: 0xc2, 0b100001000000: 0xc3,
    0b100000100000: 0xc4, 0b100000010000: 0xc5, 0b100000001000: 0xc6, 0b100000000100: 0xc7,
    0b100000000010: 0xc8, 0b100000000001: 0xc9, 0b101010000011: 0xca, 0b101001000011: 0xcb,
    0b101000100011: 0xcc, 0b101000010011: 0xcd, 0b101000001011: 0xce, 0b101000000111: 0xcf,
    0b011000000000: 0xd0, 0b010100000000: 0xd1, 0b010010000000: 0xd2, 0b010001000000: 0xd3,
    0b010000100000: 0xd4, 0b010000010000: 0xd5, 0b010000001000: 0xd6, 0b010000000100: 0xd7,
    0b010000000010: 0xd8, 0b010000000001: 0xd9, 0b110010000011: 0xda, 0b110001000011: 0xdb,
    0b110000100011: 0xdc, 0b110000010011: 0xdd, 0b110000001011: 0xde, 0b110000000111: 0xdf,
    0b001010000010: 0xe0, 0b011100000001: 0xe1, 0b001010000000: 0xe2, 0b001001000000: 0xe3,
    0b001000100000: 0xe4, 0b001000010000: 0xe5, 0b001000001000: 0xe6, 0b001000000100: 0xe7,
    0b001000000010: 0xe8, 0b001000000001: 0xe9, 0b011010000011: 0xea, 0b011001000011: 0xeb,
    0b011000100011: 0xec, 0b011000010011: 0xed, 0b011000001011: 0xee, 0b011000000111: 0xef,
    0b001000000000: 0xf0, 0b000100000000: 0xf1, 0b000010000000: 0xf2, 0b000001000000: 0xf3,
    0b000000100000: 0xf4, 0b000000010000: 0xf5, 0b000000001000: 0xf6, 0b000000000100: 0xf7,
    0b000000000010: 0xf8, 0b000000000001: 0xf9, 0b111010000011: 0xfa, 0b111001000011: 0xfb,
    0b111000100011: 0xfc, 0b111000010011: 0xfd, 0b111000001011: 0xfe, 0b111000000111: 0xff,
}

class PunchedCard():

    '''
       Interpret an image of a punched card
       ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    '''

    # Not a variable unless somebody does the work
    DPI = 150

    # (Half-)window used to find card edges
    EDGE_WIN = 10

    # Expected X-coordinates of the edges
    EXPECT_LEFT_EDGE = 50
    EXPECT_RIGHT_EDGE = -50

    # Width of card in pixels
    CARD_X = 13 * .25 * DPI

    # The hole-pattern-box is 2*MIN_X+1 by 2*MIN_Y+1
    HOLE_Y = 3
    HOLE_X = 6

    # Threshold intensity, minimal error rate from 35 to 67 in our setup.
    THRESHOLD = 50

    # Rate of hole-position fine-tuning
    FINE_TUNE = .05

    def __init__(self, fn, front=True, debug_image = None):
        '''
           fn - image filename
           front - reverses the order of the rows if False
           debug_image - Write debug image to this file
        '''

        self.fn = fn
        self.debug = debug_image

        self.holes = []
        self.im = imageio.v3.imread(fn)
        self.ymax = self.im.shape[0]
        self.xmax = self.im.shape[1]

        self.threshold = (2 * self.HOLE_X + 1) * (2 * self.HOLE_Y + 1) * self.THRESHOLD

        if len(self.im.shape) == 3:
            # color image
            self.threshold *= self.im.shape[2]

        self.measure_skew()

        self.find_front_edge()

        self.find_holes(front)

        self.values = []
        for r in self.holes:
            self.values.append(sum(2**n*x for n,x in enumerate(reversed(r))))

        if self.debug:
            imageio.imwrite(debug_image, self.im)

    def ebcdic(self):
        ''' Convert hole-pattern to EBCDIC '''

        return bytes(HOLLERITH_TO_EBCDIC.get(i, 0) for i in self.values)

    def utf8(self, code_page='cp037'):
        ''' Convert EBCDIC to UTF-8 '''

        return self.ebcdic().decode(code_page)

    def dump(self):
        ''' Debugging aid '''

        yield self.utf8()
        for row in range(1, 13):
            i = []
            for col in range(1, 81):
                if self.holes[col-1][row-1]:
                    i.append('#')
                else:
                    i.append('-')
            yield ''.join(i)

    def center_x(self, y):
        ''' Return the center X for a given Y '''

        x1 = int(self.lrl.intercept + y * self.lrl.slope)
        x2 = int(self.lrr.intercept + y * self.lrr.slope)
        return int((x1+x2)*.5)

    def hole_coord(self, col, row):
        ''' Calculate ideal coords for a hole '''

        row -= 6.5
        col -= 1
        dx = row * .25 * self.DPI
        y = self.y_front - ((.25 + .087 * col) * self.DPI) - dx * self.lrr.slope
        x = self.center_x(y) + dx
        return x, y

    def stipple(self, x):
        ''' helper function to create stippled lines when debugging '''

        if x & 8:
            return 255
        return 0

    def measure_skew(self):
        ''' Detect the left and right edges and calculate linear regressions '''

        ys = []
        left = []
        right = []
        cl = self.EXPECT_LEFT_EDGE
        cr = self.xmax + self.EXPECT_RIGHT_EDGE
        for y in range(100, self.ymax - 200, 100):
            ys.append(y)

            xl = 0
            pk = 0
            for x in range(cl - self.EDGE_WIN, cl + self.EDGE_WIN):
                light = self.im[y][x:x+self.EDGE_WIN].astype(int).sum()
                dark = self.im[y][x-self.EDGE_WIN:x].astype(int).sum()
                if light - dark > pk:
                    pk = light - dark
                    xl = x
            left.append(xl)

            xr = 0
            pk = 0
            for x in range(cr - self.EDGE_WIN, cr + self.EDGE_WIN):
                dark = self.im[y][x:x+self.EDGE_WIN].astype(int).sum()
                light = self.im[y][x-self.EDGE_WIN:x].astype(int).sum()
                if light - dark > pk:
                    pk = light - dark
                    xr = x
            right.append(xr)

            cl = int(cl + (xl-cl) * .125)
            cr = int(cr + (cr-cr) * .125)

        self.lrl = stats.linregress(ys, left)
        self.lrr = stats.linregress(ys, right)

        if self.debug:
            # Draw the modeled card edges
            for y in range(100, self.ymax - 200):
                cx = self.center_x(y)
                for a in (-.5, .5):
                    self.im[y][int(cx + a * self.CARD_X)] = self.stipple(y)

    def find_front_edge(self):
        ''' Find the front edge of the card '''

        yb = self.ymax
        yv = 0
        for y in range(self.ymax-20, self.ymax-200, -1):
            x = self.center_x(y)
            light = self.im[y-self.EDGE_WIN:y,x-self.EDGE_WIN:x+self.EDGE_WIN].astype(int).sum()
            dark = self.im[y:y+self.EDGE_WIN,x-self.EDGE_WIN:x+self.EDGE_WIN].astype(int).sum()
            if light - dark > yv:
                yb = y
                yv = light - dark
        self.y_front = yb

        if self.debug:
            # Draw a line through the front edge
            xc = self.center_x(yb)
            y = int(yb)
            for x in range(xc - 100, xc + 100):
                self.im[int(y - (x - xc) * self.lrr.slope)][x] = self.stipple(x)

    def find_holes(self, front):
        ''' Look for 80x12 holes '''

        delta_x = 0
        delta_y = 0

        for col in range(1, 81):
            r = []
            self.holes.append(r)
            for row in range(1, 13):
                x, y = self.hole_coord(col, row)
                x = int(x + delta_x)
                y = int(y + delta_y)
                hole, _weight, dx, dy = self.is_hole(x, y)
                if front:
                    r.append(hole)
                else:
                    r.insert(0,hole)
                if hole:
                    delta_x += dx * self.FINE_TUNE
                    delta_y += dy * self.FINE_TUNE

    def is_hole(self, x, y):
        ''' Is there at hole at (x,y) ? '''

        def ww(dx, dy):
            dy += y
            dx += x
            return self.im[dy-self.HOLE_Y:dy+self.HOLE_Y+1,dx-self.HOLE_X:dx+self.HOLE_X+1].sum()

        w = 9e9
        off = (0, 0)
        for dx in (-1, 0, 1,):
            for dy in (-2, -1, 0, 1, 2):
                w2 = ww(dx, dy)
                if w2 < w:
                    w = w2
                    off = (dx, dy)

        if w < self.threshold:
            # Draw a white outline where we found a hole
            ry = y + off[0]
            rx = x + off[1]
            for dx in range(self.HOLE_X + 1):
                self.im[ry + self.HOLE_Y,rx + dx] = 255
                self.im[ry + self.HOLE_Y,rx - dx] = 255
                self.im[ry - self.HOLE_Y,rx + dx] = 255
                self.im[ry - self.HOLE_Y,rx - dx] = 255
            for dy in range(self.HOLE_Y + 1):
                self.im[ry + dy,rx - self.HOLE_X] = 255
                self.im[ry - dy,rx - self.HOLE_X] = 255
                self.im[ry + dy,rx + self.HOLE_X] = 255
                self.im[ry - dy,rx + self.HOLE_X] = 255
            return 1, w, *off

        if self.debug:
            # Indicate where we looked for, but did not find a hole
            self.im[y-self.HOLE_Y:y+self.HOLE_Y+1,x-self.HOLE_X:x+self.HOLE_X+1] //= 3
            self.im[y-self.HOLE_Y:y+self.HOLE_Y+1,x-self.HOLE_X:x+self.HOLE_X+1] += 128

        return 0, 0, 0, 0

def main(argv):
    ''' Expects arguments to be pairs of front+back images '''

    argv.pop(0)
    for i in range(0, len(argv), 2):
        f = PunchedCard(argv[i],  front=True,) # debug_image="/tmp/_f.png")
        b = PunchedCard(argv[i+1], front=False,) # debug_image="/tmp/_b.png")
        if f.values != b.values:
            print("bad ", f.utf8().ljust(80), argv[i], argv[i+1])
            for i in f.dump():
                print("# fs " + i)
            for i in b.dump():
                print("# bs " + i)
        else:
            print("good", f.utf8().ljust(80), argv[i], argv[i+1])

if __name__ == "__main__":
    main(sys.argv)
