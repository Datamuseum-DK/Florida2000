# Florida2000 - Read punched cards with a document scanner

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
